# ferclaudeobs

A portable Claude Code configuration system **and** Obsidian knowledge management platform. 30+ curated plugins, 22 auto-triggering skills, 14 coordinated agents, and a full document intelligence pipeline for Obsidian vaults.

## Why This Exists

Setting up Claude Code from scratch on a new machine or project means reconfiguring plugins, skills, agents, hooks, and rules every time. And if you manage knowledge in Obsidian, there is no turnkey system for automated document processing, entity extraction, or cross-source research with Claude Code.

ferclaudeobs solves both problems. Clone it, run the install script, and you get:

- **For development projects**: A fully configured Claude Code environment with code review agents, TDD workflows, shipping automation, and safety hooks.
- **For knowledge management projects**: An Obsidian vault intelligence system with domain packs, document pipelines, entity extraction, NotebookLM integration, and research synthesis.

## Obsidian Knowledge Management

ferclaudeobs includes a full document intelligence system for Obsidian vault projects. It turns an Obsidian vault into a structured knowledge base with automated document processing, entity extraction, and cross-source research.

### Domain Pack System

Domain packs (`domain-packs/[name]/`) define how a vault is organized for a specific use case. Each pack contains:

- **`pack.json`** -- Pack metadata, privacy zones, pipeline configuration
- **`entities.json`** -- Entity types and extraction rules (people, companies, contracts, etc.)
- **`vault-structure.json`** -- Folder structure and automatic filing rules
- **`templates/`** -- Markdown templates for each entity type
- **`prompts/`** -- AI prompts for document enrichment and extraction

`config/active-pack.json` points to the active pack. All scripts and skills read this at startup. Create new domain packs for different use cases (legal, company intel, research, etc.).

### Vault Skills

| Command | Description |
|---------|-------------|
| `/setup-vault` | Initialize vault structure from the active domain pack |
| `/process-docs` | Run the full document pipeline: convert, extract, link, tag, file, validate |
| `/vault-search` | Search vault by keyword, entity, or filename |
| `/vault-health` | Validate vault integrity (broken links, orphans, frontmatter) |
| `/create-entity` | Create entity notes from domain pack templates |
| `/vault-stats` | Vault statistics and metrics |
| `/query-notebook` | Query NotebookLM notebooks |
| `/push-notebook` | Push vault content to NotebookLM with privacy enforcement |
| `/analyze-topic` | Multi-source research synthesis with attribution |
| `/weekly-brief` | Generate intelligence briefings from vault content |

### Vault Agents

| Agent | What It Does |
|-------|--------------|
| `@vault-orchestrator` | Coordinates multi-step vault operations and dispatches specialized agents |
| `@entity-manager` | Entity extraction, deduplication, and registry management |
| `@doc-enricher` | AI-powered document enhancement with strict privacy controls |
| `@vault-validator` | Broken links, orphaned notes, frontmatter validation, auto-fixes |
| `@notebooklm-bridge` | Bidirectional NotebookLM integration with privacy enforcement |
| `@research-synthesizer` | Combines vault, NotebookLM, and web sources into attributed analysis |

## Getting Started

### 1. One-command setup

Clones ferclaudeobs, copies all config into your project, and installs all plugins.

**macOS/Linux:**
```bash
cd your-project
bash <(curl -s https://raw.githubusercontent.com/ferone/ferclaudeobs/main/scripts/setup-project.sh)
```

**Windows (PowerShell):**
```powershell
cd your-project
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/ferone/ferclaudeobs/main/scripts/setup-project.ps1" -OutFile "$env:TEMP\setup-ferclaudeobs.ps1"; powershell -ExecutionPolicy Bypass -File "$env:TEMP\setup-ferclaudeobs.ps1"
```

**Or run locally** (if you already have ferclaudeobs cloned):
```bash
bash /path/to/ferclaudeobs/scripts/setup-project.sh /path/to/your-project
```

<details>
<summary>Manual setup (step by step)</summary>

