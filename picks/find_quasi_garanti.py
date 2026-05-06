#!/usr/bin/env python3
"""WR ultra-strict 90-95% sur micro-cote 1.03-1.10 — quasi-garanti single shot daily."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# Single shot ultra-safe
for sports, sname in [(["football","ice-hockey"],"FH"),
                       (["football","ice-hockey","tennis"],"FHT"),
                       (["football","ice-hockey","tennis","basketball"],"FHTB"),
                       (["football"],"F"),
                       (["football","tennis"],"FT")]:
    for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5"]:
        for cmin, cmax in [(1.02,1.06), (1.03,1.07), (1.03,1.08), (1.05,1.10), (1.05,1.08)]:
            for mwr in [0.90, 0.92, 0.94, 0.95, 0.97]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"QG_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_{sort}",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 1,
                                      "combo_legs_per_palier": 1},
                    })
                    # Aussi 2 paliers
                    CANDS.append({
                        "id": f"QG_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_{sort}_p2",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 2,
                                      "combo_legs_per_palier": 1},
                    })

print(f"[qg] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 20 and r["completion_rate"] >= 0.85:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[qg] {len(results)} viable QUASI-GARANTI (≥85% comp + ≥20 cyc)")
results.sort(key=lambda r: -r["comp"])
print(f"\n=== TOP 20 par COMPLETION ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["n_tot"]))
print(f"\n=== TOP 10 par VOLUME × COMP ===")
for r in results[:10]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_quasi_garanti.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
