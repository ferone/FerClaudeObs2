---
name: vault-stats
description: Show comprehensive vault statistics — note counts by type, entity coverage, link density, processing history, and domain pack info.
argument-hint: "[optional: --detailed for per-folder breakdown]"
---

Generate vault statistics. Pure Claude orchestration — no Python scripts needed.

## Gather Data

1. **Total notes**: Count .md files in vault/ (excluding _TEMPLATES, _ASSETS)
2. **Notes by type**: Grep frontmatter `type:` fields across all vault .md files
3. **Notes by folder**: Count .md files per top-level domain folder
4. **Entity stats**: Read `config/entity_registry_extracted.json` — count entities per category
5. **Link stats**: Read `config/master_linklist.json` — count total linkable entities
6. **Processing history**: Read `config/processed_log.json` — count processed files, last run date
7. **Wikilink density**: Grep for `\[\[` patterns, count total, divide by note count
8. **Missing entities**: Read `config/missing_entities.json` — count unresolved

## Present Report

Format as a structured report:

```
Vault Statistics
═══════════════
Active Pack: [pack name]
Total Notes: N
  By Type: company (X), regulation (Y), technology (Z), ...
  By Folder: 01-Global (X), 02-PH Market (Y), ...

Entity Coverage
  Domain Entities: N (pre-seeded)
  Extracted Entities: N (from documents)
  Master Link List: N (combined)
  Missing/Unresolved: N

Link Density
  Total Wikilinks: N
  Avg Links/Note: N.N

Processing
  Files Processed: N
  Last Pipeline Run: [date]
```

If `$ARGUMENTS` contains `--detailed`, add per-subfolder breakdowns.
