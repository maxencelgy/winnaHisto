#!/usr/bin/env python3
"""Sweep v5 — Walk-forward STRICT.

Étape 1 : recalibre magic avec TRAIN_END=2025-01-01
Étape 2 : teste top candidats sur 2025-01-01 à 2026-04-30 (16 mois OOS pur)

Critère croustillant absolu :
  - PnL positif sur 2025 (12 mois) ET S1-26 (4 mois)
  - PnL positif sur ≥ 5/6 trimestres (Q1-Q4 2025 + Q1 2026)
  - Streak rouge ≤ 4j
  - DD < 50% BR
"""
import csv, json, os, sys
from collections import defaultdict
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from morning_live import CATEGORIZERS
from backtest_engine import _get_index, extract_picks, build_backtest_combos

DATASETS = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
TRAIN_END = "2025-01-01"  # STRICT : exclut 2025+2026

WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
        "laliga 2","serie b","ligue 2","champions league","europa league","conference",
        "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
        "mls","liga mx","brasileirão","brasileirao","coupe","fa cup",
        "primeira liga","primera división"],
    "basketball": ["nba","wnba","euroleague","eurocup","betclic élite","pro a","acb","liga endesa",
                   "lega basket","serie a","bbl","champions league"],
    "ice-hockey": ["nhl","khl","shl","liiga","ligue magnus","del","national league","extraliga","swiss"],
    "baseball": ["mlb"],
}
REJECT = ["doubles","qualifying","u23","u21","u19","u18","reserve","youth","next pro",
          "regionalliga","série c","i-league","exhibition"]

def lok(sport, lg):
    if not lg: return False
    l = lg.lower()
    if any(r in l for r in REJECT): return False
    return any(p in l for p in WHITELIST.get(sport, []))

def round_cote(o):
    return round(round(o / 0.01) * 0.01, 2)

def fnum(s):
    try: return float(s)
    except: return None

def gen_days(sd, ed):
    s = datetime.strptime(sd,"%Y-%m-%d").date(); e = datetime.strptime(ed,"%Y-%m-%d").date()
    cur = s
    while cur <= e: yield cur.isoformat(); cur += timedelta(days=1)

def streak_red(daily):
    s=0;c=0
    for p in daily:
        if p < 0: c+=1; s=max(s,c)
        else: c=0
    return s

def max_dd(daily):
    cum=0;peak=0;dd=0
    for p in daily:
        cum+=p
        if cum>peak: peak=cum
        dd=max(dd, peak-cum)
    return dd

# ============== Étape 1 : recalibrer magic avec TRAIN_END=2025-01-01 ==============
SMART_OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart_2025.json"
EXT_OUT = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended_2025.json"
MIN_N = 15

if not os.path.exists(SMART_OUT):
    print(f"Recalibration magic avec TRAIN_END={TRAIN_END}...")
    sport_data = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: [0,0])))
    for sport in ["football","basketball","ice-hockey","baseball"]:
        csv_path = os.path.join(DATASETS, f"{sport}.csv")
        if not os.path.exists(csv_path): continue
        cat_fn = CATEGORIZERS.get(sport)
        n_used = 0
        with open(csv_path) as f:
            for r in csv.DictReader(f):
                d = r.get("date","").strip()
                if d >= TRAIN_END or not d: continue
                try:
                    hs = int(r.get("hs",0) or 0); asc = int(r.get("as",0) or 0)
                except: continue
                if hs==0 and asc==0: continue
                n_used += 1
                league = r.get("league",""); cat = r.get("category","")
                bucket = cat_fn(league, cat) if cat_fn else league
                home_won = hs > asc; is_draw = hs == asc
                total = hs + asc
                btts_yes = hs > 0 and asc > 0

                for cote_field, won in [("odds_1", home_won), ("odds_2", not home_won and not is_draw),
                                         ("odds_x", is_draw)]:
                    c = fnum(r.get(cote_field))
                    if c and c > 1.01:
                        cr = round_cote(c)
                        sport_data[(sport, bucket)]["1x2"][cr][0] += 1
                        if won: sport_data[(sport, bucket)]["1x2"][cr][1] += 1

                for cote_field, sel, won in [("odds_btts_yes","oui",btts_yes), ("odds_btts_no","non",not btts_yes)]:
                    c = fnum(r.get(cote_field))
                    if c and c > 1.01:
                        cr = round_cote(c)
                        key = f"btts_{sel}"
                        sport_data[(sport, bucket)][key][cr][0] += 1
                        if won: sport_data[(sport, bucket)][key][cr][1] += 1

                for line, side, cote_field, won_func in [
                    (1.5, "plus", "odds_o15", total > 1.5),
                    (1.5, "moins", "odds_u15", total < 1.5),
                    (2.5, "plus", "odds_o25", total > 2.5),
                    (2.5, "moins", "odds_u25", total < 2.5),
                ]:
                    c = fnum(r.get(cote_field))
                    if c and c > 1.01:
                        cr = round_cote(c)
                        key = f"over_{int(line*10)}_{side}"
                        sport_data[(sport, bucket)][key][cr][0] += 1
                        if won_func: sport_data[(sport, bucket)][key][cr][1] += 1
        print(f"  {sport}: {n_used} matchs train")

    smart = {"_smart": True}
    extended = {"_smart": True, "_extended": True}
    n_buckets_smart = 0; n_cotes_smart = 0
    n_buckets_ext = 0; n_cotes_ext = 0
    for (sport, bucket), markets in sport_data.items():
        if "1x2" in markets:
            cotes_data = markets["1x2"]
            kept = {c: {"wr": w/n, "n": n} for c,(n,w) in cotes_data.items() if n >= MIN_N}
            if kept:
                smart.setdefault(sport, {})[bucket] = kept
                n_buckets_smart += 1
                n_cotes_smart += len(kept)
        for mkt, cotes_data in markets.items():
            kept = {c: {"wr": w/n, "n": n} for c,(n,w) in cotes_data.items() if n >= MIN_N}
            if kept:
                extended.setdefault(sport, {}).setdefault(bucket, {})[mkt] = kept
                n_buckets_ext += 1
                n_cotes_ext += len(kept)

    with open(SMART_OUT,"w") as f: json.dump(smart, f, indent=2)
    with open(EXT_OUT,"w") as f: json.dump(extended, f, indent=2)
    print(f"  → {n_buckets_smart} buckets 1x2, {n_cotes_smart} cotes")
    print(f"  → {n_buckets_ext} buckets ext, {n_cotes_ext} cotes")
