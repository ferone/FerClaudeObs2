#!/usr/bin/env python3
"""
Interactive Regulatory Document Ingest
Processes all documents from LongTermForecasting/Regulatory into the Philergy vault.
PDFs are FULLY extracted to markdown (all pages, no truncation).
HTMLs are converted to clean markdown.
Each document gets proper frontmatter, wikilinks, and vault filing.
"""

import pymupdf
import json
import os
import re
import sys
from pathlib import Path
from datetime import date

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
VAULT = PROJECT_ROOT / "vault"
REG_BASE = Path("C:/Development Projects/LongTermForecasting/Regulatory")
TODAY = date.today().isoformat()

# ── Load entities for wikilink matching ────────────────────────────────────
with open(PROJECT_ROOT / "config/master_linklist.json", "r", encoding="utf-8") as f:
    master = json.load(f)

BLOCKLIST = {
    "the", "and", "for", "its", "new", "all", "can", "has", "are", "was", "be",
    "or", "is", "in", "at", "by", "to", "of", "grid", "power", "energy", "solar",
    "wind", "project", "system", "market", "policy", "plan", "data", "analysis",
    "report", "review", "study", "index", "notes", "summary", "vre", "agc", "ghi",
    "dni", "mq",
}

match_entries = []
for e in master:
    name = e["name"]
    if len(name) >= 3 and name.lower() not in BLOCKLIST:
        match_entries.append({"match": name, "entity": name})
    for alias in e.get("aliases", []):
        if len(alias) >= 3 and alias.lower() not in BLOCKLIST:
            match_entries.append({"match": alias, "entity": name})
match_entries.sort(key=lambda x: len(x["match"]), reverse=True)


def inject_wikilinks(body):
    """Inject [[wikilinks]] for first occurrence of each entity."""
    linked = set()
    count = 0
    for entry in match_entries:
        match_text = entry["match"]
        entity_name = entry["entity"]
        if entity_name.lower() in linked:
            continue
        pattern = r"\b" + re.escape(match_text) + r"\b"
        m = re.search(pattern, body, re.IGNORECASE)
        if m:
            # Skip if inside existing wikilink
            pre = body[max(0, m.start() - 100) : m.start()]
            if "[[" in pre and "]]" not in pre:
                continue
            found = m.group(0)
            repl = f"[[{entity_name}]]" if found == entity_name else f"[[{entity_name}|{found}]]"
            body = body[: m.start()] + repl + body[m.end() :]
            linked.add(entity_name.lower())
            count += 1
    return body, count


def extract_full_pdf(filepath):
    """Extract ALL pages of a PDF to markdown. No truncation."""
    try:
        doc = pymupdf.open(str(filepath))
        pages = []
        for i, page in enumerate(doc):
            text = page.get_text()
            if text.strip():
                pages.append(f"<!-- Page {i+1} -->\n\n{text}")
        doc.close()
        return "\n\n---\n\n".join(pages), len(doc)
    except Exception as e:
        return f"[PDF extraction failed: {e}]", 0


