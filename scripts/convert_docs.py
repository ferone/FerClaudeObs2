#!/usr/bin/env python3
"""
Agent: CONVERTER
Converts DOCX, PDF, HTML, TXT files in inbox/ to clean Markdown files in vault/_INBOX/
"""

import argparse
import json
import logging
import re
import shutil
from pathlib import Path
from datetime import date, datetime

PROJECT_ROOT = Path(__file__).parent.parent
INBOX_RAW    = PROJECT_ROOT / "inbox"
INBOX_VAULT  = PROJECT_ROOT / "vault" / "_INBOX"
PROCESSED_LOG = PROJECT_ROOT / "config" / "processed_log.json"
LOGS_DIR     = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(exist_ok=True)
INBOX_VAULT.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [CONVERTER] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("converter")

TODAY = date.today().isoformat()


def load_processed_log() -> dict:
    if PROCESSED_LOG.exists():
        return json.loads(PROCESSED_LOG.read_text(encoding="utf-8"))
    return {"processed": [], "last_run": None}


def save_processed_log(data: dict):
    data["last_run"] = datetime.now().isoformat()
    PROCESSED_LOG.write_text(json.dumps(data, indent=2), encoding="utf-8")


def clean_markdown(text: str) -> str:
    """Clean up common markdown conversion artifacts."""
    # Remove excessive blank lines
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    # Remove trailing spaces
    text = re.sub(r'[ \t]+\n', '\n', text)
    # Fix broken wikilinks artifacts
    text = re.sub(r'\\\[', '[', text)
    text = re.sub(r'\\\]', ']', text)
    return text.strip()


def add_basic_frontmatter(content: str, filename: str, source_file: str) -> str:
    """Add minimal frontmatter if not already present."""
    if content.startswith("---"):
        return content  # Already has frontmatter

    title = Path(filename).stem.replace("-", " ").replace("_", " ").title()
    frontmatter = f"""---
title: "{title}"
type: document
tags: []
source: "{source_file}"
date_created: {TODAY}
date_modified: {TODAY}
status: draft
confidence: medium
---

"""
    return frontmatter + content


def convert_docx(file_path: Path) -> str:
    """Convert DOCX to Markdown using mammoth."""
    try:
        import mammoth
        with open(file_path, "rb") as f:
            result = mammoth.convert_to_markdown(f)
        if result.messages:
            for msg in result.messages:
                log.debug(f"  mammoth: {msg}")
        return result.value
    except ImportError:
        log.error("mammoth not installed. Run: pip install mammoth")
        return ""
    except Exception as e:
        log.error(f"DOCX conversion failed for {file_path}: {e}")
        return ""


def convert_pdf(file_path: Path) -> str:
    """Convert PDF to Markdown using pymupdf4llm."""
    try:
        import pymupdf4llm
        return pymupdf4llm.to_markdown(str(file_path))
    except ImportError:
        # Fallback to pdfminer
        try:
            from pdfminer.high_level import extract_text
            text = extract_text(str(file_path))
            return text
        except ImportError:
            log.error("Neither pymupdf4llm nor pdfminer installed.")
            log.error("Run: pip install pymupdf4llm")
            return ""
    except Exception as e:
        log.error(f"PDF conversion failed for {file_path}: {e}")
        return ""


def convert_html(file_path: Path) -> str:
    """Convert HTML to Markdown using markdownify."""
    try:
        from markdownify import markdownify as md
        html = file_path.read_text(encoding="utf-8", errors="replace")
        return md(html, heading_style="ATX", bullets="-")
    except ImportError:
        log.error("markdownify not installed. Run: pip install markdownify")
        return ""
    except Exception as e:
        log.error(f"HTML conversion failed for {file_path}: {e}")
        return ""


def convert_txt(file_path: Path) -> str:
    """Read plain text as-is."""
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        log.error(f"TXT read failed for {file_path}: {e}")
        return ""


def convert_md(file_path: Path) -> str:
    """Already markdown — just read it."""
    return file_path.read_text(encoding="utf-8", errors="replace")


CONVERTERS = {
    ".docx": convert_docx,
    ".doc":  convert_docx,
    ".pdf":  convert_pdf,
    ".html": convert_html,
    ".htm":  convert_html,
    ".txt":  convert_txt,
    ".md":   convert_md,
    ".markdown": convert_md,
}


def process_file(file_path: Path, processed_log: dict) -> bool:
    """Convert a single file and save to vault/_INBOX/"""
    rel_path = str(file_path.relative_to(PROJECT_ROOT))

    if rel_path in processed_log["processed"]:
        log.debug(f"Already processed: {file_path.name}")
        return True

    suffix = file_path.suffix.lower()
    if suffix not in CONVERTERS:
        log.warning(f"Unsupported format: {file_path.name} ({suffix})")
        return False

    log.info(f"Converting: {file_path.name}")

    converter = CONVERTERS[suffix]
    content = converter(file_path)

    if not content:
        log.error(f"  ✗ Empty result for {file_path.name}")
        return False

    content = clean_markdown(content)
    content = add_basic_frontmatter(content, file_path.name, rel_path)

    # Output filename (always .md)
    out_name = file_path.stem + ".md"
    # Handle duplicates
    out_path = INBOX_VAULT / out_name
    counter = 1
    while out_path.exists():
        out_path = INBOX_VAULT / f"{file_path.stem}_{counter}.md"
        counter += 1

    out_path.write_text(content, encoding="utf-8")
    log.info(f"  ✓ → {out_path.relative_to(PROJECT_ROOT)}")

    processed_log["processed"].append(rel_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="Document Converter Agent")
    parser.add_argument("--input", default=str(INBOX_RAW), help="Input directory")
    parser.add_argument("--file", help="Process a single file")
    args = parser.parse_args()

    processed_log = load_processed_log()
    converted = 0
    failed = 0

    if args.file:
        files = [Path(args.file)]
    else:
        input_dir = Path(args.input)
        if not input_dir.exists():
            log.warning(f"Input directory not found: {input_dir}")
            input_dir.mkdir(parents=True, exist_ok=True)
            log.info(f"Created inbox directory: {input_dir}")
            return
        files = [
            f for f in input_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in CONVERTERS
        ]

    if not files:
        log.info("No files to convert.")
        return

    log.info(f"Found {len(files)} file(s) to process")

    for file_path in files:
        success = process_file(file_path, processed_log)
        if success:
            converted += 1
        else:
            failed += 1
        save_processed_log(processed_log)

    log.info(f"Conversion complete: {converted} converted, {failed} failed")


if __name__ == "__main__":
    main()