```bash
git clone https://github.com/ferone/ferclaudeobs.git /tmp/ferclaudeobs

cd your-project
mkdir -p .claude

cp /tmp/ferclaudeobs/settings.json .claude/
cp -r /tmp/ferclaudeobs/{rules,skills,agents,hooks,scripts} .claude/
cp /tmp/ferclaudeobs/plugins.json .claude/
cp /tmp/ferclaudeobs/.gitignore .claude/
cp /tmp/ferclaudeobs/CLAUDE.md ./
cp /tmp/ferclaudeobs/CLAUDE.local.md.example ./

chmod +x .claude/hooks/*.sh .claude/scripts/*.sh
rm -rf /tmp/ferclaudeobs

echo "CLAUDE.local.md" >> .gitignore

# Install plugins (once per machine)
bash .claude/scripts/install-plugins.sh
```
</details>

### 2. Restart Claude Code

Exit and restart your Claude Code session. Skills, agents, and rules are loaded at session start.

### 3. Run `/init`

```
/init
```

This will:
- Verify plugins are installed
- Detect your project's tech stack (language, framework, linter, test runner)
- Detect Obsidian vault indicators and recommend vault-specific configs
- Let you choose which rules, agents, and hooks to enable for this project
- Clean up README files that waste tokens
- Delegate to `/setup` to customize configs for your actual tech stack

Every change is confirmed with you before it's applied.

### Troubleshooting

| Problem | Fix |
|---------|-----|
| Skills or agents not showing up | **Restart Claude Code** -- loaded at session start |
| Hooks not running | Run `chmod +x .claude/hooks/*.sh` and verify `jq` is installed |
| "jq not found" blocking everything | Install jq: `brew install jq` (macOS) or `apt install jq` (Linux) |
| format-on-save not formatting | Ensure the formatter binary is installed locally and its config file exists |
| Plugins not installing | Run `claude plugin list` to verify CLI is working, then retry install script |
| Agent teams not coordinating | Verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is in `.claude/settings.json` |
| `/init` asks to confirm settings.json edits | Expected -- `protect-files.sh` prompts for confirmation when editing settings |

### 4. Make it yours

`/init` + `/setup` gets you 90% of the way. To fine-tune:

- **`rules/code-quality.md`** -- update naming conventions to match your team's style
- **`rules/frontend.md`** -- pick your design principle, highlight your component framework
- **`rules/security.md`** -- add paths specific to your project's sensitive areas
- **`rules/obsidian.md`** -- customize vault interaction rules for your domain pack
- **`CLAUDE.md`** -- add architectural decisions, domain knowledge, workflow quirks
- **`CLAUDE.local.md`** -- rename the `.example` file for personal preferences (gitignored)
- **`plugins.json`** -- add or remove plugins for your workflow

## Skills (Auto-Triggering)

All skills auto-trigger when Claude detects the right context. You can also invoke any skill manually with `/name`.

### Core Setup Skills

| Command | When It Auto-Triggers | Description |
|---------|----------------------|-------------|
| `/init` | Setting up a new project with ferclaudeobs | Check plugins, detect project type, select configs, customize for tech stack |
| `/setup` | After /init, or when .claude/ config needs updating | Scan codebase, customize all config files to match actual tech stack |

### Obsidian Vault Skills

| Command | When It Auto-Triggers | Description |
|---------|----------------------|-------------|
| `/setup-vault` | Initializing an Obsidian vault project | Initialize vault structure from domain pack |
| `/process-docs` | Documents need processing through the pipeline | Run document pipeline (convert, extract, link, tag, file, validate) |
| `/ingest` | Importing documents from external sources | Per-document pipeline with Chinese auto-translation, flexible input (file/folder/tree), batch summaries |
| `/vault-search` | Searching for vault content | Search vault by keyword, entity, or filename |
| `/vault-health` | Checking vault integrity | Validate vault integrity, auto-fix issues |
| `/create-entity` | Creating new entity notes | Create entity notes from domain pack templates |
| `/vault-stats` | Reviewing vault metrics | Vault statistics and metrics |
| `/query-notebook` | Querying NotebookLM | Query NotebookLM notebooks for insights |
| `/push-notebook` | Pushing content to NotebookLM | Push vault content to NotebookLM with privacy enforcement |
| `/analyze-topic` | Researching a topic across sources | Multi-source research synthesis with attribution |
| `/weekly-brief` | Generating periodic briefings | Generate intelligence briefings from vault content |

### Development Skills

