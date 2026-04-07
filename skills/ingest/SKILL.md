---
name: ingest
description: Ingest documents into the vault one-by-one through the full pipeline. Handles any input (file, folder, tree listing), auto-detects Chinese documents for translation, processes in batches of 5, and auto-updates entity registries. Use this when importing documents from external sources with maximum quality control.
argument-hint: "--source=<file|folder|tree.md> [--batch-size=N] [--with-enrich] [--confidential-mode=full|zones]"
---

Ingest documents into the Obsidian vault with full per-document pipeline processing. Each document completes the entire pipeline (convert → extract → tag → link → file → validate) before the next one begins. Documents are processed in batches with summaries between each batch.

## Pre-flight

1. Read `config/active-pack.json` — if missing, tell user to run `/setup-vault` first and stop
2. Read the active domain pack's `pack.json`
3. Read `domain-packs/<pack>/entities.json` (pre-seeded entities)
4. Read `domain-packs/<pack>/extraction-prompt.md`
5. Read `domain-packs/<pack>/vault-structure.json` (folder mappings, MOC config)
6. Parse `$ARGUMENTS`:
   - `--source=<path>` — **required** — file, folder, or tree listing (see Source Resolution)
   - `--batch-size=N` — documents per batch (default: 5)
   - `--with-enrich` — include AI enrichment step (default: off)
   - `--confidential-mode=full|zones` — override confidential handling (default: from pack.json)
7. Resolve source into a flat, ordered file list (see Source Resolution)
8. Report:
   ```
   Ingestion Pre-flight
   ═════════════════════════
   Source:       [file|folder|tree] → N files
   Batch size:   B (ceil(N/B) batches)
   Enrichment:   [on|off]
   Conf. mode:   [full|zones]
   Domain pack:  [pack display_name]
   ═════════════════════════
   Starting batch 1 of M...
   ```

---

## Source Resolution

Determine input type from `--source` and build the file list:

### Single File
If `--source` has an extension in `.pdf`, `.docx`, `.doc`, `.html`, `.htm`, `.txt`, `.md`, `.markdown` and is a single file path:
- Verify file exists
- File list = `[source_path]`

### Directory
If `--source` points to a directory:
- Use Glob to find all files matching `**/*.{pdf,docx,doc,html,htm,txt,md,markdown}` in that directory
- Exclude files matching: `README.md`, `CLAUDE.md`, `CHANGELOG*`, `treemd.md`, `CONTRIBUTING.md`, `project_catalog.md`
- Sort alphabetically for deterministic order
- Report: "Found N files in [directory]"

### Tree Listing File
If `--source` points to a `.md` file whose first 20 lines contain tree-style patterns (`├──`, `└──`, `- filename.ext —`, `- filename.ext —`):
- Parse each line to extract filenames:
  - Lines matching `- <filename>.<ext> —` or `- <filename>.<ext> --` → extract the filename
  - Lines matching `├── <filename>` or `└── <filename>` → extract the filename
  - Lines matching `**<dirname>/** (N files)` → note the subdirectory context
- Track the current subdirectory from section headers (e.g., `## analysis/ (24 files)` sets the prefix to `analysis/`)
- Resolve each filename relative to the tree file's parent directory
- Validate each resolved path exists — warn and skip missing files
- Sort by directory then filename
- Report: "Parsed tree listing: N files found, M missing (skipped)"

---

## Batch Loop

```
Initialize counters: total_entities_new=0, total_entities_matched=0, total_links=0, total_filed=0, total_translated=0, failed_files=[]

For each batch (B documents at a time):
  Print: "── Batch N/M ──────────────────────"
  
  For each document in this batch (SEQUENTIALLY):
    Run Per-Document Pipeline (Phases 1-8)
    Track results per document
  
  Run Batch Boundary Steps:
    → Rebuild all MOC indexes
    → Full vault validation
    → Print batch summary
  
  Continue to next batch automatically

Print Final Summary
```

---

## Per-Document Pipeline

For each individual document, execute these phases in order. **Do not start the next document until all phases complete for the current one.**

### Phase 1: Chinese Detection

Read the document to check for Chinese content:

**For PDF files:**
- Use Read tool with `pages: "1-2"` to read the first 2 pages
- Check extracted text for CJK Unicode characters (ranges: \u4E00-\u9FFF, \u3400-\u4DBF)

**For other files:**
- Use Read tool to read the first 500 characters
- Check for CJK characters in the same ranges

**If Chinese content detected (>30% of characters are CJK):**
1. Report: `"🇨🇳 Chinese document detected: [filename]. Launching translation..."`
2. Determine document size:
   - For PDFs: try reading pages incrementally (1-20, 21-40, ...) until Read returns empty/error to estimate total pages
   - For text files: count total characters
