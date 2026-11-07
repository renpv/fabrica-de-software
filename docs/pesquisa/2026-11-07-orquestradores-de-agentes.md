# Orquestradores de agentes de codificação: o que existe e o que reaproveitar

Data de acesso: 2026-11-07. Todas as afirmações vêm de documentação oficial, repositórios (consulta via `gh api`) ou changelogs. Onde a fonte é secundária ou o dado não foi confirmado, está escrito.

## Resumo

- Nenhuma ferramenta cobre sozinha o seu desenho (contas múltiplas por agente + predefinições de fluxo + GitHub e GitLab + runner local + notificação só em decisão). A central continua fazendo sentido, mas como camada fina em cima de APIs que já existem.
- Testar primeiro (1): **Cursor Cloud Agents API v1 + SDK** [F1][F2]. É o MVP: cria agente por REST, aceita GitHub e GitLab, tem modo `machine`/`pool` (executa no seu PC, com saída apenas outbound) [F1][F3]. Atenção: o webhook ainda só existe na API v0; na v1 está "em breve" [F1].
- Testar primeiro (2): **OpenHands Agent Canvas + Automation Server** (MIT, ativo, release de 06/11/2026) [F4][F5]. Já faz o que você quer construir (agentes Claude Code/Codex via ACP, backends local/Docker/VM/nuvem, automações por cron e webhook assinado, receita "Software Factory" triage → dev → review → watchdog) [F6][F7][F8]. Serve como referência de desenho ou até como base. Lacuna: integração nativa com GitHub é do plano Enterprise; GitLab não aparece nos gatilhos [F9].
- Testar primeiro (3): **Symphony (OpenAI, Apache-2.0)** como *especificação* a copiar: daemon que consulta o rastreador, cria workspace isolado por issue, reinicia agente travado, fluxo versionado em `WORKFLOW.md` [F10][F11]. Só tem exemplo com Linear + Codex, e o próprio repositório se declara "preview de engenharia" [F10]. Use a ideia, não o código.
- Para o Claude Code: o caminho local mais seguro é **você mesmo rodar `claude -p` / Agent SDK** num runner seu [F12]. Cuidado: a Anthropic diz que terceiros não podem oferecer login claude.ai nem os limites da assinatura nos seus produtos; use chave de API ou o CLI já logado pelo próprio usuário (ponto a confirmar) [F13].
- Evitar como base: **Vibe Kanban** (empresa encerrada em abril/2026, serviços remotos desligados, só comunidade) [F14]; **Claude Squad** (AGPL-3.0, TUI interativa, sem gatilhos) [F15]; **Conductor** e **Sculptor** (apps desktop de uso interativo, sem webhook) [F16][F17].
- Sem confirmação: preços de Devin e Factory (fontes oficiais não abertas), suporte a GitLab nos gatilhos das "rotinas" do Claude (a doc só cita GitHub) [F18].

## Tabela comparativa

