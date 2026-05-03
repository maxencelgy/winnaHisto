#!/usr/bin/env python3
"""Sweep v7 extreme — extension V6A : combo 5-6 jambes Over 1.5 + variantes
+ tests de Hockey/Basket combo 2j cote mid (1.40-1.70) qui n'ont pas été
explorés en montante.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Extension V6A : combos 5-6 jambes Over 1.5 mini-cote
for cmin, cmax in [(1.05, 1.15), (1.08, 1.20), (1.10, 1.22)]:
    for legs in [5, 6]:
        for n_p in [3, 4, 5]:
            CANDS.append({
                "id": f"V7A_o15_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Over 1.5 mega-combo",
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

# B. Hockey/Basket combo 2j mid-cote (1.40-1.70)
for sports in [["ice-hockey"], ["basketball"], ["ice-hockey","basketball"]]:
    for cmin, cmax in [(1.30, 1.60), (1.40, 1.70), (1.50, 1.80)]:
        for legs in [2, 3]:
            for n_p in [2, 3, 4]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"V7B_{sname}_l{legs}_{cmin}-{cmax}_p{n_p}",
                    "label": "Hockey/Basket mid-cote combo",
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

# C. Foot multi-market combo 3-4j cote 1.10-1.30 (variante de V6D)
for cmin, cmax in [(1.10, 1.25), (1.15, 1.30)]:
    for legs in [3, 4]:
        for n_p in [3, 4, 5, 6]:
            CANDS.append({
                "id": f"V7C_foo_xmkt_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Foot xmkt combo mini",
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

# D. Multi-sport combo 2j ULTRA-FAV cote 1.10-1.25 (variante V6 mais ×3 ×4 sports)
for sports in [["football","ice-hockey","basketball"],
               ["football","ice-hockey","basketball","tennis"]]:
    for cmin, cmax in [(1.10, 1.25), (1.15, 1.30)]:
        for legs in [2, 3]:
            for n_p in [3, 4, 5, 6, 7]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"V7D_xs_{sname}_l{legs}_{cmin}-{cmax}_p{n_p}",
                    "label": "Multi-sport ultra-fav combo",
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

print(f"[v7 extreme] {len(CANDS)} configs")

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

print(f"\n[v7 extreme] {len(viable)} viables ({len(results)} total)")

print(f"\n=== TOP 30 par PnL S1-26 ===")
viable.sort(key=lambda r: -s1(r)["pnl"])
print(f"{'ID':<60s} {'PnL':>7s} {'#✓/tot':>10s} {'%':>4s} {'Cap':>6s} {'WRp':>5s} | Apr PnL")
print("-"*125)
for r in viable[:30]:
    s = s1(r); a = apr(r)
    print(f"{r['id'][:59]:<60s} {s['pnl']:>+5.0f}€  {s['n_complete']:>2d}/{s['n_total']:<3d}  {s['compl']:>3.0f}%  {s['avg_cap']:>5.0f}€ {s['wr_p']:>4.0f}% | {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par AVRIL PnL ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:60]:<60s}  Apr +{a['pnl']:.0f}€ | S1 +{s['pnl']:.0f}€ ({s['compl']:.0f}%)")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v7_extreme.json","w") as f:
    json.dump({"all": results, "viable": viable[:60]}, f, indent=2)
print("\nSaved.")
