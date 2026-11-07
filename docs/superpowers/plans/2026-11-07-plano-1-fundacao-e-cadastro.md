# Plano 1: Fundação e cadastro, implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ter a central no ar, em desenvolvimento, com login, cofre de segredos e o cadastro guiado de contas de agente (Cursor e Claude local), de conexões com o GitHub e o GitLab, de projetos (com o repositório preparado e conferido pela central) e de predefinições de fluxo. A execução do fluxo fica para os próximos planos.

**Architecture:** Monólito modular em Django 5.2 + DRF (`backend/apps/<módulo>`), com uma camada de serviços por módulo e adaptadores (padrão Strategy + Adapter) para cada agente e cada plataforma, registrados por tipo. Front-end React + TypeScript + Mantine (`frontend/`) que consome a API tipada pelo OpenAPI. Toda entidade pertence a um `Dono`, e o isolamento é garantido por um mixin de queryset e por testes.

**Tech Stack:** Python 3.13, uv, Django >=5.2,<5.3, DRF, drf-spectacular, django-environ, cryptography (Fernet), httpx + respx, PyJWT[crypto], pytest-django, import-linter, PostgreSQL 17 · Node 22, React 19, Vite, TypeScript, Mantine 9, TanStack Query 5, openapi-fetch, openapi-typescript, Vitest, Testing Library, MSW, oxlint (as mesmas do top-tenis, `~/dev/top-tenis/backend/pyproject.toml` e `frontend/package.json`).

**Spec:** `docs/superpowers/specs/2026-11-07-fabrica-de-software-design.md`

## Onde este plano entra

A spec foi dividida em planos que entregam software funcionando cada um (escolha do Claude, trocável):

1. **Fundação e cadastro** (este).
2. **Runner local e adaptador Claude:** o PC conecta, recebe trabalho e roda o `claude` numa worktree.
3. **Motor de fluxo:** registrar spec a partir do plano aprovado, publicar tasks, executar (Cursor e Claude), revisar, merge, ajuste por spec, efeito "na próxima etapa".
4. **Pendências e PWA:** caixa de decisões, Web Push e respostas.
5. **Deploy na VPS** (depende do ok do Renato).

## Global Constraints

- Python 3.13 fixado em `backend/.python-version`; Node 22 em `frontend/.nvmrc`; Django `>=5.2,<5.3`; PostgreSQL 17.
- Banco de desenvolvimento e testes na porta **5434** (o top-tenis usa a 5433).
- Configuração só por variável de ambiente (12-factor): `DATABASE_URL`, `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `FABRICA_URL_PUBLICA`, `FABRICA_CHAVES_COFRE` (lista separada por vírgula; a primeira cifra, todas decifram). `.env.example` sem valores reais.
- Segredos nunca aparecem em resposta da API, log, `repr`, mensagem de erro nem fixture. Na API são só de escrita; a leitura devolve `tem_credenciais: bool`.
- Toda entidade de domínio herda `PertenceADono`; toda view de domínio usa `EscopoDoDonoMixin`.
- Toda chamada HTTP externa usa `httpx` com timeout de 10 s. Nos testes não há rede real: tudo com `respx`.
- Textos de interface e mensagens de erro em português do Brasil, dizendo o que fazer ("A chave foi recusada pelo Cursor. Gere uma nova e cole aqui.").
- Contratos de importação (`backend/.importlinter`): `cofre` e `donos` não importam ninguém; `agentes` e `plataformas` só importam `cofre` e `donos`; `fluxos` importa `agentes`; `projetos` importa `plataformas`, `fluxos`, `agentes`. Views e API só chamam `servicos.py`.
- Commits em Conventional Commits em português, citando `Plano 1 · Task N`, assinados.
- Branch `tarefa-<issue>` a partir da `origin/main` **atual** (`git fetch origin` antes), com rebase sobre `origin/main` antes do PR. PR pronto para revisão, não rascunho. Contrato completo em `automacao/cursor/PROMPT.md`.

## Review Focus

1. **Credencial colada com espaço ou quebra de linha no fim** (chave do Cursor, token do GitLab): a central limpa as pontas antes de testar e salvar; a chave PEM do GitHub mantém as quebras internas. Testes nas Tasks 4 e 7.
2. **"Preparar" rodado duas vezes, ou etiqueta que já existe com outra cor:** nada é duplicado e nada falha (o GitHub responde 422 `already_exists`). Testes nas Tasks 6 e 7.
3. **GitLab com URL digitada de vários jeitos** (`https://gitlab.unilab.edu.br/`, com `/api/v4`, sem `https://`) **ou fora do ar:** a URL é normalizada e a falha de rede vira mensagem clara, sem stack trace. Teste na Task 7.
4. **Mais de 100 repositórios:** a listagem percorre todas as páginas. Testes nas Tasks 6 e 7.
5. **Webhook reentregue ou de origem desconhecida:** a reentrega não duplica o evento; assinatura inválida ou instalação desconhecida não grava nada. Teste na Task 10.

---

### Task 1: Base do repositório e do back-end

Cobre o checklist de projeto novo (`~/.claude/revisao/projeto-novo.md`) no que cabe ao código.

**Files:**
- Create: `backend/pyproject.toml`, `backend/.python-version`, `backend/manage.py`, `backend/config/{__init__,settings,urls,wsgi}.py`, `backend/apps/__init__.py`, `backend/apps/saude/{__init__,apps,views}.py`, `backend/pytest.ini`, `backend/conftest.py`, `backend/.importlinter`
- Create: `docker-compose.dev.yml` (serviço `db`, `postgres:17`, porta `5434:5432`)
- Create: `automacao/verificar.sh` (lint, contratos de importação, `makemigrations --check`, pytest e, a partir da Task 11, lint, tipos e testes do front-end), `.github/workflows/ci.yml` (roda `automacao/verificar.sh` com um serviço Postgres 17)
- Create: `.gitignore`, `.env.example`, `README.md` (como rodar, testar e o fluxo `main` → homologação → produção com *upstream first*), `CLAUDE.md` (propósito, comandos, onde cada versão é fixada, módulos e contratos)
- Run: `~/.claude/revisao/git-hooks/instalar.sh .` (gera o `.pre-commit-config.yaml`); no pre-push, troque o `echo` da base por `automacao/verificar.sh`
- Test: `backend/tests/test_saude.py`

