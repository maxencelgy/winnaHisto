#!/usr/bin/env python3
"""Sweep v3 — Optimiser PnL/DD ratio. Cherche gros gains avec petit DD.

Approches nouvelles :
  A. Volume haut multi-sport ultra-safe (5-8 picks/j cote 1.10-1.40)
  B. Cherry-pick par ligue spécifique (Premier League, NHL, NBA only)
  C. Triple safe parallèle (foot+hockey+basket safe avec sizing 3% ou tiered)
  D. Min_wr stricte (>= 0.70) sur cotes value
  E. Mix 1x2 + BTTS + Over avec dédup max1
  F. Conservateur extrême : flat_pct 2-3% sur winner foot+hockey

Critère : PnL/DD ratio MAXIMAL parmi 5/6 Q+ et streak ≤ 5.
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

# === A. Volume haut multi-sport ultra-safe ===
for foot_cote in [(1.20, 1.40), (1.30, 1.50)]:
    for hockey_cote in [(1.20, 1.40), (1.25, 1.50)]:
        for basket_cote in [(1.20, 1.40), (1.30, 1.55)]:
            for foot_mc in [2, 3]:
                for hockey_mc in [2, 3]:
                    for basket_mc in [1, 2]:
                        s = {
                            "id": f"VolHi_F{foot_cote[0]}m{foot_mc}_H{hockey_cote[0]}m{hockey_mc}_B{basket_cote[0]}m{basket_mc}",
                            "label": "vol_hi_safe",
                            "components": [
                                {"sport": "football", "market": "1x2",
                                 "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                                 "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                                 "min_wr": None, "min_ev": None},
                                {"sport": "ice-hockey", "market": "1x2",
                                 "cote_min": hockey_cote[0], "cote_max": hockey_cote[1],
                                 "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                                 "min_wr": None, "min_ev": None},
                                {"sport": "basketball", "market": "1x2",
                                 "cote_min": basket_cote[0], "cote_max": basket_cote[1],
                                 "sort_by": "wr", "max_legs": 1, "max_combos": basket_mc,
                                 "min_wr": None, "min_ev": None},
                            ],
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": 0.03, "min_stake": 0.5},
                        }
                        candidates.append(s)

# === C. Triple parallèle (foot mid + hockey safe + basket value) sizing tiered ===
for foot_cote in [(1.50, 1.85), (1.70, 2.10), (1.90, 2.40)]:
    for foot_sort in ["wr", "ev"]:
        for sizing in [
            ("safe_3pct", {"mode": "flat_pct", "pct": 0.03, "min_stake": 0.5}),
            ("safe_5pct", {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5}),
            ("tier_lo",   {"mode": "risk_tiered", "min_stake": 0.5,
                           "tiers": [{"cote_max": 1.5, "pct": 0.06},
                                     {"cote_max": 2.0, "pct": 0.04},
                                     {"cote_max": 999, "pct": 0.02}]}),
        ]:
            s = {
                "id": f"Tri_F{foot_cote[0]}-{foot_cote[1]}{foot_sort}_HB_{sizing[0]}",
                "label": "tri_safe",
                "components": [
                    {"sport": "football", "market": "1x2",
                     "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                     "sort_by": foot_sort, "max_legs": 1, "max_combos": 1,
                     "min_wr": None, "min_ev": None},
                    {"sport": "ice-hockey", "market": "1x2",
                     "cote_min": 1.25, "cote_max": 1.50,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                     "min_wr": None, "min_ev": None},
                    {"sport": "basketball", "market": "1x2",
                     "cote_min": 1.40, "cote_max": 1.80,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                     "min_wr": None, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": sizing[1],
            }
            candidates.append(s)

# === F. Conservateur extrême sur winner foot+hockey ===
for pct in [0.02, 0.03, 0.04, 0.06]:
    s = {
        "id": f"FH_pct{int(pct*100)}",
        "label": f"foot_hockey_{int(pct*100)}pct",
        "components": [
            {"sport": "football", "market": "1x2",
             "cote_min": 1.90, "cote_max": 2.40,
             "sort_by": "ev", "max_legs": 1, "max_combos": 1,
             "min_wr": None, "min_ev": None},
            {"sport": "ice-hockey", "market": "1x2",
             "cote_min": 1.25, "cote_max": 1.50,
             "sort_by": "wr", "max_legs": 1, "max_combos": 1,
             "min_wr": None, "min_ev": None},
        ],
        "dedup": "max1",
        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
    }
    candidates.append(s)

# === D. Min_wr stricte sur multi-sport ===
for foot_cote in [(1.50, 1.90), (1.70, 2.10), (1.90, 2.40)]:
    for mwr_foot in [0.65, 0.70, 0.75]:
        for hockey_only in [True, False]:
            comps = [
                {"sport": "football", "market": "1x2",
                 "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                 "sort_by": "ev", "max_legs": 1, "max_combos": 2,
                 "min_wr": mwr_foot, "min_ev": None},
            ]
            if not hockey_only:
                comps.append({
                    "sport": "ice-hockey", "market": "1x2",
                    "cote_min": 1.25, "cote_max": 1.50,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                })
            s = {
                "id": f"Mwr_F{foot_cote[0]}_wr{mwr_foot}_{'solo' if hockey_only else 'plusH'}",
                "label": "min_wr_strict",
                "components": comps,
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5},
            }
            candidates.append(s)

# === E. Mix 1x2 + BTTS sur foot ===
for cote_1x2 in [(1.50, 1.85), (1.70, 2.10), (1.90, 2.40)]:
    for cote_btts in [(1.40, 1.65), (1.55, 1.80)]:
        s = {
            "id": f"Mx_1x2{cote_1x2[0]}_btts{cote_btts[0]}",
            "label": "mix_1x2_btts_foot",
            "components": [
                {"sport": "football", "market": "1x2",
                 "cote_min": cote_1x2[0], "cote_max": cote_1x2[1],
                 "sort_by": "ev", "max_legs": 1, "max_combos": 2,
                 "min_wr": 0.60, "min_ev": None},
                {"sport": "football", "market": "btts",
                 "cote_min": cote_btts[0], "cote_max": cote_btts[1],
                 "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                 "min_wr": None, "min_ev": None},
                {"sport": "ice-hockey", "market": "1x2",
                 "cote_min": 1.25, "cote_max": 1.50,
                 "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                 "min_wr": None, "min_ev": None},
            ],
            "dedup": "max1",
            "sizing": {"mode": "flat_pct", "pct": 0.04, "min_stake": 0.5},
        }
        candidates.append(s)

print(f"[v3] {len(candidates)} stratégies candidates")

# === Évaluation 6 trimestres ===
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

# === Métriques ===
def oos(r): return r["eval"].get("Q1-26",{}).get("pnl",0) + r["eval"].get("Apr26",{}).get("pnl",0)
def streak(r): return max((p.get("streak",0) for p in r["eval"].values() if "streak" in p), default=0)
def dd_oos(r):
    """Max DD sur Q1-26 et Apr26 uniquement."""
    return max(r["eval"].get("Q1-26",{}).get("dd",0), r["eval"].get("Apr26",{}).get("dd",0))
def npos(r): return sum(1 for p in r["eval"].values() if p.get("pnl",0) > 0)
def n_combos_total(r): return sum(p.get("n_combos",0) for p in r["eval"].values() if "n_combos" in p)

# Pour chaque strat, calculer ratio = PnL OOS / DD OOS
def ratio(r):
    d = dd_oos(r)
    return oos(r) / max(d, 1)

# Filter robust : 5/6+ Q+, streak ≤ 5, n_combos ≥ 100, OOS ≥ 100
robust = [r for r in results
          if oos(r) >= 100 and npos(r) >= 5 and streak(r) <= 5 and n_combos_total(r) >= 100]

# Sort by ratio (PnL/DD) puis par OOS
robust.sort(key=lambda r: (-ratio(r), -oos(r)))

print(f"\n[v3] {len(robust)} stratégies robustes\n")
print(f"{'ID':50s} {'OOS':>7s} {'DD-OOS':>7s} {'Ratio':>6s} {'Q1-26':>6s} {'Apr26':>6s} {'streak':>6s} {'Q+':>3s}")
print("-" * 110)
for r in robust[:30]:
    e = r["eval"]
    q1 = e.get("Q1-26",{}).get("pnl",0)
    ap = e.get("Apr26",{}).get("pnl",0)
    print(f"  {r['strategy']['id'][:48]:50s} {oos(r):>+5.0f}€ {dd_oos(r):>5.0f}€ {ratio(r):>5.1f}x "
          f"{q1:>+4.0f}€ {ap:>+4.0f}€ {streak(r):>5d}j {npos(r):>2d}/6")

# Sauvegarde
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/find_strategies_v3_results.json", "w") as f:
    json.dump({"all": results, "robust": robust}, f, indent=2, default=str)
print(f"\n[v3] Saved datasets/find_strategies_v3_results.json")
