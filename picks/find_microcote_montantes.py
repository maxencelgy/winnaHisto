#!/usr/bin/env python3
"""Sweep montantes MICRO-COTE 1.08-1.22 sur paliers longs (5-10) — angle non exploré.
Hypothèse : cotes très basses → WR ≥80%, paliers longs jouables, compounding modéré mais sûr."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# Angle 1: foot OU micro-cote sur paliers longs
for cmin, cmax in [(1.08, 1.18), (1.10, 1.20), (1.12, 1.22), (1.15, 1.25)]:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5", "1x2,over_1_5,over_2_5,btts"]:
        for n_p in [5, 6, 7, 8, 10]:
            for mwr in [0.75, 0.80, 0.85]:
                CANDS.append({
                    "id": f"MICRO_F_{mkt[:5]}_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                    "label": "Micro-cote foot",
                    "components": [{
                        "sports": ["football"], "market": mkt,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                        "min_wr": mwr, "min_ev": None,
                        "legs_per_palier": 1,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# Angle 2: hockey 1x2 micro-cote (favoris écrasants)
for cmin, cmax in [(1.10, 1.25), (1.15, 1.30)]:
    for n_p in [4, 5, 6, 7]:
        for mwr in [0.75, 0.80, 0.85]:
            CANDS.append({
                "id": f"MICRO_H_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                "label": "Micro-cote hockey",
                "components": [{
                    "sports": ["ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

# Angle 3: combo 2j micro-cote → cote totale ~1.20-1.40, mais leg WR ≥85%
for cmin, cmax in [(1.05, 1.15), (1.08, 1.18)]:
    for mkt in ["over_1_5", "over_1_5,over_2_5,btts"]:
        for n_p in [4, 5, 6]:
            for mwr in [0.80, 0.85]:
                CANDS.append({
                    "id": f"MICRO_F2j_{mkt[:5]}_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                    "label": "Micro-cote combo 2j",
                    "components": [{
                        "sports": ["football"], "market": mkt,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 2, "max_combos": 1,
                        "min_wr": mwr, "min_ev": None,
                        "legs_per_palier": 2,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 2},
                })

print(f"[Micro-cote] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 25 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL,
                         excluded_leagues=WFR_EXCL)
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

# Tri principal: completion (métrique-clé montantes)
viable = [r for r in results if s1(r)["compl"] >= 50]
viable.sort(key=lambda r: -s1(r)["compl"])

print(f"\n[Micro-cote] {len(viable)} viables (completion ≥50%)")
print(f"\n=== TOP 20 par COMPLETION ===")
for r in viable[:20]:
    s = s1(r); a = apr(r)
    print(f"  Compl {s['compl']:>5.1f}% | +{s['pnl']:>5.0f}€ cap{s['avg_cap']:>4.0f}€ #{s['n_complete']}/{s['n_total']} | Apr {a['pnl']:+5.0f}€ | {r['id'][:60]}")

# Tri secondaire: EV pratique (PnL × completion)
viable2 = [r for r in results if s1(r)["pnl"] >= 100 and s1(r)["compl"] >= 30]
viable2.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
print(f"\n=== TOP 15 par EV PRATIQUE (pnl×compl, compl≥30) ===")
for r in viable2[:15]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f} | {s['compl']:>4.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€ | {r['id'][:60]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/microcote.json","w") as f:
    json.dump({"all": results, "viable_completion": viable[:30], "viable_ev": viable2[:20]}, f, indent=2)
print("\nSaved to datasets/microcote.json")
