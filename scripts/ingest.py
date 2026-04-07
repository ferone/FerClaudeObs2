#!/usr/bin/env python3
"""
Philergy Vault Ingest Script
Processes documents one-by-one through the full pipeline:
  copy -> tag frontmatter -> extract entities -> rebuild links -> inject wikilinks -> file to folder -> sanity check

Usage:
  python scripts/ingest.py --source=<file|folder|tree.md> [--batch-size=5] [--dry-run]
"""

import argparse
import json
import os
import re
import shutil
import sys
import logging
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

# -- Paths ----------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
VAULT_DIR = PROJECT_ROOT / "vault"
INBOX_DIR = VAULT_DIR / "_INBOX"
FAILED_DIR = INBOX_DIR / "FAILED"
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(exist_ok=True)
INBOX_DIR.mkdir(exist_ok=True)
FAILED_DIR.mkdir(exist_ok=True)

# -- Logging --------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "ingest.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ingest")

# -- Constants ------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".html", ".htm", ".txt", ".md", ".markdown"}
EXCLUDE_FILENAMES = {
    "README.md", "CLAUDE.md", "CHANGELOG_2026-02-01.md", "treemd.md",
    "CONTRIBUTING.md", "project_catalog.md", "REMAINING_TRANSLATIONS.md",
    "INDEX.md",
}
BLOCKLIST = {
    "the", "and", "for", "its", "new", "all", "can", "has", "are", "was", "be",
    "or", "is", "in", "at", "by", "to", "of", "grid", "power", "energy", "solar",
    "wind", "project", "system", "market", "policy", "plan", "data", "analysis",
    "report", "review", "study", "index", "notes", "summary", "vre", "agc", "ghi",
    "dni", "mq",
}
MIN_ENTITY_LEN = 3
TODAY = date.today().isoformat()


# ===============================================================================
# LOAD DOMAIN PACK CONFIG
# ===============================================================================

def load_pack():
    """Load domain pack configuration."""
    active_path = CONFIG_DIR / "active-pack.json"
    if not active_path.exists():
        log.error("No active domain pack. Run /setup-vault first.")
        sys.exit(1)

    active = json.loads(active_path.read_text(encoding="utf-8"))
    pack_dir = PROJECT_ROOT / active["pack_path"]
    pack_json = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
    entities_json = json.loads((pack_dir / "entities.json").read_text(encoding="utf-8"))
    structure_json = json.loads((pack_dir / "vault-structure.json").read_text(encoding="utf-8"))

    return pack_json, entities_json, structure_json, pack_dir


# ===============================================================================
# SOURCE RESOLUTION
# ===============================================================================

def resolve_source(source_path: str) -> list[Path]:
    """Resolve --source into a flat list of files to process."""
    source = Path(source_path)

    if not source.exists():
        log.error(f"Source not found: {source}")
        sys.exit(1)

    # Check if it's a tree listing file first (before single-file check)
    if source.is_file() and source.suffix == ".md":
        # Read first 20 lines to detect tree listing patterns
        try:
            head = source.read_text(encoding="utf-8").splitlines()[:20]
            head_text = "\n".join(head)
            is_tree = bool(
                re.search(r"## \S+/", head_text)
                or "├──" in head_text
                or "└──" in head_text
                or re.search(r"- \S+\.md\s+[—\-]", head_text)
            )
        except (UnicodeDecodeError, OSError):
            is_tree = False

        if is_tree:
            return parse_tree_listing(source)

        # Not a tree listing — treat as single file
        if source.name not in EXCLUDE_FILENAMES:
            return [source]
        log.warning(f"Excluded: {source.name}")
        return []

    # Single file (non-.md)
    if source.is_file() and source.suffix.lower() in SUPPORTED_EXTENSIONS:
        if source.name not in EXCLUDE_FILENAMES:
            return [source]
        log.warning(f"Excluded: {source.name}")
        return []

    # Directory
    if source.is_dir():
        files = []
        for ext in SUPPORTED_EXTENSIONS:
            files.extend(source.rglob(f"*{ext}"))
        files = [f for f in files if f.name not in EXCLUDE_FILENAMES]
        files.sort(key=lambda p: (str(p.parent), p.name))
        log.info(f"Found {len(files)} files in {source}")
        return files

    log.error(f"Unsupported source: {source}")
    sys.exit(1)


