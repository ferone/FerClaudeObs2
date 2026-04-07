#!/usr/bin/env python3
"""
Agent: ENRICHER
Uses Claude API or Gemini API to enrich markdown notes with:
- Better structure and sections
- Obsidian-optimized formatting
- Suggested related notes
- Improved frontmatter
- Domain-specific strategic context

WARNING: This sends document content to external APIs.
   Only use for NON-CONFIDENTIAL documents.
   Privacy zones are loaded from the active domain pack.

Loads domain-specific config from the active domain pack:
- enrichment-prompt.md for the system prompt
- pack.json for Ollama model and privacy_zones
"""

import argparse
import json
import logging
import os
from pathlib import Path
from datetime import date

PROJECT_ROOT = Path(__file__).parent.parent
VAULT        = PROJECT_ROOT / "vault"
INBOX_VAULT  = VAULT / "_INBOX"
CONFIG       = PROJECT_ROOT / "config"
LOGS_DIR     = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [ENRICHER] %(message)s",
    handlers=[
        logging.FileHandler(LOGS_DIR / "pipeline.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("enricher")

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


def load_enrichment_prompt(pack_path: Path) -> str:
    """Load the enrichment system prompt from the active pack."""
    prompt_file = pack_path / "enrichment-prompt.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    # Fallback: generic enrichment prompt
    return """You are helping build an Obsidian knowledge vault. When given a document, your job is to:

1. Restructure it into clean Obsidian markdown with proper headings
2. Add a concise Executive Summary at the top
3. Improve the YAML frontmatter with accurate type, category, and tags
4. Add a "Related Topics" section at the bottom with [[wikilink]] suggestions
5. Keep all factual content — never remove information, only improve structure

Return ONLY the improved markdown document. No explanation. No code blocks wrapping the output.
Start directly with the YAML frontmatter (---).
"""


ENRICH_USER_PROMPT = """Please enrich and restructure this document for the knowledge vault.
Improve its Obsidian formatting, add strategic context, and suggest related topics.

Current date: {today}
Source document: {filename}

---
{content}
---"""


def enrich_with_claude(content: str, filename: str, api_key: str,
                       system_prompt: str) -> str:
    """Enrich document using Claude API."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)

        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": ENRICH_USER_PROMPT.format(
                    today=TODAY,
                    filename=filename,
                    content=content[:12000]  # Limit content size
                )
            }]
        )
        return message.content[0].text
    except ImportError:
        log.error("anthropic package not installed. Run: pip install anthropic")
        return ""
    except Exception as e:
        log.error(f"Claude API enrichment failed: {e}")
        return ""


def enrich_with_gemini(content: str, filename: str, api_key: str,
                       system_prompt: str) -> str:
    """Enrich document using Google Gemini API."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            system_instruction=system_prompt
        )
        prompt = ENRICH_USER_PROMPT.format(
            today=TODAY,
            filename=filename,
            content=content[:12000]
        )
        response = model.generate_content(prompt)
        return response.text
    except ImportError:
        log.error("google-generativeai not installed. Run: pip install google-generativeai")
        return ""
    except Exception as e:
        log.error(f"Gemini API enrichment failed: {e}")
        return ""


def enrich_with_ollama(content: str, filename: str, system_prompt: str,
                       ollama_model: str) -> str:
    """Enrich document using local Ollama (slower but private)."""
    import requests
    payload = {
        "model": ollama_model,
        "prompt": system_prompt + "\n\n" + ENRICH_USER_PROMPT.format(
            today=TODAY,
            filename=filename,
            content=content[:6000]
        ),
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 4096}
    }
    try:
        response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=300)
        return response.json().get("response", "")
    except Exception as e:
        log.error(f"Ollama enrichment failed: {e}")
        return ""


def enrich_with_lm_studio(content: str, filename: str, system_prompt: str,
                          lm_studio_config: dict) -> str:
    """Enrich document using local LM Studio (OpenAI-compatible API)."""
    import requests
    endpoint = lm_studio_config.get("endpoint", "http://127.0.0.1:1234/v1")
    model = lm_studio_config.get("model", "google/gemma-4-26b-a4b")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ENRICH_USER_PROMPT.format(
                today=TODAY,
                filename=filename,
                content=content
            )}
        ],
        "temperature": 0.3,
        "max_tokens": 250000
    }

    try:
        response = requests.post(f"{endpoint}/chat/completions", json=payload, timeout=300)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except requests.ConnectionError:
        log.error("LM Studio not available at %s", endpoint)
        return ""
    except Exception as e:
        log.error(f"LM Studio enrichment failed: {e}")
        return ""


