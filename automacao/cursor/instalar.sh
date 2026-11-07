#!/usr/bin/env bash
# Instala as dependências do projeto no ambiente do Cursor. Idempotente:
# roda a cada Build e só instala o que já existe no repositório.
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ -f backend/pyproject.toml ]; then
  (cd backend && uv sync)
fi
if [ -f frontend/package-lock.json ]; then
  (cd frontend && npm ci)
fi
[ -f .env ] || { [ -f .env.example ] && cp .env.example .env; } || true
echo "ambiente pronto"
