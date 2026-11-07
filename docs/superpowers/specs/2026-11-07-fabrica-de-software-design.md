# Fábrica de Software: design

Data: 2026-11-07 · Status: rascunho para aprovação do Renato

## 1. Intenção e motivo

O Renato desenvolve com vários agentes de IA. Um agente escreve a spec e o plano, outro implementa, outro revisa. Hoje cada combinação de agente e plataforma se liga de um jeito: tokens gerados ora no agente, ora no GitHub ou no GitLab, links e webhooks criados à mão, um robô local para um agente e um workflow do Actions para outro (pasta `automacao/` do top-tenis). Não há padrão. O custo aparece na primeira configuração e piora quando ele **troca de agente**, porque aí a integração inteira é refeita.

A Fábrica é uma **central única** onde ele:
- cadastra uma vez cada agente, por conta, e reaproveita em qualquer projeto;
- monta o fluxo de trabalho (quem faz cada etapa) como uma **predefinição** reutilizável;
- liga projetos a repositórios do GitHub ou do GitLab sem configurar nada no repositório à mão;
- acompanha vários projetos ao mesmo tempo;
- só é chamado quando os agentes não têm autonomia para decidir, e responde pelo celular.

**Critério de sucesso:** ligar um agente novo, ou trocar o agente de um projeto, em minutos, por uma tela, sem caçar onde gerar cada token.

**Anti-objetivo (falha mesmo que funcione):** configurar ou trocar de agente continuar difícil. Toda decisão de design que esbarrar nisso perde.

## 2. Para quem

- **Agora:** só o Renato.
- **Depois:** clientes que contratam a construção de um software, em geral com contas próprias de agentes. O desenho não pode impedir essa entrada: os projetos, as contas e os segredos de cada dono ficam separados desde o primeiro modelo de dados. No MVP não há telas de cliente nem multi-inquilino exposto.

## 3. Vocabulário

| Termo | Significado |
|---|---|
| **Agente** | Tipo de ferramenta de codificação: Claude Code, Cursor (futuro: Codex/ChatGPT, OpenRouter, Antigravity). |
| **Conta** | Uma instância cadastrada de um agente com as credenciais de um dono. Ex.: "Claude, conta pessoal, no PC do Renato"; "Cursor, conta do cliente Y". É a conta que se escolhe nos fluxos, não o agente. |
| **Dono** | A quem pertence o espaço da central (projetos, contas, segredos). Hoje é só o Renato. No futuro, um cliente com acesso próprio vira outro Dono. |
| **Cliente** | Quem contratou um projeto dentro do espaço de um Dono e pode pagar contas próprias de agente. Uma conta sem cliente é do Dono. |
| **Plataforma** | Onde está o código: GitHub ou GitLab. |
| **Projeto** | Um software em construção, ligado a um repositório numa plataforma. |
| **Etapa** | Um passo do fluxo: grilling/spec, plano, publicar tasks, implementar, revisar, merge, promover. |
| **Papel** | Quem cumpre uma etapa: uma conta de agente ou o humano (aprovação). |
| **Predefinição** | Pacote salvo com o fluxo inteiro: as etapas, a ordem, o gatilho de cada uma e a conta que faz cada etapa. |
| **Spec** | Uma funcionalidade em andamento num projeto. Tem as próprias tasks e pode ter um ajuste próprio da predefinição. |
| **Task** | Unidade de trabalho entregue ao executor (hoje, uma issue). |
| **Runner local** | Programa que roda no PC do Renato, conecta-se à central (só conexão de saída), pega o trabalho destinado às contas locais e devolve o andamento. |
| **Pendência** | Ponto em que o fluxo para à espera de uma decisão humana. |

## 4. Objetivos do MVP

### 4.1 Contas de agente
- Cadastro guiado **dentro do painel**: para cada tipo de agente, a tela explica onde gerar cada credencial, com o link direto para a página certa (Cursor, Anthropic), e pede só o mínimo.
- **"Testar conexão"** antes de salvar: valida a credencial, as permissões e, quando a API permitir, a cota. O erro é dito em português claro, com o que fazer.
- Segredos guardados uma vez, cifrados, nunca mais exibidos.
- Agentes do MVP:
  - **Claude Code no PC do Renato**, via runner local, chamando o `claude` já logado naquela máquina (`claude -p` ou Agent SDK).
  - **Cursor**, via Cloud Agents API, por chave de cada conta.
