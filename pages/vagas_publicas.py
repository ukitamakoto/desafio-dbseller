import re

from playwright.sync_api import Page, expect

from pages.candidatura import CandidaturaPage


class VagasPublicasPage:
    URL = "/web/index.php/recruitmentApply/jobs.html"

    def __init__(self, page: Page):
        self.page = page
        self.cards = page.locator(".orangehrm-vacancy-card-header")

    def abrir(self) -> "VagasPublicasPage":
        self.page.goto(self.URL)
        expect(self.cards.first).to_be_visible()
        return self

    def carregar_todas(self, total: int) -> "VagasPublicasPage":
        # A página carrega as vagas em blocos conforme a rolagem.
        for _ in range(total):
            if self.cards.count() >= total:
                break
            self.cards.last.scroll_into_view_if_needed()
            self.page.mouse.wheel(0, 5000)
            self.page.wait_for_load_state("networkidle")
        expect(self.cards).to_have_count(total)
        return self

    def nomes(self) -> list[str]:
        return [t.strip() for t in self.cards.locator(".oxd-text--card-title").all_inner_texts()]

    def candidatar(self, vaga: str | None = None) -> CandidaturaPage:
        """Abre o formulário da vaga pelo nome; sem nome, o da primeira vaga listada."""
        cards = self.cards
        if vaga:
            titulo = self.page.locator(".oxd-text--card-title", has_text=re.compile(rf"^{re.escape(vaga)}$"))
            cards = cards.filter(has=titulo)
        cards.first.get_by_role("button", name="Apply").click()  # first: nomes podem se repetir na demo
        return CandidaturaPage(self.page).aguardar()
