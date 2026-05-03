#!/usr/bin/env python3
"""Sweep v10 REALISTIC — recherche profils PRATIQUES (≥40% completion).

Pas de jackpots. On cherche des montantes qui aboutissent SOUVENT
(>1 cycle sur 2-3) avec PnL solide.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Single ultra-fav (paliers 2-4) tous sports
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
    for cmin, cmax in [(1.10, 1.25), (1.15, 1.30), (1.20, 1.35), (1.25, 1.45),
                       (1.30, 1.50), (1.35, 1.55), (1.40, 1.60)]:
        for n_p in [2, 3, 4]:
            for sort in ["wr", "ev"]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"V10A_{sname}_{mkt}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Single short-paliers",
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

# B. Combo 2j short-paliers (2-3 paliers)
for sports, mkt in SPORT_MARKETS:
    for cmin, cmax in [(1.15, 1.35), (1.20, 1.40), (1.25, 1.50), (1.30, 1.55)]:
        for n_p in [2, 3]:
            for sort in ["wr", "ev"]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"V10B_{sname}_{mkt}_l2_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Combo 2j short",
                    "components": [{
                        "sports": sports, "market": mkt,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": 2, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": 2,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 2},
                })

# C. EV-filtered (min_ev ≥ 1.05) sur cote modérée
for sp in ["football", "ice-hockey", "basketball"]:
    for cmin, cmax in [(1.30, 1.55), (1.40, 1.70), (1.45, 1.75)]:
        for n_p in [2, 3, 4]:
            for mev in [1.05, 1.10]:
                CANDS.append({
                    "id": f"V10C_{sp[:3]}_{cmin}-{cmax}_ev{mev}_p{n_p}",
                    "label": "EV-filtered single",
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

print(f"[v10 realistic] {len(CANDS)} configs")

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
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 5:
        results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

# Filter HIGH completion (≥40%) AND PnL > 100€
viable = [r for r in results if s1(r)["compl"] >= 40 and s1(r)["pnl"] >= 100]

print(f"\n[v10 realistic] {len(viable)} viables (≥40% completion, PnL >100€) sur {len(results)} total")

print(f"\n=== TOP 30 par EV pratique (PnL × completion) ===")
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
for r in viable[:30]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f}  {r['id'][:60]:<60s} {s['compl']:>3.0f}%  PnL +{s['pnl']:>4.0f}€  cap {s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par PnL Avril seul (compl ≥ 40%) ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:60]:<60s}  Apr +{a['pnl']:.0f}€ | S1 +{s['pnl']:.0f}€ ({s['compl']:.0f}%)")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v10_realistic.json","w") as f:
    json.dump({"all": results, "viable": viable[:80]}, f, indent=2)
print("\nSaved.")