- Mais de uma conta do mesmo agente (cota; conta de cliente).

### 4.2 Plataformas e projetos
- **GitHub (github.com) e o GitLab self-hosted da Unilab** no MVP, os dois de primeira classe. O gitlab.com fica para depois, mas o adaptador GitLab recebe a URL da instância, então ele custa pouco.
- Nos projetos da Unilab vale a predefinição com **merge com ok humano** (regras de commit da Unilab).
- **Estado no repositório:** o andamento de cada task também fica visível na plataforma (issue, etiquetas, PR/MR), como hoje. A central guarda a configuração e o histórico, mas o fluxo continua legível e retomável pelo repositório. Isso prepara a ida para a nuvem (seção 5).
- **Riscos a verificar antes do plano (GitLab da Unilab):** (1) se a instância é alcançável pela nuvem do Cursor ou só pela rede interna; se for só interna, o Cursor precisa rodar no modo `machine` (no PC) nesses projetos; (2) se a instância consegue enviar webhooks para a VPS, ou se a central precisa consultar o estado periodicamente; (3) se a política da Unilab permite um token de acesso guardado num servidor pessoal.
- Ligar um projeto a um repositório: a central **prepara o repositório sozinha** (etiquetas, webhooks, segredos/variáveis de CI que o fluxo exigir).
- Botão **"conferir"**: mostra o estado de cada item da preparação e oferece o conserto ao lado do que faltar.
- Vários projetos em andamento ao mesmo tempo, cada um com a própria predefinição.

### 4.3 Predefinições de fluxo
- **Onde a central começa (decidido pelo Renato):** o grilling, a spec e o plano continuam numa sessão do Claude Code, como hoje, e são aprovados ali. A central entra quando há um **plano aprovado** no repositório: ela registra a spec, publica as tasks e conduz o resto. Como a central fica sabendo do plano novo fica com quem constrói (cadastro no painel, chamada da própria sessão ou detecção do arquivo na `main`), desde que não exija configuração manual a cada spec.
- A central vem com a predefinição **"Padrão"**, que reproduz o fluxo de hoje (`~/.claude/rules/fluxo-de-desenvolvimento.md`) a partir do plano aprovado: publicar tasks → executor implementa e abre PR/MR → revisor revisa (aprova e faz merge, ou pede correção) → próxima task. Promoção para produção só com ok humano.
- No Padrão, uma conta implementa (executor) e outra revisa. Hoje é a mesma conta que fez a spec e o plano na sessão.
- O Renato cria, copia e edita predefinições. Um projeto **escolhe uma predefinição**. Trocar de agente pode ser só trocar a conta numa etapa ou trocar de predefinição.
- **Ajuste por spec:** uma spec pode sobrescrever qualquer parte da predefinição só para ela.
- **As mudanças valem na hora**, tanto na predefinição (para todos os projetos que a usam) quanto na spec. "Na hora" vale a partir da **próxima etapa**: a etapa em execução termina com a conta que a pegou. *(Escolha do Claude, trocável.)*
- A central registra qual configuração cada etapa usou de fato (histórico), para entender depois o que aconteceu. *(Escolha do Claude.)*
- **Gatilhos de etapa:** webhook recebido (evento da plataforma), webhook enviado ao agente, temporizador, conclusão da etapa anterior, decisão humana.
- No MVP, as etapas e os papéis disponíveis são os do fluxo de hoje. O modelo de dados já trata a etapa como item configurável, para os papéis futuros (seção 5).

### 4.4 Acompanhamento
- Painel com todos os projetos: specs, tasks e a etapa de cada uma (na fila, em execução, em revisão, em correção, parada à espera de humano), a conta que está trabalhando e os links para a issue e o PR/MR.

