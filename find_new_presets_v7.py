#!/usr/bin/env python3
"""Sweep v7 — combos 2j et 3j avec min_wr STRICT sur picks individuels.

L'idée : sur 1 jambe le user peut perdre 1 pick à la fois mais le PnL/jour
est faible. En 2 jambes avec min_wr 0.70 chacune, le combo a WR ≈ 0.49 mais
cote × cote ≈ 2.5-3.0 → EV positive et réduit nb de jours rouges.
"""
import json, sys
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

def gen(s, e):
    s = datetime.strptime(s,"%Y-%m-%d").date(); e = datetime.strptime(e,"%Y-%m-%d").date()
    cur = s
    while cur <= e: yield cur.isoformat(); cur += timedelta(days=1)

def streak_red(daily):
    s=0;c=0
    for p in daily:
        if p<0: c+=1; s=max(s,c)
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
magic_prod={"_smart":True}
for sp,bs in raw.items():
    if sp=="_smart": continue
    magic_prod[sp]={b:{float(c):(i["wr"] if isinstance(i,dict) else i) for c,i in cs.items()} for b,cs in bs.items()}

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart_2025.json") as f: raw=json.load(f)
magic_2025={"_smart":True}
for sp,bs in raw.items():
    if sp=="_smart": continue
    magic_2025[sp]={b:{float(c):(i["wr"] if isinstance(i,dict) else i) for c,i in cs.items()} for b,cs in bs.items()}

DAYS_16M = list(gen("2025-01-01","2026-04-30"))
S1_26 = list(gen("2026-01-01","2026-04-30"))
MONTHS_26 = {
    "Jan26": list(gen("2026-01-01","2026-01-31")),
    "Feb26": list(gen("2026-02-01","2026-02-28")),
    "Mar26": list(gen("2026-03-01","2026-03-31")),
    "Apr26": list(gen("2026-04-01","2026-04-30")),
}

def run(magic, days, sports_list, market, cote_min, cote_max, max_legs, sort_by,
        max_combos, side_filter=None, min_wr=None, sizing="pct", br0=100):
    bankroll = br0; daily=[]; n_combos=0
    for d in days:
        idx=_get_index(); ms=idx.get(d,[])
        ms=[m for m in ms if m["sport"] in sports_list and lok(m["sport"], m.get("league",""))]
        if not ms: continue
        picks=extract_picks(ms, magic, market=market)
        if side_filter: picks=[p for p in picks if side_filter.lower() in p["selection"].lower()]
        if min_wr is not None: picks=[p for p in picks if p["wr"]>=min_wr]
        if max_legs==1: picks=[p for p in picks if cote_min<=p["odds"]<=cote_max]
        if not picks: continue
        combos=build_backtest_combos(picks, max_legs=max_legs, cote_min=cote_min, cote_max=cote_max,
                                     max_combos=max_combos*5, sort_by=sort_by)
        chosen=combos[:max_combos]
        if not chosen: continue
        day_pnl=0
        for c in chosen:
            stake = 10.0 if sizing=="flat" else max(0.5, bankroll*0.10)
            n_combos+=1
            if c["won"]: day_pnl += stake*(c["cote_t"]-1)
            else: day_pnl -= stake
        bankroll += day_pnl
        daily.append(day_pnl)
    pnl=sum(daily)
    return {"pnl":pnl, "br_final":bankroll,
            "ng":sum(1 for p in daily if p>0), "nr":sum(1 for p in daily if p<0),
            "n_combos":n_combos, "streak":streak_red(daily), "dd":max_dd(daily)}

candidates = []

# 2j combos avec min_wr STRICT chaque jambe
for sport_combo in [["football"],["basketball"],["ice-hockey"],
                     ["football","ice-hockey"],["football","basketball"]]:
    for cmin, cmax in [(1.40,1.70),(1.50,1.85),(1.50,2.00),(1.60,2.10),(1.30,1.70)]:
        # cote totale env. cmin² à cmax² mais on filtre par cote totale dans l'engine
        for mwr in [0.60, 0.65, 0.70, 0.75]:
            for sort in ["wr","ev"]:
                for mc in [1,2,3]:
                    cfg = dict(sports_list=sport_combo, market="1x2",
                               cote_min=cmin*cmin*0.9, cote_max=cmax*cmax*1.1,
                               max_legs=2, sort_by=sort, max_combos=mc, min_wr=mwr)
                    name = f"2j_{'+'.join(s[:3] for s in sport_combo)}_{cmin}-{cmax}_wr{mwr}_{sort}_mc{mc}"
                    candidates.append((name, cfg))

# 3j foot avec min_wr 0.65+ chaque jambe
for cmin, cmax in [(1.40,1.65),(1.50,1.80)]:
    for mwr in [0.65, 0.70]:
        for sort in ["ev","wr"]:
            for mc in [1,2]:
                ctot_max = cmax**3 * 1.1
                cfg = dict(sports_list=["football"], market="1x2",
                           cote_min=cmin**3*0.9, cote_max=ctot_max,
                           max_legs=3, sort_by=sort, max_combos=mc, min_wr=mwr)
                candidates.append((f"3j_foot_{cmin}-{cmax}_wr{mwr}_{sort}_mc{mc}", cfg))