| Ferramenta | Tipo / licença | Agentes | GitHub / GitLab | Gatilhos | Runner local | Maturidade (07/11/2026) |
|---|---|---|---|---|---|---|
| Cursor Cloud Agents API + Automations | SaaS, API em beta pública | Cursor (modelos Claude etc. dentro do Cursor) | GitHub, GitLab (cloud e self-hosted), Bitbucket, Azure DevOps | API REST; Automations: cron, PR/push, Slack, webhook, Linear; webhook de status só na v0 | Sim: `agent worker start` (machine/pool), outbound | Doc oficial atual; SDK TS/Python |
| Claude Code (rotinas, nuvem, headless, Actions) | SaaS + CLI/SDK | Só Claude | Rotinas: GitHub; Actions: GitHub; GitLab CI: beta mantido pela GitLab | Agenda, API `/fire`, evento GitHub | Self-hosted environments (beta, Team/Enterprise); `claude -p` em qualquer máquina | Rotinas em research preview |
| GitHub Copilot cloud agent / Agent HQ | SaaS, planos Copilot | Copilot, Claude, Codex (preview) | Só GitHub | UI, atribuir issue, API de tarefas (preview), automações | Não | Preview, mudando rápido |
| GitLab Duo Agent Platform | SaaS/self-managed, créditos | Agentes da GitLab | Só GitLab | Menção, atribuição, pipeline, MR, status de work item (19.2) | Não (runners de CI) | GA desde jan/2026 |
| OpenHands Agent Canvas | Open source MIT, 92.9 mil estrelas | OpenHands + Claude Code, Codex, Gemini CLI, Pi, OpenCode (ACP) | GitHub (Enterprise nativo); resto via webhook | Cron, webhook assinado | Sim (backend local, Docker, VM) | v1.37.0, 06/11/2026 |
| Symphony (OpenAI) | Apache-2.0, 28 mil estrelas, spec + Elixir | Codex (app-server) | Rastreador: Linear; PR por hook | Polling do rastreador | Sim (daemon) | v0.0.3, set/2026, "preview" |
| Vibe Kanban | Apache-2.0, 28,6 mil estrelas | 10+ (Claude, Codex, Cursor, Copilot...) | GitHub | Nenhum (uso manual) | Sim (local) | Empresa encerrada em 10/04/2026 |
| Claude Squad | AGPL-3.0, 8,7 mil estrelas | Claude, Codex, Gemini, Aider... | Via git local | Nenhum | Sim (TUI) | v1.0.20, ago/2026 |
| Conductor (conductor.build) | App Mac, gratuito (fonte não oficial) | Claude Code, Codex | Via git | Nenhum | Sim (só macOS) | Sem dado oficial coletado |
| Sculptor (Imbue) | MIT, 246 estrelas, desktop | Claude Code | Via git | Nenhum | Sim | v0.49.0, "preview de pesquisa" |
| Devin (Cognition) | SaaS | Devin | GitHub; GitLab self-managed documentado | API v3 de sessões (Team/Enterprise, não confirmado) | Não | Preço instável, não confirmado |
| Factory (Droid) | SaaS + CLI | Droid | GitHub e GitLab | `droid exec` em CI | Sim (CLI) | Preço não confirmado |
| Goose (aaif-goose) | Apache-2.0, 56 mil estrelas | Qualquer LLM (agente próprio) | Via git/CI | `goose schedule`, `goose run` em CI | Sim | v1.57.0, 28/10/2026; scheduler com bug relatado |

## Por ferramenta

### 1. Cursor Cloud Agents API, SDK e Automations (testar primeiro)

- **O que é:** API REST v1 (beta pública) para criar um agente durável e rodar "runs" por prompt. Campos úteis: `repos[].url`, `startingRef`, `prUrl`, `autoCreatePR`, `workOnCurrentBranch`, `mode` (`plan` ou `agent`), `model`, `envVars`, `mcpServers`, `agentId` idempotente [F1].
- **Auth e contas:** Bearer ou Basic, chave de usuário (Dashboard) ou chave de *service account*. O SDK aceita os dois tipos [F1][F2]. Para o seu caso, uma chave por conta cadastrada na central cobre "Cursor em outra conta".
- **Git:** GitHub (Cloud e Enterprise Server), GitLab (Cloud e Self-Hosted), Bitbucket Cloud, Azure DevOps [F1]. `prUrl` vale também para MR do GitLab [F1].
- **Runner local:** `env.type: "machine"` ou `"pool"` roda as chamadas de ferramenta na sua máquina; o laço do agente e a inferência ficam na nuvem da Cursor; o worker só abre conexão de saída [F1][F3]. O SDK também tem runtime `local` (laço no seu processo Node), mas a inferência continua nos modelos hospedados [F2].
- **Gatilhos:** Automations rodam cloud agents por cron e por eventos de GitHub, GitLab, Bitbucket, Slack, webhook, Linear [F19]. Eventos de GitLab: PR/MR aberto, push, merge, comentário (núcleo) [F19].
- **Webhooks de status:** a doc da v1 diz "em breve"; a v0 envia `statusChange` (`ERROR`/`FINISHED`) com assinatura HMAC-SHA256 em `X-Webhook-Signature` [F1][F20]. Alternativa na v1: consultar o estado do run e usar o stream de run [F1].
- **Preço:** Cloud Agents exigem plano Premium ou superior, Teams ou Enterprise (Free e Plus não incluem); uso cobrado pela tarifa do modelo, com limite de gasto [F21]. Valores em dólar não coletados.
- **Aprovação humana:** `mode: "plan"` gera um plano antes de codar, bom para o passo "aprovar plano" feito pela sua central [F1].
- **Vale reaproveitar:** a API inteira, como adaptador "Cursor" da central. **Cuidado:** API em beta, mudanças possíveis; webhook v1 ausente.
- **Referência de código:** o repositório `cursor/cookbook` tem um exemplo de "kanban para cloud agents" e orquestradores [F2].

