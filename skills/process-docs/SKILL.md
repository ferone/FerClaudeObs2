---
name: process-docs
description: Run the document processing pipeline on inbox documents. Supports dual-mode — Claude Code native processing (default) or Python script fallback. Converts, extracts entities, enriches, injects wikilinks, tags frontmatter, files notes, builds MOCs, and validates.
argument-hint: "[--engine=claude-code|python] [--mode=full|convert|extract|enrich|link|tag|mocs|validate] [--file=path] [--with-enrich] [--confidential-mode=full|zones]"
---

Process documents through the intelligence pipeline. Claude Code is the primary engine — it reads, analyzes, and transforms documents directly. Python scripts serve as a fallback for batch processing or local-only AI.

## Pre-flight

1. Check `config/active-pack.json` exists — if not, tell user to run `/setup-vault` first
2. Read the active domain pack's `pack.json`
3. Read the `processing` section to determine default engine
4. Parse `$ARGUMENTS`:
   - `--engine=claude-code|python` — override engine (default: from pack.json `processing.primary_engine`)
   - `--mode=full|convert|extract|enrich|link|tag|mocs|validate` — pipeline stage (default: full)
   - `--file=path` — process single file
   - `--with-enrich` — include AI enrichment step
   - `--confidential-mode=full|zones` — override confidential handling
5. Count files in `inbox/` and `vault/_INBOX/`
6. Report: "Engine: [claude-code|python] | Mode: [mode] | Inbox: N files | Staged: M files"

---

## Python Engine Path

If engine is `python`:

```bash
python scripts/pipeline.py --mode=<mode> [--with-enrich] [--file=<path>]
```

Read `logs/pipeline.log` (last 50 lines) after completion and present a structured summary.

---

## Claude Code Native Engine

If engine is `claude-code` (the default), execute each step below using Claude Code's own tools. Claude IS the AI — no external LLM calls needed for entity extraction or enrichment.

### Step A: Convert Documents

For each file in `inbox/` (use Glob to find them):

**PDF files (.pdf):**
- Use the Read tool with `pages` parameter to read the PDF
- For large PDFs, read in batches of 20 pages (max per Read call): pages "1-20", then "21-40", etc.
- Clean the extracted text: remove excessive whitespace, fix broken line wraps
- Write as markdown to `vault/_INBOX/<filename-stem>.md` with frontmatter:
  ```yaml
  ---
  title: "<Title derived from filename>"
  type: document
  tags: []
  source: "inbox/<original-filename>"
  date_created: <today's date YYYY-MM-DD>
  date_modified: <today's date YYYY-MM-DD>
  status: draft
  confidence: medium
  ---
  ```

**DOCX files (.docx, .doc):**
- Claude Code cannot read binary DOCX format
- Fall back to Python: `python scripts/convert_docs.py --file=inbox/<filename>`
- Report: "DOCX converted via Python fallback"

**HTML files (.html, .htm):**
- Read with the Read tool
- Convert HTML to clean markdown: strip tags, preserve headings/lists/tables structure
- Write to `vault/_INBOX/` with frontmatter

**TXT files (.txt):**
- Read with the Read tool
- Wrap in markdown structure with headings where appropriate
- Write to `vault/_INBOX/` with frontmatter

**MD files (.md, .markdown):**
- Read with the Read tool
- If no frontmatter present, add the standard frontmatter block
- Write (copy) to `vault/_INBOX/`

**After converting all files:**
- Read `config/processed_log.json`
- Add each newly processed file path to the `processed` array
- Update `last_run` to current timestamp
- Write back to `config/processed_log.json`

**Handle duplicates:** If a file already exists in `vault/_INBOX/`, append `_1`, `_2`, etc. to the stem.

### Step B: Extract Entities

Read `domain-packs/<pack>/extraction-prompt.md` for extraction guidance.
Read `domain-packs/<pack>/entities.json` for the pre-seeded entity list.
Read `config/entity_registry_extracted.json` if it exists.

