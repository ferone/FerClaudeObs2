---
name: claude-ingest
description: The definitive document ingestion skill. Converts any document (PDF, DOCX, HTML, MD) into high-quality Obsidian vault markdown using Claude vision for PDFs (preserving tables perfectly), with Chinese auto-translation, entity extraction, wikilinks, and intelligent vault filing. Battle-tested on 1000+ pages of Philippine regulatory documents.
argument-hint: "--source=<file|folder|tree.md> [--batch-size=5] [--chunk-size=10] [--with-enrich] [--inspect]"
---

The definitive document-to-vault ingestion skill. Processes documents ONE BY ONE through a complete pipeline, using Claude vision for PDF conversion (never pymupdf get_text which destroys tables). Each document completes all phases before the next begins, so entity discovery is incremental.

---

## CRITICAL RULES — READ BEFORE EVERY RUN

### PDF Conversion

1. **NEVER use pymupdf `get_text()` as the primary PDF conversion method.** It extracts raw text flow and DESTROYS all table structure. A 133-page document with 54 tables produces ZERO tables via get_text(). Always use Claude vision (Read tool with `pages` parameter).

2. **Scanned PDFs (image-only, no text layer):** Check first with pymupdf — if `sum(len(p.get_text()) for p in doc)` returns 0 chars, the PDF is scanned. For scanned PDFs >40 pages, run `ocrmypdf` first to add a text layer via Tesseract:
   ```bash
   export PATH="/c/Program Files/Tesseract-OCR:$PATH"
   python -m ocrmypdf "<input.pdf>" "<output_ocr.pdf>" --rotate-pages --deskew --language eng
   ```
   Then use Claude vision on the OCR'd PDF. For scanned PDFs <=40 pages, Claude vision works directly.

3. **Chunk size: 10 pages per agent** (default). All chunks launch in parallel in a single message. Each agent writes to `vault/_INBOX/<stem>_partNN.md`.

4. **After all parts complete:** Read and concatenate in order, add YAML frontmatter, inject wikilinks, write final file, delete part files.

### Table Preservation

1. **Every table in the PDF MUST appear as a proper markdown table** in the output:
   ```
   | Column 1 | Column 2 | Column 3 |
   |----------|----------|----------|
   | data     | data     | data     |
   ```
2. ALL numerical values preserved EXACTLY as shown in the source — never round, reformat, or omit.
3. After conversion, verify: count `|---|` occurrences in output. If the PDF clearly had tables but the markdown has zero, the conversion FAILED — redo with Claude vision.

### Chinese Documents

1. Detect: Check first 500 chars (or first 2 PDF pages) for CJK characters (Unicode ranges \u4E00-\u9FFF, \u3400-\u4DBF). If >30% CJK, it's Chinese.
2. <=20 pages: Launch ONE `chinese-translator` agent.
3. &gt;20 pages: Launch MULTIPLE parallel `chinese-translator` agents, each handling ~20 pages. Concatenate results after.
4. **Full translation only** — never summarize. Preserve ALL content, tables, figures, data.

### Type Inference Priority

1. **Source directory path** (strongest signal — e.g., `/research/competitors/` -> company)
2. **Filename patterns** (e.g., `deep_analysis_*` -> analysis, `*_verified.md` -> verification)
3. **Body content keywords** (only high-specificity: procurement, quotation, engineering, meeting)
4. **NEVER let generic energy keywords** (DOE, ERC, NGCP, MW, BESS, WESM) force type to "regulation" — these appear in EVERY Philippine energy document
5. **Default:** "analysis" for energy research documents, "document" for unknowns

### Wikilink Injection

1. Sort entities by name length **DESCENDING** ("Solar Philippines" before "Solar")
2. **First occurrence only** per entity per document
3. **Skip protected regions:** `[[existing wikilinks]]`, `` `inline code` ``, ` ```code blocks``` `, URLs, `![images]()`, `[markdown links]()`, HTML tags, YAML frontmatter
4. **Blocklist:** the, and, for, its, new, all, can, has, are, was, be, or, is, in, at, by, to, of, grid, power, energy, solar, wind, project, system, market, policy, plan, data, analysis, report, review, study, index, notes, summary

---

## Pre-flight (Phase 0)

