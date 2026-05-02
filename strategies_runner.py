#!/usr/bin/env python3
"""
Strategies exploration runner — tests 8 candidate strategies vs H7 baseline.
Each strategy = list of segments. A segment = filter+sort+cote band+max_combos.
Output: per-strategy ROI, walk-forward 5 semesters for top-3.
"""

import sys, os, json, time
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from datetime import date, timedelta
from backtest_engine import (
    _get_index, extract_picks, build_backtest_combos, load_matches_for_date
)
from morning_live import load_magic

MAGIC = load_magic()
STAKE = 10.0

# Define 9 strategies (H7 baseline + 8 new pistes)
# Each strategy = {name, segments: [{label, sports, leagues, cote_min, cote_max, max_legs, max_combos, sort_by}]}

FOOT_BASKET = ["football", "basketball"]
ALL_SPORTS = ["football", "basketball", "tennis", "ice-hockey", "baseball"]
TOP5_LEAGUES = {"England Premier League", "Spain La Liga", "Italy Serie A", "Germany Bundesliga", "France Ligue 1"}

STRATS = {
    "H7": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 10-50", "sports": ALL_SPORTS, "cote_min": 10.0, "cote_max": 50.0, "max_legs": 4, "max_combos": 2, "sort_by": "ev"},
    ],
    "P1_5combos": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 10-50", "sports": ALL_SPORTS, "cote_min": 10.0, "cote_max": 50.0, "max_legs": 4, "max_combos": 3, "sort_by": "ev"},
    ],
    "P2_5legs": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 10-50", "sports": ALL_SPORTS, "cote_min": 10.0, "cote_max": 50.0, "max_legs": 4, "max_combos": 1, "sort_by": "ev"},
        {"label": "EV5j multi 20-100", "sports": ALL_SPORTS, "cote_min": 20.0, "cote_max": 100.0, "max_legs": 5, "max_combos": 1, "sort_by": "ev"},
    ],
    "P3_triple_lottery": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 1, "sort_by": "ev"},
        {"label": "EV4j multi 10-50", "sports": ALL_SPORTS, "cote_min": 10.0, "cote_max": 50.0, "max_legs": 4, "max_combos": 3, "sort_by": "ev"},
    ],
    "P4_mix_sort": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "WR3j foot",   "sports": ["football"], "cote_min": 2.0, "cote_max": 5.0, "max_legs": 3, "max_combos": 2, "sort_by": "wr"},
    ],
    "P5_top5_leagues": [
        {"label": "EV3j top5 2-5", "sports": ["football"], "leagues": TOP5_LEAGUES, "cote_min": 2.0, "cote_max": 5.0, "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 10-50", "sports": ALL_SPORTS, "cote_min": 10.0, "cote_max": 50.0, "max_legs": 4, "max_combos": 2, "sort_by": "ev"},
    ],
    "P6_ultra_lottery": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 50-200", "sports": ALL_SPORTS, "cote_min": 50.0, "cote_max": 200.0, "max_legs": 4, "max_combos": 2, "sort_by": "ev"},
    ],
    "P7_3lottery_tight": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 12-40", "sports": ALL_SPORTS, "cote_min": 12.0, "cote_max": 40.0, "max_legs": 4, "max_combos": 3, "sort_by": "ev"},
    ],
    "P8_china_cba": [
        {"label": "EV3j fb 2-5",  "sports": FOOT_BASKET, "cote_min": 2.0, "cote_max": 5.0,  "max_legs": 3, "max_combos": 2, "sort_by": "ev"},
        {"label": "EV4j multi 10-50", "sports": ALL_SPORTS, "cote_min": 10.0, "cote_max": 50.0, "max_legs": 4, "max_combos": 1, "sort_by": "ev"},
        {"label": "EV3j China CBA", "sports": ["basketball"], "leagues": {"CBA"}, "cote_min": 2.0, "cote_max": 5.0, "max_legs": 3, "max_combos": 1, "sort_by": "ev"},
    ],
}


def daterange(start, end):
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)


def run_segment(matches_for_date, seg):
    """Run a single segment on cached matches list. Returns (n_combos, n_won, pnl)."""
    matches = matches_for_date
    if seg.get("sports"):
        matches = [m for m in matches if m["sport"] in seg["sports"]]
    if seg.get("leagues"):
        matches = [m for m in matches if m["league"] in seg["leagues"]]
    if not matches:
        return 0, 0, 0.0
    picks = extract_picks(matches, MAGIC)
    if not picks:
        return 0, 0, 0.0
    combos = build_backtest_combos(
        picks,
        max_legs=seg["max_legs"],
        cote_min=seg["cote_min"],
        cote_max=seg["cote_max"],
        max_combos=seg["max_combos"],
        sort_by=seg["sort_by"],
    )
    n_combos = len(combos)
    n_won = sum(1 for c in combos if c["won"])
    pnl = sum(STAKE * (c["cote_t"] - 1) if c["won"] else -STAKE for c in combos)
    return n_combos, n_won, pnl


def backtest_strategy(strat_segments, start, end):
    idx = _get_index()
    total_combos = 0
    total_won = 0
    total_pnl = 0.0
    n_days_played = 0
    for d in daterange(start, end):
        day_matches = idx.get(d, [])
        if not day_matches:
            continue
        day_combos = 0
        day_pnl = 0.0
        for seg in strat_segments:
            nc, nw, pnl = run_segment(day_matches, seg)
            day_combos += nc
            total_combos += nc
            total_won += nw
            day_pnl += pnl
            total_pnl += pnl
        if day_combos > 0:
            n_days_played += 1
    total_stake = total_combos * STAKE
    roi = total_pnl / total_stake if total_stake else 0
    return {
        "n_combos": total_combos,
        "n_won": total_won,
        "wr": total_won / total_combos if total_combos else 0,
        "pnl": total_pnl,
        "stake": total_stake,
        "roi": roi,
        "n_days_played": n_days_played,
    }


def run_full_period(strats_to_run, start="2024-01-01", end="2026-05-02"):
    results = {}
    for name in strats_to_run:
        t0 = time.time()
        r = backtest_strategy(STRATS[name], start, end)
        r["elapsed_s"] = round(time.time() - t0, 1)
        results[name] = r
        print(f"{name:24s} pnl={r['pnl']:>10.0f}  roi={r['roi']*100:>7.1f}%  combos={r['n_combos']:>6d}  wr={r['wr']*100:>5.1f}%  days={r['n_days_played']:>4d}  ({r['elapsed_s']}s)", flush=True)
    return results


def run_walk_forward(strat_name, semesters):
    out = []
    for sem_name, s, e in semesters:
        r = backtest_strategy(STRATS[strat_name], s, e)
        out.append({"semester": sem_name, **r})
        print(f"  {strat_name} {sem_name}: pnl={r['pnl']:.0f}  roi={r['roi']*100:.1f}%  combos={r['n_combos']}  wr={r['wr']*100:.1f}%", flush=True)
    return out


SEMESTERS = [
    ("S1-2024", "2024-01-01", "2024-06-30"),
    ("S2-2024", "2024-07-01", "2024-12-31"),
    ("S1-2025", "2025-01-01", "2025-06-30"),
    ("S2-2025", "2025-07-01", "2025-12-31"),
    ("S1-2026", "2026-01-01", "2026-05-02"),
]
