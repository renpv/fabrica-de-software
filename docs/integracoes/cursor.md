# Integração: Cursor como executor

Situação: **pausada** (2026-11-07). A primeira versão da central é construída só com o Claude, e o Cursor volta quando a central puder configurá-lo. Este registro guarda o que foi aprendido, para virar o cadastro guiado do adaptador do Cursor.

## O que já está no repositório

| Arquivo | Para quê |
|---|---|
| `.cursor/environment.json` e `.cursor/Dockerfile` | Ambiente do agente na nuvem: Docker e compose (PostgreSQL dos testes), Node 26, `gh`, `uv` e Python 3.14. A imagem foi montada e conferida localmente. |
| `automacao/cursor/instalar.sh` | `install` idempotente do ambiente. |
| `automacao/cursor/PROMPT.md` | Contrato do executor, incluindo a regra de confiança (repositório público). |
| `.github/workflows/cursor.yml` | Acorda a automação quando `agente:cursor` entra numa issue ou num PR que já tem uma ação (`acao:implementar`, `acao:corrigir`). |
| `automacao/publicar-tarefa.sh`, `automacao/etiquetas.sh` | Publicar uma task como issue (`publicar-tarefa.sh <plano> <N> cursor`) e criar as etiquetas nas três famílias: ação, agente e estado. |

## Passos manuais que faltavam (a dor que a central deve eliminar)

Foram quatro lugares diferentes para ligar uma ferramenta:

1. **Painel do Cursor, em Cloud Agents → Environments:** criar o ambiente, conectar o GitHub, escolher o repositório e apontar **environment.json location** para o repositório.
2. **GitHub, em Settings → Personal access tokens:** criar um token fine-grained só para este repositório (Contents, Issues e Pull requests com leitura e escrita), porque a integração própria do Cursor não etiqueta nem comenta.
3. **Painel do Cursor, em Cloud Agents → Secrets:** gravar o token como `GH_TOKEN`, limitado ao ambiente.
4. **Painel do Cursor, em Automations:** criar a automação com o gatilho Webhook, colar o prompt, escolher o repositório, a branch, o ambiente e o modelo, salvar e só então copiar a URL e a chave.
5. **Terminal ou GitHub, em Settings → Secrets → Actions:** gravar `CURSOR_WEBHOOK_URL` e `CURSOR_WEBHOOK_API_KEY`.

## O que a central pode automatizar (para o plano do adaptador)

- O passo 4 e o gatilho (passo 5 e o workflow) somem quando a central dispara o agente direto pela Cloud Agents API (`POST /v1/agents`), em vez de passar por uma automação com webhook.
- O passo 2 some com o GitHub App da central: ela gera um token de curta duração por task e o entrega ao agente em `envVars`.
- O passo 1 pode ficar como um único passo guiado (o ambiente com o `environment.json` do repositório). Falta confirmar se a API cria ou escolhe ambientes.
- O que restar como manual vira um assistente no painel, com o link direto para cada tela e o "testar conexão".

## Pontos em aberto

- A documentação do Cursor não diz como o corpo do webhook chega ao agente. Por isso, o contrato faz o agente procurar a fila sozinho.
- Correção de segurança do Node anunciada para cerca de 11/11/2026: remontar o ambiente depois dela.