1. Read `config/active-pack.json` — if missing, tell user to run `/setup-vault` first
2. Read domain pack's `pack.json` (privacy zones, type patterns, engine config)
3. Read `domain-packs/<pack>/entities.json` (pre-seeded entities)
4. Read `domain-packs/<pack>/extraction-prompt.md`
5. Read `domain-packs/<pack>/vault-structure.json` (folder mappings, MOC config)
6. Parse `$ARGUMENTS`:
   - `--source=<path>` — **required** — file, folder, or tree listing
   - `--batch-size=N` — documents per batch (default: 5)
   - `--chunk-size=N` — PDF pages per vision agent (default: 10)
   - `--with-enrich` — include AI enrichment step (default: off)
   - `--inspect` — launch doc-inspector after each document (default: off)
7. Resolve source into flat file list (see Source Resolution)
8. Report:
   ```
   Claude Ingest Pre-flight
   =============================
   Source:       [type] -> N files
   Batch size:   B (M batches)
   Chunk size:   C pages/agent
   Enrichment:   [on|off]
   Inspection:   [on|off]
   Domain pack:  [pack display_name]
   =============================
   ```

---

## Source Resolution

### Single File
If `--source` has extension `.pdf`, `.docx`, `.doc`, `.html`, `.htm`, `.txt`, `.md`, `.markdown`:
- Verify file exists
- File list = `[source_path]`

### Directory
If `--source` points to a directory:
- Glob for all supported extensions recursively
- Exclude: `README.md`, `CLAUDE.md`, `CHANGELOG*`, `treemd*.md`, `CONTRIBUTING.md`, `project_catalog.md`, `INDEX.md`
- Sort alphabetically

### Tree Listing File
If `--source` points to a `.md` file whose first 20 lines contain tree-style patterns:
- Parse section headers (`## dirname/`) for directory context
- Parse file entries (`- filename.ext -- description`)
- Parse tree chars (`+--`, `|--`) for nested structure
- Resolve each path relative to tree file's parent directory
- Validate existence, skip missing files with warning

---

## Per-Document Pipeline

Process each document through ALL phases sequentially. Do not start doc N+1 until doc N completes all phases.

### Phase 1: Language Detection

**For PDFs:**
- Use Read tool with `pages: "1-2"` to see first 2 pages
- Count CJK characters vs total alpha characters

**For other files:**
- Read first 500 characters
- Count CJK ratio

**If Chinese (>30% CJK):**
1. Report: `"Chinese document detected: [filename]. Launching translation..."`
2. Determine page count (for PDFs: `len(pymupdf.open(path))`)
3. Launch translation:
   - **<=20 pages:** ONE `chinese-translator` agent:
     ```
     Agent(chinese-translator): "Translate this Chinese document to English markdown.
     Source: [path]. Output to: vault/_INBOX/[stem]_EN.md.
     Full translation, all pages. Write to file."
     ```
   - **>20 pages:** MULTIPLE parallel agents, each ~20 pages:
     ```
     Agent 1: "Translate pages 1-20 -> vault/_INBOX/[stem]_EN_part1.md"
     Agent 2: "Translate pages 21-40 -> vault/_INBOX/[stem]_EN_part2.md"
     ...
     ```
     After all complete: concatenate parts, add frontmatter, delete parts.
4. From this point, pipeline operates on the translated `.md` file
5. Move original to `vault/_ASSETS/originals/`

**If NOT Chinese:** proceed to Phase 2.

### Phase 2: Convert to Markdown

#### PDF Files (.pdf) — CLAUDE VISION METHOD

**Step A: Check for text layer**
```bash
python -c "
import pymupdf
doc = pymupdf.open('<path>')
chars = sum(len(p.get_text()) for p in doc)
pages = len(doc)
print(f'{pages} pages, {chars} chars')
doc.close()
"
```

**Step B: If scanned (0 chars) and >40 pages — OCR first**
```bash
export PATH="/c/Program Files/Tesseract-OCR:$PATH"
python -m ocrmypdf "<source.pdf>" "vault/_INBOX/<stem>_ocr.pdf" --rotate-pages --deskew --language eng
```
Use the OCR'd PDF as the source for vision reading.

