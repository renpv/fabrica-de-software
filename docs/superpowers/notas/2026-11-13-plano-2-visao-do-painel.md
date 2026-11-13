# Plano 2: notas da conversa (pausado em 2026-11-13)

Estas notas registram o início do brainstorming do Plano 2. Não são a spec: o brainstorming foi **pausado** pelo Renato para retomada depois. Quem retomar continua daqui, sem refazer as primeiras perguntas.

## Onde o projeto está
- Plano 1 (fundação e cadastro) concluído e mergeado na `main` (PRs #3 a #20).
- A central é só cadastro: contas de agente, conexões GitHub/GitLab, projetos, predefinições de fluxo e recepção de webhooks. Nenhum agente executa nada e nenhum fluxo roda.
- O que estava planejado para o Plano 2 na spec geral (`docs/superpowers/specs/2026-11-07-fabrica-de-software-design.md`): runner local no PC do Renato (só conexão de saída, chama o `claude` já logado, uma worktree por task) e o adaptador do Claude. Os adaptadores devolvem à central o mesmo resultado (branch, link do PR/MR, estado). Em aberto na spec: mecanismo do runner (WebSocket, long polling, fila) e como ele se autentica.

## Teste local da central (2026-11-12)
Um teste exploratório no navegador, com banco descartável, confirmou que login, contas, plataformas, predefinições e o layout em 390px funcionam. Defeitos achados foram corrigidos no PR #20 (sem Subir/Descer, nome da predefinição, favicon). Ficaram de fora e continuam válidos: conta Cursor com chave recusada não salva (intencional); o fluxo real de GitHub e GitLab; o menu hambúrguer aberto; o aceite manual do Plano 1 com contas reais.

Armadilhas do ambiente local do Renato: a porta 8000 é do Portainer, então o back-end local usa a 8001 e o `frontend/vite.config.ts` (proxy fixo na 8000) precisa de um config temporário; o login exige `Membro`, então crie usuários com `apps.donos.servicos.criar_dono`, e não com `createsuperuser`.

## O que o Renato disse que quer (palavras dele, resumidas)
Resposta à pergunta "o que você espera estar fazendo, de manhã, quando uma task do Claude começa a rodar?":

- **Gerenciar e acompanhar a execução de cada projeto.** O foco é o gestor, e não o runner.
- **Gerenciar com facilidade o fluxo de execução das implementações nos repositórios.**
- **Visão geral do fluxo de desenvolvimento, baseada no repositório (GitHub).** O exemplo dado foi o próprio projeto da fábrica.
- **Mostrar quem é o responsável por cada etapa:** o agente que elabora as specs, o que executa o código, o que faz a revisão.
- **O painel "assiste" o fluxo.** Quando uma issue é registrada, a fábrica acompanha e **acusa quando precisa de intervenção humana**.
- **Painel principal:** os projetos em execução.
- **Há muito mais coisas, mas quer ir passo a passo** para não misturar tudo.
- **Pediu protótipos das telas num canvas**, mas deixou isso para a retomada.

## Leitura minha (palpites, ainda não confirmados)
- O Plano 2 parece mudar de natureza: do que a spec geral previa (runner e adaptador) para **observabilidade do fluxo**: um painel que lê o estado do repositório (issues, PRs, etiquetas `acao:`/`agente:`/`em-andamento`/`precisa-humano`) e mostra a etapa de cada projeto e o agente responsável. As etiquetas do `fluxo-de-desenvolvimento.md` já modelam esse estado, e os webhooks já são recebidos e guardados desde o Plano 1.
- O runner e o adaptador do Claude continuariam necessários, mas talvez em plano posterior, depois que o painel mostrar o fluxo.
- Fonte do estado: webhooks do GitHub (já chegam à central) mais consulta pela API quando faltar dado.

## Perguntas para a retomada, em ordem
1. O Plano 2 passa a ser o painel de acompanhamento e o runner vira o Plano 3, ou os dois ficam juntos? (Recomendação minha: painel primeiro, porque entrega valor sem executar nada e valida o modelo de estado.)
2. O painel acompanha só projetos que a fábrica gerencia, ou qualquer repositório conectado, inclusive os que hoje seguem o fluxo à mão (top-tenis)?
3. O que conta como "precisa de intervenção humana": só a etiqueta `precisa-humano`, ou também PR parado há muito tempo, CI vermelho, issue sem agente?
4. Como a central avisa? Só no painel, ou também notificação (e-mail, Telegram)?
5. GitLab entra já ou fica para depois (a Unilab segue GitLab e fluxo manual)?

Depois das respostas: mostrar o canvas com protótipos (painel principal com os projetos em execução, visão de um projeto com o fluxo e os responsáveis, e a lista de pendências humanas), escrever a spec em `docs/superpowers/specs/`, passar pela checagem do construtor, e só então o plano.

## Como retomar
Abrir sessão no repositório, ler este arquivo e `proximos-passos.md` da memória, e seguir pelo brainstorming (`superpowers:brainstorming`) a partir das perguntas acima. Nada foi construído para o Plano 2.
