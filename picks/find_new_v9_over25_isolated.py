#!/usr/bin/env python3
"""OVER 2.5 isolé seul + cote étroite + combos OU dual-leg — angles non testés."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Over 2.5 isolé seul WR strict
for cmin, cmax in [(1.20, 1.35), (1.25, 1.40), (1.30, 1.50), (1.40, 1.60)]:
    for mc in [3, 5, 8, 12]:
        for mwr in [0.60, 0.65, 0.70, 0.75]:
            for pct in [0.05, 0.07, 0.10, 0.15]:
                CANDS.append({
                    "id": f"O25I_{cmin}-{cmax}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                    "components": [{"sport": "football", "market": "over_2_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None}],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# B. Combo 2j tous foot OU 1.5 (dual-leg)
for cmin, cmax in [(1.10, 1.20), (1.15, 1.25), (1.20, 1.30)]:
    for mc in [1, 2, 3]:
        for mwr in [0.75, 0.80, 0.85]:
            for pct in [0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"OU_DUO_{cmin}-{cmax}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                    "components": [{"sport": "football", "market": "over_1_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 2, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None}],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# C. Cote très étroite 1.20-1.30 multi-comp F+H (laser-focused)
for cmin, cmax in [(1.18, 1.28), (1.20, 1.30), (1.22, 1.32), (1.25, 1.35)]:
    for foot_wr in [0.70, 0.75, 0.80]:
        for hockey_wr in [0.70, 0.75]:
            for f_mc, h_mc in [(3, 5), (5, 5), (3, 8), (5, 8)]:
                for pct in [0.05, 0.07, 0.10]:
                    CANDS.append({
                        "id": f"NARROW_{cmin}-{cmax}_fw{foot_wr}_hw{hockey_wr}_F{f_mc}H{h_mc}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "football", "market": "btts,over_1_5,over_2_5",
                             "cote_min": cmin, "cote_max": cmax,
                             "sort_by": "wr", "max_legs": 1, "max_combos": f_mc,
                             "min_wr": foot_wr, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": cmin, "cote_max": cmax,
                             "sort_by": "wr", "max_legs": 1, "max_combos": h_mc,
                             "min_wr": hockey_wr, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[O25 + duo + narrow] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 60 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        results.append({"id": s["id"], "strat": s, "pnl": round(sm["pnl"],1),
            "br_mult": round(sm["bankroll_final"]/100,2), "dd": round(sm["dd_max"],1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1),2), "n_combos": sm["n_combos"]})
    except: pass

results.sort(key=lambda r: -r["ratio"])
print(f"\n=== TOP 25 par RATIO (record 24.4×) ===")
for r in results[:25]:
    flag = " 🏆" if r["ratio"] > 24.4 else ""
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

results.sort(key=lambda r: -r["br_mult"])
print(f"\n=== TOP 10 par BR mult ===")
for r in results[:10]:
    flag = " 🏆" if r["br_mult"] > 517 else (" 🥈" if r["br_mult"] > 336 else "")
    print(f"  BR×{r['br_mult']:>6.1f} ratio {r['ratio']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v9_o25.json","w") as f:
    json.dump({"top_ratio": sorted(results, key=lambda r:-r["ratio"])[:30],
               "top_br": sorted(results, key=lambda r:-r["br_mult"])[:30]}, f, indent=2)
print("\nSaved.")
