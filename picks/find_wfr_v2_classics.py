#!/usr/bin/env python3
"""Sweep WFR v2 — explore CLASSIQUES (multi-comp) avec filtre Winamax FR.
Vise ratio PnL/DD ≥ 5×, BR mult ≥ 3×."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WINAMAX_FR_EXCLUDED = [
    "liga mx","egyptian","cyprus","ligapro","primera división, clausura",
    "brasileirão série d","brasileirão série b","scottish premiership",
    "first professional league","danish superliga","superliga",
    "niké liga","swiss super league","austrian bundesliga",
    "stoiximan super league","czech first league","canadian premier",
    "usl championship","copa de la liga","frauen-bundesliga",
    "serie a femminile","uefa champions league, women","liga acb",
    "germany bbl","wnba preseason","serie a2","del, playoffs",
    "relegation round"
]

CANDS = []

# A. Multi-comp foot Over 1.5 + Hockey + Basket (volume safe)
for foot_o15_mc in [3, 5, 7]:
    for hockey_mc in [2, 3, 5]:
        for basket_mc in [1, 2, 3]:
            for pct in [0.03, 0.05, 0.08]:
                for foot_wr in [0.65, 0.70]:
                    CANDS.append({
                        "id": f"WFR2A_F{foot_o15_mc}H{hockey_mc}B{basket_mc}_pct{int(pct*100)}_wr{foot_wr}",
                        "label": "Foot OU+Hockey+Basket safe",
                        "components": [
                            {"sport": "football", "market": "over_1_5",
                             "cote_min": 1.30, "cote_max": 1.55,
                             "sort_by": "wr", "max_legs": 1, "max_combos": foot_o15_mc,
                             "min_wr": foot_wr, "min_ev": None},
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

# B. Foot xmkt + multi-sport safe
for foot_mkt in ["1x2,btts,over_2_5", "btts,over_2_5"]:
    for foot_mc in [2, 3, 5]:
        for hockey_mc in [2, 3]:
            for pct in [0.03, 0.05]:
                CANDS.append({
                    "id": f"WFR2B_xmkt{foot_mkt.replace(',','+')}_F{foot_mc}H{hockey_mc}_pct{int(pct*100)}",
                    "label": "Foot xmkt + Hockey safe",
                    "components": [
                        {"sport": "football", "market": foot_mkt,
                         "cote_min": 1.40, "cote_max": 1.65,
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": 0.60, "min_ev": None},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": 1.25, "cote_max": 1.50,
                         "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                         "min_wr": 0.65, "min_ev": None},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# C. Mono-strat single-market avec ratio max
for mkt in ["1x2", "over_1_5", "over_2_5", "btts"]:
    for cmin, cmax in [(1.30, 1.55), (1.40, 1.65), (1.50, 1.75)]:
        for mwr in [0.60, 0.65, 0.70]:
            for mc in [2, 3, 5]:
                for pct in [0.03, 0.05, 0.10]:
                    CANDS.append({
                        "id": f"WFR2C_foo_{mkt}_{cmin}-{cmax}_wr{mwr}_mc{mc}_pct{int(pct*100)}",
                        "label": f"Foot {mkt} pure",
                        "components": [{
                            "sport": "football", "market": mkt,
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[WFR2 classics] {len(CANDS)} configs avec filtre Winamax FR strict")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100,
                     excluded_leagues=WINAMAX_FR_EXCLUDED)
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
            "wr": round(sm["wr_combos"]*100, 1),
        })
    except Exception:
        pass

# Filter ratio ≥ 5x + PnL >100€ + DD < 100€
viable = [r for r in results if r["ratio"] >= 5 and r["pnl"] >= 100 and r["dd"] <= 100]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[WFR2] {len(viable)} viables (ratio ≥5×, PnL ≥100€, DD ≤100€) sur {len(results)}")

print(f"\n=== TOP 25 par RATIO Winamax FR strict ===")
for r in viable[:25]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>4.1f} | +{r['pnl']:>4.0f}€ | DD {r['dd']:>4.0f}€ | streak {r['streak']:>2d}j | combos {r['n_combos']:>3d}  | {r['id'][:55]}")

print(f"\n=== TOP 15 par BR multiplier ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:15]:
    print(f"  BR×{r['br_mult']:>4.1f}  ratio {r['ratio']:>5.1f}× | PnL +{r['pnl']:.0f}€ DD {r['dd']:.0f}€ | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_wfr2_classics.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
