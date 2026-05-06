#!/usr/bin/env python3
"""COMBOS 5+ JAMBES sur 1 palier — cote totale énorme single-shot.
Cible : trouver un combo 5j daily à 65%+ comp.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

for sports, sname in [(["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB"),
                       (["football","ice-hockey"],"FH")]:
    for cmin, cmax in [(1.05,1.10), (1.08,1.15), (1.10,1.18), (1.05,1.15), (1.08,1.18)]:
        for mwr in [0.85, 0.88, 0.90, 0.92]:
            for legs in [5, 6, 7]:
                for sort in ["wr", "ev"]:
                    for n_p in [1, 2]:
                        CANDS.append({
                            "id": f"L5_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_legs{legs}_p{n_p}_{sort}",
                            "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": legs}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": legs},
                        })

print(f"[5plus] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 20:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[5plus] {len(results)} viable")
results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 15 par SCORE ===")
for r in results[:15]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f}  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 10 par PnL ===")
for r in results[:10]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_5plus_legs.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