def parse_tree_listing(tree_file: Path) -> list[Path]:
    """Parse a treemd.md-style listing into resolved file paths."""
    base_dir = tree_file.parent
    lines = tree_file.read_text(encoding="utf-8").splitlines()

    files = []
    current_dir = ""
    current_subdir = ""

    for line in lines:
        line = line.rstrip()

        # Section headers: ## analysis/ (24 files + 21 lessons)
        m = re.match(r"^## (\S+?)/?(?:\s.*)?$", line)
        if m:
            current_dir = m.group(1)
            current_subdir = ""
            continue

        # Subdirectory: - **lessons/**  or  - **lithium-battery-industry-2025-12/** (33 files)
        m = re.match(r"^(?:  )?- \*\*(\S+?)/?(?:\*\*.*)?$", line)
        if m:
            current_subdir = m.group(1).rstrip("*")
            continue

        # File entries: - filename.md — description  or    - filename.md — description
        m = re.match(r"^(?:  )*- (\S+\.md)\s+[—\-]", line)
        if m:
            filename = m.group(1)
            if current_subdir:
                rel_path = f"{current_dir}/{current_subdir}/{filename}"
            elif current_dir:
                rel_path = f"{current_dir}/{filename}"
            else:
                rel_path = filename

            # Handle "Root/" prefix
            rel_path = rel_path.replace("Root/", "")
            full_path = base_dir / rel_path

            if full_path.name in EXCLUDE_FILENAMES:
                continue
            if full_path.exists():
                files.append(full_path)

    files.sort(key=lambda p: (str(p.parent), p.name))
    log.info(f"Parsed tree listing: {len(files)} files found")
    return files


# ===============================================================================
# CHINESE DETECTION
# ===============================================================================

def is_chinese(filepath: Path) -> bool:
    """Check if a file is predominantly Chinese by CJK character ratio."""
    try:
        text = filepath.read_text(encoding="utf-8")[:2000]
    except (UnicodeDecodeError, OSError):
        return False

    if not text:
        return False

    cjk_count = sum(1 for c in text if "\u4e00" <= c <= "\u9fff" or "\u3400" <= c <= "\u4dbf")
    alpha_count = sum(1 for c in text if c.isalpha())

    if alpha_count == 0:
        return False

    return (cjk_count / alpha_count) > 0.3


# ===============================================================================
# PHASE 2: CONVERT / COPY TO _INBOX
# ===============================================================================

def copy_to_inbox(source_file: Path) -> Path | None:
    """Copy a markdown file to vault/_INBOX/ with frontmatter."""
    stem = source_file.stem
    dest = INBOX_DIR / f"{stem}.md"

    # Handle duplicates
    counter = 1
    while dest.exists():
        dest = INBOX_DIR / f"{stem}_{counter}.md"
        counter += 1

    try:
        content = source_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        log.error(f"Cannot read {source_file}: {e}")
        return None

    # Check if frontmatter already exists
    has_frontmatter = content.strip().startswith("---")

    if has_frontmatter:
        # Preserve existing frontmatter, update date_modified
        dest.write_text(content, encoding="utf-8")
    else:
        # Add standard frontmatter
        title = stem.replace("-", " ").replace("_", " ").title()
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
        dest.write_text(frontmatter + content, encoding="utf-8")

    return dest


# ===============================================================================
# PHASE 3B: TAG FRONTMATTER
# ===============================================================================

