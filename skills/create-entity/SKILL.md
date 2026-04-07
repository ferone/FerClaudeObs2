---
name: create-entity
description: Create a new entity note from the appropriate template, add it to the entity registry, and update wikilinks across the vault.
argument-hint: "[entity name] [optional: --type=company|regulation|technology|project|supplier]"
---

Create a new entity note in the vault.

## Step 1: Parse Arguments

Extract from `$ARGUMENTS`:
- Entity name (required)
- `--type`: Entity type (optional — infer if not provided)

## Step 2: Determine Type

If type not provided, try to infer:
1. Check if the name matches any entity in `config/entity_registry_extracted.json` — use its category
2. Read `domain-packs/[active-pack]/pack.json` type_inference_patterns
3. If still unclear, ask the user to choose

## Step 3: Load Template

Read the appropriate template from the active domain pack's `templates/` directory:
- company → Company.md
- regulation → Regulation.md
- technology → Technology.md
- project → Project.md
- supplier → Supplier.md
- analysis → Analysis.md
- brief → Weekly-Brief.md

Fill in `{{title}}` with the entity name and `{{date}}` with today's date.

## Step 4: Determine Target Folder

Read `domain-packs/[active-pack]/vault-structure.json` and use the `type_to_folder` mapping.

## Step 5: Write the Note

Create the note at `vault/[target-folder]/[entity-name].md`.

## Step 6: Update Entity Registry

Add the entity to `config/entity_registry_extracted.json` if not already present.

## Step 7: Update Links and MOCs

```bash
python scripts/inject_links.py --all
python scripts/build_mocs.py
```

## Step 8: Confirm

Tell the user: "Created [entity name] ([type]) at vault/[path]. Updated links and MOC indexes."
