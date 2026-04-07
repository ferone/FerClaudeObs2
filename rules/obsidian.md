---
paths:
  - "vault/**"
  - "scripts/*.py"
  - "domain-packs/**"
  - "config/**"
  - "inbox/**"
---

# Obsidian Vault Interaction Rules

## Frontmatter Requirements

Every vault note MUST have a YAML frontmatter block with at minimum:
- `title` — note title (string)
- `type` — one of: company, regulation, technology, project, person, analysis, brief, supplier, concept, document, moc, dashboard
- `tags` — list of tags
- `date_created` — ISO date (YYYY-MM-DD)
- `date_modified` — ISO date (YYYY-MM-DD), always update on edit
- `status` — one of: active, archived, draft, verified
- `confidence` — one of: high, medium, low (optional, default medium)

## Wikilink Conventions

- Link entity names on FIRST meaningful occurrence only per document
- Use alias syntax for abbreviations: `[[NGCP|National Grid Corporation of the Philippines]]`
- Never link inside: code blocks, URLs, existing links, frontmatter, images
- Never link generic words: grid, power, energy, system, market, data, project, analysis
- Sort entity matches longest-first to avoid partial matches (e.g., "Solar Philippines" before "Solar")

## Privacy Zones

Read `domain-packs/[active-pack]/pack.json` for privacy zone definitions. Enforce:
- Paths marked `"external_api": false` — NEVER send content to external APIs (Claude, Gemini, NotebookLM)
- Paths marked `"external_api": "approval_required"` — require explicit user confirmation per session
- When running enrichment or NotebookLM push, always check privacy zones first

## Vault Structure

- `_INBOX/` is a temporary staging area — the pipeline moves notes to correct folders
- `00 - HOME/` contains ONLY MOC files and HOME.md — never put regular notes here
- `_TEMPLATES/` contains note templates — never modify without explicit user instruction
- `_ASSETS/` stores images, PDFs, and charts — never store markdown here

## Template Usage

- New entity notes MUST use the template from the active domain pack's templates/ directory
- Templater placeholders use `{{title}}`, `{{date}}` syntax
- Templates are copied to `vault/_TEMPLATES/` during vault setup

## Domain Pack Awareness

- Always read `config/active-pack.json` before any vault operation to identify the active domain pack
- Load entity lists, folder mappings, and templates from the pack directory
- Never hardcode domain-specific values — always read from the pack

## Pipeline Scripts

- Python scripts in `scripts/` are the muscle — Claude Code skills orchestrate them
- Always run scripts via `python scripts/[name].py` with appropriate flags
- Check script exit codes — 0 is success, non-zero is failure
- Read `logs/pipeline.log` for detailed operation logs after running scripts
