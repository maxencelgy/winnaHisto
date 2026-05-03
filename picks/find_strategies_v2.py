#!/usr/bin/env python3
"""Sweep v2 — axes nouveaux pour trouver de meilleures stratégies.

Axes:
  1. Multi-sport + combos 2j single-sport (foot_safe + hockey_safe + foot_2j_value)
  2. Sizing modes alternatifs (kelly_fraction, risk_tiered, ev_proportional)
  3. Min_wr strict + multi-sport
  4. Mix markets (foot 1x2 + foot BTTS)
  5. Variations autour winner actuel (foot 1.9-2.4 + hockey 1.25-1.50)

Test 6 trimestres OOS, focus OOS 2026 (Q1-26 + Apr26).
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

# === Axe 1 : Variations autour du winner multi_foot_hockey ===
# Tester différentes cotes/sorts pour le foot et hockey
for foot_cote in [(1.80, 2.30), (1.90, 2.40), (2.00, 2.60), (2.20, 2.80)]:
    for foot_sort in ["ev", "wr"]:
        for hockey_cote in [(1.20, 1.45), (1.25, 1.50), (1.30, 1.55), (1.35, 1.60)]:
            for hockey_sort in ["wr", "ev"]:
                for foot_mc in [1, 2]:
                    for hockey_mc in [1, 2]:
                        s = {
                            "id": f"V1_F{foot_cote[0]}-{foot_cote[1]}{foot_sort}{foot_mc}_H{hockey_cote[0]}-{hockey_cote[1]}{hockey_sort}{hockey_mc}",
                            "label": "v1_foot_hockey",
                            "components": [
                                {"sport": "football", "market": "1x2",
                                 "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                                 "sort_by": foot_sort, "max_legs": 1, "max_combos": foot_mc,
                                 "min_wr": None, "min_ev": None},
                                {"sport": "ice-hockey", "market": "1x2",
                                 "cote_min": hockey_cote[0], "cote_max": hockey_cote[1],
                                 "sort_by": hockey_sort, "max_legs": 1, "max_combos": hockey_mc,
                                 "min_wr": None, "min_ev": None},
                            ],
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5},
                        }
                        candidates.append(s)

# === Axe 2 : Triple combinations foot + hockey + basket ===
for foot_p in [(1.6, 1.9, "wr"), (1.9, 2.4, "ev")]:
    for hockey_p in [(1.25, 1.50, "wr"), (1.40, 1.70, "wr")]:
        for basket_p in [(1.40, 1.70, "wr"), (1.80, 2.20, "ev"), (2.10, 2.50, "ev")]:
            s = {
                "id": f"V2_F{foot_p[0]}{foot_p[2]}_H{hockey_p[0]}_B{basket_p[0]}",
                "label": "v2_3sport",
                "components": [
                    {"sport": "football", "market": "1x2", "cote_min": foot_p[0], "cote_max": foot_p[1],
                     "sort_by": foot_p[2], "max_legs": 1, "max_combos": 1, "min_wr": None, "min_ev": None},
                    {"sport": "ice-hockey", "market": "1x2", "cote_min": hockey_p[0], "cote_max": hockey_p[1],
                     "sort_by": hockey_p[2], "max_legs": 1, "max_combos": 1, "min_wr": None, "min_ev": None},
                    {"sport": "basketball", "market": "1x2", "cote_min": basket_p[0], "cote_max": basket_p[1],
                     "sort_by": basket_p[2], "max_legs": 1, "max_combos": 1, "min_wr": None, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": 0.04, "min_stake": 0.5},
            }
            candidates.append(s)

# === Axe 3 : Multi-sport avec sizing alternatifs ===
base = {
    "components": [
        {"sport": "football", "market": "1x2", "cote_min": 1.90, "cote_max": 2.40,
         "sort_by": "ev", "max_legs": 1, "max_combos": 1, "min_wr": None, "min_ev": None},
        {"sport": "ice-hockey", "market": "1x2", "cote_min": 1.25, "cote_max": 1.50,
         "sort_by": "wr", "max_legs": 1, "max_combos": 1, "min_wr": None, "min_ev": None},
    ],
    "dedup": "max1",
}
for sizing in [
    ("flat_pct_3", {"mode": "flat_pct", "pct": 0.03, "min_stake": 0.5}),
    ("flat_pct_5", {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5}),
    ("flat_pct_8", {"mode": "flat_pct", "pct": 0.08, "min_stake": 0.5}),
    ("risk_tiered", {"mode": "risk_tiered", "min_stake": 0.5,
                     "tiers": [{"cote_max": 1.5, "pct": 0.08},
                               {"cote_max": 2.2, "pct": 0.05},
                               {"cote_max": 999, "pct": 0.03}]}),
    ("kelly_4", {"mode": "kelly_fraction", "kelly_div": 4.0, "cap_pct": 0.10, "min_stake": 0.5}),
    ("kelly_8", {"mode": "kelly_fraction", "kelly_div": 8.0, "cap_pct": 0.06, "min_stake": 0.5}),
    ("ev_prop", {"mode": "ev_proportional", "base_pct": 0.04, "ev_factor": 0.30,
                 "cap_pct": 0.10, "min_stake": 0.5}),
]:
    s = {**base, "id": f"V3_FH_{sizing[0]}", "label": f"v3_sizing_{sizing[0]}",
         "sizing": sizing[1]}
    candidates.append(s)

# === Axe 4 : Min_wr stricte sur multi-sport ===
for foot_cote in [(1.50, 2.00), (1.70, 2.30), (1.90, 2.50)]:
    for hockey_cote in [(1.25, 1.50), (1.40, 1.80)]:
        for mwr in [0.55, 0.60, 0.65]:
            s = {
                "id": f"V4_F{foot_cote[0]}-{foot_cote[1]}_H{hockey_cote[0]}-{hockey_cote[1]}_wr{mwr}",
                "label": "v4_minwr",
                "components": [
                    {"sport": "football", "market": "1x2",
                     "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                     "sort_by": "ev", "max_legs": 1, "max_combos": 2,
                     "min_wr": mwr, "min_ev": None},
                    {"sport": "ice-hockey", "market": "1x2",
                     "cote_min": hockey_cote[0], "cote_max": hockey_cote[1],
                     "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                     "min_wr": None, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5},
            }
            candidates.append(s)

# === Axe 5 : Multi-market foot (1x2 + BTTS) ===
for cote_1x2 in [(1.50, 1.85), (1.60, 1.90)]:
    for cote_btts in [(1.50, 1.75), (1.60, 1.90)]:
        s = {
            "id": f"V5_1x2{cote_1x2[0]}_btts{cote_btts[0]}",
            "label": "v5_multimarket_foot",
            "components": [
                {"sport": "football", "market": "1x2",
                 "cote_min": cote_1x2[0], "cote_max": cote_1x2[1],
                 "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                 "min_wr": None, "min_ev": None},
                {"sport": "football", "market": "btts",
                 "cote_min": cote_btts[0], "cote_max": cote_btts[1],
                 "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                 "min_wr": None, "min_ev": None},
            ],
            "dedup": "max1",
            "sizing": {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5},
        }
        candidates.append(s)

# === Axe 6 : Combos 2j single-sport en parallèle d'un single safe ===
# Ex: Hockey safe single + foot combo 2j value
for foot_cote_total in [(2.0, 3.0), (2.5, 4.0), (3.0, 5.0)]:
    for foot_sort in ["wr", "ev"]:
        for foot_mwr in [None, 0.55, 0.60]:
            s = {
                "id": f"V6_FH2j_{foot_cote_total[0]}-{foot_cote_total[1]}_{foot_sort}_wr{foot_mwr}",
                "label": "v6_foot2j_hockey_safe",
                "components": [
                    {"sport": "football", "market": "1x2",
                     "cote_min": foot_cote_total[0], "cote_max": foot_cote_total[1],
                     "sort_by": foot_sort, "max_legs": 2, "max_combos": 1,
                     "min_wr": foot_mwr, "min_ev": None},
                    {"sport": "ice-hockey", "market": "1x2",
                     "cote_min": 1.25, "cote_max": 1.50,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                     "min_wr": None, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": {"mode": "risk_tiered", "min_stake": 0.5,
                           "tiers": [{"cote_max": 1.5, "pct": 0.06},
                                     {"cote_max": 3.0, "pct": 0.04},
                                     {"cote_max": 999, "pct": 0.02}]},
            }
            candidates.append(s)

print(f"[v2] {len(candidates)} stratégies candidates")

# === Évaluation ===
results = []
for i, s in enumerate(candidates):
    if i % 30 == 0:
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

# Filtres
def oos(r): return r["eval"].get("Q1-26",{}).get("pnl",0) + r["eval"].get("Apr26",{}).get("pnl",0)
def streak(r): return max((p.get("streak",0) for p in r["eval"].values() if "streak" in p), default=0)
def npos(r): return sum(1 for p in r["eval"].values() if p.get("pnl",0) > 0)
def n_combos_total(r): return sum(p.get("n_combos",0) for p in r["eval"].values() if "n_combos" in p)

# Critère robustes : 5/6 Q+, OOS 2026 ≥ 100€, streak ≤ 5 (assoupli), volume suffisant
robust = [r for r in results
          if oos(r) >= 100
          and npos(r) >= 5
          and streak(r) <= 5
          and n_combos_total(r) >= 100]
robust.sort(key=lambda r: -oos(r))

print(f"\n[v2] {len(robust)} stratégies robustes (OOS 2026 ≥ 100€, 5/6 Q+, streak ≤ 5)\n")
print(f"{'ID':70s} {'OOS':>7s} {'Q1-26':>6s} {'Apr26':>6s} {'strk':>4s} {'Q+':>3s}")
print("-" * 110)
for r in robust[:25]:
    e = r["eval"]
    q1 = e.get("Q1-26",{}).get("pnl",0)
    ap = e.get("Apr26",{}).get("pnl",0)
    print(f"  {r['strategy']['id'][:68]:70s} {oos(r):>+5.0f}€ {q1:>+4.0f}€ {ap:>+4.0f}€ {streak(r):>3d}j {npos(r):>2d}/6")

# Sauvegarde
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/find_strategies_v2_results.json", "w") as f:
    json.dump({"all": results, "robust": robust}, f, indent=2, default=str)
print(f"\n[v2] Saved datasets/find_strategies_v2_results.json")
