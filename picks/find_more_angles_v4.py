#!/usr/bin/env python3
"""Sweep angles complémentaires:
  J. Baseball (sport ignoré, 17 gems audit data)
  K. BTTS autres ligues (Eredivisie, Championship, BL2, J1)
  L. Long montantes 4-6 paliers WR-filter
  M. Cross-market same-match combos (legs=2 même match)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# J. Baseball isolated
for cmin, cmax in [(1.30,1.45), (1.40,1.55), (1.50,1.70), (1.60,1.80), (1.70,1.95)]:
    for n_p in [1, 2, 3]:
        for sort in ["wr", "ev"]:
            for mwr in [None, 0.65, 0.70]:
                CANDS.append({
                    "id": f"J_BASE_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                    "kind": "J_BASEBALL",
                    "incl": None,
                    "components": [{"sports": ["baseball"], "market": "1x2",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# K. BTTS Yes autres ligues
K_LEAGUES = [
    (["eredivisie"], "ERED"),
    (["championship"], "CHAMP"),
    (["bundesliga 2", "2 bundesliga", "2. bundesliga"], "BL2"),
    (["j1 league"], "J1"),
    (["scottish premier", "premiership"], "SCOT"),
    (["super lig"], "TUR"),
    (["primeira liga"], "POR"),
    (["belgian", "jupiler"], "BEL"),
]
for incl, sname in K_LEAGUES:
    for cmin, cmax in [(1.55,1.75), (1.60,1.85), (1.70,2.00)]:
        for n_p in [1, 2, 3]:
            for sort in ["wr", "ev"]:
                for mwr in [None, 0.55, 0.60]:
                    CANDS.append({
                        "id": f"K_BTTS_{sname}_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                        "kind": "K_BTTS_OTHER",
                        "incl": incl,
                        "components": [{"sports": ["football"], "market": "btts",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

# L. Long montantes 4-6 paliers — micro-cote ultra-wr
L_SPORTS = [
    (["football","ice-hockey"], "FH"),
    (["football","ice-hockey","tennis","basketball"], "FHTB"),
    (["football"], "F"),
]
L_MARKETS = ["1x2,btts,over_1_5,over_2_5", "1x2"]
for sports, sname in L_SPORTS:
    for mkt in L_MARKETS:
        for cmin, cmax in [(1.05,1.12), (1.08,1.15), (1.05,1.15), (1.08,1.18)]:
            for n_p in [4, 5, 6]:
                for mwr in [0.85, 0.88, 0.90]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"L_LONG_{sname}_{mkt[:3]}_{cmin}-{cmax}_p{n_p}_wr{int(mwr*100)}_{sort}",
                            "kind": "L_LONG_MONT",
                            "incl": None,
                            "components": [{"sports": sports, "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

# M. Same-match cross-market combos via legs_per_palier=2 sur xmkt
# Le moteur ne lie pas explicitement same-match mais legs=2 sur xmkt prend 2 picks distincts
# Couvre cas où 2 picks du même match sortent en haut du tri
for sports, sname in [(["football"],"F"), (["football","ice-hockey"],"FH")]:
    for cmin, cmax in [(1.10,1.20), (1.10,1.25), (1.15,1.30)]:
        for mwr in [0.85, 0.88]:
            for n_p in [2, 3]:
                for sort in ["ev", "wr"]:
                    CANDS.append({
                        "id": f"M_SMCOMBO_{sname}_{cmin}-{cmax}_p{n_p}_wr{int(mwr*100)}_{sort}_legs2",
                        "kind": "M_SAMEMATCH_COMBO",
                        "incl": None,
                        "components": [{"sports": sports, "market": "1x2,btts,over_1_5,over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 2}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 2},
                    })

print(f"[v4] {len(CANDS)} configs")

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

print(f"\n[v4] {len(results)} viable (≥15 cycles)")

# Sort by PnL
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 15 par PnL ===")
print(f"  {'kind':<22} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:15]:
    print(f"  {r['kind']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

for kind in ["J_BASEBALL", "K_BTTS_OTHER", "L_LONG_MONT", "M_SAMEMATCH_COMBO"]:
    sub = [r for r in results if r["kind"] == kind]
    sub.sort(key=lambda r: -r["pnl"])
    print(f"\n=== TOP 6 {kind} ===")
    print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
    for r in sub[:6]:
        print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_more_angles_v4.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved /tmp/find_more_angles_v4.json")
