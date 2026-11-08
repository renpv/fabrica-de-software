# Task 8 - Projetos, conferir e preparar

## Implementado
- `apps/projetos` (models, servicos, serializers, views, urls, migração 0001), registrado em settings e urls.
- `Projeto(PertenceADono)` sem `predefinicao` (entra na Task 9); único por (dono, conexao, repositorio_id_externo).
  `conexao` é PROTECT; `cliente` é SET_NULL.
- Serviços: `etiquetas_do_projeto`, `url_webhook`, `conferir_projeto`, `preparar_projeto`, `criar_projeto`, `excluir_projeto`.
- API: `/api/projetos/` (GET, POST), `/{id}/` (GET, PATCH de nome/cliente/ativo, DELETE), `/{id}/conferir/`, `/{id}/preparar/`.
- plataformas: novos `url_webhook(conexao)` e `url_webhook_github()` públicos em `servicos.py` (projetos reutiliza); DELETE de conexão com projetos devolve 409 em pt-BR (antes seria ProtectedError/500).
- `.importlinter`: contrato `projetos` (proíbe saude) e `apps.projetos` nas listas proibidas de donos, saude, cofre, agentes e plataformas.

## Decisões
- `caminho` validado com `^[\w.-]+(/[\w.-]+)+$` ao criar (vem só da listagem do adaptador) e de novo antes de cada conferir/preparar.
- Erros: pedido recusado (repo fora da listagem, conexão/cliente de outro dono, duplicado) = 400; `ErroDePlataforma` = 502 (padrão das views de plataformas).
- Falha no `preparar` logo após criar: o projeto fica (busca+gravação são uma transação), resposta 201 com `erro_ao_preparar` preenchido e `conferencia` vazia; a pessoa usa `POST /preparar/`. `erro_ao_preparar` não é coluna: atributo transitório.
- `conexao`/`cliente` de outro dono: 400 via queryset do serializer limitado ao dono (e checagem no serviço).
- `predefinicao` no corpo é ignorada.
- Arquivos de teste renomeados para `test_projetos_api.py` e `test_projetos_servicos.py`: os nomes do brief colidem com `tests/agentes/test_api.py` (sem `__init__.py`, o pytest falha na coleta).

## TDD
- RED: `uv run pytest tests/projetos -q` -> `ModuleNotFoundError: No module named 'apps.projetos'` (2 erros de coleta).
- GREEN: `23 passed`. Depois `automacao/verificar.sh`: ruff, lint-imports, migrações, `231 passed`.

## Arquivos
backend/apps/projetos/*, backend/tests/projetos/{conftest,test_projetos_api,test_projetos_servicos}.py, backend/.importlinter, backend/config/{settings,urls}.py, backend/apps/plataformas/{servicos,views}.py.

## Concerns
- Adaptador falso registrado em `REGISTRO["gitlab"]` por monkeypatch; GitHub não coberto aqui (só o helper de URL).
- A URL do webhook do GitHub (`/api/webhooks/github/`) ainda está também embutida em `github.montar_manifesto`; não foi unificada para não mexer no adaptador.
- A rota de recebimento de webhooks ainda não existe (tasks futuras).

## Correção (revisão)
- `criar_projeto`: a listagem (rede) saiu da transação; o `.exists()` foi removido e a unicidade fica com o banco: `create` num savepoint, `IntegrityError` vira `ErroDeProjeto(MSG_DUPLICADO)` (400).
- Testes novos: corrida simulada (duplicata criada entre listagem e gravação) no serviço e na API; PATCH com cliente de outro dono (400, nada muda); PATCH define e limpa cliente próprio.
- `extend_schema` de `conferir`/`preparar` ganhou 400 `ErroSerializer`.
- `automacao/verificar.sh` passou.
