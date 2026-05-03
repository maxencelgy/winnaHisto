#!/usr/bin/env python3
"""Narrow ULTRA-étroit + WR strict ≥75% — pousser le profil DD59 encore plus loin."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Narrow ULTRA-étroit + WR strict ≥75%
for cmin, cmax in [(1.15, 1.25), (1.18, 1.25), (1.18, 1.28), (1.20, 1.27),
                    (1.20, 1.28), (1.20, 1.30), (1.22, 1.30), (1.22, 1.32)]:
    for foot_wr in [0.70, 0.75, 0.80]:
        for hockey_wr in [0.70, 0.75, 0.80]:
            for f_mc, h_mc in [(3, 5), (3, 8), (5, 5), (5, 8)]:
                for pct in [0.05, 0.07, 0.10, 0.12, 0.15]:
                    CANDS.append({
                        "id": f"NX_{cmin}-{cmax}_fw{foot_wr}_hw{hockey_wr}_F{f_mc}H{h_mc}_pct{int(pct*100)}",
                        "components": [
                            {"sport": "football", "market": "btts,over_1_5,over_2_5",
                             "cote_min": cmin, "cote_max": cmax,
                             "sort_by": "wr", "max_legs": 1, "max_combos": f_mc,
                             "min_wr": foot_wr, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": cmin, "cote_max": cmax,
                             "sort_by": "wr", "max_legs": 1, "max_combos": h_mc,
                             "min_wr": hockey_wr, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

# B. Narrow foot SEUL ultra-étroit
for cmin, cmax in [(1.15, 1.25), (1.18, 1.28), (1.20, 1.30)]:
    for mc in [3, 5, 8, 12]:
        for mwr in [0.70, 0.75, 0.80]:
            for pct in [0.05, 0.07, 0.10, 0.15]:
                CANDS.append({
                    "id": f"NXFOO_{cmin}-{cmax}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                    "components": [{"sport": "football", "market": "btts,over_1_5,over_2_5",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None}],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

print(f"[NX extreme] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 80 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        results.append({"id": s["id"], "strat": s, "pnl": round(sm["pnl"],1),
            "br_mult": round(sm["bankroll_final"]/100,2), "dd": round(sm["dd_max"],1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1),2), "n_combos": sm["n_combos"]})
    except: pass

# Tri par ratio
results.sort(key=lambda r: -r["ratio"])
print(f"\n=== TOP 25 par RATIO (record 24.4×, NEW DD59 = 18.3×) ===")
for r in results[:25]:
    flag = " 🏆🏆" if r["ratio"] > 24.4 else (" 🏆" if r["ratio"] > 18.3 else "")
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

# Tri par DD le plus bas (pour battre DD 59€)
ddok = [r for r in results if r["pnl"] >= 200 and r["br_mult"] >= 2]
ddok.sort(key=lambda r: r["dd"])
print(f"\n=== TOP 10 par DD le plus bas (record DD 59€, pnl≥200, BR≥2) ===")
for r in ddok[:10]:
    flag = " 🏆" if r["dd"] < 59 else ""
    print(f"  DD {r['dd']:>4.0f}€ ratio {r['ratio']:>5.1f} BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v10_nx.json","w") as f:
    json.dump({"top_ratio": sorted(results, key=lambda r:-r["ratio"])[:30],
               "top_dd_low": sorted(ddok, key=lambda r:r["dd"])[:30]}, f, indent=2)
print("\nSaved.")