def infer_type(filename: str, body_preview: str, patterns: dict, source_path: str = "") -> str:
    """Infer note type from source path, filename, and body using pack patterns.

    Uses a priority system:
    1. Source directory name (strongest signal)
    2. Filename-only matching against specific types
    3. Body content matching (only for high-specificity types)

    Avoids over-matching on regulation keywords (DOE, ERC, NGCP) that appear
    in every Philippine energy document.
    """
    source_lower = source_path.lower().replace("\\", "/")
    filename_lower = filename.lower()
    combined = (filename_lower + " " + body_preview).lower()

    # Priority 1: Source directory mapping (strongest signal)
    dir_type_map = {
        "/analysis/": "analysis",
        "/analysis/lessons/": "lesson",
        "/research/competitors/": "company",
        "/research/vivant/": "analysis",
        "/research/doe/": "regulation",
        "/research/iemop/": "research",
        "/research/ngcp/": "research",
        "/research/political/": "analysis",
        "/research/factcheck/": "analysis",
        "/research/financial_analysis/": "analysis",
        "/report/": "analysis",
        "/prompts/": "document",
        "/archive/": "document",
        "/securitysummaries/": "securities_research",
        "/bess-en/": "securities_research",
        "/bess-en/lithium-battery-industry": "securities_research",
        "/regulatory/": "regulation",
        "/resources/": "document",
    }

    # Check most specific paths first (longer matches first)
    for dir_pattern, dtype in sorted(dir_type_map.items(), key=lambda x: len(x[0]), reverse=True):
        if dir_pattern in source_lower:
            return dtype

    # Priority 2: Filename-only matching for specific types
    filename_type_map = {
        "lesson": ["lessons", "lesson"],
        "analysis": ["analysis", "deep_analysis", "conclusions", "executive_summary", "master_lessons", "financial_comparison", "competitive_intelligence"],
        "company": ["_deep", "aboitiz", "acen", "meralco", "semirara", "smc_", "first_gen", "citicore", "edc", "gbp", "terra_solar", "spnec"],
        "securities_research": ["lithium", "battery", "storage", "solid-state", "nev", "evtol"],
        "research": ["grid_snapshot", "market_design", "market_performance", "reserve_market", "retail_competition"],
    }

    for dtype, keywords in filename_type_map.items():
        for kw in keywords:
            if kw in filename_lower:
                return dtype

    # Priority 3: Body content matching (only high-specificity patterns)
    specific_patterns = {
        "securities_research": ["securities", "brokerage", "investment strategy", "deep report"],
        "meeting": ["meeting", "minutes", "transcript", "agenda", "attendees", "MOM"],
        "procurement": ["tender", "RFP", "RFQ", "bid", "proposal", "evaluation", "procurement"],
        "quotation": ["quotation", "quote", "pricing", "offer", "commercial proposal", "unit price"],
        "engineering": ["SIS", "SLD", "sizing", "calculation", "compatibility", "specification"],
    }

    for type_name, keywords in specific_patterns.items():
        for kw in keywords:
            if kw.lower() in combined:
                return type_name

    return "analysis"  # Default for energy research documents


def tag_frontmatter(filepath: Path, type_patterns: dict, source_path: str = "") -> str:
    """Add/update YAML frontmatter fields. Returns inferred type."""
    content = filepath.read_text(encoding="utf-8")

    # Parse existing frontmatter
    if content.strip().startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            fm_text = parts[1].strip()
            body = parts[2]
        else:
            fm_text = ""
            body = content
    else:
        fm_text = ""
        body = content

    # Parse frontmatter into dict
    fm = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")

    # Infer type
    body_preview = body[:500]
    if "type" not in fm or fm["type"] == "document":
        fm["type"] = infer_type(filepath.stem, body_preview, type_patterns, source_path)

    # Fill missing fields
    title = filepath.stem.replace("-", " ").replace("_", " ").title()
    fm.setdefault("title", title)
    fm.setdefault("tags", "[]")
    fm.setdefault("aliases", "[]")
    fm.setdefault("date_created", TODAY)
    fm["date_modified"] = TODAY
    fm.setdefault("status", "draft")
    fm.setdefault("confidence", "medium")

    # Rebuild frontmatter
    new_fm_lines = []
    for k, v in fm.items():
        if v in ("[]",):
            new_fm_lines.append(f"{k}: []")
        elif isinstance(v, str) and (" " in v or ":" in v or '"' in v) and not v.startswith("["):
            new_fm_lines.append(f'{k}: "{v}"')
        else:
            new_fm_lines.append(f"{k}: {v}")

    new_content = "---\n" + "\n".join(new_fm_lines) + "\n---\n" + body
    filepath.write_text(new_content, encoding="utf-8")

    return fm["type"]


# ===============================================================================
# PHASE 3A: EXTRACT ENTITIES (REGEX-BASED)
# ===============================================================================

