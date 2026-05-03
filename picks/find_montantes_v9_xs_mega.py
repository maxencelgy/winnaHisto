#!/usr/bin/env python3
"""Sweep v9 multisport mega — combos 5-6 jambes multi-sport mini-cote.
Angle complémentaire au foot O 1.5 : combos avec hockey/basket/foot mélangés.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Combos 5-6 jambes multi-sport ULTRA-FAV
for sports in [["football","ice-hockey"],
               ["football","basketball"],
               ["ice-hockey","basketball"],
               ["football","ice-hockey","basketball"],
               ["football","ice-hockey","basketball","tennis"]]:
    for cmin, cmax in [(1.05, 1.20), (1.08, 1.22), (1.10, 1.25)]:
        for legs in [5, 6, 7]:
            for n_p in [3, 4, 5]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"V9A_xs_{sname}_l{legs}_{cmin}-{cmax}_p{n_p}",
                    "label": "Multi-sport mega-combo",
                    "components": [{
                        "sports": sports, "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# B. Foot xmkt 5-6 jambes (cross-market mega)
for cmin, cmax in [(1.05, 1.20), (1.08, 1.22), (1.10, 1.25)]:
    for legs in [5, 6]:
        for n_p in [3, 4, 5]:
            CANDS.append({
                "id": f"V9B_foo_xmkt_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Foot xmkt mega-combo",
                "components": [{
                    "sports": ["football"], "market": "1x2,btts,over_1_5,over_2_5",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

# C. Combo 9-10 jambes Over 1.5 (extrême)
for cmin, cmax in [(1.10, 1.22), (1.10, 1.25)]:
    for legs in [9, 10]:
        for n_p in [3, 4]:
            CANDS.append({
                "id": f"V9C_o15_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "O 1.5 ultra-mega 9-10j",
                "components": [{
                    "sports": ["football"], "market": "over_1_5",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

print(f"[v9 mega] {len(CANDS)} configs")

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
        results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

viable = [r for r in results if s1(r)["pnl"] > 0]

print(f"\n[v9 mega] {len(viable)} viables ({len(results)} total)")

print(f"\n=== TOP 25 par PnL S1-26 ===")
viable.sort(key=lambda r: -s1(r)["pnl"])
for r in viable[:25]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:60]:<60s} {s['pnl']:>+5.0f}€  {s['n_complete']:>2d}/{s['n_total']:<3d}  {s['compl']:>3.0f}%  cap{s['avg_cap']:>5.0f}€ | Apr {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par AVRIL PnL ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:60]:<60s}  Apr +{a['pnl']:.0f}€ | S1 +{s['pnl']:.0f}€ ({s['compl']:.0f}%)")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v9_mega.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
