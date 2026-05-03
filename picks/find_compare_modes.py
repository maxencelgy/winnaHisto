#!/usr/bin/env python3
"""Compare mode 'intraday' (chronologique = backtest officiel)
   vs mode 'intraday_wr' (sort par WR/EV) sur les top profils pratiques.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.strategy_loader import load_all
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

# Top profils pratiques (>=40% completion en chronologique)
PROFILES = [
    "montante_o25_x2p_TOP_PRACTICAL",
    "montante_hockey_combo2j_x2p_TOP_PRACTICAL",
    "montante_hockey_combo2j_x2p_max_freq",
    "montante_o15_x4p_top_completion",
    "montante_hockeybasket_combo3j_x3p_practical",
    "montante_o15_combo2j_x2p_apr_freq",
    "montante_o15_x2p_66pct_safe",
    "montante_basket_combo2j_x2p_practical",
    "montante_btts_x2p_practical",
    "montante_o15_x4p_apr_winner",
    # Et quelques jackpots pour voir si WR-mode aide
    "montante_o15_combo10j_x4p_ULTIMATE",
    "montante_o15_combo8j_x5p_NUCLEAR",
    "montante_hockey_combo2j_x3p_top_pnl",
    "montante_foothockey_combo3j_x4p_top_pnl",
]

all_strats = load_all()

print(f"\n{'Profile':<55s} {'Mode':>14s} {'Compl':>6s} {'PnL S1':>9s} {'PnL Apr':>9s} {'Cap':>6s}")
print("-" * 115)

results = []
for sid in PROFILES:
    s = all_strats.get(sid)
    if not s:
        print(f"  ! {sid} not found")
        continue
    for mode in ["intraday", "intraday_wr"]:
        for pname, ps, pe in PERIODS:
            try:
                r = simulate(s, ps, pe, mode=mode, initial_stake=INITIAL)
                results.append({
                    "sid": sid, "mode": mode, "period": pname,
                    "compl": round(r["completion_rate"]*100, 1),
                    "pnl": round(r["final_pnl"], 1),
                    "cap": round(r["avg_capital_complete"], 1),
                    "n_complete": r["n_cycles_complete"],
                    "n_total": r["n_cycles_total"],
                })
            except Exception as e:
                print(f"  err {sid} {mode}: {e}")

# Print comparison side-by-side per profile
print(f"\n=== COMPARAISON PAR PROFIL (S1-26 et Apr) ===\n")
print(f"{'Profile':<48s} | {'CHRONO':>30s} | {'WR-MODE':>30s} | Diff")
print(f"{'':<48s} | {'Compl PnL_S1 PnL_Apr':>30s} | {'Compl PnL_S1 PnL_Apr':>30s}")
print("-" * 175)
for sid in PROFILES:
    chr_s1 = next((r for r in results if r["sid"]==sid and r["mode"]=="intraday" and r["period"]=="S1-26"), None)
    chr_ap = next((r for r in results if r["sid"]==sid and r["mode"]=="intraday" and r["period"]=="Apr"), None)
    wr_s1  = next((r for r in results if r["sid"]==sid and r["mode"]=="intraday_wr" and r["period"]=="S1-26"), None)
    wr_ap  = next((r for r in results if r["sid"]==sid and r["mode"]=="intraday_wr" and r["period"]=="Apr"), None)
    if not all([chr_s1, chr_ap, wr_s1, wr_ap]): continue
    diff_s1 = wr_s1["pnl"] - chr_s1["pnl"]
    diff_ap = wr_ap["pnl"] - chr_ap["pnl"]
    sign = "✓" if (diff_s1 > 0 and diff_ap > 0) else "✗" if (diff_s1 < 0 and diff_ap < 0) else "~"
    print(f"{sid[:47]:<48s} | {chr_s1['compl']:>4.0f}% +{chr_s1['pnl']:>5.0f} +{chr_ap['pnl']:>5.0f} | "
          f"{wr_s1['compl']:>4.0f}% +{wr_s1['pnl']:>5.0f} +{wr_ap['pnl']:>5.0f} | "
          f"{sign} S1{diff_s1:+.0f} Apr{diff_ap:+.0f}")

# Aggregate
chr_total_s1 = sum(r["pnl"] for r in results if r["mode"]=="intraday" and r["period"]=="S1-26")
wr_total_s1  = sum(r["pnl"] for r in results if r["mode"]=="intraday_wr" and r["period"]=="S1-26")
chr_total_ap = sum(r["pnl"] for r in results if r["mode"]=="intraday" and r["period"]=="Apr")
wr_total_ap  = sum(r["pnl"] for r in results if r["mode"]=="intraday_wr" and r["period"]=="Apr")

print(f"\n=== TOTAUX (cumul tous profils) ===")
print(f"  CHRONO (backtest officiel)  : S1 +{chr_total_s1:.0f}€  Apr +{chr_total_ap:.0f}€")
print(f"  WR-MODE (off-script)         : S1 +{wr_total_s1:.0f}€  Apr +{wr_total_ap:.0f}€")
print(f"  Diff                          : S1 {wr_total_s1-chr_total_s1:+.0f}€  Apr {wr_total_ap-chr_total_ap:+.0f}€")
print(f"  → {'WR mieux' if wr_total_s1>chr_total_s1 else 'CHRONO mieux'} sur S1, "
      f"{'WR mieux' if wr_total_ap>chr_total_ap else 'CHRONO mieux'} sur Apr")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/compare_modes.json","w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved. Total {len(results)} runs.")
