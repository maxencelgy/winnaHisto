#!/usr/bin/env python3
"""Sweep montantes v3 — Zones non explorées : BTTS, OU, cross-market combos.

Test sur S1-26 OOS strict + April 2026 isolé.
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [
    ("S1-26",   "2026-01-01", "2026-04-30"),
    ("Apr-26",  "2026-04-01", "2026-04-30"),
    ("Q1-26",   "2026-01-01", "2026-03-31"),
]

CANDS = []

# === Bloc 1 : BTTS-only foot intraday ===
# Cote BTTS oui ~1.45-1.65 → palier compound rapide
for cmin, cmax in [(1.30, 1.50), (1.40, 1.60), (1.50, 1.70), (1.55, 1.80)]:
    for n_p in [3, 4, 5, 6, 7]:
        for legs in [1, 2]:
            mwr = None  # pas de min_wr en BTTS pour avoir du volume
            CANDS.append({
                "id": f"M_btts_{cmin}-{cmax}_l{legs}_p{n_p}",
                "label": "Montante BTTS Oui foot",
                "components": [{
                    "sports": ["football"], "market": "btts",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

# === Bloc 2 : Over_2.5 foot intraday ===
for cmin, cmax in [(1.30, 1.50), (1.40, 1.60), (1.50, 1.70), (1.55, 1.80)]:
    for n_p in [3, 4, 5, 6, 7]:
        for legs in [1, 2]:
            CANDS.append({
                "id": f"M_o25_{cmin}-{cmax}_l{legs}_p{n_p}",
                "label": "Montante Over 2.5 foot",
                "components": [{
                    "sports": ["football"], "market": "over_2_5",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

# === Bloc 3 : Over_1.5 foot intraday (très safe) ===
for cmin, cmax in [(1.10, 1.20), (1.15, 1.30), (1.20, 1.35)]:
    for n_p in [5, 7, 10, 15]:
        CANDS.append({
            "id": f"M_o15_{cmin}-{cmax}_p{n_p}",
            "label": "Montante Over 1.5 ULTRA SAFE",
            "components": [{
                "sports": ["football"], "market": "over_1_5",
                "cote_min": cmin, "cote_max": cmax,
                "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                "min_wr": None, "min_ev": None,
                "legs_per_palier": 1,
            }],
            "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                          "combo_legs_per_palier": 1},
        })

# === Bloc 4 : Cross-market multi-leg (1x2 + BTTS + OU) ===
# Combos foot multi-market : la magic peut récupérer plusieurs picks par match
for mkt_set in ["1x2,btts", "1x2,over_2_5", "btts,over_2_5", "1x2,btts,over_2_5"]:
    for cmin, cmax in [(1.30, 1.55), (1.40, 1.70), (1.50, 1.85)]:
        for legs in [2, 3]:
            for n_p in [3, 4, 5]:
                CANDS.append({
                    "id": f"M_xmkt_{mkt_set.replace(',','+')}_{cmin}-{cmax}_l{legs}_p{n_p}",
                    "label": "Montante xmkt foot",
                    "components": [{
                        "sports": ["football"], "market": mkt_set,
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# === Bloc 5 : Hockey safe combo 2j ×3p,4p (zones courtes pour fréquence) ===
for cmin, cmax in [(1.10, 1.30), (1.20, 1.40), (1.30, 1.55)]:
    for n_p in [3, 4]:
        for legs in [1, 2, 3]:
            CANDS.append({
                "id": f"M_hk_l{legs}_{cmin}-{cmax}_p{n_p}",
                "label": "Montante Hockey court",
                "components": [{
                    "sports": ["ice-hockey"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                    "min_wr": None, "min_ev": None,
                    "legs_per_palier": legs,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": legs},
            })

# === Bloc 6 : Multi-sport combo court (foot+hockey+basket) ===
for sports in [["football","ice-hockey"],["football","basketball"],
               ["ice-hockey","basketball"],
               ["football","ice-hockey","basketball"]]:
    for cmin, cmax in [(1.20, 1.40), (1.30, 1.55), (1.40, 1.65)]:
        for legs in [2, 3]:
            for n_p in [3, 4]:
                CANDS.append({
                    "id": f"M_xs_{'+'.join(s[:3] for s in sports)}_{cmin}-{cmax}_l{legs}_p{n_p}",
                    "label": "Montante multisport court",
                    "components": [{
                        "sports": sports, "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": legs, "max_combos": 1,
                        "min_wr": None, "min_ev": None,
                        "legs_per_palier": legs,
                    }],
                    "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                                  "combo_legs_per_palier": legs},
                })

# === Bloc 7 : Mid-cote sort by EV ===
for sp in ["football","ice-hockey","basketball"]:
    for cmin, cmax in [(1.40, 1.70), (1.50, 1.85), (1.60, 2.00)]:
        for n_p in [3, 4, 5]:
            CANDS.append({
                "id": f"M_ev_{sp[:3]}_{cmin}-{cmax}_p{n_p}",
                "label": "Montante value mid-cote",
                "components": [{
                    "sports": [sp], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "ev", "max_legs": 1, "max_combos": 1,
                    "min_wr": None, "min_ev": 1.10,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[v3 montante] {len(CANDS)} configs × {len(PERIODS)} périodes = {len(CANDS)*len(PERIODS)} runs")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL)
            perfs[pname] = {
                "n_complete": r["n_cycles_complete"],
                "n_total": r["n_cycles_total"],
                "compl": round(r["completion_rate"]*100, 1),
                "avg_cap": round(r["avg_capital_complete"], 1),
                "roi": round(r["roi"], 1),
                "wr_p": round(r["wr_palier"]*100, 1),
                "pnl": round(r["final_pnl"], 1),
            }
        except Exception:
            perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_complete"] >= 1:
        results.append({
            "id": s["id"], "label": s["label"],
            "perfs": perfs, "strat": s,
        })

# Filter viables : completed ≥ 2 sur S1-26 ou ROI ≥ +200% sur S1-26
def s126(r): return r["perfs"].get("S1-26") or {"n_complete":0,"roi":0,"avg_cap":0,"compl":0}
def apr(r): return r["perfs"].get("Apr-26") or {"n_complete":0,"roi":0,"avg_cap":0}

viable = [r for r in results if (s126(r)["n_complete"] >= 2 or s126(r)["roi"] >= 100)]

print(f"\n[v3 montante] {len(viable)} viables ({len(results)} total)")

print(f"\n=== TOP 25 par CAPITAL × COMPLETION (S1-26) ===")
viable.sort(key=lambda r: -(s126(r)["avg_cap"] * s126(r)["compl"]/100))
print(f"{'ID':<55s} {'#✓/tot':>9s} {'%':>4s} {'AvgCap':>7s} {'ROI':>6s} {'WRp':>5s} | Apr ✓/tot ROI")
print("-"*120)
for r in viable[:25]:
    s = s126(r); a = apr(r)
    print(f"{r['id'][:54]:<55s} {s['n_complete']:>2d}/{s['n_total']:<3d}  {s['compl']:>3.0f}%  {s['avg_cap']:>6.0f}€ {s['roi']:>+5.0f}% {s['wr_p']:>4.0f}% | Apr {a['n_complete']}/{a['n_total']} ROI {a['roi']:+.0f}%")

print(f"\n=== TOP 15 par COMPLETION RATE S1-26 (n>=3 cycles) ===")
hi_compl = [r for r in viable if s126(r)["n_total"] >= 3]
hi_compl.sort(key=lambda r: -s126(r)["compl"])
for r in hi_compl[:15]:
    s = s126(r)
    print(f"  {r['id'][:55]:<55s}  {s['compl']:>3.0f}%  {s['n_complete']}/{s['n_total']}  cap {s['avg_cap']:.0f}€  ROI {s['roi']:+.0f}%")

print(f"\n=== TOP 15 par CAPITAL/cycle (S1-26) ===")
viable.sort(key=lambda r: -s126(r)["avg_cap"])
for r in viable[:15]:
    s = s126(r)
    print(f"  {r['id'][:55]:<55s}  {s['avg_cap']:>5.0f}€/cycle  {s['n_complete']}/{s['n_total']}  ROI {s['roi']:+.0f}%")

# Save
out_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_montantes_v3.json"
with open(out_path, "w") as f:
    json.dump({"all": results, "viable": viable[:80]}, f, indent=2)
print(f"\nSaved {out_path}")
