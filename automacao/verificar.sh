#!/usr/bin/env bash
# Verificação completa do projeto: o que o CI roda e o que o pre-push roda.
# Pode ser executado de qualquer pasta. Sai com código diferente de zero se algo falhar.
#
# Precisa de DATABASE_URL, DJANGO_SECRET_KEY, FABRICA_URL_PUBLICA e FABRICA_CHAVES_COFRE. Se não estiverem
# definidas, usa os valores do banco de desenvolvimento (docker-compose.dev.yml, porta 5434).
# No CI elas vêm do workflow e este script não sobrescreve nada.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$raiz"

export DATABASE_URL="${DATABASE_URL:-postgres://fabrica:fabrica@localhost:5434/fabrica}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-chave-so-para-verificacao-local}"
export FABRICA_URL_PUBLICA="${FABRICA_URL_PUBLICA:-http://localhost:8000}"
# Chave Fernet fixa, SÓ para verificação local e CI. Nunca use em ambiente real.
export FABRICA_CHAVES_COFRE="${FABRICA_CHAVES_COFRE:-wE4d6T-2qefhzG4CJH6IH9zc6fx0Bo4LzxoW3Pn9V4I=}"

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

cd frontend
passo "front-end: npm ci"
npm ci
passo "front-end: lint"
npm run lint
passo "front-end: tipos (tsc -b)"
npx tsc -b
passo "front-end: vitest"
npx vitest run
cd "$raiz"

passo "Verificação concluída sem erros."
