#!/usr/bin/env python3
"""Sweep HYBRID : trouver le sweet spot entre
  - MIDCOTE_FH_2P_RECORD (FH 1.40-1.55 WR≥60% → 63.7%/91/cap215€/+3388€ — gros gain+volume)
  - 2P_92PCT_QUASI_GARANTI (FT 1.03-1.08 WR≥88% → 92%/25/cap113€/+92€ — safe ultime)
Objectif : comp ≥ 75% ET cap ≥ 140€ ET cycles ≥ 50 ET PnL > 1500€
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# Grille fine entre les 2 extrêmes
SPORTS_LIST = [
    (["football", "ice-hockey"], "FH"),
    (["football", "tennis"], "FT"),
    (["football", "ice-hockey", "tennis"], "FHT"),
    (["football"], "F"),
]
MARKETS = ["1x2", "1x2,btts,over_1_5,over_2_5"]
COTE_RANGES = [
    (1.08, 1.18),  # ultra-safe boost
    (1.10, 1.20),
    (1.10, 1.25),
    (1.12, 1.25),
    (1.15, 1.30),
    (1.18, 1.32),
    (1.20, 1.35),
    (1.20, 1.40),
    (1.25, 1.40),
    (1.25, 1.45),
    (1.30, 1.45),
    (1.30, 1.50),
]
MIN_WR = [0.72, 0.75, 0.78, 0.80, 0.82, 0.85, 0.88]
SORTS = ["wr", "ev"]

for sports, sname in SPORTS_LIST:
    for mkt in MARKETS:
        for cmin, cmax in COTE_RANGES:
            for mwr in MIN_WR:
                for sort in SORTS:
                    CANDS.append({
                        "id": f"H_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{int(mwr*100)}_{sort}",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": 2,
                                      "combo_legs_per_palier": 1},
                    })

print(f"[hybrid] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 30:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"],
                "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"],
                "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[hybrid] {len(results)} viable (≥30 cycles)")

# Filter for hybrid sweet spot: comp ≥ 0.75 AND cap ≥ 140€
hybrids = [r for r in results if r["comp"] >= 0.75 and r["cap"] >= 140 and r["n_tot"] >= 40]
hybrids.sort(key=lambda r: -(r["comp"] * r["cap"] * (r["n_tot"]/100)))

print(f"\n=== HYBRID SWEET SPOT (comp≥75% + cap≥140€ + ≥40 cycles) ===")
print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  {'score':>6}  id")
for r in hybrids[:15]:
    score = r["comp"] * r["cap"] * (r["n_tot"]/100)
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {score:>5.0f}  {r['id']}")

# Top par PnL pur (au cas où)
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 10 par PnL pur ===")
print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:10]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_hybrid_safe_volume.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved /tmp/find_hybrid_safe_volume.json")
