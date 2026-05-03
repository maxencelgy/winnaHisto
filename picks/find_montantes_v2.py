#!/usr/bin/env python3
"""Sweep MASSIF montantes : toutes combinaisons sport × cote × paliers × legs/palier."""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

START="2026-01-01"; END="2026-04-30"; INITIAL=10

# Combinaisons sport
ALL_SPORTS = ["football", "basketball", "ice-hockey", "tennis", "baseball"]
SPORT_COMBOS = []
# 1 sport
for s in ALL_SPORTS: SPORT_COMBOS.append(([s], s[:4].upper()))
# 2 sports
for combo in itertools.combinations(ALL_SPORTS, 2):
    SPORT_COMBOS.append((list(combo), "+".join(c[:3] for c in combo)))
# 3 sports
for combo in itertools.combinations(ALL_SPORTS, 3):
    SPORT_COMBOS.append((list(combo), "+".join(c[:3] for c in combo)))
# 4 sports
for combo in itertools.combinations(ALL_SPORTS, 4):
    SPORT_COMBOS.append((list(combo), "4sports_no_"+([s for s in ALL_SPORTS if s not in combo][0])[:3]))
# 5 sports
SPORT_COMBOS.append((ALL_SPORTS, "5sports"))

COTE_RANGES = [(1.10, 1.25), (1.20, 1.40), (1.30, 1.55)]
LEGS_PER_PALIER = [1, 2, 3]
N_PALIERS = [3, 5, 7]
MODES = ["intraday"]  # interday est moins efficace en montante combo

def make_strat(sports, cmin, cmax, legs_per_palier, n_paliers):
    return {"id":"t","label":"t","components":[{
        "sports":sports, "market":"1x2",
        "cote_min":cmin, "cote_max":cmax,
        "sort_by":"wr", "max_legs":legs_per_palier,
        "max_combos":1, "min_wr":None, "min_ev":None,
        "legs_per_palier":legs_per_palier,
    }],"montante":{"initial_stake":INITIAL, "n_paliers_target":n_paliers,
                    "combo_legs_per_palier":legs_per_palier}}

results = []
total = len(SPORT_COMBOS) * len(COTE_RANGES) * len(LEGS_PER_PALIER) * len(N_PALIERS) * len(MODES)
print(f"[montante v2 sweep] {total} configs à tester")

i = 0
for sports, sname in SPORT_COMBOS:
    for cmin, cmax in COTE_RANGES:
        for legs in LEGS_PER_PALIER:
            for n_p in N_PALIERS:
                for mode in MODES:
                    i += 1
                    if i % 100 == 0:
                        print(f"  [{i}/{total}]")
                    s = make_strat(sports, cmin, cmax, legs, n_p)
                    try:
                        r = simulate(s, START, END, mode=mode, initial_stake=INITIAL)
                        r.update({"sname":sname, "cmin":cmin, "cmax":cmax,
                                  "legs":legs, "n_p":n_p, "mode":mode})
                        results.append(r)
                    except Exception as e:
                        pass

# Filter viables
viable = [r for r in results if r["n_cycles_complete"] >= 3]

print(f"\n=== TOP 20 par ROI (cycles ≥ 3) ===\n")
viable.sort(key=lambda r: -r["roi"])
print(f"{'Sport':17s} {'Cote':10s} {'Legs':>4s} {'Pal':>3s} {'Mode':>9s} {'Cycles':>9s} {'%':>4s} {'WR_p':>5s} {'AvgFin':>7s} {'ROI':>6s}")
print("-"*92)
for r in viable[:20]:
    flag = "🌟" if r["roi"] >= 80 else "★"
    print(f"{flag} {r['sname']:15s} {r['cmin']:.2f}-{r['cmax']:.2f} {r['legs']:>4d} {r['n_p']:>3d} {r['mode']:>9s} "
          f"{r['n_cycles_complete']:>2d}/{r['n_cycles_total']:<3d} {r['completion_rate']*100:>3.0f}% "
          f"{r['wr_palier']*100:>4.0f}% {r['avg_capital_complete']:>5.0f}€ {r['roi']:>+4.0f}%")

print(f"\n=== TOP 15 par CAPITAL final moyen (cycles ≥ 3) ===\n")
viable.sort(key=lambda r: -r["avg_capital_complete"])
for r in viable[:15]:
    print(f"  {r['sname']:15s} {r['cmin']:.2f}-{r['cmax']:.2f} legs={r['legs']} ×{r['n_p']}p {r['mode']} | "
          f"capital {r['avg_capital_complete']:.0f}€  ROI {r['roi']:+.0f}%  cycles {r['n_cycles_complete']}/{r['n_cycles_total']}")

print(f"\n=== TOP 15 par NB CYCLES COMPLETS ===\n")
viable.sort(key=lambda r: -r["n_cycles_complete"])
for r in viable[:15]:
    print(f"  {r['sname']:15s} {r['cmin']:.2f}-{r['cmax']:.2f} legs={r['legs']} ×{r['n_p']}p {r['mode']} | "
          f"{r['n_cycles_complete']}/{r['n_cycles_total']} ({r['completion_rate']*100:.0f}%) ROI {r['roi']:+.0f}%")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/montantes_v2_results.json","w") as f:
    json.dump({"all": results, "viable": viable}, f, indent=2)
print(f"\nSaved datasets/montantes_v2_results.json")