def read_html_to_markdown(filepath):
    """Read HTML and convert to clean markdown."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Remove script and style tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

        # Convert some HTML to markdown
        text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1", text, flags=re.DOTALL)
        text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1", text, flags=re.DOTALL)
        text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1", text, flags=re.DOTALL)
        text = re.sub(r"<h4[^>]*>(.*?)</h4>", r"#### \1", text, flags=re.DOTALL)
        text = re.sub(r"<br\s*/?>", "\n", text)
        text = re.sub(r"<p[^>]*>", "\n\n", text)
        text = re.sub(r"</p>", "", text)
        text = re.sub(r"<li[^>]*>", "- ", text)
        text = re.sub(r"</li>", "\n", text)
        text = re.sub(r"<strong>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL)
        text = re.sub(r"<em>(.*?)</em>", r"*\1*", text, flags=re.DOTALL)
        text = re.sub(r"<b>(.*?)</b>", r"**\1**", text, flags=re.DOTALL)
        text = re.sub(r"<i>(.*?)</i>", r"*\1*", text, flags=re.DOTALL)

        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean up whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = text.strip()

        return text
    except Exception as e:
        return f"[HTML read failed: {e}]"


# ── Document metadata from tree listing ────────────────────────────────────
# format: stem -> (doc_number, year, description)
DOC_META = {
    "RA-7638_DOE-Act": ("RA 7638", "1992", "Department of Energy Act: Creates the DOE with supervisory control over all energy programs"),
    "RA-9513_Renewable-Energy-Act": ("RA 9513", "2008", "Renewable Energy Act: FIT, RPS, GEOP, Net Metering, 7-year income tax holiday"),
    "RA-11234_EVOSS-Act": ("RA 11234", "2019", "Energy Virtual One-Stop Shop Act: online synchronous permitting with auto-approval"),
    "RA-11285_Energy-Efficiency-Act": ("RA 11285", "2019", "Energy Efficiency and Conservation Act: Designated Establishments, CECOs/CEMs, MEP standards"),
    "RA-11361_Anti-Obstruction-Power-Lines": ("RA 11361", "2019", "Anti-Obstruction of Power Lines Act: eminent domain for grid operators"),
    "RA-11592_LPG-Industry-Regulation": ("RA 11592", "2021", "LPG Industry Regulation Act: importing, refilling, cylinder safety regulation"),
    "RA-12120_Natural-Gas-Industry-Act": ("RA 12120", "2025", "Natural Gas Industry Development Act: downstream gas regulation and LNG framework"),
    "RA-12305_Nuclear-Energy-Safety-Act": ("RA 12305", "2025", "Nuclear Energy Safety Act: establishes PhilATOM, legal framework for SMRs"),
    "DC2026-01-0003_Dispatch-Below-Pmin": ("DC2026-01-0003", "2026", "Dispatch Below Pmin: allows dispatch below Minimum Stable Load during high VRE oversupply"),
    "DC2024-06-0019_Ancillary-Services-Monitoring": ("DC2024-06-0019", "2024", "Ancillary Services Monitoring: WESM Manual, compliance metrics and penalties"),
    "DC2024-01-0005_Forecast-Accuracy-Standard": ("DC2024-01-0005", "2024", "Forecast Accuracy Standard: financial penalties for VRE forecast deviations"),
    "DC2024-01-0004_Registration-RE-Units": ("DC2024-01-0004", "2024", "Registration of RE Units: WESM registration criteria for renewable energy generators"),
    "DC2024-01-0003_Max-Capacity-Declarations": ("DC2024-01-0003", "2024", "Maximum Capacity Declarations: prevents artificial capacity withholding for scarcity pricing"),
    "DC2024-01-0002_Dispute-Resolution": ("DC2024-01-0002", "2024", "Dispute Resolution: amendments to WESM DRA for retail market disputes"),
    "DC2023-08-0024_Billing-Compensation-Formula": ("DC2023-08-0024", "2023", "Billing Compensation Formula: ensures generators are financially whole during market intervention"),
    "DC2022-12-0039_WESM-Mindanao": ("DC2022-12-0039", "2022", "WESM Mindanao: declares commercial operation of WESM in the Mindanao Grid"),
    "DC2022-11-0036_SSRG-Reserve-Market": ("DC2022-11-0036", "2022", "SSRG Reserve Market: System Security and Reliability Guidelines and Dispatch Protocol"),
    "DC2021-08-0026_Market-Surveillance": ("DC2021-08-0026", "2021", "Market Surveillance: WESM Rules for Surveillance, Enforcement, and Compliance"),
    "DOE-Adv-2024-08-001_Reserve-Market-Resumption": ("DOE-Adv-2024-08-001", "2024", "Reserve Market Resumption: full commercial operations after testing/suspension"),
    "DOE-Adv-2024-03-001_Reserve-Market-Guidelines": ("DOE-Adv-2024-03-001", "2024", "Reserve Market Guidelines: interim pricing and settlement procedures"),
    "DC2023-01-0004_GEOP-Amendments": ("DC2023-01-0004", "2023", "GEOP Amendments: enables contestable consumers to contract directly with RE suppliers"),
    "DC2022-10-0031_RE-Preferential-Dispatch": ("DC2022-10-0031", "2022", "RE Preferential Dispatch: all renewable energy gets priority dispatch in WESM"),
    "DC2022-06-0026_REM-Rules-Amendments": ("DC2022-06-0026", "2022", "REM Rules Amendments: updates REC trading and RE certificate registration"),
    "DC2019-11-0014_EEC-Act-IRR": ("DC2019-11-0014", "2019", "EE&C Act IRR: energy audits for Designated Establishments, CECO/CEM appointments"),
    "ERC-Case-2025-150_FIT-All-2026": ("ERC-Case-2025-150", "2025", "FIT-All 2026: approves FIT-All rate of PhP 0.2011/kWh for CY 2026"),
    "ERC-Res-01-2021_Revised-Practice-Rules": ("ERC-Res-01-2021", "2021", "Revised Practice Rules: integrates eWISE portal for electronic filings"),
    "ERC-Res-09-2020_Electronic-Filings": ("ERC-Res-09-2020", "2020", "Electronic Filings: guidelines for electronic applications and virtual hearings"),
    "ERC-Res-16-2014_COC-Rules": ("ERC-Res-16-2014", "2014", "COC Rules: Certificates of Compliance for generation companies"),
    "ERC-Res-13-2024_Omnibus-Retail-Rules": ("ERC-Res-13-2024", "2024", "Omnibus Retail Rules: Customer Choice Programs, contestable customers (500kW+)"),
    "ERC-Res-08-2021_GEOP-Rules": ("ERC-Res-08-2021", "2021", "GEOP Rules: enables consumers to procure 100% clean energy from RE suppliers"),
    "ERC-Res-07-2021_Mitigating-Measure": ("ERC-Res-07-2021", "2021", "Mitigating Measure: price cap and market power abuse prevention in WESM"),
    "ERC-Case-2024-166_Market-Fees": ("ERC-Case-2024-166", "2024", "Market Fees: PEMC/IEMOP operational funding for CY 2024-2027"),
    "ERC-Case-2024-006_Market-Interventions": ("ERC-Case-2024-006", "2024", "Market Interventions: addresses WESM pricing anomalies"),
    "ERC-Case-2023-002_PDM-Co-Optimized": ("ERC-Case-2023-002", "2023", "PDM Co-Optimized: Price Determination Methodology for Co-Optimized Energy and Reserve Market"),
    "ERC-Case-2017-042_PDM-WESM": ("ERC-Case-2017-042", "2017", "PDM WESM: foundational Price Determination Methodology for the WESM spot market"),
    "Philippine-Grid-Code-2016": ("PGR", "2016", "Philippine Grid Code: master transmission grid technical standard, 500+ pages"),
    "Philippine-Distribution-Code-2017": ("PDR", "2017", "Philippine Distribution Code: distribution network standard, embedded generators"),
    "WESM-Rules-Consolidated": ("WESM Rules", "", "Consolidated WESM Market Rules: binding commercial framework for electricity trading"),
    "OATS-Rules-2022": ("OATS", "2022", "Open Access Transmission Service Rules: third-party access, wheeling charges, SIS"),
    "WESM-Manual-PCSD": ("WESM-PCSD", "2024", "Central Scheduling and Dispatch Manual v4.0: capacity declarations and scheduling"),
    "WESM-Manual-Metering": ("WESM-Metering", "", "Metering Standards and Procedures Issue 12.0: revenue metering for WESM settlement"),
    "WESM-Manual-Administered-Price": ("WESM-AP", "", "Administered Price Determination: emergency/intervention pricing methodology"),
    "WESM-Manual-Enforcement-Compliance": ("WESM-EC", "", "Enforcement and Compliance Procedures Issue 1.0: penalty frameworks"),
    "WESM-Manual-Ancillary-Services": ("WESM-AS", "2024", "Ancillary Services Monitoring Manual Issue 1.2: compliance metrics"),
    "WESM-Manual-GEOP-Procedures": ("WESM-GEOP", "", "GEOP Retail Procedures: contestable customer participation operations"),
    "DC2024-06-0018_Revised-Omnibus-RE-Guidelines": ("DC2024-06-0018", "2024", "Revised Omnibus RE Guidelines: ESS provisions, full foreign ownership, RESC procedures"),
    "ADB-ESS-Philippines-Report": ("ADB-ESS", "", "ADB Report on Energy Storage Systems in the Philippine Electric Power Industry"),
    "ERC-Res-17-2023_Revised-COC-Rules": ("ERC-Res-17-2023", "2023", "Revised COC Rules: explicitly covers DER entities including standalone BESS"),
    "ETP-Battery-Storage-Market-Report": ("ETP-BESS", "", "Energy Transition Partnership: Battery Storage Market Mechanism for Philippines"),
    "HB-6676-ESS-Act-Committee-Report": ("HB-6676", "2026", "ESS Act Committee Report: Energy Storage Systems Act passed House 192-3"),
    "Draft-2023-ESS-Amendment-Policy": ("Draft-ESS", "2023", "Draft ESS Amendment Policy: precursor to DC2026-02-0008 for BESS WESM participation"),
    "PEP-2023-2050-Vol-I": ("PEP Vol.I", "2023", "Philippine Energy Plan Vol.I: Overview and Cross-Cutting Strategies, 35% RE by 2030"),
    "PEP-2023-2050-Vol-II": ("PEP Vol.II", "2023", "Philippine Energy Plan Vol.II: Sector Plans for power, oil, gas, coal, RE"),
    "PEP-2023-2050-Vol-III": ("PEP Vol.III", "2023", "Philippine Energy Plan Vol.III: Annexes, statistical tables, demand projections"),
    "PDP-2023-2050": ("PDP", "2023", "Power Development Plan: 22-25 GW BESS by 2050, 154 GW total capacity target"),
    "NGCP-TDP-2022-2040": ("NGCP-TDP", "2022", "NGCP Transmission Development Plan: PhP 485.2B investment, 2,148 ckt-km lines"),
    "Offshore-Wind-Roadmap-Philippines": ("OSW Roadmap", "", "World Bank/ESMAP Offshore Wind Roadmap: 178 GW potential, 21 GW by 2040"),
    "NTER-2023-2032": ("NTER", "2023", "National Total Electrification Roadmap: 100% household electrification by 2028"),
    "NREP-2020-2040": ("NREP", "2020", "National Renewable Energy Program: 102 GW additional RE capacity by 2040"),
    "OECD-Clean-Energy-Finance-Roadmap-Philippines": ("OECD-CEF", "", "OECD Clean Energy Finance Roadmap: USD 300B+ investment needed by 2040"),
    "NEECP-Roadmap-2023-2050": ("NEECP", "2023", "National Energy Efficiency and Conservation Plan: 24% economy-wide energy savings"),
    "RA-11697_EVIDA": ("RA 11697", "2022", "Electric Vehicles and Charging Stations Act: EV regulatory framework and incentives"),
    "EO-12-2023_Zero-Tariff-EVs": ("EO 12/2023", "2023", "Zero tariff on electric vehicles until 2028"),
    "EO-30-2017_EICC": ("EO 30/2017", "2017", "Energy Investment Coordinating Council: 30-day approval target for energy projects"),
    "EO-21-2023_Offshore-Wind": ("EO 21/2023", "2023", "Offshore Wind Development Policy and Administrative Framework"),
    "PD-1586_EIS-System": ("PD 1586", "1978", "Environmental Impact Statement System: all power plants require ECC"),
    "DC2015-03-0001_Must-Dispatch": ("DC2015-03-0001", "2015", "Must-Dispatch framework for intermittent RE (solar/wind) and FIT biomass"),
    "DC2021-11-0036_GEAP-Guidelines": ("DC2021-11-0036", "2021", "Green Energy Auction Program: competitive bidding for RE with GET contracts"),
    "DC2022-05-0016_DSM-Additional": ("DC2022-05-0016", "2022", "Additional Demand-Side Management policy for industrial/commercial energy management"),
    "IEMOP-Reserve-Market-Operating-Guidelines": ("IEMOP-RMOG", "2024", "Reserve Market Operating Guidelines: reserve scheduling, dispatch, and settlement"),
    "NGCP-Ancillary-Services-Bulletin-2024": ("NGCP-AS-Bulletin", "2024", "NGCP Ancillary Services Bulletin: AS procurement summary, pricing, requirements"),
}

# ── Directory to vault folder mapping ──────────────────────────────────────
DIR_MAP = {
    "republic-acts": ("03 - REGULATIONS & POLICY/Republic Acts", "republic_act", "Congress of the Philippines"),
    "doe-circulars-wesm": ("03 - REGULATIONS & POLICY/DOE Circulars WESM", "doe_circular", "Department of Energy"),
    "doe-circulars-re": ("03 - REGULATIONS & POLICY/DOE Circulars RE", "doe_circular", "Department of Energy"),
    "doe-circulars-ee": ("03 - REGULATIONS & POLICY/DOE Circulars EE", "doe_circular", "Department of Energy"),
    "erc-issuances": ("03 - REGULATIONS & POLICY/ERC Issuances", "erc_issuance", "Energy Regulatory Commission"),
    "technical-codes": ("03 - REGULATIONS & POLICY/Technical Codes", "technical_code", "Various"),
    "bess-ess": ("03 - REGULATIONS & POLICY/BESS & ESS", "regulation", "Various"),
    "energy-plans": ("03 - REGULATIONS & POLICY/Energy Plans", "energy_plan", "Various"),
    "executive-orders": ("03 - REGULATIONS & POLICY/Executive Orders", "regulation", "Office of the President"),
    "re-implementing": ("03 - REGULATIONS & POLICY/RE Implementing", "doe_circular", "Department of Energy"),
    "market-competition": ("03 - REGULATIONS & POLICY/Market Competition", "doe_circular", "Department of Energy"),
    "ancillary-services": ("03 - REGULATIONS & POLICY/Ancillary Services", "regulation", "IEMOP/NGCP"),
}


def process_all():
    downloads = REG_BASE / "downloads"
    total = 0
    links_total = 0
    skipped = 0

    for subdir in sorted(downloads.iterdir()):
        if not subdir.is_dir():
            continue
        dir_name = subdir.name
        if dir_name not in DIR_MAP:
            print(f"  SKIP dir: {dir_name}")
            continue

        vault_folder, doc_type, default_issuer = DIR_MAP[dir_name]
        target_dir = VAULT / vault_folder
        target_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== {dir_name} -> {vault_folder} ===")

        for filepath in sorted(subdir.iterdir()):
            if filepath.suffix.lower() not in (".pdf", ".html"):
                continue

            stem = filepath.stem
            meta = DOC_META.get(stem)
            if not meta:
                print(f"  SKIP (no metadata): {filepath.name}")
                skipped += 1
                continue

            doc_number, doc_year, description = meta

            # Extract FULL content
            if filepath.suffix.lower() == ".pdf":
                body_text, page_count = extract_full_pdf(filepath)
                format_note = f"PDF ({page_count} pages, {filepath.stat().st_size // 1024} KB)"
            else:
                body_text = read_html_to_markdown(filepath)
                page_count = 0
                format_note = f"HTML ({filepath.stat().st_size // 1024} KB)"

            # Determine issuing body
            if doc_number.startswith("RA "):
                issuer = "Congress of the Philippines"
            elif doc_number.startswith("DC"):
                issuer = "Department of Energy"
            elif doc_number.startswith("ERC"):
                issuer = "Energy Regulatory Commission"
            elif doc_number.startswith(("EO ", "PD ")):
                issuer = "Office of the President"
            elif doc_number.startswith("HB"):
                issuer = "House of Representatives"
            else:
                issuer = default_issuer

            # Build vault note
            fm = f"""---
