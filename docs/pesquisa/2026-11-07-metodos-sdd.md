# Métodos de desenvolvimento guiado por spec: Spec Kit, OpenSpec e superpowers

Data de acesso: 2026-11-07. Pesquisa em repositórios oficiais no GitHub (via `gh api` e `raw.githubusercontent.com`, branch `main`) e, para o superpowers, também nos SKILL.md da versão instalada localmente (7.0.0).

Versões consultadas (última release de cada repositório na data de acesso) [F1][F2][F3]:

| Método | Última release | Instalada localmente | Licença |
|---|---|---|---|
| Spec Kit | v1.3.2 (2026-11-06) | não instalado | MIT |
| OpenSpec | v1.16.1 (2026-11-07) | não instalado | MIT |
| superpowers | v7.0.2 (2026-11-03) | 7.0.0 (lida em disco) | MIT |

## Resumo prático

- Os três têm o mesmo esqueleto: ideia -> especificação -> plano -> tasks -> implementação -> fechamento. Só mudam nomes, pastas e o grau de automação.
- Para um orquestrador externo, o OpenSpec é o mais fácil: tem CLI com saída JSON (`openspec list --json`, `openspec status --json`, `openspec instructions apply --json`) que diz se o plano está pronto e quais tasks estão feitas, com `id`, `description`, `done`. Existe até um "contrato para agentes" documentado [F4][F5].
- No Spec Kit não há CLI que liste tasks. O orquestrador teria de ler `specs/<feature>/tasks.md` e contar `- [ ]` contra `- [X]`. O estado "ativo" fica em `.specify/feature.json` [F6][F7].
- No superpowers, o plano é um `.md` em `docs/superpowers/plans/` com checkboxes nos passos. O progresso real fica num "ledger" git-ignorado (`.superpowers/sdd/<plano>/progress.md`) com linhas `Task <N>: complete ...`. Não há marca de "plano aprovado" legível por máquina: a aprovação é uma conversa com o usuário [F8][F9].
- Nenhum dos três tem um marcador oficial de "plano aprovado". Para a fábrica, a aprovação teria de ser convenção própria (ex.: etiqueta ou issue no GitHub). Isso é uma conclusão minha, não algo dos projetos.

## Tabela comparativa (método x etapa -> comando e artefato)

| Etapa | Spec Kit | OpenSpec | superpowers |
|---|---|---|---|
| Princípios do projeto | `/speckit-constitution` -> `.specify/memory/constitution.md` (caminho do arquivo: ver nota 1) | `openspec/config.yaml` (campo `context:`), sem comando próprio [F5] | não tem |
| Explorar/ideia | extensão `assess` (`/speckit-assess-intake` etc.) -> `.specify/assessments/<slug>/` [F6] | `/opsx:explore` (sem artefato) [F4] | `brainstorming` (skill) |
| Spec | `/speckit-specify` -> `specs/NNN-nome/spec.md` [F7] | `/opsx:propose <nome>` cria `openspec/changes/<nome>/proposal.md` e `specs/` (deltas) [F4][F5] | `brainstorming` -> `docs/superpowers/specs/AAAA-MM-DD-<tema>-design.md` [F8] |
| Esclarecer | `/speckit-clarify` (grava de volta no `spec.md`) | não tem comando separado (no perfil expandido: `/opsx:continue`) | perguntas dentro do `brainstorming` |
| Plano/design | `/speckit-plan` -> `specs/NNN-nome/plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` [F10] | `design.md` na pasta da change (gerado no `propose`) [F5] | `writing-plans` -> `docs/superpowers/plans/AAAA-MM-DD-<feature>.md` [F8] |
| Tasks | `/speckit-tasks` -> `specs/NNN-nome/tasks.md` | `tasks.md` na pasta da change (gerado no `propose`) | dentro do próprio plano (`### Task N:`) |
| Checagem de consistência | `/speckit-checklist`, `/speckit-analyze` (somente leitura) | `/opsx:verify` (perfil expandido) | `requesting-code-review` (revisão por task e no fim) |
| Implementar | `/speckit-implement` | `/opsx:apply` | `subagent-driven-development` (recomendada) ou `executing-plans` |
| Verificar o resultado | `/speckit-converge` (acrescenta tasks se faltar algo) | `/opsx:verify` | revisão final do branch inteiro |
| Fechar/arquivar | não tem etapa de arquivamento (a pasta `specs/NNN-nome/` fica) | `/opsx:archive` -> `openspec/changes/archive/AAAA-MM-DD-<nome>/` e atualiza `openspec/specs/` | `finishing-a-development-branch` (merge local, PR, manter ou descartar) |

