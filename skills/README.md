# Skills

Auto-triggering Claude Code skills -- Claude decides when to invoke each based on context. You can also invoke any skill manually with `/name`.

## Core Setup Skills (2)

| Skill | Description |
|-------|-------------|
| `/init` | Initialize ferclaudeobs for a new project -- check plugins, detect project type, select configs, customize for tech stack |
| `/setup` | Scan the project codebase and customize all .claude/ config files to match the actual tech stack |

## Obsidian Vault Skills (11)

| Skill | Description |
|-------|-------------|
| `/setup-vault` | Initialize Obsidian vault structure from domain pack |
| `/process-docs` | Run document pipeline (convert, extract, link, tag, file, validate) |
| `/claude-ingest` | **The definitive ingestion skill.** Claude vision PDF conversion (preserving tables), Chinese auto-translation, scanned PDF OCR, entity extraction, wikilinks, vault filing. Supersedes /ingest and /pdf-to-markdown. |
| `/ingest` | Legacy per-document pipeline (pymupdf-based, no table preservation). Use `/claude-ingest` instead. |
| `/vault-search` | Search vault by keyword, entity, or filename |
| `/vault-health` | Validate vault integrity, auto-fix issues |
| `/create-entity` | Create entity notes from domain pack templates |
| `/vault-stats` | Vault statistics and metrics |
| `/query-notebook` | Query NotebookLM notebooks for insights |
| `/push-notebook` | Push vault content to NotebookLM with privacy enforcement |
| `/analyze-topic` | Multi-source research synthesis with attribution |
| `/weekly-brief` | Generate intelligence briefings from vault content |

## Development Skills (9)

| Skill | Description |
|-------|-------------|
| `/debug-fix` | Find and fix bugs -- understand, reproduce, investigate, fix, verify, commit |
| `/ship` | Stage, commit, push, PR with confirmation at each step |
| `/hotfix` | Emergency production fix -- create hotfix branch, minimal change, ship fast |
| `/pr-review` | Review PR with specialist agents (code, security, performance, docs) |
| `/tdd` | Red-green-refactor TDD loop with commits after each cycle |
| `/explain` | Explain code with summary, mental model, ASCII diagram, modification guide |
| `/refactor` | Safe refactoring with tests as safety net, small testable steps |
| `/test-writer` | Write comprehensive tests for every code path: happy, edge, error, concurrency |
| `/parallel` | Decompose complex tasks and dispatch multiple agents in parallel |

## Adding Your Own

Create a directory with a `SKILL.md` file:

```
your-skill/
└── SKILL.md
```

```yaml
---
name: your-skill
description: What it does and when to use it
---

Your instructions here. Use $ARGUMENTS for user input.
```

See [Claude Code docs](https://code.claude.com/docs/en/skills) for all frontmatter options.
