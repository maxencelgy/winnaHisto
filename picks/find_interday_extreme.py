#!/usr/bin/env python3
"""INTERDAY MEGA : combos legs=2-4 × paliers 8-10 — pousser au-delà de +88k€."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

for sports, sname in [(["football","ice-hockey"],"FH"),
                       (["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB"),
                       (["football"],"F")]:
    for cmin, cmax in [(1.20,1.35), (1.25,1.40), (1.30,1.45)]:
        for mwr in [0.60, 0.65, 0.70]:
            for legs in [2, 3, 4]:
                for n_p in [8, 10, 12]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"IX_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_l{legs}_p{n_p}_{sort}",
                            "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": legs}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": legs},
                        })

print(f"[ix] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="interday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 5 and r["final_pnl"] > 5000:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[ix] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 15 par PnL ===")
for r in results[:15]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.2f}% {r['n_comp']:>3}/{r['n_tot']:<3} cap{r['cap']:>6.0f} {r['pnl']:>+7.0f}  {r['id']}")

with open("/tmp/find_interday_extreme.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
