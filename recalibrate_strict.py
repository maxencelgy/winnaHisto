#!/usr/bin/env python3
"""Recalibration STRICTE de magic_cotes_smart.json + magic_cotes_extended.json
sur train 2024-01-01 → 2026-01-01 (S1-26 reste OOS pur)."""
import csv, json, os
from collections import defaultdict
import sys
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from morning_live import CATEGORIZERS

DATASETS = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
SMART_OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json"
EXT_OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json"
TRAIN_END = "2026-01-01"
MIN_N = 15

def round_cote(o):
    return round(round(o / 0.01) * 0.01, 2)

def fnum(s):
    try: return float(s)
    except (ValueError, TypeError): return None

# Pour chaque sport : sport_data[bucket][submarket][cote] = [n, wins]
sport_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0, 0])))

sports = ["football", "basketball", "ice-hockey", "baseball", "tennis"]
for sport in sports:
    csv_path = os.path.join(DATASETS, f"{sport}.csv")
    if not os.path.exists(csv_path):
        print(f"  {sport}: pas de CSV, skip")
        continue
    cat_fn = CATEGORIZERS.get(sport)
    n_total = 0; n_used = 0
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            n_total += 1
            d = r.get("date", "").strip()
            if d >= TRAIN_END or not d: continue
            try:
                hs = int(r.get("hs", 0) or 0); asc = int(r.get("as", 0) or 0)
            except (ValueError, TypeError):
                continue
            if hs == 0 and asc == 0: continue
            n_used += 1
            league = r.get("league", ""); cat = r.get("category", "")
            bucket = cat_fn(league, cat) if cat_fn else league
            home_won = hs > asc; is_draw = hs == asc
            total = hs + asc
            btts_yes = hs > 0 and asc > 0

            # 1x2
            for cote_field, won in [("odds_1", home_won), ("odds_2", not home_won and not is_draw),
                                      ("odds_x", is_draw)]:
                c = fnum(r.get(cote_field))
                if c and c > 1.01:
                    cr = round_cote(c)
                    sport_data[(sport, bucket)]["1x2"][cr][0] += 1
                    if won: sport_data[(sport, bucket)]["1x2"][cr][1] += 1

            # BTTS
            for cote_field, won in [("odds_btts_y", btts_yes), ("odds_btts_n", not btts_yes)]:
                c = fnum(r.get(cote_field))
                if c and c > 1.01:
                    cr = round_cote(c)
                    sub = "btts_y" if cote_field == "odds_btts_y" else "btts_n"
                    sport_data[(sport, bucket)][sub][cr][0] += 1
                    if won: sport_data[(sport, bucket)][sub][cr][1] += 1

            # Over/Under (foot uniquement)
            if sport == "football":
                for thr_str, sub_o, sub_u, won_over in [
                    ("1_5", "over_1_5", "under_1_5", total >= 2),
                    ("2_5", "over_2_5", "under_2_5", total >= 3),
                ]:
                    co = fnum(r.get(f"odds_over_{thr_str}"))
                    cu = fnum(r.get(f"odds_under_{thr_str}"))
                    if co and co > 1.01:
                        cr = round_cote(co)
                        sport_data[(sport, bucket)][sub_o][cr][0] += 1
                        if won_over: sport_data[(sport, bucket)][sub_o][cr][1] += 1
                    if cu and cu > 1.01:
                        cr = round_cote(cu)
                        sport_data[(sport, bucket)][sub_u][cr][0] += 1
                        if not won_over: sport_data[(sport, bucket)][sub_u][cr][1] += 1
    print(f"  {sport}: {n_used}/{n_total} matchs train < {TRAIN_END}")

# Build outputs
def to_smart_dict(min_n=MIN_N):
    """Format : {sport: {bucket: {cote: {wr, n, ev}}}}"""
    out = {}
    for (sport, bucket), submarkets in sport_data.items():
        if "1x2" not in submarkets: continue
        if sport not in out: out[sport] = {}
        cotes_dict = {}
        for cote, (n, w) in submarkets["1x2"].items():
            if n >= min_n:
                wr = w / n
                cotes_dict[str(cote)] = {"wr": round(wr, 4), "n": n, "ev": round(wr*cote-1, 4)}
        if cotes_dict:
            out[sport][bucket] = cotes_dict
    return out

def to_ext_dict(min_n=MIN_N):
    """Format : {sport: {bucket: {sub: {cote: wr}}}}"""
    out = {"_smart": True}
    for (sport, bucket), submarkets in sport_data.items():
        if sport not in out: out[sport] = {}
        if bucket not in out[sport]: out[sport][bucket] = {}
        for sub, cotes in submarkets.items():
            kept = {}
            for cote, (n, w) in cotes.items():
                if n >= min_n:
                    kept[str(cote)] = round(w / n, 4)
            if kept:
                out[sport][bucket][sub] = kept
        if not out[sport][bucket]:
            del out[sport][bucket]
    return out

smart = to_smart_dict()
ext = to_ext_dict()

print(f"\nSMART : {sum(len(v) for v in smart.values())} buckets total")
for sp, buckets in smart.items():
    print(f"  {sp}: {len(buckets)} buckets, {sum(len(c) for c in buckets.values())} cotes")

print(f"\nEXT : {sum(len(v) for v in ext.values() if isinstance(v, dict))} buckets total")
for sp in [s for s in ext if s != "_smart"]:
    n_buckets = len(ext[sp])
    n_cotes = sum(len(sub) for b in ext[sp].values() for sub in b.values() if isinstance(sub, dict))
    print(f"  {sp}: {n_buckets} buckets, {n_cotes} cotes")

with open(SMART_OUT, "w") as f:
    json.dump(smart, f, indent=2)
print(f"\n✓ Sauvé {SMART_OUT}")
with open(EXT_OUT, "w") as f:
    json.dump(ext, f, indent=2)
print(f"✓ Sauvé {EXT_OUT}")
