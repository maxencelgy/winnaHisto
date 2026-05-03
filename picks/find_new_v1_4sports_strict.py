#!/usr/bin/env python3
"""Multi-comp 4 sports F+H+B+T, ALL WR strict ≥75%."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# 4 sports F+H+B+T avec WR strict élevé
for foot_wr in [0.70, 0.75, 0.80]:
    for hockey_wr in [0.70, 0.75, 0.80]:
        for basket_wr in [0.65, 0.70, 0.75]:
            for tennis_wr in [0.70, 0.75]:
                for f_mc in [3, 5]:
                    for h_mc in [3, 5]:
                        for b_mc in [1, 2]:
                            for t_mc in [1, 2]:
                                for pct in [0.05, 0.07, 0.10]:
                                    CANDS.append({
                                        "id": f"M4S_fw{foot_wr}_hw{hockey_wr}_bw{basket_wr}_tw{tennis_wr}_F{f_mc}H{h_mc}B{b_mc}T{t_mc}_pct{int(pct*100)}",
                                        "components": [
                                            {"sport": "football", "market": "btts,over_1_5,over_2_5",
                                             "cote_min": 1.20, "cote_max": 1.40,
                                             "sort_by": "wr", "max_legs": 1, "max_combos": f_mc,
                                             "min_wr": foot_wr, "min_ev": None},
                                            {"sport": "ice-hockey", "market": "1x2",
                                             "cote_min": 1.20, "cote_max": 1.50,
                                             "sort_by": "wr", "max_legs": 1, "max_combos": h_mc,
                                             "min_wr": hockey_wr, "min_ev": None},
                                            {"sport": "basketball", "market": "1x2",
                                             "cote_min": 1.20, "cote_max": 1.50,
                                             "sort_by": "wr", "max_legs": 1, "max_combos": b_mc,
                                             "min_wr": basket_wr, "min_ev": None},
                                            {"sport": "tennis", "market": "1x2",
                                             "cote_min": 1.20, "cote_max": 1.60,
                                             "sort_by": "wr", "max_legs": 1, "max_combos": t_mc,
                                             "min_wr": tennis_wr, "min_ev": None},
                                        ],
                                        "dedup": "max1",
                                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                                    })

print(f"[4sports strict] {len(CANDS)} configs")

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

viable = [r for r in results if r["ratio"] >= 18 and r["br_mult"] >= 50]
viable.sort(key=lambda r: -r["ratio"])
print(f"\n[4sports] {len(viable)} viables (ratio≥18, BR×≥50)")
print("=== TOP 15 par RATIO ===")
for r in viable[:15]:
    flag = " 🏆" if r["ratio"] > 24.4 or r["br_mult"] > 336 else ""
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:60]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v1_4sports.json","w") as f:
    json.dump({"viable": viable[:50], "all": results}, f, indent=2)
print("\nSaved.")
