#!/usr/bin/env python3
"""Sweep v4 — axes vraiment inexplorés.

A. Combos 2j multi-sport (foot + hockey en 2 jambes différentes du combo)
B. Combos 2j foot avec min_wr stricte sur chaque jambe
C. Multi-market triple (1x2 + BTTS + Over/Under) sur foot
D. Volume ULTRA haut (15+ picks/j) avec sizing 1-2%
E. Hockey + Basket only (pas de foot — décorrélé)
F. Multi-composantes avec sizing différent par composante (pas faisable directement, on simule via plusieurs strats avec différents sizes)
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

PERIODS = [
    ("Q1-25", "2025-01-01", "2025-03-31"),
    ("Q2-25", "2025-04-01", "2025-06-30"),
    ("Q3-25", "2025-07-01", "2025-09-30"),
    ("Q4-25", "2025-10-01", "2025-12-31"),
    ("Q1-26", "2026-01-01", "2026-03-31"),
    ("Apr26", "2026-04-01", "2026-04-30"),
]

candidates = []

# === A. Combos 2j multi-sport (1 jambe foot + 1 jambe hockey, etc) ===
for cmin, cmax in [(2.0, 3.0), (2.5, 4.0), (3.0, 5.0)]:
    for sort in ["wr", "ev"]:
        for mc in [1, 2]:
            for mwr in [None, 0.55, 0.60]:
                # Foot + Hockey combo 2j
                s = {
                    "id": f"C2_FH_{cmin}-{cmax}_{sort}_mc{mc}_wr{mwr}",
                    "label": "combo_2j_foot_hockey",
                    "components": [{
                        "sports": ["football", "ice-hockey"], "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": 2, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "risk_tiered", "min_stake": 0.5,
                               "tiers": [{"cote_max": 2.5, "pct": 0.06},
                                         {"cote_max": 4.0, "pct": 0.04},
                                         {"cote_max": 999, "pct": 0.025}]},
                }
                candidates.append(s)
                # Foot + Hockey + Basket combo 2j
                s2 = {
                    "id": f"C2_FHB_{cmin}-{cmax}_{sort}_mc{mc}_wr{mwr}",
                    "label": "combo_2j_3sport",
                    "components": [{
                        "sports": ["football", "ice-hockey", "basketball"], "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sort, "max_legs": 2, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "risk_tiered", "min_stake": 0.5,
                               "tiers": [{"cote_max": 2.5, "pct": 0.06},
                                         {"cote_max": 4.0, "pct": 0.04},
                                         {"cote_max": 999, "pct": 0.025}]},
                }
                candidates.append(s2)

# === B. Combos 3j multi-sport ===
for cmin, cmax in [(3.0, 6.0), (4.0, 8.0)]:
    for sort in ["wr", "ev"]:
        for mwr in [0.55, 0.60]:
            s = {
                "id": f"C3_FH_{cmin}-{cmax}_{sort}_wr{mwr}",
                "label": "combo_3j_foot_hockey",
                "components": [{
                    "sports": ["football", "ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 3, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None,
                }],
                "dedup": "max1",
                "sizing": {"mode": "kelly_fraction", "kelly_div": 6.0, "cap_pct": 0.05, "min_stake": 0.5},
            }
            candidates.append(s)

# === C. Hockey + Basket only (foot exclu — décorrélation alternative) ===
for hk_cote in [(1.25, 1.50), (1.30, 1.55), (1.40, 1.70)]:
    for bk_cote in [(1.30, 1.55), (1.50, 1.85), (1.80, 2.20)]:
        for hk_mc in [2, 3]:
            for bk_mc in [1, 2]:
                s = {
                    "id": f"HB_{hk_cote[0]}m{hk_mc}_{bk_cote[0]}m{bk_mc}",
                    "label": "hockey_basket_only",
                    "components": [
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": hk_cote[0], "cote_max": hk_cote[1],
                         "sort_by": "wr", "max_legs": 1, "max_combos": hk_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "basketball", "market": "1x2",
                         "cote_min": bk_cote[0], "cote_max": bk_cote[1],
                         "sort_by": "wr" if bk_cote[0] < 1.7 else "ev",
                         "max_legs": 1, "max_combos": bk_mc,
                         "min_wr": None, "min_ev": None},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": 0.04, "min_stake": 0.5},
                }
                candidates.append(s)

# === D. Foot multi-market (1x2 + BTTS + Over) sur même sport ===
for cote_1x2 in [(1.50, 1.85), (1.70, 2.10), (1.90, 2.40)]:
    for cote_btts in [(1.45, 1.65), (1.60, 1.85)]:
        for cote_over in [(1.40, 1.65), (1.55, 1.80)]:
            s = {
                "id": f"FM_1x2{cote_1x2[0]}_btts{cote_btts[0]}_o25_{cote_over[0]}",
                "label": "foot_multimarket",
                "components": [
                    {"sport": "football", "market": "1x2",
                     "cote_min": cote_1x2[0], "cote_max": cote_1x2[1],
                     "sort_by": "ev", "max_legs": 1, "max_combos": 1,
                     "min_wr": 0.60, "min_ev": None},
                    {"sport": "football", "market": "btts",
                     "cote_min": cote_btts[0], "cote_max": cote_btts[1],
                     "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                     "min_wr": None, "min_ev": None},
                    {"sport": "football", "market": "over_2_5",
                     "cote_min": cote_over[0], "cote_max": cote_over[1],
                     "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                     "min_wr": None, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": 0.04, "min_stake": 0.5},
            }
            candidates.append(s)

# === E. Volume ULTRA haut (10+ picks/j) avec sizing 1-2% ===
for sizing_pct in [0.015, 0.02, 0.025]:
    s = {
        "id": f"VolXL_pct{int(sizing_pct*1000)}",
        "label": "volume_xl",
        "components": [
            {"sport": "football", "market": "1x2",
             "cote_min": 1.20, "cote_max": 1.45,
             "sort_by": "wr", "max_legs": 1, "max_combos": 5,
             "min_wr": None, "min_ev": None},
            {"sport": "ice-hockey", "market": "1x2",
             "cote_min": 1.25, "cote_max": 1.50,
             "sort_by": "wr", "max_legs": 1, "max_combos": 4,
             "min_wr": None, "min_ev": None},
            {"sport": "basketball", "market": "1x2",
             "cote_min": 1.20, "cote_max": 1.40,
             "sort_by": "wr", "max_legs": 1, "max_combos": 3,
             "min_wr": None, "min_ev": None},
            {"sport": "baseball", "market": "1x2",
             "cote_min": 1.30, "cote_max": 1.60,
             "sort_by": "wr", "max_legs": 1, "max_combos": 2,
             "min_wr": None, "min_ev": None},
        ],
        "dedup": "max1",
        "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
    }
    candidates.append(s)

# === F. Hybride : multi_foot_hockey + 1 combo 2j multi-sport ===
for ct_min, ct_max in [(2.0, 3.0), (2.5, 4.0)]:
    for foot_pct in [0.04, 0.05, 0.06]:
        s = {
            "id": f"HYB_FHc2j{ct_min}_pct{int(foot_pct*100)}",
            "label": "hybrid_singles_combo2j",
            "components": [
                {"sport": "football", "market": "1x2",
                 "cote_min": 1.90, "cote_max": 2.40,
                 "sort_by": "ev", "max_legs": 1, "max_combos": 1,
                 "min_wr": None, "min_ev": None},
                {"sport": "ice-hockey", "market": "1x2",
                 "cote_min": 1.25, "cote_max": 1.50,
                 "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                 "min_wr": None, "min_ev": None},
                {"sports": ["football", "ice-hockey"], "market": "1x2",
                 "cote_min": ct_min, "cote_max": ct_max,
                 "sort_by": "ev", "max_legs": 2, "max_combos": 1,
                 "min_wr": 0.55, "min_ev": None},
            ],
            "dedup": "max1",
            "sizing": {"mode": "flat_pct", "pct": foot_pct, "min_stake": 0.5},
        }
        candidates.append(s)

print(f"[v4] {len(candidates)} stratégies candidates")

results = []
for i, s in enumerate(candidates):
    if i % 25 == 0:
        print(f"  [{i}/{len(candidates)}] {s['id'][:60]}")
    ev = {}
    for name, start, end in PERIODS:
        try:
            r = backtest(s, start, end, bankroll0=100)
            sm = r["summary"]
            ev[name] = {
                "pnl": round(sm["pnl"], 1),
                "br_final": round(sm["bankroll_final"], 1),
                "streak": sm["streak_red_max"],
                "n_combos": sm["n_combos"],
                "wr": round(sm["wr_combos"], 3),
                "dd": round(sm["dd_max"], 1),
            }
        except Exception as e:
            ev[name] = {"error": str(e)}
    results.append({"strategy": s, "eval": ev})

def oos(r): return r["eval"].get("Q1-26",{}).get("pnl",0) + r["eval"].get("Apr26",{}).get("pnl",0)
def streak(r): return max((p.get("streak",0) for p in r["eval"].values() if "streak" in p), default=0)
def dd_oos(r): return max(r["eval"].get("Q1-26",{}).get("dd",0), r["eval"].get("Apr26",{}).get("dd",0))
def npos(r): return sum(1 for p in r["eval"].values() if p.get("pnl",0) > 0)
def n_combos_total(r): return sum(p.get("n_combos",0) for p in r["eval"].values() if "n_combos" in p)
def ratio(r): return oos(r) / max(dd_oos(r), 1)

robust = [r for r in results
          if oos(r) >= 100 and npos(r) >= 5 and streak(r) <= 5 and n_combos_total(r) >= 100]
robust.sort(key=lambda r: (-ratio(r), -oos(r)))

print(f"\n[v4] {len(robust)} stratégies robustes (OOS≥100, 5/6 Q+, streak≤5, combos≥100)\n")
print(f"{'ID':50s} {'OOS':>7s} {'DD-O':>6s} {'Ratio':>6s} {'Q1-26':>6s} {'Apr26':>6s} {'strk':>4s} {'Q+':>3s} {'#combos':>8s}")
print("-" * 115)
for r in robust[:30]:
    e = r["eval"]
    q1 = e.get("Q1-26",{}).get("pnl",0)
    ap = e.get("Apr26",{}).get("pnl",0)
    print(f"  {r['strategy']['id'][:48]:50s} {oos(r):>+5.0f}€ {dd_oos(r):>5.0f}€ {ratio(r):>5.1f}x "
          f"{q1:>+4.0f}€ {ap:>+4.0f}€ {streak(r):>3d}j {npos(r):>2d}/6 {n_combos_total(r):>7d}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/find_strategies_v4_results.json", "w") as f:
    json.dump({"all": results, "robust": robust}, f, indent=2, default=str)
print(f"\n[v4] Saved datasets/find_strategies_v4_results.json")
