#!/bin/bash
# ferclaudeobs plugin installer
# Installs all plugins listed in plugins.json on a new machine.
# Usage: bash scripts/install-plugins.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
PLUGINS_FILE="$REPO_DIR/plugins.json"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

if ! command -v claude &>/dev/null; then
  echo -e "${RED}Error: 'claude' CLI not found.${NC}"
  echo "Install Claude Code first: https://claude.ai/code"
  exit 1
fi

if ! command -v jq &>/dev/null; then
  echo -e "${YELLOW}Warning: 'jq' not found. Falling back to grep-based parsing.${NC}"
  USE_JQ=false
else
  USE_JQ=true
fi

if [ ! -f "$PLUGINS_FILE" ]; then
  echo -e "${RED}Error: plugins.json not found at $PLUGINS_FILE${NC}"
  exit 1
fi

echo "=== ferclaudeobs Plugin Installer ==="
echo ""

# Add marketplaces
echo "Adding marketplaces..."

if [ "$USE_JQ" = true ]; then
  # Add impeccable marketplace (custom git source)
  IMPECCABLE_URL=$(jq -r '.marketplaces.impeccable.url' "$PLUGINS_FILE")
  if [ "$IMPECCABLE_URL" != "null" ]; then
    echo "  Adding impeccable marketplace..."
    claude plugin marketplace add impeccable --source git --url "$IMPECCABLE_URL" 2>/dev/null || echo -e "  ${YELLOW}(already added or failed)${NC}"
  fi
else
  echo "  Adding impeccable marketplace..."
  claude plugin marketplace add impeccable --source git --url "https://github.com/pbakaus/impeccable.git" 2>/dev/null || echo -e "  ${YELLOW}(already added or failed)${NC}"
fi

echo ""
echo "Installing plugins..."

TOTAL=0
SUCCESS=0
FAILED=0
SKIPPED=0

if [ "$USE_JQ" = true ]; then
  PLUGINS=$(jq -r '.plugins[]' "$PLUGINS_FILE")
else
  PLUGINS=$(grep -oP '"[^"]+@[^"]+"' "$PLUGINS_FILE" | tr -d '"')
fi

while IFS= read -r plugin; do
  [ -z "$plugin" ] && continue
  TOTAL=$((TOTAL + 1))

  PLUGIN_NAME="${plugin%@*}"
  MARKETPLACE="${plugin#*@}"

  echo -n "  [$TOTAL] $PLUGIN_NAME ($MARKETPLACE)... "

  if claude plugin install "$plugin" 2>/dev/null; then
    echo -e "${GREEN}installed${NC}"
    SUCCESS=$((SUCCESS + 1))
  else
    # Check if already installed
    if claude plugin list 2>/dev/null | grep -q "$PLUGIN_NAME"; then
      echo -e "${YELLOW}already installed${NC}"
      SKIPPED=$((SKIPPED + 1))
    else
      echo -e "${RED}failed${NC}"
      FAILED=$((FAILED + 1))
    fi
  fi
done <<< "$PLUGINS"

echo ""
echo "=== Done ==="
echo -e "  ${GREEN}Installed: $SUCCESS${NC}"
echo -e "  ${YELLOW}Already installed: $SKIPPED${NC}"
if [ "$FAILED" -gt 0 ]; then
  echo -e "  ${RED}Failed: $FAILED${NC}"
fi
echo "  Total: $TOTAL"
echo ""
echo "Restart Claude Code to load new plugins."
