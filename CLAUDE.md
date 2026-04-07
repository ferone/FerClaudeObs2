# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

ferclaudeobs is a portable Claude Code configuration system and Obsidian knowledge management platform. It bundles rules, skills, agents, hooks, settings, and a curated set of 30+ plugins into a single `.claude/` folder you can drop into any project. Clone once, run `/init`, and get a fully configured Claude Code environment on any machine.

The system transforms raw documents (PDFs, DOCX, HTML) dropped into `inbox/` into a connected Obsidian vault with entity extraction, wikilinks, frontmatter metadata, and Map of Content indexes.

## Architecture

Two layers work together:

1. **Claude Code orchestration** — Skills (`skills/*/SKILL.md`) invoke agents (`agents/*.md`) which coordinate via `SendMessage`. Rules (`rules/*.md`) constrain behavior. Hooks (`hooks/*.sh`) enforce safety at the tool-call level.
2. **Python document pipeline** — 12 scripts in `scripts/` handle document conversion, entity extraction, linking, tagging, MOC building, and validation. Orchestrated by `scripts/pipeline.py`.

The domain pack at `domain-packs/[name]/` drives everything: entity definitions, folder structure, privacy zones, AI prompts, and note templates. `config/active-pack.json` points to the active pack — all scripts and skills read this at startup.

### Pipeline Flow

```
inbox/ → convert_docs.py → vault/_INBOX/ → extract_entities.py → enrich_notes.py (optional)
→ inject_links.py → add_frontmatter.py → build_mocs.py → validate_vault.py → vault/
```

Full pipeline: `python scripts/pipeline.py --mode=full`
Single step: `python scripts/pipeline.py --mode=convert|extract|enrich|link|tag|mocs|validate|brief`
Single file: `python scripts/pipeline.py --mode=convert --file=inbox/my-report.pdf`
With enrichment: `python scripts/pipeline.py --mode=full --with-enrich`

Or use the skill: `/claude-ingest --source=<file|folder>` (recommended), `/process-docs`, `/process-docs --mode=extract`

### Dual Engine System

- **`--engine=claude-code`** (default): Claude reads and processes documents directly. Best quality.
- **`--engine=python`**: Python scripts use Ollama or LM Studio for local AI. Better for batch/offline processing.

Confidential files (privacy zones) always use the local engine regardless of the primary engine setting. See `pack.json` `processing` section.

## Privacy Zones

Privacy levels are defined per domain pack in `pack.json`. Example from the included `philenergy` pack:

| Path | Level | External API |
|------|-------|-------------|
| `10 - VIVANT INTERNAL` | confidential | **Never** — no external API calls |
| `08 - COMPETITORS` | sensitive | Approval required per session |
| `13 - ENGINEERING & TECHNICAL` | sensitive | Approval required per session |

**Always** check privacy zones before sending vault content to any external API. The `vault-protect.sh` hook enforces this at the tool level.

## Python Dependencies

```bash
pip install -r requirements.txt
```

Key libraries: `mammoth` (DOCX→MD), `pymupdf4llm` (PDF→MD), `python-frontmatter`, `anthropic`, `notebooklm-py`, `rich`, `click`

## Repository Layout

The repo is **flat on purpose**: `CLAUDE.md` is meant for the project root, while everything else (`rules/`, `skills/`, `agents/`, `hooks/`, `settings.json`, `plugins.json`, `scripts/`) goes inside `.claude/`. The copy commands in README.md handle the separation. Do not nest these under a `.claude/` directory here.

## Conventions

- **Rules** (`rules/*.md`): Must have `alwaysApply: true` or `paths:` frontmatter. Don't duplicate what hooks enforce or what Claude knows natively.
- **Skills** (`skills/*/SKILL.md`): Must have `name`, `description` in frontmatter. All skills auto-trigger — Claude decides when to invoke them based on context. No `disable-model-invocation: true`.
- **Agents** (`agents/*.md`): Must have `name`, `description`, `tools` (including `SendMessage`) in frontmatter. Never set `model` — users choose their own. Agents work as coordinated teams, not in isolation.
- **Hooks** (`hooks/*.sh`): Must start with `#!/bin/bash`, check for `jq` availability, use proper exit codes (0=allow, 2=block). PreToolUse hooks observe/block only — never modify files.
- **Naming**: kebab-case everywhere — `debug-fix/`, `code-reviewer.md`, `block-dangerous-commands.sh`.

