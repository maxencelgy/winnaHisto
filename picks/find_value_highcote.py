#!/usr/bin/env python3
"""High cote (1.50-2.20) single-shot WR≥65-75% — value plays sur la zone middle-high.
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
                       (["football"],"F"),
                       (["tennis"],"T"),
                       (["basketball"],"B"),
                       (["ice-hockey"],"H")]:
    for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5", "btts", "over_2_5"]:
        for cmin, cmax in [(1.50,1.75), (1.55,1.80), (1.60,1.85), (1.70,1.95),
                            (1.80,2.10), (1.90,2.20)]:
            for mwr in [None, 0.55, 0.60, 0.65, 0.70]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"V_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{mwr}_{sort}",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 1,
                                      "combo_legs_per_palier": 1},
                    })

print(f"[value] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 30:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[value] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL (single shot) ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -r["comp"])
print(f"\n=== TOP 10 par COMPLETION (≥40 cyc) ===")
sub = [r for r in results if r["n_tot"] >= 40 and r["pnl"] > 0]
for r in sub[:10]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_value_highcote.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
