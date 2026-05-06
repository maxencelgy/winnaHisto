#!/usr/bin/env python3
"""MEGA LOTTERY : 6-8 paliers × combo 2 jambes — chercher PnL >30k€.
LOTTERY actuel = 5p combo2 cote 1.50-1.75 → +25233€.
Test : 6p, 7p, 8p sur même range cote.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

SPORTS_LIST = [
    (["football","ice-hockey","tennis","basketball"], "FHTB"),
    (["football","ice-hockey","tennis"], "FHT"),
    (["football","ice-hockey"], "FH"),
]

for sports, sname in SPORTS_LIST:
    for cmin, cmax in [(1.30,1.50), (1.40,1.60), (1.50,1.75), (1.55,1.80), (1.60,1.85)]:
        for mwr in [None, 0.55, 0.60, 0.65]:
            for n_p in [6, 7, 8]:
                for sort in ["wr", "ev"]:
                    for legs in [2, 3]:
                        CANDS.append({
                            "id": f"M_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_legs{legs}_{sort}",
                            "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": legs}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": legs},
                        })

print(f"[mega] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 30 and r["final_pnl"] > 5000:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[mega] {len(results)} viable (PnL>5k€)")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL ===")
print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>7} {'pnl€':>9}  id")
for r in results[:20]:
    print(f"  {r['comp']*100:>5.2f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>6.0f} {r['pnl']:>+8.0f}  {r['id']}")

with open("/tmp/find_mega_lottery.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
