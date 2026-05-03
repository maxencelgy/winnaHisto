#!/usr/bin/env python3
"""Sweep WFR aggro — pousse le sizing 7-15% sur les top profils Winamax FR
pour trouver le BR mult max sans casser le ratio."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Top profil identifié : Foot O 1.5 cote 1.4-1.65 wr0.65 mc5 — variants sizing
for foot_mc in [3, 5, 7, 10]:
    for pct in [0.05, 0.07, 0.08, 0.10, 0.12, 0.15]:
        for mwr in [0.60, 0.65, 0.70]:
            CANDS.append({
                "id": f"AGRO_foo_o15_mc{foot_mc}_pct{int(pct*100)}_wr{mwr}",
                "label": "Foot O 1.5 aggro sizing",
                "components": [{
                    "sport": "football", "market": "over_1_5",
                    "cote_min": 1.40, "cote_max": 1.65,
                    "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                    "min_wr": mwr, "min_ev": None,
                }],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
            })

# Multi-comp F+H+B avec sizing aggro
for foot_mc in [3, 5, 7]:
    for hockey_mc in [2, 3, 5]:
        for basket_mc in [1, 2, 3]:
            for pct in [0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"AGRO_FHB_F{foot_mc}H{hockey_mc}B{basket_mc}_pct{int(pct*100)}",
                    "label": "Multi FHB aggro",
                    "components": [
                        {"sport": "football", "market": "over_1_5",
                         "cote_min": 1.30, "cote_max": 1.55,
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": 0.65, "min_ev": None},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.50,
                         "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                         "min_wr": 0.65, "min_ev": None},
                        {"sport": "basketball", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.50,
                         "sort_by": "wr", "max_legs": 1, "max_combos": basket_mc,
                         "min_wr": 0.65, "min_ev": None},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# Sizing tiered (différent stake selon cote totale combo)
for foot_mc in [3, 5]:
    for tier_low in [0.10, 0.12, 0.15]:
        CANDS.append({
            "id": f"TIERED_foo_mc{foot_mc}_low{int(tier_low*100)}",
            "label": "Foot O 1.5 sizing tiered",
            "components": [{
                "sport": "football", "market": "over_1_5",
                "cote_min": 1.40, "cote_max": 1.65,
                "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                "min_wr": 0.65, "min_ev": None,
            }],
            "dedup": "max1",
            "sizing": {"mode": "risk_tiered", "min_stake": 0.5,
                       "tiers": [{"cote_max": 1.50, "pct": tier_low},
                                 {"cote_max": 1.70, "pct": tier_low*0.7},
                                 {"cote_max": 999, "pct": tier_low*0.5}]},
        })

print(f"[WFR aggro classics] {len(CANDS)} configs")

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

# Filter ratio ≥ 4 + BR mult ≥ 3
viable = [r for r in results if r["ratio"] >= 4 and r["br_mult"] >= 3 and r["dd"] <= 200]
viable.sort(key=lambda r: -r["br_mult"])

print(f"\n[WFR aggro] {len(viable)} viables")

print(f"\n=== TOP 25 par BR multiplier (ratio ≥4) ===")
for r in viable[:25]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | PnL +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ streak {r['streak']:>2d}j #{r['n_combos']:>4d} | {r['id'][:50]}")

print(f"\n=== TOP 15 par RATIO (BR ≥3) ===")
viable.sort(key=lambda r: -r["ratio"])
for r in viable[:15]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>4.1f} | +{r['pnl']:>4.0f}€ DD {r['dd']:>3.0f}€ | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_aggro.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
