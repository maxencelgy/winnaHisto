#!/usr/bin/env python3
"""Sweep min_wr strict — push WR threshold à 0.70-0.80 pour ne garder que les ultra-favoris."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. F3H3/F3H5 BTTS+OU avec min_wr 0.70-0.85 strict
for foot_wr in [0.70, 0.75, 0.80, 0.85]:
    for hockey_wr in [0.70, 0.75, 0.80]:
        for foot_mc in [3, 5]:
            for hockey_mc in [3, 5]:
                for pct in [0.05, 0.07, 0.10]:
                    CANDS.append({
                        "id": f"SWR_BTTSO_F{foot_mc}H{hockey_mc}_fw{foot_wr}_hw{hockey_wr}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "football", "market": "btts,over_1_5,over_2_5",
                             "cote_min": 1.20, "cote_max": 1.40,
                             "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                             "min_wr": foot_wr, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.50,
                             "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                             "min_wr": hockey_wr, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

# B. Foot O 1.5 single avec min_wr ultra-strict
for cmin, cmax in [(1.30, 1.45), (1.40, 1.55), (1.40, 1.65)]:
    for mwr in [0.70, 0.75, 0.80, 0.85]:
        for mc in [3, 5, 7]:
            for pct in [0.05, 0.08, 0.10]:
                CANDS.append({
                    "id": f"SWR_o15_{cmin}-{cmax}_wr{mwr}_mc{mc}_pct{int(pct*100)}",
                    "components": [{
                        "sport": "football", "market": "over_1_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

print(f"[Strict WR] {len(CANDS)} configs")

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

viable = [r for r in results if r["ratio"] >= 12 and r["br_mult"] >= 5]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Strict WR] {len(viable)} viables (ratio ≥12, BR ≥5)")

print(f"\n=== TOP 20 par RATIO ===")
for r in viable[:20]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}")

print(f"\n=== TOP 10 par BR mult ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:10]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_strict_wr.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