3. Launch translation:
   - **≤20 pages (or ≤40,000 chars)**: Launch ONE `chinese-translator` agent via the Agent tool:
     ```
     Agent: "Translate this Chinese document to English markdown.
     Source file: [path]
     Output to: vault/_INBOX/[stem]_EN.md
     Translate the complete document, all pages. Write the full translation to the output file."
     ```
   - **>20 pages**: Launch MULTIPLE `chinese-translator` agents in parallel, each handling ~20 pages:
     ```
     Agent 1: "Translate pages 1-20 of [path]. Write to vault/_INBOX/[stem]_EN_part1.md"
     Agent 2: "Translate pages 21-40 of [path]. Write to vault/_INBOX/[stem]_EN_part2.md"
     Agent 3: "Translate pages 41-60 of [path]. Write to vault/_INBOX/[stem]_EN_part3.md"
     ...
     ```
     After all agents complete:
     - Read each part file in order
     - Concatenate into a single `vault/_INBOX/[stem]_EN.md` with proper frontmatter
     - Delete the part files
4. Increment `total_translated`
5. **From this point forward, the pipeline operates on the translated markdown file** (`vault/_INBOX/[stem]_EN.md`)
6. Move the original Chinese document to `vault/_ASSETS/originals/` for archival

**If NOT Chinese:** proceed to Phase 2 with the original file.

### Phase 2: Convert to Markdown

Convert the source document to markdown in `vault/_INBOX/`. Skip this phase if the document is already in `vault/_INBOX/` (e.g., from Chinese translation).

**PDF files (.pdf):**
- Read using the Read tool with `pages` parameter in batches of 20 pages
- Clean the text: remove excessive whitespace, fix broken line wraps
- Write as markdown to `vault/_INBOX/<stem>.md`

**DOCX files (.docx, .doc):**
- Claude cannot read binary DOCX — fall back to Python:
  ```bash
  python scripts/convert_docs.py --file="<source_path>"
  ```

**HTML files (.html, .htm):**
- Read with the Read tool
- Convert HTML to clean markdown: strip tags, preserve headings/lists/tables

**TXT files (.txt):**
- Read with the Read tool
- Wrap in markdown structure with headings where appropriate

**MD files (.md, .markdown):**
- Read with the Read tool
- Copy to `vault/_INBOX/<stem>.md`

**For ALL formats, ensure the output file has standard frontmatter:**
```yaml
---
title: "<Title derived from filename>"
type: document
tags: []
source: "<original source path>"
date_created: <today YYYY-MM-DD>
date_modified: <today YYYY-MM-DD>
status: draft
confidence: medium
---
```

If frontmatter already exists (e.g., from translation step), preserve it.

**Handle duplicates:** If `vault/_INBOX/<stem>.md` already exists, append `_1`, `_2`, etc.

**Update processed log:** Read `config/processed_log.json`, add the source file path to the `processed` array, write back.

### Phase 3: Extract Entities + Tag Frontmatter (PARALLEL)

These two operations run **in parallel** — launch both as agents in a single message, then wait for both to complete.

#### 3A: Extract Entities

Read the converted markdown file from `vault/_INBOX/`.
Strip YAML frontmatter. Skip if body content < 50 characters.

Analyze the document content and extract named entities into these categories:
- `companies`: Company names
- `organizations`: Government bodies, regulatory agencies
- `regulations`: Laws, circulars, orders (with document numbers)
- `technologies`: Technology names and acronyms
- `projects`: Named projects
- `people`: Person names (with role if mentioned)
- `locations`: Geographic locations
- `concepts`: Market concepts, financial terms, industry jargon
- `products`: Specific product names or models

Use the extraction prompt from `domain-packs/<pack>/extraction-prompt.md` as guidance.
Cross-reference with pre-seeded entities in `entities.json` to recognize known entities.

**Merge into registry:**
Read `config/entity_registry_extracted.json` (create if missing with `{"version":"1.0","entities":{}}`)

For each extracted entity:
- If entity already exists in registry: increment `count`, add source file to `sources` array → count as `matched`
- If entity is NEW (not in registry AND not in domain entities.json): add with `count: 1`, `sources: [file]`, `aliases: []`, `vault_note: null` → count as `new`

Write updated registry back to `config/entity_registry_extracted.json`.
Report: `"Entities: N new, M matched existing"`

#### 3B: Tag Frontmatter

Read `pack.json` → `type_inference_patterns`.
Read the converted markdown file.
Parse existing YAML frontmatter.

