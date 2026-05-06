#!/usr/bin/env python3
"""CROSS-VALIDATION : pick valide UNIQUEMENT si un autre marché sur même match a WR élevé.
Ex: prendre Over 2.5 cote 1.40 seulement si BTTS Yes sur même match a WR≥75%.
Engine supporte via validation_market + validation_min_wr."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# Combinations principales
VALIDATIONS = [
    ("over_2_5", "btts", 0.65),  # Over 2.5 + valide sur BTTS Yes
    ("over_2_5", "btts", 0.70),
    ("btts", "over_2_5", 0.65),  # BTTS + valide sur Over 2.5
    ("btts", "over_2_5", 0.70),
    ("over_1_5", "btts", 0.65),
    ("over_1_5", "over_2_5", 0.55),
    ("1x2", "over_1_5", 0.70),
    ("1x2", "over_2_5", 0.55),
    ("1x2", "btts", 0.55),
]

for sports, sname in [(["football"],"F"), (["football","ice-hockey"],"FH")]:
    for main_mkt, val_mkt, val_wr in VALIDATIONS:
        for cmin, cmax in [(1.30,1.50), (1.40,1.60), (1.50,1.80), (1.60,2.00)]:
            for mwr in [None, 0.55, 0.60, 0.65]:
                for n_p in [2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"CV_{sname}_{main_mkt[:3]}_v{val_mkt[:3]}_{int(val_wr*100)}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                            "components": [{"sports": sports, "market": main_mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1,
                                            "validation_market": val_mkt,
                                            "validation_min_wr": val_wr}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

print(f"[cv] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 20 and r["final_pnl"] > 1500:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[cv] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 10 par SCORE ===")
for r in results[:10]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_cross_validation.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
