#!/usr/bin/env python3
"""Soft Challenge : 10€ → 100€ via stratégie classique sizing % (sans all-in).
Tradeoff : plus lent mais DD limité, jamais de reset à 0."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

# On part de BR=10€, on backteste les stratégies top et on note quand BR atteint 100€
INITIAL = 10
TARGET = 100

# Top profils existants à tester (stratégies classiques sans all-in)
top_strats = [
    # GOAT
    {"id": "GOAT", "components": [
        {"sport": "football", "market": "btts,over_1_5,over_2_5",
         "cote_min": 1.20, "cote_max": 1.40, "sort_by": "wr", "max_legs": 1, "max_combos": 3,
         "min_wr": 0.70, "min_ev": None},
        {"sport": "ice-hockey", "market": "1x2",
         "cote_min": 1.20, "cote_max": 1.50, "sort_by": "wr", "max_legs": 1, "max_combos": 5,
         "min_wr": 0.70, "min_ev": None}
    ], "dedup": "max1", "sizing": {"mode": "flat_pct", "pct": 0.10, "min_stake": 0.5}},
    # NARROW DD24
    {"id": "NARROW_DD24", "components": [
        {"sport": "football", "market": "btts,over_1_5,over_2_5",
         "cote_min": 1.20, "cote_max": 1.30, "sort_by": "wr", "max_legs": 1, "max_combos": 3,
         "min_wr": 0.70, "min_ev": None},
        {"sport": "ice-hockey", "market": "1x2",
         "cote_min": 1.20, "cote_max": 1.30, "sort_by": "wr", "max_legs": 1, "max_combos": 5,
         "min_wr": 0.75, "min_ev": None}
    ], "dedup": "max1", "sizing": {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5}},
    # ISO_OU15 mono-marché
    {"id": "ISO_OU15", "components": [
        {"sport": "football", "market": "over_1_5",
         "cote_min": 1.15, "cote_max": 1.35, "sort_by": "wr", "max_legs": 1, "max_combos": 8,
         "min_wr": 0.80, "min_ev": None}
    ], "dedup": "max1", "sizing": {"mode": "flat_pct", "pct": 0.15, "min_stake": 0.5}},
]

# Variantes sizing
sizing_variants = [
    ("pct5", {"mode": "flat_pct", "pct": 0.05, "min_stake": 0.5}),
    ("pct7", {"mode": "flat_pct", "pct": 0.07, "min_stake": 0.5}),
    ("pct10", {"mode": "flat_pct", "pct": 0.10, "min_stake": 0.5}),
    ("pct15", {"mode": "flat_pct", "pct": 0.15, "min_stake": 0.5}),
    ("pct20", {"mode": "flat_pct", "pct": 0.20, "min_stake": 0.5}),
]

CANDS = []
for s in top_strats:
    for tag, sz in sizing_variants:
        cand = dict(s)
        cand["id"] = f"SOFT_{s['id']}_{tag}"
        cand["sizing"] = sz
        CANDS.append(cand)

print(f"[Soft Challenge] {len(CANDS)} configs")
results = []
for s in CANDS:
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=INITIAL, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        daily = r.get("daily", [])
        # Trouver jour où BR atteint TARGET
        days_to_target = None
        for i, d in enumerate(daily):
            if d.get("bankroll_end", 0) >= TARGET:
                days_to_target = i + 1
                break
        results.append({
            "id": s["id"],
            "pnl": round(sm["pnl"], 1),
            "br_final": round(sm["bankroll_final"], 1),
            "br_mult": round(sm["bankroll_final"]/INITIAL, 2),
            "dd": round(sm["dd_max"], 1),
            "n_days_total": len(daily),
            "days_to_target": days_to_target,
            "reached_target": days_to_target is not None,
            "n_combos": sm["n_combos"],
        })
    except Exception as e:
        print(f"  err {s['id']}: {e}")

# Tri : ceux qui atteignent la cible en moins de jours
viable = [r for r in results if r["reached_target"]]
viable.sort(key=lambda r: r["days_to_target"])

print(f"\n[Soft Challenge] {len(viable)}/{len(results)} atteignent {TARGET}€ depuis {INITIAL}€")
print(f"\n=== TOP par RAPIDITÉ (jours pour atteindre {TARGET}€) ===")
for r in viable[:20]:
    print(f"  Jour {r['days_to_target']:>3d} | BR final {r['br_final']:>5.0f}€ (×{r['br_mult']:>4.0f}) | DD {r['dd']:>4.0f}€ | #{r['n_combos']:>3d} | {r['id']}")

# Échecs ?
fails = [r for r in results if not r["reached_target"]]
if fails:
    print(f"\n=== ÉCHECS (n'atteignent jamais {TARGET}€) ===")
    for r in fails[:10]:
        print(f"  BR final {r['br_final']:>5.0f}€ (×{r['br_mult']:>4.0f}) | DD {r['dd']:>4.0f}€ | {r['id']}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/soft_challenge.json","w") as f:
    json.dump({"viable": viable, "fails": fails}, f, indent=2)
print("\nSaved.")