**Interfaces:**
- Produces: `GET /api/saude/` → `200 {"status": "ok"}`, sem login; `settings.FABRICA_URL_PUBLICA: str`; lint com `ruff` (check + format) no pre-commit e no `verificar.sh`.

- [ ] **Step 1: Escrever o teste que falha**

```python
def test_saude_responde_ok(client):
    resposta = client.get("/api/saude/")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `cd backend && uv run pytest tests/test_saude.py -v`. Expected: FAIL (projeto inexistente ou 404).
- [ ] **Step 3: Criar o projeto** com `uv init`, as dependências da Tech Stack, `settings.py` lendo tudo com `django-environ`, DRF com `SessionAuthentication` e `IsAuthenticated` por padrão, drf-spectacular em `/api/schema/`, e a view de saúde com `AllowAny`.
- [ ] **Step 4: Rodar e ver passar.** Run: `docker compose -f docker-compose.dev.yml up -d db && cd backend && uv run pytest -v`. Expected: PASS.
- [ ] **Step 5: Verificação completa.** Run: `automacao/verificar.sh`. Expected: termina com código 0.
- [ ] **Step 6: Commit** (`git add` por caminho): `chore: cria a base do repositório e do back-end (Plano 1 · Task 1)`. Confira com `git log -1 --format=%G?` que a saída é `G`.

---

### Task 2: Donos, login e isolamento

**Files:**
- Create: `backend/apps/donos/{__init__,apps,models,servicos,middleware,mixins,views,urls}.py`, `backend/apps/donos/management/commands/criar_dono.py`, migração
- Test: `backend/tests/donos/test_sessao.py`, `backend/tests/donos/test_isolamento.py`

**Interfaces:**
- Produces:
  - `Dono(id: UUID, nome: str, criado_em)`; `Membro(usuario: OneToOne[User], dono: FK[Dono])`.
  - `PertenceADono` (modelo abstrato): `id: UUIDField(primary_key)`, `dono: FK[Dono]`, `criado_em`, `atualizado_em`; manager com `.do_dono(dono) -> QuerySet`.
  - `DonoMiddleware`: define `request.dono` (ou `None` sem login).
  - `EscopoDoDonoMixin` (DRF): `get_queryset()` filtra por `request.dono`; `perform_create()` grava `dono=request.dono`.
  - `POST /api/sessao/ {usuario, senha}` → `200 {usuario, dono: {id, nome}}` ou `400 {"detail": "Usuário ou senha incorretos."}`; `GET /api/sessao/` → `200` igual, ou `403`; `DELETE /api/sessao/` → `204`. Mantém o CSRF do Django (o front lê o cookie `csrftoken`).
  - `manage.py criar_dono --nome NOME --usuario USUARIO --email EMAIL`: pede a senha com `getpass` (o segredo não passa por argumento).

- [ ] **Step 1: Escrever os testes que falham**

```python
def test_login_devolve_o_dono(client, membro_factory):
    membro = membro_factory(usuario__username="renato", senha="s3nha-forte")
    r = client.post("/api/sessao/", {"usuario": "renato", "senha": "s3nha-forte"}, content_type="application/json")
    assert r.status_code == 200
    assert r.json()["dono"]["id"] == str(membro.dono.id)

def test_login_errado_explica(client, membro_factory):
    membro_factory(usuario__username="renato", senha="s3nha-forte")
    r = client.post("/api/sessao/", {"usuario": "renato", "senha": "x"}, content_type="application/json")
    assert r.status_code == 400 and r.json()["detail"] == "Usuário ou senha incorretos."

def test_mixin_nao_cruza_donos(rf, membro_factory):
    # Modelo de teste concreto (app de testes) herdando PertenceADono; uma ViewSet com o mixin.
    # Cria um registro para cada um de dois donos; a lista do dono A tem só o registro de A,
    # e o GET do registro de B pelo dono A dá 404.
```

Os testes usam um modelo concreto de apoio em `backend/tests/apoio/` (app `tests.apoio`, só em `INSTALLED_APPS` no `pytest.ini` via `DJANGO_SETTINGS_MODULE=config.settings_teste`).

- [ ] **Step 2: Rodar e ver falhar.** Run: `uv run pytest tests/donos -v`. Expected: FAIL.
- [ ] **Step 3: Implementar** os modelos, o middleware, o mixin, as views de sessão (`authenticate` + `login`) e o comando.
- [ ] **Step 4: Rodar e ver passar.** Run: `uv run pytest tests/donos -v`. Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona donos, login e isolamento por dono (Plano 1 · Task 2)`.

---

### Task 3: Cofre de segredos

**Files:**
- Create: `backend/apps/cofre/{__init__,apps,servicos,campos}.py`
- Test: `backend/tests/cofre/test_cofre.py`

