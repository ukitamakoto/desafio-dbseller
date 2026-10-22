"""Validação no servidor sem passar pelo navegador (POST direto). Só no ambiente isolado."""
import re

import pytest

from dados import CABECALHO_PDF, MB

pytestmark = pytest.mark.isolado

ENVIO = "/web/index.php/recruitment/public/applicants"
CANDIDATOS = "/web/index.php/api/v2/recruitment/candidates?limit=0&model=list"
PDF_PEQUENO = ("curriculo.pdf", "application/pdf", CABECALHO_PDF + b"0" * 2048)


def enviar_direto(api, vaga_id, primeiro="DBSQA", sobrenome="SinteticoServidor", email="dbsqa.servidor@example.com", arquivo=PDF_PEQUENO):
    """Reproduz o POST do formulário público, com o token CSRF da própria página."""
    html = api.get(f"/web/index.php/recruitmentApply/applyVacancy/id/{vaga_id}").text()
    token = re.search(r':token="&quot;(.*?)&quot;"', html).group(1)
    nome, tipo, conteudo = arquivo
    return api.post(ENVIO, max_redirects=0, multipart={
        "_token": token, "vacancyId": str(vaga_id), "firstName": primeiro, "middleName": "", "lastName": sobrenome,
        "email": email, "contactNumber": "", "keywords": "", "comment": "",
        "resume": {"name": nome, "mimeType": tipo, "buffer": conteudo},
    })


@pytest.mark.parametrize(
    "ajuste",
    [
        {"arquivo": ("curriculo.exe", "application/x-msdownload", b"MZ" + b"0" * 2048)},
        {"arquivo": ("curriculo.pdf", "application/pdf", CABECALHO_PDF + b"0" * int(1.5 * MB))},
        {"primeiro": "A" * 40},
        {"primeiro": "   ", "sobrenome": "   "},
        {"email": "nao-e-email"},
    ],
    ids=["extensao-exe", "pdf-1,5MB", "nome-40", "nome-so-espacos", "email-invalido"],
)
def test_servidor_recusa_dado_invalido_sem_gravar(page, admin, vaga_isolada, ajuste):
    antes = admin.request.get(CANDIDATOS).json()["meta"]["total"]

    resposta = enviar_direto(page.request, vaga_isolada["id"], **ajuste)

    assert resposta.status == 400
    assert admin.request.get(CANDIDATOS).json()["meta"]["total"] == antes


@pytest.mark.xfail(strict=True, reason="BUG-08: currículo acima do upload_max_filesize do PHP (2 MB) gera HTTP 500 em vez de recusa")
def test_servidor_recusa_curriculo_acima_de_2MB_sem_erro_interno(page, vaga_isolada):
    resposta = enviar_direto(page.request, vaga_isolada["id"], arquivo=("curriculo.pdf", "application/pdf", CABECALHO_PDF + b"0" * (2 * MB + 1024)))

    assert resposta.status == 400