For any MISSING required field, fill in:
- `title`: Derive from filename (replace `-` and `_` with spaces, title-case)
- `type`: Match filename + first 500 chars of body against `type_inference_patterns`. First match wins. Default: `"document"`
- `tags`: `[]`
- `aliases`: `[]`
- `date_created`: today's date YYYY-MM-DD (set once, don't overwrite)
- `date_modified`: today's date YYYY-MM-DD (ALWAYS update)
- `status`: `"draft"`
- `confidence`: `"medium"`

Never overwrite existing user-set values except `date_modified`.
Write back using Edit.

### Phase 4: Rebuild Master Link List

After Phase 3 completes (both parallel operations done):

1. Read `domain-packs/<pack>/entities.json` (pre-seeded entities with folder mappings)
2. Read `config/entity_registry_extracted.json` (all extracted entities)
3. Combine into a single deduplicated list:
   - Domain entities take priority (they have folder mappings and aliases)
   - Extracted entities that match a domain entity by name (case-insensitive) are merged (count/sources added)
   - Truly new extracted entities get `source: "extracted"` and no vault_folder
4. Write combined list to `config/master_linklist.json` as an array:
   ```json
   [{"name": "...", "aliases": [...], "category": "...", "vault_folder": "...", "source": "domain|extracted"}]
   ```

This runs after **every document** so subsequent documents in the batch benefit from newly discovered entities.

### Phase 5: Inject Wikilinks

Read `config/master_linklist.json` to get all known entities.

**Filter the entity list:**
- Remove entities shorter than 3 characters
- Remove entities in blocklist: the, and, for, its, new, all, can, has, are, was, be, or, is, in, at, by, to, of, grid, power, energy, solar, wind, project, system, market, policy, plan, data, analysis, report, review, study, index, notes, summary

**Sort remaining entities by name length DESCENDING** (longest first — "Solar Philippines" before "Solar").

Read the markdown file from `vault/_INBOX/`.
Separate frontmatter from body.

**In the BODY ONLY**, for each entity (longest first):
1. Find the FIRST occurrence (case-insensitive, word boundary match)
2. **SKIP if the occurrence is inside a protected region:**
   - Existing `[[wikilinks]]`
   - Inline code (backticks)
   - Code blocks (triple backticks)
   - URLs (`http://` or `https://`)
   - Markdown images `![...](...)` 
   - Markdown links `[...](...)` 
   - HTML tags `<...>`
   - YAML frontmatter
3. Replace with `[[entity_name]]` if matched text equals entity name
4. Replace with `[[entity_name|matched_text]]` if matched text is an alias
5. Only link the FIRST occurrence per entity per document
6. Track total links injected

Write the modified file back using Edit (preserve frontmatter exactly).
Report: `"Wikilinks: N injected"`

### Phase 6: Enrich (Optional)

**Only runs if `--with-enrich` was specified.**

Read `domain-packs/<pack>/enrichment-prompt.md`.
Read `pack.json` for `privacy_zones` and `processing.confidential_mode`.

**Check confidentiality:**
- Determine where this file WILL be filed (based on type → folder mapping)
- If target folder matches a `privacy_zones` entry with `"external_api": false`:
  - If `confidential_mode` is `"full"`: Skip. Report: `"Enrichment skipped (confidential)"`
  - If `confidential_mode` is `"zones"`: Fall back to local:
    ```bash
    python scripts/enrich_notes.py --provider=ollama --file="<path>"
    ```
- If target folder matches `"external_api": "approval_required"`:
  - Report: `"File targets a sensitive zone. Enrichment requires approval."` and skip unless user has pre-approved

**For non-confidential files:**
1. Read the file
2. Apply the enrichment prompt as your own instructions. Restructure:
   - Add a concise Executive Summary at the top
   - Restructure into clean Obsidian markdown with proper headings
   - Improve YAML frontmatter (more accurate type, category, tags)
   - Add a "Related Topics" section with `[[wikilink]]` suggestions
   - Keep ALL factual content — never remove information, only improve structure
3. Validate the enriched content starts with `---` (valid YAML frontmatter). If not, discard and keep original.
4. Write the enriched version back to the same file

### Phase 7: File to Correct Vault Folder

Read `vault-structure.json` → `type_to_folder` mapping.
Read the file's frontmatter to get `type`.

1. Look up the target folder: `type_to_folder[type]`. Default if no match: `"11 - INTELLIGENCE & ANALYSIS"`
2. Create the target folder if it doesn't exist:
   ```bash
   mkdir -p "vault/<target_folder>"
   ```
