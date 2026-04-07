---
name: pdf-to-markdown
description: Convert PDFs to high-quality markdown using Claude vision with proper table preservation. Splits large PDFs into 10-page chunks processed by parallel agents, then concatenates. Handles both text-layer and scanned (image-only) PDFs. Use when ingesting PDFs where tables, formulas, and structured data must be preserved accurately.
argument-hint: "--source=<pdf-file|folder> [--pages=1-20] [--chunk-size=10] [--output=<vault-path>]"
---

Convert PDFs to high-fidelity markdown using Claude's visual PDF reading capability. Unlike pymupdf `get_text()` which strips table structure, this skill reads each page visually and preserves tables, formulas, charts, and all structured content as proper markdown.

## When to Use This

- Converting regulatory documents, technical codes, or data-heavy PDFs
- Any PDF with tables that must be preserved as markdown tables
- Scanned/image-only PDFs (no text layer)
- Re-processing PDFs that were previously extracted with pymupdf and lost table structure

## Pre-flight

1. Parse `$ARGUMENTS`:
   - `--source=<path>` — **required** — single PDF or folder of PDFs
   - `--pages=X-Y` — optional — process only specific page range
   - `--chunk-size=N` — pages per agent (default: 10)
   - `--output=<path>` — output vault path (default: `vault/_INBOX/`)
2. Read `config/active-pack.json` for domain pack config
3. For each PDF, determine:
   - Total page count (via pymupdf: `len(pymupdf.open(path))`)
   - Whether it has a text layer (via `sum(len(p.get_text()) for p in doc)` — if 0, it's scanned)

## Processing Pipeline

### Step 1: Handle Scanned PDFs (if needed)

If the PDF has NO text layer (0 chars from get_text):
```bash
export PATH="/c/Program Files/Tesseract-OCR:$PATH"
python -m ocrmypdf "<input.pdf>" "<input_ocr.pdf>" --rotate-pages --deskew --language eng
```
This adds a text layer via Tesseract OCR. The OCR'd PDF is used as the source for Claude vision (better rendering).

**Note:** ocrmypdf requires Tesseract installed at `/c/Program Files/Tesseract-OCR/tesseract.exe`. If not available, proceed with the original scanned PDF — Claude vision can still read image pages directly.

### Step 2: Split into Chunks and Launch Parallel Agents

Calculate chunks: `ceil(total_pages / chunk_size)` agents needed.

For a 133-page PDF with chunk_size=10:
- Agent 1: pages 1-10
- Agent 2: pages 11-20
- ...
- Agent 14: pages 131-133

**Launch ALL agents in a single message** for maximum parallelism. Each agent gets this prompt:

```
Read this PDF using the Read tool with pages="X-Y":
<source PDF path>

For EACH page, transcribe ALL content into markdown:

1. **Text content:** Proper markdown with headings (#, ##, ###), bold, italic, lists
2. **Tables:** Convert to proper markdown table syntax:
   | Column 1 | Column 2 | Column 3 |
   |----------|----------|----------|
   | data     | data     | data     |
   Every table in the PDF must appear as a markdown table. Do NOT flatten tables to plain text.
3. **Formulas:** Preserve in LaTeX ($...$) or code blocks
4. **Figures/Charts:** Describe as structured blocks with extracted data points
5. **Numbers:** Keep ALL numerical values EXACTLY as shown — never round or reformat
6. **Page markers:** Add <!-- Page N --> comments for each page

Do NOT summarize or skip any content. Transcribe EVERYTHING.

Write output to: vault/_INBOX/<stem>_partNN.md
Start the file with: <!-- Part NN: Pages X-Y -->
No YAML frontmatter needed.
```

### Step 3: Wait for All Agents to Complete

Monitor agent completion. If any agent fails (e.g., image dimension limit), retry with smaller chunk (5 pages).

### Step 4: Concatenate Parts

After all parts are written:

1. Read all part files in order (`_part01.md`, `_part02.md`, ...)
2. Concatenate into a single markdown body
3. Add YAML frontmatter:
   ```yaml
   ---
   title: "<Document title>"
   type: <inferred type>
   tags: [regulation, <category>]
   document_number: "<doc number>"
   issuing_body: "<issuer>"
   date_issued: "<date>"
   source: "<original PDF filename>"
   source_format: "pdf"
   conversion_method: "claude-vision"
   conversion_date: <today>
   page_count: <N>
   date_created: <today>
   date_modified: <today>
   status: active
   confidence: high
   ---
   ```
4. Inject wikilinks (first occurrence of each entity, using `config/master_linklist.json`)
5. Write final file to the target vault path
6. Delete part files from `vault/_INBOX/`

### Step 5: Verify Table Preservation

After writing the final file:
- Count markdown tables: `grep -c '|---|' <file>`
- Compare against PDF table references (search for "Table " in the content)
- Report: "Tables found: X markdown tables | Y table references in text"

If tables are missing, launch a doc-inspector agent to compare specific pages.

## Error Handling

- **Agent hits image limit:** Retry that chunk with 5 pages instead of 10
- **Scanned PDF + no Tesseract:** Proceed with direct vision read (works for shorter docs)
- **Part file missing after all agents complete:** Re-launch that specific chunk agent
- **Garbled OCR text:** The vision read should override OCR artifacts — Claude reads the page image directly

## Quality Checklist

After conversion, verify:
- [ ] All tables from the PDF appear as markdown tables (`| col | col |` with `|---|---|`)
- [ ] Table of Contents references ("Table N") match actual table count
- [ ] Numerical values are exact (spot-check 3-5 data points)
- [ ] No pages were skipped (check page count markers)
- [ ] Formulas are preserved (not flattened to plain text)
- [ ] Headings hierarchy matches the original document structure

## Example Usage

Single PDF:
```
/pdf-to-markdown --source=vault/_ASSETS/raw/Regulatory/energy-plans/PDP-2023-2050.pdf --output=vault/03 - REGULATIONS & POLICY/Energy Plans/PDP-2023-2050.md
```

Folder of PDFs:
```
/pdf-to-markdown --source=vault/_ASSETS/raw/Regulatory/energy-plans/
```

Custom chunk size for very dense tables:
```
/pdf-to-markdown --source=report.pdf --chunk-size=5
```

## Key Lesson

**Never use pymupdf `get_text()` for table-heavy PDFs.** It extracts raw text flow and destroys all column relationships. Always use Claude vision (this skill) for documents where tables, charts, or structured data must be preserved.

For quick text-only extraction (no tables needed), pymupdf is fine and much faster.
