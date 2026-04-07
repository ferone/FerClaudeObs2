#!/usr/bin/env python3
"""
Intelligence Platform — Master Pipeline Orchestrator
Usage: python scripts/pipeline.py --mode=[full|convert|extract|link|mocs|validate|brief]

Loads domain-specific configuration from the active domain pack.
"""

import argparse
import subprocess
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
VAULT_DIR    = PROJECT_ROOT / "vault"
INBOX_DIR    = PROJECT_ROOT / "inbox"
LOGS_DIR     = PROJECT_ROOT / "logs"
CONFIG_DIR   = PROJECT_ROOT / "config"
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"

LOGS_DIR.mkdir(exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("pipeline")


def load_active_pack():
    """Load the active domain pack configuration."""
    active_pack_file = CONFIG_DIR / "active-pack.json"
    if not active_pack_file.exists():
        raise FileNotFoundError(
            "No active domain pack. Run /setup-vault or create config/active-pack.json"
        )
    active = json.loads(active_pack_file.read_text(encoding="utf-8"))
    pack_path = PROJECT_ROOT / active["pack_path"]
    pack_json = json.loads((pack_path / "pack.json").read_text(encoding="utf-8"))
    return pack_path, pack_json


# ── Pipeline steps ─────────────────────────────────────────────────────────────
STEPS = {
    "convert":  "scripts/convert_docs.py",
    "extract":  "scripts/extract_entities.py",
    "enrich":   "scripts/enrich_notes.py",
    "link":     "scripts/inject_links.py",
    "tag":      "scripts/add_frontmatter.py",
    "mocs":     "scripts/build_mocs.py",
    "validate": "scripts/validate_vault.py",
    "brief":    "scripts/generate_brief.py",
}

FULL_PIPELINE = ["convert", "extract", "link", "tag", "mocs", "validate"]

def run_step(step_name: str, extra_args: list = None) -> bool:
    script = PROJECT_ROOT / STEPS[step_name]
    if not script.exists():
        log.warning(f"Script not found: {script} — skipping")
        return True

    cmd = [sys.executable, str(script)] + (extra_args or [])
    log.info(f"▶ Running step: {step_name}")
    result = subprocess.run(cmd, capture_output=False)

    if result.returncode != 0:
        log.error(f"✗ Step '{step_name}' failed with code {result.returncode}")
        return False

    log.info(f"✓ Step '{step_name}' completed")
    return True


def run_full_pipeline(display_name: str, with_enrich: bool = False, input_path: str = None):
    steps = FULL_PIPELINE.copy()
    if with_enrich:
        steps.insert(2, "enrich")  # after extract, before link

    log.info(f"═══ {display_name} Pipeline — FULL RUN — {datetime.now().isoformat()} ═══")
    log.info(f"Steps: {' → '.join(steps)}")

    results = {}
    for step in steps:
        extra = ["--input", input_path] if input_path and step == "convert" else None
        success = run_step(step, extra)
        results[step] = "✓" if success else "✗"
        if not success:
            log.error(f"Pipeline aborted at step: {step}")
            break

    log.info("═══ Pipeline Summary ═══")
    for step, status in results.items():
        log.info(f"  {status} {step}")


def main():
    # Load active pack to get display name
    try:
        _, pack_json = load_active_pack()
        display_name = pack_json.get("display_name", "Intelligence Platform")
    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)

    parser = argparse.ArgumentParser(
        description=f"{display_name} — Pipeline Orchestrator"
    )
    parser.add_argument(
        "--mode",
        choices=["full", "convert", "extract", "enrich", "link", "tag", "mocs", "validate", "brief"],
        default="full",
        help="Pipeline mode to run"
    )
    parser.add_argument("--input", help="Input path (for convert mode)")
    parser.add_argument("--file", help="Process a single file")
    parser.add_argument("--with-enrich", action="store_true",
                        help="Include AI enrichment step (requires API approval)")
    args = parser.parse_args()

    # Confirm enrich with user
    if args.with_enrich or args.mode == "enrich":
        print("\n⚠  ENRICHMENT MODE: Document content will be sent to Claude/Gemini API.")
        print("   Only NON-CONFIDENTIAL documents should be in inbox/ for this run.")
        confirm = input("   Proceed? (yes/no): ").strip().lower()
        if confirm != "yes":
            log.info("Enrichment cancelled by user.")
            args.with_enrich = False
            if args.mode == "enrich":
                sys.exit(0)

    if args.mode == "full":
        run_full_pipeline(display_name, with_enrich=args.with_enrich, input_path=args.input)
    elif args.mode == "brief":
        run_step("brief")
    else:
        extra = ["--input", args.input] if args.input else None
        if args.file:
            extra = ["--file", args.file]
        run_step(args.mode, extra)


if __name__ == "__main__":
    main()
