#!/usr/bin/env python3
"""Sweep MODE INTERDAY : 1 palier par jour, cycle dure N jours.
Différent du intraday (N paliers même jour). Plus posé, moins de cycles total.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

SPORT_MARKETS = [
    (["football","ice-hockey","tennis"], "1x2", "FHT"),
    (["football","ice-hockey","tennis","basketball"], "1x2", "FHTB"),
    (["football","ice-hockey"], "1x2,btts,over_1_5,over_2_5", "FH_xmkt"),
    (["football","ice-hockey","tennis"], "1x2,btts,over_1_5,over_2_5", "FHT_xmkt"),
    (["football"], "over_1_5", "F_o15"),
    (["football"], "over_2_5", "F_o25"),
    (["football"], "btts", "F_btts"),
    (["football","ice-hockey","tennis","basketball","baseball"], "1x2", "ALL5"),
]

for sports, mkt, sname in SPORT_MARKETS:
    for cmin, cmax in [(1.10,1.25), (1.20,1.35), (1.20,1.40), (1.25,1.40),
                        (1.30,1.50), (1.40,1.60), (1.50,1.80), (1.60,2.00)]:
        for mwr in [None, 0.55, 0.60, 0.65, 0.70, 0.75]:
            for n_p in [3, 5, 7, 10]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"I_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

print(f"[interday] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        # MODE INTERDAY
        r = simulate(s, START, END, mode="interday", initial_stake=INITIAL)
        if r["n_cycles_total"] >= 5 and r["final_pnl"] > 200:
            results.append({
                "id": s["id"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[interday] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 20 par PnL (INTERDAY) ===")
for r in results[:20]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<3} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 10 par SCORE INTERDAY ===")
for r in results[:10]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<3} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top by completion
results.sort(key=lambda r: -r["comp"])
sub = [r for r in results if r["n_tot"] >= 8]
print(f"\n=== TOP 10 par COMPLETION (INTERDAY ≥8 cyc) ===")
for r in sub[:10]:
    print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<3} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_interday_winners.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
