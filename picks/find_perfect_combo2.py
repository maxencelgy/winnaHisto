#!/usr/bin/env python3
"""Combos legs=2 sur zone PERFECT (WR≥95%) — chercher 100% comp avec cap plus élevé.
Cote totale combo 2j = ~1.10-1.20 par palier."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

for sports, sname in [(["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB"),
                       (["football","ice-hockey","tennis","basketball","baseball"],"ALL5"),
                       (["football","tennis"],"FT"),
                       (["football","ice-hockey"],"FH")]:
    for cmin, cmax in [(1.03,1.07), (1.03,1.08), (1.04,1.08), (1.05,1.10)]:
        for mwr in [0.92, 0.94, 0.95, 0.96, 0.97]:
            for n_p in [1, 2]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"PC2_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                        "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 2}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 2},
                    })

# Plus 1x2 only
for sports, sname in [(["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB")]:
    for cmin, cmax in [(1.03,1.07), (1.05,1.10)]:
        for mwr in [0.94, 0.95, 0.96]:
            for n_p in [1, 2]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"PC2_{sname}_1x2_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                        "components": [{"sports": sports, "market": "1x2",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 2}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 2},
                    })

print(f"[pc2] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 10 and r["completion_rate"] >= 0.85:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[pc2] {len(results)} viable (≥85% comp + ≥10 cyc)")
results.sort(key=lambda r: (-r["comp"], -r["n_tot"]))
print(f"\n=== TOP 20 par COMP+VOL ===")
for r in results[:20]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# 100% only
perf = [r for r in results if r["comp"] >= 1.0]
print(f"\n=== 100% PERFECT COMBO2 (n={len(perf)}) ===")
for r in sorted(perf, key=lambda x: -x["n_tot"])[:15]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_perfect_combo2.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
