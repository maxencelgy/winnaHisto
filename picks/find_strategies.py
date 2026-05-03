#!/usr/bin/env python3
"""Sweep large pour trouver des stratégies prometteuses.

- 16 mois OOS pur avec magic recalibrée train<2025-01-01
- Critère : 5/6 trimestres positifs + streak ≤ 4 + PnL ≥ 100€/100€ BR
- Variations testées : singles 1x2/BTTS/Over par sport+cote+sort+sizing,
                       combos 2j single-sport et multi-sport,
                       min_wr filters
- Output : datasets/find_strategies_results.json
"""
import sys, os, json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest as run_strategy_backtest

# Charger magic 2025 (train<2025-01-01) directement dans le backtester
# On va construire des "stratégies" en dict puis run_strategy_backtest

PERIODS = [
    ("Q1-25", "2025-01-01", "2025-03-31"),
    ("Q2-25", "2025-04-01", "2025-06-30"),
    ("Q3-25", "2025-07-01", "2025-09-30"),
    ("Q4-25", "2025-10-01", "2025-12-31"),
    ("Q1-26", "2026-01-01", "2026-03-31"),
    ("Apr26", "2026-04-01", "2026-04-30"),
]


def build_strategy(label, components, sizing_mode="flat_pct", sizing_extra=None, dedup="max1"):
    sizing = {"mode": sizing_mode, "min_stake": 0.5}
    if sizing_mode == "flat_pct":
        sizing["pct"] = 0.10
    elif sizing_mode == "risk_tiered":
        sizing["tiers"] = [
            {"cote_max": 2.0, "pct": 0.08},
            {"cote_max": 3.5, "pct": 0.05},
            {"cote_max": 999, "pct": 0.02},
        ]
    elif sizing_mode == "kelly_fraction":
        sizing["kelly_div"] = 4.0
        sizing["cap_pct"] = 0.10
    if sizing_extra:
        sizing.update(sizing_extra)
    return {
        "id": label,
        "label": label,
        "components": components,
        "dedup": dedup,
        "sizing": sizing,
    }


def gen_candidates():
    out = []
    # Singles 1x2 par sport × cote × sort × max_combos × sizing
    for sport in ["football", "basketball", "ice-hockey", "baseball"]:
        for cmin, cmax in [(1.20, 1.45), (1.30, 1.55), (1.40, 1.70), (1.50, 1.85),
                           (1.60, 1.90), (1.70, 2.00), (1.80, 2.20), (1.90, 2.40)]:
            for sort in ["wr", "ev"]:
                for mc in [2, 3, 4]:
                    for sizing in ["flat_pct", "risk_tiered"]:
                        comp = {
                            "sport": sport, "market": "1x2",
                            "cote_min": cmin, "cote_max": cmax,
                            "sort_by": sort, "max_legs": 1, "max_combos": mc,
                            "min_wr": None, "min_ev": None,
                        }
                        out.append(build_strategy(
                            f"S_{sport[:4]}_{cmin}-{cmax}_{sort}_mc{mc}_{sizing}",
                            [comp], sizing))

    # Min_wr filter sur cotes value
    for sport in ["football", "basketball", "ice-hockey"]:
        for cmin, cmax in [(1.50, 2.20), (1.80, 2.50), (2.00, 2.80)]:
            for mwr in [0.65, 0.70, 0.75]:
                comp = {
                    "sport": sport, "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "ev", "max_legs": 1, "max_combos": 4,
                    "min_wr": mwr, "min_ev": None,
                }
                out.append(build_strategy(
                    f"WR_{sport[:4]}_{cmin}-{cmax}_wr{mwr}",
                    [comp], "flat_pct"))

    # Combos 2j single-sport
    for sport in ["football", "basketball", "ice-hockey"]:
        for ctmin, ctmax in [(1.7, 2.5), (2.0, 3.0), (2.5, 4.0), (3.0, 5.0)]:
            for sort in ["ev", "wr"]:
                for mc in [2, 3]:
                    for mwr in [None, 0.55, 0.60]:
                        comp = {
                            "sport": sport, "market": "1x2",
                            "cote_min": ctmin, "cote_max": ctmax,
                            "sort_by": sort, "max_legs": 2, "max_combos": mc,
                            "min_wr": mwr, "min_ev": None,
                        }
                        sizing = "risk_tiered"
                        out.append(build_strategy(
                            f"C2_{sport[:4]}_{ctmin}-{ctmax}_{sort}_mc{mc}_wr{mwr or 'no'}",
                            [comp], sizing))

    # BTTS oui foot
    for cmin, cmax in [(1.40, 1.60), (1.50, 1.75), (1.60, 1.85)]:
        for sort in ["wr", "ev"]:
            for mc in [2, 3]:
                comp = {
                    "sport": "football", "market": "btts",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": sort, "max_legs": 1, "max_combos": mc,
                    "side_filter": "oui",
                    "min_wr": None, "min_ev": None,
                }
                out.append(build_strategy(
                    f"BO_{cmin}-{cmax}_{sort}_mc{mc}",
                    [comp], "flat_pct"))

    return out


