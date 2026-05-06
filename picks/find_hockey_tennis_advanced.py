#!/usr/bin/env python3
"""Hockey multi-leagues combinés + ATP/WTA séparés + combos legs=2 avec ligues."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# Hockey multi-ligues européennes
HOCKEY_COMBOS = [
    (["nhl", "khl"], "NHL_KHL"),
    (["nhl", "shl", "del"], "NHL_SHL_DEL"),
    (["nhl", "khl", "shl", "del", "national league", "liiga"], "ALL_HOCKEY"),
    (["shl", "del", "liiga", "national league"], "EU_HOCKEY"),
    (["national league"], "NL_CH"),
    (["liiga"], "LIIGA_FI"),
]
for incl, sname in HOCKEY_COMBOS:
    for cmin, cmax in [(1.20,1.40), (1.30,1.55), (1.40,1.65), (1.50,1.80)]:
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

# ATP vs WTA distinct
TENNIS_TYPES = [
    (["atp"], "ATP"),
    (["wta"], "WTA"),
    (["atp masters"], "ATP_M"),
    (["wta 1000"], "WTA1000"),
]
for incl, sname in TENNIS_TYPES:
    for cmin, cmax in [(1.10,1.25), (1.20,1.40), (1.30,1.55), (1.40,1.65), (1.50,1.80)]:
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

# Combos legs=2 sur ligues filtrées
COMBO_LEAGUES = [
    (["premier league"], "PL"),
    (["bundesliga"], "BUND"),
    (["la liga"], "LIGA"),
    (["serie a"], "SA"),
    (["nba"], "NBA"),
    (["nhl"], "NHL"),
    (["eredivisie"], "ERED"),
]
for incl, sname in COMBO_LEAGUES:
    for cmin, cmax in [(1.10,1.25), (1.15,1.30), (1.20,1.35)]:
        for mwr in [0.70, 0.75, 0.80]:
            for n_p in [2, 3]:
                for sort in ["wr", "ev"]:
                    sport = "basketball" if sname == "NBA" else ("ice-hockey" if sname == "NHL" else "football")
                    CANDS.append({
                        "id": f"C2_{sname}_{cmin}-{cmax}_wr{int(mwr*100)}_p{n_p}_{sort}_legs2",
                        "incl": incl,
                        "components": [{"sports": [sport], "market": "1x2,btts,over_1_5,over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 2}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 2},
                    })

print(f"[adv] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 200 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s["incl"])
        if r["n_cycles_total"] >= 12 and r["final_pnl"] > 400:
            results.append({
                "id": s["id"], "incl": s["incl"][0],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[adv] {len(results)} viable")
results.sort(key=lambda r: -r["pnl"])
print(f"\n=== TOP 25 par PnL ===")
print(f"  {'league':<22} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:25]:
    print(f"  {r['incl']:<22} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_hockey_tennis_advanced.json","w") as f: json.dump(results,f,indent=2)
print("\nSaved")
