"""Dados sintéticos: nenhuma pessoa real, domínio reservado example.com e arquivos gerados na hora."""
from pathlib import Path
from uuid import uuid4

MB = 1024 * 1024  # limite configurado no OrangeHRM 5.9 (max-file-size = 1048576)
CABECALHO_PDF = b"%PDF-1.4\n% curriculo sintetico - desafio QA\n"


def candidato(**ajustes) -> dict:
    marca = uuid4().hex[:8]
    return {
        "primeiro_nome": "DBSQA",
        "sobrenome": f"Sintetico{marca}",
        "email": f"dbsqa.{marca}@example.com",
        "telefone": "+55 (51) 99999-0000",
        "palavras_chave": "playwright, pytest, regressao",
        "notas": "Candidatura sintética gerada pela suíte de regressão.",
        **ajustes,
    }


def arquivo(pasta: Path, nome: str, tamanho: int, cabecalho: bytes = CABECALHO_PDF) -> Path:
    caminho = pasta / nome
    caminho.write_bytes(cabecalho + b"0" * max(0, tamanho - len(cabecalho)))
    return caminho
