#!/usr/bin/env python3
"""Pattern foot xmkt MAX VOLUME appliqué à toutes les cibles : 10→100, 100→300, 100→500."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

CANDS = []

# CIBLE 10→100 (×10) : 5p×1.585, 6p×1.467, 7p×1.39, 8p×1.33, 10p×1.26
for n_p, cmin, cmax, target_tag in [
    (5, 1.55, 1.65, "10to100_5p"),
    (6, 1.42, 1.55, "10to100_6p"),
    (7, 1.36, 1.45, "10to100_7p"),
    (8, 1.30, 1.40, "10to100_8p"),
    (10, 1.24, 1.32, "10to100_10p"),
]:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5",
                "1x2,over_1_5,over_2_5,btts"]:
        for mwr in [0.55, 0.60, 0.65, 0.70, 0.75]:
            CANDS.append({
                "id": f"FXMK_{target_tag}_p{n_p}_wr{mwr}_{mkt[:8]}",
                "_target": 100, "_initial": 10,
                "components": [{"sports": ["football"], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1}],
                "montante": {"initial_stake": 10, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

# CIBLE 100→300 (×3) : 2p×1.732, 3p×1.442, 4p×1.316, 5p×1.246, 6p×1.201
for n_p, cmin, cmax, target_tag in [
    (2, 1.65, 1.80, "100to300_2p"),
    (3, 1.40, 1.50, "100to300_3p"),
    (4, 1.28, 1.36, "100to300_4p"),
    (5, 1.22, 1.30, "100to300_5p"),
    (6, 1.18, 1.24, "100to300_6p"),
]:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5",
                "1x2,over_1_5,over_2_5,btts"]:
        for mwr in [0.55, 0.60, 0.65, 0.70, 0.75]:
            CANDS.append({
                "id": f"FXMK_{target_tag}_p{n_p}_wr{mwr}_{mkt[:8]}",
                "_target": 300, "_initial": 100,
                "components": [{"sports": ["football"], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1}],
                "montante": {"initial_stake": 100, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

# CIBLE 100→500 (×5) : 3p×1.71, 4p×1.495, 5p×1.380, 6p×1.308, 7p×1.258
for n_p, cmin, cmax, target_tag in [
    (3, 1.65, 1.78, "100to500_3p"),
    (4, 1.42, 1.55, "100to500_4p"),
    (5, 1.32, 1.42, "100to500_5p"),
    (6, 1.25, 1.34, "100to500_6p"),
    (7, 1.22, 1.30, "100to500_7p"),
]:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5",
                "1x2,over_1_5,over_2_5,btts"]:
        for mwr in [0.55, 0.60, 0.65, 0.70, 0.75]:
            CANDS.append({
                "id": f"FXMK_{target_tag}_p{n_p}_wr{mwr}_{mkt[:8]}",
                "_target": 500, "_initial": 100,
                "components": [{"sports": ["football"], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1}],
                "montante": {"initial_stake": 100, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[FXMK all targets] {len(CANDS)} configs")

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

import math
# Pour chaque target, top par score = compl × ln(volume)
existing_records = {
    100: {"compl": 60, "n": 5, "name": "CHALLENGE_10_TO_100"},
    300: {"compl": 53, "n": 17, "name": "CHALLENGE_100_TO_300"},
    500: {"compl": 71, "n": 7, "name": "CHALLENGE_100_TO_500"},
}
for tgt in [100, 300, 500]:
    er = existing_records[tgt]
    sub = [r for r in results if r["target"] == tgt and r["cap"] >= tgt * 0.85]
    sub.sort(key=lambda r: -(r["compl"] * math.log(max(r["n_total"], 2))))
    print(f"\n=== TARGET {tgt}€ — TOP par SCORE compl×log(vol) (record actuel: compl {er['compl']}% sur {er['n']} cycles) ===")
    for r in sub[:15]:
        better_compl = r["compl"] > er["compl"]
        better_vol = r["n_total"] > er["n"]
        flag = " 🏆🏆" if better_compl and better_vol else (" 🏆" if better_compl or better_vol else "")
        print(f"  Compl {r['compl']:>4.0f}% | #{r['n_total']:>3d} cycles | cap {r['cap']:>4.0f}€ | P5 {r['prob_5']:>5.1f}% | {r['id'][:55]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/foot_xmkt_all_targets.json","w") as f:
    json.dump({"all": results}, f, indent=2)
print("\nSaved.")
