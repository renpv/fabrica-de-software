#!/usr/bin/env bash
# Teste de fumaça do empacotamento: sobe o docker-compose.yml com um .env descartável,
# espera GET /api/saude/ responder 200 pelo Caddy e derruba tudo (sempre, com down -v).
# Não entra no CI nem no pre-push: precisa de Docker e de alguns minutos de build.
set -euo pipefail

raiz="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
porta=18080
projeto=fabrica-fumaca
tmp="$(mktemp -d)"
compose=(docker compose -p "$projeto" --env-file "$tmp/.env" -f "$raiz/docker-compose.yml")

limpar() {
  "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$tmp"
}
trap limpar EXIT

# Chaves geradas na hora, só para este teste.
segredo="$(openssl rand -hex 32)"
fernet="$(openssl rand -base64 32 | tr '+/' '-_')"
senha_db="$(openssl rand -hex 16)"
cat > "$tmp/.env" <<ENV
POSTGRES_USER=fabrica
POSTGRES_PASSWORD=$senha_db
POSTGRES_DB=fabrica
DJANGO_SECRET_KEY=$segredo
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DJANGO_NUM_PROXIES=1
FABRICA_URL_PUBLICA=http://localhost:$porta
FABRICA_CHAVES_COFRE=$fernet
FABRICA_SITE_CADDY=:80
FABRICA_PORTA_HTTP=$porta
FABRICA_PORTA_HTTPS=18443
ENV

echo "==> Subindo o compose (projeto $projeto, porta $porta)"
"${compose[@]}" up -d --build

echo "==> Esperando GET /api/saude/ (até 60 s)"
for _ in $(seq 1 30); do
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$porta/api/saude/" || true)" = "200" ]; then
    echo "saúde ok"
    exit 0
  fi
  sleep 2
done

echo "A saúde não respondeu 200 em 60 s. Logs do compose:" >&2
"${compose[@]}" logs --no-color >&2 || true
exit 1