Nota 1: o caminho exato do arquivo da constitution não foi confirmado em texto; o README só cita `.specify/memory` na árvore. Marcar como "não confirmado".

Os comandos do Spec Kit aparecem como `/speckit-specify` (skills) na documentação atual e como `/speckit.specify` (notação "pontilhada") em parte da documentação e no Gemini. A grafia depende do agente (ver abaixo) [F11].

---

## 1. GitHub Spec Kit (github/spec-kit)

### Etapas e comandos [F6][F7][F12]

Caminho curto: `/speckit-specify` -> `/speckit-plan` -> `/speckit-tasks` -> `/speckit-implement` -> `/speckit-converge`.

Caminho completo, com portões de qualidade: `/speckit-constitution` (uma vez por projeto) -> `/speckit-specify` -> `/speckit-clarify` -> `/speckit-plan` -> `/speckit-checklist` -> `/speckit-tasks` -> `/speckit-analyze` -> `/speckit-implement` -> `/speckit-converge`.

Só o `specify` é obrigatório antes do `plan`. Há também extensões: `bug` (`/speckit-bug-assess`, `/speckit-bug-fix`, `/speckit-bug-test`) e `assess` (`/speckit-assess-intake`, `-research`, `-define`, `-shape`, `-decide`) [F6].

### Artefatos [F6][F7][F10]

- Spec: `specs/NNN-nome-da-feature/spec.md` (diretório padrão `specs/`; pode ser mudado com a variável `SPECIFY_FEATURE_DIRECTORY`). O prefixo é sequencial de 3 dígitos por padrão.
- Plano: `specs/NNN-nome/plan.md`, mais `research.md`, `data-model.md`, `contracts/`, `quickstart.md` (exemplo do `spec-driven.md`).
- Tasks: `specs/NNN-nome/tasks.md`.
- Checklists: `specs/NNN-nome/checklists/requirements.md` (feito pelo specify/clarify) e checklists próprios de revisão.
- Feature ativa: `.specify/feature.json` (não depende do branch do git).
- Bug e avaliação: `.specify/bugs/<slug>/`, `.specify/assessments/<slug>/` (com `decision.md`).
- Arquivamento: não encontrado (não há etapa de arquivar).

### Formato das tasks [F13]

Linha de checkbox com ID: `- [ ] T001 [P] [US1] Descrição com caminho do arquivo`. `[P]` = pode rodar em paralelo; `[US1]` = história de usuário. O `/speckit-implement` marca `[X]` nas tasks concluídas. As tasks são agrupadas em fases: Setup, Foundational, uma fase por história de usuário e Polish. O `converge` acrescenta tasks novas numa seção "Convergence" do mesmo arquivo.

### Agentes suportados e instalação [F11][F14]

Instalação do CLI: `uv tool install specify-cli` (requer Python 3.11+ e uv); depois `specify init <projeto> --integration <chave>`. Em projeto existente: `specify integration install <chave>`. Há `--integration none` para equipes com agentes mistos.

A lista oficial tem 40+ integrações. Chaves relevantes e onde instalam:

| Agente | Chave | Onde instala | Como chamar |
|---|---|---|---|
| Claude Code | `claude` | `.claude/skills/speckit-<cmd>/SKILL.md` | `/speckit-specify` |
| Cursor | `cursor-agent` | `.cursor/skills/speckit-<cmd>/SKILL.md` | `/speckit-specify` |
| Codex CLI | `codex` | `.agents/skills/speckit-<cmd>/SKILL.md` | `$speckit-specify` |
| Gemini CLI | `gemini` | `.gemini/commands/speckit.<cmd>.toml` | `/speckit.specify` |
| Antigravity (agy) | `agy` | `.agents/skills/speckit-<cmd>/SKILL.md` | `/speckit-specify` |
| GitHub Copilot | `copilot` | (ver guia do Copilot) | `/speckit-specify` |

Outros da lista: Amp, Auggie, Cline, Devin, Factory Droid, Goose, Kimi, Kiro, opencode, Qwen, Trae, Zed, genérico (traga o seu). Lista completa na página de integrações [F11].

### Como um orquestrador externo saberia

