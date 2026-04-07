#!/usr/bin/env python3
"""
Agent: EXTRACTOR
Reads all .md files in vault/_INBOX/ and vault/
Extracts named entities and updates config/entity_registry.json
Uses local Ollama by default; falls back to regex matching against domain entities.

Loads domain-specific config from the active domain pack:
- entities.json for domain entity list
- extraction-prompt.md for the LLM extraction prompt
- pack.json for Ollama model configuration
"""

import argparse
import json
import logging
import re
import requests
from pathlib import Path
from datetime import datetime

PROJECT_ROOT  = Path(__file__).parent.parent
VAULT         = PROJECT_ROOT / "vault"
INBOX_VAULT   = VAULT / "_INBOX"
CONFIG        = PROJECT_ROOT / "config"
REGISTRY_FILE = CONFIG / "entity_registry_extracted.json"
LOGS_DIR      = PROJECT_ROOT / "logs"

OLLAMA_URL    = "http://localhost:11434/api/generate"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EXTRACTOR] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("extractor")


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


def load_domain_entities(pack_path: Path) -> dict:
    """Load the pre-seeded domain entity list from the active pack."""
    entity_file = pack_path / "entities.json"
    if entity_file.exists():
        return json.loads(entity_file.read_text(encoding="utf-8"))
    return {"entities": {}}


def load_extraction_prompt(pack_path: Path) -> str:
    """Load the extraction prompt from the active pack."""
    prompt_file = pack_path / "extraction-prompt.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    # Fallback: generic extraction prompt
    return """Extract named entities from the following document.

Return ONLY a JSON object with these keys:
- companies: list of company names
- organizations: list of government/regulatory body names
- regulations: list of laws, circulars, orders (with their numbers if present)
- technologies: list of technology names and acronyms
- projects: list of named project names
- people: list of person names (with role if mentioned)
- locations: list of geographic locations
- concepts: list of market concepts, financial terms, industry jargon
- products: list of specific product names/models

Be specific — extract exact names as they appear in the text.
Return only the JSON, no explanation, no markdown code blocks.
"""


def load_registry() -> dict:
    """Load the extracted entity registry."""
    if REGISTRY_FILE.exists():
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    return {
        "version": "1.0",
        "last_updated": None,
        "entities": {
            "companies": {},
            "organizations": {},
            "regulations": {},
            "technologies": {},
            "projects": {},
            "people": {},
            "locations": {},
            "concepts": {},
            "products": {}
        }
    }


def save_registry(registry: dict):
    registry["last_updated"] = datetime.now().isoformat()
    REGISTRY_FILE.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def extract_with_ollama(text: str, extraction_prompt: str, ollama_model: str) -> dict:
    """Use local Ollama model for entity extraction."""
    # Truncate very long documents
    if len(text) > 8000:
        text = text[:8000] + "\n\n[Document truncated for entity extraction]"

    full_prompt = extraction_prompt + f"\n\nDocument:\n---\n{text}\n---"

    payload = {
        "model": ollama_model,
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 2000}
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        result_text = response.json().get("response", "")

        # Try to parse JSON from response
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r"```\w*\n?", "", result_text).strip()

        entities = json.loads(result_text)
        return entities
    except requests.ConnectionError:
        log.warning("Ollama not available at localhost:11434")
        return {}
    except json.JSONDecodeError as e:
        log.warning(f"Could not parse Ollama response as JSON: {e}")
        return {}
    except Exception as e:
        log.error(f"Ollama extraction failed: {e}")
        return {}