### 4.5 Pendências e PWA de notificação
- O fluxo para e cria uma pendência quando:
  - o merge precisa de ok humano (predefinições com "merge com ok humano", como as da Unilab);
  - a promoção para produção precisa de ok;
  - a conta está sem cota e não há outra conta permitida;
  - o agente declara que não tem autonomia (o `precisa-humano` de hoje);
  - uma falha se repete (por exemplo, a mesma correção reprovada duas vezes; o limite exato fica com quem constrói).
- **PWA simples**, separado do painel ou como uma parte leve dele: recebe notificação push (celular e PC), lista as pendências, mostra o detalhe e permite responder: aprovar, pedir correção com texto, dar o ok de produção, escolher outra conta, mandar instrução em texto livre ao agente travado. A resposta destrava o fluxo na hora.
- Fora das pendências, a central trabalha em silêncio.
- **Troca de conta por cota:** no MVP é manual. A central avisa e oferece a troca em um clique. *(Escolha do Claude, trocável.)*

## 5. Futuro (prever no desenho, não construir)

- **Grilling, spec e plano dentro da central:** o agente conduz a conversa e as perguntas chegam como pendências no PWA.
- **Tudo na nuvem:** o objetivo de longo prazo é não depender do PC. Os agentes rodam na nuvem, orquestrados pelas issues, etiquetas e PRs/MRs dos repositórios.
- **Papéis configuráveis por etapa:** um agente faz o grilling e escreve a spec e as tasks, outro codifica, outro valida, outro só escreve e valida os testes.
- **Mais agentes:** Claude na nuvem (sessões web e rotinas), Antigravity (`agy`), Codex/ChatGPT, OpenRouter (API).
- **Troca automática de conta** quando a cota acaba, respeitando as contas permitidas ao projeto.
- **Clientes** com acesso próprio aos seus projetos.
- Outros canais de notificação (Telegram etc.).

## 6. Não-objetivos do MVP

- Telas e acesso para clientes.
- Agentes além do Claude Code local e do Cursor.
- Escrever o próprio agente de codificação: a central orquestra agentes que já existem.
- Substituir o GitHub ou o GitLab como lugar das issues e dos PRs/MRs.

## 7. Restrições

- **Stack** (padrão dos projetos pessoais): Django com DRF, React com TypeScript, PostgreSQL, `uv`. Deploy na VPS do Renato com Docker Compose e Caddy. Monólito modular.
- **Autosserviço:** orientações, configurações e validações ficam no painel, e não no `.env` nem em documentos.
- **Segredos** nunca passam pelo chat nem aparecem depois de salvos.
- **Termos da Anthropic:** terceiros não podem oferecer o login do claude.ai nem os limites da assinatura em produtos próprios. Consequências:
  - a conta Claude pessoal roda **no PC do próprio dono**, com o `claude` que ele mesmo logou, disparado pelo runner local;
  - a conta Claude de um **cliente** usa a **chave de API** do cliente, e não o login da assinatura dele.
  - Fonte: `docs/pesquisa/2026-11-07-orquestradores-de-agentes.md` (ponto marcado ali como "a confirmar com a Anthropic").
- **Cursor:** a Cloud Agents API v1 está em beta e ainda não tem webhook de status. A central precisa consultar o estado (polling ou stream) até ele existir.
- Um projeto de cliente só usa contas permitidas para aquele projeto. O trabalho de um cliente nunca cai na conta de outro. *(Escolha do Claude.)*
- O contrato do executor de hoje (pegar a task, branch `tarefa-<N>`, PR/MR com `Closes #N`, correção no mesmo branch) continua sendo o contrato que todo executor cumpre. A central monta o adaptador de cada agente para esse contrato.

## 8. Decidido pelo Renato

- Central única para configurar, orquestrar e acompanhar.
- Uso só dele agora, com clientes depois.
- Agentes do MVP: Cursor e Claude (Claude começando pelo PC). Contas múltiplas por agente, por cota e por conta de cliente.
- GitHub e GitLab no MVP.
- Predefinições com o fluxo inteiro e os agentes, ajustáveis na predefinição e na spec, com efeito imediato.
- Aviso só quando os agentes não têm autonomia, por um PWA simples que permite responder.
- A central prepara o repositório sozinha, com um botão para conferir.
- Papéis múltiplos por etapa ficam para o futuro.
- O grilling, a spec e o plano continuam na sessão do Claude Code. A central começa no plano aprovado.
- No GitLab, o MVP atende à instância da Unilab.
- O fluxo pode esperar o PC quando depende dele ("aguardando o runner"). O objetivo é ir para a nuvem, orquestrado pelos repositórios.

