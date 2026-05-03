#!/usr/bin/env python3
"""Sweep v6 — refinement autour de F_1.6-1.9_wr_mc3 (winner v5).

Objectif : trouver une variante encore mieux ou confirmer que wr_mc3 est l'optimum.

Tests :
  - Cote ranges adjacents (1.55-1.85, 1.6-1.85, 1.6-1.95, 1.55-1.9, 1.65-1.95, 1.55-1.95, 1.5-2.0)
  - Ajout min_wr filter (0.55, 0.60, 0.65) sur 1.6-1.9
  - Ajout min_ev filter (1.05, 1.08, 1.10) sur 1.6-1.9
  - max_combos 1, 2, 3, 4, 5
  - Filter par grandes ligues (Top5 European)

Test sur :
  - Magic 2025 sur 16 mois OOS pur (Q1-25 → Apr26)
  - Magic prod sur S1-26 (Jan-Apr 2026)
"""
import json, sys
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, extract_picks, build_backtest_combos

WHITELIST_FULL = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
        "laliga 2","serie b","ligue 2","champions league","europa league","conference",
        "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
        "mls","liga mx","brasileirão","brasileirao","coupe","fa cup",
        "primeira liga","primera división"],
}
WHITELIST_TOP5 = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1",
                 "champions league","europa league","conference"],
}
REJECT = ["doubles","qualifying","u23","u21","u19","u18","reserve","youth","next pro",
          "regionalliga","série c","i-league","exhibition"]

def make_lok(whitelist):
    def lok(sport, lg):
        if not lg: return False
        l = lg.lower()
        if any(r in l for r in REJECT): return False
        return any(p in l for p in whitelist.get(sport, []))
    return lok

lok_full = make_lok(WHITELIST_FULL)
lok_top5 = make_lok(WHITELIST_TOP5)

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

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json") as f: raw=json.load(f)
magic_prod = {"_smart":True}
for sp,bs in raw.items():
    if sp=="_smart": continue
    magic_prod[sp]={b:{float(c):(i["wr"] if isinstance(i,dict) else i) for c,i in cs.items()} for b,cs in bs.items()}

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart_2025.json") as f: raw=json.load(f)
magic_2025 = {"_smart":True}
for sp,bs in raw.items():
    if sp=="_smart": continue
    magic_2025[sp]={b:{float(c):(i["wr"] if isinstance(i,dict) else i) for c,i in cs.items()} for b,cs in bs.items()}

def run(magic, days, lok_fn, sports_list, market, cote_min, cote_max, max_legs, sort_by,
        max_combos, side_filter=None, min_wr=None, min_ev=None, sizing="pct", br0=100):
    bankroll = br0; daily = []; n_combos = 0
    for d in days:
        idx = _get_index()
        ms = idx.get(d, [])
        ms = [m for m in ms if m["sport"] in sports_list and lok_fn(m["sport"], m.get("league",""))]
        if not ms: continue
        picks = extract_picks(ms, magic, market=market)
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

# Période 1 : magic_2025 sur Q1-25 → Apr26
DAYS_16M = list(gen_days("2025-01-01","2026-04-30"))
# Période 2 : magic_prod sur S1-26
S1_26 = list(gen_days("2026-01-01","2026-04-30"))
MONTHS_26 = {
    "Jan26": list(gen_days("2026-01-01","2026-01-31")),
    "Feb26": list(gen_days("2026-02-01","2026-02-28")),
    "Mar26": list(gen_days("2026-03-01","2026-03-31")),
    "Apr26": list(gen_days("2026-04-01","2026-04-30")),
}

# Variations
candidates = []

# A. Cote ranges autour de 1.6-1.9
for cmin, cmax in [(1.50,1.80),(1.55,1.85),(1.55,1.90),(1.55,1.95),(1.60,1.85),(1.60,1.90),
                    (1.60,1.95),(1.60,2.00),(1.65,1.95),(1.65,2.00),(1.50,2.00),(1.40,2.00),
                    (1.70,2.00),(1.50,1.85),(1.45,1.85)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["football"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"FA_{cmin}-{cmax}_{sort}_mc{mc}", cfg, lok_full))

# B. F_1.6-1.9 + min_wr
for mwr in [0.50, 0.55, 0.60, 0.65]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["football"], market="1x2", cote_min=1.60, cote_max=1.90,
                       max_legs=1, sort_by=sort, max_combos=mc, min_wr=mwr)
            candidates.append((f"FB_wr{mwr}_{sort}_mc{mc}", cfg, lok_full))

# C. F_1.6-1.9 + min_ev
for mev in [1.05, 1.08, 1.10, 1.12]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["football"], market="1x2", cote_min=1.60, cote_max=1.90,
                       max_legs=1, sort_by=sort, max_combos=mc, min_ev=mev)
            candidates.append((f"FC_ev{mev}_{sort}_mc{mc}", cfg, lok_full))

# D. F_1.6-1.9 mais Top5 leagues seulement
for sort in ["wr","ev"]:
    for mc in [2,3,4]:
        cfg = dict(sports_list=["football"], market="1x2", cote_min=1.60, cote_max=1.90,
                   max_legs=1, sort_by=sort, max_combos=mc)
        candidates.append((f"FD_top5_{sort}_mc{mc}", cfg, lok_top5))

