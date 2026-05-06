#!/usr/bin/env python3
"""Sweep v5 angles complémentaires:
  N. Ultra-long montantes 7-8 paliers WR strict
  O. Basketball league-filtered (NBA, NBA Playoffs, Liga ACB)
  P. Foot TOP5 only (Premier, La Liga, Serie A, Bundesliga, Ligue 1)
  Q. Multi-component avec sort=cote (lowest odds first sur xmkt)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# N. Ultra-long montantes 7-10 paliers
N_SPORTS = [
    (["football","ice-hockey"], "FH"),
    (["football","ice-hockey","tennis","basketball"], "FHTB"),
    (["football"], "F"),
]
for sports, sname in N_SPORTS:
    for mkt in ["1x2,btts,over_1_5,over_2_5", "1x2"]:
        for cmin, cmax in [(1.05,1.10), (1.05,1.12), (1.05,1.15), (1.08,1.15)]:
            for n_p in [7, 8, 9, 10]:
                for mwr in [0.85, 0.88, 0.90, 0.92]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"N_ULTRA_{sname}_{mkt[:3]}_{cmin}-{cmax}_p{n_p}_wr{int(mwr*100)}_{sort}",
                            "kind": "N_ULTRA_LONG",
                            "incl": None,
                            "components": [{"sports": sports, "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

# O. Basketball ligues spécifiques
O_LEAGUES = [
    (["nba"], "NBA"),
    (["liga acb"], "LIGA_ACB"),
    (["nba", "liga acb", "lega basket", "vtb"], "MULTI_BASKET"),
    (["euroleague"], "EUROLEAGUE"),
]
for incl, sname in O_LEAGUES:
    for cmin, cmax in [(1.20,1.40), (1.30,1.50), (1.40,1.60), (1.50,1.75), (1.70,2.00)]:
        for n_p in [1, 2, 3]:
            for sort in ["wr", "ev"]:
                for mwr in [None, 0.65, 0.70]:
                    CANDS.append({
                        "id": f"O_BASKET_{sname}_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                        "kind": "O_BASKET_LEAGUE",
                        "incl": incl,
                        "components": [{"sports": ["basketball"], "market": "1x2",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

# P. Foot TOP5 only
P_LEAGUES = [
    (["premier league", "la liga", "serie a", "bundesliga", "ligue 1"], "TOP5"),
    (["premier league"], "PL"),
    (["la liga"], "LIGA"),
    (["serie a"], "SA"),
    (["ligue 1"], "L1"),
]
for incl, sname in P_LEAGUES:
    for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5", "btts", "over_2_5"]:
        for cmin, cmax in [(1.20,1.40), (1.30,1.50), (1.40,1.60), (1.50,1.75)]:
            for n_p in [2, 3, 4]:
                for mwr in [None, 0.65, 0.70]:
                    for sort in ["ev", "wr"]:
                        CANDS.append({
                            "id": f"P_TOP5_{sname}_{mkt[:3]}_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                            "kind": "P_FOOT_TOP5",
                            "incl": incl,
                            "components": [{"sports": ["football"], "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

# Q. Sort=cote (lowest odds first) — pure safe pick on xmkt
for sports, sname in [(["football","ice-hockey"],"FH"), (["football","ice-hockey","tennis","basketball"],"FHTB")]:
    for cmin, cmax in [(1.03,1.15), (1.05,1.20), (1.08,1.25)]:
        for mwr in [None, 0.75, 0.80, 0.85]:
            for n_p in [3, 4, 5, 6]:
                CANDS.append({
                    "id": f"Q_COTE_{sname}_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                    "kind": "Q_SORT_COTE",
                    "incl": None,
                    "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": "cote", "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

print(f"[v5] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s.get("incl"))
        if r["n_cycles_total"] >= 15:
            results.append({
                "id": s["id"], "kind": s["kind"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[v5] {len(results)} viable (≥15 cycles)")

# Sort by PnL
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 15 par PnL ===")
print(f"  {'kind':<18} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:15]:
    print(f"  {r['kind']:<18} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

for kind in ["N_ULTRA_LONG", "O_BASKET_LEAGUE", "P_FOOT_TOP5", "Q_SORT_COTE"]:
    sub = [r for r in results if r["kind"] == kind]
    sub.sort(key=lambda r: -r["pnl"])
    print(f"\n=== TOP 6 {kind} ===")
    print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
    for r in sub[:6]:
        print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_more_angles_v5.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved /tmp/find_more_angles_v5.json")
