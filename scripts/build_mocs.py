#!/usr/bin/env python3
"""
Agent: MOC_BUILDER
Rebuilds all MOC (Map of Content) index files based on current vault contents.
Also moves processed files from _INBOX to the correct vault folder.

Loads domain-specific config from the active domain pack:
- vault-structure.json for FOLDER_TO_MOC (mocs field) and TYPE_TO_FOLDER (type_to_folder field)
"""

import json
import logging
import re
import shutil
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
    format="%(asctime)s [MOC_BUILDER] %(message)s",
    handlers=[logging.FileHandler(LOGS_DIR / "pipeline.log"), logging.StreamHandler()]
)
log = logging.getLogger("moc_builder")

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


def load_vault_structure(pack_path: Path) -> dict:
    """Load vault-structure.json from the active domain pack."""
    vs_file = pack_path / "vault-structure.json"
    if vs_file.exists():
        return json.loads(vs_file.read_text(encoding="utf-8"))
    return {"folders": [], "mocs": {}, "type_to_folder": {}}


def get_note_metadata(md_file: Path) -> dict:
    """Extract frontmatter metadata from a note."""
    content = md_file.read_text(encoding="utf-8", errors="replace")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                return yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
    return {}


def file_note_from_inbox(md_file: Path, type_to_folder: dict) -> Path:
    """Move a note from _INBOX to the correct vault folder based on its type."""
    meta = get_note_metadata(md_file)
    note_type = meta.get("type", "document")

    # Get target folder from pack config, with a sensible fallback
    fallback_folder = type_to_folder.get("document", "_INBOX")
    target_folder_name = type_to_folder.get(note_type, fallback_folder)
    target_folder = VAULT / target_folder_name
    target_folder.mkdir(parents=True, exist_ok=True)

    # Handle duplicate filenames
    dest = target_folder / md_file.name
    if dest.exists():
        stem = md_file.stem
        counter = 1
        while dest.exists():
            dest = target_folder / f"{stem}_{counter}.md"
            counter += 1

    shutil.move(str(md_file), str(dest))
    log.info(f"  Filed: {md_file.name} → {target_folder_name}/")
    return dest


def build_moc_for_folder(folder_name: str, moc_name: str):
    """Rebuild a single MOC file for a given vault folder."""
    folder_path = VAULT / folder_name
    moc_path = VAULT / "00 - HOME" / f"{moc_name}.md"

    if not folder_path.exists():
        return

    # Collect all notes in this folder and subfolders
    notes = []
    for md_file in sorted(folder_path.rglob("*.md")):
        meta = get_note_metadata(md_file)
        rel_path = md_file.relative_to(VAULT)
        subfolder = str(rel_path.parent).replace(folder_name + "/", "").replace(folder_name, "")

        notes.append({
            "name": md_file.stem,
            "type": meta.get("type", "document"),
            "status": meta.get("status", ""),
            "subfolder": subfolder.strip("/") or "Root",
            "date_created": str(meta.get("date_created", "")),
            "path": str(rel_path),
        })

    if not notes:
        return

    # Group by subfolder
    groups = {}
    for note in notes:
        key = note["subfolder"]
        groups.setdefault(key, []).append(note)

    # Build MOC content
    lines = [
        f"---",
        f'title: "{moc_name}"',
        f"type: moc",
        f"tags: [moc, index]",
        f"date_created: {TODAY}",
        f"date_modified: {TODAY}",
        f"---",
        f"",
        f"# {moc_name}",
        f"",
        f"> Index for the **{folder_name}** domain. Auto-generated — do not edit links manually.",
        f"",
        f"## Overview",
        f"",
        f"*(Add a summary of this domain here)*",
        f"",
        f"## Notes by Category",
        f"",
    ]

    for group_name in sorted(groups.keys()):
        group_notes = groups[group_name]
        lines.append(f"### {group_name}")
        lines.append("")
        for note in sorted(group_notes, key=lambda n: n["name"]):
            status_badge = f" `{note['status']}`" if note.get("status") else ""
            lines.append(f"- [[{note['name']}]]{status_badge}")
        lines.append("")

    # Recent additions section
    recent = sorted(notes, key=lambda n: n["date_created"], reverse=True)[:10]
    if recent:
        lines += ["## Recently Added", ""]
        for note in recent:
            lines.append(f"- [[{note['name']}]] — {note['date_created']}")
        lines.append("")

    lines += ["## Related MOCs", "- [[HOME]]", ""]

    moc_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"  Rebuilt: {moc_name} ({len(notes)} notes)")


