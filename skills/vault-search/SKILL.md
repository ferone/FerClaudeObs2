---
name: vault-search
description: Search across the Obsidian vault using keyword matching, frontmatter queries, and entity registry lookup. Returns relevant notes with context.
argument-hint: "[search query — entity name, topic, or question]"
---

Search the vault for information about a topic or entity. This is a pure Claude orchestration skill — no Python scripts needed.

## Step 1: Parse Query

Extract the search query from `$ARGUMENTS`.

## Step 2: Parallel Search

Run these searches simultaneously:

1. **Keyword search**: Use Grep to search `vault/` for the query term in .md files
2. **Entity registry search**: Read `config/master_linklist.json` and `config/entity_registry_extracted.json` — look for entities matching or containing the query
3. **Filename search**: Use Glob to find vault files whose names match the query

## Step 3: Rank Results

Priority order:
1. Exact entity name match (entity note exists)
2. Title/filename match
3. Content match (keyword in body)
4. Alias match (entity aliases contain query)

## Step 4: Present Results

For the top 5 results:
- Read the file's frontmatter + first 500 characters of body
- Extract any paragraphs that mention the query term
- List backlinks (other notes that link TO this note via [[wikilinks]])

Present as a structured report with note paths, types, and relevance snippets.

## Step 5: Suggest Next Steps

- "Want me to analyze this topic in depth? Try /analyze-topic [topic]"
- "Want to create a new entity note? Try /create-entity [name]"