| Command | When It Auto-Triggers | Description |
|---------|----------------------|-------------|
| `/debug-fix` | Debugging bugs, errors, or issues | Find and fix bugs -- understand, reproduce, investigate, fix, verify, commit |
| `/ship` | Work is ready to commit and push | Scan, stage, commit, push, PR with confirmation at each step |
| `/hotfix` | Emergency production fix needed | Create `hotfix/` branch, minimal change, critical tests, ship with `[HOTFIX]` label |
| `/pr-review` | Reviewing code changes or PRs | Delegate to agent team (code, security, performance, docs), synthesize unified report |
| `/tdd` | Building features test-first | Red-green-refactor loop with commits after each cycle |
| `/explain` | Explaining code or concepts | One-sentence summary, mental model, ASCII diagram, modification guide |
| `/refactor` | Refactoring code | Safe refactoring with tests as safety net, small testable steps |
| `/test-writer` | New features added | Comprehensive tests for every code path: happy, edge, error, concurrency |
| `/parallel` | Complex tasks with independent components | Decompose task, dispatch multiple agents in parallel, synthesize results |

## Agents (Coordinated Teams)

Agents work as a **coordinated team** -- they communicate via `SendMessage` to share findings, flag cross-cutting issues, and avoid duplicated work. Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (configured in settings.json).

### Code Review Team

| Agent | When It's Used | What It Does |
|-------|---------------|--------------|
| `@code-reviewer` | Auto-delegated for code changes | Reviews for correctness, error handling, complexity. Routes auth issues to `@security-reviewer`, perf issues to `@performance-reviewer`. |
| `@security-reviewer` | Auto-delegated when security-related code changes | OWASP vulnerability analysis. Shares critical findings with `@code-reviewer`. |
| `@performance-reviewer` | Auto-delegated for performance-sensitive code | Finds real bottlenecks (N+1, memory leaks, blocking I/O). Flags security-sensitive fixes for `@security-reviewer`. |
| `@doc-reviewer` | Auto-delegated when docs change | Reviews accuracy by cross-referencing code. Syncs with `@code-reviewer` findings. |

### Vault Operations Team

| Agent | When It's Used | What It Does |
|-------|---------------|--------------|
| `@chinese-translator` | Auto-delegated when Chinese documents are detected | Translates Chinese PDFs/docs to English markdown with energy/battery/PH glossary. Parallel page-range splitting for large docs. |
| `@vault-orchestrator` | Auto-delegated for multi-step vault operations | Coordinates pipeline sequences, dispatches specialized agents, synthesizes results. |
| `@entity-manager` | Auto-delegated for entity extraction tasks | Manages entity registry, deduplication, stub note creation, and naming conflicts. |
| `@doc-enricher` | Auto-delegated for document enhancement | AI-powered restructuring with strict privacy controls. Defaults to local Ollama. |
| `@vault-validator` | Auto-delegated for vault health checks | Broken links, orphaned notes, frontmatter validation, auto-fixes. |
| `@notebooklm-bridge` | Auto-delegated for NotebookLM operations | Queries notebooks and pushes vault content with privacy enforcement. |
| `@research-synthesizer` | Auto-delegated for cross-source research | Combines vault, NotebookLM, and web sources into attributed analysis documents. |

### Utility

| Agent | When It's Used | What It Does |
|-------|---------------|--------------|
| `@frontend-designer` | Auto-delegated when building UI | Creates distinctive, production-grade UI. Requests `@code-reviewer` after generating code. |
| `@parallel-executor` | Dispatched by `/parallel` skill | General-purpose worker for parallel subtask execution. |

### Using Agents Directly

```
@security-reviewer Review the auth middleware changes in src/middleware/auth.ts
```

```
@frontend-designer Build a dashboard page for the analytics module
```

```
@vault-orchestrator Process all documents in inbox/ through the full pipeline
```

## Plugins (30+)

All plugins are listed in `plugins.json` and installed via the install scripts. Plugins are user-level -- once installed on a machine, they work across all projects.

**Included**: superpowers, feature-dev, code-review, pr-review-toolkit, commit-commands, code-simplifier, frontend-design, impeccable, github, gitlab, linear, vercel, supabase, firebase, context7, firecrawl, playwright, chrome-devtools-mcp, huggingface-skills, typescript-lsp, pyright-lsp, security-guidance, skill-creator, claude-code-setup, claude-md-management, ralph-loop, playground, greptile, qodo-skills, explanatory-output-style, learning-output-style.

