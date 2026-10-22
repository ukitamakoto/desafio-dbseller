"""Consulta interna (Admin), somente leitura: a tela de Candidates e a página pública contam a mesma história que a API."""
import json
from pathlib import Path

import jsonschema
import pytest

from pages.candidatos import CandidatosPage

API = "/web/index.php/api/v2/recruitment"
CONTRATO = json.loads((Path(__file__).parents[1] / "contratos" / "candidatos.schema.json").read_text())

pytestmark = pytest.mark.interno


def nome_completo(c: dict) -> str:
    return " ".join(p for p in (c["firstName"], c["middleName"], c["lastName"]) if p)


def test_pagina_publica_mostra_so_vagas_ativas_e_publicadas(admin):
    internas = admin.request.get(f"{API}/vacancies?limit=50&offset=0").json()["data"]
    publicas = admin.request.get(f"{API}/public/vacancies?limit=50&offset=0").json()["data"]

    esperadas = sorted(v["id"] for v in internas if v["status"] and v["isPublished"])
    assert sorted(v["id"] for v in publicas) == esperadas


@pytest.mark.contrato
def test_filtro_por_vaga_em_candidates_bate_com_a_api(admin):
    vagas = admin.request.get(f"{API}/vacancies?limit=50&offset=0").json()["data"]
    for vaga in vagas:  # a massa é compartilhada: usa a primeira vaga que tiver candidatos
        corpo = admin.request.get(f"{API}/candidates?limit=50&offset=0&model=list&vacancyId={vaga['id']}"
                                  "&sortField=candidate.dateOfApplication&sortOrder=DESC").json()
        if corpo["meta"]["total"]:
            break
    else:
        pytest.skip("nenhuma vaga com candidatos na massa atual")
    jsonschema.validate(corpo, CONTRATO)

    tela = CandidatosPage(admin.new_page()).abrir().filtrar_por_vaga(vaga["name"])

    assert tela.quantidade() == corpo["meta"]["total"]
    assert set(tela.coluna(1)) == {vaga["name"]}
    assert sorted(" ".join(n.split()) for n in tela.coluna(2)) == sorted(nome_completo(c) for c in corpo["data"])
