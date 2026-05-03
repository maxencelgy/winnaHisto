#!/usr/bin/env python3
"""Challenge ×5 : 100€ → 500€."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 100
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

CANDS = []
configs = [
    (4, 1.45, 1.55, "4p_150"),
    (5, 1.35, 1.42, "5p_138"),
    (5, 1.36, 1.42, "5p_138_strict"),
    (6, 1.28, 1.34, "6p_131"),
    (6, 1.30, 1.36, "6p_133"),
    (7, 1.23, 1.30, "7p_126"),
    (8, 1.20, 1.26, "8p_122"),
]
for n_p, cmin, cmax, tag in configs:
    for sport, mkt in [("football", "over_1_5"), ("football", "over_1_5,over_2_5"),
                        ("football", "btts,over_1_5,over_2_5"), ("ice-hockey", "1x2")]:
        for mwr in [0.60, 0.65, 0.70, 0.75, 0.80]:
            CANDS.append({
                "id": f"X5_{tag}_{sport[:3]}_{mkt[:5]}_p{n_p}_wr{mwr}",
                "label": "Challenge x5",
                "components": [{
                    "sports": [sport], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[X5] {len(CANDS)} configs")
results = []
for i, s in enumerate(CANDS):
    if i % 30 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL, excluded_leagues=WFR_EXCL)
            perfs[pname] = {"compl": round(r["completion_rate"]*100,1),
                "avg_cap": round(r["avg_capital_complete"],1),
                "n_total": r["n_cycles_total"],
                "n_complete": r["n_cycles_complete"],
                "pnl": round(r["final_pnl"],1)}
        except: perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 5:
        s1 = perfs["S1-26"]
        compl_rate = s1["compl"]/100
        results.append({
            "id": s["id"], "perfs": perfs, "strat": s,
            "compl": s1["compl"], "cap": s1["avg_cap"], "n_total": s1["n_total"],
            "n_complete": s1["n_complete"],
            "prob_3": round((1 - (1 - compl_rate)**3) * 100, 2),
            "prob_5": round((1 - (1 - compl_rate)**5) * 100, 2),
            "prob_10": round((1 - (1 - compl_rate)**10) * 100, 2),
        })

viable = [r for r in results if r["cap"] >= 450 and r["compl"] >= 30]
viable.sort(key=lambda r: -r["prob_5"])

print(f"\n[X5] {len(viable)} viables (cap ≥450€ ET compl ≥30%)")
print(f"\n=== TOP 20 par PROB_5 ===")
for r in viable[:20]:
    flag = " 🏆" if r["prob_5"] >= 95 else ""
    print(f"  P3 {r['prob_3']:>5.1f}% P5 {r['prob_5']:>5.1f}% P10 {r['prob_10']:>5.1f}% | compl {r['compl']:>4.0f}% cap {r['cap']:>4.0f}€ #{r['n_total']:>2d} | {r['id'][:55]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v16_x5.json","w") as f:
    json.dump({"viable": viable[:50]}, f, indent=2)
print("\nSaved.")
