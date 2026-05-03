#!/usr/bin/env python3
"""Narrow cote 1.20-1.30 + 3 sports F+H+B — extension du profil DD22 vers + de volume."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Narrow 3 sports F+H+B
for cmin, cmax in [(1.18, 1.28), (1.20, 1.28), (1.20, 1.30)]:
    for foot_wr in [0.70, 0.75, 0.80]:
        for hockey_wr in [0.70, 0.75]:
            for basket_wr in [0.65, 0.70, 0.75]:
                for f_mc, h_mc, b_mc in [(3, 5, 1), (3, 5, 2), (3, 8, 1), (5, 5, 1), (5, 5, 2)]:
                    for pct in [0.05, 0.07, 0.10]:
                        CANDS.append({
                            "id": f"NX3_{cmin}-{cmax}_fw{foot_wr}_hw{hockey_wr}_bw{basket_wr}_F{f_mc}H{h_mc}B{b_mc}_pct{int(pct*100)}",
                            "components": [
                                {"sport": "football", "market": "btts,over_1_5,over_2_5",
                                 "cote_min": cmin, "cote_max": cmax,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": f_mc,
                                 "min_wr": foot_wr, "min_ev": None},
                                {"sport": "ice-hockey", "market": "1x2",
                                 "cote_min": cmin, "cote_max": cmax,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": h_mc,
                                 "min_wr": hockey_wr, "min_ev": None},
                                {"sport": "basketball", "market": "1x2",
                                 "cote_min": cmin, "cote_max": cmax,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": b_mc,
                                 "min_wr": basket_wr, "min_ev": None},
                            ],
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                        })

print(f"[NX3] {len(CANDS)} configs")

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

results.sort(key=lambda r: -r["ratio"])
print(f"\n=== TOP 20 par RATIO (record 24.4× / DD24=16.2× / DD22=13.2×) ===")
for r in results[:20]:
    flag = " 🏆" if r["ratio"] > 24.4 else (" 🥈" if r["ratio"] > 18.3 else "")
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

ddok = [r for r in results if r["pnl"] >= 200 and r["br_mult"] >= 2]
ddok.sort(key=lambda r: r["dd"])
print(f"\n=== TOP 10 par DD le plus bas (record 22€) ===")
for r in ddok[:10]:
    flag = " 🏆" if r["dd"] < 22 else ""
    print(f"  DD {r['dd']:>4.0f}€ ratio {r['ratio']:>5.1f} BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ #{r['n_combos']:>3d} | {r['id'][:65]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v12_nx3.json","w") as f:
    json.dump({"top_ratio": sorted(results, key=lambda r:-r["ratio"])[:30],
               "top_dd": sorted(ddok, key=lambda r:r["dd"])[:30]}, f, indent=2)
print("\nSaved.")
