# Regressão do Recruitment — OrangeHRM (desafio QA DBSeller)

[![Regressão Recruitment](https://github.com/ukitamakoto/desafio-dbseller/actions/workflows/regressao-recruitment.yml/badge.svg)](https://github.com/ukitamakoto/desafio-dbseller/actions/workflows/regressao-recruitment.yml)

Suíte automatizada que detecta regressões no fluxo público de candidatura do módulo **Recruitment** do OrangeHRM e na consulta interna de **Candidates**. Roda em cerca de 1 minuto, por qualquer pessoa ou na pipeline, e **não grava nada na demo compartilhada**.

Este repositório é a entrega da Atividade 3. A investigação das Atividades 1 e 2 e as evidências estão no documento de evidências enviado junto.

## Fluxo escolhido e por quê

**Página pública de vagas → formulário de candidatura → candidatura visível em Candidates.**

- É a porta de entrada do processo seletivo e a única parte do Recruitment usada por pessoas anônimas. Quando quebra, ninguém de dentro percebe: o candidato desiste e a vaga simplesmente não recebe candidaturas.
- As regras do formulário são regra de negócio: campos obrigatórios, formato de e-mail e telefone, limites de caracteres, tipo e tamanho do currículo (1 MB). Elas dependem de configuração e de código compartilhado com outras telas, então mudanças em outras áreas podem quebrá-las.
- A API pública é anônima: um campo novo nela (por exemplo, o gestor da vaga) seria vazamento de dado.
- A consulta interna fecha o ciclo: o que a página pública mostra precisa bater com o que o recrutador vê.

## O que é testado

| Teste | O que verifica | Técnica |
|---|---|---|
| `test_vagas_publicas.py` · contrato da API pública | Esquema JSON fechado (`additionalProperties: false`), `meta.total` coerente, nenhuma vaga inativa ou não publicada exposta | Contrato |
| `test_vagas_publicas.py` · página pública | A página lista exatamente as vagas da API, na mesma ordem, inclusive as carregadas na rolagem | Oráculo pela API |
| `test_candidatura_validacoes.py` · envio vazio | Nome, sobrenome, e-mail e currículo exigidos, e nenhuma requisição de escrita sai do navegador | Negativo |
| `test_candidatura_validacoes.py` · limites e formatos (×8) | Nome 30/31, e-mail 50/51, e-mail sem domínio e sem arroba, telefone válido e com letras | Valor-limite, partição de equivalência |
| `test_candidatura_validacoes.py` · currículo (×4) | PDF de exatamente 1 MB aceito, 1 MB + 1 byte recusado, `.exe` e `.png` recusados | Valor-limite, negativo |
| `test_candidatura_envio.py` · candidatura válida | O POST multipart leva vaga, nome, e-mail, telefone, palavras-chave, notas, currículo e token CSRF; o consentimento desmarcado não é enviado; o diálogo de sucesso aparece | Positivo até a fronteira da gravação |
| `test_candidatura_envio.py` · gravação real (só isolado) | A candidatura é gravada, aparece em Candidates com a vaga e o status *Application Initiated* e é apagada ao final | Positivo ponta a ponta |
| `test_candidatos_consulta.py` · vagas públicas × internas | A página pública mostra exatamente as vagas ativas e publicadas do cadastro interno | Consistência entre áreas |
| `test_candidatos_consulta.py` · filtro por vaga | O filtro de Candidates mostra a mesma quantidade, a mesma vaga e os mesmos nomes que a API; resposta validada por contrato | Consistência tela × API, contrato |

São 19 testes: 18 rodam na demo compartilhada e 1 só no ambiente isolado.

## Como rodar

Pré-requisito: [uv](https://docs.astral.sh/uv/) (ele instala o Python 3.12 se faltar).

```bash
uv sync
uv run playwright install chromium
uv run pytest                 # demo pública, somente leitura
uv run pytest -m publico      # só a parte sem login (também: -m interno, -m contrato)
```

Saídas:

- `reports/relatorio.html`: relatório HTML autocontido.
- `reports/junit.xml`: para a pipeline.
- `test-results/`: trace e print de cada teste que falhar. Abra com `uv run playwright show-trace test-results/<teste>/trace.zip`.

O código de saída `3` significa que o ambiente estava fora do ar, e não regressão do produto. A suíte verifica isso antes de começar.

Variáveis opcionais: `ORANGEHRM_USUARIO`, `ORANGEHRM_SENHA` (padrão: as credenciais públicas exibidas na tela de login da demo) e `ORANGEHRM_MODO` (`compartilhado` ou `isolado`). A URL muda com `--base-url`.

## Como a suíte protege o ambiente compartilhado

- Cada contexto do navegador passa por uma guarda (`conftest.py`) que deixa passar só leitura (GET) e o login. Qualquer outra requisição é abortada e **reprova o teste**, então ninguém consegue gravar na demo sem perceber. A exceção silenciosa é a telemetria do produto (`/events/push`).
- Nos testes negativos, a validação acontece no navegador, e o teste prova que nenhuma requisição saiu.
- O cenário positivo intercepta o `POST /recruitment/public/applicants`, confere o conteúdo enviado e responde exatamente como o servidor responde no sucesso: o redirect para `?success=true`. A tela real de sucesso é então exibida e verificada.

## Ambiente isolado: fluxo completo com gravação

Para provar a gravação de verdade, a suíte roda contra um OrangeHRM 5.9 próprio, a mesma versão da demo:

```bash
./isolado/subir.sh   # Docker: OrangeHRM 5.9 + MariaDB, instalação automática, http://localhost:8200
ORANGEHRM_MODO=isolado ORANGEHRM_SENHA='Isolado@2026' uv run pytest --base-url http://localhost:8200
docker compose -f isolado/docker-compose.yml down   # apaga tudo
```

A limpeza tem três camadas:

1. Cada teste apaga, pela API e dentro de um `finally`, o que criou.
2. A massa da sessão (cargo e vaga publicada) é criada no início e removida no fim.
3. O banco roda em `tmpfs`, então derrubar os containers apaga qualquer resto.

No modo isolado a guarda deixa passar a escrita. Resultado local: 18 passaram e 1 foi pulado. O pulado é o filtro de Candidates, porque a instância nova não tem candidatos antes do teste de gravação.

## Versões

| Item | Versão |
|---|---|
| Python | 3.12.12 |
| pytest | 9.1.1 |
| pytest-playwright | 0.10.0 |
| Playwright (Python) | 1.64.0 |
| Chromium | 156.0.8078.4 |
| pytest-html | 4.2.0 |
| jsonschema | 4.26.0 |
| uv | 0.10.4 |
| OrangeHRM (demo e isolado) | OS 5.9 |

As versões exatas de todas as dependências estão travadas em `uv.lock`, e a pipeline usa `uv sync --locked`.

## Dados sintéticos

Os dados de candidato vêm de `dados/__init__.py`:

- Nome fixo `DBSQA` e sobrenome `Sintetico<8 hex>`, único por execução.
- E-mail no domínio reservado `example.com`.
- Telefone fictício.

Os currículos são gerados na hora, no diretório temporário de cada teste:

- PDF de 4 KB.
- PDF de exatamente 1.048.576 bytes, e outro com 1 byte a mais.
- `.exe` e `.png` para os tipos recusados.

Nenhum dado pessoal, credencial corporativa ou arquivo real é usado.

## Pipeline

`.github/workflows/regressao-recruitment.yml` roda em todo push e pull request, de segunda a sexta às 06:00 (Brasília) e sob demanda. Os horários fixos existem porque o problema relatado é regressão causada por mudanças em *outras* áreas. Relatório, JUnit e traces ficam como artefato da execução por 30 dias.

## Limitações conhecidas

- **A demo é compartilhada e muda o tempo todo.** Ela tem vagas criadas por outros usuários ("test"; "Tester" surgiu durante o desafio). O colaborador ligado ao Admin foi renomeado de um dia para o outro. O formato global de data está em `Y-d-m`, diferente do padrão. Por isso os testes comparam a tela com a API no momento da execução, em vez de valores fixos.
- **A demo pode ficar fora do ar.** A suíte para com o código 3 e uma mensagem clara.
- **Validação do lado do servidor.** No ambiente compartilhado não dá para testar (exigiria gravar). Ela fica para o modo isolado, ainda sem casos (ver "Como cresce").
- **O positivo na demo para na fronteira do servidor.** Ele prova o contrato entre tela e servidor, não o processamento da candidatura. O processamento é coberto pelo teste isolado.
- **Filtro de Candidates.** Depende de existir alguma vaga com candidatos, e é pulado quando não há.
- **Navegador e idioma.** Só Chromium, e mensagens em inglês (en-US), o idioma da demo.

## Como cresce

- **Mais casos no modo isolado:**
  - POST direto ao servidor com arquivo inválido (validação no servidor).
  - Candidatura para vaga inativa ou não publicada.
  - Candidatura duplicada.
  - Workflow do candidato até *Hire*, incluindo o defeito encontrado na Atividade 1: ações em vaga sem hiring manager devolvem 500.
- **Defeitos fixados em teste:** `xfail(strict=True)` por bug aberto, para a suíte avisar quando o bug for corrigido.
- **Mais navegadores:** Firefox e WebKit (`--browser firefox --browser webkit`) e viewport mobile para a página pública.
- **Acessibilidade:** axe-core no formulário público.
- **Contratos:** gerados a partir da especificação OpenAPI do OrangeHRM.
- **Pipeline:** usar a suíte como gate de deploy, com o modo isolado subindo a versão candidata via Docker.

## Estrutura

```
conftest.py            ambiente, guarda contra escrita, sessão de admin, massa do modo isolado
pages/                 Page Objects: vagas públicas, formulário de candidatura, Candidates
dados/                 fábrica de dados sintéticos e arquivos de currículo
contratos/             JSON Schema das APIs usadas pelas telas
tests/                 cenários
isolado/               OrangeHRM 5.9 descartável (Docker) e instalação automática
.github/workflows/     pipeline
```
