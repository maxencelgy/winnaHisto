#!/usr/bin/env python3
"""Sweep BEAT HYBRID v2 : trouver mieux que META_HYBRID_SAFE_VOLUME (76.7%/116/163€/+2901€).
Score à battre = comp × cap × (n_tot/100) = 14488.
Stratégies :
  R. Refine grid fine autour de 1.20-1.40 cote
  S. legs_per_palier=2 (combo daily) sur la même zone
  T. Markets isolés : over_1_5, over_2_5, btts seul cote 1.20-1.40
  U. Multi-sport extended : F+H+T+B, FH+B, etc
  V. WR plus lâche (0.65-0.70) avec gros volume
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# R. Fine grid around winning zone
SPORTS_FINE = [
    (["football","ice-hockey","tennis"], "FHT"),
    (["football","ice-hockey","tennis","basketball"], "FHTB"),
    (["football","tennis","basketball"], "FTB"),
    (["football","ice-hockey","basketball"], "FHB"),
]
for sports, sname in SPORTS_FINE:
    for cmin, cmax in [(1.15,1.35), (1.18,1.38), (1.20,1.42), (1.22,1.42),
                        (1.18,1.40), (1.20,1.45), (1.15,1.40), (1.22,1.40)]:
        for mwr in [0.65, 0.68, 0.70, 0.72, 0.75]:
            for sort in ["wr", "ev"]:
                for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5"]:
                    CANDS.append({
                        "id": f"R_FINE_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_{sort}",
                        "kind": "R_FINE",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 2,
                                      "combo_legs_per_palier": 1},
                    })

# S. legs_per_palier=2 (combo daily) sur la même zone gagnante
for sports, sname in [(["football","ice-hockey","tennis"],"FHT"), (["football","ice-hockey"],"FH")]:
    for cmin, cmax in [(1.15,1.30), (1.20,1.35), (1.20,1.40)]:
        for mwr in [0.70, 0.72, 0.75, 0.78]:
            for sort in ["wr", "ev"]:
                for n_p in [2, 3]:
                    CANDS.append({
                        "id": f"S_COMBO2_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}",
                        "kind": "S_COMBO2_DAILY",
                        "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 2}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 2},
                    })

# T. Markets isolés
for mkt in ["over_1_5", "over_2_5", "btts"]:
    for sports, sname in [(["football","ice-hockey"],"FH"), (["football"],"F")]:
        for cmin, cmax in [(1.15,1.35), (1.20,1.40), (1.30,1.50), (1.40,1.60)]:
            for mwr in [0.55, 0.60, 0.65, 0.70]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"T_ISO_{mkt[:3]}_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_{sort}",
                        "kind": "T_MKT_ISO",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 2,
                                      "combo_legs_per_palier": 1},
                    })

# V. WR très lâche pour volume max
for sports, sname in [(["football","ice-hockey","tennis","basketball"], "FHTB"),
                       (["football","ice-hockey","tennis"], "FHT")]:
    for cmin, cmax in [(1.20,1.40), (1.25,1.45), (1.20,1.45)]:
        for mwr in [None, 0.55, 0.60, 0.65]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"V_VOL_{sname}_{cmin}-{cmax}_wr{mwr}_{sort}",
                    "kind": "V_LOOSE_VOLUME",
                    "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": 2,
                                  "combo_legs_per_palier": 1},
                })

print(f"[v2_beat] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 30:
            results.append({
                "id": s["id"], "kind": s["kind"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[v2_beat] {len(results)} viable (≥30 cycles)")

# Score = comp × cap × n_tot/100 (HYBRID référence = 14488)
HYBRID_SCORE = 0.767 * 163 * 1.16
print(f"\n=== TOP 20 par SCORE comp×cap×n_tot/100 (HYBRID ref={HYBRID_SCORE:.0f}) ===")
results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"  {'kind':<18} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7} {'score':>6}  id")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    flag = " ★" if score > HYBRID_SCORE else ""
    print(f"  {r['kind']:<18} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f} {score:>5.0f}{flag}  {r['id']}")

# Top par PnL
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 10 par PnL pur ===")
print(f"  {'kind':<18} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:10]:
    print(f"  {r['kind']:<18} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top par volume cycles
results.sort(key=lambda r: -r["n_tot"])
print(f"\n=== TOP 10 par Volume cycles ===")
print(f"  {'kind':<18} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:10]:
    print(f"  {r['kind']:<18} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top par completion
results.sort(key=lambda r: -r["comp"])
print(f"\n=== TOP 10 par Completion (≥50 cyc) ===")
sub = [r for r in results if r["n_tot"] >= 50]
print(f"  {'kind':<18} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in sub[:10]:
    print(f"  {r['kind']:<18} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_hybrid_v2_beat.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved /tmp/find_hybrid_v2_beat.json")
