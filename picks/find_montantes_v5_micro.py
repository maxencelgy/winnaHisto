#!/usr/bin/env python3
"""Sweep v5 micro — angles fins non testés.

A. Montante anti-streak : skip après loss
B. Cote intermédiaire 1.5-1.7 single avec sort_by=ev seulement
C. Hockey 1.10-1.30 ×5p+ paliers (très safe long)
D. Combo 3j multi-sport short (×2,×3 paliers)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# C. Hockey ultra-safe long : 1.10-1.30 cote × paliers étendus
for cmin, cmax in [(1.05, 1.20), (1.10, 1.20), (1.10, 1.25), (1.15, 1.25)]:
    for n_p in [3, 5, 7, 10]:
        CANDS.append({
            "id": f"M5C_hk_{cmin}-{cmax}_p{n_p}",
            "label": "Hockey ultra-safe long",
            "components": [{
                "sports": ["ice-hockey"], "market": "1x2",
                "cote_min": cmin, "cote_max": cmax,
                "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                "min_wr": null, "min_ev": null,
                "legs_per_palier": 1
            }],
            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                          "combo_legs_per_palier": 1},
        }) if False else CANDS.append({
            "id": f"M5C_hk_{cmin}-{cmax}_p{n_p}",
            "label": "Hockey ultra-safe long",
            "components": [{
                "sports": ["ice-hockey"], "market": "1x2",
                "cote_min": cmin, "cote_max": cmax,
                "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                "min_wr": None, "min_ev": None,
                "legs_per_palier": 1,
            }],
            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                          "combo_legs_per_palier": 1},
        })

# D. Combo 3j multi-sport
for sports in [["football","ice-hockey"],["football","basketball"],
               ["ice-hockey","basketball"]]:
    for cmin, cmax in [(1.20, 1.40), (1.25, 1.50), (1.35, 1.60)]:
        for n_p in [2, 3, 4]:
            CANDS.append({
                "id": f"M5D_xs_{'+'.join(s[:3] for s in sports)}_{cmin}-{cmax}_l3_p{n_p}",
                "label": "Combo3j multi-sport short",
                "components": [{
                    "sports": sports, "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 3, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 3,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 3},
            })

# B. Cote 1.5-1.7 single sort by EV avec EV>=1.05/1.10
for sp in ["ice-hockey","football","basketball"]:
    for cmin, cmax in [(1.45, 1.65), (1.55, 1.75), (1.50, 1.80)]:
        for mev in [1.05, 1.10]:
            for n_p in [2, 3, 4]:
                CANDS.append({
                    "id": f"M5B_{sp[:3]}_{cmin}-{cmax}_ev{mev}_p{n_p}",
                    "label": "Mid-cote value single",
                    "components": [{
                        "sports": [sp], "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "ev", "max_legs": 1, "max_combos": 1,
                        "min_wr": None, "min_ev": mev,
                        "legs_per_palier": 1,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# E. Foot OU very small range sub-cote 1.10
for cmin, cmax in [(1.05, 1.15), (1.05, 1.20), (1.08, 1.18)]:
    for mkt in ["over_1_5", "1x2"]:
        for n_p in [3, 5, 7, 10, 15]:
            CANDS.append({
                "id": f"M5E_foo_{mkt}_{cmin}-{cmax}_p{n_p}",
                "label": "Foot mini-cote ULTRA",
                "components": [{
                    "sports": ["football"], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[v5 micro] {len(CANDS)} configs")

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
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 3:
        results.append({"id": s["id"], "label": s["label"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

viable = [r for r in results if s1(r)["pnl"] > 0]

print(f"\n[v5 micro] {len(viable)} viables ({len(results)} total)")

print(f"\n=== TOP 25 par PnL S1-26 ===")
viable.sort(key=lambda r: -s1(r)["pnl"])
print(f"{'ID':<55s} {'PnL':>7s} {'#✓/tot':>9s} {'%':>4s} {'Cap':>5s} {'WRp':>5s} | Apr PnL")
print("-"*110)
for r in viable[:25]:
    s = s1(r); a = apr(r)
    print(f"{r['id'][:54]:<55s} {s['pnl']:>+5.0f}€  {s['n_complete']:>2d}/{s['n_total']:<3d}  {s['compl']:>3.0f}%  {s['avg_cap']:>4.0f}€ {s['wr_p']:>4.0f}%  | {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par AVRIL PnL ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:55]:<55s}  Apr +{a['pnl']:.0f}€ | S1-26 +{s['pnl']:.0f}€")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_montantes_v5_micro.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print(f"\nSaved.")
