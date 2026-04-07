#!/usr/bin/env python3
"""
Agent: TAGGER
Adds or updates YAML frontmatter on all notes in vault/_INBOX/
Uses entity registry and filename patterns to infer type and category.

Loads type_inference_patterns from the active domain pack's pack.json
instead of using hardcoded patterns.
"""

import argparse
import json
import logging
import re
import yaml
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent.parent
VAULT        = PROJECT_ROOT / "vault"
INBOX_VAULT  = VAULT / "_INBOX"
CONFIG       = PROJECT_ROOT / "config"
LOGS_DIR     = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TAGGER] %(message)s",
    handlers=[logging.FileHandler(LOGS_DIR / "pipeline.log"), logging.StreamHandler()]
)
log = logging.getLogger("tagger")

TODAY = date.today().isoformat()


def load_active_pack():
    """Load the active domain pack configuration."""
    active_pack_file = CONFIG / "active-pack.json"
    if not active_pack_file.exists():
        raise FileNotFoundError(
            "No active domain pack. Run /setup-vault or create config/active-pack.json"
        )
    active = json.loads(active_pack_file.read_text(encoding="utf-8"))
    pack_path = PROJECT_ROOT / active["pack_path"]
    pack_json = json.loads((pack_path / "pack.json").read_text(encoding="utf-8"))
    return pack_path, pack_json


def build_type_patterns(pack_json: dict) -> list:
    """
    Build type inference patterns from pack.json's type_inference_patterns.

    Pack format:
        "type_inference_patterns": {
            "regulation": ["DOE", "ERC", "NGCP", "RA", "DC", "circular", "order"],
            "project": ["project", "MW", "MWh", "construction", "COD"],
            ...
        }

    Returns list of (compiled_regex, type_name) tuples.
    """
    patterns_config = pack_json.get("type_inference_patterns", {})
    type_patterns = []

    for type_name, keywords in patterns_config.items():
        if not keywords:
            continue
        # Build a regex that matches any of the keywords as whole words
        escaped_keywords = [re.escape(kw) for kw in keywords]
        pattern_str = r'\b(' + '|'.join(escaped_keywords) + r')\b'
        type_patterns.append((pattern_str, type_name))

    return type_patterns


def infer_type(filename: str, content: str, type_patterns: list) -> str:
    text = (filename + " " + content[:500]).lower()
    for pattern, type_name in type_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return type_name
    return 'document'


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse existing frontmatter. Returns (fm_dict, body_text)."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
                return fm, parts[2]
            except yaml.YAMLError:
                pass
    return {}, content


def write_frontmatter(fm: dict, body: str) -> str:
    """Serialize frontmatter back to string."""
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_str}---{body}"


def update_frontmatter(md_file: Path, type_patterns: list) -> bool:
    """Add or update frontmatter on a single note."""
    content = md_file.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(content)

    changed = False

    # Set defaults if missing
    title = fm.get("title", md_file.stem.replace("-", " ").replace("_", " ").title())
    if "title" not in fm:
        fm["title"] = title
        changed = True

    if "type" not in fm:
        fm["type"] = infer_type(md_file.name, body, type_patterns)
        changed = True

    if "tags" not in fm:
        fm["tags"] = []
        changed = True

    if "aliases" not in fm:
        fm["aliases"] = []
        changed = True

    if "date_created" not in fm:
        fm["date_created"] = TODAY
        changed = True

    if "date_modified" not in fm:
        fm["date_modified"] = TODAY
        changed = True
    else:
        fm["date_modified"] = TODAY
        changed = True

    if "status" not in fm:
        fm["status"] = "draft"
        changed = True

    if "confidence" not in fm:
        fm["confidence"] = "medium"
        changed = True

    if changed:
        md_file.write_text(write_frontmatter(fm, body), encoding="utf-8")
    return changed


def main():
    parser = argparse.ArgumentParser(description="Frontmatter Tagger Agent")
    parser.add_argument("--all", action="store_true", help="Process entire vault")
    parser.add_argument("--file", help="Process single file")
    args = parser.parse_args()

    # Load active pack configuration
    try:
        _, pack_json = load_active_pack()
    except FileNotFoundError as e:
        log.error(str(e))
        return

    # Build type patterns from pack config
    type_patterns = build_type_patterns(pack_json)
    log.info(f"Loaded {len(type_patterns)} type inference patterns from domain pack")

    if args.file:
        files = [Path(args.file)]
    elif args.all:
        files = [f for f in VAULT.rglob("*.md") if "_TEMPLATES" not in str(f)]
    else:
        files = list(INBOX_VAULT.glob("*.md"))

    updated = 0
    for f in files:
        if update_frontmatter(f, type_patterns):
            updated += 1

    log.info(f"Frontmatter updated: {updated}/{len(files)} files")


if __name__ == "__main__":
    main()
