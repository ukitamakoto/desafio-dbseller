"""Configuração da suíte: ambiente, guarda contra escrita e sessão de administrador."""
import os
import re
from uuid import uuid4

import pytest
from playwright.sync_api import BrowserContext, expect

# Modo "compartilhado" (padrão) nunca grava na demo pública; "isolado" é para uma instância própria.
MODO = os.getenv("ORANGEHRM_MODO", "compartilhado")
# Credenciais públicas exibidas na própria tela de login da demo; em outro ambiente, use variáveis.
USUARIO = os.getenv("ORANGEHRM_USUARIO", "Admin")
SENHA = os.getenv("ORANGEHRM_SENHA", "admin123")

LOGIN = re.compile(r"/auth/validate$")
TELEMETRIA = re.compile(r"/events/push$")  # registro de uso do produto, não faz parte do fluxo

expect.set_options(timeout=15_000)


def pytest_collection_modifyitems(config, items):
    if MODO != "isolado":
        pular = pytest.mark.skip(reason="grava dados: só roda com ORANGEHRM_MODO=isolado")
        for item in items:
            if "isolado" in item.keywords:
                item.add_marker(pular)


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezone_id": "America/Sao_Paulo",
    }


@pytest.fixture(scope="session", autouse=True)
def ambiente_disponivel(base_url, playwright):
    """Falha cedo, com mensagem clara, se o OrangeHRM estiver fora do ar (não é regressão do produto)."""
    api = playwright.request.new_context(base_url=base_url)
    try:
        resposta = api.get("/web/index.php/api/v2/recruitment/public/vacancies?limit=1", timeout=30_000)
        ok, detalhe = resposta.ok, f"HTTP {resposta.status}"
    except Exception as erro:  # rede, DNS, timeout
        ok, detalhe = False, str(erro)
    finally:
        api.dispose()
    if not ok:
        pytest.exit(f"Ambiente OrangeHRM indisponível em {base_url}: {detalhe}", returncode=3)


def proteger(context: BrowserContext) -> list[str]:
    """Aborta toda requisição de escrita (exceto login) e devolve a lista do que foi bloqueado."""
    bloqueadas: list[str] = []

    def guarda(route):
        req = route.request
        if MODO == "isolado" or req.method in ("GET", "HEAD") or LOGIN.search(req.url):
            return route.continue_()
        if not TELEMETRIA.search(req.url):
            bloqueadas.append(f"{req.method} {req.url}")
        route.abort()

    context.route("**/*", guarda)
    return bloqueadas


@pytest.fixture(autouse=True)
def sem_escrita(context):
    bloqueadas = proteger(context)
    yield bloqueadas
    assert not bloqueadas, f"Tentativa de escrita no ambiente compartilhado: {bloqueadas}"


@pytest.fixture(scope="session")
def sessao_admin(browser, base_url, tmp_path_factory, browser_context_args):
    """Login uma vez por execução; os testes internos reaproveitam o estado da sessão."""
    context = browser.new_context(**browser_context_args)
    proteger(context)
    page = context.new_page()
    page.goto("/web/index.php/auth/login")
    page.get_by_placeholder("Username").fill(USUARIO)
    page.get_by_placeholder("Password").fill(SENHA)
    page.get_by_role("button", name="Login").click()
    page.wait_for_url("**/dashboard/index")
    estado = tmp_path_factory.mktemp("sessao") / "admin.json"
    context.storage_state(path=estado)
    context.close()
    return estado


@pytest.fixture(scope="session")
def vaga_isolada(browser, sessao_admin, browser_context_args):
    """Massa própria do modo isolado: cargo e vaga ativa/publicada criados pela API e removidos ao final."""
    context = browser.new_context(**browser_context_args, storage_state=sessao_admin)
    api, base = context.request, "/web/index.php/api/v2"
    marca = uuid4().hex[:6]
    gestor = api.get(f"{base}/admin/users?username={USUARIO}").json()["data"][0]["employee"]["empNumber"]
    cargo = api.post(f"{base}/admin/job-titles", data={"title": f"QA Isolado {marca}"}).json()["data"]["id"]
    vaga = api.post(f"{base}/recruitment/vacancies", data={
        "name": f"Vaga QA Isolada {marca}", "jobTitleId": cargo, "employeeId": gestor,
        "numOfPositions": 1, "description": "Massa sintética", "status": True, "isPublished": True,
    }).json()["data"]
    yield vaga["name"]
    api.delete(f"{base}/recruitment/vacancies", data={"ids": [vaga["id"]]})
    api.delete(f"{base}/admin/job-titles", data={"ids": [cargo]})
    context.close()


@pytest.fixture(scope="session", autouse=True)
def massa_do_modo_isolado(request):
    # Instância isolada nasce vazia: semeia a vaga antes de qualquer teste precisar dela.
    if MODO == "isolado":
        return request.getfixturevalue("vaga_isolada")


@pytest.fixture
def admin(browser, sessao_admin, browser_context_args):
    """Contexto autenticado como administrador, com a mesma guarda contra escrita."""
    context = browser.new_context(**browser_context_args, storage_state=sessao_admin)
    bloqueadas = proteger(context)
    yield context
    context.close()
    assert not bloqueadas, f"Tentativa de escrita no ambiente compartilhado: {bloqueadas}"
