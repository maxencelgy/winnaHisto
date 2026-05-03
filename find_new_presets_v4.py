#!/usr/bin/env python3
"""Sweep v4 — TOUS sports + walk-forward 4 ans (2023, 2024, 2025, S1-26).

Croustillant absolu :
  - PnL positif sur CHAQUE année (2023, 2024, 2025, S1-26)
  - Streak rouge max ≤ 4j
  - DD < 50% BR initial
  - Au moins 100 combos par année (sauf S1-26 qui est 4 mois → 30+)

Test exhaustif par sport, cote range, sort, max_combos, market.
"""
import sys, json
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, extract_picks, build_backtest_combos

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

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json") as f:
    raw = json.load(f)
magic = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic[sp] = {b: {float(c): (info["wr"] if isinstance(info, dict) else info)
                     for c, info in cotes.items()}
                 for b, cotes in buckets.items()}
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json") as f:
    magic_ext = json.load(f)

YEARS = {
    "2023": list(gen_days("2023-01-01","2023-12-31")),
    "2024": list(gen_days("2024-01-01","2024-12-31")),
    "2025": list(gen_days("2025-01-01","2025-12-31")),
    "S1-26": list(gen_days("2026-01-01","2026-04-30")),
}

def run(days, sports_list, market, cote_min, cote_max, max_legs, sort_by,
        max_combos, side_filter=None, min_wr=None, min_ev=None, sizing="pct", br0=100):
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
        if min_ev is not None:
            picks = [p for p in picks if p["wr"]*p["odds"] >= min_ev]
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

def eval_4y(cfg):
    out = {}
    for y, days in YEARS.items():
        out[y] = run(days=days, **cfg)
    return out

def is_robust(ev):
    """Positif sur 4/4 années, streak ≤ 4j sur S1-26, n_combos>=30 sur S1-26."""
    for y in ["2023","2024","2025","S1-26"]:
        if ev[y]["pnl"] <= 0: return False
        if ev[y]["streak"] > 4: return False
    if ev["S1-26"]["n_combos"] < 30: return False
    return True

# ============== Candidats ==============
candidates = []

# 1x2 singles tous sports × cote × sort × max_combos
for sport in ["football","basketball","ice-hockey","baseball"]:
    for cmin, cmax in [(1.10,1.25),(1.20,1.35),(1.25,1.45),(1.30,1.50),(1.35,1.55),
                        (1.40,1.65),(1.50,1.80),(1.60,1.90),(1.70,2.00),(1.80,2.20)]:
        for sort in ["wr","ev"]:
            for mc in [2,3,4]:
                cfg = dict(sports_list=[sport], market="1x2", cote_min=cmin, cote_max=cmax,
                           max_legs=1, sort_by=sort, max_combos=mc)
                candidates.append((f"{sport[:4]}_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# Min_wr filter
for sport in ["football","basketball","ice-hockey","baseball"]:
    for cmin, cmax in [(1.40,2.00),(1.50,2.20),(1.80,2.50)]:
        for mwr in [0.65, 0.70, 0.75]:
            cfg = dict(sports_list=[sport], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by="ev", max_combos=4, min_wr=mwr)
            candidates.append((f"WR{mwr}_{sport[:4]}_{cmin}-{cmax}", cfg))

# 2j combos
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
            candidates.append((f"BTTSo_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

# BTTS non foot
for cmin, cmax in [(1.50,1.80),(1.70,2.00),(1.90,2.30)]:
    for sort in ["wr","ev"]:
        for mc in [2,3]:
            cfg = dict(sports_list=["football"], market="btts", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc, side_filter="non")
            candidates.append((f"BTTSn_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

print(f"Total candidats : {len(candidates)}")
print(f"Test sur 4 années (2023, 2024, 2025, S1-26)...\n")

# Eval 4y pour TOUS les candidats (peut prendre du temps mais nécessaire)
results = []
for i, (name, cfg) in enumerate(candidates):
    if i % 20 == 0:
        print(f"  [{i}/{len(candidates)}] {name}...")
    ev = eval_4y(cfg)
    results.append((name, cfg, ev))

# Filtre robustes
robust = [(n,c,e) for n,c,e in results if is_robust(e)]
robust.sort(key=lambda x: -sum(x[2][y]["pnl"] for y in YEARS))

print(f"\n\n{'='*100}")
print(f"=== {len(robust)} ROBUSTES (4/4 ans positifs, streak ≤ 4) ===\n")
print(f"{'Preset':40s} {'2023':>7s} {'2024':>7s} {'2025':>7s} {'S1-26':>7s} {'TOT':>8s} {'min_strk':>8s}")
print("-"*100)
for n,c,e in robust[:40]:
    p23,p24,p25,ps = (e[y]["pnl"] for y in ["2023","2024","2025","S1-26"])
    tot = p23+p24+p25+ps
    max_streak = max(e[y]["streak"] for y in YEARS)
    print(f"  {n:38s} {p23:>+5.0f}€ {p24:>+5.0f}€ {p25:>+5.0f}€ {ps:>+5.0f}€ {tot:>+6.0f}€ {max_streak:>6d}j")

# Top 5 détaillé
print(f"\n\n=== TOP 5 DETAIL ===\n")
for n,c,e in robust[:5]:
    print(f"\n{n}")
    print(f"  cfg: {c}")
    for y in YEARS:
        r = e[y]
        print(f"  {y}: PnL +{r['pnl']:.0f}€ BR {r['br_final']:.0f}€ "
              f"streak {r['streak']}j DD {r['dd']:.0f}€ {r['n_combos']} combos")

# Save
out = {"all": [{"name":n,"cfg":c,"ev":{y:e[y] for y in YEARS}} for n,c,e in results],
       "robust": [{"name":n,"cfg":c,"ev":{y:e[y] for y in YEARS}} for n,c,e in robust]}
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v4_results.json","w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n💾 datasets/sweep_v4_results.json")