def update_home_dashboard():
    """Update the HOME.md recent additions section."""
    home_path = VAULT / "00 - HOME" / "HOME.md"
    if not home_path.exists():
        return

    # Find all recently added notes (last 7 days worth)
    all_notes = []
    for md_file in VAULT.rglob("*.md"):
        if "_TEMPLATES" in str(md_file) or "00 - HOME" in str(md_file):
            continue
        meta = get_note_metadata(md_file)
        created = str(meta.get("date_created", ""))
        if created >= str(date.today()):  # Today
            all_notes.append((md_file.stem, created))

    if all_notes:
        log.info(f"  {len(all_notes)} notes added today")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MOC Builder Agent")
    parser.add_argument("--file-inbox", action="store_true",
                        help="Move _INBOX files to correct folders first")
    args = parser.parse_args()

    # Load active pack configuration
    try:
        pack_path, pack_json = load_active_pack()
    except FileNotFoundError as e:
        log.error(str(e))
        return

    # Load domain-specific config from pack
    vault_structure = load_vault_structure(pack_path)
    folder_to_moc = vault_structure.get("mocs", {})
    type_to_folder = vault_structure.get("type_to_folder", {})

    # Step 1: File inbox notes
    if args.file_inbox or True:  # Always do this
        inbox_files = list(INBOX_VAULT.glob("*.md"))
        if inbox_files:
            log.info(f"Filing {len(inbox_files)} notes from _INBOX...")
            for f in inbox_files:
                try:
                    file_note_from_inbox(f, type_to_folder)
                except Exception as e:
                    log.error(f"  Failed to file {f.name}: {e}")

    # Step 2: Rebuild all MOCs
    # folder_to_moc is {moc_name: folder_name} from vault-structure.json
    log.info("Rebuilding MOC index files...")
    for moc_name, folder_name in folder_to_moc.items():
        build_moc_for_folder(folder_name, moc_name)

    # Step 3: Update HOME
    update_home_dashboard()

    log.info("MOC rebuild complete")


if __name__ == "__main__":
    main()


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATOR (separate script logic, importable)
# ─────────────────────────────────────────────────────────────────────────────

def validate_vault():
    """
    QA check on vault health. Returns report dict.
    Run via: python scripts/validate_vault.py
    """
    report = {
        "orphaned_notes": [],      # Notes with no incoming or outgoing links
        "broken_links": [],        # [[links]] that point to non-existent notes
        "missing_frontmatter": [], # Notes without proper frontmatter
        "low_confidence": [],      # Notes marked confidence: low
        "draft_notes": [],         # Notes in draft status
        "empty_notes": [],         # Notes with very little content
    }

    all_notes = {f.stem: f for f in VAULT.rglob("*.md")
                 if "_TEMPLATES" not in str(f)}

    wikilink_pattern = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')

    incoming_links = {name: 0 for name in all_notes}
    outgoing_links = {name: [] for name in all_notes}

    for note_name, note_file in all_notes.items():
        content = note_file.read_text(encoding="utf-8", errors="replace")
        meta = get_note_metadata(note_file)

        # Check frontmatter
        if not meta:
            report["missing_frontmatter"].append(note_name)

        # Check content length
        body = content.split("---", 2)[-1] if "---" in content else content
        if len(body.strip()) < 50:
            report["empty_notes"].append(note_name)

        # Check status/confidence
        if meta.get("confidence") == "low":
            report["low_confidence"].append(note_name)
        if meta.get("status") == "draft":
            report["draft_notes"].append(note_name)

        # Check links
        links = wikilink_pattern.findall(content)
        for link in links:
            link_target = link.split("#")[0].strip()  # Handle section links
            if link_target in all_notes:
                incoming_links[link_target] = incoming_links.get(link_target, 0) + 1
                outgoing_links[note_name].append(link_target)
            else:
                report["broken_links"].append(f"{note_name} → [[{link_target}]]")

    # Find orphans (no incoming AND no outgoing links)
    for note_name in all_notes:
        if (incoming_links.get(note_name, 0) == 0 and
                len(outgoing_links.get(note_name, [])) == 0 and
                note_name not in ["HOME"]):
            report["orphaned_notes"].append(note_name)

    return report