def extract_entities_regex(filepath: Path, domain_entities: dict) -> tuple[int, int]:
    """Extract entities by matching domain entity names against document text.
    Returns (new_count, matched_count).
    """
    content = filepath.read_text(encoding="utf-8")

    # Strip frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        body = parts[2] if len(parts) >= 3 else content
    else:
        body = content

    if len(body.strip()) < 50:
        return 0, 0

    # Load or create registry
    registry_path = CONFIG_DIR / "entity_registry_extracted.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    else:
        registry = {"version": "1.0", "last_updated": TODAY, "entities": {}}

    source_file = str(filepath.relative_to(PROJECT_ROOT))
    new_count = 0
    matched_count = 0

    # Match domain entities against body text
    for cat_name, cat_entities in domain_entities["entities"].items():
        if cat_name not in registry["entities"]:
            registry["entities"][cat_name] = {}

        for entity in cat_entities:
            names_to_check = [entity["name"]] + entity.get("aliases", [])
            found = False

            for name in names_to_check:
                if len(name) < 3:
                    continue
                pattern = r"\b" + re.escape(name) + r"\b"
                if re.search(pattern, body, re.IGNORECASE):
                    found = True
                    break

            if found:
                ename = entity["name"]
                if ename in registry["entities"][cat_name]:
                    registry["entities"][cat_name][ename]["count"] += 1
                    if source_file not in registry["entities"][cat_name][ename]["sources"]:
                        registry["entities"][cat_name][ename]["sources"].append(source_file)
                    matched_count += 1
                else:
                    registry["entities"][cat_name][ename] = {
                        "count": 1,
                        "sources": [source_file],
                        "aliases": entity.get("aliases", []),
                        "vault_note": None,
                    }
                    matched_count += 1

    registry["last_updated"] = datetime.now().isoformat()
    registry_path.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")

    return new_count, matched_count


# ===============================================================================
# PHASE 4: REBUILD MASTER LINK LIST
# ===============================================================================

def rebuild_master_linklist(domain_entities: dict) -> list[dict]:
    """Combine domain + extracted entities into master link list."""
    master = []
    seen = set()

    # Domain entities first
    for cat_name, cat_entities in domain_entities["entities"].items():
        for e in cat_entities:
            key = e["name"].lower()
            if key not in seen:
                master.append({
                    "name": e["name"],
                    "aliases": e.get("aliases", []),
                    "category": cat_name,
                    "vault_folder": e.get("folder", ""),
                    "source": "domain",
                })
                seen.add(key)
                for alias in e.get("aliases", []):
                    seen.add(alias.lower())

    # Extracted entities
    registry_path = CONFIG_DIR / "entity_registry_extracted.json"
    if registry_path.exists():
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        for cat_name, cat_entities in registry["entities"].items():
            for name, data in cat_entities.items():
                key = name.lower()
                if key not in seen:
                    master.append({
                        "name": name,
                        "aliases": data.get("aliases", []),
                        "category": cat_name,
                        "vault_folder": "",
                        "source": "extracted",
                    })
                    seen.add(key)

    linklist_path = CONFIG_DIR / "master_linklist.json"
    linklist_path.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")

    return master


# ===============================================================================
# PHASE 5: INJECT WIKILINKS
# ===============================================================================

def inject_wikilinks(filepath: Path, master: list[dict]) -> int:
    """Inject [[wikilinks]] for first occurrence of each entity. Returns count."""
    content = filepath.read_text(encoding="utf-8")

    # Split frontmatter from body
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parts[0] + "---" + parts[1] + "---"
            body = parts[2]
        else:
            return 0
    else:
        frontmatter = ""
        body = content

    # Build entity match list (name + aliases), sorted by length desc
    match_entries = []
    for e in master:
        name = e["name"]
        if len(name) >= MIN_ENTITY_LEN and name.lower() not in BLOCKLIST:
            match_entries.append({"match": name, "entity": name})
        for alias in e.get("aliases", []):
            if len(alias) >= MIN_ENTITY_LEN and alias.lower() not in BLOCKLIST:
                match_entries.append({"match": alias, "entity": name})

    match_entries.sort(key=lambda x: len(x["match"]), reverse=True)

    # Find protected regions
    def find_protected(text):
        regions = []
        for pattern in [
            r"```.*?```",
            r"`[^`]+`",
            r"\[\[.*?\]\]",
            r"https?://\S+",
            r"\[([^\]]*)\]\([^\)]*\)",
            r"!\[([^\]]*)\]\([^\)]*\)",
        ]:
            for m in re.finditer(pattern, text, re.DOTALL):
                regions.append((m.start(), m.end()))
        return regions

    linked = set()
    link_count = 0

    for entry in match_entries:
        match_text = entry["match"]
        entity_name = entry["entity"]

        if entity_name.lower() in linked:
            continue

        pattern = r"\b" + re.escape(match_text) + r"\b"
        m = re.search(pattern, body, re.IGNORECASE)

        if not m:
            continue

        # Check protected regions
        protected = find_protected(body)
        is_protected = any(m.start() >= ps and m.end() <= pe for ps, pe in protected)
        if is_protected:
            continue

        found_text = m.group(0)
        if found_text == entity_name:
            replacement = f"[[{entity_name}]]"
        else:
            replacement = f"[[{entity_name}|{found_text}]]"

        body = body[: m.start()] + replacement + body[m.end() :]
        linked.add(entity_name.lower())
        link_count += 1

    filepath.write_text(frontmatter + body, encoding="utf-8")
    return link_count