else:
    print(f"✓ {SMART_OUT} existe déjà, skip recalibration")

# ============== Étape 2 : Charger magic 2025 et tester candidats ==============
with open(SMART_OUT) as f: raw = json.load(f)
magic = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                     for c,info in cotes.items()}
                 for b, cotes in buckets.items()}

with open(EXT_OUT) as f: magic_ext = json.load(f)

# Périodes test (16 mois OOS pur)
PERIODS = {
    "Q1-25": list(gen_days("2025-01-01","2025-03-31")),
    "Q2-25": list(gen_days("2025-04-01","2025-06-30")),
    "Q3-25": list(gen_days("2025-07-01","2025-09-30")),
    "Q4-25": list(gen_days("2025-10-01","2025-12-31")),
    "Q1-26": list(gen_days("2026-01-01","2026-03-31")),
    "Apr26": list(gen_days("2026-04-01","2026-04-30")),
}

def run(days, sports_list, market, cote_min, cote_max, max_legs, sort_by,
        max_combos, side_filter=None, min_wr=None, sizing="pct", br0=100):
    bankroll = br0; daily = []; n_combos = 0
    m_ref = magic_ext if market in ("btts","over_1_5","over_2_5") else magic
    for d in days:
        idx = _get_index()
        ms = idx.get(d, [])
        ms = [m for m in ms if m["sport"] in sports_list and lok(m["sport"], m.get("league",""))]
        if not ms: continue
        picks = extract_picks(ms, m_ref, market=market)
        if side_filter:
            picks = [p for p in picks if side_filter.lower() in p["selection"].lower()]
        if min_wr is not None:
            picks = [p for p in picks if p["wr"] >= min_wr]
        if max_legs == 1:
            picks = [p for p in picks if cote_min <= p["odds"] <= cote_max]
        if not picks: continue
        combos = build_backtest_combos(picks, max_legs=max_legs,
                                        cote_min=cote_min, cote_max=cote_max,
                                        max_combos=max_combos*5, sort_by=sort_by)
        chosen = combos[:max_combos]
        if not chosen: continue
        day_pnl = 0
        for c in chosen:
            stake = 10.0 if sizing=="flat" else max(0.5, bankroll*0.10)
            n_combos += 1
            if c["won"]: day_pnl += stake*(c["cote_t"]-1)
            else: day_pnl -= stake
        bankroll += day_pnl
        daily.append(day_pnl)
    pnl = sum(daily)
    return {"pnl":pnl, "br_final":bankroll, "ng":sum(1 for p in daily if p>0),
            "nr":sum(1 for p in daily if p<0), "n_combos":n_combos,
            "streak":streak_red(daily), "dd":max_dd(daily)}

