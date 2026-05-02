#!/usr/bin/env python3
"""Calibre les magic cotes Over/Under 1.5 / 2.5 pour football
et fusionne dans magic_cotes_extended.json."""
import csv, json, os
from collections import defaultdict
import sys
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from morning_live import categorize_foot

CSV_PATH = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified/football.csv"
EXT_PATH = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json"

# Date de coupure : on calibre sur 2024-2025, on garde 2026 OOS pour validation
TRAIN_END = "2026-01-01"

def round_cote(o):
    return round(round(o / 0.01) * 0.01, 2)

# Buckets : counter[bucket][cote_str] = (n_obs, n_won)
def calibrate(market_key, threshold):
    """market_key = 'over_1_5' ou 'over_2_5', threshold = 2 ou 3 (total_score >= threshold)."""
    data = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # bucket -> cote -> [n, won]
    data_under = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    n_total = 0
    n_kept = 0
    with open(CSV_PATH) as f:
        for r in csv.DictReader(f):
            n_total += 1
            d = r.get("date", "").strip()
            if d >= TRAIN_END:
                continue
            try:
                hs = int(r.get("hs", 0)); asc = int(r.get("as", 0))
            except ValueError:
                continue
            total = hs + asc
            won_over = total >= threshold

            cote_o = r.get(f"odds_{market_key}", "").strip()
            cote_u = r.get(f"odds_under_{market_key.split('_', 1)[1]}", "").strip()

            try:
                co_f = float(cote_o) if cote_o else None
                cu_f = float(cote_u) if cote_u else None
            except ValueError:
                co_f = cu_f = None

            if not co_f and not cu_f:
                continue
            n_kept += 1
            league = r.get("league", "")
            cat = r.get("category", "")
            bucket = categorize_foot(league, cat)

            if co_f and 1.01 < co_f < 50:
                cr = round_cote(co_f)
                data[bucket][cr][0] += 1
                if won_over:
                    data[bucket][cr][1] += 1
            if cu_f and 1.01 < cu_f < 50:
                cr = round_cote(cu_f)
                data_under[bucket][cr][0] += 1
                if not won_over:
                    data_under[bucket][cr][1] += 1

    print(f"  market {market_key}: {n_kept}/{n_total} matchs avec cotes, {len(data)} buckets")
    return data, data_under

def to_dict(d, min_n=15):
    """Convert defaultdict[bucket][cote] = [n,won] to {bucket: {cote: wr}} avec n_min."""
    out = {}
    for bucket, cotes in d.items():
        kept = {}
        for c, (n, w) in cotes.items():
            if n >= min_n:
                kept[str(c)] = round(w / n, 4)
        if kept:
            out[bucket] = kept
    return out

print("=" * 70)
print("Calibration Over/Under foot — train sur 2024-01-01 → 2026-01-01")
print("=" * 70)

print("\n[Over/Under 1.5]")
o15, u15 = calibrate("over_1_5", 2)
o15_d = to_dict(o15)
u15_d = to_dict(u15)
print(f"  → {sum(len(v) for v in o15_d.values())} cotes magiques over_1_5 sur {len(o15_d)} buckets")
print(f"  → {sum(len(v) for v in u15_d.values())} cotes magiques under_1_5 sur {len(u15_d)} buckets")

print("\n[Over/Under 2.5]")
o25, u25 = calibrate("over_2_5", 3)
o25_d = to_dict(o25)
u25_d = to_dict(u25)
print(f"  → {sum(len(v) for v in o25_d.values())} cotes magiques over_2_5 sur {len(o25_d)} buckets")
print(f"  → {sum(len(v) for v in u25_d.values())} cotes magiques under_2_5 sur {len(u25_d)} buckets")

# Fusion dans magic_cotes_extended.json
print("\n[Fusion magic_cotes_extended.json]")
with open(EXT_PATH) as f:
    ext = json.load(f)

if "football" not in ext:
    ext["football"] = {}
fb = ext["football"]

for bucket in set(o15_d) | set(u15_d) | set(o25_d) | set(u25_d):
    if bucket not in fb:
        fb[bucket] = {}
    if bucket in o15_d: fb[bucket]["over_1_5"] = o15_d[bucket]
    if bucket in u15_d: fb[bucket]["under_1_5"] = u15_d[bucket]
    if bucket in o25_d: fb[bucket]["over_2_5"] = o25_d[bucket]
    if bucket in u25_d: fb[bucket]["under_2_5"] = u25_d[bucket]

with open(EXT_PATH, "w") as f:
    json.dump(ext, f, indent=2)

print(f"  ✓ Sauvé dans {EXT_PATH}")
print(f"  ✓ {len(fb)} foot buckets avec marchés étendus")

# Stats sample : montre les 5 buckets les + couverts
sizes = sorted([(b, sum(len(fb[b].get(m, {})) for m in ("over_1_5","under_1_5","over_2_5","under_2_5"))) for b in fb], key=lambda x: -x[1])[:8]
print("\nTop buckets par couverture O/U :")
for b, s in sizes:
    print(f"  {b:30s} {s:>4d} cotes")
