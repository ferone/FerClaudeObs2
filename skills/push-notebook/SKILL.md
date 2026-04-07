---
name: push-notebook
description: Push curated vault content to a NotebookLM notebook for deep analysis and artifact generation.
argument-hint: "[vault folder or note paths to push] [optional: --notebook=name]"
---

Push vault content to NotebookLM.

## Step 1: Parse Paths

Extract vault paths from `$ARGUMENTS`. Can be:
- A folder path (e.g., "vault/05 - TECHNOLOGIES/BESS")
- Specific note paths (e.g., "vault/03 - REGULATIONS/RA 9513.md")

## Step 2: Privacy Check

Read `domain-packs/[active-pack]/pack.json` privacy_zones.
For each path being pushed:
- If it matches a `"external_api": false` zone → REFUSE and explain why
- If it matches a `"external_api": "approval_required"` zone → ask for explicit confirmation

## Step 3: Select Notebook

Read `config/notebook_registry.json`. Select target notebook from `$ARGUMENTS` or ask user.

## Step 4: Confirm

Show the user:
- Number of notes to push
- Target NotebookLM notebook
- Warning: "Content will be sent to Google servers"
Ask for confirmation.

## Step 5: Push

```bash
python scripts/notebooklm_bridge.py push --notebook="<name>" --paths="<paths>"
```

## Step 6: Update Registry

Update `config/notebook_registry.json` with `last_synced` timestamp.

Report results to the user.