**Step C: Calculate chunks and launch parallel agents**

`ceil(total_pages / chunk_size)` agents. For a 133-page PDF with chunk_size=10 = 14 agents.

Launch ALL agents in a single message:
```
Agent(parallel-executor): "Read PDF pages='1-10': <path>
For EACH page, transcribe ALL content into markdown:
1. Text: proper markdown with headings (#, ##, ###), bold, italic, lists
2. Tables: MUST be proper markdown tables:
   | Column 1 | Column 2 | Column 3 |
   |----------|----------|----------|
   | data     | data     | data     |
3. Formulas: preserve in LaTeX or code blocks
4. Figures/Charts: describe with extracted data points
5. Numbers: keep ALL values EXACTLY as shown
6. Add <!-- Page N --> comments for each page
Do NOT summarize — transcribe EVERYTHING.
Write to: vault/_INBOX/<stem>_partNN.md
Start with: <!-- Part NN: Pages X-Y -->"
```

**Step D: Wait for all agents to complete**

Check `vault/_INBOX/<stem>_part*.md` — count parts vs expected. If any missing after agents report done, re-launch that chunk.

**Step E: Concatenate parts**

1. Read all part files in order (sorted by part number)
2. Concatenate into single body
3. Add YAML frontmatter:
   ```yaml
   ---
   title: "<Document title>"
   type: <inferred type>
   tags: []
   source: "<original filename>"
   source_format: "pdf"
   conversion_method: "claude-vision"
   page_count: <N>
   date_created: <today>
   date_modified: <today>
   status: draft
   confidence: medium
   ---
   ```
4. Inject wikilinks into the body (see Phase 4 logic)
5. Write final file to `vault/_INBOX/<stem>.md`
6. Delete all part files
7. Count tables: `grep -c '|---|' <file>` — report count

#### DOCX Files (.docx, .doc)
- Claude cannot read binary DOCX — fall back to Python:
  ```bash
  python scripts/convert_docs.py --file="<path>"
  ```

#### HTML Files (.html, .htm)
- Read with the Read tool
- Convert to markdown: strip script/style tags, convert headings/lists/bold/italic, strip remaining tags
- Write to `vault/_INBOX/` with frontmatter

#### MD Files (.md, .markdown)
- Read with the Read tool
- If no frontmatter, add standard frontmatter block
- Copy to `vault/_INBOX/`

#### TXT Files (.txt)
- Read, wrap in markdown structure, write with frontmatter

**For ALL formats:** handle duplicate filenames with `_1`, `_2` suffixes.

### Phase 3: Extract Entities + Tag Frontmatter

**Extract entities:**
- Read the converted markdown from `vault/_INBOX/`
- Strip YAML frontmatter, skip if body < 50 chars
- Match domain entity names + aliases against body text (regex, word-boundary)
- Merge new entities into `config/entity_registry_extracted.json`:
  - Existing: increment count, add source
  - New: add with count=1, source=[file]
- Report: `"Entities: N new, M matched"`

**Tag frontmatter:**
- Infer type using priority system (see Critical Rules above)
- Fill missing fields: title, type, tags, aliases, dates, status, confidence
- Never overwrite existing user-set values except date_modified
- Write back using Edit

**Rebuild master link list:**
- Combine `entities.json` (domain) + `entity_registry_extracted.json` (extracted)
- Deduplicate by name (case-insensitive), domain entities take priority
- Write to `config/master_linklist.json`

This runs after EVERY document so subsequent documents benefit from newly discovered entities.

### Phase 4: Inject Wikilinks

Read `config/master_linklist.json`. Apply wikilink injection rules (see Critical Rules section).

For each entity (longest first):
1. Find FIRST occurrence in body (case-insensitive, word boundary)
2. Skip if inside protected region
3. Replace: `[[entity]]` or `[[entity|matched_text]]` if alias
4. Track linked entities to prevent duplicates

Write modified file back. Report: `"Wikilinks: N injected"`

### Phase 5: File to Vault Folder

Read `vault-structure.json` -> `type_to_folder` mapping.

