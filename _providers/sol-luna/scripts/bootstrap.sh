#!/usr/bin/env bash
# Provider-local bootstrap: install Claude role files and shared policy guidance.
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
PROVIDER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TPL="$PROVIDER_DIR/references/project-template"

if [[ ! -d "$TPL" ]]; then
  # Running from monorepo root scripts/
  REPO_ROOT="$(cd "$PROVIDER_DIR/../.." && pwd)"
  if [[ -d "$REPO_ROOT/templates/codex" ]]; then
    exec bash "$REPO_ROOT/scripts/bootstrap.sh" "$ROOT"
  fi
  echo "project-template not found at $TPL" >&2
  exit 1
fi

echo "==> Target project: $ROOT"
mkdir -p "$ROOT/.claude/agents"

copy_if_missing() {
  local src="$1" dest="$2"
  if [[ -e "$dest" ]]; then
    echo "keep existing: $dest"
  else
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
    echo "created: $dest"
  fi
}

for f in luna-scout.md luna-worker.md luna-critic.md luna-tester.md; do
  copy_if_missing "$TPL/.claude/agents/$f" "$ROOT/.claude/agents/$f"
done
copy_if_missing "$TPL/AGENTS.md" "$ROOT/AGENTS.md"
copy_if_missing "$TPL/CLAUDE.md" "$ROOT/CLAUDE.md"

GI="$ROOT/.gitignore"
touch "$GI"
for line in '.env' '.env.*'; do
  grep -qxF "$line" "$GI" 2>/dev/null || echo "$line" >>"$GI"
done

echo
echo "==> Done. Provider contract: $PROVIDER_DIR/CONTRACT.md"