### 2. Claude Code (headless, rotinas, sessões na nuvem, Actions, GitLab CI)

- **Headless:** `claude -p "prompt" --allowedTools ...` e pacotes Agent SDK em Python/TypeScript, com saída estruturada e callbacks de aprovação de ferramenta [F12]. É o que a central chamaria no runner local.
- **Rotinas na nuvem ("scheduled tasks", antes "routines"):** prompt + repositórios + conectores, com gatilhos de agenda, API (POST em `/fire` com token bearer, campo opcional `text`) e evento do GitHub. Pro, Max, Ultra, Team e Enterprise. Research preview, com cabeçalho beta `experimental-cc-routine-2026-04-01` [F18].
- **Limites das rotinas (doc oficial):** agenda mínima de 1 hora; 100 execuções agendadas por hora por conta; chamadas de API: 30 por hora por rotina e 100 por hora por conta; eventos GitHub acima do teto são descartados; a rotina pertence à conta individual e commits saem com a sua identidade GitHub; branches com prefixo `claude/` [F18]. O endpoint `/fire` é só para usuários claude.ai e não faz parte da API da plataforma [F18].
- **GitLab:** a doc de rotinas só descreve gatilho GitHub [F18]. Para GitLab há a integração de CI/CD, em **beta e mantida pela GitLab**, que roda `claude -p` num job e abre MR; gatilho por pipeline ou por webhook de comentário com `@claude` via um "ouvinte" seu [F22].
- **Ambientes self-hosted (runner próprio):** beta público em Team e Enterprise, desligado por padrão; runners seus fazem polling em `api.anthropic.com` (sem porta de entrada); clonam só de GitHub ou GitHub Enterprise Server, e outro host git só com `--environment` [F23]. Não serve ao plano pessoal/Pro.
- **Actions:** `anthropics/claude-code-action` (MIT, 9,8 mil estrelas, tag `v1`) [F24].
- **Remote Control e canais:** continuar sessão local pelo celular/navegador; "channels" empurram webhooks/alertas para dentro de uma sessão em andamento via servidor MCP [F25].
- **Restrição importante:** "a Anthropic não permite que terceiros ofereçam login claude.ai ou os limites da assinatura nos seus produtos, inclusive agentes feitos com o Agent SDK; use chave de API" [F13]. Para a central, o desenho mais seguro é: o runner roda no PC do próprio usuário, que já fez `claude login` lá; ou usar chave de API por conta. Confirmar com a Anthropic se uma central própria que só dispara `claude -p` no PC do dono se enquadra.
- **Vale reaproveitar:** `claude -p` + Agent SDK no runner; rotinas com gatilho `/fire` como "agente na nuvem" para repositórios GitHub. **Evitar:** depender de rotinas para GitLab.

### 3. GitHub Agent HQ / Copilot cloud agent

- **O que é:** o "mission control" do GitHub para vários agentes. Agentes de terceiros hoje documentados: Claude e Codex, em preview público; precisam ser habilitados nas políticas [F26]. Atribuição pela aba Agents, issue ou menção `@agente` em comentário de PR [F26].
- **Cobrança:** sessões usam minutos do GitHub Actions e créditos de IA [F26]. Cloud agent novo disponível em planos pagos desde 28/10/2026; sessão em Actions limitada a 59 min; um PR por tarefa; só repositórios GitHub [F27].
- **API:** `POST /agents/repos/{owner}/{repo}/tasks` (campos `prompt`, `base_ref`, `model`, `create_pull_request`), listagem e consulta de estado (`queued`, `in_progress`, `completed`, `failed`, `idle`, `waiting_for_user`, `timed_out`, `cancelled`). Aceita só token de usuário (PAT ou OAuth/GitHub App user-to-server), não token de instalação [F28]. A página de how-to não cita webhooks nem limites de taxa [F28]. O changelog diz que Pro, Pro+ e Max também podem usar a API [F29].
- **Atribuir issue por API:** assignee `copilot-swe-agent[bot]` em REST ou GraphQL, com opções de `base_branch`, `custom_instructions`, `custom_agent`, `model` [F28].
- **Vale reaproveitar:** adaptador GitHub para "Copilot/Claude/Codex via GitHub" usando a API de tarefas; o estado `waiting_for_user` é bom gancho de notificação. **Evitar:** contar com isso para GitLab; é só GitHub.