**Interfaces:**
- Produces:
  - `cofre.servicos.cifrar(texto: str) -> str` e `decifrar(token: str) -> str`, com `MultiFernet` das chaves de `FABRICA_CHAVES_COFRE`.
  - `cofre.servicos.ChaveDoCofreAusente(Exception)`, levantada na inicialização (`AppConfig.ready`) quando a variável está vazia, com a mensagem "Defina FABRICA_CHAVES_COFRE. Gere uma chave com: uv run python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"".
  - `cofre.campos.CampoSecretoJSON(models.TextField)`: o Python vê um `dict[str, str]`, e o banco guarda o texto cifrado. `deconstruct` compatível com migrações.
  - `cofre.campos.ValorSecreto`: o `dict` devolvido pelo campo é desta subclasse, com `__repr__`/`__str__` = `"<segredo>"`, para não vazar em log nem em erro.

- [ ] **Step 1: Escrever os testes que falham:** `test_ida_e_volta` (`decifrar(cifrar("abc")) == "abc"`); `test_rotacao` (cifrado com a chave antiga, decifra com `FABRICA_CHAVES_COFRE="nova,antiga"`); `test_banco_guarda_cifrado` (o valor bruto lido por SQL não contém o texto puro); `test_repr_nao_vaza` (`"abc" not in repr(obj.credenciais)`); `test_sem_chave_falha_com_instrucao`.
- [ ] **Step 2: Rodar e ver falhar.** Run: `uv run pytest tests/cofre -v`. Expected: FAIL.
- [ ] **Step 3: Implementar** o serviço e o campo.
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona o cofre de segredos cifrados (Plano 1 · Task 3)`.

---

### Task 4: Contas de agente, modelo e provedores

**Files:**
- Create: `backend/apps/agentes/{__init__,apps,models,servicos}.py`, `backend/apps/agentes/provedores/{__init__,base,cursor,claude_local}.py`, migração
- Create: `backend/apps/donos/models.py`: acrescentar `Cliente(PertenceADono): nome: str`
- Test: `backend/tests/agentes/test_provedores.py`, `backend/tests/agentes/test_servicos.py`

**Interfaces:**
- Consumes: `PertenceADono`, `CampoSecretoJSON`.
- Produces:

```python
@dataclass(frozen=True)
class ResultadoTeste:
    ok: bool
    status: Literal["ok", "falha", "aguardando_runner"]
    mensagem: str            # pt-BR, pronta para mostrar

@dataclass(frozen=True)
class CampoCadastro:
    chave: str; rotulo: str; secreto: bool; ajuda: str; obrigatorio: bool = True

@dataclass(frozen=True)
class PassoGuia:
    texto: str; link: str | None = None

class ProvedorDeAgente(Protocol):
    tipo: str; nome: str
    campos: list[CampoCadastro]
    guia: list[PassoGuia]
    def testar(self, credenciais: dict[str, str], config: dict) -> ResultadoTeste: ...

# provedores/__init__.py
REGISTRO: dict[str, ProvedorDeAgente]   # "cursor", "claude_local"
def obter_provedor(tipo: str) -> ProvedorDeAgente   # KeyError vira ValueError("Tipo de agente desconhecido: <tipo>")
```

  - `ContaAgente(PertenceADono)`: `nome`, `tipo` (choices do registro), `cliente: FK[Cliente] | None`, `credenciais: CampoSecretoJSON`, `config: JSONField(default=dict)`, `limite_simultaneo: PositiveSmallInteger = 1`, `status` (`nao_testada` | `ok` | `falha` | `aguardando_runner`), `ultimo_teste_em: datetime | None`, `ultimo_teste_mensagem: str`.
  - `agentes.servicos.limpar_credenciais(tipo: str, dados: dict[str, str]) -> dict[str, str]`: tira os espaços e as quebras de linha das pontas de cada valor (Review Focus 1).
  - `agentes.servicos.testar_dados(tipo, credenciais, config) -> ResultadoTeste` (sem salvar) e `testar_conta(conta) -> ResultadoTeste` (grava `status`, `ultimo_teste_em` e `ultimo_teste_mensagem`).
- Cursor (`tipo="cursor"`): um campo `api_key` (secreto). `testar` faz `GET https://api.cursor.com/v1/me` com `Authorization: Bearer <api_key>`. Com 200, a mensagem é `"Conectado como <userEmail ou apiKeyName>."`; com 401/403, `"A chave foi recusada pelo Cursor. Gere uma nova no painel do Cursor e cole aqui."`; com erro de rede ou timeout, `"Não consegui falar com o Cursor agora. Tente de novo em instantes."`. O guia aponta para o painel do Cursor (`https://cursor.com/dashboard`) e para a doc da API; confira na doc o caminho exato da tela de chaves antes de escrever o texto do passo.
- Claude local (`tipo="claude_local"`): sem campos secretos; `config` aceita `rotulo_maquina: str`. `testar` devolve `ResultadoTeste(ok=False, status="aguardando_runner", mensagem="Esta conta fica pronta quando o runner do seu PC se conectar.")`. O guia explica que o login é o do `claude` já feito no PC (restrição da spec, seção 7).

- [ ] **Step 1: Escrever os testes que falham**

```python
@respx.mock
def test_cursor_ok_mostra_quem_conectou():
    respx.get("https://api.cursor.com/v1/me").respond(200, json={"apiKeyName": "fabrica", "userEmail": "r@x.com"})
    r = obter_provedor("cursor").testar({"api_key": "k"}, {})
    assert r.ok and r.status == "ok" and r.mensagem == "Conectado como r@x.com."

@respx.mock
def test_cursor_chave_recusada(): ...      # 401 → mensagem de chave recusada, ok False, status "falha"
@respx.mock
def test_cursor_fora_do_ar(): ...          # httpx.ConnectTimeout → mensagem de rede
@respx.mock
def test_cursor_envia_chave_limpa():       # Review Focus 1
    rota = respx.get("https://api.cursor.com/v1/me").respond(200, json={"apiKeyName": "a"})
    testar_dados("cursor", {"api_key": "  k123\n"}, {})
    assert rota.calls.last.request.headers["Authorization"] == "Bearer k123"
def test_claude_local_aguarda_runner(): ...
def test_testar_conta_grava_status(conta_factory): ...
def test_tipo_desconhecido(): ...
```