def extract_with_lm_studio(text: str, extraction_prompt: str, lm_studio_config: dict) -> dict:
    """Use local LM Studio (OpenAI-compatible API) for entity extraction."""
    endpoint = lm_studio_config.get("endpoint", "http://127.0.0.1:1234/v1")
    model = lm_studio_config.get("model", "google/gemma-4-26b-a4b")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": extraction_prompt},
            {"role": "user", "content": f"Document:\n---\n{text}\n---"}
        ],
        "temperature": 0.1,
        "max_tokens": 250000
    }

    try:
        response = requests.post(f"{endpoint}/chat/completions", json=payload, timeout=300)
        response.raise_for_status()
        result_text = response.json()["choices"][0]["message"]["content"]

        # Try to parse JSON from response
        result_text = result_text.strip()
        if result_text.startswith("```"):
            result_text = re.sub(r"```\w*\n?", "", result_text).strip()

        entities = json.loads(result_text)
        return entities
    except requests.ConnectionError:
        log.warning("LM Studio not available at %s", endpoint)
        return {}
    except json.JSONDecodeError as e:
        log.warning(f"Could not parse LM Studio response as JSON: {e}")
        return {}
    except Exception as e:
        log.error(f"LM Studio extraction failed: {e}")
        return {}


def extract_with_regex(text: str, domain_entities: dict) -> dict:
    """Fallback: match against known domain entities using regex."""
    found = {cat: [] for cat in ["companies", "organizations", "regulations",
                                   "technologies", "projects", "locations", "concepts"]}

    all_entities = domain_entities.get("entities", {})

    for category, entries in all_entities.items():
        for entry in entries:
            names_to_check = [entry["name"]] + entry.get("aliases", [])
            for name in names_to_check:
                pattern = re.compile(r'\b' + re.escape(name) + r'\b', re.IGNORECASE)
                if pattern.search(text):
                    # Map category to extraction category
                    cat_map = {
                        "organizations": "organizations",
                        "companies_philippines": "companies",
                        "suppliers_global": "companies",
                        "regulations": "regulations",
                        "technologies": "technologies",
                        "market_concepts": "concepts",
                        "locations_philippines": "locations",
                    }
                    target_cat = cat_map.get(category, "concepts")
                    if entry["name"] not in found[target_cat]:
                        found[target_cat].append(entry["name"])
                    break

    return found


def merge_entities(registry: dict, new_entities: dict, source_file: str):
    """Merge newly extracted entities into the registry."""
    for category, items in new_entities.items():
        if category not in registry["entities"]:
            registry["entities"][category] = {}

        if isinstance(items, list):
            for item in items:
                if not item or not isinstance(item, str):
                    continue
                item = item.strip()
                if len(item) < 2:
                    continue
                if item not in registry["entities"][category]:
                    registry["entities"][category][item] = {
                        "count": 1,
                        "sources": [source_file],
                        "aliases": [],
                        "vault_note": None
                    }
                else:
                    registry["entities"][category][item]["count"] += 1
                    if source_file not in registry["entities"][category][item]["sources"]:
                        registry["entities"][category][item]["sources"].append(source_file)


def process_file(md_file: Path, registry: dict, domain_entities: dict,
                 extraction_prompt: str, ollama_model: str,
                 use_llm: bool = True, provider: str = "ollama",
                 lm_studio_config: dict = None) -> int:
    """Extract entities from a single markdown file."""
    content = md_file.read_text(encoding="utf-8", errors="replace")

    # Strip frontmatter for extraction
    if content.startswith("---"):
        parts = content.split("---", 2)
        text = parts[2] if len(parts) > 2 else content
    else:
        text = content

    if len(text.strip()) < 50:
        log.debug(f"Skipping short file: {md_file.name}")
        return 0

    source = str(md_file.relative_to(PROJECT_ROOT))
    log.info(f"Extracting entities: {md_file.name}")

    # Try LLM provider first, fall back to regex
    entities = {}
    if use_llm:
        if provider == "lm-studio" and lm_studio_config is not None:
            entities = extract_with_lm_studio(text, extraction_prompt, lm_studio_config)
        else:
            entities = extract_with_ollama(text, extraction_prompt, ollama_model)

    if not entities:
        log.debug(f"  Using regex fallback for {md_file.name}")
        entities = extract_with_regex(text, domain_entities)

    total = sum(len(v) for v in entities.values() if isinstance(v, list))
    log.info(f"  Found {total} entities")

    merge_entities(registry, entities, source)
    return total


