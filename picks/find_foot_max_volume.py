#!/usr/bin/env python3
"""Foot uniquement (matchs dispo tous les jours), MAX VOLUME — battre les 93 cycles du HIGH_VOL."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

# Pour MAX volume : cote large + WR moins strict (mais cap reste ≥ target)
CANDS = []

# Pour 100→200, on cherche cycles courts (2-4 paliers) + foot uniquement
configs = [
    # 2 paliers ×1.42 → 200€ - MAX VOLUME (cote large + WR plus tolerant)
    (2, 1.40, 1.50, "2p_145_wide"),
    (2, 1.38, 1.55, "2p_146_wider"),
    (2, 1.40, 1.55, "2p_147_widest"),
    # 3 paliers ×1.26
    (3, 1.22, 1.30, "3p_126_wide"),
    (3, 1.20, 1.32, "3p_126_wider"),
    (3, 1.20, 1.35, "3p_127_widest"),
    # 4 paliers ×1.19
    (4, 1.16, 1.22, "4p_119"),
    (4, 1.15, 1.25, "4p_120_wider"),
    # 5 paliers ×1.149
    (5, 1.12, 1.18, "5p_115"),
    (5, 1.10, 1.20, "5p_115_wider"),
    # 6 paliers ×1.122
    (6, 1.10, 1.17, "6p_113"),
    (6, 1.08, 1.18, "6p_113_wider"),
]

for n_p, cmin, cmax, tag in configs:
    for mkt in ["over_1_5", "over_1_5,over_2_5", "btts,over_1_5,over_2_5",
                "1x2,over_1_5,over_2_5,btts"]:
        for mwr in [0.60, 0.65, 0.70, 0.75, 0.80]:
            CANDS.append({
                "id": f"FMV_{tag}_p{n_p}_wr{mwr}_{mkt[:8]}",
                "label": "Foot Max Volume",
                "components": [{
                    "sports": ["football"], "market": mkt,
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": 100, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[FMV] {len(CANDS)} configs")
results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=100, excluded_leagues=WFR_EXCL)
            perfs[pname] = {"compl": round(r["completion_rate"]*100,1),
                "avg_cap": round(r["avg_capital_complete"],1),
                "n_total": r["n_cycles_total"],
                "n_complete": r["n_cycles_complete"],
                "pnl": round(r["final_pnl"],1)}
        except: perfs[pname] = None
    if perfs.get("S1-26"):
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

# Critère : cap ≥ 180€ (proche 200€) ET completion ≥ 50% ET volume ≥ 50 cycles
viable = [r for r in results if r["cap"] >= 180 and r["compl"] >= 50 and r["n_total"] >= 50]
# Tri prioritaire : score = compl × ln(n_total) (favorise compl haute + volume haut)
import math
viable.sort(key=lambda r: -(r["compl"] * math.log(r["n_total"])))

print(f"\n[FMV] {len(viable)} viables (cap≥180€, compl≥50%, vol≥50 cycles)")
print(f"\n=== TOP 25 par SCORE COMPL × LOG(VOLUME) ===")
for r in viable[:25]:
    flag = " 🏆🏆" if r["n_total"] > 93 else (" 🏆" if r["n_total"] > 50 else "")
    print(f"  Compl {r['compl']:>4.0f}% | #{r['n_total']:>3d} cycles | cap {r['cap']:>4.0f}€ | P3 {r['prob_3']:>5.1f}% P5 {r['prob_5']:>5.1f}% | {r['id'][:55]}{flag}")

# Tri par volume max
viable_vol = [r for r in results if r["cap"] >= 180 and r["compl"] >= 55]
viable_vol.sort(key=lambda r: -r["n_total"])
print(f"\n=== TOP 15 par VOLUME ABSOLU (compl ≥55%) ===")
for r in viable_vol[:15]:
    flag = " 🏆🏆" if r["n_total"] > 93 else ""
    print(f"  #{r['n_total']:>3d} cycles | compl {r['compl']:>4.0f}% | cap {r['cap']:>4.0f}€ | P5 {r['prob_5']:>5.1f}% | {r['id'][:55]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/foot_max_volume.json","w") as f:
    json.dump({"viable": viable[:50], "by_volume": viable_vol[:30]}, f, indent=2)
print("\nSaved.")
