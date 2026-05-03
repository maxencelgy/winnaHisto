#!/usr/bin/env python3
"""Sweep v15 — Mode INTERDAY (1 palier/jour, cycle dure plusieurs jours)
Pour ceux qui veulent un rythme plus posé."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Single sports/markets en interday
SPORT_MARKETS = [
    (["football"], "1x2"),
    (["football"], "over_1_5"),
    (["football"], "over_2_5"),
    (["football"], "btts"),
    (["ice-hockey"], "1x2"),
    (["basketball"], "1x2"),
    (["football","ice-hockey"], "1x2"),
    (["football","basketball"], "1x2"),
    (["ice-hockey","basketball"], "1x2"),
    (["football","ice-hockey","basketball"], "1x2"),
]
for sports, mkt in SPORT_MARKETS:
    for cmin, cmax in [(1.10, 1.25), (1.20, 1.35), (1.25, 1.45),
                       (1.30, 1.50), (1.40, 1.60), (1.50, 1.70)]:
        for n_p in [3, 5, 7, 10]:
            for sort in ["wr", "ev"]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"V15A_id_{sname}_{mkt}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Interday single",
                    "components": [{
                        "sports": sports, "market": mkt,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": 1,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

print(f"[v15 interday] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="interday", initial_stake=INITIAL)
            perfs[pname] = {
                "n_complete": r["n_cycles_complete"],
                "n_total": r["n_cycles_total"],
                "compl": round(r["completion_rate"]*100, 1),
                "avg_cap": round(r["avg_capital_complete"], 1),
                "pnl": round(r["final_pnl"], 1),
            }
        except Exception:
            perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 3:
        results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

viable = [r for r in results if s1(r)["compl"] >= 30 and s1(r)["pnl"] >= 50]

print(f"\n[v15 interday] {len(viable)} viables (≥30% completion, PnL >50€)")

print(f"\n=== TOP 25 par EV pratique ===")
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
for r in viable[:25]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f}  {r['id'][:60]:<60s} {s['compl']:>3.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v15_interday.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
