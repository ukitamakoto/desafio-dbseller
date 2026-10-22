"""Cenário positivo: no ambiente compartilhado vai até a fronteira da gravação; no isolado, grava e limpa."""
import re
from email.parser import BytesParser
from email.policy import default

import pytest
from playwright.sync_api import expect

from dados import arquivo, candidato
from pages.vagas_publicas import VagasPublicasPage

API_CANDIDATOS = "/web/index.php/api/v2/recruitment/candidates"


def campos_multipart(request) -> dict:
    cabecalho = f"Content-Type: {request.headers['content-type']}\r\n\r\n".encode()
    mensagem = BytesParser(policy=default).parsebytes(cabecalho + request.post_data_buffer)
    # Os campos de texto não declaram charset; o navegador envia UTF-8.
    return {p.get_param("name", header="content-disposition"): p.get_filename() or p.get_payload(decode=True).decode("utf-8")
            for p in mensagem.iter_parts()}


def abrir_formulario(page, vaga=None):
    vagas = VagasPublicasPage(page).abrir()
    vaga = vaga or vagas.nomes()[0]
    formulario = vagas.candidatar(vaga)
    return formulario, vaga, re.search(r"/applyVacancy/id/(\d+)", page.url).group(1)


@pytest.mark.publico
def test_candidatura_valida_envia_os_dados_corretos_ao_servidor(page, tmp_path):
    dados = candidato()
    formulario, _, vaga_id = abrir_formulario(page)
    enviadas = []

    def intercepta(route):
        # Responde como o servidor responde no sucesso (redirect com ?success=true), sem gravar nada.
        enviadas.append(route.request)
        route.fulfill(status=302, headers={"Location": page.url.split("?")[0] + "?success=true"})

    page.route("**/recruitment/public/applicants", intercepta)
    formulario.preencher(dados).anexar(arquivo(tmp_path, "curriculo.pdf", 4096)).enviar()

    expect(formulario.dialogo_sucesso).to_contain_text("Application Received")
    assert len(enviadas) == 1
    req = enviadas[0]
    assert req.method == "POST"
    assert req.headers["content-type"].startswith("multipart/form-data")
    campos = campos_multipart(req)
    assert campos["_token"]  # proteção CSRF presente
    assert {k: campos[k] for k in ("vacancyId", "firstName", "lastName", "email", "contactNumber", "keywords", "comment", "resume")} == {
        "vacancyId": vaga_id,
        "firstName": dados["primeiro_nome"],
        "lastName": dados["sobrenome"],
        "email": dados["email"],
        "contactNumber": dados["telefone"],
        "keywords": dados["palavras_chave"],
        "comment": dados["notas"],
        "resume": "curriculo.pdf",
    }
    assert "consentToKeepData" not in campos  # checkbox desmarcado não é enviado


@pytest.mark.isolado
def test_candidatura_valida_grava_e_aparece_em_candidates(page, admin, vaga_isolada, tmp_path):
    dados = candidato(consentimento=True)
    formulario, vaga, _ = abrir_formulario(page, vaga_isolada)

    formulario.preencher(dados).anexar(arquivo(tmp_path, "curriculo.pdf", 4096)).enviar()
    expect(formulario.dialogo_sucesso).to_contain_text("Application Received")

    lista = admin.request.get(f"{API_CANDIDATOS}?limit=50&offset=0&model=list&sortField=candidate.dateOfApplication&sortOrder=DESC").json()["data"]
    criados = [c for c in lista if c["lastName"] == dados["sobrenome"]]
    try:
        assert len(criados) == 1
        assert criados[0]["vacancy"]["name"] == vaga
        assert criados[0]["status"]["label"] == "Application Initiated"
    finally:  # limpeza mesmo se a verificação falhar
        if criados:
            admin.request.delete(API_CANDIDATOS, data={"ids": [c["id"] for c in criados]})
