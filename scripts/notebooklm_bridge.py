#!/usr/bin/env python3
"""
NotebookLM Bridge — Bidirectional integration between Obsidian vault and Google NotebookLM.
Uses notebooklm-py for API access.

Usage:
  python scripts/notebooklm_bridge.py list
  python scripts/notebooklm_bridge.py query --notebook="name" --question="question"
  python scripts/notebooklm_bridge.py push --notebook="name" --paths="vault/05 - TECHNOLOGIES"
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG = PROJECT_ROOT / "config"
VAULT = PROJECT_ROOT / "vault"
LOGS_DIR = PROJECT_ROOT / "logs"

LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [NOTEBOOKLM] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("notebooklm_bridge")


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


def load_notebook_registry():
    """Load the notebook registry from config or domain pack."""
    registry_file = CONFIG / "notebook_registry.json"
    if registry_file.exists():
        return json.loads(registry_file.read_text(encoding="utf-8"))

    # Fall back to domain pack's notebooks.json
    try:
        pack_path, _ = load_active_pack()
        notebooks_file = pack_path / "notebooks.json"
        if notebooks_file.exists():
            data = json.loads(notebooks_file.read_text(encoding="utf-8"))
            # Initialize registry from pack template
            registry = {
                "auth": {
                    "method": "browser_cookie",
                    "last_verified": None
                },
                "notebooks": data.get("notebooks", [])
            }
            save_notebook_registry(registry)
            return registry
    except FileNotFoundError:
        pass

    return {"auth": {"method": "browser_cookie", "last_verified": None}, "notebooks": []}


def save_notebook_registry(registry):
    """Save the notebook registry."""
    CONFIG.mkdir(parents=True, exist_ok=True)
    registry_file = CONFIG / "notebook_registry.json"
    registry_file.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def find_notebook(registry, name):
    """Find a notebook by name (case-insensitive partial match)."""
    name_lower = name.lower()
    for nb in registry.get("notebooks", []):
        if name_lower in nb["name"].lower():
            return nb
    return None


def is_path_confidential(path_str, pack_json):
    """Check if a path is in a confidential privacy zone."""
    for zone in pack_json.get("privacy_zones", []):
        if zone["path"] in path_str and zone.get("external_api") is False:
            return True
    return False


def cmd_list(args):
    """List available NotebookLM notebooks."""
    registry = load_notebook_registry()
    notebooks = registry.get("notebooks", [])

    if not notebooks:
        print(json.dumps({"status": "empty", "message": "No notebooks configured. Add notebooks to domain-packs/[pack]/notebooks.json"}))
        return

    result = {
        "status": "ok",
        "count": len(notebooks),
        "notebooks": []
    }
    for nb in notebooks:
        result["notebooks"].append({
            "name": nb["name"],
            "description": nb.get("description", ""),
            "url": nb.get("url", ""),
            "last_synced": nb.get("last_synced"),
            "vault_folders": nb.get("vault_folders", [])
        })

    print(json.dumps(result, indent=2))


def cmd_query(args):
    """Query a NotebookLM notebook."""
    registry = load_notebook_registry()

    notebook = find_notebook(registry, args.notebook)
    if not notebook:
        print(json.dumps({
            "status": "error",
            "message": f"Notebook '{args.notebook}' not found. Available: {[n['name'] for n in registry.get('notebooks', [])]}"
        }))
        sys.exit(1)

    log.info(f"Querying notebook: {notebook['name']}")
    log.info(f"Question: {args.question}")

    try:
        from notebooklm import NotebookLM

        client = NotebookLM()

        # Find or access the notebook by ID or URL
        notebook_id = notebook.get("id", "")
        if not notebook_id and notebook.get("url"):
            # Try to extract ID from URL
            url = notebook["url"]
            if "/notebook/" in url:
                notebook_id = url.split("/notebook/")[-1].split("?")[0].split("/")[0]

        if not notebook_id:
            print(json.dumps({
                "status": "error",
                "message": f"No notebook ID or URL configured for '{notebook['name']}'. Update notebooks.json with the notebook ID or URL."
            }))
            sys.exit(1)

        # Query the notebook
        nb = client.get_notebook(notebook_id)
        response = nb.ask(args.question)

        # Update last queried
        notebook["last_queried"] = datetime.now().isoformat()
        save_notebook_registry(registry)

        result = {
            "status": "ok",
            "notebook": notebook["name"],
            "question": args.question,
            "answer": str(response),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))

    except ImportError:
        print(json.dumps({
            "status": "error",
            "message": "notebooklm-py not installed. Run: pip install 'notebooklm-py[browser]' && playwright install chromium"
        }))
        sys.exit(1)
    except Exception as e:
        log.error(f"NotebookLM query failed: {e}")
        print(json.dumps({
            "status": "error",
            "message": str(e),
            "hint": "Try logging into NotebookLM in your browser first, then retry."
        }))
        sys.exit(1)


def cmd_push(args):
    """Push vault content to a NotebookLM notebook."""
    registry = load_notebook_registry()

    notebook = find_notebook(registry, args.notebook)
    if not notebook:
        print(json.dumps({
            "status": "error",
            "message": f"Notebook '{args.notebook}' not found."
        }))
        sys.exit(1)

    # Load pack for privacy checks
    try:
        _, pack_json = load_active_pack()
    except FileNotFoundError:
        pack_json = {}

    # Collect files to push
    paths = args.paths.split(",")
    files_to_push = []
    skipped_confidential = []

    for p in paths:
        p = p.strip()
        path = PROJECT_ROOT / p if not Path(p).is_absolute() else Path(p)

        if path.is_file() and path.suffix == ".md":
            if is_path_confidential(str(path), pack_json):
                skipped_confidential.append(str(path))
            else:
                files_to_push.append(path)
        elif path.is_dir():
            for md_file in path.rglob("*.md"):
                if is_path_confidential(str(md_file), pack_json):
                    skipped_confidential.append(str(md_file))
                elif "_TEMPLATES" not in str(md_file):
                    files_to_push.append(md_file)

    if skipped_confidential:
        log.warning(f"Skipped {len(skipped_confidential)} confidential files")

    if not files_to_push:
        print(json.dumps({
            "status": "error",
            "message": "No files to push (all may be in confidential zones).",
            "skipped_confidential": len(skipped_confidential)
        }))
        sys.exit(1)

    log.info(f"Pushing {len(files_to_push)} files to notebook: {notebook['name']}")

    try:
        from notebooklm import NotebookLM

        client = NotebookLM()
        notebook_id = notebook.get("id", "")
        if not notebook_id and notebook.get("url"):
            url = notebook["url"]
            if "/notebook/" in url:
                notebook_id = url.split("/notebook/")[-1].split("?")[0].split("/")[0]

        if not notebook_id:
            print(json.dumps({
                "status": "error",
                "message": f"No notebook ID configured for '{notebook['name']}'."
            }))
            sys.exit(1)

        nb = client.get_notebook(notebook_id)

        pushed = 0
        failed = 0
        for md_file in files_to_push:
            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                # Strip frontmatter for cleaner source content
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        content = parts[2].strip()

                title = md_file.stem
                nb.add_source(content, title=title)
                pushed += 1
                log.info(f"  Pushed: {md_file.name}")
            except Exception as e:
                log.error(f"  Failed: {md_file.name}: {e}")
                failed += 1

        # Update sync timestamp
        notebook["last_synced"] = datetime.now().isoformat()
        save_notebook_registry(registry)

        result = {
            "status": "ok",
            "notebook": notebook["name"],
            "pushed": pushed,
            "failed": failed,
            "skipped_confidential": len(skipped_confidential),
            "timestamp": datetime.now().isoformat()
        }
        print(json.dumps(result, indent=2))

    except ImportError:
        print(json.dumps({
            "status": "error",
            "message": "notebooklm-py not installed. Run: pip install 'notebooklm-py[browser]'"
        }))
        sys.exit(1)
    except Exception as e:
        log.error(f"Push failed: {e}")
        print(json.dumps({
            "status": "error",
            "message": str(e)
        }))
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="NotebookLM Bridge")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list command
    subparsers.add_parser("list", help="List available notebooks")

    # query command
    query_parser = subparsers.add_parser("query", help="Query a notebook")
    query_parser.add_argument("--notebook", required=True, help="Notebook name")
    query_parser.add_argument("--question", required=True, help="Question to ask")

    # push command
    push_parser = subparsers.add_parser("push", help="Push vault content to a notebook")
    push_parser.add_argument("--notebook", required=True, help="Notebook name")
    push_parser.add_argument("--paths", required=True, help="Comma-separated vault paths to push")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "push":
        cmd_push(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
