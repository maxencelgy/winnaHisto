#!/usr/bin/env python3
"""BTTS isolé sweep ULTRA-FIN : toutes cotes, toutes ligues, tous WR.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# BTTS toute cote, multi-paliers
for cmin, cmax in [(1.40,1.55), (1.50,1.70), (1.55,1.75), (1.60,1.80),
                    (1.65,1.85), (1.70,1.90), (1.80,2.00), (1.85,2.10)]:
    for mwr in [None, 0.50, 0.55, 0.60, 0.65, 0.70]:
        for n_p in [1, 2, 3]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"B_btts_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                    "components": [{"sports": ["football"], "market": "btts",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# Over 1.5 isolé
for cmin, cmax in [(1.10,1.20), (1.15,1.25), (1.18,1.30), (1.22,1.35), (1.30,1.45)]:
    for mwr in [None, 0.70, 0.75, 0.80, 0.85]:
        for n_p in [1, 2, 3, 4]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"B_o15_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                    "components": [{"sports": ["football"], "market": "over_1_5",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

print(f"[btts_o15] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 30 and r["final_pnl"] > 500:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[btts_o15] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 10 par SCORE ===")
for r in results[:10]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_btts_strict.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
