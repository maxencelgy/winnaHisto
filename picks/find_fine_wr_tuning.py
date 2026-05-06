#!/usr/bin/env python3
"""TUNING FIN du WR threshold sur les meilleures configs récentes.
Test toutes les valeurs WR de 0.55 à 0.90 par pas de 0.01 sur les configs gagnantes.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# Base configs : les patterns les plus prometteurs
BASE_CONFIGS = [
    # FH 1x2 mid-cote 2P (HYBRID winner family)
    {"sports": ["football","ice-hockey"], "market": "1x2", "cmin": 1.20, "cmax": 1.40, "n_p": 2, "name": "FH_1x2_2P"},
    {"sports": ["football","ice-hockey","tennis"], "market": "1x2", "cmin": 1.20, "cmax": 1.40, "n_p": 2, "name": "FHT_1x2_2P"},
    {"sports": ["football","ice-hockey","basketball"], "market": "1x2", "cmin": 1.15, "cmax": 1.35, "n_p": 2, "name": "FHB_1x2_2P"},
    # FH single high-cote
    {"sports": ["football","ice-hockey"], "market": "1x2", "cmin": 1.70, "cmax": 1.95, "n_p": 1, "name": "FH_1x2_HIGH_1S"},
    # 5 sports 2P
    {"sports": ["football","ice-hockey","tennis","basketball","baseball"], "market": "1x2", "cmin": 1.25, "cmax": 1.45, "n_p": 2, "name": "ALL5_2P"},
    # FH OU 2.5 single
    {"sports": ["football","ice-hockey"], "market": "over_2_5", "cmin": 1.80, "cmax": 2.10, "n_p": 1, "name": "FH_OU25_1S"},
    # Combo 2j 2P
    {"sports": ["football","ice-hockey","tennis"], "market": "1x2,btts,over_1_5,over_2_5", "cmin": 1.20, "cmax": 1.40, "n_p": 2, "name": "FHT_xmkt_combo2_2P", "legs": 2},
    # Combo 2j 3P
    {"sports": ["football","ice-hockey","tennis"], "market": "1x2,btts,over_1_5,over_2_5", "cmin": 1.20, "cmax": 1.40, "n_p": 3, "name": "FHT_xmkt_combo2_3P", "legs": 2},
]

# WR threshold à tester
WR_VALS = [round(x*0.01,2) for x in range(55, 91)]  # 0.55 à 0.90

for cfg in BASE_CONFIGS:
    legs = cfg.get("legs", 1)
    for mwr in WR_VALS:
        for sort in ["wr", "ev"]:
            CANDS.append({
                "id": f"FT_{cfg['name']}_wr{int(mwr*100)}_{sort}",
                "components": [{"sports": cfg["sports"], "market": cfg["market"],
                                "cote_min": cfg["cmin"], "cote_max": cfg["cmax"],
                                "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                "min_wr": mwr, "min_ev": None,
                                "legs_per_palier": legs}],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": cfg["n_p"],
                              "combo_legs_per_palier": legs},
            })

print(f"[fine_wr] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
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

print(f"\n[fine_wr] {len(results)} viable")

# Group by base config name → trouve le meilleur WR par config
import re
by_name = {}
for r in results:
    m = re.match(r"FT_(.+)_wr\d+_\w+", r["id"])
    if m:
        name = m.group(1)
        by_name.setdefault(name, []).append(r)

print(f"\n=== BEST WR par config ===")
for name, group in by_name.items():
    group.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
    print(f"\n  --- {name} ---")
    for r in group[:3]:
        score = r["comp"] * r["cap"] * r["n_tot"]/100
        print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top global by score
results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 15 GLOBAL par SCORE ===")
for r in results[:15]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_fine_wr_tuning.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