To add a plugin, add it to `plugins.json` and re-run the install script.

## Customization Guide

| Want to... | Do this |
|---|---|
| Add project-specific rules | Create `.claude/rules/your-rule.md` |
| Scope rules to file paths | Add `paths:` frontmatter to rule files |
| Add a team workflow | Create `.claude/skills/your-skill/SKILL.md` |
| Add a specialist agent | Create `.claude/agents/your-agent.md` (include `SendMessage` in tools) |
| Enforce behavior deterministically | Add a hook in `settings.json` |
| Override settings locally | Copy `settings.local.json.example` to `.claude/settings.local.json` |
| Personal CLAUDE.md overrides | Rename `CLAUDE.local.md.example` to `CLAUDE.local.md` |
| Add a new plugin | Add to `plugins.json` and re-run install script |
| Create a new domain pack | Copy an existing pack in `domain-packs/` and customize |

### Example: Project-specific rule

```yaml
---
paths:
  - "src/billing/**"
---

# Billing Module

- All monetary values use cents (integers), never floating point dollars
- Tax calculations must use the tax-engine service, never inline math
- Every billing mutation must be idempotent with a unique request ID
```

## What's Inside

```
ferclaudeobs/
├── CLAUDE.md                           # Template project instructions -> copy to YOUR project root
├── CLAUDE.local.md.example             # Personal overrides template -> copy and rename
├── CONTRIBUTING.md                     # Contribution guidelines
├── plugins.json                        # Plugin manifest -- all 30+ plugins to install
├── settings.json                       # Project settings -> copy to .claude/
├── settings.local.json.example         # Personal settings template
├── requirements.txt                    # Python dependencies for vault pipeline scripts
├── .gitignore                          # Gitignore for .claude/ directory
├── config/                             # Runtime configuration
│   └── active-pack.json                #   Points to the active domain pack
├── domain-packs/                       # Domain-specific knowledge configurations
│   └── [name]/                         #   One directory per domain pack
│       ├── pack.json                   #     Pack metadata, privacy zones, pipeline config
│       ├── entities.json               #     Entity definitions and extraction rules
│       ├── vault-structure.json        #     Vault folder structure and filing rules
│       ├── templates/                  #     Markdown templates for entity types
│       └── prompts/                    #     AI prompts for enrichment and extraction
├── scripts/                            # Setup, installation, and pipeline scripts
│   ├── setup-project.sh                #   One-command project setup (macOS/Linux)
│   ├── setup-project.ps1               #   One-command project setup (Windows)
│   ├── install-plugins.sh              #   Plugin-only installer (macOS/Linux)
│   ├── install-plugins.ps1             #   Plugin-only installer (Windows)
│   ├── pipeline.py                     #   Document processing pipeline orchestrator
│   ├── setup_vault.py                  #   Vault initialization from domain pack
│   ├── convert_docs.py                 #   Document format conversion
│   ├── extract_entities.py             #   Entity extraction from documents
│   ├── inject_links.py                 #   Wikilink injection into vault notes
│   ├── add_frontmatter.py              #   YAML frontmatter generation
│   ├── enrich_notes.py                 #   AI-powered note enrichment
│   ├── build_mocs.py                   #   Map of Content generation
│   ├── validate_vault.py               #   Vault integrity validation
│   └── notebooklm_bridge.py            #   NotebookLM API integration
├── rules/                              # Modular instructions -> copy to .claude/rules/
│   ├── code-quality.md                 #   Principles, naming, comments, markers, file organization
│   ├── testing.md                      #   Testing conventions (always loaded)
│   ├── database.md                     #   Migration safety rules (loads near migration files)
│   ├── error-handling.md               #   Error handling patterns (loads near backend files)
│   ├── security.md                     #   Security rules (loads near API/auth files)
│   ├── frontend.md                     #   Design tokens, principles, accessibility (loads near UI files)
│   └── obsidian.md                     #   Vault interaction rules (loads for Obsidian projects)
├── skills/                             # Auto-triggering slash commands -> copy to .claude/skills/
│   ├── init/SKILL.md                   #   /init -- project setup with config selection
│   ├── setup/SKILL.md                  #   /setup -- scan codebase, customize all config files
│   ├── debug-fix/SKILL.md              #   /debug-fix -- find and fix bugs from any source
│   ├── ship/SKILL.md                   #   /ship -- commit, push, PR with confirmations
│   ├── hotfix/SKILL.md                 #   /hotfix -- emergency production fix, ship fast
│   ├── pr-review/SKILL.md              #   /pr-review -- review via coordinated agent team
│   ├── tdd/SKILL.md                    #   /tdd -- strict red-green-refactor TDD loop
│   ├── explain/SKILL.md                #   /explain <file-or-function>
│   ├── refactor/SKILL.md               #   /refactor <target>
│   ├── test-writer/SKILL.md            #   Auto-triggers on new features -- comprehensive tests
│   ├── parallel/SKILL.md               #   /parallel -- multi-agent parallel task execution
│   ├── setup-vault/SKILL.md            #   /setup-vault -- initialize vault from domain pack
│   ├── process-docs/SKILL.md           #   /process-docs -- run document processing pipeline
│   ├── ingest/SKILL.md                 #   /ingest -- per-document pipeline with Chinese translation, flexible input
│   ├── vault-search/SKILL.md           #   /vault-search -- search vault by keyword, entity, or filename
│   ├── vault-health/SKILL.md           #   /vault-health -- validate vault integrity
│   ├── create-entity/SKILL.md          #   /create-entity -- create entity notes from templates
│   ├── vault-stats/SKILL.md            #   /vault-stats -- vault statistics and metrics
│   ├── query-notebook/SKILL.md         #   /query-notebook -- query NotebookLM notebooks
│   ├── push-notebook/SKILL.md          #   /push-notebook -- push vault content to NotebookLM
│   ├── analyze-topic/SKILL.md          #   /analyze-topic -- multi-source research synthesis
│   └── weekly-brief/SKILL.md           #   /weekly-brief -- generate intelligence briefings
├── agents/                             # Coordinated agent team -> copy to .claude/agents/
│   ├── code-reviewer.md                #   General code review -- routes to specialists
│   ├── security-reviewer.md            #   Security-focused code review
│   ├── performance-reviewer.md         #   Finds real bottlenecks, not theoretical ones
│   ├── frontend-designer.md            #   Creates distinctive UI -- anti-AI-slop
│   ├── doc-reviewer.md                 #   Documentation accuracy and completeness
│   ├── parallel-executor.md            #   Worker agent for parallel task execution
│   ├── chinese-translator.md           #   Chinese-to-English document translation with energy glossary
│   ├── vault-orchestrator.md           #   Coordinates multi-step vault pipeline operations
│   ├── entity-manager.md               #   Entity extraction, deduplication, registry updates
│   ├── doc-enricher.md                 #   AI-powered document enhancement with privacy controls
│   ├── vault-validator.md              #   Vault health checks and auto-fixes
│   ├── notebooklm-bridge.md            #   Bidirectional NotebookLM integration
│   └── research-synthesizer.md         #   Multi-source research synthesis with attribution
└── hooks/                              # Hook scripts -> copy to .claude/hooks/
    ├── protect-files.sh                #   Block edits to sensitive files and directories
    ├── warn-large-files.sh             #   Block writes to build artifacts and binary files
    ├── scan-secrets.sh                 #   Detect API keys, tokens, and credentials
    ├── block-dangerous-commands.sh     #   Block push to main, force push, reset --hard, etc.
    ├── format-on-save.sh               #   Auto-format after edits (auto-detects formatter)
    ├── vault-protect.sh                #   Protect vault privacy zones and sensitive content
    └── session-start.sh                #   Inject branch/commit/stash/PR context at session start
```

## Credits

Built from and inspired by:
- [dotclaude](https://github.com/poshan0126/dotclaude) -- the original `.claude/` template
- [Official Claude Code Documentation](https://code.claude.com/docs/en)
- [Trail of Bits claude-code-config](https://github.com/trailofbits/claude-code-config)
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
- Community best practices from Claude Code power users

## License

MIT -- use it, fork it, adapt it, share it.
