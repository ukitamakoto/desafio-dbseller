import re

from playwright.sync_api import Page, expect


class CandidatosPage:
    URL = "/web/index.php/recruitment/viewCandidates"

    def __init__(self, page: Page):
        self.page = page
        # O texto vem com espaço inicial (" (64) Records Found").
        self.total = page.get_by_text(re.compile(r"^\s*(\(\d+\) Records? Found|No Records Found)\s*$"))
        self.linhas = page.locator(".oxd-table-body .oxd-table-card")

    def abrir(self) -> "CandidatosPage":
        self.page.goto(self.URL)
        expect(self.total).to_be_visible()
        return self

    def filtrar_por_vaga(self, vaga: str) -> "CandidatosPage":
        grupo = self.page.locator(".oxd-input-group", has=self.page.get_by_text("Vacancy", exact=True))
        grupo.locator(".oxd-select-text").click()
        self.page.get_by_role("option", name=vaga, exact=True).click()
        with self.page.expect_response(lambda r: "/api/v2/recruitment/candidates?" in r.url):
            self.page.get_by_role("button", name="Search").click()
        expect(self.total).to_be_visible()
        return self

    def quantidade(self) -> int:
        texto = self.total.inner_text()
        return 0 if texto.startswith("No") else int(re.search(r"\d+", texto).group())

    def coluna(self, indice: int) -> list[str]:
        # Colunas: seleção, Vacancy, Candidate, Hiring Manager, Date of Application, Status, Actions
        return [c.strip() for c in self.linhas.locator(f".oxd-table-cell:nth-child({indice + 1})").all_inner_texts()]