title: "{doc_number}: {description[:80]}"
type: {doc_type}
tags: [regulation, {dir_name.replace('-', '_')}]
document_number: "{doc_number}"
issuing_body: "{issuer}"
date_issued: "{doc_year}"
source: "{filepath.name}"
source_format: "{filepath.suffix.lower()[1:]}"
date_created: {TODAY}
date_modified: {TODAY}
status: active
confidence: high
---"""

            body = f"""# {doc_number}

## {description}

**Issuing Body:** {issuer}
**Date:** {doc_year}
**Document Number:** {doc_number}
**Source:** {format_note}

---

{body_text}
"""

            # Inject wikilinks
            body, link_count = inject_wikilinks(body)
            links_total += link_count

            # Write to vault
            dest = target_dir / f"{stem}.md"
            counter = 1
            while dest.exists():
                dest = target_dir / f"{stem}_{counter}.md"
                counter += 1

            with open(dest, "w", encoding="utf-8") as f:
                f.write(fm + "\n\n" + body)

            total += 1
            size_kb = dest.stat().st_size // 1024
            print(f"  [OK] {stem} -> {vault_folder} | {link_count} links | {size_kb} KB")

    # Also process the root master .md file
    master_md = REG_BASE / "Comprehensive Regulatory Database and Policy Analysis of the Philippine Energy Market.md"
    if master_md.exists():
        # Check if already in vault
        existing = VAULT / "03 - REGULATIONS & POLICY" / master_md.name
        if not existing.exists():
            content = master_md.read_text(encoding="utf-8")
            fm = f"""---
title: "Comprehensive Regulatory Database and Policy Analysis of the Philippine Energy Market"
type: regulation
tags: [regulation, master_reference, database]
document_number: "Master Reference"
issuing_body: "Ikutu Limited (Research)"
source: "{master_md.name}"
date_created: {TODAY}
date_modified: {TODAY}
status: active
confidence: high
---

"""
            body, link_count = inject_wikilinks(content)
            dest = VAULT / "03 - REGULATIONS & POLICY" / master_md.name
            dest.write_text(fm + body, encoding="utf-8")
            total += 1
            links_total += link_count
            print(f"\n  [OK] Master regulatory database -> 03 - REGULATIONS & POLICY | {link_count} links")

    print(f"\n{'='*50}")
    print(f"Regulatory Ingestion Complete")
    print(f"{'='*50}")
    print(f"Total documents:  {total}")
    print(f"Skipped:          {skipped}")
    print(f"Total wikilinks:  {links_total}")
    print(f"{'='*50}")


if __name__ == "__main__":
    process_all()
