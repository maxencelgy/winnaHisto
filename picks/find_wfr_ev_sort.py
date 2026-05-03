#!/usr/bin/env python3
"""Sweep sort_by EV — multi-comp avec value picks (sort EV plutôt que WR)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. F3H3 BTTS+OU avec sort EV
for foot_mc in [3, 5]:
    for hockey_mc in [3, 5]:
        for cote_h in [(1.30, 1.55), (1.40, 1.65)]:  # Hockey value mid
            for pct in [0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"EV_F{foot_mc}H{hockey_mc}_{cote_h[0]}-{cote_h[1]}_pct{int(pct*100)}",
                    "components": [
                        {"sport": "football", "market": "btts,over_1_5,over_2_5",
                         "cote_min": 1.20, "cote_max": 1.40,
                         "sort_by": "ev", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": None, "min_ev": 1.05},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": cote_h[0], "cote_max": cote_h[1],
                         "sort_by": "ev", "max_legs": 1, "max_combos": hockey_mc,
                         "min_wr": None, "min_ev": 1.05},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# B. Foot mid-cote 1.5-1.85 sort EV
for foot_mc in [2, 3, 5]:
    for cote in [(1.50, 1.75), (1.55, 1.85), (1.60, 1.90)]:
        for mev in [1.05, 1.10, 1.15]:
            for pct in [0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"EV_foo_{cote[0]}-{cote[1]}_ev{mev}_mc{foot_mc}_pct{int(pct*100)}",
                    "components": [{
                        "sport": "football", "market": "1x2",
                        "cote_min": cote[0], "cote_max": cote[1],
                        "sort_by": "ev", "max_legs": 1, "max_combos": foot_mc,
                        "min_wr": None, "min_ev": mev,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# C. Combo 2j multi-sport sort EV
for cote_t in [(1.6, 2.5), (1.8, 2.8), (2.0, 3.0)]:
    for sports in [["football", "ice-hockey"],
                   ["football", "ice-hockey", "basketball"]]:
        for mc in [1, 2, 3]:
            for pct in [0.03, 0.05, 0.07]:
                for mwr in [0.55, 0.60]:
                    CANDS.append({
                        "id": f"EV_C2j_{'+'.join(s[:3] for s in sports)}_{cote_t[0]}-{cote_t[1]}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                        "components": [{
                            "sports": sports, "market": "1x2",
                            "cote_min": cote_t[0], "cote_max": cote_t[1],
                            "sort_by": "ev", "max_legs": 2, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[EV sort sweep] {len(CANDS)} configs")

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

viable = [r for r in results if r["ratio"] >= 5 and r["br_mult"] >= 5]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[EV sort] {len(viable)} viables (ratio ≥5, BR ≥5)")

print(f"\n=== TOP 25 par RATIO ===")
for r in viable[:25]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>4d} | {r['id'][:55]}")

print(f"\n=== TOP 15 par BR mult ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:15]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_ev_sort.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