- [ ] **Step 2: Rodar e ver falhar.** Run: `uv run pytest tests/agentes -v`. Expected: FAIL.
- [ ] **Step 3: Implementar** os provedores, o registro, o modelo e os serviços.
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona contas de agente com provedores Cursor e Claude local (Plano 1 · Task 4)`.

---

### Task 5: API de contas de agente

**Files:**
- Create: `backend/apps/agentes/{serializers,views,urls}.py`, `backend/apps/donos/` (API de clientes: `serializers`, `views`, `urls`)
- Test: `backend/tests/agentes/test_api.py`

**Interfaces:**
- Consumes: Task 4.
- Produces:
  - `GET /api/tipos-de-agente/` → `[{tipo, nome, campos: [{chave, rotulo, secreto, ajuda, obrigatorio}], guia: [{texto, link}]}]`.
  - `GET|POST /api/contas-agente/`, `GET|PATCH|DELETE /api/contas-agente/{id}/`. Leitura: `{id, nome, tipo, cliente, config, limite_simultaneo, status, ultimo_teste_em, ultimo_teste_mensagem, tem_credenciais}`. Escrita: os mesmos campos editáveis mais `credenciais` (só de escrita; no PATCH, a ausência mantém o valor anterior).
  - `POST /api/contas-agente/testar/ {tipo, credenciais, config}` → `{ok, status, mensagem}`, sem gravar nada.
  - `POST /api/contas-agente/{id}/testar/` → `{ok, status, mensagem}`, gravando o status.
  - `GET|POST|PATCH|DELETE /api/clientes/`.

- [ ] **Step 1: Escrever os testes que falham:** `test_resposta_nunca_tem_credenciais` (procura a chave no corpo de todas as rotas, inclusive nos erros 400); `test_patch_sem_credenciais_mantem`; `test_testar_sem_salvar_nao_cria_registro`; `test_conta_de_outro_dono_da_404`; `test_conta_com_cliente_de_outro_dono_da_400`; `test_tipos_de_agente_lista_cursor_e_claude_local`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar** os serializers e as ViewSets com `EscopoDoDonoMixin`, chamando só `agentes.servicos`.
- [ ] **Step 4: Rodar e ver passar** e gerar o OpenAPI: `uv run python manage.py spectacular --file ../frontend/openapi.yaml`. Expected: PASS e arquivo gerado.
- [ ] **Step 5: Commit:** `feat: expõe a API de contas de agente e clientes (Plano 1 · Task 5)`.

---

### Task 6: Conexão com o GitHub (GitHub App criado pela central)

O Renato não cria o App à mão: a central usa o *manifest flow* do GitHub, em que um clique cria o App com as permissões e o webhook certos.

**Files:**
- Create: `backend/apps/plataformas/{__init__,apps,models,servicos,etiquetas}.py`, `backend/apps/plataformas/adaptadores/{__init__,base,github}.py`, `backend/apps/plataformas/{serializers,views,urls}.py`, migração
- Test: `backend/tests/plataformas/test_github.py`, `backend/tests/plataformas/test_github_api.py`

**Interfaces:**
- Consumes: `PertenceADono`, `CampoSecretoJSON`. Defina um `ResultadoTeste` próprio em `plataformas.adaptadores.base`, com os mesmos campos do de `agentes`, para `plataformas` não depender de `agentes`.
- Produces:

```python
@dataclass(frozen=True)
class Repositorio:
    id_externo: str; caminho: str; url_web: str      # caminho: "dono/repo" ou "grupo/sub/projeto"

@dataclass(frozen=True)
class ItemConferencia:
    chave: str; titulo: str; ok: bool; mensagem: str; consertavel: bool

class AdaptadorPlataforma(Protocol):
    def testar(self) -> ResultadoTeste: ...
    def listar_repositorios(self) -> list[Repositorio]: ...                       # todas as páginas
    def conferir(self, repo: Repositorio, url_webhook: str) -> list[ItemConferencia]: ...
    def preparar(self, repo: Repositorio, url_webhook: str) -> list[ItemConferencia]: ...  # idempotente

def obter_adaptador(conexao: ConexaoPlataforma) -> AdaptadorPlataforma
```

  - `ConexaoPlataforma(PertenceADono)`: `nome`, `tipo` (`github` | `gitlab`), `url_base: str` (vazio no GitHub), `credenciais: CampoSecretoJSON`, `config: JSONField`, `status`, `ultimo_teste_mensagem`.
  - `etiquetas.ETIQUETAS: list[Etiqueta(nome, cor, descricao)]`: `tarefa`, `em-andamento`, `em-revisao`, `correcao`, `precisa-humano`, `melhoria` (cores em hex sem `#`; descrições curtas em pt-BR).
  - `GitHubAdaptador.token_de_instalacao() -> str`: JWT RS256 (`iat = agora - 60`, `exp = agora + 540`, `iss = app_id`) → `POST /app/installations/{installation_id}/access_tokens`. O Plano 3 usa este método para entregar tokens de curta duração.
  - Credenciais do GitHub, vindas da conversão do manifesto: `app_id`, `slug`, `pem`, `webhook_secret`, `client_id`, `client_secret`; `config.installation_id`.
