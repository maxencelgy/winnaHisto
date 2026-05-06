#!/usr/bin/env python3
"""Ligues Amérique du Sud + Asie non couvertes : Argentina, Brasileirão, J-League, K-League, etc.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

LEAGUES = [
    (["primera division argentina", "liga profesional"], "ARG"),
    (["brasileirão", "brasileirao", "serie a brasil"], "BRA"),
    (["copa libertadores"], "LIBER"),
    (["copa sudamericana"], "SUDAM"),
    (["j1 league", "j-league"], "JPN"),
    (["k-league", "k league"], "KOR"),
    (["chinese super league", "csl"], "CHN"),
    (["a-league", "a league"], "AUS"),
    (["liga mx"], "MX"),
    (["mls", "major league soccer"], "USA"),
    (["liga mx", "mls", "primera division argentina", "brasileirão"], "AMERICAS"),
]

for incl, sname in LEAGUES:
    for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5"]:
        for cmin, cmax in [(1.20,1.40), (1.30,1.50), (1.40,1.65), (1.50,1.80), (1.60,2.00), (1.80,2.30)]:
            for mwr in [None, 0.55, 0.60, 0.65, 0.70]:
                for n_p in [1, 2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"S_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                            "incl": incl,
                            "components": [{"sports": ["football"], "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

print(f"[southam_asian] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s["incl"])
        if r["n_cycles_total"] >= 12 and r["final_pnl"] > 300:
            results.append({
                "id": s["id"], "incl": s["incl"][0],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[southam_asian] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 25 par PnL ===")
print(f"  {'league':<22} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:25]:
    print(f"  {r['incl']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 15 par SCORE ===")
for r in results[:15]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['incl']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_southam_asian.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