### 4. GitLab Duo Agent Platform

- **O que é:** plataforma de agentes e "flows" dentro do GitLab. GA em 15/01/2026; cobrança por GitLab Credits [F30][F31]. Flows personalizados são GA e ganham em 19.2 o gatilho "work item status changed"; gatilhos incluem menção, atribuição, pipeline e ciclo de vida de MR; permitem pontos de aprovação humana; consomem créditos [F31].
- **Lacuna:** a página oficial não menciona agentes de terceiros (Claude Code, Codex) nem webhook como gatilho [F31]. Só GitLab.
- **Vale reaproveitar:** como destino/alvo nos projetos que estão no GitLab da Unilab, se a licença já existir; os eventos do GitLab (webhooks de projeto) é que a central deve consumir diretamente. **Evitar:** como base da central.

### 5. OpenHands (Agent Canvas) (testar primeiro)

- **O que é:** o README atual descreve o projeto como "centro de controle de desenvolvedor auto-hospedado para agentes de código e automações": roda OpenHands, Claude Code, Codex, Gemini, Pi, OpenCode ou qualquer agente ACP, em backends local, remoto e nuvem [F4]. Licença MIT; repositório com 92,9 mil estrelas e release v1.37.0 em 06/11/2026 [F5]. Automation Server em repositório separado (`OpenHands/automation`, MIT, 48 estrelas) [F5].
- **Arquitetura:** Canvas (UI React) → Agent Server (executa) + Automation Server (cron, gatilhos, histórico de runs, despacha conversas) + sandbox/workspace [F7]. Dá para rodar tudo local ou em Docker/VM/Helm; backend remoto usa a mesma API do local [F7].
- **Agentes e contas:** agente ACP usa o login de assinatura da máquina ou chave de API; "Agent Profiles" guardam configurações reutilizáveis e segredos por perfil [F6][F8]. Isso se aproxima de "cadastrar agente por conta".
- **Gatilhos:** automações por cron e por **fonte de evento** (webhook com URL pública e segredo de assinatura; rejeita assinatura inválida com 401; o payload inteiro vai para o prompt) [F9]. GitHub, Jira Data Center e Bitbucket Data Center são fontes embutidas **no OpenHands Enterprise**; para o resto, webhook customizado [F9]. GitLab não aparece na lista.
- **Fluxo configurável:** a receita "Software Factory" configura quatro automações independentes (triage, developer, reviewer, watchdog) que levam uma issue GitHub até PR, revisão, testes e merge, com três tokens de menor privilégio por papel [F8]. Isso é o mais próximo do seu "predefinições de fluxo" que achei, mas é um conjunto de automações, não um modelo de etapas com troca de agente.
- **Notificação / aprovação humana:** acesso por celular via Tailscale/ngrok; integra Slack [F4][F7]. Não confirmei um mecanismo de "pedir decisão e receber resposta".
- **Vale reaproveitar/testar:** subir o Agent Canvas em Docker na VPS ou no PC, ligar Claude Code por ACP e rodar o "Software Factory" num repositório de teste. **Evitar:** assumir que GitLab funciona sem webhook customizado; a base é grande e muda rápido.

### 6. Symphony (OpenAI)

- **O que é:** especificação (`SPEC.md`) e implementação de referência em Elixir; Apache-2.0; 28 mil estrelas; release v0.0.3 em 15/09/2026. Descrito pelo próprio README como "preview de engenharia de baixo perfil para ambientes confiáveis" [F10][F5].
- **Como funciona:** consulta o rastreador numa cadência fixa, despacha com concorrência limitada, cria workspace isolado por issue, roda a sessão do agente via app-server do Codex, tenta de novo e reconcilia; política do fluxo vive em `WORKFLOW.md` no repositório; recupera estado após reinício sem banco; estados de entrega como `Human Review`; não é motor de workflow genérico [F11].
- **Limites para você:** rastreador demonstrado é Linear; agente demonstrado é Codex; a implementação de referência não é produto mantido [F10]. Não encontrei adaptador GitHub/GitLab oficial.
- **Vale reaproveitar:** o desenho (poll + workspace por issue + `WORKFLOW.md` versionado + estado de entrega "aguardando humano"). Implementar um adaptador próprio em Django.

