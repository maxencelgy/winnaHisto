#!/usr/bin/env python3
"""Sweep MASSIF : trouver challenges avec completion la plus haute possible.
Stratégie : explorer cote ultra-basse + WR ultra-strict + N paliers variable."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

# Pour 10€→100€ il faut N paliers cote^N = 10
# Pour completion la plus haute : maximiser N et minimiser cote
# 10p × 1.26, 12p × 1.21, 15p × 1.166, 20p × 1.122

CANDS = []

# ANGLE A : Long paliers cote ultra-basse pour 10€→100€
print("=== Angle A: longs paliers ultra-bas ===")
for n_p, cmin, cmax, tag in [
    (8, 1.30, 1.40, "8p_135"),
    (9, 1.27, 1.35, "9p_131"),
    (10, 1.24, 1.32, "10p_128"),
    (11, 1.21, 1.30, "11p_125"),
    (12, 1.18, 1.27, "12p_122"),
    (15, 1.15, 1.22, "15p_118"),
]:
    for sport, mkt in [("football", "over_1_5"), ("football", "over_1_5,over_2_5"),
                        ("football", "btts,over_1_5,over_2_5"), ("ice-hockey", "1x2")]:
        for mwr in [0.70, 0.75, 0.80, 0.85, 0.90]:
            CANDS.append({
                "id": f"USC10_{tag}_{sport[:3]}_{mkt[:5]}_p{n_p}_wr{mwr}",
                "label": "Ultra-safe 10→100",
                "components": [{
                    "sports": [sport], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": 10, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
                "_target": 100, "_initial": 10,
            })

# ANGLE B : Court paliers cote moyenne pour 100→200
print("=== Angle B: court paliers pour 100→200 ===")
for n_p, cmin, cmax, tag in [
    (2, 1.40, 1.45, "2p_142"),
    (2, 1.42, 1.45, "2p_142_strict"),
    (3, 1.25, 1.30, "3p_127"),
    (3, 1.26, 1.30, "3p_128_strict"),
    (4, 1.18, 1.22, "4p_120"),
    (5, 1.14, 1.17, "5p_115"),
]:
    for sport, mkt in [("football", "over_1_5"), ("ice-hockey", "1x2"),
                        ("football", "btts,over_1_5,over_2_5")]:
        for mwr in [0.75, 0.80, 0.85, 0.90]:
            CANDS.append({
                "id": f"USC2_{tag}_{sport[:3]}_{mkt[:5]}_p{n_p}_wr{mwr}",
                "label": "Ultra-safe 100→200",
                "components": [{
                    "sports": [sport], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": 100, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
                "_target": 200, "_initial": 100,
            })

# ANGLE C : 10→50 (×5) en peu de paliers - gain modeste mais probable
print("=== Angle C: 10→50 modeste mais probable ===")
for n_p, cmin, cmax, tag in [
    (3, 1.65, 1.75, "3p_170"),
    (4, 1.45, 1.55, "4p_150"),
    (5, 1.36, 1.42, "5p_138"),
    (6, 1.28, 1.34, "6p_131"),
    (7, 1.23, 1.30, "7p_126"),
    (8, 1.20, 1.27, "8p_123"),
]:
    for sport, mkt in [("football", "over_1_5"), ("ice-hockey", "1x2"),
                        ("football", "btts,over_1_5,over_2_5")]:
        for mwr in [0.70, 0.75, 0.80, 0.85]:
            CANDS.append({
                "id": f"USC5_{tag}_{sport[:3]}_{mkt[:5]}_p{n_p}_wr{mwr}",
                "label": "10→50 confort",
                "components": [{
                    "sports": [sport], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": 10, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
                "_target": 50, "_initial": 10,
            })

print(f"[USC] {len(CANDS)} configs total")

results = []
for i, s in enumerate(CANDS):
    if i % 60 == 0: print(f"  [{i}/{len(CANDS)}]")
    target = s.pop("_target")
    initial = s.pop("_initial")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=initial, excluded_leagues=WFR_EXCL)
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
            "id": s["id"], "perfs": perfs, "strat": s, "target": target, "initial": initial,
            "compl": s1["compl"], "cap": s1["avg_cap"], "n_total": s1["n_total"],
            "n_complete": s1["n_complete"],
            "prob_3": round((1 - (1 - compl_rate)**3) * 100, 2),
            "prob_5": round((1 - (1 - compl_rate)**5) * 100, 2),
            "prob_10": round((1 - (1 - compl_rate)**10) * 100, 2),
        })

# Pour chaque target, top par completion (la métrique-clé pour fiabilité)
for tgt in [100, 200, 50]:
    sub = [r for r in results if r["target"] == tgt and r["cap"] >= tgt * 0.9]
    sub.sort(key=lambda r: -r["compl"])
    print(f"\n=== TARGET {tgt}€ - TOP par COMPLETION (cap ≥ {tgt*0.9}€) ===")
    for r in sub[:15]:
        flag = " 🏆🏆" if r["compl"] >= 80 else (" 🏆" if r["compl"] >= 70 else "")
        print(f"  Compl {r['compl']:>4.0f}% | cap {r['cap']:>4.0f}€ #{r['n_total']:>2d} | P3 {r['prob_3']:>5.1f}% P5 {r['prob_5']:>5.1f}% | {r['id'][:60]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/ultra_safe_challenges.json","w") as f:
    json.dump({"all": results}, f, indent=2)
print("\nSaved.")