# Sweep large
candidates = []
# Hockey deep
for cmin, cmax in [(1.10,1.25),(1.20,1.35),(1.25,1.40),(1.25,1.45),(1.25,1.50),(1.30,1.50),
                    (1.30,1.55),(1.40,1.65),(1.50,1.80)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["ice-hockey"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"H_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# Foot deep
for cmin, cmax in [(1.20,1.40),(1.30,1.50),(1.40,1.65),(1.50,1.80),(1.60,1.90),(1.80,2.20)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["football"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"F_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# Basket
for cmin, cmax in [(1.20,1.40),(1.30,1.55),(1.50,1.80),(1.80,2.20)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["basketball"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"B_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# Baseball
for cmin, cmax in [(1.50,1.90),(1.70,2.10),(1.90,2.50)]:
    for sort in ["wr","ev"]:
        for mc in [2,3]:
            cfg = dict(sports_list=["baseball"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"BB_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# Min_wr stricte
for sport in ["football","basketball","ice-hockey","baseball"]:
    for cmin, cmax in [(1.40,2.00),(1.50,2.20),(1.80,2.50),(2.00,2.80)]:
        for mwr in [0.65, 0.70, 0.75]:
            cfg = dict(sports_list=[sport], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by="ev", max_combos=4, min_wr=mwr)
            candidates.append((f"WR{mwr}_{sport[:4]}_{cmin}-{cmax}", cfg))

# 2j
for sport in ["football","basketball","ice-hockey"]:
    for cmin, cmax in [(1.20,1.50),(1.30,1.60),(1.40,1.80),(1.50,2.00)]:
        for sort in ["wr","ev"]:
            for mc in [2,3]:
                cfg = dict(sports_list=[sport], market="1x2", cote_min=cmin, cote_max=cmax,
                           max_legs=2, sort_by=sort, max_combos=mc)
                candidates.append((f"2j_{sport[:4]}_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# BTTS oui foot
for cmin, cmax in [(1.40,1.55),(1.50,1.70),(1.55,1.75),(1.70,1.90)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["football"], market="btts", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc, side_filter="oui")
            candidates.append((f"BO_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

print(f"\nTotal candidats: {len(candidates)}")
print("Test 16 mois OOS pur (Q1-25 → Apr26)...\n")

results = []
for i, (name, cfg) in enumerate(candidates):
    if i % 30 == 0:
        print(f"  [{i}/{len(candidates)}]")
    ev = {p: run(days=days, **cfg) for p, days in PERIODS.items()}
    results.append((name, cfg, ev))

# Tri par PnL total
def total_pnl(ev): return sum(ev[p]["pnl"] for p in PERIODS)
def n_pos(ev): return sum(1 for p in PERIODS if ev[p]["pnl"] > 0)
def max_streak(ev): return max(ev[p]["streak"] for p in PERIODS)

results.sort(key=lambda x: -total_pnl(x[2]))

# Croustillant : ≥5/6 périodes positives + streak ≤ 4 + ≥30 combos par période active
def is_crous(ev):
    if n_pos(ev) < 5: return False
    if max_streak(ev) > 4: return False
    # Pas de période avec moins de 5 combos quand active
    return True

robust = [(n,c,e) for n,c,e in results if is_crous(e)]

print(f"\n\n{'='*100}")
print(f"=== TOP 25 par PnL total 16 mois OOS PUR ===\n")
print(f"{'Preset':40s} {'Q1-25':>7s} {'Q2-25':>7s} {'Q3-25':>7s} {'Q4-25':>7s} {'Q1-26':>7s} {'Apr26':>7s} {'TOT':>7s}")
print("-"*100)
for n,c,e in results[:25]:
    parts = [f"{e[p]['pnl']:>+5.0f}€" for p in PERIODS]
    tot = total_pnl(e)
    flag = "★" if is_crous(e) else " "
    print(f"{flag} {n:38s} {' '.join(parts)} {tot:>+5.0f}€")

print(f"\n\n=== {len(robust)} CROUSTILLANTS (5/6+ périodes +, streak≤4) ===")
for n,c,e in robust[:20]:
    parts = [f"{e[p]['pnl']:>+5.0f}€" for p in PERIODS]
    tot = total_pnl(e)
    print(f"  {n:38s} {' '.join(parts)} = {tot:>+6.0f}€  np={n_pos(e)}/6 strk={max_streak(e)}j")

# Détail top 5 robustes
print(f"\n\n=== TOP 5 ROBUSTES DÉTAIL ===\n")
for n,c,e in robust[:5]:
    print(f"\n{n}")
    print(f"  cfg: {c}")
    for p in PERIODS:
        r = e[p]
        print(f"  {p}: PnL +{r['pnl']:.0f}€ BR_fin {r['br_final']:.0f}€ "
              f"streak {r['streak']}j DD {r['dd']:.0f}€ {r['n_combos']} combos {r['ng']}+/{r['nr']}-")

out = {"all":[{"name":n,"cfg":c,"ev":{p:e[p] for p in PERIODS}} for n,c,e in results],
       "robust":[{"name":n,"cfg":c,"ev":{p:e[p] for p in PERIODS}} for n,c,e in robust]}
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v5_results.json","w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n💾 datasets/sweep_v5_results.json")
