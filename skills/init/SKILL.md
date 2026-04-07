---
name: init
description: Initialize ferclaudeobs for a new project — check plugins, detect project type, select which rules/agents/hooks to enable, then customize for the tech stack.
argument-hint: "[optional: project type like 'nextjs' or 'python-api']"
---

Initialize this project's `.claude/` configuration with ferclaudeobs. This is the entry point after cloning ferclaudeobs into a new project.

## Phase 1: Check Plugin Installation

Read `plugins.json` from the ferclaudeobs repo (or `.claude/plugins.json` if already copied).

Check if the user's Claude Code has the required plugins installed. Use Bash to run:
```bash
claude plugin list 2>/dev/null
```

If plugins are missing, inform the user and offer to install them:
- On Windows: `powershell -ExecutionPolicy Bypass -File .claude/scripts/install-plugins.ps1`
- On macOS/Linux: `bash .claude/scripts/install-plugins.sh`

If the `claude` CLI is not available or plugin commands fail, inform the user they need to install plugins manually and continue — don't block the setup.

## Phase 2: Detect Project Type

Scan the project root for:

**Package manifests**: `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Gemfile`, `composer.json`, `build.gradle`, `pom.xml`, `Makefile`, `Dockerfile`

**Frontend indicators**: `.tsx`, `.jsx`, `.vue`, `.svelte` files, `tailwind.config.*`, CSS/SCSS files in components directories

**Backend indicators**: `src/api/`, `src/routes/`, `src/controllers/`, `src/services/`, Express/FastAPI/Django/Rails/Hono patterns

**Database indicators**: `prisma/`, `drizzle/`, `migrations/`, `alembic/`, `knexfile.*`, ORM in dependencies

**Documentation**: `docs/` directory, significant `.md` files beyond README

**Obsidian vault indicators**: `vault/` directory, `domain-packs/` directory, `scripts/pipeline.py`, `config/active-pack.json`, `.obsidian/` directory, `inbox/` directory

If Obsidian indicators are found, flag as "Obsidian Knowledge Management project" and auto-recommend:
- Rule: `obsidian.md` (vault interaction rules)
- Agents: `vault-orchestrator`, `entity-manager`, `doc-enricher`, `vault-validator`, `notebooklm-bridge`, `research-synthesizer`
- Hook: `vault-protect.sh`

**Monorepo indicators**: `workspaces` in package.json, `pnpm-workspace.yaml`, `lerna.json`, `nx.json`, `turbo.json`

## Phase 3: Present Selection UI

Based on detection results, present categorized selection using AskUserQuestion with `multiSelect: true`.

### Rules Selection
Present all rules with auto-recommendations:
- **code-quality** — Always recommended (universal)
- **testing** — Always recommended (universal)
- **security** — Recommended if API/auth/middleware code found
- **frontend** — Recommended if frontend files found
- **error-handling** — Recommended if backend code found
- **database** — Recommended if migrations/ORM found

### Agents Selection
Present all agents with auto-recommendations:
- **code-reviewer** — Always recommended
- **security-reviewer** — Always recommended
- **performance-reviewer** — Always recommended
- **frontend-designer** — Recommended if frontend found
- **doc-reviewer** — Recommended if docs/ directory found
- **parallel-executor** — Always recommended

### Hooks Selection
Present all hooks — all recommended by default:
- **protect-files** — Blocks edits to sensitive files
- **warn-large-files** — Blocks writes to build artifacts
- **scan-secrets** — Detects hardcoded credentials
- **block-dangerous-commands** — Blocks destructive shell commands
- **format-on-save** — Auto-formats after edits
- **session-start** — Injects git context at session start

## Phase 4: Apply Selections

For each unselected item:
- Delete the corresponding file (rule `.md`, agent `.md`, or hook `.sh`)
- If a hook is removed, also remove its entry from `settings.json` hooks configuration

For selected items, keep as-is.

## Phase 5: Clean Up

Delete files that waste tokens at runtime:
- `.claude/README.md` (if it exists — repo README, not project README)
- `.claude/CONTRIBUTING.md` (if it exists)
- `.claude/.gitignore` (for the ferclaudeobs repo, not the project)
- `.claude/rules/README.md`
- `.claude/agents/README.md`
- `.claude/hooks/README.md`
- `.claude/skills/README.md`
- `.claude/plugins.json` (already used, not needed at runtime)
- `.claude/scripts/` directory (already used, not needed at runtime)

## Phase 6: Delegate to /setup

Run the `/setup` skill to customize the remaining configuration files for the actual tech stack. This handles:
- Updating CLAUDE.md with actual build/test/lint commands
- Updating settings.json permissions for the actual package manager
- Updating rule paths to match actual directories
- Detecting and enabling the project's formatter
- Final review pass

## Rules

- NEVER delete files without confirming with the user first
- Present recommendations clearly — mark recommended items with "(Recommended)"
- If detection is uncertain, ask the user rather than guessing
- If the project is empty (no source files), inform the user and keep all defaults
- Always complete all phases — don't stop early
