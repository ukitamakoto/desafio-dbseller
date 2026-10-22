"""Consulta interna (Admin), somente leitura: a tela de Candidates e a página pública contam a mesma história que a API."""
import json
from collections import Counter
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
    internas = admin.request.get(f"{API}/vacancies?limit=0").json()["data"]  # limit=0: todas
    publicas = admin.request.get(f"{API}/public/vacancies?limit=0").json()["data"]

    esperadas = sorted(v["id"] for v in internas if v["status"] and v["isPublished"])
    assert sorted(v["id"] for v in publicas) == esperadas


@pytest.mark.contrato
def test_filtro_por_vaga_em_candidates_bate_com_a_api(admin):
    vagas = admin.request.get(f"{API}/vacancies?limit=0").json()["data"]
    repetidos = Counter(v["name"] for v in vagas)
    # Massa compartilhada: vaga ativa, de nome único no filtro e com candidatos que caibam numa página.
    for vaga in (v for v in vagas if v["status"] and repetidos[v["name"]] == 1):
        corpo = admin.request.get(f"{API}/candidates?limit=50&offset=0&model=list&vacancyId={vaga['id']}"
                                  "&sortField=candidate.dateOfApplication&sortOrder=DESC").json()
        if 0 < corpo["meta"]["total"] <= 50:
            break
    else:
        pytest.skip("nenhuma vaga ativa, de nome único, com 1 a 50 candidatos na massa atual")
    jsonschema.validate(corpo, CONTRATO)

    tela = CandidatosPage(admin.new_page()).abrir().filtrar_por_vaga(vaga["name"])

    assert tela.quantidade() == corpo["meta"]["total"]
    assert set(tela.coluna(1)) == {vaga["name"]}
    assert sorted(" ".join(n.split()) for n in tela.coluna(2)) == sorted(nome_completo(c) for c in corpo["data"])
