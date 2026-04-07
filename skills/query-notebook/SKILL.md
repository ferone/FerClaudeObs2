---
name: query-notebook
description: Query a NotebookLM notebook and bring synthesized insights back into the Obsidian vault as a new note.
argument-hint: "[question to ask NotebookLM] [optional: --notebook=name]"
---

Query NotebookLM for insights and create a vault note from the response.

## Step 1: Check NotebookLM Setup

Verify `notebooklm-py` is installed:
```bash
python -c "import notebooklm; print('OK')"
```

If not installed, tell the user: "Install with: pip install 'notebooklm-py[browser]' && playwright install chromium"

## Step 2: Select Notebook

Read `config/notebook_registry.json` (or `domain-packs/[active-pack]/notebooks.json` if registry doesn't exist).

If `$ARGUMENTS` contains `--notebook=name`, use that. Otherwise, present available notebooks and ask user to choose.

## Step 3: Execute Query

```bash
python scripts/notebooklm_bridge.py query --notebook="<name>" --question="<question>"
```

## Step 4: Create Vault Note

Parse the JSON response and create a new note in `vault/11 - INTELLIGENCE & ANALYSIS/` with:
- Title: The question
- Frontmatter: type=analysis, source=notebooklm:[notebook name], confidence=medium
- Body: The synthesized response
- Related Topics section with [[wikilink]] suggestions

## Step 5: Inject Links

```bash
python scripts/inject_links.py --file="<new note path>"
```

Report the created note path to the user.
