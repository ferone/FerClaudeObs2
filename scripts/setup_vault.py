#!/usr/bin/env python3
"""
Intelligence Platform -- First-Time Vault Setup
Run this ONCE before anything else: python scripts/setup_vault.py

Loads all domain-specific configuration (folders, templates, MOCs, home dashboard)
from the active domain pack instead of hardcoded values.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent.parent
VAULT = PROJECT_ROOT / "vault"
CONFIG = PROJECT_ROOT / "config"

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


def create_moc(name: str, folder_ref: str) -> str:
    return f"""---
title: "{name}"
type: moc
tags: [moc, index]
date_created: {TODAY}
date_modified: {TODAY}
---

# {name}

> Index of all notes in the **{folder_ref}** domain.

## Overview

*(Update this summary as the domain grows)*

## Key Notes


## All Notes in This Domain

```dataview
TABLE type, status, date_modified as "Updated"
FROM "{folder_ref}"
SORT date_modified DESC
```

## Related MOCs
- [[HOME]]

"""


def install_dependencies():
    """Install Python dependencies from project root requirements.txt."""
    requirements_file = PROJECT_ROOT / "requirements.txt"
    if requirements_file.exists():
        print("Installing Python dependencies from requirements.txt...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )
        print("[OK] Dependencies installed")
    else:
        print("[WARN] No requirements.txt found at project root -- skipping dependency install")


def check_ollama(pack_json: dict):
    """Check Ollama connectivity and model availability."""
    ollama_config = pack_json.get("ollama", {})
    endpoint = ollama_config.get("endpoint", "http://localhost:11434")
    recommended_model = ollama_config.get("model_extraction", "qwen2.5:32b")

    try:
        import requests
        r = requests.get(f"{endpoint}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            print(f"[OK] Ollama running -- models: {', '.join(models) if models else 'none pulled yet'}")
            # Check if recommended model (or a variant) is available
            model_base = recommended_model.split(":")[0]
            if not any(model_base in m for m in models):
                print(f"  [WARN] Recommend pulling: ollama pull {recommended_model}")
        else:
            print("[WARN] Ollama not responding -- entity extraction will be limited")
    except Exception:
        print(f"[WARN] Ollama not reachable at {endpoint}")
        print(f"  Install from https://ollama.com and run: ollama pull {recommended_model}")


def setup():
    pack_path, pack_json = load_active_pack()
    display_name = pack_json.get("display_name", "Intelligence Platform")

    print(f"\n=== {display_name} -- First-Time Setup ===\n")

    # Load vault structure from domain pack
    vault_structure_file = pack_path / "vault-structure.json"
    if not vault_structure_file.exists():
        print(f"✗ vault-structure.json not found in pack: {pack_path}")
        sys.exit(1)
    vault_structure = json.loads(vault_structure_file.read_text(encoding="utf-8"))

    folders = vault_structure.get("folders", [])
    mocs = vault_structure.get("mocs", {})

    # 1. Create directory structure
    print("Creating vault folder structure...")
    for folder in folders:
        (VAULT / folder).mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "inbox").mkdir(exist_ok=True)
    (PROJECT_ROOT / "logs").mkdir(exist_ok=True)
    print(f"[OK] Created {len(folders)} vault folders")

    # 2. Create templates from pack's templates/ directory
    print("Creating note templates...")
    tmpl_dir = VAULT / "_TEMPLATES"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    pack_templates_dir = pack_path / "templates"
    template_count = 0
    if pack_templates_dir.exists():
        for tmpl_file in pack_templates_dir.glob("*.md"):
            content = tmpl_file.read_text(encoding="utf-8")
            dest = tmpl_dir / tmpl_file.name
            dest.write_text(content, encoding="utf-8")
            template_count += 1
    print(f"[OK] Created {template_count} templates")

    # 3. Create HOME.md from pack's home-dashboard.md
    print("Creating HOME dashboard...")
    home_source = pack_path / "home-dashboard.md"
    if home_source.exists():
        home_content = home_source.read_text(encoding="utf-8")
        # Replace template placeholders
        home_content = home_content.replace("{{pack_display_name}}", display_name)
        home_content = home_content.replace("{{date}}", TODAY)
    else:
        # Fallback: minimal HOME.md
        home_content = f"""---
title: "{display_name}"
type: dashboard
tags: [home, dashboard]
date_created: {TODAY}
date_modified: {TODAY}
---

# {display_name}

> Knowledge vault dashboard.

*Last pipeline run: check `logs/pipeline.log`*
"""
    home_dir = VAULT / "00 - HOME"
    home_dir.mkdir(parents=True, exist_ok=True)
    (home_dir / "HOME.md").write_text(home_content, encoding="utf-8")
    print("[OK] HOME.md created")

    # 4. Create MOC files from vault-structure.json mocs field
    print("Creating MOC index files...")
    for moc_name, folder_ref in mocs.items():
        moc_path = VAULT / "00 - HOME" / f"{moc_name}.md"
        if not moc_path.exists():
            moc_path.write_text(create_moc(moc_name, folder_ref), encoding="utf-8")
    print(f"[OK] Created {len(mocs)} MOC files")

    # 5. Create processed log
    processed_log = CONFIG / "processed_log.json"
    if not processed_log.exists():
        CONFIG.mkdir(parents=True, exist_ok=True)
        processed_log.write_text(json.dumps({"processed": [], "last_run": None}, indent=2), encoding="utf-8")
    print("[OK] Initialized processed_log.json")

    # 6. Create missing entities tracker
    missing = CONFIG / "missing_entities.json"
    if not missing.exists():
        missing.write_text(json.dumps({"missing": []}, indent=2), encoding="utf-8")
    print("[OK] Initialized missing_entities.json")

    # 7. Create .obsidian config directory hint
    obsidian_hint = VAULT / ".obsidian" / "README.txt"
    obsidian_hint.parent.mkdir(exist_ok=True)
    obsidian_hint.write_text(
        "Obsidian will auto-create its config files here when you open the vault.\n"
        "Install recommended plugins from the domain pack's obsidian_plugins list.\n",
        encoding="utf-8"
    )

    # 8. Check Ollama
    print("\nChecking Ollama connection...")
    check_ollama(pack_json)

    # 9. Install dependencies
    print("\nInstalling Python packages...")
    try:
        install_dependencies()
    except Exception as e:
        print(f"[WARN] Dependency install failed: {e}")
        print("  Run manually: pip install -r requirements.txt")

    # 10. Summary
    print(f"\n=== Setup Complete ===")
    print(f"\n[OK] Vault created at: {VAULT}")
    print(f"[INBOX] Drop documents in: {PROJECT_ROOT / 'inbox'}")
    print(f"[RUN]  Run pipeline: python scripts/pipeline.py --mode=full")
    print(f"\n[OPEN] Open Obsidian, click 'Open folder as vault', and select:")
    print(f"   {VAULT}")

    # Show recommended plugins from pack
    plugins = pack_json.get("obsidian_plugins", [])
    if plugins:
        print(f"\n[PLUGINS] Install these Obsidian plugins (Settings -> Community Plugins):")
        for plugin in plugins:
            print(f"   - {plugin}")


if __name__ == "__main__":
    setup()
