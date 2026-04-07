# ferclaudeobs -- Complete System Guide

## What Is This?

ferclaudeobs is a portable Claude Code configuration system that combines:
1. **Claude Code Development Tools** -- Skills, agents, hooks, and rules for software development
2. **Obsidian Knowledge Management** -- An AI-powered document processing pipeline that transforms raw documents into a connected, searchable Obsidian vault
3. **NotebookLM Integration** -- Bidirectional querying and content pushing to Google NotebookLM

It is designed for anyone who needs to make sense of large volumes of documents -- energy sector intelligence, legal case research, company competitive intelligence, international arbitration, etc.

---

## Architecture Overview

```
+-----------------------------------------------------------+
|                      ferclaudeobs                         |
|                                                           |
|  +--------------+  +--------------+  +--------------+     |
|  |  Claude Code  |  |   Obsidian   |  |  NotebookLM  |   |
|  |  Dev Tools    |  |  Vault Engine|  |  Bridge      |   |
|  |              |  |              |  |              |     |
|  | 11 Dev Skills|  | 10 Vault     |  | Query &      |   |
|  | 6 Dev Agents |  |    Skills    |  | Push via     |   |
|  | 7 Rules      |  | 6 Vault      |  | notebooklm-  |   |
|  | 7 Hooks      |  |   Agents     |  | py           |   |
|  |              |  | 10 Python    |  |              |   |
|  |              |  |   Scripts    |  |              |   |
|  +--------------+  +--------------+  +--------------+     |
|                                                           |
|  +-------------------------------------------------------+|
|  |                Domain Pack System                     ||
|  |  Swappable knowledge packs: energy, legal, intel...   ||
|  +-------------------------------------------------------+|
+-----------------------------------------------------------+
```

---

## How the Document Pipeline Works

This is the core of the knowledge management system. It transforms raw documents into connected knowledge.

### The Pipeline Flow

```
                    +---------+
                    |  inbox/  |  Raw documents dropped here
                    | PDF,DOCX|  (never modified, never deleted)
                    | HTML,TXT|
                    +----+----+
                         |
                    +----v----+
                    |CONVERTER|  scripts/convert_docs.py
                    |         |  PDF/DOCX/HTML -> clean Markdown
                    +----+----+
                         |
                    +----v----+
              vault/| _INBOX/ |  Staging area
                    +----+----+
                         |
                    +----v----+
                    |EXTRACTOR|  scripts/extract_entities.py
                    |         |  Uses Ollama (local AI) to find:
                    |         |  companies, regulations, tech,
                    |         |  projects, people, locations
                    +----+----+
                         |
                  +------v------+
                  |  ENRICHER   |  scripts/enrich_notes.py
                  |  (optional) |  AI-powered restructuring
                  |             |  Adds summaries, context
                  |  ! Privacy  |  NEVER touches confidential files
                  +------+------+
                         |
                    +----v----+
                    | LINKER  |  scripts/inject_links.py
                    |         |  Injects [[wikilinks]] for every
                    |         |  known entity (first occurrence only)
                    +----+----+
                         |
                    +----v----+
                    | TAGGER  |  scripts/add_frontmatter.py
                    |         |  Adds/updates YAML frontmatter:
                    |         |  title, type, tags, dates, status
                    +----+----+
                         |
                    +----v----+
                    |  MOC    |  scripts/build_mocs.py
                    | BUILDER |  Moves notes to correct folders
                    |         |  Rebuilds Map of Content indexes
                    +----+----+
                         |
                    +----v----+
                    |VALIDATOR|  scripts/validate_vault.py
                    |         |  Checks: broken links, orphans,
                    |         |  missing metadata, empty notes
                    +----+----+
                         |
                    +----v----+
                    |  VAULT  |  Connected knowledge base
                    | 11 domains, MOC indexes, entity notes
                    | Graph view, backlinks, semantic search
                    +---------+
```

### Step-by-Step: Processing Your First Documents

1. **Drop documents in `inbox/`**
   - Supported: PDF, DOCX, HTML, TXT, Markdown
   - The pipeline NEVER modifies or deletes originals

2. **Run the pipeline**
   ```
   /process-docs
   ```
   Or with AI enrichment (sends content to external APIs):
   ```
   /process-docs --with-enrich
   ```

3. **What happens**:
   - CONVERTER transforms each file to clean Markdown
   - EXTRACTOR finds named entities (companies, regulations, tech terms...)
   - LINKER creates [[wikilinks]] connecting related concepts
   - TAGGER adds structured YAML metadata to each note
   - MOC_BUILDER moves notes to the right domain folder and rebuilds indexes
   - VALIDATOR checks for broken links and missing metadata

4. **Open in Obsidian**
   - Open the `vault/` folder as an Obsidian vault
   - See the graph view -- your documents are now a connected knowledge network
   - Click any entity to see all documents that mention it

### Pipeline Modes

You can run individual stages instead of the full pipeline:

| Mode | Command | What It Does |
|------|---------|-------------|
| `full` | `/process-docs` | Run all stages end to end |
| `convert` | `/process-docs --mode=convert` | Only convert inbox files to Markdown |
| `extract` | `/process-docs --mode=extract` | Only extract entities from staged files |
| `enrich` | `/process-docs --mode=enrich --with-enrich` | Only run AI enrichment |
| `link` | `/process-docs --mode=link` | Only inject wikilinks |
| `tag` | `/process-docs --mode=tag` | Only add/update frontmatter |
| `mocs` | `/process-docs --mode=mocs` | Only rebuild MOC indexes and file notes |
| `validate` | `/process-docs --mode=validate` | Only run vault validation |

You can also target a single file:
```
/process-docs --file=inbox/my-report.pdf
```

### Pipeline Engines

The pipeline supports two engines:

