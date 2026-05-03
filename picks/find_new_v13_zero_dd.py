#!/usr/bin/env python3
"""Profils montantes avec completion 100% sur S1 (zéro cycle échoué)."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"), ("Apr", "2026-04-01", "2026-04-30")]

# Configs ultra-conservatives : peu de paliers + cote très basse + WR très haut
CANDS = []

for n_p in [2, 3]:
    for cmin, cmax in [(1.05, 1.15), (1.08, 1.18), (1.10, 1.20), (1.10, 1.25), (1.15, 1.25), (1.15, 1.30), (1.20, 1.30)]:
        for sport, mkt in [("football", "over_1_5"), ("football", "over_1_5,over_2_5"),
                            ("football", "btts,over_1_5,over_2_5"), ("ice-hockey", "1x2")]:
            for mwr in [0.75, 0.80, 0.85, 0.90]:
                CANDS.append({
                    "id": f"ZDD_{sport[:3]}_{mkt[:5]}_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                    "label": "Zero DD montante",
                    "components": [{"sports": [sport], "market": mkt,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                        "min_wr": mwr, "min_ev": None, "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

print(f"[Zero DD] {len(CANDS)} configs")
results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
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
        results.append({"id": s["id"], "perfs": perfs, "strat": s})

# Filtre : completion 100% ET n_cycles >= 5
def s1(r): return r["perfs"]["S1-26"]
viable = [r for r in results if s1(r)["compl"] >= 95 and s1(r)["n_total"] >= 5]
viable.sort(key=lambda r: (-s1(r)["compl"], -s1(r)["pnl"]))

print(f"\n[Zero DD] {len(viable)} viables (compl ≥95% ET n_cycles ≥5)")
print("=== TOP 20 par COMPLETION ===")
for r in viable[:20]:
    s = s1(r)
    apr = r["perfs"].get("Apr") or {"pnl":0}
    flag = " 🏆" if s["compl"] == 100.0 else ""
    print(f"  Compl {s['compl']:>5.1f}% | +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ #{s['n_complete']}/{s['n_total']} | Apr {apr['pnl']:+5.0f}€ | {r['id'][:60]}{flag}")

# Top par n_total (volume) avec compl 100%
v100 = [r for r in viable if s1(r)["compl"] == 100.0]
v100.sort(key=lambda r: -s1(r)["n_total"])
print(f"\n=== TOP par VOLUME (compl 100%) ===")
for r in v100[:15]:
    s = s1(r)
    apr = r["perfs"].get("Apr") or {"pnl":0}
    print(f"  #{s['n_total']:>2d} cycles | +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ | Apr {apr['pnl']:+5.0f}€ | {r['id'][:60]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v13_zero_dd.json","w") as f:
    json.dump({"viable": viable[:50], "perfect_100": v100[:30]}, f, indent=2)
print("\nSaved.")
