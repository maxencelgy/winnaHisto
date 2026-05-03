#!/usr/bin/env python3
"""Sweep sizing avancé — risk_tiered + ev_proportional + kelly_fraction sur top profils."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

CANDS = []

# Base profile : Foot O 1.5 cote 1.40-1.65 WR≥65% mc5
BASE_COMPS = [{
    "sport": "football", "market": "over_1_5",
    "cote_min": 1.40, "cote_max": 1.65,
    "sort_by": "wr", "max_legs": 1, "max_combos": 5,
    "min_wr": 0.65, "min_ev": None,
}]

# A. Kelly fractional variants
for kelly_div in [2, 3, 4, 6, 8]:
    for cap_pct in [0.05, 0.08, 0.10, 0.15]:
        CANDS.append({
            "id": f"KELLY_div{kelly_div}_cap{int(cap_pct*100)}",
            "components": BASE_COMPS,
            "dedup": "max1",
            "sizing": {"mode": "kelly_fraction", "kelly_div": kelly_div,
                       "cap_pct": cap_pct, "min_stake": 0.5},
        })

# B. EV proportional
for base_pct in [0.05, 0.07, 0.10]:
    for ev_factor in [0.20, 0.30, 0.50]:
        for cap_pct in [0.10, 0.15, 0.20]:
            CANDS.append({
                "id": f"EVP_base{int(base_pct*100)}_ev{int(ev_factor*100)}_cap{int(cap_pct*100)}",
                "components": BASE_COMPS,
                "dedup": "max1",
                "sizing": {"mode": "ev_proportional", "base_pct": base_pct,
                           "ev_factor": ev_factor, "cap_pct": cap_pct, "min_stake": 0.5},
            })

# C. Risk tiered avec différents tiers
for tier_low in [0.08, 0.10, 0.12, 0.15]:
    for tier_decay in [0.6, 0.7, 0.8]:
        CANDS.append({
            "id": f"TIER_low{int(tier_low*100)}_decay{int(tier_decay*10)}",
            "components": BASE_COMPS,
            "dedup": "max1",
            "sizing": {"mode": "risk_tiered", "min_stake": 0.5,
                       "tiers": [
                           {"cote_max": 1.50, "pct": tier_low},
                           {"cote_max": 1.70, "pct": tier_low * tier_decay},
                           {"cote_max": 999, "pct": tier_low * tier_decay * tier_decay},
                       ]},
        })

# D. Multi-comp + sizing avancés
for sizing_cfg in [
    {"mode": "kelly_fraction", "kelly_div": 4, "cap_pct": 0.10},
    {"mode": "kelly_fraction", "kelly_div": 6, "cap_pct": 0.15},
    {"mode": "ev_proportional", "base_pct": 0.05, "ev_factor": 0.30, "cap_pct": 0.15},
    {"mode": "flat_pct", "pct": 0.08},
    {"mode": "flat_pct", "pct": 0.10},
]:
    sizing_cfg["min_stake"] = 0.5
    CANDS.append({
        "id": f"MULTI_FHB_{sizing_cfg.get('mode')}_{sizing_cfg.get('pct') or sizing_cfg.get('kelly_div') or sizing_cfg.get('ev_factor')}",
        "components": [
            {"sport": "football", "market": "over_1_5",
             "cote_min": 1.30, "cote_max": 1.55,
             "sort_by": "wr", "max_legs": 1, "max_combos": 5,
             "min_wr": 0.65, "min_ev": None},
            {"sport": "ice-hockey", "market": "1x2",
             "cote_min": 1.20, "cote_max": 1.50,
             "sort_by": "wr", "max_legs": 1, "max_combos": 3,
             "min_wr": 0.65, "min_ev": None},
            {"sport": "basketball", "market": "1x2",
             "cote_min": 1.20, "cote_max": 1.50,
             "sort_by": "wr", "max_legs": 1, "max_combos": 1,
             "min_wr": 0.65, "min_ev": None},
        ],
        "dedup": "max1",
        "sizing": sizing_cfg,
    })

print(f"[Sizing advanced] {len(CANDS)} configs Winamax FR")

results = []
for i, s in enumerate(CANDS):
    if i % 20 == 0: print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        results.append({
            "id": s["id"], "strat": s,
            "pnl": round(sm["pnl"], 1),
            "br_mult": round(sm["bankroll_final"]/100, 2),
            "dd": round(sm["dd_max"], 1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1), 2),
            "streak": sm["streak_red_max"],
            "n_combos": sm["n_combos"],
        })
    except Exception:
        pass

viable = [r for r in results if r["ratio"] >= 5 and r["br_mult"] >= 4]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n[Sizing] {len(viable)} viables (ratio ≥5×, BR ≥4)")

print(f"\n=== TOP 25 par RATIO ===")
for r in viable[:25]:
    print(f"  Ratio {r['ratio']:>5.1f}× | BR×{r['br_mult']:>4.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}")

print(f"\n=== TOP 15 par BR mult ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:15]:
    print(f"  BR×{r['br_mult']:>5.1f} ratio {r['ratio']:>4.1f}× | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€  | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/wfr_sizing.json","w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print("\nSaved.")