## 9. Escolhas do Claude (trocáveis)

- Runner local com conexão só de saída (padrão GitHub Actions runner / GitLab Runner), substituindo o robô de `automacao/robo/`.
- "Na hora" = a partir da próxima etapa.
- Histórico da configuração usada em cada etapa.
- Troca de conta por cota manual no MVP.
- Contas permitidas por projeto.
- PWA no MVP: lista de pendências, detalhe e botões de resposta.
- **Execução do Claude local:** o runner cria uma worktree por task, roda o `claude`, que implementa e faz os commits, e depois faz o push. A central abre o PR/MR pela API. O token da plataforma é de curta duração, fornecido pela central a cada task, e não fica guardado no PC. O Cursor abre o próprio PR (`autoCreatePR`). Os dois adaptadores devolvem à central o mesmo resultado (branch, link do PR/MR e estado).
- **Spec e plano** ficam como arquivos no repositório do projeto (`docs/superpowers/specs/` e `plans/`), como hoje. A central os lê e mostra no painel e no PWA para aprovar. "Publicar tasks" cria uma issue por task do plano aprovado.
- **Merge:** o revisor aprova, e a central faz o merge pela API, só com o CI verde. Cada predefinição tem a opção "merge autônomo" ou "merge com ok humano". Esta segunda opção serve, por exemplo, aos projetos da Unilab, e cria uma pendência.
- **Detecção de pendências:** "sem autonomia" é sinalizado pelo agente, que aplica a etiqueta `precisa-humano` ou comenta com um marcador (contrato que já existe). "Sem cota" e falhas são detectados pelo adaptador, pelo erro da API ou pela saída do processo.
- **Isolamento:** toda entidade pertence a um **Dono**. No MVP há um único usuário e um único dono, com testes que garantem que uma consulta não cruza donos.
- **Plataformas:** no GitHub, um GitHub App instalado uma vez (dá para criar webhooks e etiquetas sem token amplo); no GitLab, um token de acesso (de grupo ou pessoal) guiado pelo painel. Os webhooks chegam à VPS pelo Caddy.
- **Formato do fluxo:** lista linear de etapas com dois desvios fixos (reprovar volta para a correção; pendência pausa). Quando a predefinição muda no meio de uma spec, ela continua da etapa atual pelo nome; se essa etapa foi removida, segue para a próxima que existir.
- **Concorrência:** um limite de tasks simultâneas por conta, configurável, com padrão 1 para o Claude local. Tasks de projetos diferentes rodam em paralelo em contas diferentes.

## 10. Deixado para quem constrói

- Mecanismo do runner local (WebSocket, long polling, fila) e como ele se autentica na central.
- Como a central fala com o Claude Code local (`claude -p` ou Agent SDK) e como detecta "sem autonomia" e "sem cota".
- Forma de autenticação nas plataformas (GitHub App ou token; aplicação OAuth ou token no GitLab), desde que o cadastro siga guiado e simples.
- Cifragem dos segredos e o armazenamento.
- Push do PWA (Web Push / VAPID) e a autenticação do Renato.
- Desenho das telas, seguindo o padrão de autosserviço.

## 11. Referências

- Fluxo atual: `~/.claude/rules/fluxo-de-desenvolvimento.md`; adaptadores atuais em `automacao/` no top-tenis.
- Levantamento de ferramentas: `docs/pesquisa/2026-11-07-orquestradores-de-agentes.md`. Ideias para reaproveitar: Cursor Cloud Agents API (adaptador Cursor, modo `machine` no PC, `mode: plan`), Symphony (fila por issue, estado "aguardando humano") e OpenHands Agent Canvas (receita "Software Factory", gatilhos por cron e webhook assinado).