# ===============================================================================
# PHASE 7: FILE TO CORRECT VAULT FOLDER
# ===============================================================================

def file_to_vault(filepath: Path, note_type: str, type_to_folder: dict) -> Path | None:
    """Move file from _INBOX to the correct vault folder based on type."""
    target_folder_name = type_to_folder.get(note_type, "11 - INTELLIGENCE & ANALYSIS/Market Reports")
    target_dir = VAULT_DIR / target_folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    dest = target_dir / filepath.name

    # Handle collisions
    counter = 1
    while dest.exists():
        dest = target_dir / f"{filepath.stem}_{counter}{filepath.suffix}"
        counter += 1

    try:
        shutil.move(str(filepath), str(dest))
        return dest
    except OSError as e:
        log.error(f"Failed to move {filepath} -> {dest}: {e}")
        return None


# ===============================================================================
# PHASE 8: SANITY CHECK
# ===============================================================================

def sanity_check(filepath: Path) -> tuple[bool, str]:
    """Verify file is valid. Returns (ok, message)."""
    if not filepath.exists():
        return False, "File not at destination"

    content = filepath.read_text(encoding="utf-8")

    if not content.strip().startswith("---"):
        return False, "No valid frontmatter"

    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "Malformed frontmatter"

    body = parts[2].strip()
    if len(body) < 50:
        return False, f"Body too short ({len(body)} chars)"

    return True, "OK"


# ===============================================================================
# BATCH BOUNDARY: REBUILD MOCs
# ===============================================================================

def rebuild_mocs(mocs_config: dict):
    """Rebuild all MOC index files."""
    home_dir = VAULT_DIR / "00 - HOME"
    home_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for moc_name, folder_name in mocs_config.items():
        folder_path = VAULT_DIR / folder_name
        if not folder_path.exists():
            continue

        # Find all .md files in the folder
        notes = list(folder_path.rglob("*.md"))
        if not notes:
            continue

        # Group by subfolder
        groups = defaultdict(list)
        for note in notes:
            rel = note.relative_to(folder_path)
            subfolder = str(rel.parent) if str(rel.parent) != "." else "General"
            groups[subfolder].append(note)

        # Build MOC content
        lines = [
            "---",
            f'title: "{moc_name}"',
            "type: moc",
            "tags: [moc, index]",
            f"date_created: {TODAY}",
            f"date_modified: {TODAY}",
            "---",
            "",
            f"# {moc_name}",
            "",
            f"> Index for the **{folder_name}** domain. Auto-generated — do not edit links manually.",
            "",
            "## Notes by Category",
            "",
        ]

        for subfolder in sorted(groups.keys()):
            lines.append(f"### {subfolder}")
            for note in sorted(groups[subfolder], key=lambda n: n.stem):
                lines.append(f"- [[{note.stem}]]")
            lines.append("")

        # Recently added (last 10 by modification time)
        recent = sorted(notes, key=lambda n: n.stat().st_mtime, reverse=True)[:10]
        lines.append("## Recently Added")
        for note in recent:
            mtime = datetime.fromtimestamp(note.stat().st_mtime).strftime("%Y-%m-%d")
            lines.append(f"- [[{note.stem}]] — {mtime}")
        lines.append("")
        lines.append("## Related MOCs")
        lines.append("- [[HOME]]")

        moc_path = home_dir / f"{moc_name}.md"
        moc_path.write_text("\n".join(lines), encoding="utf-8")
        count += 1

    return count


# ===============================================================================
# MAIN
# ===============================================================================