- Plano pronto: existência de `specs/NNN/plan.md` e `tasks.md`. Não há campo "aprovado". O `/speckit-analyze` é só um relatório de leitura; o `checklist` é "de revisor" (`[x]` só pelo revisor) [F12].
- Task pendente/concluída: contar `- [ ]` e `- [X]` em `tasks.md`. Não encontrei CLI nem saída JSON que liste tasks.
- Feature ativa: `.specify/feature.json`.
- Existe um recurso de workflows e um servidor MCP no código (`src/specify_cli/workflows`, `mcp_server`), mas não li o suficiente para afirmar o que expõem: não confirmado.

### Licença e telemetria

MIT [F1]. Telemetria: não encontrei menção a telemetria nem no README nem na documentação de instalação; as únicas ocorrências da palavra no código são comentários sobre "handlers" de eventos. Marcar como "não encontrada em documentação" (não equivale a prova de que não existe).

---

## 2. OpenSpec (Fission-AI/OpenSpec)

### Etapas e comandos [F4][F15]

Perfil padrão (`core`): `/opsx:explore` -> `/opsx:propose <nome>` -> `/opsx:apply` -> `/opsx:archive`. O perfil também inclui `update` e `sync`.

Perfil expandido (ligar com `openspec config profile`, depois `openspec update`): `/opsx:new`, `/opsx:continue`, `/opsx:ff` (avançar rápido), `/opsx:verify`, `/opsx:bulk-archive`, `/opsx:onboard`.

A grafia muda por agente: `/opsx:propose` (Claude Code, Gemini, entre outros), `/opsx-propose` (Cursor e a maioria), `$openspec-propose` (Codex, só skills), `/openspec-<skill>` (agentes só com skills), `@opsx-propose` (Amazon Q) [F15].

### Artefatos [F5][F16]

```
openspec/
  config.yaml
  specs/                      # specs "vivas" (fonte de verdade)
  changes/
    <nome>/
      proposal.md             # por que e o que muda
      design.md               # abordagem técnica
      tasks.md                # checklist de implementação
      .openspec.yaml          # metadados (schema, skip_specs, ...)
      specs/                  # specs "delta" (ADDED/MODIFIED/REMOVED Requirements)
    archive/
      AAAA-MM-DD-<nome>/      # change arquivada
```

Ao arquivar, os deltas são mesclados em `openspec/specs/`. O formato de spec usa `### Requirement: <nome>` e `#### Scenario:` com WHEN/THEN. A ordem dos artefatos é definida por um schema (`proposal` -> `specs` -> `design` -> `tasks`; dá para criar schemas próprios).

### Formato das tasks [F16]

`tasks.md` com checkbox e ID numerado por grupo: `- [ ] 1.1 Criar ThemeContext`, `- [ ] 2.3 ...`. O `/opsx:apply` marca `[x]`. O estado é guardado nesses checkboxes.

### Agentes suportados e instalação [F15][F17]

Mais de 30 ferramentas. Instalação do CLI: `npm install -g @fission-ai/openspec@latest` (Node 22.12 ou mais novo), ou `brew install openspec`, ou script `curl -fsSL https://openspec.dev/cli/install.sh | sh`. Depois `openspec init` e escolher as ferramentas; `openspec update` atualiza os arquivos gerados.

| Agente | Id | Skills | Comandos |
|---|---|---|---|
| Claude Code | `claude` | `.claude/skills/openspec-*/SKILL.md` | `.claude/commands/opsx/<id>.md` |
| Cursor | `cursor` | `.cursor/skills/openspec-*/SKILL.md` | `.cursor/commands/opsx-<id>.md` |
| Codex | `codex` | `.agents/skills/openspec-*/SKILL.md` | não gera (só skills; `$openspec-*`) |
| Gemini CLI | `gemini` | `.gemini/skills/openspec-*/SKILL.md` | `.gemini/commands/opsx/<id>.toml` |
| Antigravity | `antigravity` | `.agent/skills/openspec-*/SKILL.md` | `.agent/workflows/opsx-<id>.md` |

### Como um orquestrador externo saberia (ponto forte)

O "contrato para agentes" documenta saídas JSON, uma por chamada [F5]:

- `openspec list --json`: cada change vem com `name`, `completedTasks`, `totalTasks`, `status` (`no-tasks`, `in-progress` ou `complete`).
- `openspec status --json --change <nome>`: lista os artefatos com `status` (`done`, `ready`, `blocked`, `skipped`) e `isPlanningComplete` (todos os artefatos de planejamento existem). Atenção: isso significa "planejamento escrito", não "aprovado" nem "implementado".
- `openspec instructions apply --json`: `state` (`blocked`, `ready`, `all_done`), `progress` {total, complete, remaining} e `tasks: [{id, description, done}]`.
- `openspec validate --all --json` e `openspec archive <nome> --json` (não interativo; devolve `archivedAs`).
- Código de saída 0 em sucesso e 1 em falha, com envelope de diagnóstico.
- Não há campo de "aprovação humana" no schema padrão: `isPlanningComplete` só diz que os arquivos existem. Aprovação seria convenção externa.

