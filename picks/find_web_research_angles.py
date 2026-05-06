#!/usr/bin/env python3
"""Sweep angles issus de la recherche web (Reddit/Buchdahl/Boydsbets):
  E. Draw bias Ligue 2 / BL2 / Belgian Pro cote 3.2-4.0
  F. ITF Challenger underdog tennis cote 2.0-3.5
  G. BTTS Yes Bundesliga/Eredivisie/Championship cote 1.6-1.85
  H. Under 2.5 Serie A/Ligue 1 défensif cote 1.7-2.0
  I. Hockey underdog 2.4-3.2 (puck line proxy via 1x2)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 100
START, END = "2026-01-01", "2026-04-30"

CANDS = []

# E. DRAW bias ligues "weak" — Ligue 2, Belgian Pro, BL2
DRAW_LEAGUES = [
    (["ligue 2"], "L2"),
    (["bundesliga 2", "2 bundesliga", "2. bundesliga"], "BL2"),
    (["jupiler", "belgian"], "BEL"),
    (["championship"], "CHAMP"),
    (["eredivisie"], "ERED"),
    (["serie b"], "SB"),
    (["ligue 2", "bundesliga 2", "championship", "serie b", "jupiler"], "L2_BL2_CHAMP_SB_BEL"),
]
for incl, sname in DRAW_LEAGUES:
    for cmin, cmax in [(3.0,3.6), (3.2,4.0), (3.4,4.2), (3.0,4.5)]:
        for n_p in [1, 2, 3]:
            for sort in ["wr", "ev"]:
                CANDS.append({
                    "id": f"E_DRAW_{sname}_{cmin}-{cmax}_p{n_p}_{sort}",
                    "kind": "E_DRAW_L2",
                    "incl": incl,
                    "components": [{"sports": ["football"], "market": "1x2",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": None, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# F. Tennis underdog (proxy ITF — pas de filtre tournament en data, on prend toutes cotes 2.0-3.5)
for cmin, cmax in [(1.80,2.50), (2.00,3.00), (2.20,3.20), (2.50,3.50)]:
    for n_p in [1, 2]:
        for sort in ["wr", "ev"]:
            for mwr in [None, 0.40, 0.45]:
                CANDS.append({
                    "id": f"F_TENNIS_UD_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                    "kind": "F_TENNIS_UD",
                    "incl": None,
                    "components": [{"sports": ["tennis"], "market": "1x2",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

# G. BTTS Yes ligues "BTTS-friendly" — Bundesliga, Eredivisie, Championship
BTTS_LEAGUES = [
    (["bundesliga"], "BUND"),  # match aussi BL2 sauf si on filtre
    (["eredivisie"], "ERED"),
    (["championship"], "CHAMP"),
    (["bundesliga", "eredivisie", "championship"], "BUND_ERED_CHAMP"),
]
for incl, sname in BTTS_LEAGUES:
    for cmin, cmax in [(1.55,1.75), (1.60,1.85), (1.65,1.90), (1.70,2.00)]:
        for n_p in [1, 2, 3]:
            for sort in ["wr", "ev"]:
                for mwr in [None, 0.55, 0.60]:
                    CANDS.append({
                        "id": f"G_BTTS_{sname}_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                        "kind": "G_BTTS_LEAGUE",
                        "incl": incl,
                        "components": [{"sports": ["football"], "market": "btts",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

# H. Under 2.5 ligues défensives — Serie A, Ligue 1, Greek SL
DEF_LEAGUES = [
    (["serie a"], "SA"),
    (["ligue 1"], "L1"),
    (["greek", "super league"], "GSL"),
    (["serie a", "ligue 1"], "SA_L1"),
    (["serie a", "ligue 1", "greek"], "SA_L1_GSL"),
]
for incl, sname in DEF_LEAGUES:
    for cmin, cmax in [(1.55,1.80), (1.60,1.85), (1.70,2.00), (1.80,2.10)]:
        for n_p in [1, 2, 3]:
            for sort in ["wr", "ev"]:
                for mwr in [None, 0.50, 0.55]:
                    CANDS.append({
                        "id": f"H_U25_{sname}_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                        "kind": "H_UNDER25_DEF",
                        "incl": incl,
                        "components": [{"sports": ["football"], "market": "over_2_5",
                                        "cote_min": cmin, "cote_max": cmax,
                                        "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                        "min_wr": mwr, "min_ev": None,
                                        "legs_per_palier": 1}],
                        "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                      "combo_legs_per_palier": 1},
                    })

# I. Hockey underdog 1x2 cote 2.4-3.2
for cmin, cmax in [(2.0,2.8), (2.2,3.0), (2.4,3.2), (2.5,3.5)]:
    for n_p in [1, 2]:
        for sort in ["wr", "ev"]:
            for mwr in [None, 0.40, 0.45]:
                CANDS.append({
                    "id": f"I_HOCKEY_UD_{cmin}-{cmax}_p{n_p}_wr{mwr}_{sort}",
                    "kind": "I_HOCKEY_UD",
                    "incl": None,
                    "components": [{"sports": ["ice-hockey"], "market": "1x2",
                                    "cote_min": cmin, "cote_max": cmax,
                                    "sort_by": sort, "max_legs": 1, "max_combos": 1,
                                    "min_wr": mwr, "min_ev": None,
                                    "legs_per_palier": 1}],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": 1},
                })

print(f"[web_angles] {len(CANDS)} configs")

results = []
for i, s in enumerate(CANDS):
    if i % 100 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = simulate(s, START, END, mode="intraday", initial_stake=INITIAL,
                      included_leagues=s.get("incl"))
        if r["n_cycles_total"] >= 15:
            results.append({
                "id": s["id"], "kind": s["kind"],
                "comp": r["completion_rate"], "n_comp": r["n_cycles_complete"],
                "n_tot": r["n_cycles_total"], "cap": r["avg_capital_complete"],
                "pnl": r["final_pnl"],
            })
    except Exception:
        pass

print(f"\n[web_angles] {len(results)} viable (≥15 cycles)")

def score(r): return r["comp"] * r["cap"]
results.sort(key=lambda r: -r["pnl"])

print(f"\n=== TOP 20 par PnL ===")
print(f"  {'kind':<18} {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
for r in results[:20]:
    print(f"  {r['kind']:<18} {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

# Top par kind
for kind in ["E_DRAW_L2", "F_TENNIS_UD", "G_BTTS_LEAGUE", "H_UNDER25_DEF", "I_HOCKEY_UD"]:
    sub = [r for r in results if r["kind"] == kind]
    sub.sort(key=lambda r: -r["pnl"])
    print(f"\n=== TOP 5 {kind} ===")
    print(f"  {'compl%':>6} {'n_c/tot':>8} {'cap€':>5} {'pnl€':>7}  id")
    for r in sub[:5]:
        print(f"  {r['comp']*100:>5.1f}% {r['n_comp']:>3}/{r['n_tot']:<4} {r['cap']:>4.0f} {r['pnl']:>+6.0f}  {r['id']}")

with open("/tmp/find_web_research_angles.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved /tmp/find_web_research_angles.json")
