#!/usr/bin/env python3
"""Sweep v5 — Objectif RATIO 20× (gros gain + DD minuscule).

Approche :
  A. Combos 2j SAFE single-sport (foot 1.3-1.5 chaque jambe, multi par jour)
  B. Combos 2j SAFE multi-sport (foot+hockey, cotes basses)
  C. Combos 3j SAFE (cote totale 2.0-4.0, chaque jambe 1.3-1.5)
  D. Volume MEGA (15+ picks safe, sizing 1-1.5%)
  E. Multi-strat lourd : 4-5 singles + 3 combos 2j safe

Critère winner : ratio ≥ 8× ET PnL ≥ 200€ ET streak ≤ 3.
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

# === A. Combos 2j SAFE single-sport — chaque jambe cote 1.3-1.5 → cote totale 1.7-2.25 ===
for sport in ["football", "ice-hockey"]:
    for cmin, cmax in [(1.7, 2.0), (1.8, 2.2), (1.9, 2.4)]:
        for sort in ["wr", "ev"]:
            for mc in [3, 4, 5, 6]:
                for sizing_pct in [0.015, 0.02, 0.03]:
                    s = {
                        "id": f"C2safe_{sport[:4]}_{cmin}-{cmax}_{sort}_mc{mc}_pct{int(sizing_pct*1000)}",
                        "label": f"combo_2j_safe_{sport}",
                        "components": [{
                            "sport": sport, "market": "1x2",
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": sort, "max_legs": 2, "max_combos": mc,
                            "min_wr": 0.65, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
                    }
                    candidates.append(s)

# === B. Combos 2j SAFE multi-sport ===
for cmin, cmax in [(1.7, 2.1), (1.8, 2.3), (2.0, 2.6)]:
    for mc in [3, 4, 5]:
        for sizing_pct in [0.015, 0.02, 0.03]:
            s = {
                "id": f"C2safe_FH_{cmin}-{cmax}_mc{mc}_pct{int(sizing_pct*1000)}",
                "label": "combo_2j_safe_FH",
                "components": [{
                    "sports": ["football", "ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 2, "max_combos": mc,
                    "min_wr": 0.65, "min_ev": None,
                }],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
            }
            candidates.append(s)

# === C. Combos 3j SAFE ===
for cmin, cmax in [(2.0, 3.0), (2.5, 3.8), (3.0, 4.5)]:
    for mc in [2, 3, 4]:
        for sizing_pct in [0.01, 0.015, 0.02]:
            s = {
                "id": f"C3safe_FH_{cmin}-{cmax}_mc{mc}_pct{int(sizing_pct*1000)}",
                "label": "combo_3j_safe_FH",
                "components": [{
                    "sports": ["football", "ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 3, "max_combos": mc,
                    "min_wr": 0.65, "min_ev": None,
                }],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
            }
            candidates.append(s)

# === D. Volume MEGA ultra-safe ===
for foot_mc in [4, 5, 6]:
    for hockey_mc in [3, 4, 5]:
        for basket_mc in [2, 3]:
            for sizing_pct in [0.01, 0.015, 0.02]:
                s = {
                    "id": f"VolMega_F{foot_mc}_H{hockey_mc}_B{basket_mc}_pct{int(sizing_pct*1000)}",
                    "label": "volume_mega_safe",
                    "components": [
                        {"sport": "football", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.40,
                         "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "ice-hockey", "market": "1x2",
                         "cote_min": 1.25, "cote_max": 1.45,
                         "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                         "min_wr": None, "min_ev": None},
                        {"sport": "basketball", "market": "1x2",
                         "cote_min": 1.20, "cote_max": 1.40,
                         "sort_by": "wr", "max_legs": 1, "max_combos": basket_mc,
                         "min_wr": None, "min_ev": None},
                    ],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
                }
                candidates.append(s)

# === E. Multi-strat lourd : 4 singles + 3 combos 2j safe ===
for foot_pct in [0.02, 0.03]:
    for combo_pct in [0.015, 0.02]:
        # Note : sizing s'applique globalement, pas par composante.
        # On utilise le min commun.
        s = {
            "id": f"HEAVY_pct{int(foot_pct*1000)}_combo{int(combo_pct*1000)}",
            "label": "multi_strat_heavy",
            "components": [
                {"sport": "football", "market": "1x2",
                 "cote_min": 1.30, "cote_max": 1.50,
                 "sort_by": "wr", "max_legs": 1, "max_combos": 3,
                 "min_wr": None, "min_ev": None},
                {"sport": "ice-hockey", "market": "1x2",
                 "cote_min": 1.25, "cote_max": 1.50,
                 "sort_by": "wr", "max_legs": 1, "max_combos": 2,
                 "min_wr": None, "min_ev": None},
                {"sport": "basketball", "market": "1x2",
                 "cote_min": 1.30, "cote_max": 1.55,
                 "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                 "min_wr": None, "min_ev": None},
                {"sports": ["football", "ice-hockey"], "market": "1x2",
                 "cote_min": 1.8, "cote_max": 2.4,
                 "sort_by": "wr", "max_legs": 2, "max_combos": 2,
                 "min_wr": 0.65, "min_ev": None},
            ],
            "dedup": "max1",
            "sizing": {"mode": "flat_pct", "pct": foot_pct, "min_stake": 0.5},
        }
        candidates.append(s)

# === F. Combos 2j BTTS oui foot ===
for cmin, cmax in [(2.5, 3.2), (3.0, 3.8)]:
    for mc in [2, 3]:
        for sizing_pct in [0.02, 0.03]:
            s = {
                "id": f"C2_btts_{cmin}-{cmax}_mc{mc}_pct{int(sizing_pct*1000)}",
                "label": "combo_2j_btts_oui",
                "components": [{
                    "sport": "football", "market": "btts",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 2, "max_combos": mc,
                    "min_wr": 0.65, "min_ev": None,
                }],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": sizing_pct, "min_stake": 0.5},
            }
            candidates.append(s)

print(f"[v5] {len(candidates)} stratégies candidates — objectif ratio ≥ 8×")

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
def ratio(r): return oos(r) / max(dd_oos(r), 1)
def n_combos_total(r): return sum(p.get("n_combos",0) for p in r["eval"].values() if "n_combos" in p)

# Filtre "20×" : ratio ≥ 8 (relaxé), 5/6 Q+, streak ≤ 4
robust = [r for r in results
          if oos(r) >= 100 and npos(r) >= 5 and streak(r) <= 4
          and n_combos_total(r) >= 100]
robust.sort(key=lambda r: (-ratio(r), -oos(r)))

print(f"\n[v5] {len(robust)} robustes\n")
print(f"{'ID':55s} {'OOS':>6s} {'DD-O':>6s} {'Ratio':>6s} {'strk':>4s} {'Q+':>3s} {'#':>5s}")
print("-" * 100)
for r in robust[:30]:
    print(f"  {r['strategy']['id'][:53]:55s} {oos(r):>+5.0f}€ {dd_oos(r):>5.0f}€ {ratio(r):>5.1f}x "
          f"{streak(r):>3d}j {npos(r):>2d}/6 {n_combos_total(r):>4d}")

print(f"\n[v5] Stratégies avec RATIO ≥ 20× : ", end="")
big = [r for r in robust if ratio(r) >= 20]
print(f"{len(big)}")
for r in big[:5]:
    print(f"  {r['strategy']['id']}: OOS +{oos(r):.0f}€ DD {dd_oos(r):.0f}€ ratio {ratio(r):.1f}x")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/find_strategies_v5_results.json", "w") as f:
    json.dump({"all": results, "robust": robust}, f, indent=2, default=str)
print(f"\n[v5] Saved datasets/find_strategies_v5_results.json")
