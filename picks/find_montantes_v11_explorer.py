#!/usr/bin/env python3
"""Sweep v11 explorer — sports peu testés + nouveaux angles.
A. Basket-only profils (NBA, ACB, EuroLeague)
B. Baseball-only profils (MLB)
C. Cross-market foot 3j mid-cote avec EV filter
D. Tennis pour combo multi-sport (test inclusion limitée)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Basket-only
for cmin, cmax in [(1.10, 1.25), (1.15, 1.30), (1.20, 1.35), (1.25, 1.45),
                   (1.30, 1.55), (1.40, 1.65), (1.50, 1.75)]:
    for legs in [1, 2]:
        for n_p in [2, 3, 4, 5]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"V11A_bas_l{legs}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Basket-only montante",
                    "components": [{
                        "sports": ["basketball"], "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# B. Baseball-only
for cmin, cmax in [(1.20, 1.40), (1.30, 1.55), (1.40, 1.70), (1.50, 1.85)]:
    for legs in [1, 2]:
        for n_p in [2, 3, 4]:
            CANDS.append({
                "id": f"V11B_bsb_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Baseball-only montante",
                "components": [{
                    "sports": ["baseball"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

# C. Foot xmkt 3j mid-cote avec EV
for mkt_set in ["1x2,btts", "1x2,over_2_5", "1x2,btts,over_2_5"]:
    for cmin, cmax in [(1.30, 1.55), (1.40, 1.65), (1.50, 1.80)]:
        for n_p in [2, 3, 4]:
            for mev in [None, 1.05]:
                CANDS.append({
                    "id": f"V11C_foo_xmkt_{mkt_set.replace(',','+')}_l3_{cmin}-{cmax}_p{n_p}_ev{mev}",
                    "label": "Foot xmkt 3j EV",
                    "components": [{
                        "sports": ["football"], "market": mkt_set,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "ev", "max_legs": 3, "max_combos": 1,
                        "min_wr": None, "min_ev": mev,
                        "legs_per_palier": 3,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 3},
                })

# D. Multi-comp Foot+Basket combo 2j (zone non testée à ce profile)
for cmin, cmax in [(1.20, 1.40), (1.30, 1.55), (1.40, 1.65)]:
    for n_p in [2, 3, 4]:
        for sort in ["wr", "ev"]:
            CANDS.append({
                "id": f"V11D_foo+bas_l2_{cmin}-{cmax}_p{n_p}_{sort}",
                "label": "Foot+Basket combo 2j",
                "components": [{
                    "sports": ["football", "basketball"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 2, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 2,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 2},
            })

# E. Foot + Basket + Tennis combo 3j (hybride)
for cmin, cmax in [(1.20, 1.40), (1.30, 1.55)]:
    for n_p in [2, 3]:
        CANDS.append({
            "id": f"V11E_xs_foo+bas+ten_l3_{cmin}-{cmax}_p{n_p}",
            "label": "Foot+Basket+Tennis combo 3j",
            "components": [{
                "sports": ["football", "basketball", "tennis"], "market": "1x2",
                "cote_min": cmin, "cote_max": cmax,
                "sort_by": "wr", "max_legs": 3, "max_combos": 1,
                "min_wr": None, "min_ev": None,
                "legs_per_palier": 3,
            }],
            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                          "combo_legs_per_palier": 3},
        })

print(f"[v11 explorer] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 30 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL)
            perfs[pname] = {
                "n_complete": r["n_cycles_complete"],
                "n_total": r["n_cycles_total"],
                "compl": round(r["completion_rate"]*100, 1),
                "avg_cap": round(r["avg_capital_complete"], 1),
                "roi": round(r["roi"], 1),
                "wr_p": round(r["wr_palier"]*100, 1),
                "pnl": round(r["final_pnl"], 1),
            }
        except Exception:
            perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 5:
        results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

# Filter ≥30% completion + PnL >100€
viable = [r for r in results if s1(r)["compl"] >= 30 and s1(r)["pnl"] >= 100]

print(f"\n[v11 explorer] {len(viable)} viables (≥30% completion, PnL >100€)")

print(f"\n=== TOP 25 par EV pratique (PnL × completion) ===")
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
for r in viable[:25]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f}  {r['id'][:60]:<60s} {s['compl']:>3.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v11_explorer.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