def build_master_linklist(registry: dict, domain_entities: dict) -> list:
    """
    Build a flat list of all known entity names for the linker to use.
    Returns list of {name, aliases, category, vault_path} dicts.
    """
    master = []

    # From domain_entities (pre-seeded)
    for category, entries in domain_entities.get("entities", {}).items():
        for entry in entries:
            master.append({
                "name": entry["name"],
                "aliases": entry.get("aliases", []),
                "category": category,
                "vault_folder": entry.get("folder", ""),
                "source": "domain"
            })

    # From extracted registry
    for category, items in registry.get("entities", {}).items():
        for name, data in items.items():
            # Check if already in master
            existing = next((e for e in master if e["name"].lower() == name.lower()), None)
            if not existing:
                master.append({
                    "name": name,
                    "aliases": data.get("aliases", []),
                    "category": category,
                    "vault_folder": "",
                    "source": "extracted"
                })

    return master


def main():
    parser = argparse.ArgumentParser(description="Entity Extractor Agent")
    parser.add_argument("--no-ollama", action="store_true", help="Skip Ollama, use regex only")
    parser.add_argument("--provider", choices=["ollama", "lm-studio"],
                        default="ollama", help="LLM provider for extraction")
    parser.add_argument("--file", help="Process a single file")
    parser.add_argument("--all", action="store_true", help="Process entire vault (not just inbox)")
    args = parser.parse_args()

    # Load active pack configuration
    try:
        pack_path, pack_json = load_active_pack()
    except FileNotFoundError as e:
        log.error(str(e))
        return

    # Load domain-specific config from pack
    domain_entities = load_domain_entities(pack_path)
    extraction_prompt = load_extraction_prompt(pack_path)
    ollama_config = pack_json.get("ollama", {})
    ollama_model = ollama_config.get("model_extraction", "qwen2.5:32b")
    lm_studio_config = pack_json.get("processing", {}).get("lm_studio", {})

    registry = load_registry()

    provider = args.provider
    use_llm = not args.no_ollama

    if use_llm and provider == "ollama":
        # Test Ollama connection
        try:
            endpoint = ollama_config.get("endpoint", "http://localhost:11434")
            r = requests.get(f"{endpoint}/api/tags", timeout=3)
            log.info(f"Ollama connected — using model: {ollama_model}")
        except Exception:
            log.warning("Ollama not reachable — using regex extraction only")
            use_llm = False
    elif use_llm and provider == "lm-studio":
        # Test LM Studio connection
        try:
            endpoint = lm_studio_config.get("endpoint", "http://localhost:1234/v1")
            r = requests.get(f"{endpoint}/models", timeout=3)
            model = lm_studio_config.get("model_extraction", "default")
            log.info(f"LM Studio connected — using model: {model}")
        except Exception:
            log.warning("LM Studio not reachable — using regex extraction only")
            use_llm = False

    if args.file:
        files = [Path(args.file)]
    elif args.all:
        files = list(VAULT.rglob("*.md"))
        files = [f for f in files if "_TEMPLATES" not in str(f)]
    else:
        files = list(INBOX_VAULT.glob("*.md"))

    if not files:
        log.info("No files to extract from.")
    else:
        log.info(f"Processing {len(files)} file(s)")
        total_entities = 0
        for f in files:
            total_entities += process_file(
                f, registry, domain_entities, extraction_prompt, ollama_model,
                use_llm, provider, lm_studio_config
            )
        log.info(f"Total entities extracted: {total_entities}")

    # Build and save master link list
    master = build_master_linklist(registry, domain_entities)
    master_file = CONFIG / "master_linklist.json"
    master_file.write_text(json.dumps(master, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Master link list: {len(master)} entities ->{master_file}")

    save_registry(registry)
    log.info(f"Registry saved ->{REGISTRY_FILE}")


if __name__ == "__main__":
    main()
