# Agents

Agents are specialized Claude instances that work as a **coordinated team**. They communicate via `SendMessage` to share findings, flag cross-cutting issues, and avoid duplicated work.

Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json (already configured).

Claude delegates to agents automatically based on the task description, or you can invoke them with `@agent-name`.

## Code Review Team (4)

### code-reviewer
General code review with specific bug patterns to catch: off-by-one errors, null dereferences, inverted conditions, race conditions, swallowed errors, misleading names, excessive complexity. Routes auth issues to `@security-reviewer` and perf issues to `@performance-reviewer`. Synthesizes findings from the full team.

### security-reviewer
Reviews code for OWASP-style vulnerabilities: injection, broken auth, data exposure, weak crypto, missing validation. Reports findings by severity with exact file:line locations and specific fixes. Shares critical findings with `@code-reviewer`.

### performance-reviewer
Finds real bottlenecks -- not theoretical micro-optimizations. Covers database (N+1, missing indexes), memory (leaks, unbounded caches), computation (repeated work, blocking calls), network (sequential calls, missing timeouts), frontend (re-renders, bundle size), and concurrency (lock contention, missing pooling). Flags security-sensitive perf fixes for `@security-reviewer`.

### doc-reviewer
Reviews documentation for accuracy (do docs match code?), completeness (are required params documented?), staleness (do referenced APIs still exist?), and clarity. Cross-references with `@code-reviewer` findings.

## Vault Operations Team (8)

### doc-inspector
Compares a source document (PDF/HTML) against its vault markdown note to verify completeness and accuracy. Identifies missing sections, truncated content, formatting errors, and data loss. Reports PASS/FAIL/PARTIAL verdict with specific page-level findings. Launch one inspector per document for parallel quality checks. Reports to `@vault-orchestrator`.

### chinese-translator
Translates Chinese PDF/document content into complete English markdown for the vault. Handles one document or one page range per instance — launch multiple agents in parallel for batch translation or to split large documents. Includes a comprehensive energy/battery/Philippine-specific glossary for consistent technical terminology. Reports entity candidates found during translation to `@entity-manager` via SendMessage.

### vault-orchestrator
Coordinates multi-step vault operations -- dispatches specialized agents, manages pipeline sequences (convert, extract, enrich, link, tag, mocs, validate), and synthesizes results. Reads domain pack config before every run. Dispatches `@entity-manager`, `@doc-enricher`, `@vault-validator`, `@notebooklm-bridge`, and `@research-synthesizer`.

### entity-manager
Manages entity extraction, deduplication, registry updates, and stub note creation. Maintains `entity_registry_extracted.json` and `master_linklist.json`. Resolves naming conflicts and creates vault notes for high-frequency entities. Reports findings to `@vault-orchestrator` and coordinates with `@doc-enricher` and `@notebooklm-bridge`.

### doc-enricher
Enhances vault documents with AI-powered restructuring and improved metadata. Has strict privacy guardrails -- checks every file path against domain pack privacy zones before processing. Defaults to local Ollama; only uses external APIs with explicit approval. Reports enriched files to `@vault-orchestrator` and new entities to `@entity-manager`.

### vault-validator
Runs comprehensive vault health checks -- broken links, orphaned notes, frontmatter validation, structural integrity. Can auto-fix simple issues (stub notes, missing frontmatter, date formatting). Reports health scores to `@vault-orchestrator` and missing entities to `@entity-manager`.

### notebooklm-bridge
Handles bidirectional communication with Google NotebookLM -- querying notebooks for insights and pushing curated vault content. Enforces privacy zones on all push operations. Reports query results to `@research-synthesizer` or `@vault-orchestrator` and new entities to `@entity-manager`.

### research-synthesizer
Synthesizes research across vault notes, NotebookLM insights, and web search into coherent analysis documents with proper attribution. Follows a structured output format (executive summary, findings, implications, risks, recommendations). Requests NotebookLM queries from `@notebooklm-bridge` and entity info from `@entity-manager`.

## Utility (2)

### frontend-designer
Creates distinctive, production-grade UI. Finds or creates design tokens first, picks a design principle, then builds components. Has Write/Edit tools so it actually generates files. Anti-AI-slop aesthetics built in. After generating code, requests `@code-reviewer` for quality checks.

### parallel-executor
General-purpose worker agent for parallel task execution. Handles independent subtasks assigned by the `/parallel` skill and reports results back to the orchestrator.

## Team Communication

Agents communicate via `SendMessage`:
- Each agent has `SendMessage` in its tools list
- Agents flag cross-cutting issues for the relevant specialist (e.g., code-reviewer flags auth issues for security-reviewer)
- The orchestrating agent collects and synthesizes all findings
- Agents deduplicate -- if another agent already flagged something, they reference it instead of repeating

## Adding Your Own

Create a new `.md` file in this directory:

```yaml
---
name: your-agent-name
description: When Claude should delegate to this agent
tools:
  - Read
  - Grep
  - Glob
  - Bash
  - SendMessage
---

Your agent's system prompt here.

## Team Coordination

Document how this agent interacts with other agents in the team.
```

See [Claude Code docs](https://code.claude.com/docs/en/sub-agents) for all frontmatter options.