### Licença e telemetria [F17]

MIT. Telemetria ligada por padrão: coleta só nome do comando e versão (sem argumentos, caminhos ou conteúdo); desligada automaticamente em CI. Desativar com `openspec config set telemetry.enabled false`, `OPENSPEC_TELEMETRY=0` ou `DO_NOT_TRACK=1`.

---

## 3. superpowers (obra/superpowers)

Fonte: README do repositório [F3] e os SKILL.md instalados em `/home/renpv/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills` [F8][F9]. A release atual do repositório (7.0.2) é mais nova que a instalada (7.0.0); não comparei o conteúdo das duas.

### Etapas e skills [F3][F8]

Não são comandos fixos: são skills que o agente aciona sozinho pela descrição (o nome completo é `superpowers:<skill>`).

1. `brainstorming`: pergunta antes de construir, escreve o design, faz uma "checagem de construtor" com subagente e trava (HARD-GATE) até o usuário aprovar. Para software, o passo seguinte é só `writing-plans`.
2. `using-git-worktrees`: cria workspace isolado (não implementa na main sem consentimento).
3. `writing-plans`: escreve o plano; depois pergunta ao usuário qual execução usar.
4. `subagent-driven-development` (recomendada: um implementador novo por task, revisão por task e revisão final do branch) ou `executing-plans` (o próprio agente faz tudo e há uma revisão no fim). Os dois compartilham o mesmo ledger e podem trocar de executor no meio.
5. `test-driven-development` e `requesting-code-review` ao longo da execução.
6. `finishing-a-development-branch`: verifica testes, detecta o ambiente e oferece: (1) merge local, (2) push e PR, (3) manter como está, (4) descartar sob pedido. Depois limpa o workspace.

### Artefatos [F8][F9]

- Spec/design: `docs/superpowers/specs/AAAA-MM-DD-<tema>-design.md`, versionado no git.
- Plano: `docs/superpowers/plans/AAAA-MM-DD-<feature>.md`, versionado.
- Workspace de execução (git-ignorado): `<raiz-do-repo>/.superpowers/sdd/<nome-do-plano>/`, com `progress.md` (o ledger), briefs, relatórios e pacotes de revisão. O script `scripts/sdd-workspace PLAN_FILE` imprime o caminho.
- Arquivamento: não encontrado (não há etapa de arquivar; o `finishing-a-development-branch` cuida do branch).

### Formato das tasks [F8][F9]

No plano: cabeçalho `### Task N: [Componente]` e, dentro, passos com checkbox `- [ ] **Step 1: ...**` (escrever teste que falha, rodar, implementar, rodar, commit). O cabeçalho do plano traz a instrução para o agente usar `subagent-driven-development` ou `executing-plans`. Na minha leitura dos SKILL.md, o checkbox do plano não é descrito como o registro oficial de progresso. O registro oficial é o ledger: a primeira linha é `# SDD ledger — plan: <caminho do plano>` e cada task concluída ganha uma linha `Task <N>: complete (commits <base7>..<head7>, review clean)` (ou `tests: <comando> -> <resultado>` no `executing-plans`). Também há linhas `Ruling: <decisão> — <motivo> — <custo se errada>`. Em caso de perda de contexto, a regra é confiar no ledger e no `git log`.

### Agentes suportados e instalação [F3]

| Agente | Instalação (README) |
|---|---|
| Claude Code | `/plugin install superpowers@claude-plugins-official` |
| Antigravity | `agy plugin install https://github.com/obra/superpowers` |
| Cursor | `/add-plugin superpowers` no chat do agente |
| Codex CLI | `/plugins`, buscar "superpowers" e instalar (no app: barra lateral de Plugins) |
| Gemini CLI | `gemini extensions install https://github.com/obra/superpowers` |

O README lista ainda: Devin CLI, Factory Droid, GitHub Copilot CLI, Grok Build CLI, Kimi Code, OpenCode, Pi, Qwen Code, Hermes Agent e Muse. Cada um tem comando próprio no README [F3].

### Como um orquestrador externo saberia