# E. Cote 1.6-1.9 avec min_wr ET min_ev combinés
for mwr in [0.55, 0.60]:
    for mev in [1.05, 1.08]:
        for sort in ["wr","ev"]:
            cfg = dict(sports_list=["football"], market="1x2", cote_min=1.60, cote_max=1.90,
                       max_legs=1, sort_by=sort, max_combos=3, min_wr=mwr, min_ev=mev)
            candidates.append((f"FE_wr{mwr}_ev{mev}_{sort}", cfg, lok_full))

print(f"Total candidats : {len(candidates)}")

# Phase 1 : test rapide sur magic_2025 sur 16 mois OOS pur
print("\n[Phase 1] magic_2025 sur 16 mois OOS pur (Q1-25 → Apr26)...")
phase1 = []
for i,(n,c,lk) in enumerate(candidates):
    if i % 30 == 0: print(f"  [{i}/{len(candidates)}]")
    r = run(magic_2025, days=DAYS_16M, lok_fn=lk, **c)
    phase1.append((n,c,lk,r))

phase1.sort(key=lambda x: -x[3]["pnl"])

print(f"\n=== TOP 30 phase 1 (16m OOS pur sur magic_2025) ===")
print(f"{'Preset':40s} {'PnL':>8s} {'BR_fin':>8s} {'streak':>6s} {'DD':>7s} {'combos':>6s}")
print("-"*92)
for n,c,lk,r in phase1[:30]:
    print(f"  {n:38s} {r['pnl']:>+6.0f}€ {r['br_final']:>7.0f}€ {r['streak']:>5d}j {r['dd']:>6.0f}€ {r['n_combos']:>6d}")

# Phase 2 : top 15 retesté sur magic_prod sur S1-26 mois par mois
print(f"\n\n[Phase 2] Top 15 sur magic_prod S1-26 mois par mois...\n")
print(f"{'Preset':40s} {'Jan':>7s} {'Feb':>7s} {'Mar':>7s} {'Apr':>7s} {'TOT':>7s} {'streak':>6s} {'combos':>6s}")
print("-"*100)

phase2 = []
for n,c,lk,r1 in phase1[:15]:
    monthly = {m: run(magic_prod, days=days, lok_fn=lk, **c) for m, days in MONTHS_26.items()}
    rt = run(magic_prod, days=S1_26, lok_fn=lk, **c)
    phase2.append((n,c,lk,r1,monthly,rt))
    parts = [f"{monthly[m]['pnl']:>+5.0f}€" for m in MONTHS_26]
    n_pos = sum(1 for m in MONTHS_26 if monthly[m]["pnl"] > 0)
    n_neutral = sum(1 for m in MONTHS_26 if abs(monthly[m]["pnl"]) <= 5)
    flag = "★" if n_pos+n_neutral >= 4 and rt["streak"] <= 3 else " "
    print(f"{flag} {n:38s} {' '.join(parts)} {rt['pnl']:>+5.0f}€ {rt['streak']:>5d}j {rt['n_combos']:>6d}")

# Croustillants : 4/4 mois positifs ou neutres + streak ≤ 3 + PnL S1-26 ≥ 100€
print(f"\n\n=== ★ CROUSTILLANTS ABSOLUS (4/4 mois OK + streak ≤ 3 + PnL ≥ 100€ S1-26) ===\n")
crous = []
for n,c,lk,r1,monthly,rt in phase2:
    n_pos = sum(1 for m in MONTHS_26 if monthly[m]["pnl"] > 0)
    n_neutral = sum(1 for m in MONTHS_26 if abs(monthly[m]["pnl"]) <= 5)
    if n_pos + n_neutral < 4: continue
    if rt["streak"] > 3: continue
    if rt["pnl"] < 100: continue
    crous.append((n,c,lk,r1,monthly,rt))

if crous:
    for n,c,lk,r1,monthly,rt in crous:
        print(f"  {n}")
        print(f"    cfg: {c}")
        for m in MONTHS_26:
            x = monthly[m]
            print(f"    {m}: +{x['pnl']:.0f}€ streak {x['streak']}j combos {x['n_combos']}")
        print(f"    S1-26 TOT: +{rt['pnl']:.0f}€ BR_fin {rt['br_final']:.0f}€ streak {rt['streak']}j DD {rt['dd']:.0f}€ ({rt['n_combos']} combos)")
        print(f"    16m OOS pur: +{r1['pnl']:.0f}€ ({r1['n_combos']} combos sur 16m)\n")
else:
    print("  Aucun candidat ne bat le baseline F_1.6-1.9_wr_mc3")

# Save
out = {"phase1":[{"name":n,"cfg":c,"r":r} for n,c,_,r in phase1[:50]],
       "phase2":[{"name":n,"cfg":c,"monthly":m,"total":t} for n,c,_,_,m,t in phase2],
       "crous":[{"name":n,"cfg":c,"monthly":m,"total":t} for n,c,_,_,m,t in crous]}
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v6_results.json","w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n💾 datasets/sweep_v6_results.json")
