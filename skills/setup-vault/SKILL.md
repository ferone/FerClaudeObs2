---
name: setup-vault
description: Initialize a new Obsidian vault with a domain pack — creates folder structure, templates, entity registry, MOC indexes, and configures Obsidian plugins.
argument-hint: "[optional: domain pack name like 'philenergy']"
---

Initialize an Obsidian knowledge management vault using a domain pack.

## Step 1: Select Domain Pack

List available domain packs by checking subdirectories of `domain-packs/`:
```bash
ls domain-packs/
```

If `$ARGUMENTS` specifies a pack name, use that. Otherwise, present the available packs to the user and ask them to choose.

## Step 2: Activate Pack

Write `config/active-pack.json`:
```json
{
  "pack": "<selected_pack>",
  "pack_path": "domain-packs/<selected_pack>",
  "activated_at": "<ISO timestamp>"
}
```

## Step 3: Check Prerequisites

1. Verify Python 3 is available: `python --version` or `python3 --version`
2. Install dependencies: `pip install -r requirements.txt`
3. Read the pack's `pack.json` to understand what we're setting up

## Step 4: Run Vault Setup

```bash
python scripts/setup_vault.py
```

This creates:
- All vault folders from vault-structure.json
- Templates in vault/_TEMPLATES/
- HOME.md dashboard
- MOC index files
- Config files (processed_log.json, missing_entities.json)

## Step 5: Configure Obsidian

Generate `.obsidian/` configuration files in the vault:

1. Create `vault/.obsidian/app.json`:
```json
{
  "useMarkdownLinks": false,
  "showFrontmatter": true,
  "newFileLocation": "folder",
  "newFileFolderPath": "_INBOX",
  "attachmentFolderPath": "_ASSETS"
}
```

2. Create `vault/.obsidian/community-plugins.json` with the plugin IDs from pack.json's `obsidian_plugins` list.

## Step 6: Present Results

Show the user:
- Vault location
- Number of folders created
- Templates available
- Plugin installation instructions (they must install via Obsidian UI)
- Next steps: "Drop documents in inbox/ and run /process-docs"
