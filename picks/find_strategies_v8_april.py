#!/usr/bin/env python3
"""Sweep v8 — FOCUS AVRIL 2026 (mois récent).

Test sur Avril seul + valid sur S1-26 Q1-26 pour s'assurer qu'on n'overfit pas Avril.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

PERIODS = [
    ("Apr-26", "2026-04-01", "2026-04-30"),
    ("Q1-26",  "2026-01-01", "2026-03-31"),
    ("S1-26",  "2026-01-01", "2026-04-30"),
]
BANKROLL0 = 100.0

CANDS = []

# Sweep ciblé Avril : combos solides courte fenêtre
# A. Multi-sport combo 2j cote modérée
for sports in [["football","ice-hockey"],["football","ice-hockey","basketball"],
               ["football","ice-hockey","basketball","tennis"]]:
    for cmin, cmax in [(1.30, 1.55), (1.40, 1.70), (1.50, 1.85)]:
        for legs in [2, 3]:
            for mc in [1, 2, 3]:
                for pct in [0.05, 0.08, 0.10]:
                    for sort in ["ev", "wr"]:
                        s = {
                            "id": f"V8_xs_{'+'.join(s[:3] for s in sports)}_{cmin}-{cmax}_l{legs}_mc{mc}_{sort}_pct{int(pct*100)}",
                            "label": "v8_combo_xsport",
                            "components": [{
                                "sports": sports, "market": "1x2",
                                "cote_min": cmin, "cote_max": cmax,
                                "sort_by": sort, "max_legs": legs, "max_combos": mc,
                                "min_wr": 0.55, "min_ev": None,
                            }],
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                        }
                        CANDS.append(s)

# B. Cross-market foot (1x2 + BTTS ou Over_2_5) en combo
for mkt_set in ["1x2,btts", "1x2,over_2_5", "btts,over_2_5"]:
    for cmin, cmax in [(1.30, 1.60), (1.40, 1.70), (1.50, 1.85)]:
        for legs in [2, 3]:
            for mc in [1, 2]:
                for pct in [0.05, 0.08, 0.10]:
                    s = {
                        "id": f"V8_xmkt_{mkt_set.replace(',','+')}_{cmin}-{cmax}_l{legs}_mc{mc}_pct{int(pct*100)}",
                        "label": "v8_combo_xmkt",
                        "components": [{
                            "sport": "football", "market": mkt_set,
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": "wr", "max_legs": legs, "max_combos": mc,
                            "min_wr": 0.55, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    }
                    CANDS.append(s)

# C. Multi-comp F+H+B avec value-foot mid-cote
for foot_cote in [(1.7, 2.0), (1.8, 2.2), (1.9, 2.4)]:
    for foot_mc in [1, 2]:
        for hockey_mc in [3, 5, 7]:
            for basket_mc in [2, 3, 5]:
                for pct in [0.05, 0.08, 0.10]:
                    s = {
                        "id": f"V8_FvHB_{foot_cote[0]}-{foot_cote[1]}_F{foot_mc}H{hockey_mc}B{basket_mc}_pct{int(pct*100)}",
                        "label": "v8_value_foot_safe_HB",
                        "components": [
                            {"sport": "football", "market": "1x2",
                             "cote_min": foot_cote[0], "cote_max": foot_cote[1],
                             "sort_by": "ev", "max_legs": 1, "max_combos": foot_mc,
                             "min_wr": None, "min_ev": None},
                            {"sport": "ice-hockey", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.40,
                             "sort_by": "wr", "max_legs": 1, "max_combos": hockey_mc,
                             "min_wr": 0.65, "min_ev": None},
                            {"sport": "basketball", "market": "1x2",
                             "cote_min": 1.20, "cote_max": 1.40,
                             "sort_by": "wr", "max_legs": 1, "max_combos": basket_mc,
                             "min_wr": 0.65, "min_ev": None},
                        ],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    }
                    CANDS.append(s)

print(f"[v8 april] {len(CANDS)} candidats")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0: print(f"  [{i}/{len(CANDS)}]")
    perfs = {}
    try:
        for pname, ps, pe in PERIODS:
            r = backtest(s, ps, pe, bankroll0=BANKROLL0)
            sm = r["summary"]
            perfs[pname] = {
                "pnl": round(sm["pnl"], 2),
                "roi": round(sm["roi"], 1),
                "br_mult": round(sm["bankroll_final"]/BANKROLL0, 2),
                "dd": round(sm["dd_max"], 2),
                "ratio": round(sm["pnl"]/max(sm["dd_max"],1), 2),
                "streak": sm["streak_red_max"],
                "n_combos": sm["n_combos"],
            }
        results.append({"id": s["id"], "perfs": perfs, "strat": s})
    except Exception:
        pass

# Filter : Apr ET S1-26 positifs ET DD raisonnable
def apr(r): return r["perfs"]["Apr-26"]
def s126(r): return r["perfs"]["S1-26"]
def q126(r): return r["perfs"]["Q1-26"]

viable = [r for r in results
          if apr(r)["pnl"] > 0 and s126(r)["pnl"] > 0
          and apr(r)["dd"] < 80 and s126(r)["dd"] < 80
          and s126(r)["n_combos"] > 30]

print(f"\n[v8 april] {len(viable)} viables Apr+S126 positifs")

print(f"\n=== TOP 25 par PnL Apr-26 (S126 positif aussi) ===")
viable.sort(key=lambda r: -apr(r)["pnl"])
print(f"{'ID':<55s} {'AprPnL':>7s} {'AprBRx':>6s} {'AprDD':>6s} {'AprStr':>6s} | {'S1PnL':>7s} {'S1Ratio':>7s} {'S1Str':>5s}")
print("-"*125)
for r in viable[:25]:
    a = apr(r); s = s126(r); q = q126(r)
    print(f"{r['id'][:54]:<55s} {a['pnl']:>+5.0f}€  {a['br_mult']:>4.1f}x  {a['dd']:>4.0f}€   {a['streak']:>2d}j  "
          f"| {s['pnl']:>+5.0f}€   {s['ratio']:>5.1f}   {s['streak']:>2d}j")

print(f"\n=== TOP 15 par RATIO S1-26 ===")
viable.sort(key=lambda r: -s126(r)["ratio"])
for r in viable[:15]:
    a = apr(r); s = s126(r)
    print(f"  {r['id'][:55]:<55s}  S1 +{s['pnl']:.0f}€ ratio {s['ratio']}  | Apr +{a['pnl']:.0f}€ DD {a['dd']:.0f}€")

# Save
out_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v8_april.json"
with open(out_path, "w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print(f"\nSaved {out_path}")