- Rotas:
  - `POST /api/conexoes-plataforma/github/manifesto/ {nome}` → `{acao: "https://github.com/settings/apps/new?state=<s>", manifesto: {...}}`. O `state` é assinado (`django.core.signing`, validade de 1 hora) e leva o id do dono. Manifesto: `name` = `"Fabrica " + nome` (o GitHub exige um nome único, então o front sugere um nome com sufixo), `url` = `FABRICA_URL_PUBLICA`, `hook_attributes.url` = `FABRICA_URL_PUBLICA + "/api/webhooks/github/"`, `redirect_url` = `.../api/conexoes-plataforma/github/retorno/`, `setup_url` = `.../api/conexoes-plataforma/github/instalado/`, `public: false`, `default_permissions` = `{contents: write, issues: write, pull_requests: write, metadata: read, checks: read, actions: read}`, `default_events` = `[issues, issue_comment, pull_request, pull_request_review, check_suite]`.
  - `GET /api/conexoes-plataforma/github/retorno/?code&state` → `POST https://api.github.com/app-manifests/{code}/conversions`, grava a conexão e redireciona (302) para `https://github.com/apps/{slug}/installations/new?state=<s>`.
  - `GET /api/conexoes-plataforma/github/instalado/?installation_id&state` → grava `config.installation_id` e redireciona para `/plataformas` no front.
  - `GET /api/conexoes-plataforma/`, `GET|DELETE /api/conexoes-plataforma/{id}/`, `POST /api/conexoes-plataforma/{id}/testar/`, `GET /api/conexoes-plataforma/{id}/repositorios/`.
- `conferir` (GitHub): `app_instalado_no_repo` (o repo está em `GET /installation/repositories`), `etiquetas` (todas as de `ETIQUETAS` existem), `webhook` (`GET /app/hook/config` com o JWT: a `url` bate com a esperada e `content_type` é `json`). `preparar`: cria as etiquetas que faltam (422 com `already_exists` conta como ok) e corrige `/app/hook/config` com `PATCH` se a URL estiver diferente. Instalação ausente não é consertável: a mensagem traz o link `https://github.com/apps/{slug}/installations/new`.

- [ ] **Step 1: Escrever os testes que falham** (todos com `respx`; a chave PEM de teste é gerada com `cryptography` na fixture): `test_manifesto_tem_webhook_e_permissoes`; `test_retorno_converte_e_grava_cifrado`; `test_retorno_com_state_invalido_da_400`; `test_instalado_grava_installation_id`; `test_token_de_instalacao_usa_jwt_rs256` (decodifica o JWT enviado com a chave pública da fixture e confere `iss`); `test_listar_repositorios_percorre_paginas` (header `Link` com `rel="next"`, 150 repositórios; Review Focus 4); `test_conferir_aponta_etiquetas_faltando`; `test_preparar_duas_vezes_nao_duplica` (o segundo POST de etiqueta responde 422 `already_exists`, e o resultado continua todo ok; Review Focus 2); `test_pem_mantem_quebras_internas`.
- [ ] **Step 2: Rodar e ver falhar.** Run: `uv run pytest tests/plataformas -v`. Expected: FAIL.
- [ ] **Step 3: Implementar** o modelo, o adaptador, o registro em `obter_adaptador` e as views.
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: conecta ao GitHub por App criado pela central (Plano 1 · Task 6)`.

---

### Task 7: Conexão com o GitLab (instância da Unilab)

**Files:**
- Create: `backend/apps/plataformas/adaptadores/gitlab.py`; a rota de criação em `views.py` e `urls.py`
- Test: `backend/tests/plataformas/test_gitlab.py`

**Interfaces:**
- Consumes: Task 6 (`AdaptadorPlataforma`, `ItemConferencia`, `Repositorio`, `ETIQUETAS`, `ConexaoPlataforma`).
- Produces:
  - `plataformas.servicos.normalizar_url_gitlab(texto: str) -> str`: devolve `https://host[/caminho]` sem barra no fim e sem `/api/v4`; sem esquema, assume `https://`. Exemplos que viram `https://gitlab.unilab.edu.br`: `gitlab.unilab.edu.br`, `https://gitlab.unilab.edu.br/`, `https://gitlab.unilab.edu.br/api/v4`.
  - `POST /api/conexoes-plataforma/gitlab/ {nome, url_base, token}`: limpa o token, testa e só grava se o teste passar; caso contrário, `400 {"detail": <mensagem do teste>}`. Gera `webhook_secret = secrets.token_urlsafe(32)` nas credenciais.
  - `testar`: `GET {url}/api/v4/personal_access_tokens/self` com `PRIVATE-TOKEN`. Exige `"api"` em `scopes`. Mensagens: sem `api` → `"O token precisa do escopo api. Crie outro marcando api."`; 401 → `"O GitLab recusou o token. Confira se ele não expirou."`; rede, DNS ou TLS → `"Não consegui acessar <url>. Confira o endereço e se a central alcança a rede da instância."`.
  - `listar_repositorios`: `GET /api/v4/projects?membership=true&min_access_level=40&per_page=100`, seguindo `X-Next-Page` (é preciso ser Maintainer para criar o webhook).
  - `conferir` e `preparar`: `etiquetas` (`GET`/`POST /projects/:id/labels`; 409 conta como ok) e `webhook` (`GET /projects/:id/hooks`, procurando a `url` esperada; cria com `token=webhook_secret`, `issues_events`, `merge_requests_events`, `note_events`, `pipeline_events`, `enable_ssl_verification=true`). O `:id` é o `id_externo` numérico.
  - URL do webhook do GitLab: `FABRICA_URL_PUBLICA + "/api/webhooks/gitlab/<conexao.id>/"`.

