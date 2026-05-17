"""
03 — Polymarket Dataset: Enrich Market Index via Gamma API

For each market in data_processed/markets_index.json, fetches:
  - GET https://gamma-api.polymarket.com/markets/{market_id}  → full market metadata
  - GET https://gamma-api.polymarket.com/markets/{market_id}/tags  → tag list

Merges everything into the original dict and adds a "tags" field.
Saves to data_processed/markets_enriched.json.

Idempotent: resumes from where it left off if the output file already exists.
Saves progress every SAVE_EVERY markets to avoid data loss on long runs.
"""

import json
import time
from pathlib import Path

import requests
from tqdm import tqdm

# ── Config ────────────────────────────────────────────────────────────────────

GAMMA_BASE   = "https://gamma-api.polymarket.com"
SLEEP_S      = 0.15   # 150 ms between markets (~6.5 markets/s, well within rate limits)
SAVE_EVERY   = 100    # checkpoint to disk every N markets
TIMEOUT      = 15     # HTTP timeout in seconds
MAX_RETRIES  = 3
BACKOFF      = 1.5    # exponential backoff base (seconds)

IN_PATH  = Path("data_processed/markets_index.json")
OUT_PATH = Path("data_processed/markets_enriched.json")

# ── HTTP session ──────────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get(url: str) -> dict | list | None:
    """GET with exponential backoff. Returns parsed JSON or None on failure."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = SESSION.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES:
                print(f"  [FAIL] {url} — {exc}")
                return None
            wait = BACKOFF ** attempt
            time.sleep(wait)
    return None


def enrich_market(entry: dict) -> dict:
    """
    Fetch market metadata and tags for one market_id.
    Returns the original entry merged with API data + a 'tags' list field.
    """
    market_id = entry["market_id"]

    market_data = _get(f"{GAMMA_BASE}/markets/{market_id}")
    tags_data   = _get(f"{GAMMA_BASE}/markets/{market_id}/tags")

    result = dict(entry)  # start from original fields

    if market_data and isinstance(market_data, dict):
        result.update(market_data)

    result["tags"] = tags_data if isinstance(tags_data, list) else []

    return result


# ── Load inputs ───────────────────────────────────────────────────────────────

markets_index: list[dict] = json.load(open(IN_PATH))
print(f"Markets to enrich : {len(markets_index)}")

# Resume from existing output if present
already_done: dict[str, dict] = {}
if OUT_PATH.exists():
    existing = json.load(open(OUT_PATH))
    already_done = {e["market_id"]: e for e in existing}
    print(f"Resuming — already enriched: {len(already_done)}")

# ── Main loop ─────────────────────────────────────────────────────────────────

enriched: list[dict] = list(already_done.values())
pending = [e for e in markets_index if e["market_id"] not in already_done]
print(f"Pending           : {len(pending)}")

for i, entry in enumerate(tqdm(pending, desc="Enriching markets"), start=1):
    result = enrich_market(entry)
    enriched.append(result)

    time.sleep(SLEEP_S)

    # Checkpoint every SAVE_EVERY markets
    if i % SAVE_EVERY == 0:
        with open(OUT_PATH, "w") as f:
            json.dump(enriched, f, indent=2)
        tqdm.write(f"  Checkpoint saved ({len(enriched)} markets)")

# Final save
with open(OUT_PATH, "w") as f:
    json.dump(enriched, f, indent=2)

# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\nDone. {len(enriched)} markets saved -> {OUT_PATH}")
print(f"File size: {OUT_PATH.stat().st_size / 1024 / 1024:.1f} MB")

# Quick check: count markets with tags
with_tags    = sum(1 for e in enriched if e.get("tags"))
without_tags = len(enriched) - with_tags
print(f"Markets with tags : {with_tags}")
print(f"Markets no tags   : {without_tags}")
