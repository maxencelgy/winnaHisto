#!/usr/bin/env python3
"""Run 12 multi-sport backtests over 2026-04-01 to 2026-05-02 and report ROI-sorted."""
import sys
from backtest_engine import run_backtest_period
from morning_live import load_magic

START = "2026-04-01"
END = "2026-05-02"
STAKE = 10

# (label, sports_filter, sort_by, max_legs, cote_min, cote_max, max_combos)
VARIANTS = [
    ("[foot,basket] EV 3j 2-5",          ["football", "basketball"],            "ev",      3, 2.0,  5.0,  5),
    ("[foot,tennis] EV 3j 2-5",          ["football", "tennis"],                "ev",      3, 2.0,  5.0,  5),
    ("[foot,baseball] EV 3j 2-5",        ["football", "baseball"],              "ev",      3, 2.0,  5.0,  5),
    ("[foot,hockey] EV 3j 2-5",          ["football", "ice-hockey"],            "ev",      3, 2.0,  5.0,  5),
    ("[foot,tennis,baseball] EV 3j 2-5", ["football", "tennis", "baseball"],    "ev",      3, 2.0,  5.0,  5),
    ("[foot,basket,tennis] EV 3j 2-5",   ["football", "basketball", "tennis"],  "ev",      3, 2.0,  5.0,  5),
    ("ALL EV 2j 1.5-3",                  None,                                  "ev",      2, 1.5,  3.0,  5),
    ("ALL EV 3j 2-5",                    None,                                  "ev",      3, 2.0,  5.0,  5),
    ("ALL EV 4j 5-15",                   None,                                  "ev",      4, 5.0, 15.0,  5),
    ("ALL WR 3j 1.5-3",                  None,                                  "winrate", 3, 1.5,  3.0,  5),
    ("ALL WR 2j 1.3-2.5",                None,                                  "winrate", 2, 1.3,  2.5,  5),
    ("[foot,basket] EV 4j 3-10",         ["football", "basketball"],            "ev",      4, 3.0, 10.0,  5),
]


def main():
    magic = load_magic()
    results = []
    for i, (label, sports, sort_by, legs, cmin, cmax, mx) in enumerate(VARIANTS, 1):
        kwargs = dict(
            max_legs=legs,
            cote_min=cmin,
            cote_max=cmax,
            max_combos=mx,
            sort_by=sort_by,
            stake=STAKE,
        )
        if sports is not None:
            kwargs["sports_filter"] = sports
        try:
            r = run_backtest_period(START, END, magic, **kwargs)
            results.append({
                "i": i,
                "label": label,
                "sports": sports if sports else "ALL",
                "n": r["n_combos_total"],
                "wr": r["wr_combos"] * 100,
                "pnl": r["pnl_total"],
                "roi": r["roi"] * 100,
            })
        except Exception as e:
            print(f"VARIANT {i} ({label}) ERROR: {e}", file=sys.stderr)
            results.append({"i": i, "label": label, "sports": sports, "n": 0, "wr": 0, "pnl": 0, "roi": -999})

    print("\n=== RESULTS (input order) ===")
    for r in results:
        sp = r["sports"] if isinstance(r["sports"], str) else ",".join(r["sports"])
        print(f"VARIANT {r['i']} : sports={sp} combos={r['n']} WR={r['wr']:.1f}% PnL={r['pnl']:.2f}€ ROI={r['roi']:.2f}%  [{r['label']}]")

    sorted_r = sorted(results, key=lambda x: x["roi"], reverse=True)
    print("\n=== SORTED BY ROI ===")
    for r in sorted_r:
        sp = r["sports"] if isinstance(r["sports"], str) else ",".join(r["sports"])
        print(f"VARIANT {r['i']} : sports={sp} combos={r['n']} WR={r['wr']:.1f}% PnL={r['pnl']:.2f}€ ROI={r['roi']:.2f}%  [{r['label']}]")

    print("\n=== TOP 3 ===")
    for rank, r in enumerate(sorted_r[:3], 1):
        sp = r["sports"] if isinstance(r["sports"], str) else ",".join(r["sports"])
        print(f"#{rank}  VARIANT {r['i']} [{r['label']}] sports={sp} -> ROI={r['roi']:.2f}% PnL={r['pnl']:.2f}€ WR={r['wr']:.1f}% combos={r['n']}")


if __name__ == "__main__":
    main()
