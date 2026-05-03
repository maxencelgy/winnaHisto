#!/usr/bin/env python3
"""Sweep WFR EXTRÊME — pousser sizing 10-20% sur sweet spot identifié."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Foot O 1.5 sweet spot — sizing extreme + cote variations
for foot_mc in [3, 5, 7]:
    for pct in [0.10, 0.12, 0.15, 0.18, 0.20]:
        for cote_range in [(1.30, 1.55), (1.40, 1.65), (1.50, 1.75)]:
            for mwr in [0.60, 0.65, 0.70]:
                CANDS.append({
                    "id": f"EXT_o15_mc{foot_mc}_pct{int(pct*100)}_{cote_range[0]}-{cote_range[1]}_wr{mwr}",
                    "label": "Foot O 1.5 EXTREME",
                    "components": [{
                        "sport": "football", "market": "over_1_5",
                        "cote_min": cote_range[0], "cote_max": cote_range[1],
                        "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# Multi-comp aggro avec foot OU 1.5 + Hockey + Basket
for foot_mc in [3, 5, 7]:
    for hockey_mc in [2, 3, 5]:
        for pct in [0.05, 0.07, 0.10, 0.12]:
            CANDS.append({
                "id": f"EXT_FH_F{foot_mc}H{hockey_mc}_pct{int(pct*100)}",
                "label": "Foot OU + Hockey AGGRO",
                "components": [
                    {"sport": "football", "market": "over_1_5",
                     "cote_min": 1.30, "cote_max": 1.55,
                     "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                     "min_wr": 0.65, "min_ev": None},
                    {"sport": "ice-hockey", "market": "1x2",
                     "cote_min": 1.20, "cote_max": 1.50,
                     "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                     "min_wr": 0.65, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
            })

# Combo 2j + Multi-sport
for cote_total in [(1.5, 2.5), (1.7, 2.5), (2.0, 3.0)]:
    for sports in [["football"], ["football", "ice-hockey"], ["football", "ice-hockey", "basketball"]]:
        for mc in [1, 2, 3]:
            for pct in [0.03, 0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"EXT_C2j_{'+'.join(s[:3] for s in sports)}_{cote_total[0]}-{cote_total[1]}_mc{mc}_pct{int(pct*100)}",
                    "label": "Combo 2j multi-sport",
                    "components": [{
                        "sports": sports, "market": "1x2",
                        "cote_min": cote_total[0], "cote_max": cote_total[1],
                        "sort_by": "ev", "max_legs": 2, "max_combos": mc,
                        "min_wr": 0.55, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

print(f"[WFR EXTREME] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 30 == 0: print(f"  [{i}/{len(CANDS)}]")
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

viable = [r for r in results if r["ratio"] >= 4 and r["br_mult"] >= 5]
viable.sort(key=lambda r: -r["br_mult"])

print(f"\n[WFR EXTREME] {len(viable)} viables (ratio ≥4, BR ≥5)")

print(f"\n=== TOP 25 par BR multiplier ===")
for r in viable[:25]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d}  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_extreme.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