## Key Design

- **Plugin-inclusive**: 30+ curated plugins bundled via `plugins.json`. Install scripts in `scripts/` handle setup on any new machine.
- **Auto-triggering skills**: All skills auto-trigger when Claude detects the right context. No manual-only restrictions.
- **Agent teams**: Agents coordinate via `SendMessage` — they share findings, flag cross-cutting issues, and deduplicate work. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (configured in settings.json).
- **Framework-agnostic templates**: Never hardcode `npm`/`pnpm`/`yarn` or specific libraries. `/setup` handles project-specific customization at runtime.
- **Token consciousness**: Every line in `alwaysApply: true` rules costs tokens every turn. Path-scoped rules only cost when working near matched files.

## Workflow

- After adding a new file to `rules/`, `skills/`, `agents/`, or `hooks/`, update both the README.md in that subdirectory and the structure tree in the root README.md.
- After adding a new plugin, update `plugins.json` with the plugin identifier.
- One change per PR — don't bundle a new skill with a rule fix with a README update.
- Hook scripts must exit 0 if dependencies (like `jq`) are missing — never block the user.
- Test hook scripts with sample JSON input before committing.

## Obsidian Knowledge Management

This system supports Obsidian vault projects for document intelligence. When a project contains `vault/`, `domain-packs/`, `scripts/pipeline.py`, and `config/active-pack.json`, it's an Obsidian knowledge management project.

### Domain Pack System
- Domain packs live in `domain-packs/[name]/` with `pack.json`, `entities.json`, `vault-structure.json`, templates, and prompts
- `config/active-pack.json` points to the active pack — all scripts read this at startup
- Create new domain packs for different use cases (legal, company intel, research)

### Key Skills
- `/setup-vault` — Initialize vault from domain pack
- `/claude-ingest` — **The definitive ingestion skill.** Claude vision PDF conversion (tables preserved), Chinese auto-translation, scanned PDF OCR, entity extraction, wikilinks, vault filing
- `/process-docs` — Batch document pipeline (convert → extract → link → tag → file → validate)
- `/vault-search` — Search vault by keyword, entity, or filename
- `/vault-health` — Validate vault integrity
- `/create-entity` — Create entity notes from templates
- `/query-notebook` — Query NotebookLM notebooks
- `/push-notebook` — Push vault content to NotebookLM
- `/analyze-topic` — Multi-source research synthesis
- `/weekly-brief` — Generate intelligence briefings
- `/vault-stats` — Vault statistics and metrics

### Key Agents
- `chinese-translator` — Chinese-to-English document translation with domain glossary
- `doc-inspector` — Verifies document conversion completeness (PDF/HTML vs vault markdown)
- `vault-orchestrator` — Coordinates multi-step vault operations
- `entity-manager` — Entity extraction and registry management
- `doc-enricher` — AI document enhancement with privacy controls
- `vault-validator` — Health checks and auto-fixes
- `notebooklm-bridge` — Bidirectional NotebookLM integration
- `research-synthesizer` — Cross-source research synthesis

## Don'ts

- Don't add project scaffolding skills — this is for daily work, not project creation.
- Don't add vendor-specific configurations (CI providers, cloud platforms).
- Don't duplicate content across rules, hooks, and skills.
- Don't modify generated files (`*.gen.ts`, `*.generated.*`).
- Don't add `disable-model-invocation: true` to skills — all skills must auto-trigger.
- Don't create agents without `SendMessage` in their tools — agents must be team-aware.
- Don't send confidential zone content to external APIs without explicit user approval.
