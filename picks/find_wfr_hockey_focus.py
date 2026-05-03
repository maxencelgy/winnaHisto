#!/usr/bin/env python3
"""Sweep Hockey focus — variations fines cote, mc, pct sur Hockey + multi-comp."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Hockey solo + sizing aggro
for cmin, cmax in [(1.20, 1.40), (1.20, 1.45), (1.25, 1.45), (1.25, 1.50), (1.30, 1.50)]:
    for mc in [3, 5, 7, 10]:
        for mwr in [0.60, 0.65, 0.70]:
            for pct in [0.05, 0.07, 0.10, 0.12]:
                CANDS.append({
                    "id": f"HK_{cmin}-{cmax}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                    "components": [{
                        "sport": "ice-hockey", "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

# B. Hockey + Foot OU multi-comp variations cote
for hk_cote in [(1.20, 1.40), (1.25, 1.45), (1.30, 1.50)]:
    for foot_cote in [(1.30, 1.55), (1.35, 1.55), (1.40, 1.60)]:
        for hk_mc in [3, 5]:
            for foot_mc in [3, 5]:
                for pct in [0.05, 0.07]:
                    CANDS.append({
                        "id": f"HF_HK{hk_cote[0]}-{hk_cote[1]}_F{foot_cote[0]}-{foot_cote[1]}_H{hk_mc}F{foot_mc}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": hk_cote[0], "cote_max": hk_cote[1],
                             "sort_by": "wr", "max_legs": 1, "max_combos": hk_mc,
                             "min_wr": 0.65, "min_ev": None},
                            {"sport": "football", "market": "over_1_5",
                             "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                             "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                             "min_wr": 0.65, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[Hockey focus] {len(CANDS)} configs")

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

viable = [r for r in results if r["ratio"] >= 8 and r["br_mult"] >= 5]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Hockey focus] {len(viable)} viables (ratio ≥8, BR ≥5)")

print(f"\n=== TOP 20 par RATIO ===")
for r in viable[:20]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>4d} | {r['id'][:55]}")

print(f"\n=== TOP 10 par BR mult ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:10]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_hockey_focus.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