- Plano pronto: existência de `docs/superpowers/plans/*.md`. Aprovação: só por conversa com o usuário (o `writing-plans` pede "revise o plano" e espera). Nada legível por máquina.
- Task concluída: linhas `Task <N>: complete` no ledger `.superpowers/sdd/<plano>/progress.md`, e os commits citados no git. O ledger é local e git-ignorado, então um orquestrador em outra máquina não o vê; só os commits e o PR ficam visíveis.
- Observação relevante: o `subagent-driven-development` manda não parar entre tasks nem perguntar ao usuário ("rulings, not stalls"); decide sozinho e registra no ledger.

### Licença e telemetria [F3]

MIT. Telemetria mínima e opcional: o logo da Prime Radiant no "visual companion" do brainstorming é carregado do site do projeto e inclui a versão do superpowers (sem dados de projeto, prompt ou agente). Desativar com `SUPERPOWERS_DISABLE_TELEMETRY` (também respeita `DISABLE_TELEMETRY` e `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`).

---

## Perguntas em aberto

1. Spec Kit: caminho exato do arquivo da constitution (`.specify/memory/constitution.md`?) não confirmado em texto; o que `src/specify_cli/workflows` e `mcp_server` expõem para automação não foi lido.
2. Spec Kit: telemetria não encontrada, mas não li o código inteiro.
3. OpenSpec: o conteúdo exato de `proposal.md`/`design.md` no schema padrão e se o `apply` aceita rodar sem aprovação humana não foram lidos em detalhe; o comando `/opsx:propose` gera todos os artefatos de uma vez (segundo o README), a ordem fina depende do schema.
4. superpowers: comparar o 7.0.2 (atual) com o 7.0.0 instalado (pode haver mudança nas skills); o formato do checkbox do plano como registro de progresso não é confirmado nos SKILL.md.
5. Nenhum dos três tem um marcador oficial de "plano aprovado". Decidir se a fábrica usa etiqueta de issue, arquivo de status ou outra convenção.
6. Para os executores citados (Cursor, Codex, agy), só li as páginas de integração do Spec Kit e a tabela do OpenSpec. Não testei nenhuma instalação.

## Fontes

- [F1] https://github.com/github/spec-kit (release v1.3.2, publicada em 2026-11-06, licença MIT; consultado via `gh api repos/github/spec-kit`)
- [F2] https://github.com/Fission-AI/OpenSpec (release v1.16.1, 2026-11-07, licença MIT)
- [F3] https://github.com/obra/superpowers (release v7.0.2, 2026-11-03, licença MIT; README: instalação por agente e telemetria)
- [F4] https://github.com/Fission-AI/OpenSpec/blob/main/README.md (comandos, fluxo, instalação, telemetria)
- [F5] https://github.com/Fission-AI/OpenSpec/blob/main/docs/agent-contract.md (saídas JSON do CLI)
- [F6] https://github.com/github/spec-kit/blob/main/README.md
- [F7] https://github.com/github/spec-kit/blob/main/docs/quickstart.md
- [F8] Skills instaladas do superpowers 7.0.0: `/home/renpv/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.0/skills/{brainstorming,writing-plans,subagent-driven-development,executing-plans,finishing-a-development-branch}/SKILL.md`
- [F9] Mesmos arquivos, trechos sobre o ledger `.superpowers/sdd/` (subagent-driven-development e executing-plans)
- [F10] https://github.com/github/spec-kit/blob/main/spec-driven.md e https://github.com/github/spec-kit/blob/main/templates/commands/specify.md (pasta `specs/`, `.specify/feature.json`)
- [F11] https://github.com/github/spec-kit/blob/main/docs/integrations/index.md e `docs/integrations/cli.md` (lista de agentes, grafia dos comandos); guias `claude.md`, `cursor-agent.md`, `codex.md`, `gemini.md`, `agy.md` na mesma pasta
- [F12] https://github.com/github/spec-kit/blob/main/docs/reference/agentic-sdd.md
- [F13] https://github.com/github/spec-kit/blob/main/templates/tasks-template.md e `templates/commands/implement.md`
- [F14] https://github.com/github/spec-kit/blob/main/docs/installation.md
- [F15] https://github.com/Fission-AI/OpenSpec/blob/main/docs/supported-tools.md
- [F16] https://github.com/Fission-AI/OpenSpec/blob/main/docs/concepts.md e `docs/commands.md` (estrutura de pastas, `tasks.md`, archive)
- [F17] https://github.com/Fission-AI/OpenSpec/blob/main/docs/cli.md e README (instalação, telemetria)
