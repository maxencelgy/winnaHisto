#!/usr/bin/env python3
"""Sweep sizing avancé sur le profil GOAT (F3+H5 BTTS+OU WR≥70%) — tenter battre BR×336."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

# Profil GOAT validé : F3+H5 BTTS+OU 1.20-1.40 WR≥70% pct10 → BR×336 ratio 24.4×
GOAT_COMPS = [{
    "sport": "football", "market": "btts,over_1_5,over_2_5",
    "cote_min": 1.20, "cote_max": 1.40,
    "sort_by": "wr", "max_legs": 1, "max_combos": 3,
    "min_wr": 0.70, "min_ev": None,
}, {
    "sport": "ice-hockey", "market": "1x2",
    "cote_min": 1.20, "cote_max": 1.50,
    "sort_by": "wr", "max_legs": 1, "max_combos": 5,
    "min_wr": 0.70, "min_ev": None,
}]

CANDS = []

# A. Kelly fractional sur GOAT
for kelly_div in [2, 3, 4, 5, 6, 8, 10]:
    for cap_pct in [0.05, 0.07, 0.10, 0.12, 0.15, 0.20]:
        CANDS.append({
            "id": f"GOAT_KELLY_div{kelly_div}_cap{int(cap_pct*100)}",
            "components": GOAT_COMPS,
            "dedup": "max1",
            "sizing": {"mode": "kelly_fraction", "kelly_div": kelly_div,
                       "cap_pct": cap_pct, "min_stake": 0.5},
        })

# B. EV proportional sur GOAT
for base_pct in [0.03, 0.05, 0.07, 0.10]:
    for ev_factor in [0.20, 0.30, 0.50, 0.80]:
        for cap_pct in [0.10, 0.15, 0.20]:
            CANDS.append({
                "id": f"GOAT_EVP_b{int(base_pct*100)}_f{int(ev_factor*100)}_c{int(cap_pct*100)}",
                "components": GOAT_COMPS,
                "dedup": "max1",
                "sizing": {"mode": "ev_proportional", "base_pct": base_pct,
                           "ev_factor": ev_factor, "cap_pct": cap_pct, "min_stake": 0.5},
            })

# C. Risk tiered sur GOAT
for tier_set in [
    {"hi": 0.15, "mid": 0.10, "lo": 0.05, "wr_hi": 0.80, "wr_mid": 0.70},
    {"hi": 0.20, "mid": 0.12, "lo": 0.07, "wr_hi": 0.80, "wr_mid": 0.70},
    {"hi": 0.12, "mid": 0.08, "lo": 0.04, "wr_hi": 0.75, "wr_mid": 0.65},
    {"hi": 0.18, "mid": 0.12, "lo": 0.06, "wr_hi": 0.75, "wr_mid": 0.65},
]:
    sid = f"GOAT_RTIER_h{int(tier_set['hi']*100)}_m{int(tier_set['mid']*100)}_l{int(tier_set['lo']*100)}_wh{int(tier_set['wr_hi']*100)}"
    CANDS.append({
        "id": sid,
        "components": GOAT_COMPS,
        "dedup": "max1",
        "sizing": {"mode": "risk_tiered", "min_stake": 0.5,
                   "tier_pct": {"hi": tier_set["hi"], "mid": tier_set["mid"], "lo": tier_set["lo"]},
                   "tier_wr": {"hi": tier_set["wr_hi"], "mid": tier_set["wr_mid"]}},
    })

print(f"[GOAT sizing] {len(CANDS)} configs")

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
    except Exception as e:
        pass

# Tri par BR mult (battre 336)
results.sort(key=lambda r: -r["br_mult"])
print(f"\n=== TOP 15 par BR mult (record actuel BR×336) ===")
for r in results[:15]:
    flag = " 🏆" if r["br_mult"] > 336 else ""
    print(f"  BR×{r['br_mult']:>6.1f} ratio {r['ratio']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}{flag}")

# Tri par ratio (battre 24.4)
results.sort(key=lambda r: -r["ratio"])
print(f"\n=== TOP 15 par RATIO (record actuel 24.4×) ===")
for r in results[:15]:
    flag = " 🏆" if r["ratio"] > 24.4 else ""
    print(f"  Ratio {r['ratio']:>5.1f}× BR×{r['br_mult']:>6.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}{flag}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/goat_sizing.json","w") as f:
    json.dump({"all": results, "top_br": sorted(results, key=lambda r:-r["br_mult"])[:30],
               "top_ratio": sorted(results, key=lambda r:-r["ratio"])[:30]}, f, indent=2)
print("\nSaved.")
