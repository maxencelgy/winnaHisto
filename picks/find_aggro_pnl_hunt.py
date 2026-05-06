#!/usr/bin/env python3
"""Sweep AGGRO PnL HUNT — chercher des PnL ABSOLU énormes même avec compl basse.
Cibles : haut paliers, haut cote, multi-sports max.
Score : juste le PnL S1-26.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# 4-paliers avec cotes mid-high
for sports, sname in [(["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB"),
                       (["football","ice-hockey"],"FH")]:
    for cmin, cmax in [(1.30,1.50), (1.35,1.55), (1.40,1.60), (1.45,1.65),
                        (1.50,1.75), (1.55,1.80)]:
        for mwr in [None, 0.55, 0.60, 0.65, 0.70]:
            for n_p in [3, 4, 5]:
                for sort in ["ev", "wr"]:
                    for legs in [1, 2]:
                        CANDS.append({
                            "id": f"A_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_legs{legs}_{sort}",
                            "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": legs}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": legs},
                        })

print(f"[aggro] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 25 and r["final_pnl"] > 1000:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[aggro] {len(results)} viable (≥25 cyc + PnL>1000)")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 30 par PnL ===")
print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:30]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_aggro_pnl_hunt.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
