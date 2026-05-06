#!/usr/bin/env python3
"""Niches spécifiques jamais explorées :
  - Tennis Grand Slams isolated (Roland-Garros, Wimbledon, US, AUS)
  - NHL Playoffs vs regular season
  - Hockey deep dive (KHL, NHL, NL, SHL...)
  - Tennis ATP Masters 1000 only
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# Tennis Grand Slams
TENNIS_LEAGUES = [
    (["atp roland garros", "wta roland garros", "roland garros"], "RG"),
    (["wimbledon"], "WIMB"),
    (["us open", "us-open"], "USO"),
    (["australian open"], "AO"),
    (["atp masters 1000", "wta 1000"], "M1000"),
    (["atp masters", "atp 1000"], "ATP_M"),
    (["atp", "wta"], "ATP_WTA_ALL"),
    (["challenger", "itf"], "CHALL_ITF"),
]
for incl, sname in TENNIS_LEAGUES:
    for cmin, cmax in [(1.10,1.25), (1.20,1.40), (1.30,1.50), (1.50,1.80), (1.70,2.00)]:
        for mwr in [None, 0.65, 0.70, 0.75]:
            for n_p in [1, 2, 3]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"T_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                        "incl": incl,
                        "components": [{"sports": ["tennis"], "market": "1x2",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

# Hockey deep dive
HOCKEY_LEAGUES = [
    (["nhl"], "NHL"),
    (["nhl, playoffs", "nhl playoffs"], "NHL_PO"),
    (["khl"], "KHL"),
    (["national league"], "NL"),
    (["shl", "swedish hockey"], "SHL"),
    (["liiga", "finnish"], "LIIGA"),
    (["del", "deutsche eishockey"], "DEL"),
    (["ligue magnus"], "MAGNUS"),
    (["extraliga"], "EXTRA"),
]
for incl, sname in HOCKEY_LEAGUES:
    for cmin, cmax in [(1.20,1.40), (1.30,1.55), (1.50,1.80), (1.70,2.00)]:
        for mwr in [None, 0.55, 0.60, 0.65]:
            for n_p in [1, 2, 3]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"H_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                        "incl": incl,
                        "components": [{"sports": ["ice-hockey"], "market": "1x2",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

# NBA Playoffs vs regular season
BASKET_LEAGUES = [
    (["nba, playoffs", "nba playoffs"], "NBA_PO"),
    (["nba"], "NBA"),
    (["euroleague"], "EUROLEAGUE"),
    (["liga acb", "acb"], "ACB"),
]
for incl, sname in BASKET_LEAGUES:
    for cmin, cmax in [(1.20,1.40), (1.30,1.55), (1.50,1.80), (1.70,2.00)]:
        for mwr in [None, 0.55, 0.60, 0.65]:
            for n_p in [1, 2, 3]:
                for sort in ["wr", "ev"]:
                    CANDS.append({
                        "id": f"B_{sname}_{cmin}-{cmax}_wr{mwr}_p{n_p}_{sort}",
                        "incl": incl,
                        "components": [{"sports": ["basketball"], "market": "1x2",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

print(f"[niche] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s["incl"])
        if r["n_cycles_total"] >= 12 and r["final_pnl"] > 300:
            results.append({
                "id": s["id"], "incl": s["incl"][0],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[niche] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 25 par PnL ===")
print(f"  {'league':<22} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:25]:
    print(f"  {r['incl']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

results.sort(key=lambda r: -(r["comp"] * r["cap"] * r["n_tot"]/100))
print(f"\n=== TOP 15 par SCORE ===")
for r in results[:15]:
    score = r["comp"] * r["cap"] * r["n_tot"]/100
    print(f"  score={score:>5.0f} {r['incl']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} cap{r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_niche_specific.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
