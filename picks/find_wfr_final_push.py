#!/usr/bin/env python3
"""Sweep MEGA final push — angles non testés en WFR strict."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Cote variations fines BTTS+OU
for cmin in [1.18, 1.20, 1.22, 1.25]:
    for cmax in [1.32, 1.35, 1.38, 1.40, 1.42]:
        if cmax <= cmin: continue
        for foot_mc in [3, 5]:
            for hockey_mc in [3, 5]:
                for pct in [0.05, 0.07, 0.10]:
                    CANDS.append({
                        "id": f"FP_BTTSO_F{foot_mc}H{hockey_mc}_{cmin}-{cmax}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "football", "market": "btts,over_1_5,over_2_5",
                             "cote_min": cmin, "cote_max": cmax,
                             "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                             "min_wr": None, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.50,
                             "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                             "min_wr": 0.65, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

# B. Combo 2j foot xmkt + Hockey single
for foot_cote in [(1.20, 1.40), (1.20, 1.35), (1.25, 1.45)]:
    for foot_mc in [1, 2, 3]:
        for hockey_mc in [3, 5]:
            for pct in [0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"FP_C2j_xmkt_{foot_cote[0]}-{foot_cote[1]}_F{foot_mc}H{hockey_mc}_pct{int(pct*100)}",
                    "components": [
                        {"sport": "football", "market": "btts,over_1_5,over_2_5",
                         "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                         "sort_by": "wr", "max_legs": 2, "max_combos": foot_mc,
                         "min_wr": None, "min_ev": None,
                         "label": "Foot xmkt combo 2j"},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.50,
                         "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                         "min_wr": 0.65, "min_ev": None,
                         "label": "Hockey safe"},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# C. Multi-comp 4 sports (incl baseball MLB)
for foot_mc in [3, 5]:
    for hockey_mc in [2, 3]:
        for basket_mc in [1, 2]:
            for baseball_mc in [1, 2, 3]:
                for pct in [0.05, 0.07]:
                    CANDS.append({
                        "id": f"FP_4S_F{foot_mc}H{hockey_mc}B{basket_mc}MLB{baseball_mc}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "football", "market": "btts,over_1_5,over_2_5",
                             "cote_min": 1.20, "cote_max": 1.40,
                             "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                             "min_wr": None, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.50,
                             "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                             "min_wr": 0.65, "min_ev": None},
                            {"sport": "basketball", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.50,
                             "sort_by": "wr", "max_legs": 1, "max_combos": basket_mc,
                             "min_wr": 0.65, "min_ev": None},
                            {"sport": "baseball", "market": "1x2",
                             "cote_min": 1.30, "cote_max": 1.70,
                             "sort_by": "wr", "max_legs": 1, "max_combos": baseball_mc,
                             "min_wr": 0.55, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

# D. Single foot xmkt nb picks aggressif (10-15 picks/jour)
for cote_range in [(1.20, 1.35), (1.20, 1.40), (1.25, 1.40)]:
    for foot_mc in [10, 12, 15, 20]:
        for pct in [0.02, 0.03, 0.05]:
            CANDS.append({
                "id": f"FP_VOL_xmkt_{cote_range[0]}-{cote_range[1]}_F{foot_mc}_pct{int(pct*100)}",
                "components": [{
                    "sport": "football", "market": "btts,over_1_5,over_2_5",
                    "cote_min": cote_range[0], "cote_max": cote_range[1],
                    "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                    "min_wr": None, "min_ev": None,
                }],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
            })

print(f"[Final push] {len(CANDS)} configs")

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

# Filter best — ratio ≥10 + BR ≥10 (cherche les vrais gros)
viable = [r for r in results if r["ratio"] >= 10 and r["br_mult"] >= 10]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Final push] {len(viable)} viables (ratio ≥10, BR ≥10)")

print(f"\n=== TOP 25 par RATIO ===")
for r in viable[:25]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>4d} | {r['id'][:55]}")

print(f"\n=== TOP 15 par BR mult ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:15]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_final_push.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
