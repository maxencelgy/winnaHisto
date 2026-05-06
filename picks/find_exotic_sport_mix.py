#!/usr/bin/env python3
"""SPORT MIX EXOTIQUES : combinaisons sports rares (HB, TB, FB+Baseball, etc.).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

EXOTIC_SPORTS = [
    (["ice-hockey", "basketball"], "HB"),
    (["tennis", "basketball"], "TB"),
    (["football", "basketball"], "FB"),
    (["football", "tennis", "basketball"], "FTB"),
    (["football", "baseball"], "FBSB"),
    (["football", "ice-hockey", "baseball"], "FHBSB"),
    (["football", "tennis", "baseball"], "FTBSB"),
    (["football", "ice-hockey", "tennis", "baseball"], "FHTBSB"),
    (["football", "ice-hockey", "tennis", "basketball", "baseball"], "ALL5"),
    (["ice-hockey"], "H"),
    (["basketball"], "B"),
]

for sports, sname in EXOTIC_SPORTS:
    for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5"]:
        for cmin, cmax in [(1.10,1.25), (1.15,1.30), (1.20,1.40), (1.25,1.45), (1.30,1.50)]:
            for mwr in [None, 0.70, 0.75, 0.80]:
                for n_p in [1, 2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"E_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                            "components": [{"sports": sports, "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

print(f"[exotic] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
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

print(f"\n[exotic] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 15 par SCORE ===")
for r in results[:15]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_exotic_sport_mix.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
