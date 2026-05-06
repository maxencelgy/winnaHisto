#!/usr/bin/env python3
"""Sweep BALANCED : trouver configs avec comp ≥25% ET PnL ≥8000€.
Zone optimale = legs 3-4 × paliers 2-3 × cote 1.20-1.40."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

for sports, sname in [(["football","ice-hockey"],"FH"),
                       (["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB"),
                       (["football","ice-hockey","tennis","basketball","baseball"],"ALL5"),
                       (["football"],"F")]:
    for cmin, cmax in [(1.18,1.32), (1.20,1.32), (1.22,1.36), (1.20,1.35),
                        (1.22,1.38), (1.25,1.38), (1.20,1.30), (1.25,1.35)]:
        for mwr in [0.55, 0.60, 0.65, 0.70, 0.75]:
            for legs in [3, 4]:
                for n_p in [2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"BAL_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_l{legs}_p{n_p}_{sort}",
                            "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": legs}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": legs},
                        })

print(f"[bal] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 30 and r["completion_rate"] >= 0.20 and r["final_pnl"] >= 5000:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[bal] {len(results)} viable BALANCED (comp≥20% + PnL≥5k)")
results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 20 par SCORE ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top by PnL
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 10 par PnL ===")
for r in results[:10]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_best_balanced.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
