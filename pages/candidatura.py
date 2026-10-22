from pathlib import Path

from playwright.sync_api import Page, expect

# Mensagens exibidas pelo OrangeHRM 5.9 (en-US).
OBRIGATORIO = "Required"
EMAIL_INVALIDO = "Expected format: admin@example.com"
TIPO_NAO_PERMITIDO = "File type not allowed"
TAMANHO_EXCEDIDO = "Attachment Size Exceeded"
LIMITE_30 = "Should not exceed 30 characters"
LIMITE_50 = "Should not exceed 50 characters"
TELEFONE_INVALIDO = "Allows numbers and only + - / ( )"


class CandidaturaPage:
    def __init__(self, page: Page):
        self.page = page
        self.titulo = page.get_by_text("Apply for ", exact=False).first
        self.primeiro_nome = page.get_by_placeholder("First Name")
        self.nome_do_meio = page.get_by_placeholder("Middle Name")
        self.sobrenome = page.get_by_placeholder("Last Name")
        self.email = page.locator(".oxd-input-group", has=page.get_by_text("Email", exact=True)).locator("input")
        self.telefone = page.locator(".oxd-input-group", has=page.get_by_text("Contact Number", exact=True)).locator("input")
        self.curriculo = page.locator("input[type=file]")
        self.palavras_chave = page.get_by_placeholder("Enter comma seperated words...")  # grafia do próprio produto
        self.notas = page.locator("textarea")
        self.consentimento = page.get_by_text("Consent to keep data", exact=True)
        self.enviar_botao = page.get_by_role("button", name="Submit")
        self.dialogo_sucesso = page.locator(".oxd-dialog-sheet")

    def aguardar(self) -> "CandidaturaPage":
        self.page.wait_for_url("**/applyVacancy/id/**")
        expect(self.titulo).to_be_visible()
        return self

    def preencher(self, dados: dict) -> "CandidaturaPage":
        self.primeiro_nome.fill(dados.get("primeiro_nome", ""))
        self.nome_do_meio.fill(dados.get("nome_do_meio", ""))
        self.sobrenome.fill(dados.get("sobrenome", ""))
        self.email.fill(dados.get("email", ""))
        self.telefone.fill(dados.get("telefone", ""))
        self.palavras_chave.fill(dados.get("palavras_chave", ""))
        self.notas.fill(dados.get("notas", ""))
        if dados.get("consentimento"):
            self.consentimento.click()
        return self

    def anexar(self, arquivo: Path) -> "CandidaturaPage":
        self.curriculo.set_input_files(arquivo)
        return self

    def enviar(self) -> "CandidaturaPage":
        self.enviar_botao.click()
        return self

    def erros(self) -> dict[str, str]:
        """Mensagem de validação por campo, identificado pelo rótulo ou pelo placeholder.

        Espera a validação renderizar; pressupõe ao menos uma mensagem na tela (há sempre um obrigatório vazio).
        """
        expect(self.page.locator(".oxd-input-field-error-message").first).to_be_visible()
        return self.page.evaluate(
            """() => Object.fromEntries([...document.querySelectorAll('.oxd-input-field-error-message')].map(e => {
                const grupo = e.closest('.oxd-input-group');
                const rotulo = grupo.querySelector('.oxd-input-group__label-wrapper label')?.innerText.replace('*', '').trim();
                return [rotulo || grupo.querySelector('input')?.placeholder, e.innerText.trim()];
            }))"""
        )
