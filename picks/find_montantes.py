#!/usr/bin/env python3
"""Sweep large : trouver les meilleures montantes par sport, cote, paliers."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

START = "2026-01-01"
END = "2026-04-30"
INITIAL = 10

# Configurations à tester
COTE_RANGES = [
    (1.10, 1.30),
    (1.15, 1.35),
    (1.20, 1.40),
    (1.25, 1.45),
    (1.30, 1.50),
    (1.30, 1.55),
    (1.40, 1.60),
    (1.50, 1.75),
]
SPORT_CONFIGS = [
    (["football"], "Foot"),
    (["basketball"], "Basket"),
    (["ice-hockey"], "Hockey"),
    (["baseball"], "Baseball"),
    (["tennis"], "Tennis"),
    (["football","ice-hockey"], "F+H"),
    (["football","basketball"], "F+B"),
    (["ice-hockey","basketball"], "H+B"),
    (["football","ice-hockey","basketball"], "FHB"),
    (["football","ice-hockey","basketball","baseball"], "4sports"),
    (["football","ice-hockey","basketball","baseball","tennis"], "5sports"),
]
N_PALIERS = [3, 4, 5, 6]
MODES = ["interday", "intraday"]

def make_strat(sports, cmin, cmax, n_paliers):
    return {
        "id": "test", "label": "test",
        "components": [{
            "sports": sports, "market": "1x2",
            "cote_min": cmin, "cote_max": cmax,
            "sort_by": "wr", "max_legs": 1, "max_combos": 1,
            "min_wr": None, "min_ev": None,
        }],
        "montante": {"n_paliers_target": n_paliers, "initial_stake": INITIAL},
    }

results = []
total = len(COTE_RANGES) * len(SPORT_CONFIGS) * len(N_PALIERS) * len(MODES)
print(f"[montante sweep] {total} configs à tester sur S1-26\n")

i = 0
for sports, sport_name in SPORT_CONFIGS:
    for cmin, cmax in COTE_RANGES:
        for n_p in N_PALIERS:
            for mode in MODES:
                i += 1
                if i % 50 == 0:
                    print(f"  [{i}/{total}] {sport_name} {cmin}-{cmax} {n_p}p {mode}")
                strat = make_strat(sports, cmin, cmax, n_p)
                try:
                    r = simulate(strat, START, END, mode=mode, initial_stake=INITIAL)
                    r["sport_name"] = sport_name
                    r["cmin"] = cmin
                    r["cmax"] = cmax
                    r["n_paliers"] = n_p
                    r["mode"] = mode
                    results.append(r)
                except Exception as e:
                    pass

# Filtrer : au moins 5 cycles complets pour être considéré
viable = [r for r in results if r["n_cycles_complete"] >= 5]

# Tri par ROI
viable.sort(key=lambda r: -r["roi"])

print(f"\n=== Top 30 montantes par ROI (cycles complets ≥ 5) ===\n")
print(f"{'Sport':9s} {'Cote':10s} {'N_p':>3s} {'Mode':9s} {'Cycles ✓':>9s} {'%':>4s} {'WR_p':>5s} {'AvgFin':>7s} {'ROI':>6s}")
print("-"*82)
for r in viable[:30]:
    flag = "🌟" if r["roi"] >= 50 else "★" if r["roi"] >= 20 else "✓"
    print(f"{flag} {r['sport_name']:7s} {r['cmin']:.2f}-{r['cmax']:.2f} {r['n_paliers']:>3d} {r['mode']:9s} "
          f"{r['n_cycles_complete']:>2d}/{r['n_cycles_total']:<3d} {r['completion_rate']*100:>3.0f}% "
          f"{r['wr_palier']*100:>4.0f}% {r['avg_capital_complete']:>5.0f}€ {r['roi']:>+5.0f}%")

# Tri par nombre de cycles complets
viable_by_cycles = sorted(viable, key=lambda r: -r["n_cycles_complete"])
print(f"\n=== Top 15 par NB CYCLES COMPLETS (peu importe ROI) ===\n")
for r in viable_by_cycles[:15]:
    print(f"  {r['sport_name']:7s} {r['cmin']:.2f}-{r['cmax']:.2f} {r['n_paliers']}p {r['mode']:9s} "
          f"{r['n_cycles_complete']:>2d}/{r['n_cycles_total']} ({r['completion_rate']*100:.0f}%) ROI {r['roi']:+.0f}%")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/montantes_sweep.json","w") as f:
    json.dump({"all": results, "viable": viable}, f, indent=2)
print(f"\n[montante sweep] Saved datasets/montantes_sweep.json")