### 7. Vibe Kanban (evitar como base)

- Quadro kanban com workspaces por branch e revisão de diff, para 10+ agentes (Claude Code, Codex, Cursor, Copilot, Gemini CLI etc.); GitHub apenas; auto-hospedagem em Docker documentada [F14].
- **Em 10/04/2026 a Bloop anunciou o encerramento da empresa.** O projeto segue como open source mantido pela comunidade; serviços remotos (issues, comentários, projetos, organizações) saíram do ar após 30 dias, e a arquitetura passa a ser totalmente local [F32]. Apache-2.0, 28,6 mil estrelas, último release v0.1.44 em 24/04/2026, com push recente (04/11/2026) [F5].
- **Utilidade:** inspiração de interface (kanban + diff com comentários). Sem gatilhos, sem GitLab. Risco de abandono.

### 8. Claude Squad

- TUI que gerencia vários agentes (Claude Code, Codex, Gemini, Aider) em workspaces git isolados [F15]. AGPL-3.0, 8,7 mil estrelas, v1.0.20 em 20/08/2026 [F5].
- Interativo, sem webhook, agenda nem notificações. AGPL complica reaproveitar código. Só como ideia de isolamento por worktree.

### 9. Conductor (conductor.build)

- App de Mac que roda agentes Claude Code e Codex em paralelo, um git worktree por workspace; gratuito, paga-se o modelo direto; só Apple Silicon (fontes **não oficiais** coletadas via busca, o site oficial não foi aberto) [F16]. Você usa WSL/Linux: **descartado**.

### 10. Sculptor (Imbue)

- App desktop (Mac, Linux) para agentes em paralelo; MIT; 246 estrelas; v0.49.0 em 21/10/2026; o README se diz "preview de pesquisa" e sem banda para contribuições externas [F17][F5]. Sem gatilhos. **Evitar** como base.

### 11. Devin (Cognition)

- API v3: `POST /v3/organizations/{org_id}/sessions` com token de serviço `cog_`; escopos de organização e de enterprise [F33]. A página não cobre webhooks, limites de taxa nem agenda [F33]. Há integração documentada com GitLab self-managed 16.6+ [F34].
- **Preço:** fontes secundárias discordam (planos de US$ 20 a US$ 500, preço por ACU, cota com excedente) e nenhuma é a página oficial de preços. **Não confirmado.**
- **Vale:** testar só se houver necessidade de um agente "terceirizado" por sessão API; custo e acesso à API (Team/Enterprise) podem inviabilizar para dev solo.

### 12. Factory (Droid)

- `droid exec` é o modo headless para CI (começa somente leitura; `--auto low|medium|high` libera escrita); roda em Linux glibc; chave `FACTORY_API_KEY`; exemplos com GitHub Actions e GitLab CI; GitHub Enterprise Server e GitLab self-hosted exigem plano Enterprise, e GitLab self-hosted ainda não suporta *service account* de acesso ao repositório [F35].
- Preço **não confirmado**. Possível futuro adaptador "Droid via CLI headless".

### 13. Goose (aaif-goose, ex-block/goose)

- Agente open source (Apache-2.0, 56 mil estrelas, v1.57.0 em 28/10/2026) com receitas, `goose run` headless e `goose schedule` por cron [F5][F36]. Há issue aberta relatando que o agendador não serve para receitas sem supervisão na 1.45.0 (precisava de alternativa via launchd) [F36]. Não é orquestrador de outros agentes e sim mais um agente. Útil como "agente genérico" via OpenRouter/qualquer LLM no futuro.

### 14. Outros relevantes

- **OpenAI Codex:** CLI, SDK ("controlar agentes Codex locais"), Codex Cloud, tarefas agendadas e App Server para embutir em produtos [F37]. É o alvo do MVP futuro; o Symphony e o OpenHands já falam com ele (app-server e ACP).
- **Agent Client Protocol (ACP):** padrão JSON-RPC sobre stdio para falar com agentes de código; o OpenHands já usa adaptadores para Claude Code, Codex, Gemini CLI, Pi, OpenCode [F6]. Candidato a contrato único do seu "runner local".

