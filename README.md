# Fábrica de software

Back-end em Django com DRF (e, depois, front-end em React) que orquestra agentes de IA para implementar projetos de software.

## Como rodar

Requisitos: Docker, `uv` (>= 0.13.4) e Python 3.14 (o `uv` instala sozinho).

```bash
cp .env.example .env            # preencha DJANGO_SECRET_KEY e o resto
docker compose -f docker-compose.dev.yml up -d db   # PostgreSQL 18 na porta 5434
cd backend
uv sync
set -a; source ../.env; set +a  # carrega as variáveis no terminal
uv run python manage.py migrate
uv run python manage.py runserver
```

Teste rápido: `curl http://localhost:8000/api/saude/` deve devolver `{"status":"ok"}`. O esquema da API fica em `/api/schema/`.

Para o banco do `docker-compose.dev.yml`, use `DATABASE_URL=postgres://fabrica:fabrica@localhost:5434/fabrica`.

### Front-end

Requisito: Node 26 (`frontend/.nvmrc`).

```bash
cd frontend
npm ci
npm run dev     # http://localhost:5173, com /api encaminhado para http://localhost:8000
```

Suba o back-end antes (passos acima). Depois de atualizar o `frontend/openapi.yaml`, rode `npm run gerar-api` para regenerar os tipos da API.

## Como testar

```bash
automacao/verificar.sh
```

Roda `ruff` (check e format), os contratos de importação, a checagem de migrações e o `pytest`, e depois, no front-end, `npm ci`, o lint, o `tsc -b` e o `vitest`. É o mesmo script do CI e do pre-push. Sem variáveis definidas, ele usa o banco de desenvolvimento acima.

Para ligar os hooks do git: `~/.claude/revisao/git-hooks/instalar.sh .` e depois `pre-commit install`.

## Rodar como em produção

O `docker-compose.yml` sobe a central como ela roda na VPS, com três serviços:

- `db`: PostgreSQL 18, com o volume `pgdata`. Não publica porta.
- `backend`: Django com gunicorn (usuário sem privilégios). Na entrada roda `migrate`, serve `/static/` com WhiteNoise e tem healthcheck em `/api/saude/`. Não publica porta.
- `caddy`: serve o `dist` do front-end, encaminha `/api`, `/admin` e `/static` para o back-end e entrega `/api/webhooks/*` sem cache (`Caddyfile`). É o único que publica portas (80 e 443); os volumes `caddy_data` e `caddy_config` guardam os certificados.

Variáveis obrigatórias no `.env` (modelo em `.env.example`): `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `FABRICA_URL_PUBLICA` e `FABRICA_CHAVES_COFRE`. Opcionais: `FABRICA_SITE_CADDY` (`:80` ou o domínio, para HTTPS automático), `FABRICA_PORTA_HTTP`, `FABRICA_PORTA_HTTPS` e `DJANGO_NUM_PROXIES` (1 atrás do Caddy). A `DATABASE_URL` é montada pelo compose. Nenhum segredo entra nas imagens.

```bash
cp .env.example .env     # preencha os valores
docker compose up -d --build
docker compose ps
```

Teste de fumaça (sobe o compose com um `.env` descartável na porta 18080, espera `GET /api/saude/` dar 200 pelo Caddy e derruba tudo): `automacao/fumaca.sh`. Ele não roda no CI nem no pre-push, por causa do tempo de build.

O deploy na VPS fica fora do Plano 1 e só acontece com o ok explícito do responsável.

## Fluxo de branches

- `main` é a branch de integração. O trabalho sai de uma branch curta a partir da `main` e volta por PR (merge com squash).
- As branches de homologação e de produção só recebem por promoção, sempre no sentido `main` → homologação → produção.
- Correção urgente entra primeiro na `main` (*upstream first*) e depois desce para os ambientes.
- Cada task do plano tem a sua branch (`plano<P>-tarefa-<N>`) e o seu PR.
- Promover para produção depende do ok explícito do responsável.
