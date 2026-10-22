import json
from pathlib import Path

import jsonschema
import pytest

from pages.vagas_publicas import VagasPublicasPage

API_PUBLICA = "/web/index.php/api/v2/recruitment/public/vacancies?limit=50&offset=0"
CONTRATO = json.loads((Path(__file__).parents[1] / "contratos" / "vagas_publicas.schema.json").read_text())

pytestmark = pytest.mark.publico


@pytest.mark.contrato
def test_api_publica_de_vagas_respeita_o_contrato(page):
    resposta = page.request.get(API_PUBLICA)
    assert resposta.ok, resposta.status
    corpo = resposta.json()

    jsonschema.validate(corpo, CONTRATO)
    assert corpo["meta"]["total"] == len(corpo["data"])
    expostas_indevidamente = [v["name"] for v in corpo["data"] if not (v["status"] and v["isPublished"])]
    assert not expostas_indevidamente, f"vaga inativa ou não publicada na página pública: {expostas_indevidamente}"


def test_pagina_publica_lista_exatamente_as_vagas_publicadas(page):
    vagas = page.request.get(API_PUBLICA).json()["data"]

    tela = VagasPublicasPage(page).abrir().carregar_todas(len(vagas))

    assert tela.nomes() == [v["name"] for v in vagas]
