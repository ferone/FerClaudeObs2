---
title: "{{pack_display_name}}"
type: dashboard
tags: [home, dashboard]
date_created: {{date}}
date_modified: {{date}}
---

# {{pack_display_name}}

> The strategic brain for Philippine energy market intelligence and Vivant decision-making.

---

## Navigate by Domain

| Domain | MOC | Notes |
|--------|-----|-------|
| Global Context | [[MOC - Global Context]] | Macro forces, geopolitics, commodities |
| PH Energy Market | [[MOC - Philippines Energy Market]] | WESM, pricing, grid zones |
| Regulations | [[MOC - Regulations & Policy]] | DOE, ERC, NGCP rules |
| Grid & Infrastructure | [[MOC - Grid & Infrastructure]] | NGCP, substations, transmission |
| Technologies | [[MOC - Technologies]] | BESS, Solar, Wind, EMS, SCADA |
| Global Suppliers | [[MOC - Global Suppliers]] | PV, battery, inverter, wind |
| PH Market Players | [[MOC - Philippines Market Players]] | Gencos, DUs, IPPs |
| Competitors | [[MOC - Competitors]] | Intelligence on competing players |
| Projects | [[MOC - Projects]] | All project tracking |
| Vivant Internal | [[MOC - Vivant Internal]] | STRICTLY CONFIDENTIAL |
| Intelligence | [[MOC - Intelligence & Analysis]] | Analysis, briefs, forecasts |

---

## Active Priorities

```dataview
TABLE status, category, date_modified
FROM "09 - PROJECTS/Vivant Projects"
WHERE status = "active"
SORT date_modified DESC
LIMIT 10
```

---

## Recently Added

```dataview
TABLE type, category, date_created
FROM ""
WHERE date_created >= date(today) - dur(7 days)
SORT date_created DESC
LIMIT 20
```

---

## Needs Attention

```dataview
TABLE status, confidence
FROM ""
WHERE confidence = "low" OR status = "draft"
SORT date_modified ASC
LIMIT 10
```

---

## Vault Statistics

```dataview
TABLE length(rows) as "Count"
GROUP BY type
```

---

*Last pipeline run: check `logs/pipeline.log`*