def build_confidential_checker(pack_json: dict):
    """Build a confidentiality checker from the pack's privacy_zones."""
    privacy_zones = pack_json.get("privacy_zones", [])
    # Collect paths where external_api is False (fully confidential)
    confidential_markers = []
    for zone in privacy_zones:
        if zone.get("external_api") is False:
            confidential_markers.append(zone["path"])
        elif zone.get("level") == "confidential":
            confidential_markers.append(zone["path"])

    # Always include generic markers
    confidential_markers.extend(["CONFIDENTIAL", "confidential"])

    def is_confidential(file_path: Path) -> bool:
        """Check if a file is in a confidential folder."""
        path_str = str(file_path)
        return any(marker in path_str for marker in confidential_markers)

    return is_confidential


def process_file(md_file: Path, provider: str, api_key: str,
                 system_prompt: str, ollama_model: str,
                 is_confidential, lm_studio_config: dict = None) -> bool:
    """Enrich a single markdown file."""
    if is_confidential(md_file):
        log.warning(f"SKIPPING confidential file: {md_file.name}")
        return False

    content = md_file.read_text(encoding="utf-8", errors="replace")

    if len(content.strip()) < 100:
        log.debug(f"Skipping short file: {md_file.name}")
        return False

    log.info(f"Enriching: {md_file.name} (via {provider})")

    enriched = ""
    if provider == "claude" and api_key:
        enriched = enrich_with_claude(content, md_file.name, api_key, system_prompt)
    elif provider == "gemini" and api_key:
        enriched = enrich_with_gemini(content, md_file.name, api_key, system_prompt)
    elif provider == "ollama":
        enriched = enrich_with_ollama(content, md_file.name, system_prompt, ollama_model)
    elif provider == "lm-studio" and lm_studio_config is not None:
        enriched = enrich_with_lm_studio(content, md_file.name, system_prompt, lm_studio_config)

    if not enriched:
        log.warning(f"  No enrichment result for {md_file.name}")
        return False

    # Validate that we got something sensible back
    if not enriched.strip().startswith("---") and "title" not in enriched[:200]:
        log.warning(f"  Enrichment result looks invalid for {md_file.name}, skipping")
        return False

    # Save enriched version
    md_file.write_text(enriched, encoding="utf-8")
    log.info(f"  ✓ Enriched: {md_file.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="AI Enrichment Agent")
    parser.add_argument("--provider", choices=["claude", "gemini", "ollama", "lm-studio"],
                        default="ollama", help="AI provider to use")
    parser.add_argument("--claude-key", default=os.environ.get("ANTHROPIC_API_KEY"),
                        help="Claude API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--gemini-key", default=os.environ.get("GEMINI_API_KEY"),
                        help="Gemini API key (or set GEMINI_API_KEY env var)")
    parser.add_argument("--file", help="Process a single file")
    parser.add_argument("--all", action="store_true", help="Process all inbox files")
    args = parser.parse_args()

    # Load active pack configuration
    try:
        pack_path, pack_json = load_active_pack()
    except FileNotFoundError as e:
        log.error(str(e))
        return

    # Load domain-specific config from pack
    system_prompt = load_enrichment_prompt(pack_path)
    ollama_config = pack_json.get("ollama", {})
    ollama_model = ollama_config.get("model_enrichment", "qwen2.5:32b")
    lm_studio_config = pack_json.get("processing", {}).get("lm_studio", {})
    is_confidential = build_confidential_checker(pack_json)

    # Determine API key
    api_key = None
    if args.provider == "claude":
        api_key = args.claude_key
        if not api_key:
            log.error("Claude API key required. Set ANTHROPIC_API_KEY or use --claude-key")
            return
    elif args.provider == "gemini":
        api_key = args.gemini_key
        if not api_key:
            log.error("Gemini API key required. Set GEMINI_API_KEY or use --gemini-key")
            return

    log.info(f"Enrichment provider: {args.provider}")

    if args.file:
        files = [Path(args.file)]
    else:
        files = list(INBOX_VAULT.glob("*.md"))

    if not files:
        log.info("No files to enrich.")
        return

    log.info(f"Processing {len(files)} file(s)")
    enriched = 0
    for f in files:
        if process_file(f, args.provider, api_key, system_prompt, ollama_model,
                        is_confidential, lm_studio_config):
            enriched += 1

    log.info(f"Enrichment complete: {enriched}/{len(files)} files enriched")


if __name__ == "__main__":
    main()