## Lacunas: o que nenhuma resolve

1. **Cadastro de agente por conta com credenciais guardadas uma vez e roteamento por etapa.** O mais próximo são os perfis do OpenHands [F8] e as chaves de serviço do Cursor [F1]. Nenhuma ferramenta modela "Claude da conta pessoal" vs "Claude do cliente" vs "Cursor de outra conta" como entidades com cota e estado.
2. **Predefinições de fluxo reutilizáveis e ajustáveis por spec** (spec → plano → tasks → implementar → revisar → merge, com agente diferente por etapa). OpenHands (quatro automações soltas) e Symphony (um `WORKFLOW.md` por repositório) chegam perto, mas sem modelo de etapas nem herança "predefinição → projeto → spec".
3. **GitHub e GitLab no mesmo fluxo.** Copilot é só GitHub [F27]; Duo é só GitLab [F31]; rotinas do Claude só GitHub [F18]; Symphony usa Linear [F10]; OpenHands tem GitHub no Enterprise [F9]. Só o Cursor lista os dois nos gatilhos e na API [F1][F19]. Você terá de normalizar eventos de issue/PR/MR e etiquetas em adaptador próprio.
4. **Notificar só em decisão e deixar responder.** Existem estados úteis (`waiting_for_user` no Copilot [F28], `Human Review` no Symphony [F11], `plan` no Cursor [F1]), mas nenhuma ferramenta tem caixa de entrada de decisões com resposta que volte ao agente. Isso é o centro do valor da sua central.
5. **Detecção de cota esgotada e de agente travado** de forma uniforme: cada serviço expõe de um jeito (limites por hora das rotinas [F18], limite de gasto no Cursor [F21]); Symphony reinicia agentes travados [F10], mas só no seu escopo.
6. **Visão consolidada de vários projetos e agentes de fornecedores diferentes.** Agent HQ tenta, mas só dentro do GitHub [F26].
7. **Runner local unificado:** Cursor tem worker próprio [F3], Claude tem runner só para Team/Enterprise [F23], OpenHands tem Agent Server [F7]. Cada um com protocolo diferente.

## Perguntas em aberto

- Rodar `claude -p` num runner disparado pela sua central, no PC do dono já logado com assinatura Max, é aceito pelos termos? A doc só proíbe terceiros de oferecer login/limites da assinatura [F13]. Pedir confirmação à Anthropic ou usar chave de API.
- Quando o Cursor lançará webhooks na API v1? Hoje só a v0 tem [F1][F20].
- O Automation Server do OpenHands aceita eventos do GitLab? Só vi GitHub (Enterprise), Jira DC e Bitbucket DC como embutidos [F9]; testar o webhook customizado com o GitLab.
- Limites de taxa e de concorrência do Cursor Cloud Agents API e valores em dólar: não coletados.
- Preço e acesso à API do Devin e preço do Factory: não confirmados em fonte oficial.
- Conductor: licença e termos não verificados na fonte oficial.
- Rotinas do Claude funcionam com repositório GitLab? A doc não diz; só GitHub é descrito [F18].

## Recomendação prática de ordem de teste

1. **Cursor Cloud Agents API:** criar um agente por REST num repositório de teste (GitHub e GitLab), com `mode: "plan"`, e testar `env.type: "machine"` no seu PC.
2. **OpenHands Agent Canvas:** subir em Docker, ligar Claude Code por ACP, rodar o "Software Factory" e registrar um webhook de teste vindo do GitLab.
3. **Symphony:** ler o `SPEC.md` e o `WORKFLOW.md` para copiar o modelo de poll + workspace por issue + estado "aguardando humano". Não subir o Elixir em produção.

## Fontes

