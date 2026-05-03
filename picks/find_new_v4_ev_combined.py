#!/usr/bin/env python3
"""EV strict + WR strict combinés sur foot+hockey — angle peu testé."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# A. Sort par EV avec min_ev élevé, WR strict
for foot_ev in [1.05, 1.10, 1.15, 1.20]:
    for hockey_ev in [1.05, 1.10, 1.15]:
        for foot_wr in [0.65, 0.70]:
            for hockey_wr in [0.65, 0.70]:
                for f_mc in [3, 5]:
                    for h_mc in [3, 5]:
                        for pct in [0.05, 0.07, 0.10]:
                            CANDS.append({
                                "id": f"EVS_F_ev{foot_ev}wr{foot_wr}_H_ev{hockey_ev}wr{hockey_wr}_F{f_mc}H{h_mc}_pct{int(pct*100)}",
                                "components": [
                                    {"sport": "football", "market": "btts,over_1_5,over_2_5",
                                     "cote_min": 1.20, "cote_max": 1.50,
                                     "sort_by": "ev", "max_legs": 1, "max_combos": f_mc,
                                     "min_wr": foot_wr, "min_ev": foot_ev},
                                    {"sport": "ice-hockey", "market": "1x2",
                                     "cote_min": 1.20, "cote_max": 1.60,
                                     "sort_by": "ev", "max_legs": 1, "max_combos": h_mc,
                                     "min_wr": hockey_wr, "min_ev": hockey_ev},
                                ],
                                "dedup": "max1",
                                "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                            })

# B. Foot xmkt seul avec EV strict + WR strict
for ev_min in [1.05, 1.10, 1.15, 1.20, 1.25]:
    for wr_min in [0.60, 0.65, 0.70]:
        for cmin, cmax in [(1.20, 1.40), (1.20, 1.50), (1.20, 1.60)]:
            for mc in [3, 5, 8]:
                for pct in [0.05, 0.07, 0.10]:
                    CANDS.append({
                        "id": f"EVF_xmkt_{cmin}-{cmax}_ev{ev_min}wr{wr_min}_mc{mc}_pct{int(pct*100)}",
                        "components": [{
                            "sport": "football", "market": "btts,over_1_5,over_2_5",
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": "ev", "max_legs": 1, "max_combos": mc,
                            "min_wr": wr_min, "min_ev": ev_min,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    })

print(f"[EV combined] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
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
print(f"\n=== TOP 15 par RATIO (record actuel 24.4×) ===")
for r in results[:15]:
    flag = " 🏆" if r["ratio"] > 24.4 else ""
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:60]}{flag}")

# Tri par BR mult
results.sort(key=lambda r: -r["br_mult"])
print(f"\n=== TOP 15 par BR mult (record actuel BR×336/JACKPOT BR×517) ===")
for r in results[:15]:
    flag = " 🏆" if r["br_mult"] > 517 else (" 🥈" if r["br_mult"] > 336 else "")
    print(f"  BR×{r['br_mult']:>6.1f} ratio {r['ratio']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:60]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/new_v4_ev.json","w") as f:
    json.dump({"all": results, "top_ratio": sorted(results, key=lambda r:-r["ratio"])[:30],
               "top_br": sorted(results, key=lambda r:-r["br_mult"])[:30]}, f, indent=2)
print("\nSaved.")
