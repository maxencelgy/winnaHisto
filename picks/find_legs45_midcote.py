#!/usr/bin/env python3
"""Combos legs=4 et legs=5 mid-cote — extension du legs=3 +15153€ record.
Cote totale par palier explose : legs=4 cote 1.30 → 2.86, legs=5 cote 1.30 → 3.71
"""
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
    for cmin, cmax in [(1.20,1.30), (1.20,1.35), (1.25,1.40), (1.25,1.35), (1.30,1.40)]:
        for mwr in [None, 0.65, 0.70, 0.75]:
            for legs in [4, 5]:
                for n_p in [1, 2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"L{legs}MC_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                            "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": legs}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": legs},
                        })

print(f"[l45_mc] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 25 and r["final_pnl"] > 2000:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[l45_mc] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.2f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>5.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 10 par SCORE ===")
for r in results[:10]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.2f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>5.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_legs45_midcote.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