def evaluate(strategy):
    """Évalue sur 6 trimestres (16 mois OOS strict)."""
    res = {}
    for name, start, end in PERIODS:
        try:
            r = run_strategy_backtest(strategy, start, end, bankroll0=100)
            s = r["summary"]
            res[name] = {
                "pnl": round(s["pnl"], 1),
                "br_final": round(s["bankroll_final"], 1),
                "streak": s["streak_red_max"],
                "n_combos": s["n_combos"],
                "wr": round(s["wr_combos"], 3),
                "dd": round(s["dd_max"], 1),
            }
        except Exception as e:
            res[name] = {"error": str(e)}
    return res


def is_promising(eval_res):
    """5/6 trimestres positifs + streak ≤ 4 + total PnL ≥ 100."""
    valid_periods = [r for r in eval_res.values() if "pnl" in r]
    if len(valid_periods) < 6:
        return False
    n_pos = sum(1 for r in valid_periods if r["pnl"] > 0)
    if n_pos < 5:
        return False
    max_streak = max(r["streak"] for r in valid_periods)
    if max_streak > 4:
        return False
    total = sum(r["pnl"] for r in valid_periods)
    if total < 100:
        return False
    return True


def main():
    cands = gen_candidates()
    print(f"[sweep] {len(cands)} stratégies candidates")
    out = []
    for i, s in enumerate(cands):
        if i % 20 == 0:
            print(f"  [{i}/{len(cands)}] {s['id']}")
        ev = evaluate(s)
        out.append({"strategy": s, "eval": ev})

    # Filter promising
    promising = [r for r in out if is_promising(r["eval"])]
    promising.sort(key=lambda r: -sum(p.get("pnl", 0) for p in r["eval"].values() if "pnl" in p))

    print(f"\n[sweep] {len(promising)} stratégies prometteuses (5/6+ Q+, streak≤4, PnL≥100)\n")
    print(f"{'Strategy':50s} {'Q1-25':>7s} {'Q2-25':>7s} {'Q3-25':>7s} {'Q4-25':>7s} {'Q1-26':>7s} {'Apr26':>7s} {'TOT':>7s}")
    print("-" * 105)
    for r in promising[:30]:
        ev = r["eval"]
        parts = []
        for n, _, _ in PERIODS:
            p = ev.get(n, {}).get("pnl", 0)
            parts.append(f"{p:>+5.0f}€")
        total = sum(ev.get(n, {}).get("pnl", 0) for n, _, _ in PERIODS)
        print(f"  {r['strategy']['id']:48s} {' '.join(parts)} {total:>+5.0f}€")

    out_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/find_strategies_results.json"
    with open(out_path, "w") as f:
        json.dump({"all": out, "promising": promising}, f, indent=2, default=str)
    print(f"\n[sweep] Saved {out_path}")


if __name__ == "__main__":
    main()
