#!/usr/bin/env python3
"""Recalibration LIVE — magic à jour incluant TOUS les matchs jusqu'à today.

À lancer hebdomadairement (ou avant chaque jour de paris) pour avoir la magic
la plus précise possible en prod live.

Différence vs recalibrate_strict.py (TRAIN_END = 2026-01-01) :
  - recalibrate_strict : utilisé pour BACKTEST (OOS strict)
  - recalibrate_now    : utilisé pour LIVE (data la plus fraîche)

Versionne les fichiers magic dans datasets/magic_versions/ pour rollback.
"""
import csv, json, os, shutil, sys
from collections import defaultdict
from datetime import date, datetime
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from morning_live import CATEGORIZERS

DATASETS = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
SMART_OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json"
EXT_OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json"
VERSIONS_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_versions"

# TRAIN_END = today (inclus tous les matchs jusqu'à hier inclus)
TRAIN_END = date.today().isoformat()
MIN_N = 15

os.makedirs(VERSIONS_DIR, exist_ok=True)

# Backup les magic actuelles avant écrasement
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
for src, name in [(SMART_OUT, "smart"), (EXT_OUT, "extended")]:
    if os.path.exists(src):
        dst = os.path.join(VERSIONS_DIR, f"magic_{name}_{ts}.json")
        shutil.copy(src, dst)
        print(f"  📦 Backup {name} → {dst}")

print(f"\n🔄 Recalibration LIVE (TRAIN_END = {TRAIN_END})...")

def round_cote(o):
    return round(round(o / 0.01) * 0.01, 2)

def fnum(s):
    try: return float(s)
    except (ValueError, TypeError): return None

# sport_data[(sport, bucket)][market_key][cote] = [n, wins]
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
            if hs == 0 and asc == 0 and sport != "baseball":  # baseball peut avoir 0-0 légitime
                continue
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
                    key = "btts_y" if cote_field == "odds_btts_y" else "btts_n"
                    sport_data[(sport, bucket)][key][cr][0] += 1
                    if won: sport_data[(sport, bucket)][key][cr][1] += 1
            # Over/Under
            for line, won_o, won_u in [(0.5, total>0.5, total<=0.5),
                                         (1.5, total>1.5, total<=1.5),
                                         (2.5, total>2.5, total<=2.5),
                                         (3.5, total>3.5, total<=3.5)]:
                key_suffix = str(line).replace(".", "_")
                for cote_field, won, market_key in [
                    (f"odds_over_{key_suffix}", won_o, f"over_{key_suffix}"),
                    (f"odds_under_{key_suffix}", won_u, f"under_{key_suffix}"),
                ]:
                    c = fnum(r.get(cote_field))
                    if c and c > 1.01:
                        cr = round_cote(c)
                        sport_data[(sport, bucket)][market_key][cr][0] += 1
                        if won: sport_data[(sport, bucket)][market_key][cr][1] += 1
    print(f"  {sport}: {n_used:,}/{n_total:,} matchs (jusqu'à {TRAIN_END})")

# Build smart (1x2 only, all sports) + extended (tous markets, structure unifiée)
smart = {}
extended = {}
for (sport, bucket), markets in sport_data.items():
    if "1x2" in markets:
        cotes_1x2 = markets["1x2"]
        kept = {}
        for cote, (n, wins) in cotes_1x2.items():
            if n >= MIN_N:
                kept[cote] = {"wr": round(wins / n, 4), "n": n, "ev": round(wins / n * cote, 3)}
        if kept:
            smart.setdefault(sport, {})[bucket] = kept

    # Extended : tous markets pour ce bucket
    for mkt, cotes_data in markets.items():
        kept_ext = {}
        for cote, (n, wins) in cotes_data.items():
            if n >= MIN_N:
                kept_ext[cote] = {"wr": round(wins / n, 4), "n": n}
        if kept_ext:
            extended.setdefault(sport, {}).setdefault(bucket, {})[mkt] = kept_ext

# Stats
print(f"\nSMART (1x2) : {sum(len(b) for b in smart.values())} buckets total")
for sp, buckets in smart.items():
    n_cotes = sum(len(c) for c in buckets.values())
    print(f"  {sp}: {len(buckets)} buckets, {n_cotes} cotes")

print(f"\nEXT : {sum(len(b) for b in extended.values())} buckets total")
for sp, buckets in extended.items():
    n_cotes = sum(sum(len(c) for c in m.values()) for m in buckets.values())
    print(f"  {sp}: {len(buckets)} buckets, {n_cotes} cotes")

with open(SMART_OUT, "w") as f:
    json.dump(smart, f, indent=2, ensure_ascii=False)
print(f"\n✓ Sauvé {SMART_OUT}")

with open(EXT_OUT, "w") as f:
    json.dump(extended, f, indent=2, ensure_ascii=False)
print(f"✓ Sauvé {EXT_OUT}")

# Note de version
note = {
    "recalibrated_at": datetime.now().isoformat(),
    "train_end": TRAIN_END,
    "min_n": MIN_N,
    "smart_buckets": {sp: len(b) for sp, b in smart.items()},
    "ext_buckets": {sp: len(b) for sp, b in extended.items()},
}
with open(os.path.join(VERSIONS_DIR, f"recalibration_{ts}.json"), "w") as f:
    json.dump(note, f, indent=2)

print(f"\n✅ Magic recalibrée jusqu'à {TRAIN_END} ! Backups dans {VERSIONS_DIR}/")
print(f"   Pour rollback : cp {VERSIONS_DIR}/magic_smart_<ts>.json {SMART_OUT}")
