---
name: analyze-topic
description: Deep analysis on a topic by aggregating vault notes, entity connections, and optionally NotebookLM insights into a comprehensive analysis note.
argument-hint: "[topic or question to analyze]"
---

Perform deep multi-source analysis on a topic.

## Step 1: Gather from Vault

Use vault-search approach:
1. Grep vault/ for the topic
2. Check entity registries for related entities
3. Read matching notes — extract key insights, facts, and data points

## Step 2: Gather from NotebookLM (optional)

If `config/notebook_registry.json` exists and has notebooks:
- Identify which notebook is most relevant to the topic
- Query it: `python scripts/notebooklm_bridge.py query --notebook="<best>" --question="<topic>"`
- Parse the response

## Step 3: Synthesize Analysis

Create a comprehensive analysis note with these sections:
- **Executive Summary** — 3-5 sentence overview
- **Background** — Context and history from vault notes
- **Key Findings** — Numbered findings with source attribution
- **Implications** — What this means strategically
- **Risks & Uncertainties** — What could go wrong
- **Recommendations** — Actionable next steps
- **Sources** — List of vault notes and NotebookLM notebooks consulted

## Step 4: Create Note

Use the Analysis template from the active domain pack.
Save to `vault/11 - INTELLIGENCE & ANALYSIS/Market Reports/`.
Add proper frontmatter with type=analysis, today's date, and source references.

## Step 5: Link and Index

```bash
python scripts/inject_links.py --file="<new note>"
python scripts/build_mocs.py
```

Present the analysis to the user.
