#!/usr/bin/env python3
"""
Agent: VALIDATOR
Runs QA checks on the vault and produces a health report.
"""

import logging
import sys
from pathlib import Path
from datetime import date

# Fix import: add scripts/ directory to sys.path so we can import from build_mocs
SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from build_mocs import validate_vault

PROJECT_ROOT = Path(__file__).parent.parent
VAULT        = PROJECT_ROOT / "vault"
LOGS_DIR     = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [VALIDATOR] %(message)s",
    handlers=[logging.FileHandler(LOGS_DIR / "pipeline.log"), logging.StreamHandler()]
)
log = logging.getLogger("validator")

TODAY = date.today().isoformat()


def main():
    log.info("Running vault validation...")
    report = validate_vault()

    # Print report
    print(f"\n{'='*60}")
    print(f"  Vault Health Report — {TODAY}")
    print(f"{'='*60}\n")

    sections = [
        ("broken_links",        "Broken Links",          "Links pointing to non-existent notes"),
        ("orphaned_notes",      "Orphaned Notes",        "Notes with no connections"),
        ("missing_frontmatter", "Missing Frontmatter",   "Notes without YAML metadata"),
        ("empty_notes",         "Empty/Short Notes",     "Notes with very little content"),
        ("draft_notes",         "Draft Notes",           "Notes still in draft status"),
        ("low_confidence",      "Low Confidence Notes",  "Notes marked as low-confidence"),
    ]

    total_issues = 0
    for key, title, desc in sections:
        items = report.get(key, [])
        total_issues += len(items)
        status = "OK" if not items else f"{len(items)} issues"
        print(f"{title} ({status})")
        if items:
            print(f"  {desc}:")
            for item in items[:10]:  # Show first 10
                print(f"    - {item}")
            if len(items) > 10:
                print(f"    ... and {len(items) - 10} more")
        print()

    print(f"{'─'*60}")
    print(f"Total issues: {total_issues}")

    if total_issues == 0:
        print("Vault is healthy!")
    elif total_issues < 10:
        print("Minor issues to address when convenient.")
    else:
        print("Multiple issues found — run pipeline to fix automatically.")

    print(f"{'='*60}\n")

    # Save report
    report_path = VAULT / "11 - INTELLIGENCE & ANALYSIS" / "vault_health_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Vault Health Report — {TODAY}",
        "",
        f"| Issue Type | Count |",
        f"|-----------|-------|",
    ]
    for key, title, _ in sections:
        lines.append(f"| {title} | {len(report.get(key, []))} |")
    lines += ["", "---", ""]

    for key, title, desc in sections:
        items = report.get(key, [])
        if items:
            lines.append(f"## {title}")
            lines.append(f"*{desc}*")
            lines.append("")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    log.info(f"Report saved → {report_path}")


if __name__ == "__main__":
    main()
