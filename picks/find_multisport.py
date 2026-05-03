#!/usr/bin/env python3
"""Sweep ciblé : trouver la meilleure stratégie MULTI-SPORT.

Compositions testées : foot+basket, foot+hockey, foot+basket+hockey, hockey+basket, etc.
Test sur 6 trimestres (Q1-25 → Apr-26). Critère : 5/6 positifs + streak ≤ 3 + PnL ≥ 100€.
Validation finale sur S1-26 strict.
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

# Composantes par sport — settings éprouvés (issus de sweeps précédents)
SPORT_PROFILES = {
    "football_safe":  {"sport": "football",   "cote_min": 1.40, "cote_max": 1.70, "sort_by": "wr"},
    "football_value": {"sport": "football",   "cote_min": 1.60, "cote_max": 1.90, "sort_by": "wr"},
    "football_high":  {"sport": "football",   "cote_min": 1.90, "cote_max": 2.40, "sort_by": "ev"},
    "basket_safe":    {"sport": "basketball", "cote_min": 1.30, "cote_max": 1.60, "sort_by": "wr"},
    "basket_value":   {"sport": "basketball", "cote_min": 1.50, "cote_max": 1.90, "sort_by": "wr"},
    "basket_high":    {"sport": "basketball", "cote_min": 2.10, "cote_max": 2.50, "sort_by": "ev"},
    "hockey_safe":    {"sport": "ice-hockey", "cote_min": 1.25, "cote_max": 1.50, "sort_by": "wr"},
    "hockey_value":   {"sport": "ice-hockey", "cote_min": 1.40, "cote_max": 1.80, "sort_by": "wr"},
    "baseball_safe":  {"sport": "baseball",   "cote_min": 1.50, "cote_max": 1.90, "sort_by": "wr"},
}

# Combinaisons multi-sport (2 à 4 sports)
COMPOS = []

for n in [2, 3, 4]:
    for combo in itertools.combinations(SPORT_PROFILES.keys(), n):
        # Filtrer : pas plus d'1 profil par sport
        sports_in = [SPORT_PROFILES[k]["sport"] for k in combo]
        if len(set(sports_in)) != n:
            continue
        COMPOS.append(combo)

print(f"[multi-sport] {len(COMPOS)} compositions multi-sport à tester")

def make_strategy(profiles, max_combos_per_sport=2, sizing_mode="flat_pct"):
    """Construit une strategy multi-composante."""
    components = []
    for prof_key in profiles:
        p = SPORT_PROFILES[prof_key]
        components.append({
            "sport": p["sport"], "market": "1x2",
            "cote_min": p["cote_min"], "cote_max": p["cote_max"],
            "sort_by": p["sort_by"],
            "max_legs": 1, "max_combos": max_combos_per_sport,
            "min_wr": None, "min_ev": None,
            "label": prof_key,
        })
    sizing = {"mode": sizing_mode, "min_stake": 0.5}
    if sizing_mode == "flat_pct":
        sizing["pct"] = 0.05  # plus prudent en multi-composante (volume haut)
    elif sizing_mode == "risk_tiered":
        sizing["tiers"] = [
            {"cote_max": 2.0, "pct": 0.05},
            {"cote_max": 999, "pct": 0.03},
        ]
    return {
        "id": "_".join(profiles)[:80],
        "label": " + ".join(profiles),
        "components": components,
        "dedup": "max1",
        "sizing": sizing,
    }


def evaluate(s):
    """Évalue sur 6 trimestres."""
    res = {}
    for name, start, end in PERIODS:
        try:
            r = backtest(s, start, end, bankroll0=100)
            sm = r["summary"]
            res[name] = {
                "pnl": round(sm["pnl"], 1),
                "br_final": round(sm["bankroll_final"], 1),
                "streak": sm["streak_red_max"],
                "n_combos": sm["n_combos"],
                "wr": round(sm["wr_combos"], 3),
                "dd": round(sm["dd_max"], 1),
            }
        except Exception as e:
            res[name] = {"error": str(e)}
    return res


# Test : 2 max_combos par sport, sizing flat_pct 5% par défaut
results = []
for i, combo in enumerate(COMPOS):
    if i % 10 == 0:
        print(f"  [{i}/{len(COMPOS)}] {' + '.join(combo)}")
    for mc in [1, 2]:
        s = make_strategy(combo, max_combos_per_sport=mc)
        ev = evaluate(s)
        results.append({"strategy": s, "eval": ev, "n_sports": len(combo), "mc": mc})

# Filter : focus sur OOS strict (Q1-26 + Apr26)
def oos_pnl(r):
    e = r["eval"]
    return e.get("Q1-26", {}).get("pnl", 0) + e.get("Apr26", {}).get("pnl", 0)

def n_pos_all(r):
    return sum(1 for p in r["eval"].values() if p.get("pnl", 0) > 0)

def max_streak_all(r):
    return max((p.get("streak", 0) for p in r["eval"].values() if "streak" in p), default=0)

# Critère croustillant : OOS 2026 > +100€, 5/6 Q+, streak ≤ 3
robust = [r for r in results
          if oos_pnl(r) > 100
          and n_pos_all(r) >= 5
          and max_streak_all(r) <= 3
          and all(p.get("n_combos", 0) > 0 for p in r["eval"].values())]
robust.sort(key=lambda r: -oos_pnl(r))

print(f"\n[multi-sport] {len(robust)} compositions robustes (OOS 2026 > +100€, 5/6 Q+, streak ≤ 3)\n")
print(f"{'Composition':50s} {'OOS 2026':>9s} {'Q1-26':>7s} {'Apr26':>7s} {'streak':>6s} {'mc':>3s} {'sports':>6s}")
print("-" * 105)
for r in robust[:20]:
    e = r["eval"]
    q126 = e.get("Q1-26", {}).get("pnl", 0)
    apr = e.get("Apr26", {}).get("pnl", 0)
    print(f"  {r['strategy']['label'][:48]:50s} {oos_pnl(r):>+7.0f}€ {q126:>+5.0f}€ {apr:>+5.0f}€ "
          f"{max_streak_all(r):>5d}j {r['mc']:>3d} {r['n_sports']:>6d}")

# Top 1 → ajouter à picks/strategies/
print(f"\n=== Top 1 ===")
if robust:
    top = robust[0]
    print(f"Label: {top['strategy']['label']}")
    print(f"Composantes: {len(top['strategy']['components'])} sports")
    print(f"OOS 2026: +{oos_pnl(top):.0f}€ (Q1-26 +{top['eval']['Q1-26']['pnl']:.0f}€ + Apr26 +{top['eval']['Apr26']['pnl']:.0f}€)")
    print(f"Streak max: {max_streak_all(top)}j sur 6 trimestres")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/find_multisport_results.json", "w") as f:
    json.dump({"all": results, "robust": robust}, f, indent=2, default=str)
print(f"\n💾 Saved datasets/find_multisport_results.json")
