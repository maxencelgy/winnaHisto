#!/usr/bin/env python3
"""Sweep montantes v4 — FRÉQUENCE HAUTE.

Objectif : montantes 2-3 paliers maximisant le PnL net moyen, pas le ROI %.
On veut : "à chaque journée tu lances la montante, ça finit souvent et ça paie bien".

Métrique = PnL net total (gains accumulés - pertes) sur S1-26.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# Sport+market scope avec couvert: 1x2 sur tous les sports + multi-market sur foot
SPORT_MARKETS = [
    (["football"],            "1x2"),
    (["football"],            "btts"),
    (["football"],            "over_2_5"),
    (["football"],            "over_1_5"),
    (["football"],            "1x2,btts"),
    (["football"],            "1x2,btts,over_2_5"),
    (["ice-hockey"],          "1x2"),
    (["basketball"],          "1x2"),
    (["football","ice-hockey"], "1x2"),
    (["football","ice-hockey","basketball"], "1x2"),
    (["football","ice-hockey","basketball","tennis"], "1x2"),
]

# Cote ranges courts (fav très safe → mid-cote)
COTE_RANGES = [(1.10, 1.25), (1.15, 1.30), (1.20, 1.40),
               (1.30, 1.50), (1.40, 1.60), (1.50, 1.70)]

# Paliers courts pour fréquence
N_PALIERS = [2, 3, 4]
LEGS_PER_PALIER = [1, 2]

# Sort selection
SORT_BY = ["wr", "ev"]

for sports, mkt in SPORT_MARKETS:
    for cmin, cmax in COTE_RANGES:
        for n_p in N_PALIERS:
            for legs in LEGS_PER_PALIER:
                for sort in SORT_BY:
                    sname = "+".join(s[:3] for s in sports)
                    CANDS.append({
                        "id": f"F_{sname}_{mkt.replace(',','+')}_{cmin}-{cmax}_l{legs}_p{n_p}_{sort}",
                        "label": "Montante fréquence",
                        "components": [{
                            "sports": sports, "market": mkt,
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": sort, "max_legs": legs, "max_combos": 1,
                            "min_wr": None, "min_ev": None,
                            "legs_per_palier": legs,
                        }],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": legs},
                    })

print(f"[v4 freq] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
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

def s126(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0,"n_complete":0,"n_total":0}

# Filter : PnL positif + completion ≥ 30%
viable = [r for r in results if s126(r)["pnl"] > 0 and s126(r)["compl"] >= 30]

print(f"\n[v4 freq] {len(viable)} viables ({len(results)} total)")

print(f"\n=== TOP 30 par PnL NET TOTAL S1-26 ===")
viable.sort(key=lambda r: -s126(r)["pnl"])
print(f"{'ID':<55s} {'PnL':>7s} {'#✓/tot':>9s} {'%':>4s} {'AvgCap':>7s} {'WRp':>5s}  | Apr PnL")
print("-"*120)
for r in viable[:30]:
    s = s126(r); a = apr(r)
    print(f"{r['id'][:54]:<55s} {s['pnl']:>+6.0f}€ {s['n_complete']:>2d}/{s['n_total']:<3d}  {s['compl']:>3.0f}%  "
          f"{s['avg_cap']:>6.0f}€ {s['wr_p']:>4.0f}%   | {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par COMPLETION (n>=8 cycles) ===")
hi_compl = [r for r in viable if s126(r)["n_total"] >= 8]
hi_compl.sort(key=lambda r: -s126(r)["compl"])
for r in hi_compl[:15]:
    s = s126(r); a = apr(r)
    print(f"  {r['id'][:55]:<55s}  {s['compl']:>3.0f}%  {s['n_complete']}/{s['n_total']}  PnL +{s['pnl']:.0f}€ | Apr PnL {a['pnl']:+.0f}€")

print(f"\n=== TOP 15 par PnL Apr-26 SEUL ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s126(r); a = apr(r)
    print(f"  {r['id'][:55]:<55s}  Apr PnL {a['pnl']:+.0f}€  ({a['n_complete']}/{a['n_total']})  | S1-26 +{s['pnl']:.0f}€")

# Save
out_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_montantes_v4_freq.json"
with open(out_path, "w") as f:
    json.dump({"all": results, "viable": viable[:80]}, f, indent=2)
print(f"\nSaved {out_path}")
