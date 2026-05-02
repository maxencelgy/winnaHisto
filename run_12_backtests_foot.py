#!/usr/bin/env python3
"""Run 12 football-only backtests over 2026-04-01 to 2026-05-02 and report ROI-sorted."""
import sys
from backtest_engine import run_backtest_period
from morning_live import load_magic

START = "2026-04-01"
END = "2026-05-02"
STAKE = 10
SPORTS = ["football"]

VARIANTS = [
    # (label, sort_by, max_legs, cote_min, cote_max, max_combos)
    ("EV 2j cote 1.5-3 max=5",  "ev",        2, 1.5,  3.0,  5),
    ("EV 2j cote 2-5 max=5",    "ev",        2, 2.0,  5.0,  5),
    ("EV 2j cote 3-8 max=5",    "ev",        2, 3.0,  8.0,  5),
    ("EV 3j cote 2-5 max=5",    "ev",        3, 2.0,  5.0,  5),
    ("EV 3j cote 3-8 max=5",    "ev",        3, 3.0,  8.0,  5),
    ("EV 3j cote 5-15 max=5",   "ev",        3, 5.0, 15.0,  5),
    ("EV 4j cote 5-15 max=5",   "ev",        4, 5.0, 15.0,  5),
    ("WR 2j cote 1.3-3 max=5",  "winrate",   2, 1.3,  3.0,  5),
    ("WR 3j cote 2-5 max=5",    "winrate",   3, 2.0,  5.0,  5),
    ("WR 3j cote 1.5-3 max=5",  "winrate",   3, 1.5,  3.0,  5),
    ("EV 3j cote 2-5 max=10",   "ev",        3, 2.0,  5.0, 10),
    ("EV 3j cote 2-5 max=3",    "ev",        3, 2.0,  5.0,  3),
]

def main():
    magic = load_magic()
    results = []
    for i, (label, sort_by, legs, cmin, cmax, mx) in enumerate(VARIANTS, 1):
        try:
            r = run_backtest_period(
                START, END, magic,
                sports_filter=SPORTS,
                max_legs=legs,
                cote_min=cmin,
                cote_max=cmax,
                max_combos=mx,
                sort_by=sort_by,
                stake=STAKE,
            )
            results.append({
                "i": i,
                "label": label,
                "n": r["n_combos_total"],
                "wr": r["wr_combos"] * 100,
                "pnl": r["pnl_total"],
                "roi": r["roi"] * 100,
            })
        except Exception as e:
            print(f"VARIANT {i} ({label}) ERROR: {e}", file=sys.stderr)
            results.append({"i": i, "label": label, "n": 0, "wr": 0, "pnl": 0, "roi": -999})

    # Print individual lines (in original order)
    print("\n=== RESULTS (input order) ===")
    for r in results:
        print(f"VARIANT {r['i']} : combos={r['n']} WR={r['wr']:.1f}% PnL={r['pnl']:.2f}€ ROI={r['roi']:.2f}%  [{r['label']}]")

    # Sort by ROI desc
    sorted_r = sorted(results, key=lambda x: x["roi"], reverse=True)
    print("\n=== SORTED BY ROI ===")
    for r in sorted_r:
        print(f"VARIANT {r['i']} : combos={r['n']} WR={r['wr']:.1f}% PnL={r['pnl']:.2f}€ ROI={r['roi']:.2f}%  [{r['label']}]")

    print("\n=== TOP 3 ===")
    for rank, r in enumerate(sorted_r[:3], 1):
        print(f"#{rank}  VARIANT {r['i']} [{r['label']}] -> ROI={r['roi']:.2f}% PnL={r['pnl']:.2f}€ WR={r['wr']:.1f}% combos={r['n']}")

if __name__ == "__main__":
    main()