- [ ] **Step 1: Escrever os testes que falham:** `test_normalizar_url` (parametrizado com os três exemplos e mais `http://interno:8080/gitlab/`, que vira `http://interno:8080/gitlab`); `test_token_sem_escopo_api_explica`; `test_token_com_quebra_de_linha_e_limpo`; `test_instancia_fora_do_ar_mensagem_clara` (`httpx.ConnectError`; a resposta não tem traceback; Review Focus 3); `test_listar_segue_x_next_page` (Review Focus 4); `test_preparar_cria_webhook_com_segredo`; `test_preparar_duas_vezes_nao_duplica` (Review Focus 2); `test_criar_conexao_invalida_nao_grava`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: conecta ao GitLab self-hosted por token (Plano 1 · Task 7)`.

---

### Task 8: Projetos, conferir e preparar

**Files:**
- Create: `backend/apps/projetos/{__init__,apps,models,servicos,serializers,views,urls}.py`, migração
- Test: `backend/tests/projetos/test_servicos.py`, `backend/tests/projetos/test_api.py`

**Interfaces:**
- Consumes: `obter_adaptador`, `Repositorio`, `ItemConferencia` (Task 6), `Cliente` (Task 4), `Predefinicao` (Task 9; o FK entra aqui como `null=True` e a validação de contas, na Task 9).
- Produces:
  - `Projeto(PertenceADono)`: `nome`, `conexao: FK[ConexaoPlataforma]`, `repositorio_caminho`, `repositorio_id_externo`, `repositorio_url`, `cliente: FK[Cliente] | None`, `predefinicao: FK[Predefinicao] | None`, `ativo: bool = True`, `ultima_conferencia: JSONField(default=list)`, `ultima_conferencia_em`. Único por (`dono`, `conexao`, `repositorio_id_externo`).
  - `projetos.servicos.url_webhook(projeto) -> str`; `conferir_projeto(projeto) -> list[ItemConferencia]` e `preparar_projeto(projeto) -> list[ItemConferencia]`, que gravam o resultado em `ultima_conferencia`.
  - `POST /api/projetos/ {nome, conexao, repositorio_id_externo, cliente?, predefinicao?}`: busca o repositório na listagem do adaptador (`400` se não estiver acessível), cria o projeto e roda `preparar_projeto` na hora. A resposta traz `conferencia`.
  - `GET /api/projetos/`, `GET|PATCH|DELETE /api/projetos/{id}/`, `POST /api/projetos/{id}/conferir/`, `POST /api/projetos/{id}/preparar/` → `{itens: [ItemConferencia], conferido_em}`.

- [ ] **Step 1: Escrever os testes que falham** (com um adaptador falso registrado pelo teste): `test_criar_projeto_ja_prepara`; `test_conferir_grava_resultado`; `test_repositorio_inacessivel_da_400`; `test_projeto_de_outro_dono_da_404`; `test_conexao_de_outro_dono_da_400`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona projetos com conferir e preparar repositório (Plano 1 · Task 8)`.

---

### Task 9: Predefinições de fluxo (dados e validação)

Só a configuração. Quem executa as etapas é o Plano 3.

**Files:**
- Create: `backend/apps/fluxos/{__init__,apps,models,servicos,serializers,views,urls}.py`, migração
- Modify: `backend/apps/projetos/servicos.py` (validação de contas do projeto)
- Test: `backend/tests/fluxos/test_servicos.py`, `backend/tests/fluxos/test_api.py`

**Interfaces:**
- Consumes: `ContaAgente`, `Cliente`.
- Produces:
  - `fluxos.servicos.ETAPAS = ["publicar_tasks", "implementar", "revisar", "merge", "promover"]` (a ordem padrão) e `GATILHOS = ["anterior_concluida", "webhook", "temporizador", "decisao_humana"]`.
  - `Predefinicao(PertenceADono)`: `nome`, `descricao`, `etapas: JSONField` (lista de `{chave, papel: {"tipo": "conta", "conta_id": "<uuid>"} | {"tipo": "humano"} | {"tipo": "central"}, gatilho, temporizador_minutos?}`), `merge_autonomo: bool = True`.
  - `fluxos.servicos.validar_etapas(dono, etapas) -> list[str]` (erros em pt-BR). Regras: chaves conhecidas e sem repetição; `implementar` e `revisar` exigem `papel.tipo == "conta"` com uma conta do mesmo dono; `promover` exige `"humano"`; `publicar_tasks` e `merge` usam `"central"`; `temporizador` exige `temporizador_minutos >= 1`.
  - `fluxos.servicos.criar_padrao(dono, executor: ContaAgente, revisor: ContaAgente) -> Predefinicao`: o "Padrão" da spec (4.3), com as cinco etapas na ordem, `implementar` → executor, `revisar` → revisor, gatilho `anterior_concluida`, `promover` com `decisao_humana` e `merge_autonomo=True`.
  - `fluxos.servicos.duplicar(predefinicao, nome) -> Predefinicao`.
  - `projetos.servicos.validar_contas_do_projeto(projeto, predefinicao) -> list[str]`: toda conta usada precisa ter `conta.cliente` em (`None`, `projeto.cliente`); senão `"A conta <nome> é do cliente <X> e não pode trabalhar neste projeto."`. É chamada no `POST`/`PATCH` de projeto e no `PATCH` de predefinição (para cada projeto que a usa).
  - API: `GET|POST /api/predefinicoes/`, `GET|PATCH|DELETE /api/predefinicoes/{id}/`, `POST /api/predefinicoes/padrao/ {executor, revisor}`, `POST /api/predefinicoes/{id}/duplicar/ {nome}`, `GET /api/etapas-e-gatilhos/` (os rótulos em pt-BR para o front). Apagar uma predefinição em uso dá `400 "Esta predefinição é usada por N projeto(s)."`.

