#!/usr/bin/env python3
"""Sweep COMBOS 3 LEGS par palier — angle jamais testé.
Cible : trouver des montantes avec 3 picks combinés par palier (cote totale ~1.7-2.5 par palier).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

SPORTS_LIST = [
    (["football", "ice-hockey", "tennis"], "FHT"),
    (["football", "ice-hockey"], "FH"),
    (["football", "ice-hockey", "tennis", "basketball"], "FHTB"),
    (["football"], "F"),
]

# Combo 3 jambes — cote individuelle plus basse car combinée
for sports, sname in SPORTS_LIST:
    for cmin, cmax in [(1.05,1.15), (1.08,1.18), (1.10,1.20), (1.12,1.25), (1.15,1.30)]:
        for mwr in [0.78, 0.82, 0.85, 0.88]:
            for n_p in [1, 2, 3]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"C3_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                        "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 3}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 3},
                    })

# Combo 4 jambes pour cote ultra-basse
for sports, sname in [(["football","ice-hockey","tennis"],"FHT"), (["football","ice-hockey"],"FH")]:
    for cmin, cmax in [(1.05,1.12), (1.08,1.15), (1.10,1.18)]:
        for mwr in [0.85, 0.88, 0.90]:
            for n_p in [1, 2]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"C4_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                        "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 4}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 4},
                    })

print(f"[c3legs] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
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

print(f"\n[c3legs] {len(results)} viable")

results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL ===")
print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:20]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 10 par SCORE ===")
for r in results[:10]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f}  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_combos_3legs.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
