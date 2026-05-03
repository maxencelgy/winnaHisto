#!/usr/bin/env python3
"""Foot 1x2 isolé WR strict — angle non testé seul (toujours en xmkt avant)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

# === Classique foot 1x2 isolé WR strict ===
print("=== FOOT 1X2 CLASSIQUE WR strict ===")
CL = []
for cmin, cmax in [(1.30, 1.50), (1.30, 1.60), (1.40, 1.60), (1.40, 1.70), (1.50, 1.80), (1.60, 1.90)]:
    for mc in [3, 5, 8]:
        for mwr in [0.65, 0.70, 0.75]:
            for pct in [0.05, 0.07, 0.10]:
                CL.append({
                    "id": f"F1X2_{cmin}-{cmax}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                    "components": [{"sport": "football", "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None}],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })
print(f"[F1X2 CL] {len(CL)} configs")
cl_results = []
for i, s in enumerate(CL):
    if i % 30 == 0: print(f"  [{i}/{len(CL)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        cl_results.append({"id": s["id"], "strat": s, "pnl": round(sm["pnl"],1),
            "br_mult": round(sm["bankroll_final"]/100,2), "dd": round(sm["dd_max"],1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1),2), "n_combos": sm["n_combos"]})
    except: pass
cl_v = [r for r in cl_results if r["ratio"] >= 5]
cl_v.sort(key=lambda r: -r["ratio"])
print(f"[F1X2 CL] {len(cl_v)} viables (ratio≥5)")
print("=== TOP 15 par RATIO ===")
for r in cl_v[:15]:
    flag = " 🏆" if r["ratio"] > 24.4 else ""
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}{flag}")

# === Montantes foot 1x2 ===
print("\n=== FOOT 1X2 MONTANTES ===")
MT = []
for cmin, cmax in [(1.30, 1.55), (1.40, 1.65), (1.50, 1.75), (1.60, 1.85)]:
    for n_p in [3, 4, 5]:
        for mwr in [0.65, 0.70, 0.75]:
            MT.append({
                "id": f"F1X2_MT_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                "label": "Foot 1x2 montante",
                "components": [{"sports": ["football"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None, "legs_per_palier": 1}],
                "montante": {"initial_stake": 10, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })
print(f"[F1X2 MT] {len(MT)} configs")
mt_results = []
for i, s in enumerate(MT):
    if i % 12 == 0: print(f"  [{i}/{len(MT)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=10, excluded_leagues=WFR_EXCL)
            perfs[pname] = {"compl": round(r["completion_rate"]*100,1),
                "avg_cap": round(r["avg_capital_complete"],1),
                "n_total": r["n_cycles_total"], "pnl": round(r["final_pnl"],1)}
        except: perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 5:
        mt_results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}
mt_v = [r for r in mt_results if s1(r)["compl"] >= 40 and s1(r)["pnl"] >= 50]
mt_v.sort(key=lambda r: -s1(r)["compl"])
print(f"[F1X2 MT] {len(mt_v)} viables")
print("=== TOP 15 par COMPLETION ===")
for r in mt_v[:15]:
    s = s1(r); a = apr(r)
    flag = " 🏆" if s["compl"] > 77 else ""
    print(f"  Compl {s['compl']:>5.1f}% | +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ #{s['n_total']} | Apr {a['pnl']:+5.0f}€ | {r['id'][:55]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v5_f1x2.json","w") as f:
    json.dump({"classique": cl_v[:30], "montantes": mt_v[:30]}, f, indent=2)
print("\nSaved.")
