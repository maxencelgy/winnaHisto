#!/usr/bin/env python3
"""LONG-TERM ROBUSTNESS — test top profils sur 2025 (12 mois)
Note: magic trained <2026-01-01 donc partiellement utilisé pour 2025,
mais reste utile pour confirmer la stabilité long-terme."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest
from picks.montante_engine import simulate
from picks.strategy_loader import load_all

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

# 2025 par trimestre
PERIODS = [
    ("Q1-25", "2025-01-01", "2025-03-31"),
    ("Q2-25", "2025-04-01", "2025-06-30"),
    ("Q3-25", "2025-07-01", "2025-09-30"),
    ("Q4-25", "2025-10-01", "2025-12-31"),
    ("S1-26", "2026-01-01", "2026-04-30"),  # vrai OOS
]

TOP_CLASSICS = [
    "MMC_BTTSO_F3H3_pct5_RATIO195",
    "MCA_xmkt_F3H5_pct7_BR96_RATIO19",
    "foot_o15_mc5_TOP_RATIO_WFR",
    "foot_o15_mc5_pct8_BR19_WFR",
    "foot_pure_o15_safe_ratio57",
]
TOP_MONTANTES = [
    "montante_xmkt_OU_x4p_TOP_EV_WFR",
    "montante_xmkt_BTTSO_x3p_71pct_RECORD",
    "montante_xmkt_OU_combo3j_x2p_apr_record",
    "montante_o25_x2p_TOP_PRACTICAL",
    "montante_hockey_combo2j_x2p_TOP_PRACTICAL",
]

all_strats = load_all()

print("="*100)
print("CLASSIQUES — Perf trimestrielle 2025 + S1-26 (Winamax FR)")
print("="*100)
print(f"{'ID':<48s} {'Q1-25':>9s} {'Q2-25':>9s} {'Q3-25':>9s} {'Q4-25':>9s} | {'S1-26':>9s} | {'5/5':>5s}")
print("-"*120)
for sid in TOP_CLASSICS:
    s = all_strats.get(sid)
    if not s:
        print(f"  ! {sid} not found"); continue
    perfs = []
    for pname, ps, pe in PERIODS:
        try:
            r = backtest(s, ps, pe, bankroll0=100, excluded_leagues=WFR_EXCL)
            perfs.append(r["summary"]["pnl"])
        except Exception:
            perfs.append(0)
    n_pos = sum(1 for p in perfs if p > 0)
    print(f"  {sid[:47]:<48s} {perfs[0]:>+7.0f}€  {perfs[1]:>+7.0f}€  {perfs[2]:>+7.0f}€  {perfs[3]:>+7.0f}€ | {perfs[4]:>+7.0f}€ | {n_pos}/5")

print()
print("="*100)
print("MONTANTES — Perf trimestrielle 2025 + S1-26")
print("="*100)
print(f"{'ID':<48s} {'Q1-25':>9s} {'Q2-25':>9s} {'Q3-25':>9s} {'Q4-25':>9s} | {'S1-26':>9s} | {'5/5':>5s}")
print("-"*120)
for sid in TOP_MONTANTES:
    s = all_strats.get(sid)
    if not s:
        print(f"  ! {sid} not found"); continue
    perfs = []
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=10, excluded_leagues=WFR_EXCL)
            perfs.append(r["final_pnl"])
        except Exception:
            perfs.append(0)
    n_pos = sum(1 for p in perfs if p > 0)
    print(f"  {sid[:47]:<48s} {perfs[0]:>+7.0f}€  {perfs[1]:>+7.0f}€  {perfs[2]:>+7.0f}€  {perfs[3]:>+7.0f}€ | {perfs[4]:>+7.0f}€ | {n_pos}/5")

print("\nDone.")
