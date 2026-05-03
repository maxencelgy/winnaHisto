#!/usr/bin/env python3
"""Sweep FINAL — combos multi-sport WR strict + variantes inexploitées."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Multi-comp 4 sports F+H+B+T avec WR strict
for foot_wr in [0.70, 0.75, 0.80]:
    for hockey_wr in [0.65, 0.70, 0.75]:
        for tennis_mc in [1, 2, 3]:
            for basket_mc in [0, 1, 2]:
                for foot_mc in [3, 5]:
                    for hockey_mc in [3, 5]:
                        for pct in [0.07, 0.10]:
                            comps = [
                                {"sport": "football", "market": "btts,over_1_5,over_2_5",
                                 "cote_min": 1.20, "cote_max": 1.40,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                                 "min_wr": foot_wr, "min_ev": None},
                                {"sport": "ice-hockey", "market": "1x2",
                                 "cote_min": 1.20, "cote_max": 1.50,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                                 "min_wr": hockey_wr, "min_ev": None},
                            ]
                            if basket_mc > 0:
                                comps.append({"sport": "basketball", "market": "1x2",
                                              "cote_min": 1.20, "cote_max": 1.50,
                                              "sort_by": "wr", "max_legs": 1, "max_combos": basket_mc,
                                              "min_wr": 0.65, "min_ev": None})
                            if tennis_mc > 0:
                                comps.append({"sport": "tennis", "market": "1x2",
                                              "cote_min": 1.30, "cote_max": 1.60,
                                              "sort_by": "wr", "max_legs": 1, "max_combos": tennis_mc,
                                              "min_wr": 0.65, "min_ev": None})
                            CANDS.append({
                                "id": f"FIN_F{foot_mc}H{hockey_mc}B{basket_mc}T{tennis_mc}_fw{foot_wr}_hw{hockey_wr}_pct{int(pct*100)}",
                                "components": comps,
                                "dedup": "max1",
                                "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                            })

print(f"[Final mixes] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        results.append({
            "id": s["id"], "strat": s,
            "pnl": round(sm["pnl"], 1),
            "br_mult": round(sm["bankroll_final"]/100, 2),
            "dd": round(sm["dd_max"], 1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1), 2),
            "streak": sm["streak_red_max"],
            "n_combos": sm["n_combos"],
        })
    except Exception:
        pass

viable = [r for r in results if r["ratio"] >= 18 and r["br_mult"] >= 50]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Final mixes] {len(viable)} viables (ratio ≥18, BR ≥50)")

print(f"\n=== TOP 20 par RATIO ===")
for r in viable[:20]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}")

print(f"\n=== TOP 10 par BR mult (ratio ≥18) ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:10]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/final_mixes.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
