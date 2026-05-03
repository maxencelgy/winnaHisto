#!/usr/bin/env python3
"""Trouver le profil montante optimal pour 10€ → 100€ (×10) le plus vite.
Cibles : cap_moyen ≥80€ ET completion ≥30%."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 10
TARGET = 100  # cible 10×
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

CANDS = []

# A. Montante n_paliers visant 100€
# 5p × 1.585 / 6p × 1.467 / 7p × 1.39 / 8p × 1.33
config_paliers = [
    (5, 1.55, 1.65, "5p_high"),  # cote 1.55-1.65 → 5p ~1.60^5 = 105€
    (6, 1.40, 1.55, "6p_mid"),   # cote 1.40-1.55 → 6p ~1.47^6 = 100€
    (6, 1.45, 1.55, "6p_high"),
    (7, 1.35, 1.45, "7p_mid"),   # cote 1.35-1.45 → 7p ~1.40^7 = 105€
    (8, 1.28, 1.40, "8p_mid"),   # cote 1.28-1.40 → 8p ~1.33^8 = 100€
    (8, 1.30, 1.45, "8p_high"),
    (9, 1.25, 1.35, "9p_low"),   # 9p ~1.30^9 = 106€
    (10, 1.22, 1.32, "10p_low"), # 10p ~1.26^10 = 100€
]

for n_p, cmin, cmax, tag in config_paliers:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5", "1x2,over_1_5,over_2_5,btts"]:
        for mwr in [0.65, 0.70, 0.75, 0.80]:
            CANDS.append({
                "id": f"GOAL100_{tag}_{cmin}-{cmax}_p{n_p}_wr{mwr}_{mkt[:8]}",
                "label": "10→100 montante",
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

# B. Multi-sport cross : foot + hockey alternés
for n_p, cmin, cmax, tag in [(6, 1.40, 1.55, "6p_FH"), (8, 1.28, 1.40, "8p_FH")]:
    for foot_wr in [0.70, 0.75]:
        for hockey_wr in [0.65, 0.70]:
            CANDS.append({
                "id": f"GOAL100_{tag}_{cmin}-{cmax}_fw{foot_wr}_hw{hockey_wr}",
                "label": "10→100 cross-sport",
                "components": [
                    {"sports": ["football"], "market": "over_1_5,over_2_5",
                     "cote_min": cmin, "cote_max": cmax,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                     "min_wr": foot_wr, "min_ev": None, "legs_per_palier": 1},
                    {"sports": ["ice-hockey"], "market": "1x2",
                     "cote_min": cmin, "cote_max": cmax,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                     "min_wr": hockey_wr, "min_ev": None, "legs_per_palier": 1},
                ],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[10→100] {len(CANDS)} configs")

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

# Critère : cap_moyen ≥ 80€ (proche 100€) ET completion ≥ 30%
viable = [r for r in results if s1(r)["avg_cap"] >= 70 and s1(r)["compl"] >= 25]
viable.sort(key=lambda r: -(s1(r)["avg_cap"] * s1(r)["compl"]/100))  # EV pratique

print(f"\n[10→100] {len(viable)} viables (cap≥70€ ET compl≥25%)")
print(f"\n=== TOP 20 par EV PRATIQUE (cap × compl) ===")
for r in viable[:20]:
    s = s1(r); a = apr(r)
    ev = s["avg_cap"] * s["compl"]/100
    print(f"  EV {ev:>5.0f} | cap {s['avg_cap']:>4.0f}€ compl {s['compl']:>4.0f}% +{s['pnl']:>4.0f}€ #{s['n_complete']}/{s['n_total']} | Apr {a['pnl']:+5.0f}€ | {r['id'][:60]}")

print(f"\n=== TOP 10 par CAP MOYEN ===")
viable_cap = [r for r in results if s1(r)["compl"] >= 25]
viable_cap.sort(key=lambda r: -s1(r)["avg_cap"])
for r in viable_cap[:10]:
    s = s1(r); a = apr(r)
    flag = " 🏆" if s["avg_cap"] >= 100 else ""
    print(f"  cap {s['avg_cap']:>4.0f}€ | compl {s['compl']:>4.0f}% +{s['pnl']:>4.0f}€ | Apr {a['pnl']:+4.0f}€ | {r['id'][:60]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/goal_10_to_100.json","w") as f:
    json.dump({"viable_ev": viable[:30], "all": results}, f, indent=2)
print("\nSaved.")
