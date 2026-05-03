#!/usr/bin/env python3
"""Sweep v14 — Hockey mid-cote 1.50-1.85 EV strict + variants pour trouver
profils Hockey-only complémentaires aux existants (1.20-1.50 et 1.30-1.60)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Hockey single mid-cote large + EV
for cmin, cmax in [(1.40, 1.60), (1.45, 1.70), (1.50, 1.75), (1.55, 1.80),
                   (1.60, 1.85), (1.65, 1.95), (1.70, 2.00)]:
    for n_p in [2, 3, 4]:
        for mev in [None, 1.05, 1.10]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"V14A_ice_{cmin}-{cmax}_p{n_p}_{sort}_ev{mev}",
                    "label": "Hockey mid-cote",
                    "components": [{
                        "sports": ["ice-hockey"], "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                        "min_wr": None, "min_ev": mev,
                        "legs_per_palier": 1,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# B. Foot+Hockey single mid-cote (multi-sport pool large)
for cmin, cmax in [(1.40, 1.60), (1.50, 1.75), (1.60, 1.85), (1.70, 1.95)]:
    for n_p in [2, 3]:
        for mev in [None, 1.05]:
            CANDS.append({
                "id": f"V14B_foo+ice_{cmin}-{cmax}_p{n_p}_ev{mev}",
                "label": "Foot+Hockey mid-cote",
                "components": [{
                    "sports": ["football", "ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": None, "min_ev": mev,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

# C. Foot 1x2 mid-cote 1.40-1.70 (zone non testée à fond)
for cmin, cmax in [(1.30, 1.50), (1.40, 1.60), (1.45, 1.65), (1.50, 1.70),
                   (1.55, 1.75), (1.60, 1.80)]:
    for n_p in [2, 3, 4]:
        for sort in ["wr", "ev"]:
            CANDS.append({
                "id": f"V14C_foo_{cmin}-{cmax}_p{n_p}_{sort}",
                "label": "Foot 1x2 mid-cote",
                "components": [{
                    "sports": ["football"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[v14 hockey-value] {len(CANDS)} configs")

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
                "pnl": round(r["final_pnl"], 1),
            }
        except Exception:
            perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 5:
        results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

viable = [r for r in results if s1(r)["compl"] >= 30 and s1(r)["pnl"] >= 100]

print(f"\n[v14] {len(viable)} viables (≥30% completion, PnL >100€)")

print(f"\n=== TOP 25 par EV pratique ===")
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
for r in viable[:25]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f}  {r['id'][:60]:<60s} {s['compl']:>3.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v14_hockey_value.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