- [ ] **Step 1: Escrever os testes que falham:** `test_padrao_tem_as_cinco_etapas_na_ordem`; `test_implementar_sem_conta_da_erro`; `test_conta_de_outro_dono_da_erro`; `test_promover_exige_humano`; `test_temporizador_sem_minutos_da_erro`; `test_duplicar_copia_etapas`; `test_conta_de_cliente_y_em_projeto_do_cliente_x_e_recusada`; `test_conta_do_dono_vale_em_projeto_de_cliente`; `test_patch_da_predefinicao_valida_projetos_que_usam`; `test_apagar_em_uso_da_400`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona predefinições de fluxo com validação (Plano 1 · Task 9)`.

---

### Task 10: Recebimento de webhooks

Só recebe, verifica e guarda. Quem processa é o Plano 3.

**Files:**
- Create: `backend/apps/plataformas/webhooks.py` (views), o modelo `EventoRecebido` e a migração
- Test: `backend/tests/plataformas/test_webhooks.py`

**Interfaces:**
- Consumes: `ConexaoPlataforma`.
- Produces:
  - `EventoRecebido(PertenceADono)`: `conexao: FK`, `tipo_evento: str`, `entrega_id: str` (único por `conexao`), `payload: JSONField`, `recebido_em`, `processado_em: datetime | None`.
  - `POST /api/webhooks/github/` (sem login nem CSRF): acha a conexão por `payload.installation.id == config.installation_id`; valida `X-Hub-Signature-256` (HMAC-SHA256 com `webhook_secret`, comparação em tempo constante); usa `X-GitHub-Event` e `X-GitHub-Delivery`. O evento `installation` com `action=created` sem conexão casada é aceito e ignorado (202), porque o `instalado/` da Task 6 grava o id.
  - `POST /api/webhooks/gitlab/<uuid:conexao_id>/`: valida `X-Gitlab-Token` contra o `webhook_secret` (tempo constante); usa `X-Gitlab-Event` e `X-Gitlab-Event-UUID`.
  - Respostas: válido e novo → `202`; reentrega (mesmo `entrega_id`) → `200` sem gravar de novo; assinatura inválida ou conexão desconhecida → `401`/`404` sem gravar (Review Focus 5).

- [ ] **Step 1: Escrever os testes que falham:** `test_github_assinatura_valida_grava`; `test_github_assinatura_invalida_nao_grava`; `test_github_reentrega_nao_duplica`; `test_github_instalacao_desconhecida_404`; `test_gitlab_token_valido_grava`; `test_gitlab_token_errado_401`; `test_gitlab_reentrega_nao_duplica`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: recebe e guarda webhooks do GitHub e do GitLab (Plano 1 · Task 10)`.

> Nota: a ordem das Tasks 8, 9 e 10 pode ser 9 → 8 → 10 se o executor preferir criar o FK de `Projeto.predefinicao` já com o modelo existente. O resultado final é o mesmo.

---

### Task 11: Base do front-end e login

**Files:**
- Create: `frontend/` com Vite (React + TS), Mantine 9, TanStack Query 5, react-router 7, openapi-fetch, openapi-typescript (script `gerar-api` igual ao do top-tenis), Vitest + Testing Library + MSW, oxlint; `frontend/.nvmrc` (`22`); `frontend/src/api/cliente.ts` (openapi-fetch com `credentials: "include"` e o cabeçalho `X-CSRFToken` lido do cookie); `frontend/src/tema/{tokens.ts,tema.ts}`; `frontend/src/app/{App.tsx,rotas.tsx,Layout.tsx}`; `frontend/src/sessao/{TelaLogin.tsx,useSessao.ts,RotaProtegida.tsx}`; proxy do Vite `/api` → `http://localhost:8000`
- Modify: `automacao/verificar.sh` (`npm run lint`, `npx tsc -b`, `npx vitest run`)
- Test: `frontend/src/sessao/TelaLogin.test.tsx`, `frontend/src/sessao/RotaProtegida.test.tsx`

**Interfaces:**
- Consumes: `/api/sessao/` (Task 2), `frontend/openapi.yaml` (Task 5 em diante).
- Produces: `Layout` com navegação para `Contas de agente` (`/contas`), `Plataformas e projetos` (`/plataformas`), `Predefinições` (`/predefinicoes`); `useSessao(): {sessao, entrar(usuario, senha), sair()}`; `RotaProtegida` redireciona para `/entrar` sem sessão.

- [ ] **Step 1: Escrever os testes que falham:** `entra e vai para /contas` (MSW responde 200 no POST de sessão); `mostra "Usuário ou senha incorretos."` com o 400; `sem sessão, /contas redireciona para /entrar`.
- [ ] **Step 2: Rodar e ver falhar.** Run: `cd frontend && npx vitest run`. Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Run: `npx vitest run && npm run lint && npx tsc -b`. Expected: tudo PASS.
- [ ] **Step 5: Commit:** `feat: cria o front-end com login (Plano 1 · Task 11)`.

---

### Task 12: Tela de contas de agente (cadastro guiado)

**Files:**
- Create: `frontend/src/contas/{TelaContas.tsx,AssistenteConta.tsx,CartaoConta.tsx,api.ts}`
- Test: `frontend/src/contas/AssistenteConta.test.tsx`, `frontend/src/contas/TelaContas.test.tsx`

**Interfaces:**
- Consumes: `/api/tipos-de-agente/`, `/api/contas-agente/` (incluindo `testar/`), `/api/clientes/`.
- Produces: a rota `/contas`.
- Comportamento:
  - A lista mostra cada conta com o nome, o tipo, o cliente (ou "Sua"), um selo de status (`ok`, `falha`, `aguardando runner`, `não testada`) e a última mensagem de teste. Ações: Testar de novo, Editar e Excluir (com confirmação).
  - Assistente "Nova conta", em três passos: (1) escolher o tipo; (2) seguir o guia do tipo (os passos com os links abrindo em nova aba) e preencher os campos (os secretos com `PasswordInput`), mais o nome, o cliente e o limite simultâneo; (3) "Testar conexão", que mostra a mensagem do servidor. **Salvar só fica habilitado depois de um teste com `ok`**, exceto no tipo com `status = aguardando_runner`, que pode ser salvo com o aviso.
  - Na edição, os campos secretos ficam vazios com o texto "Deixe em branco para manter a credencial salva."