For each `.md` file in `vault/_INBOX/`:
1. Read the file
2. Strip YAML frontmatter (everything between the first two `---` markers)
3. Skip if body content is less than 50 characters
4. Analyze the document content and extract named entities into these categories:
   - `companies`: Company names found in the text
   - `organizations`: Government bodies, regulatory agencies
   - `regulations`: Laws, circulars, orders (with numbers if present)
   - `technologies`: Technology names and acronyms
   - `projects`: Named projects
   - `people`: Person names (with role if mentioned)
   - `locations`: Geographic locations
   - `concepts`: Market concepts, financial terms, industry jargon
   - `products`: Specific product names or models

   Use the extraction prompt from the domain pack as guidance for what to look for.
   Cross-reference with the pre-seeded entities in `entities.json` to recognize known entities.

5. For each extracted entity, merge into `config/entity_registry_extracted.json`:
   - If entity already exists: increment `count`, add source file to `sources` array
   - If new entity: create entry with `count: 1`, `sources: [<file>]`, `aliases: []`, `vault_note: null`

6. After processing all files, build the master link list:
   - Combine all entities from `domain-packs/<pack>/entities.json` (pre-seeded, with folder mappings)
   - Add extracted entities from `config/entity_registry_extracted.json` (deduplicated by name, case-insensitive)
   - Write combined list to `config/master_linklist.json` as an array of objects:
     ```json
     [{"name": "...", "aliases": [...], "category": "...", "vault_folder": "...", "source": "domain|extracted"}]
     ```

### Step C: Enrich (Optional)

Only runs if `--with-enrich` is specified or `--mode=enrich`.

Read `domain-packs/<pack>/enrichment-prompt.md` for enrichment instructions.
Read `pack.json` for `privacy_zones` and `processing.confidential_mode`.

**Warn the user first:**
> "Enrichment will restructure documents using Claude's AI. Non-confidential files processed directly. Confidential files: [skipped|processed locally via Ollama] per confidential_mode=[full|zones]. Proceed?"

For each `.md` file in `vault/_INBOX/`:

1. **Check confidentiality**: If file path matches any `privacy_zones` entry where `external_api` is `false`:
   - If `confidential_mode` is `"full"`: Skip this file. Log: "Skipped (confidential)"
   - If `confidential_mode` is `"zones"`: Fall back to local processing:
     ```bash
     python scripts/enrich_notes.py --provider=ollama --file=<path>
     ```

2. **Non-confidential files**: Read the file. Apply the enrichment prompt as your own instructions. Restructure the document:
   - Add a concise Executive Summary at the top
   - Restructure into clean Obsidian markdown with proper headings
   - Improve the YAML frontmatter (accurate type, category, tags)
   - Add a "Related Topics" section with [[wikilink]] suggestions
   - Keep ALL factual content — never remove information, only improve structure
   - Write the enriched version back to the same file

3. **Validate before writing**: Verify the enriched content starts with `---` (valid YAML frontmatter). If not, discard the enrichment and keep the original.

### Step D: Inject Wikilinks

Read `config/master_linklist.json` to get all known entities.

Filter the entity list:
- Remove entities shorter than 3 characters
- Remove entities in the blocklist: the, and, for, its, new, all, can, has, are, was, be, or, is, in, at, by, to, grid, power, energy, solar, wind, project, system, market, policy, plan, data

Sort remaining entities by name length DESCENDING (longest first — prevents "Solar" matching inside "Solar Philippines").