# Volume haut single multi-sport cote 1.40-1.80 sort wr (4-6 picks/j)
for cmin, cmax in [(1.30,1.60),(1.40,1.70),(1.40,1.80),(1.50,1.85)]:
    for sort in ["wr","ev"]:
        for mc in [4,5,6,8]:
            for sports in [["football","basketball","ice-hockey"],["football","ice-hockey"],
                          ["football","basketball","ice-hockey","baseball"]]:
                cfg = dict(sports_list=sports, market="1x2", cote_min=cmin, cote_max=cmax,
                           max_legs=1, sort_by=sort, max_combos=mc)
                name = f"V_{'+'.join(s[:3] for s in sports)}_{cmin}-{cmax}_{sort}_mc{mc}"
                candidates.append((name, cfg))

print(f"Total candidats : {len(candidates)}")

# Phase 1 : magic_2025 sur 16m OOS pur
print(f"\n[Phase 1] magic_2025 sur 16m OOS pur...")
phase1=[]
for i,(n,c) in enumerate(candidates):
    if i%50==0: print(f"  [{i}/{len(candidates)}]")
    r=run(magic_2025, days=DAYS_16M, **c)
    phase1.append((n,c,r))
phase1.sort(key=lambda x:-x[2]["pnl"])

print(f"\n=== TOP 30 (magic_2025 16m) ===")
print(f"{'Preset':50s} {'PnL':>8s} {'streak':>6s} {'DD':>7s} {'combos':>6s}")
for n,c,r in phase1[:30]:
    if r["n_combos"]<30: continue
    print(f"  {n:48s} {r['pnl']:>+6.0f}€ {r['streak']:>5d}j {r['dd']:>6.0f}€ {r['n_combos']:>6d}")

# Phase 2 : top 20 sur magic_prod S1-26
print(f"\n\n[Phase 2] Top 20 sur magic_prod S1-26 mois par mois...\n")
phase2=[]
for n,c,r1 in phase1[:20]:
    if r1["n_combos"]<30: continue
    monthly={m:run(magic_prod,days=days,**c) for m,days in MONTHS_26.items()}
    rt=run(magic_prod,days=S1_26,**c)
    phase2.append((n,c,r1,monthly,rt))

print(f"{'Preset':50s} {'Jan':>6s} {'Feb':>6s} {'Mar':>6s} {'Apr':>6s} {'TOT':>6s} {'strk':>5s} {'combo':>5s}")
for n,c,r1,monthly,rt in phase2:
    parts=[f"{monthly[m]['pnl']:>+4.0f}€" for m in MONTHS_26]
    n_pos=sum(1 for m in MONTHS_26 if monthly[m]["pnl"]>0)
    n_pos_or_neutral=sum(1 for m in MONTHS_26 if monthly[m]["pnl"]>=-3)
    flag="★" if n_pos_or_neutral>=4 and rt["streak"]<=3 and rt["pnl"]>=100 else " "
    print(f"{flag} {n:48s} {' '.join(parts)} {rt['pnl']:>+4.0f}€ {rt['streak']:>3d}j {rt['n_combos']:>5d}")

# Croustillants
print(f"\n\n=== ★ CROUSTILLANTS ABSOLUS ===")
crous=[]
for n,c,r1,monthly,rt in phase2:
    n_pos_or_neutral=sum(1 for m in MONTHS_26 if monthly[m]["pnl"]>=-3)
    if n_pos_or_neutral<4: continue
    if rt["streak"]>3: continue
    if rt["pnl"]<100: continue
    crous.append((n,c,r1,monthly,rt))
if crous:
    for n,c,r1,monthly,rt in crous:
        print(f"\n{n}")
        print(f"  cfg: {c}")
        for m in MONTHS_26:
            x=monthly[m]
            print(f"  {m}: +{x['pnl']:.0f}€ streak {x['streak']}j combos {x['n_combos']}")
        print(f"  S1-26: +{rt['pnl']:.0f}€ BR_fin {rt['br_final']:.0f}€ streak {rt['streak']}j DD {rt['dd']:.0f}€")
        print(f"  16m OOS pur: +{r1['pnl']:.0f}€")
else:
    print("  Aucun candidat ne bat F_1.6-1.9_wr_mc3 baseline")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v7_results.json","w") as f:
    json.dump({"phase1":[{"name":n,"cfg":c,"r":r} for n,c,r in phase1[:50]],
               "phase2":[{"name":n,"cfg":c,"monthly":m,"total":t} for n,c,_,m,t in phase2],
               "crous":[{"name":n,"cfg":c,"monthly":m,"total":t} for n,c,_,m,t in crous]},
              f, indent=2, default=str)
