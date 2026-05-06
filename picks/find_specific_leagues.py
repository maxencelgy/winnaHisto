#!/usr/bin/env python3
"""Sweep LIGUES SPÉCIFIQUES non couvertes : Eredivisie, Liga Portugal, MLS, NHL spécifique, KHL...
Audit avait identifié des pépites dans plusieurs ligues sans stratégie associée.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

LEAGUES = [
    (["eredivisie"], "ERED", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["primeira liga", "liga portugal"], "POR", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["mls"], "MLS", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["scottish premiership", "scottish premier"], "SCO", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["liga mx"], "MX", ["football"], "1x2"),
    (["liga argentina", "primera division argentina"], "ARG", ["football"], "1x2"),
    (["copa libertadores"], "LIBER", ["football"], "1x2"),
    (["championship"], "CHAMP_FB", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["khl"], "KHL", ["ice-hockey"], "1x2"),
    (["allsvenskan"], "ALLSV", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["jupiler", "belgian"], "BEL", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["super lig", "süper lig"], "TUR", ["football"], "1x2,btts,over_1_5,over_2_5"),
    (["a-league"], "ALEAGUE", ["football"], "1x2"),
    (["copa del rey"], "COPA", ["football"], "1x2"),
    (["fa cup"], "FACUP", ["football"], "1x2"),
    (["coupe de france"], "CDF", ["football"], "1x2"),
]

for incl, sname, sports, mkt in LEAGUES:
    for cmin, cmax in [(1.20,1.40), (1.30,1.50), (1.40,1.60), (1.50,1.80), (1.60,2.00)]:
        for mwr in [None, 0.60, 0.65, 0.70]:
            for n_p in [1, 2, 3]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"L_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                        "incl": incl,
                        "components": [{"sports": sports, "market": mkt,
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

print(f"[leagues] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s["incl"])
        if r["n_cycles_total"] >= 12 and r["final_pnl"] > 500:
            results.append({
                "id": s["id"], "incl": s["incl"][0],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[leagues] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 25 par PnL ===")
print(f"  {'league':<10} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:25]:
    print(f"  {r['incl']:<10} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_specific_leagues.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
