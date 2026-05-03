#!/usr/bin/env python3
"""Sweep MEGA Winamax FR — explore profils non couverts.
Filter Winamax FR strict appliqué. Vise ≥40% completion + PnL ≥150€."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

WINAMAX_FR_EXCLUDED = [
    "liga mx","egyptian","cyprus","ligapro","primera división, clausura",
    "brasileirão série d","brasileirão série b","scottish premiership",
    "first professional league","danish superliga","superliga",
    "niké liga","swiss super league","austrian bundesliga",
    "stoiximan super league","czech first league","canadian premier",
    "usl championship","copa de la liga","frauen-bundesliga",
    "serie a femminile","uefa champions league, women","liga acb",
    "germany bbl","wnba preseason","serie a2","del, playoffs",
    "relegation round"
]

CANDS = []

# A. Combos 2j multi-sport mid-cote (différents pools)
for sports in [["football","ice-hockey"],
               ["football","basketball"],
               ["ice-hockey","basketball"],
               ["football","ice-hockey","basketball"]]:
    for cmin, cmax in [(1.20, 1.40), (1.25, 1.45), (1.30, 1.50),
                       (1.35, 1.55), (1.40, 1.60)]:
        for n_p in [2, 3]:
            for sort in ["wr", "ev"]:
                sname = "+".join(s[:3] for s in sports)
                CANDS.append({
                    "id": f"WFR_A_{sname}_l2_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "MS combo 2j",
                    "components": [{
                        "sports": sports, "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": 2, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": 2,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 2},
                })

# B. Foot Over 2.5 + variantes mid/high
for cmin, cmax in [(1.45, 1.65), (1.55, 1.75), (1.60, 1.85), (1.70, 1.95)]:
    for n_p in [2, 3, 4]:
        for sort in ["wr", "ev"]:
            for legs in [1, 2]:
                CANDS.append({
                    "id": f"WFR_B_o25_l{legs}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Over 2.5 single/combo",
                    "components": [{
                        "sports": ["football"], "market": "over_2_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# C. Foot Over 1.5 mid-cote (pas couvert en intraday)
for cmin, cmax in [(1.30, 1.45), (1.35, 1.55), (1.40, 1.60), (1.45, 1.65)]:
    for n_p in [2, 3, 4]:
        for legs in [1, 2]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"WFR_C_o15_mid_l{legs}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Over 1.5 mid-cote",
                    "components": [{
                        "sports": ["football"], "market": "over_1_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# D. BTTS combo 2j
for cmin, cmax in [(1.40, 1.60), (1.50, 1.70), (1.60, 1.80)]:
    for n_p in [2, 3]:
        for sort in ["wr", "ev"]:
            CANDS.append({
                "id": f"WFR_D_btts_l2_{cmin}-{cmax}_p{n_p}_{sort}",
                "label": "BTTS combo 2j",
                "components": [{
                    "sports": ["football"], "market": "btts",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 2, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": 2,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 2},
            })

# E. Multi-market foot 1x2+BTTS+OU combo 2j-3j (cross-market)
for mkt_set in ["1x2,btts", "1x2,over_2_5", "btts,over_2_5", "1x2,btts,over_1_5,over_2_5"]:
    for cmin, cmax in [(1.20, 1.40), (1.30, 1.50), (1.40, 1.60)]:
        for legs in [2, 3]:
            for n_p in [2, 3]:
                CANDS.append({
                    "id": f"WFR_E_xmkt_{mkt_set.replace(',','+')}_l{legs}_{cmin}-{cmax}_p{n_p}",
                    "label": "Foot xmkt combo",
                    "components": [{
                        "sports": ["football"], "market": mkt_set,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

print(f"[Sweep WFR new] {len(CANDS)} configs avec filtre Winamax FR")

results = []
for i, s in enumerate(CANDS):
    if i % 30 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL,
                         excluded_leagues=WINAMAX_FR_EXCLUDED)
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

# Filter ≥40% completion + PnL ≥150€
viable = [r for r in results if s1(r)["compl"] >= 40 and s1(r)["pnl"] >= 150]

print(f"\n[WFR new] {len(viable)} viables (≥40% completion, PnL >150€) sur {len(results)}")

print(f"\n=== TOP 30 par EV pratique (Winamax FR strict) ===")
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))
for r in viable[:30]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f}  {r['id'][:60]:<60s} {s['compl']:>3.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€")

print(f"\n=== TOP 15 par AVRIL PnL ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
for r in viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  {r['id'][:60]:<60s} Apr +{a['pnl']:.0f}€ | S1 +{s['pnl']:.0f}€ ({s['compl']:.0f}%)")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_wfr_new.json","w") as f:
    json.dump({"all": results, "viable": viable[:60]}, f, indent=2)
print("\nSaved.")