| Engine | Flag | Description |
|--------|------|-------------|
| **Claude Code native** | `--engine=claude-code` (default) | Claude Code reads, analyzes, and transforms documents directly. No external LLM needed — Claude IS the AI. Best quality for entity extraction and enrichment. |
| **Python scripts** | `--engine=python` | Runs the Python pipeline via subprocess. Uses Ollama or LM Studio for local AI. Better for batch processing or fully local/offline operation. |

The default engine is set in `pack.json` under `processing.primary_engine`. Override per-run with:
```
/process-docs --engine=python          # Force Python pipeline
/process-docs --engine=claude-code     # Force Claude Code native
```

**When Python is still used in Claude Code native mode:**
- **DOCX conversion**: Claude cannot read binary `.docx` files — Python's mammoth library handles this
- **Confidential file enrichment**: Files in privacy zones fall back to local Ollama/LM Studio

### Processing Configuration

The `processing` section in `pack.json` controls engine behavior:

```json
"processing": {
  "primary_engine": "claude-code",      // Default engine
  "fallback_engine": "ollama",          // For steps Claude can't handle
  "confidential_engine": "ollama",      // For privacy zone files
  "confidential_mode": "zones",         // "full" = all local, "zones" = only privacy zones local
  "lm_studio": {
    "endpoint": "http://localhost:1234/v1",
    "model": "gemma-4-26b-a4b"          // LM Studio model
  }
}
```

| Field | Values | Purpose |
|-------|--------|---------|
| `primary_engine` | `claude-code`, `python` | Default engine when no `--engine` flag is passed |
| `fallback_engine` | `ollama`, `lm-studio` | Used for steps Claude Code can't handle natively |
| `confidential_engine` | `ollama`, `lm-studio` | Always local — processes privacy zone files |
| `confidential_mode` | `full`, `zones` | `full`: ALL docs processed locally. `zones`: only privacy-zone docs local |
| `lm_studio.endpoint` | URL | LM Studio OpenAI-compatible API endpoint |
| `lm_studio.model` | Model name | LM Studio model (e.g., `gemma-4-26b-a4b`) |

### LM Studio Setup