3. Check for filename collisions in target folder. If collision, append `_1`, `_2`, etc.
4. Move the file:
   ```bash
   mv "vault/_INBOX/<filename>" "vault/<target_folder>/<filename>"
   ```
5. Report: `"Filed: [filename] → [target_folder]"`

### Phase 8: Per-Document Sanity Check

Verify:
1. File exists at the destination path
2. File has valid YAML frontmatter (starts with `---`, has required fields)
3. Body content is > 50 characters
4. The `type` field is a recognized type

If any check fails:
- Create `vault/_INBOX/FAILED/` if it doesn't exist
- Move the file there with an error marker in frontmatter: `ingestion_error: "<description>"`
- Add to `failed_files` list
- Report: `"⚠ FAILED: [filename] — [reason]"`

If all checks pass:
- Report: `"✓ [filename] → [target_folder] | [N entities] | [M wikilinks]"`

---

## Batch Boundary Steps

After each batch of B documents completes:

### Rebuild MOC Indexes

Read `vault-structure.json` → `mocs` mapping (MOC name → folder name).

For each MOC entry:
1. Use Glob to find all `.md` files in `vault/<folder_name>/` (recursive)
2. Read each file's frontmatter: title, type, status, date_created
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
   
   > Index for the **<Folder Name>** domain. Auto-generated — do not edit links manually.
   
   ## Overview
   *(Add a summary of this domain here)*
   
   ## Notes by Category
   
   ### <Subfolder 1>
   - [[Note A]] `status`
   - [[Note B]] `status`
   
   ## Recently Added
   - [[Note X]] — YYYY-MM-DD
   
   ## Related MOCs
   - [[HOME]]
   ```
5. Write each MOC to `vault/00 - HOME/<MOC Name>.md`

### Vault Validation

Use Glob to find all `.md` files in `vault/` (excluding `_TEMPLATES` and `_ASSETS`).

Check for:
- **Broken links**: `[[wikilink]]` targets that don't match any note filename in the vault
- **Orphaned notes**: notes with zero incoming AND zero outgoing links (excluding HOME and MOC files)
- **Missing frontmatter**: notes without valid YAML frontmatter
- **Empty/short notes**: body content < 50 characters
- **Draft notes**: status = draft (informational, not an error)

Write health report to `vault/11 - INTELLIGENCE & ANALYSIS/vault_health_report.md`.

### Batch Summary

```
── Batch N/M Complete ──────────────
Processed:    B/Total files (R remaining)
Translated:   T Chinese → English
Converted:    C files to markdown
Entities:     X new, Y matched existing
Wikilinks:    L injected
Filed:        F files to vault folders
Failed:       E files (see vault/_INBOX/FAILED/)
MOCs:         M indexes rebuilt
Validation:   V issues (B broken links, O orphans)
────────────────────────────────────
Continuing to batch N+1...
```

---

## Final Summary

After all batches complete:

```
Ingestion Complete
═══════════════════════════════════════
Total files:     N processed
Chinese docs:    T translated → English
Converted:       C files to markdown
Entities:        X new entities added to registry
                 Y matched existing entities
Wikilinks:       L total injected across all documents
Filed:           F files moved to vault folders
MOCs:            M indexes rebuilt (across B batches)
Validation:      V total issues
Failed:          E files (listed below)
═══════════════════════════════════════
```

If any files failed, list them:
```
Failed Files:
  - [filename] — [reason]
  - [filename] — [reason]
```

---

## Error Recovery

- **Single document failure**: Log the error, move to `vault/_INBOX/FAILED/`, continue to next document. Never crash the entire pipeline on one file.
- **Translation agent failure**: Report the failure, skip translation, and attempt to process the document as-is (it may still have some usable content in mixed Chinese/English).
- **Entity registry corruption**: If `entity_registry_extracted.json` is malformed, back it up and create a fresh one. Re-extract entities for the current batch.
- **Missing domain pack files**: If extraction-prompt.md or enrichment-prompt.md is missing, skip that step and warn the user.

---

## Relationship to /process-docs

`/ingest` does NOT replace `/process-docs`. They serve different purposes:

| | `/process-docs` | `/ingest` |
|---|---|---|
| **Processing model** | Step-by-step across all files | All steps per file, then next file |
| **Input** | `inbox/` directory | Any file, folder, or tree listing |
| **Chinese detection** | No | Yes, with parallel translation agents |
| **Entity growth** | Batch — entities found after linking step | Incremental — each doc enriches the next |
| **Summaries** | One final summary | Per-batch + final |
| **Best for** | Quick batch processing of inbox | Importing external document collections |
