#!/usr/bin/env bash
# Cria ou atualiza as etiquetas do fluxo, em três famílias:
#   ação (o quê), agente (quem; acorda o agente) e estado/tipo.
# Idempotente. Também apaga as etiquetas do padrão antigo (ação e agente juntos).
set -euo pipefail
REPO="renpv/fabrica-de-software"

while IFS='|' read -r nome cor descricao; do
  gh label create "$nome" -R "$REPO" --color "$cor" --description "$descricao" --force >/dev/null
  echo "ok: $nome"
done <<'LISTA'
acao:implementar|1d76db|Ação: implementar a task
acao:revisar|5319e7|Ação: revisar o PR
acao:corrigir|d93f0b|Ação: corrigir o que a revisão pediu
agente:claude|0e8a16|Agente: acorda o Claude
agente:cursor|0e8a16|Agente: acorda o Cursor
em-andamento|fbca04|O agente começou
precisa-humano|b60205|Parado, esperando o Renato
tarefa|c2e0c6|Task de um plano
melhoria|c5def5|Backlog; nenhum agente pega
LISTA

for antiga in pronta-cursor correcao em-revisao; do
  if gh label list -R "$REPO" --limit 200 --json name --jq '.[].name' | grep -qx "$antiga"; then
    gh label delete "$antiga" -R "$REPO" --yes >/dev/null
    echo "apagada: $antiga"
  fi
done
