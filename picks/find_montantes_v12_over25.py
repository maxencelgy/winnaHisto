#!/usr/bin/env python3
"""Sweep v12 — Over 2.5 buts foot (zone moins explorée que Over 1.5).
+ comparaison Over 1.5 vs Over 2.5 sur mêmes profils.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Over 2.5 single — toutes cotes / paliers
for cmin, cmax in [(1.30, 1.50), (1.40, 1.60), (1.50, 1.70),
                   (1.55, 1.80), (1.60, 1.85), (1.70, 1.95)]:
    for n_p in [2, 3, 4, 5]:
        for sort in ["wr", "ev"]:
            CANDS.append({
                "id": f"V12A_o25_{cmin}-{cmax}_p{n_p}_{sort}",
                "label": "Over 2.5 single",
                "components": [{
                    "sports": ["football"], "market": "over_2_5",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

# B. Over 2.5 combo 2j
for cmin, cmax in [(1.30, 1.55), (1.40, 1.65), (1.50, 1.75)]:
    for n_p in [2, 3, 4]:
        for sort in ["wr", "ev"]:
            CANDS.append({
                "id": f"V12B_o25_l2_{cmin}-{cmax}_p{n_p}_{sort}",
                "label": "Over 2.5 combo 2j",
                "components": [{
                    "sports": ["football"], "market": "over_2_5",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 2, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 2,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 2},
            })

# C. BTTS single & combo (mid cote)
for cmin, cmax in [(1.40, 1.60), (1.50, 1.70), (1.60, 1.80)]:
    for n_p in [2, 3, 4]:
        for legs in [1, 2]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"V12C_btts_l{legs}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "BTTS oui montante",
                    "components": [{
                        "sports": ["football"], "market": "btts",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# D. Combo Foot O 2.5 + BTTS mix
for cmin, cmax in [(1.40, 1.65), (1.50, 1.75)]:
    for n_p in [2, 3, 4]:
        CANDS.append({
            "id": f"V12D_xmkt_btts+o25_l2_{cmin}-{cmax}_p{n_p}",
            "label": "Foot xmkt BTTS+O 2.5",
            "components": [{
                "sports": ["football"], "market": "btts,over_2_5",
                "cote_min": cmin, "cote_max": cmax,
                "sort_by": "wr", "max_legs": 2, "max_combos": 1,
                "min_wr": None, "min_ev": None,
                "legs_per_palier": 2,
            }],
            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                          "combo_legs_per_palier": 2},
        })

print(f"[v12 over25/btts] {len(CANDS)} configs")

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

viable = [r for r in results if s1(r)["compl"] >= 30 and s1(r)["pnl"] >= 100]

print(f"\n[v12] {len(viable)} viables (≥30% completion, PnL >100€)")

print(f"\n=== TOP 25 par EV pratique ===")
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
for r in viable[:25]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f}  {r['id'][:60]:<60s} {s['compl']:>3.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par AVRIL PnL (compl ≥ 30%) ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:60]:<60s}  Apr +{a['pnl']:.0f}€ | S1 +{s['pnl']:.0f}€ ({s['compl']:.0f}%)")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v12_over25.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
