"""Cenários negativos e de limite: tudo é barrado no navegador, nada chega ao servidor."""
import pytest

from dados import MB, arquivo
from pages import candidatura as msg

pytestmark = pytest.mark.publico

OBRIGATORIOS = {"First Name": msg.OBRIGATORIO, "Last Name": msg.OBRIGATORIO, "Email": msg.OBRIGATORIO, "Resume": msg.OBRIGATORIO}


def esperados(preenchido: str, erro: str | None) -> dict[str, str]:
    """Os obrigatórios que ficaram vazios, mais o erro do campo preenchido, se houver."""
    return {k: v for k, v in OBRIGATORIOS.items() if k != preenchido} | ({preenchido: erro} if erro else {})


def test_envio_vazio_exige_todos_os_campos_obrigatorios(formulario, sem_escrita):
    formulario.enviar()

    assert formulario.erros(4) == OBRIGATORIOS
    assert sem_escrita == []  # validação no cliente: nenhuma requisição de escrita saiu


@pytest.mark.parametrize(
    ("campo", "rotulo", "valor", "esperado"),
    [
        ("primeiro_nome", "First Name", "A" * 30, None),
        ("primeiro_nome", "First Name", "A" * 31, msg.LIMITE_30),
        ("email", "Email", "a" * 38 + "@example.com", None),
        ("email", "Email", "a" * 39 + "@example.com", msg.LIMITE_50),
        ("email", "Email", "dbsqa@", msg.EMAIL_INVALIDO),
        ("email", "Email", "dbsqa.example.com", msg.EMAIL_INVALIDO),
        ("telefone", "Contact Number", "+55 (51) 99999-0000", None),
        ("telefone", "Contact Number", "abc123", msg.TELEFONE_INVALIDO),
        ("palavras_chave", "Keywords", "k" * 250, None),
        ("palavras_chave", "Keywords", "k" * 251, msg.LIMITE_250),
        ("notas", "Notes", "n" * 250, None),
        ("notas", "Notes", "n" * 251, msg.LIMITE_250),
    ],
    ids=["nome-30-aceito", "nome-31-recusado", "email-50-aceito", "email-51-recusado",
         "email-sem-dominio", "email-sem-arroba", "telefone-valido", "telefone-com-letras",
         "keywords-250-aceito", "keywords-251-recusado", "notas-250-aceito", "notas-251-recusado"],
)
def test_limites_e_formatos_dos_campos(formulario, campo, rotulo, valor, esperado):
    formulario.preencher({campo: valor}).enviar()

    erros = esperados(rotulo, esperado)
    assert formulario.erros(len(erros)) == erros


@pytest.mark.parametrize(
    ("nome", "tamanho", "cabecalho", "esperado"),
    [
        ("curriculo.pdf", MB, b"%PDF-1.4\n", None),
        ("curriculo.pdf", MB + 1, b"%PDF-1.4\n", msg.TAMANHO_EXCEDIDO),
        ("curriculo.exe", 2048, b"MZ", msg.TIPO_NAO_PERMITIDO),
        ("curriculo.png", 2048, b"\x89PNG\r\n", msg.TIPO_NAO_PERMITIDO),
    ],
    ids=["pdf-1MB-exato-aceito", "pdf-1MB+1-byte-recusado", "extensao-exe", "extensao-png"],
)
def test_curriculo_respeita_tipo_e_tamanho(formulario, tmp_path, nome, tamanho, cabecalho, esperado):
    formulario.anexar(arquivo(tmp_path, nome, tamanho, cabecalho)).enviar()

    erros = esperados("Resume", esperado)
    assert formulario.erros(len(erros)) == erros
