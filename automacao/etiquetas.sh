#!/usr/bin/env bash
# Cria ou atualiza as etiquetas do fluxo. Idempotente.
set -euo pipefail
REPO="renpv/fabrica-de-software"

while IFS='|' read -r nome cor descricao; do
  gh label create "$nome" -R "$REPO" --color "$cor" --description "$descricao" --force >/dev/null
  echo "ok: $nome"
done <<'EOF'
tarefa|0e8a16|Task de um plano
pronta-cursor|1d76db|Liberada para o Cursor (gatilho)
em-andamento|fbca04|O executor começou
em-revisao|5319e7|PR aberto, aguardando o orquestrador
correcao|d93f0b|Revisão pediu correção (gatilho)
precisa-humano|b60205|Parado, esperando o Renato
melhoria|c5def5|Backlog; nenhum executor pega
EOF
