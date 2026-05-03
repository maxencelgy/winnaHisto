#!/usr/bin/env python3
"""Sweep combo 3j multi-sport — angle moins testé en classique WFR."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Combo 3j multi-sport cote totale modérée
for cote_t in [(2.0, 3.5), (2.5, 4.0), (3.0, 5.0), (2.5, 5.0)]:
    for sports in [["football", "ice-hockey"],
                   ["football", "ice-hockey", "basketball"],
                   ["football", "ice-hockey", "basketball", "tennis"]]:
        for mc in [1, 2, 3]:
            for pct in [0.03, 0.05, 0.07, 0.10]:
                for mwr in [0.55, 0.60, 0.65]:
                    CANDS.append({
                        "id": f"C3J_{'+'.join(s[:3] for s in sports)}_{cote_t[0]}-{cote_t[1]}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                        "components": [{
                            "sports": sports, "market": "1x2",
                            "cote_min": cote_t[0], "cote_max": cote_t[1],
                            "sort_by": "wr", "max_legs": 3, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

# B. Combo 4j ultra-safe multi-sport
for cote_t in [(2.0, 3.5), (3.0, 5.0)]:
    for sports in [["football", "ice-hockey", "basketball"],
                   ["football", "ice-hockey", "basketball", "tennis"]]:
        for mc in [1, 2]:
            for pct in [0.03, 0.05, 0.07]:
                for mwr in [0.65, 0.70]:
                    CANDS.append({
                        "id": f"C4J_{'+'.join(s[:3] for s in sports)}_{cote_t[0]}-{cote_t[1]}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                        "components": [{
                            "sports": sports, "market": "1x2",
                            "cote_min": cote_t[0], "cote_max": cote_t[1],
                            "sort_by": "wr", "max_legs": 4, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[Combo 3j/4j multi-sport] {len(CANDS)} configs")

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

viable = [r for r in results if r["ratio"] >= 5 and r["br_mult"] >= 5]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Combo3j/4j] {len(viable)} viables (ratio ≥5, BR ≥5)")

print(f"\n=== TOP 20 par RATIO ===")
for r in viable[:20]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>4d} | {r['id'][:60]}")

print(f"\n=== TOP 10 par BR mult ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:10]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_combo3j.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
