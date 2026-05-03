#!/usr/bin/env python3
"""ROBUSTNESS CHECK — décompose la perf des top stratégies en sous-périodes
pour détecter overfit/lucky-runs."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest
from picks.montante_engine import simulate
from picks.strategy_loader import load_all

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

# Décomposition S1-26 en mois individuels
PERIODS = [
    ("Jan",   "2026-01-01", "2026-01-31"),
    ("Feb",   "2026-02-01", "2026-02-28"),
    ("Mar",   "2026-03-01", "2026-03-31"),
    ("Apr",   "2026-04-01", "2026-04-30"),
]

# Top stratégies à tester
TOP_CLASSICS = [
    "MMC_BTTSO_F3H3_pct5_RATIO195",
    "MCA_xmkt_F3H5_pct7_BR96_RATIO19",
    "foot_o15_mc5_TOP_RATIO_WFR",
    "foot_o15_mc5_pct8_BR19_WFR",
    "foot_pure_o15_safe_ratio57",
    "multi_F5H3B1_TOP_BRMULT_WFR",
]
TOP_MONTANTES = [
    "montante_xmkt_OU_x4p_TOP_EV_WFR",
    "montante_xmkt_OU_combo3j_x2p_apr_record",
    "montante_xmkt_BTTSO_x3p_71pct_RECORD",
    "montante_wfr_xmkt_combo2j_x3p_TOP_PNL",
    "montante_o25_x2p_TOP_PRACTICAL",
    "montante_hockey_combo2j_x2p_TOP_PRACTICAL",
]

all_strats = load_all()

print("="*100)
print("CLASSIQUES — Perf par mois (filter Winamax FR)")
print("="*100)
print(f"{'ID':<48s} {'Jan':>10s} {'Feb':>10s} {'Mar':>10s} {'Apr':>10s} | {'TOTAL':>10s} | {'Robust':>8s}")
print("-"*120)
for sid in TOP_CLASSICS:
    s = all_strats.get(sid)
    if not s:
        print(f"  ! {sid} not found")
        continue
    monthly = []
    for pname, ps, pe in PERIODS:
        try:
            r = backtest(s, ps, pe, bankroll0=100, excluded_leagues=WFR_EXCL)
            monthly.append(r["summary"]["pnl"])
        except Exception as e:
            monthly.append(0)
    total = sum(monthly)
    n_pos = sum(1 for m in monthly if m > 0)
    robust = f"{n_pos}/4"
    print(f"  {sid[:47]:<48s} {monthly[0]:>+8.0f}€  {monthly[1]:>+8.0f}€  {monthly[2]:>+8.0f}€  {monthly[3]:>+8.0f}€ | {total:>+8.0f}€ | {robust:>8s}")

print()
print("="*100)
print("MONTANTES — Perf par mois (mode intraday, Winamax FR)")
print("="*100)
print(f"{'ID':<48s} {'Jan':>9s}({''}) {'Feb':>9s} {'Mar':>9s} {'Apr':>9s} | {'TOTAL':>10s} | {'Robust':>8s}")
print("-"*120)
for sid in TOP_MONTANTES:
    s = all_strats.get(sid)
    if not s:
        print(f"  ! {sid} not found")
        continue
    monthly = []
    monthly_compl = []
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=10, excluded_leagues=WFR_EXCL)
            monthly.append(r["final_pnl"])
            monthly_compl.append(r["completion_rate"]*100 if r["n_cycles_total"] else 0)
        except Exception as e:
            monthly.append(0); monthly_compl.append(0)
    total = sum(monthly)
    n_pos = sum(1 for m in monthly if m > 0)
    robust = f"{n_pos}/4"
    print(f"  {sid[:47]:<48s} {monthly[0]:>+5.0f}€({monthly_compl[0]:>2.0f}%)  {monthly[1]:>+5.0f}€({monthly_compl[1]:>2.0f}%)  {monthly[2]:>+5.0f}€({monthly_compl[2]:>2.0f}%)  {monthly[3]:>+5.0f}€({monthly_compl[3]:>2.0f}%) | {total:>+5.0f}€ | {robust:>8s}")
