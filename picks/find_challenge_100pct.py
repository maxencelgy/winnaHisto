#!/usr/bin/env python3
"""Trouver stratégie 100% prob d'atteindre 100€ via multi-cycles.
Logique : si completion ≥75% et cap_moy ≥90€, alors 5 cycles cumulés = 99.9% chances de réussite.
On cherche un profil avec : cap_moy ≥85€ ET completion ≥65%."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

CANDS = []

# Stratégies visant cap ≥ 100€ avec completion la plus haute possible
configs = [
    # 4 paliers cote ~1.78 → 100€
    (4, 1.70, 1.85, "4p_178"),
    (4, 1.65, 1.80, "4p_172"),
    (4, 1.75, 1.95, "4p_185"),
    # 5 paliers cote ~1.585 → 100€
    (5, 1.50, 1.70, "5p_160"),
    (5, 1.55, 1.65, "5p_160_strict"),
    (5, 1.55, 1.70, "5p_162"),
    (5, 1.60, 1.75, "5p_167"),
    # 6 paliers cote ~1.467 → 100€
    (6, 1.40, 1.55, "6p_147"),
    (6, 1.42, 1.52, "6p_147_strict"),
    (6, 1.45, 1.55, "6p_150"),
    # 7 paliers cote ~1.39 → 100€
    (7, 1.35, 1.45, "7p_140"),
    (7, 1.36, 1.42, "7p_139_strict"),
    (7, 1.38, 1.45, "7p_141"),
]

for n_p, cmin, cmax, tag in configs:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5", "1x2,over_1_5,over_2_5,btts"]:
        for mwr in [0.55, 0.60, 0.65, 0.70, 0.75]:
            CANDS.append({
                "id": f"WIN100_{tag}_p{n_p}_wr{mwr}_{mkt[:8]}",
                "label": "100% Challenge",
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

# Multi-sport hockey 1x2 (souvent favoris écrasants)
for n_p, cmin, cmax, tag in [(5, 1.55, 1.70, "5p_H"), (6, 1.40, 1.55, "6p_H"), (7, 1.35, 1.45, "7p_H")]:
    for mwr in [0.65, 0.70, 0.75, 0.80]:
        CANDS.append({
            "id": f"WIN100_{tag}_p{n_p}_wr{mwr}",
            "label": "100% Hockey",
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

print(f"[100%] {len(CANDS)} configs")

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
        s1 = perfs["S1-26"]
        # Compute probability of reaching 100€ over K cycles
        compl_rate = s1["compl"]/100
        cap = s1["avg_cap"]
        results.append({
            "id": s["id"], "perfs": perfs, "strat": s,
            "compl": s1["compl"], "cap": s1["avg_cap"],
            "n_total": s1["n_total"],
            # Prob of at least 1 success in K cycles
            "prob_3": round((1 - (1 - compl_rate)**3) * 100, 2),
            "prob_5": round((1 - (1 - compl_rate)**5) * 100, 2),
            "prob_10": round((1 - (1 - compl_rate)**10) * 100, 2),
        })

# Filtre : cap doit pouvoir atteindre 100€ ET completion ≥ 50%
viable = [r for r in results if r["cap"] >= 90 and r["compl"] >= 40]
# Tri par prob_5 (proba d'atteindre 100€ en 5 tentatives max)
viable.sort(key=lambda r: -r["prob_5"])

print(f"\n[100%] {len(viable)} viables (cap ≥ 90€ ET compl ≥ 40%)")
print(f"\n=== TOP 25 par PROB_5 cycles (atteindre 100€ en max 5 tentatives) ===")
for r in viable[:25]:
    flag = " 🏆🏆🏆" if r["prob_5"] >= 99.9 else (" 🏆🏆" if r["prob_5"] >= 99 else (" 🏆" if r["prob_5"] >= 95 else ""))
    apr = r["perfs"].get("Apr", {})
    print(f"  P5 {r['prob_5']:>5.1f}% P3 {r['prob_3']:>5.1f}% P10 {r['prob_10']:>5.1f}% | compl {r['compl']:>4.0f}% cap {r['cap']:>4.0f}€ #{r['n_total']:>2d} | Apr cap{apr.get('avg_cap','-'):>3} | {r['id'][:55]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/challenge_100pct.json","w") as f:
    json.dump({"viable": viable[:50], "all_count": len(results)}, f, indent=2)
print("\nSaved.")
