#!/usr/bin/env python3
"""Sweep v6 — Maximiser PnL × DD ratio + plus de combinés/jour.

Nouveaux axes :
  A. Combos 4j safe (cote totale 2.0-3.5, chaque jambe ~1.2-1.4)
  B. Multi-market triple par match (1x2 + BTTS + Over_2_5) sur foot
  C. Volume extrême 20+ picks/jour avec sizing 1-2%
  D. Compositions ULTRA-LOURDES (6-8 composantes)
  E. Combos 5j foot lottery (cote totale 5-12)
"""
import sys, os, json, itertools
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

# === A. Combos 4j safe ===
for cmin, cmax in [(2.0, 2.8), (2.5, 3.5), (3.0, 4.5)]:
    for sport_combo in [["football"], ["football","ice-hockey"], ["football","ice-hockey","basketball"]]:
        for mc in [1, 2]:
            for sizing_pct in [0.01, 0.02, 0.03]:
                for mwr in [0.65, 0.70]:
                    s = {
                        "id": f"C4_{'-'.join(s[:3] for s in sport_combo)}_{cmin}-{cmax}_mc{mc}_pct{int(sizing_pct*1000)}_wr{mwr}",
                        "label": "combo_4j_safe",
                        "components": [{
                            "sports": sport_combo, "market": "1x2",
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": "wr", "max_legs": 4, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
                    }
                    candidates.append(s)

# === B. Multi-market triple foot (1x2 + BTTS + Over_2_5) ===
for cote_1x2 in [(1.50, 1.80), (1.70, 2.00)]:
    for cote_btts in [(1.45, 1.65), (1.55, 1.80)]:
        for cote_over in [(1.45, 1.65), (1.55, 1.80)]:
            for foot_mc in [2, 3, 4]:
                s = {
                    "id": f"FT_1x2{cote_1x2[0]}_btts{cote_btts[0]}_o25{cote_over[0]}_mc{foot_mc}",
                    "label": "foot_triple_market",
                    "components": [
                        {"sport": "football", "market": "1x2",
                         "cote_min": cote_1x2[0], "cote_max": cote_1x2[1],
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": 0.60, "min_ev": None},
                        {"sport": "football", "market": "btts",
                         "cote_min": cote_btts[0], "cote_max": cote_btts[1],
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "football", "market": "over_2_5",
                         "cote_min": cote_over[0], "cote_max": cote_over[1],
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": 1.25, "cote_max": 1.50,
                         "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                         "min_wr": None, "min_ev": None},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": 0.02, "min_stake": 0.5},
                }
                candidates.append(s)

# === C. Volume extrême (20+ picks/j) ===
for foot_safe_mc in [4, 5, 6, 8]:
    for hockey_safe_mc in [3, 4, 5]:
        for basket_safe_mc in [2, 3, 4]:
            for sizing_pct in [0.008, 0.012, 0.015]:
                s = {
                    "id": f"V20_F{foot_safe_mc}_H{hockey_safe_mc}_B{basket_safe_mc}_pct{int(sizing_pct*1000)}",
                    "label": "volume_extreme",
                    "components": [
                        {"sport": "football", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.40,
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_safe_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": 1.25, "cote_max": 1.45,
                         "sort_by": "wr", "max_legs": 1, "max_combos": hockey_safe_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "basketball", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.40,
                         "sort_by": "wr", "max_legs": 1, "max_combos": basket_safe_mc,
                         "min_wr": None, "min_ev": None},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
                }
                candidates.append(s)

# === D. Composition ULTRA-LOURDE (8 composantes) — combine TOUT ===
for sizing_pct in [0.012, 0.015, 0.02, 0.025]:
    s = {
        "id": f"ULTRA_pct{int(sizing_pct*1000)}",
        "label": "ultra_heavy_8comp",
        "components": [
            # Singles foot value (winner)
            {"sport": "football", "market": "1x2",
             "cote_min": 1.90, "cote_max": 2.40,
             "sort_by": "ev", "max_legs": 1, "max_combos": 1,
             "min_wr": None, "min_ev": None, "label": "Foot value high"},
            # Singles foot safe
            {"sport": "football", "market": "1x2",
             "cote_min": 1.30, "cote_max": 1.60,
             "sort_by": "wr", "max_legs": 1, "max_combos": 2,
             "min_wr": None, "min_ev": None, "label": "Foot safe"},
            # Singles hockey safe (winner)
            {"sport": "ice-hockey", "market": "1x2",
             "cote_min": 1.25, "cote_max": 1.50,
             "sort_by": "wr", "max_legs": 1, "max_combos": 3,
             "min_wr": None, "min_ev": None, "label": "Hockey safe"},
            # Combos 2j hockey safe
            {"sport": "ice-hockey", "market": "1x2",
             "cote_min": 1.70, "cote_max": 2.00,
             "sort_by": "wr", "max_legs": 2, "max_combos": 2,
             "min_wr": 0.65, "min_ev": None, "label": "Combos 2j hockey"},
            # Singles basket safe
            {"sport": "basketball", "market": "1x2",
             "cote_min": 1.30, "cote_max": 1.55,
             "sort_by": "wr", "max_legs": 1, "max_combos": 1,
             "min_wr": None, "min_ev": None, "label": "Basket safe"},
            # Foot BTTS oui safe
            {"sport": "football", "market": "btts",
             "cote_min": 1.50, "cote_max": 1.75,
             "sort_by": "wr", "max_legs": 1, "max_combos": 1,
             "min_wr": None, "min_ev": None, "label": "Foot BTTS oui"},
            # Foot Over 2.5 safe
            {"sport": "football", "market": "over_2_5",
             "cote_min": 1.45, "cote_max": 1.70,
             "sort_by": "wr", "max_legs": 1, "max_combos": 1,
             "min_wr": None, "min_ev": None, "label": "Foot Over 2.5"},
            # Combo 2j multi-sport
            {"sports": ["football", "ice-hockey"], "market": "1x2",
             "cote_min": 2.5, "cote_max": 4.0,
             "sort_by": "ev", "max_legs": 2, "max_combos": 1,
             "min_wr": 0.55, "min_ev": None, "label": "Combo 2j multi-sport"},
        ],
        "dedup": "max1",
        "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
    }
    candidates.append(s)

# === E. Foot-only volume haut (foot dominant, 250k matchs train) ===
for cmin1, cmax1 in [(1.30, 1.55), (1.40, 1.65)]:
    for cmin2, cmax2 in [(1.65, 1.95), (1.80, 2.20)]:
        for sizing_pct in [0.015, 0.02, 0.025]:
            s = {
                "id": f"FootXL_{cmin1}_{cmin2}_pct{int(sizing_pct*1000)}",
                "label": "foot_volume_xl",
                "components": [
                    {"sport": "football", "market": "1x2",
                     "cote_min": cmin1, "cote_max": cmax1,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 4,
                     "min_wr": None, "min_ev": None},
                    {"sport": "football", "market": "1x2",
                     "cote_min": cmin2, "cote_max": cmax2,
                     "sort_by": "ev", "max_legs": 1, "max_combos": 2,
                     "min_wr": 0.55, "min_ev": None},
                    {"sport": "football", "market": "btts",
                     "cote_min": 1.50, "cote_max": 1.75,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                     "min_wr": None, "min_ev": None},
                    {"sport": "football", "market": "over_2_5",
                     "cote_min": 1.45, "cote_max": 1.70,
                     "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                     "min_wr": None, "min_ev": None},
                ],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
            }
            candidates.append(s)

print(f"[v6] {len(candidates)} stratégies candidates")

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

def oos(r): return r["eval"].get("Q1-26",{}).get("pnl",0) + r["eval"].get("Apr26",{}).get("pnl",0)
def streak(r): return max((p.get("streak",0) for p in r["eval"].values() if "streak" in p), default=0)
def dd_oos(r): return max(r["eval"].get("Q1-26",{}).get("dd",0), r["eval"].get("Apr26",{}).get("dd",0))
def npos(r): return sum(1 for p in r["eval"].values() if p.get("pnl",0) > 0)
def ratio(r): return oos(r) / max(dd_oos(r), 1)
def n_combos_total(r): return sum(p.get("n_combos",0) for p in r["eval"].values() if "n_combos" in p)

robust = [r for r in results
          if oos(r) >= 100 and npos(r) >= 5 and streak(r) <= 5
          and n_combos_total(r) >= 100]
robust.sort(key=lambda r: (-ratio(r), -oos(r)))

print(f"\n[v6] {len(robust)} robustes\n")
print(f"{'ID':55s} {'OOS':>7s} {'DD-O':>7s} {'Ratio':>6s} {'strk':>4s} {'#':>5s}")
print("-" * 100)
for r in robust[:30]:
    print(f"  {r['strategy']['id'][:53]:55s} {oos(r):>+5.0f}€ {dd_oos(r):>5.0f}€ {ratio(r):>5.1f}x "
          f"{streak(r):>3d}j {n_combos_total(r):>4d}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/find_strategies_v6_results.json", "w") as f:
    json.dump({"all": results, "robust": robust}, f, indent=2, default=str)
print(f"\n[v6] Saved")
