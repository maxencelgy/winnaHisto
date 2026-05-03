#!/usr/bin/env python3
"""Robustness check des NEW records — split S1-26 par mois."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest
from picks.strategy_loader import load_all

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

PERIODS = [
    ("Jan", "2026-01-01", "2026-01-31"),
    ("Feb", "2026-02-01", "2026-02-28"),
    ("Mar", "2026-03-01", "2026-03-31"),
    ("Apr", "2026-04-01", "2026-04-30"),
]

NEW_RECORDS = [
    "AGRO_F3H3_pct10_BR208",
    "AS_FT_F3H5T2_pct5_RATIO17_TENNIS",
    "AS_FT_F3H5T2_pct7_BR116_TENNIS",
    "MMC_BTTSO_F3H3_pct5_RATIO195",
    "MMC_BTTSO_F3H5_pct7_BR104_RATIO19",
    "MCA_xmkt_F3H5_pct7_BR96_RATIO19",
    "MCA_xmkt_F3H3_pct7_BR45_RATIO19",
    "MCA_xmkt_F3H5_pct10_BR517_JACKPOT",
    "foot_o15_mc5_pct8_BR19_WFR",
    "foot_o15_mc5_pct10_BR36_WFR",
]

all_strats = load_all()

print(f"\n{'Stratégie':<48s} {'Jan':>9s} {'Feb':>9s} {'Mar':>9s} {'Apr':>9s} | {'Total':>9s} | {'Robust':>7s}")
print("-"*120)
for sid in NEW_RECORDS:
    s = all_strats.get(sid)
    if not s:
        print(f"  ! {sid}")
        continue
    perfs = []
    for pname, ps, pe in PERIODS:
        try:
            r = backtest(s, ps, pe, bankroll0=100, excluded_leagues=WFR_EXCL)
            perfs.append(r["summary"]["pnl"])
        except Exception:
            perfs.append(0)
    total = sum(perfs)
    n_pos = sum(1 for p in perfs if p > 0)
    print(f"  {sid[:47]:<48s} {perfs[0]:>+7.0f}€  {perfs[1]:>+7.0f}€  {perfs[2]:>+7.0f}€  {perfs[3]:>+7.0f}€ | {total:>+7.0f}€ | {n_pos}/4")