For each `.md` file in `vault/_INBOX/`:
1. Read the file
2. Separate frontmatter from body
3. In the BODY ONLY, for each entity (longest first):
   - Find the FIRST occurrence (case-insensitive, word boundary)
   - SKIP if the occurrence is inside any of these protected regions:
     - Existing `[[wikilinks]]`
     - Inline code (backticks)
     - Code blocks (triple backticks)
     - URLs (http:// or https://)
     - Markdown images `![...](...)` 
     - Markdown links `[...](...)` 
     - HTML tags `<...>`
   - Replace with `[[entity_name]]` if matched text equals entity name
   - Replace with `[[entity_name|matched_text]]` if matched text is an alias
   - Only link FIRST occurrence per entity per document
4. Write the modified file back using Edit (preserve frontmatter exactly)

### Step E: Tag Frontmatter

Read `pack.json` to get `type_inference_patterns`.

For each `.md` file in `vault/_INBOX/`:
1. Read the file and parse existing YAML frontmatter
2. For any MISSING required field, fill in the default:
   - `title`: Derive from filename (replace `-` and `_` with spaces, title-case)
   - `type`: Match filename + first 500 chars of body against `type_inference_patterns`. First match wins. Default: `"document"`
   - `tags`: `[]`
   - `aliases`: `[]`
   - `date_created`: today's date (YYYY-MM-DD)
   - `date_modified`: today's date (ALWAYS update this field)
   - `status`: `"draft"`
   - `confidence`: `"medium"`
3. Never overwrite existing user-set values (except date_modified)
4. Write back using Edit

### Step F: File Notes to Correct Folders

Read `domain-packs/<pack>/vault-structure.json` to get the `type_to_folder` mapping.

For each `.md` file in `vault/_INBOX/`:
1. Read the file's frontmatter to get `type`
2. Look up the target folder in `type_to_folder`. If no match, use the default: `"11 - INTELLIGENCE & ANALYSIS/Market Reports"`
3. Check if target folder exists. If not, create it:
   ```bash
   mkdir -p "vault/<target_folder>"
   ```
4. Check for filename collisions in target folder. If collision, append `_1`, `_2`, etc.
5. Move the file:
   ```bash
   mv "vault/_INBOX/<filename>" "vault/<target_folder>/<filename>"
   ```

### Step G: Rebuild MOC Indexes

Read `domain-packs/<pack>/vault-structure.json` to get the `mocs` mapping (MOC name → folder name).

For each MOC entry:
1. Use Glob to find all `.md` files in `vault/<folder_name>/` (recursive)
2. Read each file's frontmatter to get: title, type, status, date_created
3. Group notes by subfolder
4. Generate MOC markdown:
   ```markdown
   ---
   title: "<MOC Name>"
   type: moc
   tags: [moc, index]
   date_created: <today>
   date_modified: <today>
   ---
   
   # <MOC Name>
   
   > Index for the **<Folder Name>** domain.
   
   ## Overview
   
   *(Add a summary of this domain here)*
   
   ## Notes by Category
   
   ### <Subfolder 1>
   - [[Note A]] `status`
   - [[Note B]]
   
   ### <Subfolder 2>
   ...
   
   ## Recently Added
   - [[Note X]] — date
   
   ## Related MOCs
   - [[HOME]]
   ```
5. Write each MOC to `vault/00 - HOME/<MOC Name>.md`

### Step H: Validate

Use Glob to find all `.md` files in `vault/` (excluding `_TEMPLATES`).

Build a link graph:
- For each note, use Grep to extract all `[[wikilink]]` targets
- Read each note's frontmatter

Check for:
- **Broken links**: wikilink targets that don't match any note name in the vault
- **Orphaned notes**: notes with zero incoming AND zero outgoing links (excluding HOME)
- **Missing frontmatter**: notes without valid YAML frontmatter
- **Empty/short notes**: body content less than 50 characters
- **Draft notes**: status = draft
- **Low confidence**: confidence = low

Write health report to `vault/11 - INTELLIGENCE & ANALYSIS/vault_health_report.md`.

---

## Results Report

After all steps complete, present a structured summary:

```
Pipeline Complete (engine: claude-code)
═══════════════════════════════════════
Converted:   N files (M via Python fallback for DOCX)
Extracted:   N entities across K categories
Enriched:    N files (M skipped for confidentiality)
Linked:      N wikilinks injected
Tagged:      N files with frontmatter updated
Filed:       N files moved to vault folders
MOCs:        N indexes rebuilt
Validation:  N issues found (X broken links, Y orphans, Z missing frontmatter)
```