[LM Studio](https://lmstudio.ai/) provides a local LLM server with an OpenAI-compatible API. To use it:

1. Download and install LM Studio
2. Load a model (e.g., `gemma-4-26b-a4b`)
3. Start the local server (default: `http://localhost:1234/v1`)
4. Set `processing.lm_studio.model` in pack.json to match your loaded model
5. Use it as a provider:
   ```
   /process-docs --engine=python    # Then scripts use LM Studio via --provider=lm-studio
   python scripts/extract_entities.py --provider=lm-studio
   python scripts/enrich_notes.py --provider=lm-studio
   ```

---

## Domain Pack System

Domain packs make the engine reusable across different fields.

### What's in a Domain Pack?

```
domain-packs/philenergy/
+-- pack.json              # Manifest: categories, privacy zones, plugins
+-- entities.json          # Pre-seeded entities (90+ for PH energy)
+-- vault-structure.json   # Folder hierarchy (67 folders, 11 domains)
+-- enrichment-prompt.md   # AI prompt for document enrichment
+-- extraction-prompt.md   # AI prompt for entity extraction
+-- notebooks.json         # NotebookLM notebook links
+-- home-dashboard.md      # HOME.md template with dataview queries
+-- templates/             # 7 note templates
    +-- Company.md
    +-- Regulation.md
    +-- Technology.md
    +-- Project.md
    +-- Supplier.md
    +-- Analysis.md
    +-- Weekly-Brief.md
```

### How Domain Packs Work

```
config/active-pack.json ----> Points to: domain-packs/philenergy/
                                            |
    Every script reads this at startup      |
                                            v
    +---------------------------------------------------+
    | pack.json tells each script:                      |
    |  * What entities to look for (entities.json)      |
    |  * What folder structure to use (vault-*.json)    |
    |  * What AI prompts to use (*.md prompts)          |
    |  * What privacy zones to enforce                  |
    |  * What Obsidian plugins to configure             |
    +---------------------------------------------------+
```

### Creating a New Domain Pack

To use this system for a different domain (legal, company intel, etc.):

1. Create `domain-packs/my-domain/`
2. Create `pack.json` with your entity categories and privacy zones
3. Create `entities.json` with pre-seeded entities for your domain
4. Create `vault-structure.json` with your folder hierarchy
5. Create templates for your note types
6. Create extraction and enrichment prompts tuned to your domain
7. Run `/setup-vault my-domain`

Example: For a legal research vault, your entity categories might be:
- cases, statutes, courts, judges, parties, legal_concepts, jurisdictions

Example: For a company competitive intelligence vault:
- companies, products, executives, financials, patents, markets, partnerships

### PhilEnergy Pack: Entity Categories

The bundled `philenergy` domain pack ships with 98 pre-seeded entities across 7 categories:

| Category | Count | Examples |
|----------|-------|---------|
| Organizations | 10 | NGCP, IEMOP, DOE, ERC, PSALM |
| Philippine Companies | 15 | Vivant, MERALCO, ACEN, Aboitiz Power |
| Global Suppliers | 21 | Sungrow, BYD, CATL, LONGi, Vestas |
| Regulations | 10 | RA 9513, RA 9136 (EPIRA), FIT, RCOA |
| Technologies | 17 | BESS, LFP, PCS, EMS, SCADA, TOPCon |
| Market Concepts | 16 | WESM, LCOE, LCOS, LMP, FCAS |
| Locations | 9 | Luzon, Visayas, Mindanao, Cebu, Davao |

---

## The Vault Structure (PhilEnergy Example)

```
vault/
+-- _INBOX/              <-- Pipeline staging area (auto-processed)
+-- _TEMPLATES/          <-- Note templates (do not edit directly)
+-- _ASSETS/             <-- Images, PDFs, charts
|   +-- images/
|   +-- pdfs/
|   +-- charts/
|
+-- 00 - HOME/           <-- Dashboard + Map of Content indexes
|   +-- HOME.md          <-- Master entry point with dataview queries
|   +-- MOC - Global Context.md
|   +-- MOC - Philippines Energy Market.md
|   +-- MOC - Regulations & Policy.md
|   +-- MOC - Grid & Infrastructure.md
|   +-- MOC - Technologies.md
|   +-- MOC - Global Suppliers.md
|   +-- MOC - Philippines Market Players.md
|   +-- MOC - Competitors.md
|   +-- MOC - Projects.md
|   +-- MOC - Vivant Internal.md
|   +-- MOC - Intelligence & Analysis.md
|
+-- 01 - GLOBAL CONTEXT/
|   +-- Macroeconomics/
|   +-- Energy Geopolitics/
|   +-- Country Studies/
|   +-- Commodity Markets/
|   +-- Climate & Policy/
|
+-- 02 - PHILIPPINES ENERGY MARKET/
|   +-- Market Structure/
|   +-- WESM/
|   +-- Pricing & Tariffs/
|   +-- Demand Forecasting/
|   +-- Grid Zones/
|
+-- 03 - REGULATIONS & POLICY/
|   +-- DOE Circulars/
|   +-- ERC Orders/
|   +-- NGCP Guidelines/
|   +-- IEMOP Rules/
|   +-- Legislation/
|
+-- 04 - GRID & INFRASTRUCTURE/
|   +-- NGCP/
|   +-- Substations/
|   +-- Transmission Lines/
|   +-- Distribution Utilities/
|   +-- Interconnections/
|
+-- 05 - TECHNOLOGIES/
|   +-- Solar PV/
|   +-- BESS/
|   +-- Wind/
|   +-- Hydro/
|   +-- Geothermal/
|   +-- Inverters & PCS/
|   +-- EMS & SCADA/
|   +-- Grid-Forming Technology/
|   +-- Emerging Technologies/
|
+-- 06 - GLOBAL SUPPLIERS/
|   +-- PV Manufacturers/
|   +-- Battery Manufacturers/
|   +-- Inverter & PCS Suppliers/
|   +-- Wind Turbine Manufacturers/
|   +-- EMS & Software Vendors/
|   +-- EPC Contractors/
|   +-- Financial Institutions/
|
+-- 07 - MARKET PLAYERS - PHILIPPINES/
|   +-- Generation Companies/
|   +-- Distribution Utilities/
|   +-- Retail Electricity Suppliers/
|   +-- Independent Power Producers/
|   +-- Government Entities/
|
+-- 08 - COMPETITORS/
|   +-- Company Profiles/
|   +-- Financial Analysis/
|   +-- Project Tracking/
|   +-- Strategic Intelligence/
|
+-- 09 - PROJECTS/
|   +-- Vivant Projects/
|   +-- Competitor Projects/
|   +-- Government Initiatives/
|   +-- Market Opportunities/
|
+-- 10 - VIVANT INTERNAL/            <-- STRICTLY CONFIDENTIAL
|   +-- Corporate Strategy/
|   +-- Financial Models/
|   +-- Procurement/
|   +-- BD & Pipeline/
|   +-- Operations/
|
+-- 11 - INTELLIGENCE & ANALYSIS/
    +-- Weekly Briefs/
    +-- Market Reports/
    +-- Risk Analysis/
    +-- Price Forecasts/
    +-- Strategic Memos/
```

### Automatic Filing

The pipeline automatically files notes into the correct folder based on their detected type:

| Detected Type | Filed To |
|--------------|----------|
| regulation | 03 - REGULATIONS & POLICY |
| technology | 05 - TECHNOLOGIES |
| supplier | 06 - GLOBAL SUPPLIERS |
| company | 07 - MARKET PLAYERS - PHILIPPINES |
| project | 09 - PROJECTS |
| analysis | 11 - INTELLIGENCE & ANALYSIS/Market Reports |
| brief | 11 - INTELLIGENCE & ANALYSIS/Weekly Briefs |
| document | 11 - INTELLIGENCE & ANALYSIS/Market Reports |

Type detection uses pattern matching from `pack.json`. For example, a document mentioning "DOE", "ERC", "circular", or "order" is inferred as type `regulation`.

---

## NotebookLM Integration

### Bidirectional Flow

```
+--------------+          +------------------+
|              |  QUERY   |                  |
|   Obsidian   | <------- |   NotebookLM     |
|    Vault     |          |   Notebooks      |
|              |  PUSH    |                  |
|              | -------->|                  |
+--------------+          +------------------+

Query: Ask NotebookLM questions -> get AI-synthesized answers ->
       create vault notes from responses

Push:  Select vault notes -> check privacy zones ->
       send content to NotebookLM for deep analysis
```

### Query Workflow
```
/query-notebook "What are the LCOE trends for BESS in Southeast Asia?"
  |
  +-- 1. Reads config/notebook_registry.json
  +-- 2. Selects best notebook (or asks user)
  +-- 3. Runs: python scripts/notebooklm_bridge.py query ...
  +-- 4. Creates Obsidian note from response
  +-- 5. Injects [[wikilinks]]
  +-- 6. Files in vault/11 - INTELLIGENCE & ANALYSIS/
```

### Push Workflow
```
/push-notebook "vault/05 - TECHNOLOGIES/BESS" --notebook="BESS Technology Intelligence"
  |
  +-- 1. Checks privacy zones (BLOCKS confidential content)
  +-- 2. Confirms with user (content goes to Google)
  +-- 3. Runs: python scripts/notebooklm_bridge.py push ...
  +-- 4. Updates notebook_registry.json with sync timestamp
  +-- 5. Reports: N notes pushed, N failed, N skipped (confidential)
```

### Pre-configured Notebooks (PhilEnergy)

| Notebook Name | Description | Vault Folders |
|--------------|-------------|---------------|
| PH Energy Regulations | Regulatory documents, DOE circulars, ERC orders | 03 - REGULATIONS & POLICY |
| BESS Technology Intelligence | Battery storage tech, supplier analysis, cost trends | 05 - TECHNOLOGIES/BESS, 06 - GLOBAL SUPPLIERS/Battery Manufacturers |
| Market & Competitor Analysis | WESM data, competitor profiles, market intelligence | 02 - PHILIPPINES ENERGY MARKET, 08 - COMPETITORS |

### Setting Up NotebookLM

1. Install the package:
   ```bash
   pip install "notebooklm-py[browser]"
   playwright install chromium
   ```

2. Log into NotebookLM in your browser

3. Edit `domain-packs/[pack]/notebooks.json`:
   - Add your notebook URLs or IDs
   - Map each notebook to relevant vault folders

4. Test: `/query-notebook "test question" --notebook="My Notebook"`

---

## Privacy & Security

### Privacy Zones

Privacy zones are defined in `pack.json` and enforced everywhere:

```json
"privacy_zones": [
  {
    "path": "10 - VIVANT INTERNAL",
    "level": "confidential",
    "external_api": false
  },
  {
    "path": "08 - COMPETITORS",
    "level": "sensitive",
    "external_api": "approval_required"
  }
]
```

- **confidential** (`external_api: false`): Content is NEVER sent to any external API. All processing uses local Ollama only.
- **sensitive** (`external_api: "approval_required"`): Content can be sent externally only after explicit user confirmation.

### What Gets Checked

| Operation | Privacy Check |
|-----------|--------------|
| AI Enrichment (Claude/Gemini) | Blocked for confidential paths |
| NotebookLM Push | Blocked for confidential paths |
| NotebookLM Query | Safe (query text only, not vault content) |
| Local Ollama Processing | Always safe (runs locally) |
| Wikilink Injection | Always safe (local text processing) |
| Entity Extraction (Ollama) | Always safe (runs locally) |

### Hook Protection

The `vault-protect.sh` hook runs as a PreToolUse hook on every Edit/Write operation and blocks direct edits to:
- Files in paths containing `INTERNAL` or `CONFIDENTIAL`
- Template files (`_TEMPLATES/`)
- The `HOME.md` dashboard

Additional hooks that protect the project:

| Hook | What It Does |
|------|-------------|
| `protect-files.sh` | Blocks edits to sensitive files and directories |
| `warn-large-files.sh` | Blocks writes to build artifacts and binary files |
| `scan-secrets.sh` | Detects API keys, tokens, and credentials before they are written |
| `block-dangerous-commands.sh` | Blocks force pushes, reset --hard, push to main |
| `format-on-save.sh` | Auto-formats files after edits (PostToolUse) |
| `vault-protect.sh` | Protects vault privacy zones and sensitive content |
| `session-start.sh` | Injects branch/commit/stash/PR context at session start |

All hooks fail open -- if `jq` is missing or an error occurs, they exit 0 (allow) rather than blocking the user.

---

## Agent Teams

### Vault Operations Team

```
           +----------------------+
           |  vault-orchestrator  |  Dispatches & coordinates
           +----------+-----------+
                      |
      +---------------+---------------+
      |               |               |
+-----v-----+  +-----v-----+  +-----v------+
|  entity-   |  |   doc-    |  |   vault-   |
|  manager   |  |  enricher |  |  validator  |
|            |  |           |  |            |
| Extracts & |  | AI-powered|  | Health     |
| deduplicates| | enhancement| | checks &   |
| entities   |  | (privacy  |  | auto-fixes |
|            |  |  aware)   |  |            |
+------------+  +-----------+  +------------+

      +---------------+---------------+
      |                               |
+-----v------+              +---------v------+
| notebooklm-|              |   research-    |
|   bridge   |              |  synthesizer   |
|            |              |                |
| Query &    |<------------>| Multi-source   |
| push to    |  Coordinates | research with  |
| NotebookLM |              | attribution    |
+------------+              +----------------+
```

The vault-orchestrator manages pipeline sequencing:
- CONVERTER and EXTRACTOR can run in parallel
- EXTRACTOR must finish before LINKER
- LINKER must finish before MOC_BUILDER
- TAGGER can run in parallel with LINKER
- VALIDATOR always runs last

If any agent fails on a specific file, the orchestrator logs the error, moves the file to `vault/_INBOX/FAILED/`, and continues processing the rest.

### Code Review Team

```
           +------------------+
           |  code-reviewer    |  Routes issues
           +-------+----------+
                   |
      +------------+------------+
      |            |            |
+-----v----+ +----v-----+ +---v------+
| security-| |performance| |  doc-    |
| reviewer | | -reviewer | | reviewer |
+----------+ +----------+ +----------+
```

### All Agents

| Agent | Role | Coordinates With |
|-------|------|-----------------|
| `@vault-orchestrator` | Coordinates multi-step vault operations | All vault agents |
| `@entity-manager` | Entity extraction, deduplication, registry | vault-orchestrator |
| `@doc-enricher` | AI-powered document enhancement (privacy aware) | vault-orchestrator |
| `@vault-validator` | Broken links, orphans, frontmatter validation | vault-orchestrator |
| `@notebooklm-bridge` | Query and push to NotebookLM | research-synthesizer |
| `@research-synthesizer` | Multi-source research with attribution | notebooklm-bridge |
| `@code-reviewer` | General code review, routes to specialists | security, performance, doc reviewers |
| `@security-reviewer` | OWASP vulnerability analysis | code-reviewer |
| `@performance-reviewer` | Finds real bottlenecks (N+1, memory leaks) | code-reviewer, security-reviewer |
| `@frontend-designer` | Creates distinctive, production-grade UI | code-reviewer |
| `@doc-reviewer` | Documentation accuracy and completeness | code-reviewer |
| `@parallel-executor` | Worker agent for parallel subtask execution | Any dispatching agent |

All agents communicate via `SendMessage` and require `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (configured in settings.json).

### Using Agents Directly

```
@security-reviewer Review the auth middleware changes in src/middleware/auth.ts
```

```
@vault-orchestrator Process the 15 new documents I just dropped in inbox/
```

```
@research-synthesizer What is the current state of BESS deployment in Southeast Asia?
```

---

## Skills Reference

### Vault Management Skills

| Skill | What It Does | Triggers On |
|-------|-------------|-------------|
| `/setup-vault` | Initialize vault from domain pack | "set up vault", "new obsidian project" |
| `/process-docs` | Run document pipeline | "process documents", "run pipeline" |
| `/vault-search` | Search vault for information | "what do we know about X", "search vault" |
| `/vault-health` | Check vault integrity | "vault health", "broken links" |
| `/create-entity` | Create new entity note | "create entity", "new company note" |
| `/vault-stats` | Show vault statistics | "vault statistics", "how many notes" |
| `/query-notebook` | Query NotebookLM | "ask NotebookLM", "query notebook" |
| `/push-notebook` | Push content to NotebookLM | "push to NotebookLM", "sync notebook" |
| `/analyze-topic` | Deep multi-source analysis | "analyze topic", "research synthesis" |
| `/weekly-brief` | Generate intelligence briefing | "weekly brief", "generate briefing" |

### Development Skills

| Skill | What It Does |
|-------|-------------|
| `/init` | Initialize ferclaudeobs for new project |
| `/setup` | Customize config for project tech stack |
| `/debug-fix` | Find and fix bugs |
| `/ship` | Stage, commit, push, create PR |
| `/hotfix` | Emergency production fix |
| `/pr-review` | Review PR with specialist agents |
| `/tdd` | Test-driven development loop |
| `/explain` | Explain code with diagrams |
| `/refactor` | Safe refactoring with test safety net |
| `/test-writer` | Write comprehensive tests |
| `/parallel` | Decompose and parallelize tasks |

### Skill Details: /analyze-topic

The `/analyze-topic` skill creates comprehensive analysis documents by combining multiple sources:

1. **Vault search** -- finds all notes mentioning the topic
2. **Entity registry lookup** -- identifies related entities
3. **NotebookLM query** (if configured) -- gets AI-synthesized insights from uploaded documents
4. **Synthesis** -- produces a structured analysis note with:
   - Executive Summary
   - Background and context
   - Key Findings (with source attribution)
   - Implications
   - Risks & Uncertainties
   - Recommendations
   - Sources consulted

### Skill Details: /weekly-brief

The `/weekly-brief` skill generates intelligence briefings from notes added or modified in the past N days (default 7):

- **Top Stories** -- Most significant developments
- **Market Movements** -- Price and market data
- **Regulatory Updates** -- New regulations or policy changes
- **Competitor Activity** -- Competitor-related notes
- **Supplier Intelligence** -- Supplier updates
- **Project Updates** -- Project status changes
- **Risk Flags** -- Notes with confidence=low or risk-related content
- **Looking Ahead** -- Upcoming events and deadlines
- **New Notes Added** -- List of all new notes with [[wikilinks]]

---

## Getting Started

### For Knowledge Management (Obsidian Vault)

```
Step 1: Clone the repo
  git clone https://github.com/ferone/ferclaudeobs.git

Step 2: Set up your project
  cd my-project
  /init                         <-- Detects Obsidian project type
  /setup-vault philenergy       <-- Initialize vault with PhilEnergy domain pack

Step 3: Install Python dependencies
  pip install -r requirements.txt

Step 4: Install a local LLM (for confidential docs / offline processing)

  Option A -- Ollama:
    Download from https://ollama.com
    ollama pull qwen2.5:32b     <-- Primary model
    ollama pull qwen2.5:7b      <-- Lighter fallback

  Option B -- LM Studio (alternative):
    Download from https://lmstudio.ai
    Load model: gemma-4-26b-a4b
    Start local server (default: http://localhost:1234/v1)

  Note: Local LLM is only needed for confidential files and the
  Python fallback engine. Claude Code native mode (the default)
  uses Claude's own AI and needs no local LLM.

Step 5: Install Obsidian plugins
  Open vault/ in Obsidian
  Settings -> Community Plugins -> Install the 13 recommended plugins

Step 6: Process documents
  Drop files in inbox/
  /process-docs                 <-- Converts, extracts entities, links, files

Step 7: Explore your knowledge
  /vault-search "NGCP"          <-- Find information
  /analyze-topic "BESS"         <-- Deep analysis
  /weekly-brief                 <-- Intelligence briefing
```

### For Software Development

```
Step 1: Clone and copy
  git clone https://github.com/ferone/ferclaudeobs.git /tmp/ferclaudeobs
  cp -r /tmp/ferclaudeobs/.claude/ my-project/.claude/
  cp /tmp/ferclaudeobs/CLAUDE.md my-project/CLAUDE.md

Step 2: Initialize
  cd my-project
  /init              <-- Detects project type, enables relevant config
  /setup             <-- Customizes rules/agents for your tech stack
```

Or use the one-command setup:

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

---

## Obsidian Plugins

These 13 plugins are auto-configured by `/setup-vault`:

### Required (6)

| Plugin | Purpose |
|--------|---------|
| **Dataview** | Query vault as a database (SQL-like queries over notes) |
| **Templater** | Auto-apply templates when creating new notes |
| **Smart Connections** | Local AI-powered semantic search (no cloud) |
| **Copilot** | Chat interface using local Ollama |
| **Graph Analysis** | Community detection in knowledge graph |
| **Claudian** | Embed Claude Code as sidebar assistant in Obsidian |

### Recommended (7)

| Plugin | Purpose |
|--------|---------|
| **Folder Notes** | Make MOC files visible in folder tree |
| **Periodic Notes** | Auto-create weekly/monthly review notes |
| **Kanban** | Board view for project tracking |
| **Excalidraw** | Draw diagrams and mind maps |
| **Advanced Tables** | Easier markdown table editing |
| **Tag Wrangler** | Bulk tag management and reorganization |
| **Smart Second Brain** | RAG-powered note interaction |

---

## Configuration Files Reference

| File | Purpose | When Read |
|------|---------|-----------|
| `config/active-pack.json` | Points to active domain pack | Every script startup |
| `config/processed_log.json` | Tracks which files have been converted | By convert_docs.py |
| `config/entity_registry_extracted.json` | All entities found by extraction | By extract_entities.py, inject_links.py |
| `config/master_linklist.json` | Combined entity list for linking | By inject_links.py |
| `config/missing_entities.json` | Broken wikilink targets | By validate_vault.py |
| `config/notebook_registry.json` | NotebookLM notebook metadata | By notebooklm_bridge.py |
| `domain-packs/[pack]/pack.json` | Domain pack manifest | Every script startup |
| `domain-packs/[pack]/entities.json` | Pre-seeded entities for the domain | By extract_entities.py, inject_links.py |
| `domain-packs/[pack]/vault-structure.json` | Folder hierarchy and type-to-folder mapping | By setup_vault.py, build_mocs.py |
| `domain-packs/[pack]/notebooks.json` | NotebookLM notebook definitions | By notebooklm_bridge.py |

---

## Frontmatter Schema

Every vault note has YAML frontmatter:

```yaml
---
title: "Note Title"
type: company
category: "Subcategory"
tags: [energy, bess]
aliases: ["Alt Name"]
date_created: 2026-04-04
date_modified: 2026-04-04
status: active
confidence: medium
source: "original.pdf"
---
```

### Core Fields

| Field | Values | Required |
|-------|--------|----------|
| `title` | Any string | Yes |
| `type` | company, regulation, technology, project, supplier, analysis, brief, document, moc | Yes |
| `category` | Free text subcategory | No |
| `tags` | Array of strings | Yes |
| `aliases` | Array of alternate names | No |
| `date_created` | ISO date | Yes |
| `date_modified` | ISO date | Yes |
| `status` | active, archived, draft, verified | Yes |
| `confidence` | high, medium, low | No |
| `source` | Original filename or URL | No |

### Type-Specific Extensions

**Company:**
```yaml
country: "Philippines"
sector: "Energy"
market_cap: "..."
founded: 2010
employees: 500
revenue_usd: "..."
```

**Regulation:**
```yaml
issuing_body: "DOE"
document_number: "DC2026-02-0008"
date_issued: 2026-02-15
effective_date: 2026-03-01
scope: "BESS interconnection requirements"
```

**Technology:**
```yaml
maturity: "commercial"
relevant_sectors: ["energy storage", "grid"]
key_players: ["BYD", "CATL", "Sungrow"]
```

**Project:**
```yaml
developer: "Vivant Energy Corporation"
technology: "BESS"
capacity_mw: 100
storage_mwh: 400
location: "Leyte"
grid_zone: "Visayas"
stage: "construction"
cod_target: "2027-Q2"
capex_usd: "..."
tariff_type: "RCOA"
offtaker: "MERALCO"
```

**Supplier:**
```yaml
origin_country: "China"
product_lines: ["Battery Cells", "Battery Packs"]
technology: "LFP"
tier: "Tier 1"
philippine_presence: true
warranty_years: 15
annual_shipments_gw: 80
```

---

## Wikilink Strategy

The core linking principle: **One entity = one note. Everything links to it. Never duplicate.**

```
If "Sungrow" appears in 50 documents -> ONE Sungrow.md note
All other notes link to it: [[Sungrow]]
The Sungrow note accumulates everything known about them
Click any entity -> see ALL documents that mention it (via backlinks)
```

### Linking Rules

- Link FIRST occurrence per document only (not every mention)
- Use alias syntax for long names: `[[NGCP|National Grid Corporation of the Philippines]]`
- Never link inside code blocks, URLs, or existing links
- Sort entity matches longest-first to avoid partial matches ("Solar" matching inside "Solar Philippines")
- Both pre-seeded entities (from `entities.json`) and extracted entities (from `entity_registry_extracted.json`) are used for linking
- The combined link list is maintained in `config/master_linklist.json`

### How It Works in Practice

Given a document containing:
```
The DOE issued DC2026-02-0008 requiring NGCP to facilitate
BESS interconnection. Sungrow and BYD are leading suppliers
for the Visayas grid zone projects.
```

After link injection:
```
The [[DOE]] issued [[DC2026-02-0008]] requiring [[NGCP]] to facilitate
[[BESS]] interconnection. [[Sungrow]] and [[BYD]] are leading suppliers
for the [[Visayas]] grid zone projects.
```

Each link points to a dedicated entity note. Open Obsidian's graph view to see how everything connects.

---

## Python Scripts Reference

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `pipeline.py` | Orchestrates all pipeline stages | CLI args | Runs other scripts in sequence |
| `setup_vault.py` | Creates vault structure from domain pack | active-pack.json | Vault folders, templates, HOME.md, MOCs |
| `convert_docs.py` | Converts PDF/DOCX/HTML to Markdown | inbox/ files | vault/_INBOX/*.md |
| `extract_entities.py` | Extracts entities using Ollama or LM Studio (`--provider=ollama\|lm-studio`) | vault/_INBOX/*.md | entity_registry_extracted.json |
| `enrich_notes.py` | AI-powered document restructuring (`--provider=claude\|gemini\|ollama\|lm-studio`) | vault/_INBOX/*.md | Enhanced .md files |
| `inject_links.py` | Injects [[wikilinks]] for known entities | .md files + master_linklist.json | Modified .md files |
| `add_frontmatter.py` | Adds/updates YAML frontmatter | .md files | Modified .md files |
| `build_mocs.py` | Moves notes to folders, rebuilds MOC indexes | vault/ | Filed notes, updated MOC files |
| `validate_vault.py` | Checks vault health | vault/ | Health report + missing_entities.json |
| `notebooklm_bridge.py` | Query/push to NotebookLM | CLI args | JSON responses, updated registry |

### Dependencies

From `requirements.txt`:
- `mammoth` + `python-docx` -- DOCX conversion
- `pymupdf4llm` -- PDF conversion (high quality, preserves structure)
- `markdownify` -- HTML to Markdown
- `python-frontmatter` + `PyYAML` -- YAML frontmatter parsing
- `anthropic` -- Claude API for enrichment
- `requests` -- HTTP requests (Ollama API)
- `rich` -- Terminal output formatting
- `click` -- CLI argument parsing
- `watchdog` -- File system monitoring
- `notebooklm-py` -- NotebookLM integration

---

## Rules Reference

Rules are modular instructions loaded by Claude Code. Rules with `alwaysApply: true` are loaded every turn (costs tokens). Path-scoped rules only load when working near matched files.

| Rule | Scope | What It Governs |
|------|-------|----------------|
| `code-quality.md` | Always loaded | Naming conventions, comments, markers, file organization |
| `testing.md` | Always loaded | Testing conventions, coverage requirements |
| `database.md` | Near migration files | Migration safety, schema changes |
| `error-handling.md` | Near backend files | Error handling patterns |
| `security.md` | Near API/auth files | Security rules, sensitive paths |
| `frontend.md` | Near UI files | Design tokens, accessibility, components |
| `obsidian.md` | Near vault files | Vault interaction rules, privacy enforcement |

---

## Settings & Permissions

The `settings.json` file configures:

**Environment:**
- `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` -- Enables agent coordination via SendMessage

**Allowed commands (pre-approved, no confirmation needed):**
- All git commands (status, diff, log, branch, stash, add, commit, fetch, checkout, switch)
- GitHub CLI (gh pr, gh issue, gh run)
- Python pipeline scripts (python scripts/*.py)
- Package installation (pip install)
- Build/test/lint commands (npm run lint/test/typecheck/build)

**Denied operations (hard blocked):**
- Reading .env files, secrets, .pem, .key files
- Writing to .env files, secrets, .pem, .key files
- Editing any of the above

**Hook triggers:**
- PreToolUse (Edit/Write): protect-files, warn-large-files, scan-secrets, vault-protect
- PreToolUse (Bash): block-dangerous-commands
- PostToolUse (Edit/Write): format-on-save
- SessionStart: session-start (loads context)
- Notification: Desktop notification when Claude needs attention

**Pipeline processing (pack.json):**

These settings live in the domain pack's `pack.json`, not in `settings.json`:

| Field | Values | Purpose |
|-------|--------|---------|
| `processing.primary_engine` | `claude-code`, `python` | Default engine when no `--engine` flag is passed |
| `processing.fallback_engine` | `ollama`, `lm-studio` | For steps Claude Code can't handle (DOCX conversion) |
| `processing.confidential_engine` | `ollama`, `lm-studio` | Always local -- processes privacy-zone files |
| `processing.confidential_mode` | `full`, `zones` | `full`: all docs local. `zones`: only privacy-zone docs local |
| `processing.lm_studio.endpoint` | URL | LM Studio API endpoint (default: `http://localhost:1234/v1`) |
| `processing.lm_studio.model` | Model name | LM Studio model (default: `gemma-4-26b-a4b`) |

---

## Customization Guide

| Want to... | Do this |
|---|---|
| Add project-specific rules | Create `rules/your-rule.md` with frontmatter |
| Scope rules to file paths | Add `paths:` frontmatter to rule files |
| Add a team workflow | Create `skills/your-skill/SKILL.md` |
| Add a specialist agent | Create `agents/your-agent.md` (include `SendMessage` in tools) |
| Enforce behavior deterministically | Add a hook in `settings.json` |
| Override settings locally | Copy `settings.local.json.example` to `settings.local.json` |
| Personal CLAUDE.md overrides | Rename `CLAUDE.local.md.example` to `CLAUDE.local.md` |
| Add a new plugin | Add to `plugins.json` and re-run install script |
| Create a new domain pack | Create `domain-packs/my-pack/` with pack.json and supporting files |

---

## Troubleshooting

### Pipeline Issues

| Problem | Fix |
|---------|-----|
| "No active domain pack" | Run `/setup-vault [pack-name]` |
| "Ollama not reachable" | Install from ollama.com, run `ollama pull qwen2.5:32b` |
| "No files to convert" | Check inbox/ directory has supported files (PDF, DOCX, HTML, TXT) |
| Enrichment fails | Check API key is set (ANTHROPIC_API_KEY or GEMINI_API_KEY) |
| Pipeline crashes on one file | Check `logs/pipeline.log` -- failed files go to `vault/_INBOX/FAILED/` |
| Entities not being extracted | Verify Ollama is running: `curl http://localhost:11434/api/tags` |
| "LM Studio not reachable" | Verify LM Studio server is running. Check `processing.lm_studio.endpoint` in pack.json |
| Wrong LM Studio model | Ensure model name in LM Studio matches `processing.lm_studio.model` in pack.json (default: `gemma-4-26b-a4b`) |
| Engine selection confusion | Default engine is in `pack.json` under `processing.primary_engine`. Override with `--engine=python` or `--engine=claude-code` |

### NotebookLM Issues

| Problem | Fix |
|---------|-----|
| "notebooklm-py not installed" | `pip install "notebooklm-py[browser]"` and `playwright install chromium` |
| "No notebook ID configured" | Edit `domain-packs/[pack]/notebooks.json` with your notebook URLs |
| Auth fails | Log into NotebookLM in your browser first |
| Push blocked | Check if target path is in a confidential privacy zone |

### Vault Issues

| Problem | Fix |
|---------|-----|
| Broken wikilinks | Run `/vault-health --fix` to create stub notes |
| Notes stuck in _INBOX | Run `/process-docs --mode=mocs` to file them |
| Missing frontmatter | Run `/process-docs --mode=tag` to add metadata |
| MOC indexes outdated | Run `/process-docs --mode=mocs` to rebuild |
| Graph view is empty | Ensure notes have [[wikilinks]] -- run `/process-docs --mode=link` |

### General Issues

| Problem | Fix |
|---------|-----|
| Skills not showing up | Restart Claude Code -- skills are loaded at session start |
| Hooks not running | Run `chmod +x hooks/*.sh` and verify `jq` is installed |
| Agent teams not coordinating | Verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json |
| format-on-save not formatting | Ensure the formatter binary is installed and its config file exists |
| Plugins not installing | Run `claude plugin list` to verify CLI works, then retry install script |

---

## Appendix: Full File Tree

```
ferclaudeobs/
+-- CLAUDE.md                           # Project instructions
+-- CLAUDE.local.md.example             # Personal overrides template
+-- CONTRIBUTING.md                     # Contribution guidelines
+-- README.md                           # Project README
+-- plugins.json                        # 30+ plugin manifest
+-- settings.json                       # Claude Code settings, hooks, permissions
+-- settings.local.json.example         # Personal settings template
+-- requirements.txt                    # Python dependencies
+-- config/                             # Runtime configuration
+-- domain-packs/                       # Domain-specific knowledge packs
|   +-- philenergy/                     #   Philippine Energy Intelligence
|       +-- pack.json                   #     Manifest (categories, privacy, plugins)
|       +-- entities.json               #     98 pre-seeded entities
|       +-- vault-structure.json        #     67 folders, 11 domains
|       +-- enrichment-prompt.md        #     AI prompt for enrichment
|       +-- extraction-prompt.md        #     AI prompt for extraction
|       +-- notebooks.json              #     NotebookLM notebook links
|       +-- home-dashboard.md           #     HOME.md template
|       +-- templates/                  #     7 note templates
+-- scripts/                            # Pipeline and setup scripts
|   +-- pipeline.py                     #   Pipeline orchestrator
|   +-- setup_vault.py                  #   Vault initialization
|   +-- convert_docs.py                 #   PDF/DOCX/HTML -> Markdown
|   +-- extract_entities.py             #   Entity extraction (Ollama / LM Studio)
|   +-- enrich_notes.py                 #   AI enrichment (Claude / Gemini / Ollama / LM Studio)
|   +-- inject_links.py                 #   [[wikilink]] injection
|   +-- add_frontmatter.py             #   YAML frontmatter management
|   +-- build_mocs.py                   #   MOC index builder
|   +-- validate_vault.py              #   Vault health checker
|   +-- notebooklm_bridge.py           #   NotebookLM query/push
|   +-- setup-project.sh               #   One-command setup (macOS/Linux)
|   +-- setup-project.ps1              #   One-command setup (Windows)
|   +-- install-plugins.sh             #   Plugin installer (macOS/Linux)
|   +-- install-plugins.ps1            #   Plugin installer (Windows)
+-- skills/                             # 21 auto-triggering skills
|   +-- init/SKILL.md                   #   /init
|   +-- setup/SKILL.md                  #   /setup
|   +-- debug-fix/SKILL.md             #   /debug-fix
|   +-- ship/SKILL.md                   #   /ship
|   +-- hotfix/SKILL.md                #   /hotfix
|   +-- pr-review/SKILL.md             #   /pr-review
|   +-- tdd/SKILL.md                    #   /tdd
|   +-- explain/SKILL.md               #   /explain
|   +-- refactor/SKILL.md              #   /refactor
|   +-- test-writer/SKILL.md           #   /test-writer
|   +-- parallel/SKILL.md              #   /parallel
|   +-- setup-vault/SKILL.md           #   /setup-vault
|   +-- process-docs/SKILL.md          #   /process-docs
|   +-- vault-search/SKILL.md          #   /vault-search
|   +-- vault-health/SKILL.md          #   /vault-health
|   +-- create-entity/SKILL.md         #   /create-entity
|   +-- vault-stats/SKILL.md           #   /vault-stats
|   +-- query-notebook/SKILL.md        #   /query-notebook
|   +-- push-notebook/SKILL.md         #   /push-notebook
|   +-- analyze-topic/SKILL.md         #   /analyze-topic
|   +-- weekly-brief/SKILL.md          #   /weekly-brief
+-- agents/                             # 12 coordinated agents
|   +-- code-reviewer.md               #   General code review
|   +-- security-reviewer.md           #   Security-focused review
|   +-- performance-reviewer.md        #   Performance analysis
|   +-- frontend-designer.md           #   UI/UX design
|   +-- doc-reviewer.md                #   Documentation review
|   +-- parallel-executor.md           #   Parallel task worker
|   +-- vault-orchestrator.md          #   Vault pipeline coordinator
|   +-- entity-manager.md              #   Entity registry management
|   +-- doc-enricher.md                #   Document enhancement
|   +-- vault-validator.md             #   Vault health checks
|   +-- notebooklm-bridge.md           #   NotebookLM integration
|   +-- research-synthesizer.md        #   Cross-source research
+-- rules/                              # 7 modular rules
|   +-- code-quality.md                #   Naming, comments, organization
|   +-- testing.md                      #   Testing conventions
|   +-- database.md                    #   Migration safety
|   +-- error-handling.md              #   Error patterns
|   +-- security.md                    #   Security rules
|   +-- frontend.md                    #   Design and accessibility
|   +-- obsidian.md                    #   Vault interaction rules
+-- hooks/                              # 7 hook scripts
    +-- protect-files.sh               #   Block sensitive file edits
    +-- warn-large-files.sh            #   Block build artifact writes
    +-- scan-secrets.sh                #   Detect credentials
    +-- block-dangerous-commands.sh    #   Block destructive git commands
    +-- format-on-save.sh             #   Auto-format after edits
    +-- vault-protect.sh              #   Protect vault privacy zones
    +-- session-start.sh              #   Load context at session start
```