def main():
    parser = argparse.ArgumentParser(description="Philergy Vault Ingest")
    parser.add_argument("--source", required=True, help="File, folder, or tree listing")
    parser.add_argument("--batch-size", type=int, default=5, help="Documents per batch")
    parser.add_argument("--dry-run", action="store_true", help="Parse and report only, don't process")
    args = parser.parse_args()

    # -- Pre-flight --
    pack_json, entities_json, structure_json, pack_dir = load_pack()
    type_patterns = pack_json.get("type_inference_patterns", {})
    type_to_folder = structure_json.get("type_to_folder", {})
    mocs_config = structure_json.get("mocs", {})

    log.info(f"Domain pack: {pack_json.get('display_name', 'Unknown')}")

    # -- Source resolution --
    files = resolve_source(args.source)
    if not files:
        log.error("No files to process.")
        sys.exit(1)

    total = len(files)
    batch_size = args.batch_size
    num_batches = (total + batch_size - 1) // batch_size

    print(f"""
Ingestion Pre-flight
=============================
Source:       {args.source} -> {total} files
Batch size:   {batch_size} ({num_batches} batches)
Domain pack:  {pack_json.get('display_name')}
=============================
""")

    if args.dry_run:
        for i, f in enumerate(files, 1):
            print(f"  {i:3d}. {f.name}")
        print(f"\nDry run complete. {total} files would be processed.")
        return

    # -- Counters --
    total_entities_new = 0
    total_entities_matched = 0
    total_links = 0
    total_filed = 0
    total_translated = 0
    total_chinese_skipped = 0
    failed_files = []

    # -- Batch loop --
    for batch_idx in range(num_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, total)
        batch_files = files[batch_start:batch_end]

        print(f"\n-- Batch {batch_idx + 1}/{num_batches} ----------------------")
        for i, f in enumerate(batch_files, batch_start + 1):
            print(f"  {i}. {f.name}")
        print()

        batch_entities_new = 0
        batch_entities_matched = 0
        batch_links = 0
        batch_filed = 0

        for source_file in batch_files:
            log.info(f"Processing: {source_file.name}")

            # Phase 1: Chinese detection
            if is_chinese(source_file):
                log.warning(f"  [CN] CHINESE detected: {source_file.name} — skipping (use Claude /ingest for translation)")
                total_chinese_skipped += 1
                continue

            # Phase 2: Copy to _INBOX
            inbox_file = copy_to_inbox(source_file)
            if not inbox_file:
                failed_files.append((source_file.name, "Copy failed"))
                continue

            # Phase 3B: Tag frontmatter
            note_type = tag_frontmatter(inbox_file, type_patterns, str(source_file))

            # Phase 3A: Extract entities (regex-based)
            new_ents, matched_ents = extract_entities_regex(inbox_file, entities_json)
            batch_entities_new += new_ents
            batch_entities_matched += matched_ents

            # Phase 4: Rebuild master link list
            master = rebuild_master_linklist(entities_json)

            # Phase 5: Inject wikilinks
            links = inject_wikilinks(inbox_file, master)
            batch_links += links

            # Phase 7: File to vault folder
            dest = file_to_vault(inbox_file, note_type, type_to_folder)
            if not dest:
                failed_files.append((source_file.name, "Filing failed"))
                continue

            # Phase 8: Sanity check
            ok, msg = sanity_check(dest)
            if not ok:
                log.warning(f"  [!] FAILED sanity: {source_file.name} — {msg}")
                shutil.move(str(dest), str(FAILED_DIR / dest.name))
                failed_files.append((source_file.name, msg))
                continue

            batch_filed += 1
            folder_name = dest.parent.relative_to(VAULT_DIR)
            log.info(f"  [OK] {source_file.name} -> {folder_name} | {matched_ents} entities | {links} wikilinks | type={note_type}")

        # -- Batch boundary: MOCs --
        moc_count = rebuild_mocs(mocs_config)

        # -- Batch summary --
        total_entities_new += batch_entities_new
        total_entities_matched += batch_entities_matched
        total_links += batch_links
        total_filed += batch_filed

        remaining = total - batch_end
        print(f"""
-- Batch {batch_idx + 1}/{num_batches} Complete --------------
Processed:    {batch_end - batch_start}/{total} files ({remaining} remaining)
Entities:     {batch_entities_matched} matched
Wikilinks:    {batch_links} injected
Filed:        {batch_filed} files to vault folders
Failed:       {len([f for f in failed_files if f])} files
MOCs:         {moc_count} indexes rebuilt
------------------------------------""")

    # -- Final summary --
    print(f"""
Ingestion Complete
=======================================
Total files:     {total} processed
Chinese docs:    {total_chinese_skipped} skipped (need Claude /ingest)
Entities:        {total_entities_matched} matched across all documents
Wikilinks:       {total_links} total injected
Filed:           {total_filed} files moved to vault folders
MOCs:            rebuilt across {num_batches} batches
Failed:          {len(failed_files)} files
=======================================""")

    if failed_files:
        print("\nFailed Files:")
        for name, reason in failed_files:
            print(f"  - {name} — {reason}")


if __name__ == "__main__":
    main()
