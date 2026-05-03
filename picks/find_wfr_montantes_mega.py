#!/usr/bin/env python3
"""Sweep MEGA montantes WFR — explore zones non couvertes en mode strict."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

CANDS = []

# A. Foot xmkt complet 1x2+BTTS+OU 1.5+OU 2.5 — variations cote/legs/paliers
for cmin, cmax in [(1.10, 1.30), (1.20, 1.40), (1.25, 1.45), (1.30, 1.50)]:
    for legs in [1, 2, 3]:
        for n_p in [2, 3, 4]:
            CANDS.append({
                "id": f"WMM_xmkt_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Foot xmkt mega",
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

# B. Multi-sport combos 2j cote spécifique
for sports in [["football","ice-hockey"],
               ["football","basketball"],
               ["ice-hockey","basketball"],
               ["football","ice-hockey","basketball"]]:
    for cmin, cmax in [(1.20, 1.40), (1.30, 1.50), (1.40, 1.60), (1.45, 1.65)]:
        for legs in [1, 2]:
            for n_p in [2, 3]:
                for sort in ["wr", "ev"]:
                    sname = "+".join(s[:3] for s in sports)
                    CANDS.append({
                        "id": f"WMM_ms_{sname}_l{legs}_{cmin}-{cmax}_p{n_p}_{sort}",
                        "label": "Multi-sport mega",
                        "components": [{
                            "sports": sports, "market": "1x2",
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": sort, "max_legs": legs, "max_combos": 1,
                            "min_wr": None, "min_ev": None,
                            "legs_per_palier": legs,
                        }],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": legs},
                    })

# C. Hockey ultra-fav 1.10-1.30 paliers étendus
for cmin, cmax in [(1.10, 1.25), (1.15, 1.30), (1.20, 1.35)]:
    for n_p in [3, 4, 5, 7]:
        for legs in [1, 2]:
            CANDS.append({
                "id": f"WMM_hk_ultra_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Hockey ultra mini-cote",
                "components": [{
                    "sports": ["ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

# D. Foot Over 2.5 mid-cote (zone moins couverte)
for cmin, cmax in [(1.55, 1.75), (1.60, 1.80), (1.70, 1.95), (1.80, 2.10)]:
    for legs in [1, 2]:
        for n_p in [2, 3]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"WMM_o25_l{legs}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "label": "Foot O 2.5 mid-cote",
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

print(f"[WMM mega] {len(CANDS)} configs Winamax FR strict")

results = []
for i, s in enumerate(CANDS):
    if i % 30 == 0: print(f"  [{i}/{len(CANDS)}]")
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

viable = [r for r in results if s1(r)["compl"] >= 35 and s1(r)["pnl"] >= 200]
viable.sort(key=lambda r: -(s1(r)["pnl"] * s1(r)["compl"]/100))

print(f"\n[WMM mega] {len(viable)} viables (≥35% completion, PnL ≥200€)")

print(f"\n=== TOP 30 par EV pratique Winamax FR ===")
for r in viable[:30]:
    s = s1(r); a = apr(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"  EV {ev:>5.0f} | {s['compl']:>3.0f}% +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {a['pnl']:+5.0f}€ | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wmm_mega.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
