"""
02 — Filtering the Polymarket Dataset

Dataset
-------
Source:   https://www.kaggle.com/datasets/sandeepkumarfromin/full-market-data-from-polymarket
Coverage: Polymarket binary prediction markets, 2025
Size:     ~4.9 GB, 3 385 markets

Folder structure
----------------
data/Polymarket_dataset/Polymarket_dataset/
└── market=0x{conditionId}/
    ├── book/
    │   ├── token={token_id_0}.ndjson   <- outcome 0 (conditionId, market_id, capture_ts_ms)
    │   └── token={token_id_1}.ndjson   <- outcome 1
    ├── holder/
    │   └── market=0x{conditionId}.ndjson  <- top holders per token
    ├── price/
    │   ├── token={token_id_0}.ndjson   <- price time series {t, p}
    │   └── token={token_id_1}.ndjson
    └── trade/
        └── market=0x{conditionId}.ndjson  <- all trades (both tokens)

Section 1
---------
Build a compact market index by reading the book/ metadata files for all
3 385 markets, validating consistency, and saving to
data_processed/markets_index.json.
"""

import json
from pathlib import Path

import pandas as pd
from tqdm import tqdm

DATASET_DIR   = Path("data/Polymarket_dataset/Polymarket_dataset")
DATA_PROC_DIR = Path("data_processed")
DATA_PROC_DIR.mkdir(exist_ok=True)

print(f"Dataset path exists: {DATASET_DIR.exists()}")


# ── Section 1 — Market Index from Book Files ─────────────────────────────────
#
# Each book/ folder contains exactly 2 files (one per outcome token),
# each a single JSON object:
#   {"token_id": "...", "conditionId": "0x...", "market_id": "565754",
#    "capture_ts_ms": 1755699113838}
#
# Both files share the same conditionId and market_id.
# capture_ts_ms may differ by 0–2 ms (sequential capture) — we take the minimum.
#
# Validation checks per market:
#   1. Exactly 2 book files
#   2. conditionId identical in both files
#   3. market_id identical in both files
#   4. capture_ts_ms difference <= 10 ms
#   5. Folder name market=0x{...} matches conditionId


def parse_book_file(path: Path) -> dict:
    """
    Read the first JSON object from a book file.
    Files contain multiple concatenated JSON objects (one per token capture);
    we only need the first one since conditionId/market_id/capture_ts_ms are shared.
    """
    with open(path) as f:
        content = f.read()
    obj, _ = json.JSONDecoder().raw_decode(content.lstrip())
    return obj


def extract_market_metadata(market_dir: Path) -> dict | None:
    """
    Parse both book files for one market.
    Returns {conditionId, market_id, capture_ts_ms} or None on structural error.
    Prints a message for every failed validation check.
    """
    condition_id_from_folder = market_dir.name.removeprefix("market=")
    book_dir   = market_dir / "book"
    book_files = sorted(book_dir.glob("token=*.ndjson"))

    # 1. File count
    if len(book_files) != 2:
        print(f"market={condition_id_from_folder}: expected 2 book files, got {len(book_files)}")
        return None

    r0 = parse_book_file(book_files[0])
    r1 = parse_book_file(book_files[1])

    # 2 & 3. conditionId and market_id consistency
    for field in ("conditionId", "market_id"):
        if r0[field] != r1[field]:
            print(f"market={condition_id_from_folder}: {field} not similar")

    # 4. capture_ts_ms tolerance <= 10 ms
    ts_diff = abs(r0["capture_ts_ms"] - r1["capture_ts_ms"])
    if ts_diff > 10:
        print(f"market={condition_id_from_folder}: capture_ts_ms not similar (diff={ts_diff} ms)")

    # 5. Folder name matches conditionId
    if r0["conditionId"] != condition_id_from_folder:
        print(
            f"market={condition_id_from_folder}: "
            f"conditionId mismatch with folder name ({r0['conditionId']})"
        )

    return {
        "conditionId":   r0["conditionId"],
        "market_id":     r0["market_id"],
        "capture_ts_ms": min(r0["capture_ts_ms"], r1["capture_ts_ms"]),
    }


market_dirs = sorted(
    d for d in DATASET_DIR.iterdir()
    if d.is_dir() and d.name.startswith("market=")
)
print(f"Total market folders: {len(market_dirs)}")

markets: list[dict] = []
for market_dir in tqdm(market_dirs, desc="Building market index"):
    result = extract_market_metadata(market_dir)
    if result is not None:
        markets.append(result)

print(f"Processed: {len(markets)} / {len(market_dirs)} markets")

# ── Summary stats ─────────────────────────────────────────────────────────────

df = pd.DataFrame(markets)
df["capture_dt_utc"] = pd.to_datetime(df["capture_ts_ms"], unit="ms", utc=True)

print(f"Markets          : {len(df)}")
print(f"Unique market_ids: {df['market_id'].nunique()}")
print("Capture timestamp range:")
print(f"  Earliest : {df['capture_dt_utc'].min()}")
print(f"  Latest   : {df['capture_dt_utc'].max()}")

# ── Save to JSON ──────────────────────────────────────────────────────────────

OUT_PATH = DATA_PROC_DIR / "markets_index.json"

with open(OUT_PATH, "w") as f:
    json.dump(markets, f, indent=2)

check = json.load(open(OUT_PATH))
assert len(check) == len(markets), "Round-trip length mismatch!"

print(f"Saved {len(markets)} entries -> {OUT_PATH}")
print(f"File size: {OUT_PATH.stat().st_size / 1024:.1f} KB")
