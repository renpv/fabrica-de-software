#!/usr/bin/env bash
# Publica a Task N de um plano como issue para o executor.
# Uso: automacao/publicar-tarefa.sh docs/superpowers/plans/<plano>.md <N> [etiqueta]
#   etiqueta: "pronta-cursor" (padrão). A etiqueta vai por último, porque é o gatilho.
# Idempotente: se já existe issue aberta com o mesmo título, não cria outra.
set -euo pipefail

REPO="renpv/fabrica-de-software"
PLANO="$1"
N="$2"
ETIQUETA="${3:-pronta-cursor}"

SPEC="$(grep -m1 -oE '^\*\*Spec:\*\* `[^`]+`' "$PLANO" | grep -oE '`[^`]+`' | tr -d '`')"
[ -n "$SPEC" ] || { echo "Plano sem linha **Spec:**" >&2; exit 1; }

corpo="$(python3 -I - "$PLANO" "$N" "$SPEC" <<'EOF'
import re, sys
plano, n, spec = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(plano, encoding="utf-8").read()
total = len(re.findall(r"^### Task \d+:", s, re.M))
m = re.search(rf"^### Task {n}:.*?(?=^---\s*$|^## |\Z)", s, re.S | re.M)
if not m:
    sys.exit(f"Task {n} não encontrada em {plano}")
print(f"**Plano:** `{plano}` (Task {n} de {total})\n**Spec:** `{spec}`\n\n"
      "Leia o plano inteiro, em especial *Global Constraints* e *Review Focus*, "
      "e o contrato em `automacao/cursor/PROMPT.md`.\n")
print(m.group(0).strip())
EOF
)"
titulo_task="$(printf '%s\n' "$corpo" | grep -m1 '^### Task' | sed 's/^### //')"
plano_num="$(basename "$PLANO" | grep -oE 'plano-[0-9]+(-[0-9]+)?' | sed 's/^plano-//; s/-/./')"
titulo="Plano ${plano_num} · ${titulo_task}"

existente="$(gh issue list -R "$REPO" --state open --search "\"$titulo\" in:title" --json number,title \
  --jq ".[] | select(.title == \"$titulo\") | .number" | head -1)"
if [ -n "$existente" ]; then
  echo "Já existe a issue #$existente: $titulo"
  exit 0
fi

url="$(gh issue create -R "$REPO" --title "$titulo" --label tarefa --body "$corpo")"
gh issue edit "$url" --add-label "$ETIQUETA" >/dev/null
echo "$url"
