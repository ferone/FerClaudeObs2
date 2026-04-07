#!/usr/bin/env python3
"""
Agent: LINKER
Injects [[wikilinks]] into markdown files based on the master entity list.
Rules:
  - Link only the FIRST occurrence of each entity per document
  - Never link inside existing [[links]], code blocks, URLs, or frontmatter
  - Sort entities by length (longest first) to avoid partial matches
  - Minimum entity length: 3 characters
"""

import argparse
import json
import logging
import re
import shutil
from pathlib import Path
from datetime import datetime

PROJECT_ROOT  = Path(__file__).parent.parent
VAULT         = PROJECT_ROOT / "vault"
INBOX_VAULT   = VAULT / "_INBOX"
CONFIG        = PROJECT_ROOT / "config"
MASTER_LIST   = CONFIG / "master_linklist.json"
LOGS_DIR      = PROJECT_ROOT / "logs"
BACKUP_DIR    = PROJECT_ROOT / "logs" / "backups"

BACKUP_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [LINKER] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("linker")

# Entities shorter than this won't be auto-linked (too many false positives)
MIN_ENTITY_LENGTH = 3

# These categories won't be auto-linked (too generic)
SKIP_CATEGORIES = {"metrics", "concepts"}

# Entities that should never be auto-linked (too common/ambiguous)
BLOCKLIST = {
    "the", "and", "for", "its", "new", "all", "can", "has",
    "are", "was", "be", "or", "is", "in", "at", "by", "to",
    "grid", "power", "energy", "solar", "wind", "project", "system",
    "market", "policy", "plan", "data"
}


def load_master_linklist() -> list:
    if not MASTER_LIST.exists():
        log.warning(f"Master link list not found: {MASTER_LIST}")
        log.warning("Run extract_entities.py first")
        return []
    return json.loads(MASTER_LIST.read_text(encoding="utf-8"))


def strip_frontmatter(content: str) -> tuple[str, str]:
    """Returns (frontmatter, body)"""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return "---" + parts[1] + "---", parts[2]
    return "", content


def protect_regions(text: str) -> tuple[str, list]:
    """
    Replace regions that should NOT be linked with placeholders.
    Returns (modified_text, [(placeholder, original), ...])
    """
    placeholders = []
    counter = [0]

    def replace(match, prefix="PROTECTED"):
        placeholder = f"⟨{prefix}{counter[0]}⟩"
        counter[0] += 1
        placeholders.append((placeholder, match.group(0)))
        return placeholder

    # Order matters — protect these in sequence
    patterns = [
        (r'\[\[.*?\]\]', "WIKILINK"),           # Existing wikilinks
        (r'`[^`\n]+`', "INLINE_CODE"),          # Inline code
        (r'```[\s\S]*?```', "CODE_BLOCK"),       # Code blocks
        (r'https?://\S+', "URL"),                # URLs
        (r'!\[.*?\]\(.*?\)', "IMAGE"),           # Images
        (r'\[.*?\]\(.*?\)', "MD_LINK"),          # Markdown links
        (r'<[^>]+>', "HTML_TAG"),                # HTML tags
    ]

    for pattern, prefix in patterns:
        text = re.sub(pattern, lambda m, p=prefix: replace(m, p), text, flags=re.DOTALL)

    return text, placeholders


def restore_regions(text: str, placeholders: list) -> str:
    """Restore protected regions."""
    for placeholder, original in reversed(placeholders):
        text = text.replace(placeholder, original)
    return text


def inject_links_into_text(text: str, entities: list) -> tuple[str, int]:
    """
    Inject [[wikilinks]] into text for first occurrence of each entity.
    Returns (modified_text, count_of_links_added)
    """
    # Protect regions we don't want to touch
    protected_text, placeholders = protect_regions(text)

    linked_count = 0
    already_linked = set()  # Track which entities have been linked in this doc

    # Sort by length descending to match longer names first
    sorted_entities = sorted(entities, key=lambda e: len(e["name"]), reverse=True)

    for entity in sorted_entities:
        name = entity["name"]

        # Skip if too short or blocklisted
        if len(name) < MIN_ENTITY_LENGTH or name.lower() in BLOCKLIST:
            continue

        # Build the set of names to search for (name + aliases)
        search_names = [name] + entity.get("aliases", [])

        for search_name in search_names:
            if search_name in already_linked:
                continue
            if len(search_name) < MIN_ENTITY_LENGTH:
                continue

            # Build regex pattern — word boundary match, case-insensitive
            escaped = re.escape(search_name)
            pattern = re.compile(
                r'(?<!\[\[)(?<!\[\[[\w\s]*)(\b' + escaped + r'\b)(?!\]\])',
                re.IGNORECASE
            )

            def make_link(match, entity_name=name, found_name=search_name):
                actual = match.group(1)
                # Use alias syntax if the found text differs from the note name
                if actual.lower() != entity_name.lower():
                    return f"[[{entity_name}|{actual}]]"
                return f"[[{entity_name}]]"

            new_text, n = pattern.subn(make_link, protected_text, count=1)

            if n > 0:
                protected_text = new_text
                already_linked.add(name)
                linked_count += 1
                break  # Found via one of the aliases, move to next entity

    # Restore protected regions
    result = restore_regions(protected_text, placeholders)
    return result, linked_count


def backup_file(file_path: Path):
    """Create a backup of the file before modifying it."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"{file_path.stem}_{timestamp}.md.bak"
    shutil.copy2(file_path, backup_path)


def process_file(md_file: Path, entities: list, make_backup: bool = True) -> int:
    """Inject wikilinks into a single markdown file. Returns count of links added."""
    content = md_file.read_text(encoding="utf-8", errors="replace")

    frontmatter, body = strip_frontmatter(content)

    new_body, links_added = inject_links_into_text(body, entities)

    if links_added == 0:
        return 0

    if make_backup:
        backup_file(md_file)

    new_content = frontmatter + new_body
    md_file.write_text(new_content, encoding="utf-8")
    return links_added


def main():
    parser = argparse.ArgumentParser(description="Wikilink Injector Agent")
    parser.add_argument("--file", help="Process a single file")
    parser.add_argument("--all", action="store_true", help="Process entire vault")
    parser.add_argument("--no-backup", action="store_true", help="Skip file backups")
    args = parser.parse_args()

    entities = load_master_linklist()
    if not entities:
        log.error("No entities loaded. Run extract_entities.py first.")
        return

    log.info(f"Loaded {len(entities)} entities for linking")

    # Filter out skip categories and short names
    entities = [
        e for e in entities
        if e.get("category") not in SKIP_CATEGORIES
        and len(e["name"]) >= MIN_ENTITY_LENGTH
        and e["name"].lower() not in BLOCKLIST
    ]
    log.info(f"  After filtering: {len(entities)} entities will be linked")

    if args.file:
        files = [Path(args.file)]
    elif args.all:
        files = list(VAULT.rglob("*.md"))
        files = [f for f in files if "_TEMPLATES" not in str(f) and "00 - HOME" not in str(f)]
    else:
        # Default: process vault/_INBOX/ only
        files = list(INBOX_VAULT.glob("*.md"))

    if not files:
        log.info("No files to process.")
        return

    log.info(f"Processing {len(files)} file(s)")
    total_links = 0
    files_modified = 0

    for f in files:
        links = process_file(f, entities, make_backup=not args.no_backup)
        if links > 0:
            log.info(f"  {f.name}: +{links} links")
            total_links += links
            files_modified += 1

    log.info(f"Linking complete: {total_links} links added across {files_modified} files")


if __name__ == "__main__":
    main()
