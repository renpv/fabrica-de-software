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

## Como testar

```bash
automacao/verificar.sh
```

Roda `ruff` (check e format), os contratos de importação, a checagem de migrações e o `pytest`. É o mesmo script do CI e do pre-push. Sem variáveis definidas, ele usa o banco de desenvolvimento acima.

Para ligar os hooks do git: `~/.claude/revisao/git-hooks/instalar.sh .` e depois `pre-commit install`.

## Fluxo de branches

- `main` é a branch de integração. O trabalho sai de uma branch curta a partir da `main` e volta por PR (merge com squash).
- As branches de homologação e de produção só recebem por promoção, sempre no sentido `main` → homologação → produção.
- Correção urgente entra primeiro na `main` (*upstream first*) e depois desce para os ambientes.
- Cada task do plano tem a sua branch (`plano<P>-tarefa-<N>`) e o seu PR.
- Promover para produção depende do ok explícito do responsável.
