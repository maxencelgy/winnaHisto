#!/usr/bin/env python3
"""Sweep v7 — Zones non explorées : cross-market combos foot, BTTS/OU pures, mid-cote.

Test sur S1-26 OOS strict (magic_cotes_smart_oos.json + extended_oos.json).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest

START = "2026-01-01"; END = "2026-04-30"
BANKROLL0 = 100.0

CANDS = []

# === Bloc A : BTTS-only foot (single, multi-combos) ===
for mkt in ["btts", "over_2_5", "over_1_5", "under_2_5"]:
    for cmin, cmax in [(1.30, 1.55), (1.40, 1.65), (1.50, 1.80), (1.60, 2.00)]:
        for mwr in [0.55, 0.60, 0.65]:
            for mc in [2, 3, 5]:
                for pct in [0.05, 0.08, 0.10]:
                    s = {
                        "id": f"A_foot_{mkt}_{cmin}-{cmax}_wr{mwr}_mc{mc}_pct{int(pct*100)}",
                        "label": "foot_market_pure",
                        "components": [{
                            "sport": "football", "market": mkt,
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    }
                    CANDS.append(s)

# === Bloc B : Cross-market combos foot 2j (1x2 + OU/BTTS dans le combo) ===
# Grâce à extract_picks "1x2,btts" qui mix les markets dans les combos
for mkt_set in ["1x2,btts", "1x2,over_2_5", "btts,over_2_5",
                "1x2,btts,over_2_5"]:
    for cmin, cmax in [(1.30, 1.60), (1.40, 1.80), (1.50, 2.00)]:
        for legs in [2, 3]:
            for mwr in [0.55, 0.60]:
                for mc in [1, 2]:
                    for pct in [0.05, 0.08]:
                        s = {
                            "id": f"B_xmkt_{mkt_set.replace(',','+')}_{cmin}-{cmax}_l{legs}_wr{mwr}_mc{mc}_pct{int(pct*100)}",
                            "label": "foot_xmkt_combo",
                            "components": [{
                                "sport": "football", "market": mkt_set,
                                "cote_min": cmin, "cote_max": cmax,
                                "sort_by": "wr", "max_legs": legs, "max_combos": mc,
                                "min_wr": mwr, "min_ev": None,
                            }],
                            "dedup": "max1",
                            "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                        }
                        CANDS.append(s)

# === Bloc C : Multi-comp foot OU + hockey 1x2 + basket 1x2 (mix sécurisé) ===
for foot_mkt in ["over_2_5", "btts"]:
    for foot_mc in [2, 3, 4]:
        for hockey_mc in [2, 3, 4]:
            for basket_mc in [1, 2, 3]:
                for pct in [0.05, 0.08, 0.10]:
                    for mwr in [0.55, 0.60]:
                        s = {
                            "id": f"C_FxOU+H+B_{foot_mkt}_F{foot_mc}H{hockey_mc}B{basket_mc}_wr{mwr}_pct{int(pct*100)}",
                            "label": "tri_safe_with_market",
                            "components": [
                                {"sport": "football", "market": foot_mkt,
                                 "cote_min": 1.40, "cote_max": 1.70,
                                 "sort_by": "wr", "max_legs": 1, "max_combos": foot_mc,
                                 "min_wr": mwr, "min_ev": None},
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

# === Bloc D : Combo 2j foot OU+1x2 single mc1 — pure stable ===
for cmin, cmax in [(1.40, 1.70), (1.50, 1.80), (1.60, 2.00)]:
    for mwr in [0.55, 0.60, 0.65]:
        for pct in [0.05, 0.08, 0.10, 0.12]:
            s = {
                "id": f"D_2j_xmkt_{cmin}-{cmax}_wr{mwr}_pct{int(pct*100)}",
                "label": "foot_2j_xmkt_stable",
                "components": [{
                    "sport": "football", "market": "1x2,btts,over_2_5",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "ev", "max_legs": 2, "max_combos": 1,
                    "min_wr": mwr, "min_ev": 1.05,
                }],
                "dedup": "max1",
                "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
            }
            CANDS.append(s)

# === Bloc E : Pure value picks single sport sort by EV (focus high-EV picks) ===
for sp in ["football", "ice-hockey", "basketball"]:
    for cmin, cmax in [(1.30, 1.60), (1.50, 1.80), (1.70, 2.00), (2.00, 2.50)]:
        for mev in [1.05, 1.10, 1.15]:
            for mc in [3, 5, 8]:
                for pct in [0.03, 0.05, 0.08]:
                    s = {
                        "id": f"E_{sp[:3]}_{cmin}-{cmax}_ev{mev}_mc{mc}_pct{int(pct*100)}",
                        "label": "value_single",
                        "components": [{
                            "sport": sp, "market": "1x2",
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": "ev", "max_legs": 1, "max_combos": mc,
                            "min_wr": None, "min_ev": mev,
                        }],
                        "dedup": "max1",
                        "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                    }
                    CANDS.append(s)

print(f"[v7] {len(CANDS)} candidats à tester")

results = []
for i, s in enumerate(CANDS):
    if i % 50 == 0:
        print(f"  [{i}/{len(CANDS)}]")
    try:
        r = backtest(s, START, END, bankroll0=BANKROLL0)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        results.append({
            "id": s["id"],
            "pnl": round(sm["pnl"], 2),
            "roi": round(sm["roi"], 1),
            "br_final": round(sm["bankroll_final"], 2),
            "br_mult": round(sm["bankroll_final"] / BANKROLL0, 2),
            "dd": round(sm["dd_max"], 2),
            "ratio": round(sm["pnl"] / max(sm["dd_max"], 1), 2),
            "streak_red": sm["streak_red_max"],
            "n_combos": sm["n_combos"],
            "wr": round(sm["wr_combos"]*100, 1),
            "n_days_played": sm["n_days_played"],
            "strat": s,
        })
    except Exception as e:
        pass

# Filtres
viable = [r for r in results if r["pnl"] >= 50 and r["br_mult"] >= 1.5 and r["dd"] <= 50]
viable.sort(key=lambda r: -r["ratio"])

print(f"\n=== TOP 25 par RATIO PnL/DD ===")
print(f"{'ID':<55s} {'PnL':>7s} {'ROI':>6s} {'BRx':>5s} {'DD':>6s} {'R':>5s} {'STR':>3s} {'#':>4s}")
print("-"*100)
for r in viable[:25]:
    print(f"{r['id'][:54]:<55s} {r['pnl']:>+6.0f}€ {r['roi']:>+5.0f}% {r['br_mult']:>4.1f}x {r['dd']:>5.0f}€ "
          f"{r['ratio']:>4.1f} {r['streak_red']:>2d}j {r['n_combos']:>3d}")

print(f"\n=== TOP 15 par PnL ===")
viable.sort(key=lambda r: -r["pnl"])
for r in viable[:15]:
    print(f"  {r['id'][:60]:<60s} +{r['pnl']:.0f}€  ROI {r['roi']:+.0f}%  ratio {r['ratio']}  DD {r['dd']:.0f}€")

print(f"\n=== TOP 15 par BR multiplier ===")
viable.sort(key=lambda r: -r["br_mult"])
for r in viable[:15]:
    print(f"  {r['id'][:60]:<60s} BR×{r['br_mult']:.1f}  PnL +{r['pnl']:.0f}€  DD {r['dd']:.0f}€")

# Save
out_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v7_results.json"
with open(out_path, "w") as f:
    json.dump({"all": results, "viable": viable[:50]}, f, indent=2)
print(f"\nSaved {out_path}")