- [ ] **Step 1: Escrever os testes que falham:** `salvar fica desabilitado até o teste dar ok`; `mostra a mensagem de chave recusada`; `claude local salva com o aviso de runner`; `edição não pré-preenche o segredo`; `a lista mostra o selo de status`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona o cadastro guiado de contas de agente (Plano 1 · Task 12)`.

---

### Task 13: Tela de plataformas e projetos

**Files:**
- Create: `frontend/src/plataformas/{TelaPlataformas.tsx,ConectarGitHub.tsx,ConectarGitLab.tsx,NovoProjeto.tsx,Conferencia.tsx,api.ts}`
- Test: `frontend/src/plataformas/*.test.tsx`

**Interfaces:**
- Consumes: Tasks 6 a 9 (rotas de conexões, projetos e predefinições).
- Produces: a rota `/plataformas`.
- Comportamento:
  - "Conectar GitHub": pede um nome, chama `manifesto/` e envia um `<form method="post" action={acao}>` com um campo oculto `manifest` (JSON). Ao voltar do GitHub, a lista mostra a conexão; se faltar a instalação, mostra o botão "Instalar no GitHub".
  - "Conectar GitLab": a URL da instância, o token e o guia (onde criar o token, marcando o escopo `api` e com o papel de Maintainer nos projetos). Mostra a mensagem de erro do servidor sem apagar o que foi digitado.
  - "Novo projeto": escolher a conexão, o repositório (lista com busca), o cliente opcional e a predefinição opcional. Ao criar, mostra a conferência.
  - `Conferencia`: um item por linha, com ✓ ou ✗, o título e a mensagem; "Conferir" refaz; "Consertar" chama `preparar/` quando algum item com falha é consertável.

- [ ] **Step 1: Escrever os testes que falham:** `conectar GitHub envia o manifesto para a URL de ação`; `erro do GitLab preserva o formulário`; `novo projeto mostra a conferência`; `consertar só aparece com item consertável em falha`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona a tela de plataformas e projetos (Plano 1 · Task 13)`.

---

### Task 14: Tela de predefinições

**Files:**
- Create: `frontend/src/predefinicoes/{TelaPredefinicoes.tsx,EditorPredefinicao.tsx,api.ts}`
- Test: `frontend/src/predefinicoes/EditorPredefinicao.test.tsx`

**Interfaces:**
- Consumes: Task 9.
- Produces: a rota `/predefinicoes`.
- Comportamento:
  - A lista mostra as predefinições e quantos projetos usam cada uma.
  - "Criar a partir do Padrão" pede o executor e o revisor (selects com as contas).
  - O editor mostra as etapas na ordem, cada uma com o rótulo, o papel (conta, humano ou central, conforme a regra da etapa) e o gatilho (com os minutos quando for `temporizador`), e a chave "Merge autônomo / com ok humano". Dá para ativar e desativar etapas e reordená-las com botões subir e descer.
  - Os erros de validação do servidor aparecem junto da etapa. Ao salvar uma predefinição em uso, o aviso diz "Vale na hora para N projeto(s), a partir da próxima etapa de cada um."
  - Botão Duplicar.

- [ ] **Step 1: Escrever os testes que falham:** `criar a partir do padrão pede executor e revisor`; `promover só oferece humano`; `mostra o aviso de N projetos ao salvar`; `erro do servidor aparece na etapa`.
- [ ] **Step 2: Rodar e ver falhar.** Expected: FAIL.
- [ ] **Step 3: Implementar.**
- [ ] **Step 4: Rodar e ver passar.** Expected: PASS.
- [ ] **Step 5: Commit:** `feat: adiciona o editor de predefinições (Plano 1 · Task 14)`.

---

### Task 15: Empacotamento para rodar como na VPS

Prepara, mas **não faz deploy** (o deploy depende do ok do Renato, no Plano 5).

**Files:**
- Create: `backend/Dockerfile` (uv, gunicorn, `collectstatic`, `migrate` na entrada), `frontend/Dockerfile` (build) e `Caddyfile` (serve o `dist`, faz proxy de `/api` e `/admin` para o back-end, e expõe `/api/webhooks/*` sem cache), `docker-compose.yml` (db, backend, caddy; volumes do Postgres e do Caddy), seção "Rodar como em produção" no `README.md`
- Test: `automacao/fumaca.sh` (sobe o compose com um `.env` de teste, espera `GET /api/saude/` dar 200 pelo Caddy e derruba)

- [ ] **Step 1: Escrever `automacao/fumaca.sh`** (sai com código ≠ 0 se a saúde não responder em 60 s).
- [ ] **Step 2: Rodar e ver falhar.** Run: `automacao/fumaca.sh`. Expected: FAIL (sem Dockerfiles).
- [ ] **Step 3: Implementar** os Dockerfiles, o compose e o Caddyfile.
- [ ] **Step 4: Rodar e ver passar.** Run: `automacao/fumaca.sh`. Expected: `saúde ok` e código 0.
- [ ] **Step 5: Commit:** `chore: empacota a central em Docker Compose com Caddy (Plano 1 · Task 15)`.

---

## Aceite do plano

- `automacao/verificar.sh` verde.
- `automacao/fumaca.sh` verde.
- Manual, contra contas reais (o Renato): cadastrar uma conta do Cursor e ver "Conectado como …"; conectar o GitHub pelo botão e instalar o App num repositório de teste; conectar o GitLab da Unilab e ver o teste passar (isso responde aos riscos 1 a 3 da spec); criar um projeto de cada plataforma e ver a conferência toda ✓; criar o Padrão e associar a um projeto.
