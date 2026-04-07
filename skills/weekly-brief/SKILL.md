---
name: weekly-brief
description: Generate a weekly intelligence briefing from all notes added or modified in the past 7 days, synthesizing trends and key developments.
argument-hint: "[optional: number of days to cover, default 7]"
---

Generate an intelligence briefing.

## Step 1: Find Recent Notes

Parse `$ARGUMENTS` for number of days (default 7).

Use Bash to find recently modified vault notes:
```bash
find vault/ -name "*.md" -mtime -7 -not -path "*/._*" -not -path "*/_TEMPLATES/*" -not -path "*/.obsidian/*"
```

## Step 2: Read and Categorize

For each recent note:
1. Read its frontmatter (type, tags, category)
2. Read its first paragraph and any Executive Summary section
3. Group notes by domain folder (01-11)

## Step 3: Synthesize Brief

Use the Weekly-Brief template from the active domain pack.
Fill in each section:
- **Top Stories** — Most significant developments (notes with type=regulation or high-impact changes)
- **Market Movements** — Price and market data (from analysis and market notes)
- **Regulatory Updates** — New regulations or policy changes
- **Competitor Activity** — Competitor-related notes
- **Supplier Intelligence** — Supplier updates
- **Project Updates** — Project status changes
- **Risk Flags** — Notes with confidence=low or risk-related content
- **Looking Ahead** — Upcoming events, deadlines, or expected developments
- **New Notes Added** — List of all new notes with [[wikilinks]]

## Step 4: Create and File

Save the brief to `vault/11 - INTELLIGENCE & ANALYSIS/Weekly Briefs/Weekly Brief — <date>.md`

## Step 5: Link

```bash
python scripts/inject_links.py --file="<brief path>"
python scripts/build_mocs.py
```

Present the brief to the user.
