# Fábrica de software

Orquestra agentes de IA que implementam projetos. Back-end Django + DRF em `backend/`; front-end React com TypeScript em `frontend/` (a partir da Task 11 do Plano 1).

## Comandos
- Banco: `docker compose -f docker-compose.dev.yml up -d db` (PostgreSQL 18, porta 5434).
- Verificação completa: `automacao/verificar.sh` (ruff, contratos de importação, migrações, pytest). É o que o CI e o pre-push rodam.
- Testes: `cd backend && uv run pytest`. Exigem `DATABASE_URL`, `DJANGO_SECRET_KEY`, `FABRICA_URL_PUBLICA` e `FABRICA_CHAVES_COFRE` (modelo em `.env.example`).

## Onde cada versão é fixada
- Python 3.14: `backend/.python-version` e `requires-python` em `backend/pyproject.toml`.
- Django `>=5.2.19,<5.3` e as outras dependências: `backend/pyproject.toml`, travadas em `backend/uv.lock`.
- uv: `[tool.uv] required-version` em `backend/pyproject.toml`; no CI, `version` do `setup-uv` em `.github/workflows/ci.yml`.
- PostgreSQL 18: `docker-compose.dev.yml` e `ci.yml`.
- Node 26: `frontend/.nvmrc` (Task 11).
- Fonte e motivos: `docs/pesquisa/2026-11-07-versoes-da-stack.md`.

## Configuração
Só por variável de ambiente (12-factor). Lista em `.env.example`. Atrás de proxy (Caddy), defina `DJANGO_NUM_PROXIES=1`; com 0 o limite de login usa o IP direto e ignora `X-Forwarded-For`. Segredo nunca aparece em resposta da API, log nem mensagem de erro.

## Módulos e contratos de importação
Os módulos ficam em `backend/apps/`. Os contratos estão em `backend/.importlinter` e são checados por `lint-imports`:
- `cofre` e `donos` não importam ninguém;
- `agentes` e `plataformas` só importam `cofre` e `donos`;
- `fluxos` importa `agentes`;
- `projetos` importa `plataformas`, `fluxos` e `agentes`.

Ao criar um módulo, acrescente o contrato dele no `.importlinter`. Views e API só chamam `servicos.py`.

## Fluxo
- `main` → homologação → produção, com *upstream first* para correções.
- Uma branch por task, `plano<P>-tarefa-<N>`, um PR por task, merge com squash.
- Commits em Conventional Commits em português, assinados, citando `Plano <P> · Task <N>`.
- Texto de interface e mensagens de erro em português do Brasil, dizendo o que fazer.
