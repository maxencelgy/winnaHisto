#!/usr/bin/env python3
"""TOP 5 LIGUES INDIVIDUELLES isolées : Premier League, La Liga, Serie A, Bundesliga, Ligue 1.
Plus chaque ligue européenne majeure individuellement.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

LEAGUES = [
    (["premier league"], "PL"),
    (["la liga"], "LIGA"),
    (["serie a"], "SA"),
    (["bundesliga"], "BUND"),
    (["ligue 1"], "L1"),
    (["championship"], "CHAMP"),
    (["serie b"], "SB"),
    (["ligue 2"], "L2"),
    (["la liga 2"], "LIGA2"),
    (["bundesliga 2", "2. bundesliga"], "BL2"),
]

for incl, sname in LEAGUES:
    for mkt in ["1x2", "1x2,btts,over_1_5,over_2_5", "btts", "over_2_5", "over_1_5"]:
        for cmin, cmax in [(1.20,1.40), (1.30,1.50), (1.40,1.60), (1.50,1.80), (1.60,2.00), (1.30,1.55)]:
            for mwr in [None, 0.55, 0.60, 0.65, 0.70]:
                for n_p in [1, 2, 3]:
                    for sort in ["wr", "ev"]:
                        CANDS.append({
                            "id": f"T5_{sname}_{mkt[:3]}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                            "incl": incl,
                            "components": [{"sports": ["football"], "market": mkt,
                                            "cote_min": cmin, "cote_max": cmax,
                                            "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                            "min_wr": mwr, "min_ev": None,
                                            "legs_per_palier": 1}],
                            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                          "combo_legs_per_palier": 1},
                        })

print(f"[top5_iso] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 300 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s["incl"])
        if r["n_cycles_total"] >= 12 and r["final_pnl"] > 500:
            results.append({
                "id": s["id"], "incl": s["incl"][0],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[top5_iso] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 25 par PnL ===")
print(f"  {'league':<22} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:25]:
    print(f"  {r['incl']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top par ligue (best per league)
by_league = {}
for r in results:
    by_league.setdefault(r["incl"], []).append(r)
print(f"\n=== BEST par LIGUE ===")
for lg, group in sorted(by_league.items()):
    group.sort(key=lambda r: -r["pnl"])
    if group:
        r = group[0]
        score = r["comp"] * r["cap"] * r["n_tot"]/100
        print(f"  {lg:<22} score={score:>5.0f}  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_top5_isolated.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