1. Look up target folder from type
2. Default if no match: `"11 - INTELLIGENCE & ANALYSIS/Market Reports"`
3. Create target folder if needed: `mkdir -p "vault/<folder>"`
4. Handle filename collisions: append `_1`, `_2`
5. Move: `mv "vault/_INBOX/<file>" "vault/<folder>/<file>"`
6. Report: `"Filed: [filename] -> [folder]"`

### Phase 6: Quality Check

**Standard checks:**
- File exists at destination
- Valid YAML frontmatter (starts with `---`, has required fields)
- Body content > 50 chars
- Type field is recognized

**For PDFs — table verification:**
- Count `|---|` in the output file
- If source PDF clearly had tables (check for "Table" references in content) but markdown has 0 table separators, flag as WARNING

**If `--inspect` flag:**
- Launch `doc-inspector` agent:
  ```
  Agent(doc-inspector): "Compare source [path] against vault note [path].
  Check structural completeness, table preservation, data integrity.
  Report PASS/FAIL/PARTIAL with specific findings."
  ```
- If FAIL verdict: move to `vault/_INBOX/FAILED/`, add `ingestion_error` to frontmatter

**If all checks pass:**
- Report: `"[OK] [filename] -> [folder] | [N entities] | [M wikilinks] | [T tables]"`

**If any check fails:**
- Move to `vault/_INBOX/FAILED/`
- Report: `"[FAIL] [filename] -- [reason]"`

### Phase 7: Batch Boundary (every batch_size docs)

**Rebuild MOC indexes:**
- Read `vault-structure.json` -> `mocs` mapping
- For each MOC: Glob all .md files in the mapped folder, read frontmatter, group by subfolder
- Generate MOC markdown with notes listing, recently added section
- Write to `vault/00 - HOME/<MOC Name>.md`

**Print batch summary:**
```
-- Batch N/M Complete ----------------------
Processed:    B/Total files (R remaining)
Translated:   T Chinese -> English
Converted:    C files (P via PDF vision, D via DOCX fallback, H via HTML, M as markdown)
Tables:       X markdown tables recovered from PDFs
Entities:     E new, F matched existing
Wikilinks:    L injected
Filed:        G files to vault folders
Failed:       J files (see vault/_INBOX/FAILED/)
MOCs:         K indexes rebuilt
--------------------------------------------
```

### Phase 8: Final Summary

```
Claude Ingest Complete
=======================================
Total files:     N processed
Chinese docs:    T translated -> English
PDF conversion:  P files via Claude vision (X tables preserved)
Scanned PDFs:    S preprocessed with Tesseract OCR
Entities:        E new + F matched = G total
Wikilinks:       L total injected
Filed:           H files to vault folders
MOCs:            rebuilt across B batches
Failed:          J files
Inspected:       I files (if --inspect)
=======================================
```

---

## Error Recovery

- **Single document failure:** Log error, move to `vault/_INBOX/FAILED/`, continue to next document. Never crash the batch.
- **Vision agent failure (image limit):** Retry that chunk with `chunk_size / 2` pages.
- **ocrmypdf failure (missing Tesseract):** Warn, attempt direct vision read (works for shorter scanned docs).
- **Translation agent failure:** Flag, skip translation, process as-is.
- **Entity registry corruption:** Back up, create fresh `{"version":"1.0","entities":{}}`.
- **Missing domain pack files:** Warn, skip that phase.

---

## Enrichment (Optional — only with --with-enrich)

If `--with-enrich` is specified, run after Phase 4 (wikilinks) and before Phase 5 (filing):

1. Read `enrichment-prompt.md` from domain pack
2. Check privacy zones: if target folder is in a confidential zone, skip or use local Ollama
3. Apply enrichment: add executive summary, restructure headings, improve tags
4. Validate: enriched content must start with valid YAML frontmatter
5. Keep ALL factual content — never remove information

---

## Relationship to Other Skills

| Skill | Use When |
|-------|----------|
| `/claude-ingest` | **Default for all document ingestion.** Best quality, table preservation, Chinese support. |
| `/process-docs` | Quick batch processing of inbox/ with Python engine fallback. No vision, no table preservation. |
| `/ingest` | Legacy per-document pipeline. Superseded by `/claude-ingest`. |
| `/pdf-to-markdown` | Standalone PDF conversion only (no entity extraction, no filing). Use `/claude-ingest` instead. |
