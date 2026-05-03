#!/usr/bin/env python3
"""Multi-comp 3 marchés foot (1x2 + btts + over_2_5) chaque sur match différent."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Multi-comp 3 marchés foot
for cmin, cmax in [(1.20, 1.40), (1.20, 1.50)]:
    for wr1 in [0.65, 0.70, 0.75]:
        for wr2 in [0.70, 0.75, 0.80]:
            for wr3 in [0.65, 0.70, 0.75]:
                for mc1, mc2, mc3 in [(2, 3, 3), (3, 3, 3), (3, 5, 5), (2, 5, 3)]:
                    for pct in [0.05, 0.07, 0.10]:
                        CANDS.append({
                            "id": f"M3M_1x2{wr1}+ou{wr2}+btts{wr3}_{cmin}-{cmax}_F{mc1}-{mc2}-{mc3}_pct{int(pct*100)}",
                            "components": [
                                {"sport": "football", "market": "1x2",
                                 "cote_min": cmin, "cote_max": cmax,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": mc1,
                                 "min_wr": wr1, "min_ev": None},
                                {"sport": "football", "market": "over_2_5",
                                 "cote_min": cmin, "cote_max": cmax,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": mc2,
                                 "min_wr": wr2, "min_ev": None},
                                {"sport": "football", "market": "btts",
                                 "cote_min": cmin, "cote_max": cmax,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": mc3,
                                 "min_wr": wr3, "min_ev": None},
                            ],
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                        })

# Multi-comp 4 marchés foot+hockey (1x2 + over_1_5 + over_2_5 + hockey 1x2)
for wr_o15 in [0.75, 0.80]:
    for wr_o25 in [0.70, 0.75]:
        for wr_h in [0.70, 0.75]:
            for mc_o15, mc_o25, mc_h in [(3, 3, 3), (5, 3, 5), (3, 5, 5)]:
                for pct in [0.05, 0.07, 0.10]:
                    CANDS.append({
                        "id": f"M4_o15{wr_o15}+o25{wr_o25}+H{wr_h}_F{mc_o15}-{mc_o25}-H{mc_h}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "football", "market": "over_1_5",
                             "cote_min": 1.15, "cote_max": 1.35,
                             "sort_by": "wr", "max_legs": 1, "max_combos": mc_o15,
                             "min_wr": wr_o15, "min_ev": None},
                            {"sport": "football", "market": "over_2_5",
                             "cote_min": 1.20, "cote_max": 1.45,
                             "sort_by": "wr", "max_legs": 1, "max_combos": mc_o25,
                             "min_wr": wr_o25, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.50,
                             "sort_by": "wr", "max_legs": 1, "max_combos": mc_h,
                             "min_wr": wr_h, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[Multi-mkt] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        results.append({"id": s["id"], "strat": s, "pnl": round(sm["pnl"],1),
            "br_mult": round(sm["bankroll_final"]/100,2), "dd": round(sm["dd_max"],1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1),2), "n_combos": sm["n_combos"]})
    except: pass

results.sort(key=lambda r: -r["ratio"])
print(f"\n=== TOP 20 par RATIO (record 24.4×) ===")
for r in results[:20]:
    flag = " 🏆" if r["ratio"] > 24.4 else ""
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

results.sort(key=lambda r: -r["br_mult"])
print(f"\n=== TOP 10 par BR mult ===")
for r in results[:10]:
    flag = " 🏆" if r["br_mult"] > 517 else (" 🥈" if r["br_mult"] > 336 else "")
    print(f"  BR×{r['br_mult']:>6.1f} ratio {r['ratio']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v7_multimkt.json","w") as f:
    json.dump({"top_ratio": sorted(results, key=lambda r:-r["ratio"])[:30],
               "top_br": sorted(results, key=lambda r:-r["br_mult"])[:30]}, f, indent=2)
print("\nSaved.")
