#!/usr/bin/env python3
"""Sweep multi-comp avec combos 2j en composante — pousser ratio."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Foot xmkt avec cote variations + multi-sport combo
for foot_cote in [(1.20, 1.35), (1.20, 1.40), (1.25, 1.45)]:
    for foot_mc in [3, 5, 7]:
        for hockey_mc in [3, 5]:
            for include_basket in [False, True]:
                for pct in [0.05, 0.07, 0.10]:
                    for foot_mkt in ["over_1_5,over_2_5", "btts,over_1_5,over_2_5", "1x2,over_1_5,over_2_5"]:
                        comps = [{
                            "sport": "football", "market": foot_mkt,
                            "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                            "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                            "min_wr": None, "min_ev": None,
                        }, {
                            "sport": "ice-hockey", "market": "1x2",
                            "cote_min": 1.20, "cote_max": 1.50,
                            "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                            "min_wr": 0.65, "min_ev": None,
                        }]
                        if include_basket:
                            comps.append({
                                "sport": "basketball", "market": "1x2",
                                "cote_min": 1.20, "cote_max": 1.50,
                                "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                                "min_wr": 0.65, "min_ev": None,
                            })
                        CANDS.append({
                            "id": f"MMC_{foot_mkt.replace(',','+')}_{foot_cote[0]}-{foot_cote[1]}_F{foot_mc}H{hockey_mc}{'B2' if include_basket else 'B0'}_pct{int(pct*100)}",
                            "components": comps,
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                        })

print(f"[Multi-mkt combos] {len(CANDS)} configs")

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

# Best ratio + bonne BR mult
viable = [r for r in results if r["ratio"] >= 10 and r["br_mult"] >= 15]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Multi-mkt] {len(viable)} viables (ratio ≥10, BR ≥15)")

print(f"\n=== TOP 25 par RATIO ===")
for r in viable[:25]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>4d} | {r['id'][:55]}")

print(f"\n=== TOP 15 par BR mult (ratio ≥10) ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:15]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_multimkt.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
