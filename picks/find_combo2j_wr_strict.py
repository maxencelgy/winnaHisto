#!/usr/bin/env python3
"""Sweep combos 2j cross-market avec WR strict ≥75% par leg — tenter de battre ratio 24×."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Combo 2j cross-market F+H, leg WR strict
for cmin, cmax in [(1.20, 1.40), (1.20, 1.50), (1.25, 1.45)]:
    for foot_mkt in ["btts,over_1_5,over_2_5", "1x2,btts,over_1_5,over_2_5"]:
        for foot_wr in [0.70, 0.75, 0.80]:
            for hockey_wr in [0.70, 0.75]:
                for mc in [1, 2, 3]:
                    for pct in [0.05, 0.07, 0.10]:
                        CANDS.append({
                            "id": f"C2JS_F{foot_mkt[:3]}-H_{cmin}-{cmax}_fw{foot_wr}_hw{hockey_wr}_mc{mc}_pct{int(pct*100)}",
                            "components": [{
                                "sports": ["football"], "market": foot_mkt,
                                "cote_min": cmin, "cote_max": cmax,
                                "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                                "min_wr": foot_wr, "min_ev": None,
                            }, {
                                "sports": ["ice-hockey"], "market": "1x2",
                                "cote_min": cmin, "cote_max": cmax,
                                "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                                "min_wr": hockey_wr, "min_ev": None,
                            }],
                            "combine_into_combo": True,
                            "max_combos_total": mc,
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                        })

# B. Combo 2j foot pur xmkt cote 1.20-1.40 WR strict (deux différents matches foot)
for cmin, cmax in [(1.20, 1.35), (1.20, 1.40)]:
    for mwr in [0.75, 0.80]:
        for mc in [1, 2, 3]:
            for pct in [0.05, 0.07, 0.10]:
                CANDS.append({
                    "id": f"C2JF_xmkt_{cmin}-{cmax}_wr{mwr}_mc{mc}_pct{int(pct*100)}",
                    "components": [{
                        "sports": ["football"], "market": "btts,over_1_5,over_2_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 2, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

print(f"[C2J WR strict] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 40 == 0: print(f"  [{i}/{len(CANDS)}]")
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

viable = [r for r in results if r["ratio"] >= 18 and r["br_mult"] >= 30]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[C2J WR strict] {len(viable)} viables (ratio ≥18, BR×≥30)")
print(f"\n=== TOP 20 par RATIO ===")
for r in viable[:20]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:60]}")

# Tri secondaire par BR mult
viable.sort(key=lambda r: -r["br_mult"])
print(f"\n=== TOP 10 par BR mult (ratio≥18) ===")
for r in viable[:10]:
    print(f"  BR×{r['br_mult']:>6.1f} ratio {r['ratio']:>5.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ | {r['id'][:60]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/c2j_wr_strict.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved to datasets/c2j_wr_strict.json")
