---
name: vault-health
description: Run vault validation checks and report on broken links, orphaned notes, missing frontmatter, and overall vault quality.
argument-hint: "[optional: --fix to auto-fix simple issues]"
---

Check the health of the Obsidian vault.

## Step 1: Run Validator

```bash
python scripts/validate_vault.py
```

## Step 2: Read Report

Read the generated health report from `vault/11 - INTELLIGENCE & ANALYSIS/vault_health_report.md`.

## Step 3: Augment with Statistics

Calculate additional stats using Grep/Glob:
- Total .md files in vault (excluding _TEMPLATES)
- Notes by type (grep for `type:` in frontmatter)
- Entity coverage: entities in registry vs entities with vault notes
- Wikilink count (grep for `\[\[` patterns)

## Step 4: Auto-Fix (if --fix)

If `$ARGUMENTS` contains `--fix`:
- Create stub notes for broken wikilink targets (minimal frontmatter + placeholder body)
- Add missing frontmatter to notes that lack it: `python scripts/add_frontmatter.py --all`
- Rebuild MOC indexes: `python scripts/build_mocs.py`

## Step 5: Present Results

Show the health report with severity tiers and actionable recommendations.
