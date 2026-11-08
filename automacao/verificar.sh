#!/usr/bin/env bash
# Verificação completa do projeto: o que o CI roda e o que o pre-push roda.
# Pode ser executado de qualquer pasta. Sai com código diferente de zero se algo falhar.
#
# Precisa de DATABASE_URL, DJANGO_SECRET_KEY e FABRICA_URL_PUBLICA. Se não estiverem
# definidas, usa os valores do banco de desenvolvimento (docker-compose.dev.yml, porta 5434).
# No CI elas vêm do workflow e este script não sobrescreve nada.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

export DATABASE_URL="${DATABASE_URL:-postgres://fabrica:fabrica@localhost:5434/fabrica}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-chave-so-para-verificacao-local}"
export FABRICA_URL_PUBLICA="${FABRICA_URL_PUBLICA:-http://localhost:8000}"

passo() { printf '\n==> %s\n' "$1"; }

cd backend
passo "back-end: ruff check"
uv run ruff check .
passo "back-end: ruff format --check"
uv run ruff format --check .
passo "back-end: contratos de importação"
uv run lint-imports
passo "back-end: migrações em dia"
uv run python manage.py makemigrations --check --dry-run
passo "back-end: pytest"
uv run pytest -q
cd "$raiz"

# --- front-end: os passos (lint, tipos e testes) entram na Task 11 ---

passo "Verificação concluída sem erros."
