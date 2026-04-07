#!/bin/bash
# ferclaudeobs project setup — clones repo, copies config, installs plugins
# Usage: bash <(curl -s https://raw.githubusercontent.com/ferone/ferclaudeobs/main/scripts/setup-project.sh)
#   or:  bash setup-project.sh [project-path]

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/ferone/ferclaudeobs.git"
TMP_DIR=$(mktemp -d)

cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# Determine project directory
if [ $# -ge 1 ]; then
  PROJECT_DIR="$(cd "$1" && pwd)"
else
  PROJECT_DIR="$(pwd)"
fi

echo -e "${CYAN}${BOLD}=== ferclaudeobs Setup ===${NC}"
echo -e "Project: ${BOLD}$PROJECT_DIR${NC}"
echo ""

# Validate project directory
if [ ! -d "$PROJECT_DIR" ]; then
  echo -e "${RED}Error: Directory '$PROJECT_DIR' does not exist.${NC}"
  exit 1
fi

# Warn if .claude/ already exists
if [ -d "$PROJECT_DIR/.claude" ]; then
  echo -e "${YELLOW}Warning: .claude/ already exists in this project.${NC}"
  read -rp "Overwrite existing config? (y/N) " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
  fi
fi

# Step 1: Clone and copy
echo -e "${BOLD}[1/2] Cloning ferclaudeobs and copying config...${NC}"

git clone --depth 1 "$REPO_URL" "$TMP_DIR/ferclaudeobs" 2>&1 | tail -1
SRC="$TMP_DIR/ferclaudeobs"

mkdir -p "$PROJECT_DIR/.claude"

cp "$SRC/settings.json" "$PROJECT_DIR/.claude/"
cp -r "$SRC/rules" "$PROJECT_DIR/.claude/"
cp -r "$SRC/skills" "$PROJECT_DIR/.claude/"
cp -r "$SRC/agents" "$PROJECT_DIR/.claude/"
cp -r "$SRC/hooks" "$PROJECT_DIR/.claude/"
cp -r "$SRC/scripts" "$PROJECT_DIR/.claude/"
cp "$SRC/plugins.json" "$PROJECT_DIR/.claude/"
cp "$SRC/.gitignore" "$PROJECT_DIR/.claude/"

# CLAUDE.md goes to project root
if [ -f "$PROJECT_DIR/CLAUDE.md" ]; then
  echo -e "${YELLOW}  CLAUDE.md already exists at project root — skipping (won't overwrite).${NC}"
else
  cp "$SRC/CLAUDE.md" "$PROJECT_DIR/"
fi

if [ ! -f "$PROJECT_DIR/CLAUDE.local.md" ]; then
  cp "$SRC/CLAUDE.local.md.example" "$PROJECT_DIR/"
fi

# Make scripts executable
chmod +x "$PROJECT_DIR/.claude/hooks/"*.sh 2>/dev/null || true
chmod +x "$PROJECT_DIR/.claude/scripts/"*.sh 2>/dev/null || true

# Add CLAUDE.local.md to .gitignore if not already there
if [ -f "$PROJECT_DIR/.gitignore" ]; then
  if ! grep -q "CLAUDE.local.md" "$PROJECT_DIR/.gitignore"; then
    echo "CLAUDE.local.md" >> "$PROJECT_DIR/.gitignore"
  fi
else
  echo "CLAUDE.local.md" > "$PROJECT_DIR/.gitignore"
fi

echo -e "${GREEN}  Config files copied.${NC}"

# Step 2: Install plugins
echo -e "${BOLD}[2/2] Installing plugins...${NC}"

if ! command -v claude &>/dev/null; then
  echo -e "${YELLOW}  'claude' CLI not found — skipping plugin installation.${NC}"
  echo -e "${YELLOW}  Install Claude Code (https://claude.ai/code), then run:${NC}"
  echo -e "${YELLOW}    bash $PROJECT_DIR/.claude/scripts/install-plugins.sh${NC}"
else
  bash "$PROJECT_DIR/.claude/scripts/install-plugins.sh"
fi

echo ""
echo -e "${GREEN}${BOLD}=== Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code (if already running)"
echo "  2. Run /init to select configs and customize for your project"
echo ""