- [F1] Cursor, Cloud Agents API (endpoints): https://cursor.com/docs/cloud-agent/api/endpoints.md
- [F2] Cursor, SDK TypeScript: https://cursor.com/docs/sdk/typescript.md
- [F3] Cursor, My Machines: https://cursor.com/docs/cloud-agent/self-hosted/my-machines.md e visão geral https://cursor.com/docs/cloud-agent/self-hosted.md
- [F4] OpenHands, README: https://github.com/OpenHands/OpenHands
- [F5] Estrelas, licenças e releases consultados via `gh api repos/<dono>/<repo>` em 2026-11-07: BloopAI/vibe-kanban, openai/symphony, OpenHands/OpenHands, OpenHands/automation, smtg-ai/claude-squad, imbue-ai/sculptor, aaif-goose/goose, anthropics/claude-code-action
- [F6] OpenHands, ACP Agents: https://docs.openhands.dev/openhands/usage/agent-canvas/acp-agents.md
- [F7] OpenHands, Arquitetura: https://docs.openhands.dev/openhands/usage/agent-canvas/architecture.md
- [F8] OpenHands, Software Factory: https://docs.openhands.dev/openhands/usage/use-cases/software-factory.md
- [F9] OpenHands, Event Sources: https://docs.openhands.dev/openhands/usage/agent-canvas/automation-events.md e https://docs.openhands.dev/openhands/usage/automations/event-automations.md
- [F10] Symphony, repositório: https://github.com/openai/symphony
- [F11] Symphony, SPEC: https://github.com/openai/symphony/blob/main/SPEC.md
- [F12] Claude Code, execução programática: https://code.claude.com/docs/en/headless.md
- [F13] Claude Agent SDK, visão geral (nota sobre login claude.ai): https://code.claude.com/docs/en/agent-sdk/overview.md
- [F14] Vibe Kanban, README: https://github.com/BloopAI/vibe-kanban
- [F15] Claude Squad, README: https://github.com/smtg-ai/claude-squad
- [F16] Conductor (fontes secundárias, não oficial): https://www.conductor.build e https://codepick.dev/en/tool/conductor/
- [F17] Sculptor, README: https://github.com/imbue-ai/sculptor
- [F18] Claude Code, tarefas agendadas/rotinas: https://code.claude.com/docs/en/routines
- [F19] Cursor, Automations: https://cursor.com/docs/cloud-agent/automations.md
- [F20] Cursor, Webhooks (v0): https://cursor.com/docs/cloud-agent/api/webhooks.md
- [F21] Cursor, Cloud Agents (planos e cobrança): https://cursor.com/docs/cloud-agent.md
- [F22] Claude Code, GitLab CI/CD (beta, mantido pela GitLab): https://code.claude.com/docs/en/gitlab-ci-cd
- [F23] Claude Code, ambientes self-hosted: https://code.claude.com/docs/en/self-hosted-environments
- [F24] anthropics/claude-code-action: https://github.com/anthropics/claude-code-action
- [F25] Claude Code, Remote Control e canais: https://code.claude.com/docs/en/remote-control.md e https://code.claude.com/docs/en/channels.md (conforme índice https://code.claude.com/docs/llms.txt)
- [F26] GitHub Docs, agentes de terceiros: https://docs.github.com/en/copilot/concepts/agents/about-third-party-agents
- [F27] GitHub Docs, Copilot cloud agent: https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent
- [F28] GitHub Docs, cloud agent via API: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/use-cloud-agent-via-the-api e https://docs.github.com/en/rest/agent-tasks/agent-tasks
- [F29] GitHub Changelog, API de tarefas para Pro/Pro+/Max: https://github.blog/changelog/2026-06-04-agent-tasks-rest-api-now-available-for-copilot-pro-pro-and-max/
- [F30] GitLab, Duo Agent Platform GA (issue oficial): https://gitlab.com/gitlab-org/gitlab/-/issues/585273
- [F31] GitLab, flows multi-etapa (julho/2026): https://about.gitlab.com/blog/multi-step-software-delivery-with-agentic-flows/
- [F32] Bloop, anúncio de encerramento: https://www.vibekanban.com/blog/shutdown
- [F33] Devin, API v3: https://docs.devin.ai/api-reference/overview
- [F34] Devin, GitLab self-managed: https://docs.devin.ai/enterprise/integrations/gitlab-self-managed.md
- [F35] Factory, droid exec e GitLab: https://docs.factory.ai/cli/droid-exec/cookbook/github-actions e https://docs.factory.ai/onboarding/integrating-with-your-engineering-system/gitlab-self-hosted
- [F36] Goose, headless e issue do scheduler: https://goose-docs.ai/docs/tutorials/headless-goose/ e https://github.com/aaif-goose/goose/issues/11164
- [F37] Codex, índice da documentação: https://developers.openai.com/codex/llms.txt
