#!/usr/bin/env python3
"""Sweep MEGA — re-test des top profils avec filtre Winamax FR strict.
Identifie les VRAIES top stratégies réalistes (pas dépendantes de ligues fantômes).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.strategy_loader import load_all
from picks.montante_engine import simulate
from picks.backtester import backtest

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

WINAMAX_FR_EXCLUDED = [
    "liga mx","egyptian","cyprus","ligapro","primera división, clausura",
    "brasileirão série d","brasileirão série b","scottish premiership",
    "first professional league","danish superliga","superliga",
    "niké liga","swiss super league","austrian bundesliga",
    "stoiximan super league","czech first league","canadian premier",
    "usl championship","copa de la liga","frauen-bundesliga",
    "serie a femminile","uefa champions league, women","liga acb",
    "germany bbl","wnba preseason","serie a2","del, playoffs",
    "relegation round"
]

print(f"[Sweep Winamax FR] {len(WINAMAX_FR_EXCLUDED)} ligues exclues\n")

all_strats = load_all()
classics = []
montantes = []
for sid, s in all_strats.items():
    is_m = s.get("mode") == "montante" or "montante" in s
    (montantes if is_m else classics).append((sid, s))

print(f"Classiques: {len(classics)} | Montantes: {len(montantes)}\n")

# === MONTANTES (mode intraday) ===
print("[1/2] Re-test montantes avec Winamax FR strict...")
mt_results = []
for i, (sid, s) in enumerate(montantes):
    if i % 20 == 0: print(f"  [{i}/{len(montantes)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            mode = s.get("montante", {}).get("preferred_mode", "intraday")
            r = simulate(s, ps, pe, mode=mode, initial_stake=INITIAL,
                         excluded_leagues=WINAMAX_FR_EXCLUDED)
            perfs[pname] = {
                "n_complete": r["n_cycles_complete"],
                "n_total": r["n_cycles_total"],
                "compl": round(r["completion_rate"]*100, 1),
                "avg_cap": round(r["avg_capital_complete"], 1),
                "pnl": round(r["final_pnl"], 1),
            }
        except Exception:
            perfs[pname] = None
    if perfs.get("S1-26"):
        mt_results.append({"id": sid, "label": s.get("label"), "perfs": perfs})

def s1m(r): return r["perfs"]["S1-26"]
def aprm(r): return r["perfs"].get("Apr") or {"pnl":0}

# Filter ≥30% completion + PnL >50€
mt_viable = [r for r in mt_results if s1m(r)["compl"] >= 30 and s1m(r)["pnl"] >= 50]
mt_viable.sort(key=lambda r: -(s1m(r)["pnl"] * s1m(r)["compl"]/100))

print(f"\n=== TOP 25 MONTANTES Winamax FR (par EV pratique) ===")
print(f"{'ID':<55s} {'Compl':>6s} {'PnL S1':>8s} {'Cap':>6s} {'Apr':>7s}")
print("-"*100)
for r in mt_viable[:25]:
    s = s1m(r); a = aprm(r)
    ev = s["pnl"] * s["compl"]/100
    print(f"{r['id'][:54]:<55s} {s['compl']:>5.0f}% +{s['pnl']:>5.0f}€ {s['avg_cap']:>5.0f}€  {a['pnl']:+5.0f}€")

# === CLASSIQUES ===
print(f"\n[2/2] Re-test classiques avec Winamax FR strict (peut prendre 5-10 min)...")
cls_results = []
for i, (sid, s) in enumerate(classics):
    if i % 5 == 0: print(f"  [{i}/{len(classics)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100,
                     excluded_leagues=WINAMAX_FR_EXCLUDED)
        sm = r["summary"]
        cls_results.append({
            "id": sid, "label": s.get("label"),
            "pnl": round(sm["pnl"], 1),
            "br_final": round(sm["bankroll_final"], 1),
            "br_mult": round(sm["bankroll_final"]/100, 2),
            "dd": round(sm["dd_max"], 1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1), 2),
            "streak": sm["streak_red_max"],
            "n_combos": sm["n_combos"],
            "wr": round(sm["wr_combos"]*100, 1),
        })
    except Exception as e:
        print(f"  err {sid}: {e}")

cls_viable = [r for r in cls_results if r["pnl"] >= 50 and r["dd"] <= 100]
cls_viable.sort(key=lambda r: -r["ratio"])

print(f"\n=== TOP 20 CLASSIQUES Winamax FR (par RATIO PnL/DD) ===")
print(f"{'ID':<55s} {'PnL':>7s} {'BRx':>5s} {'DD':>5s} {'Ratio':>6s} {'Strk':>4s} {'#':>4s}")
print("-"*100)
for r in cls_viable[:20]:
    print(f"{r['id'][:54]:<55s} +{r['pnl']:>5.0f}€ {r['br_mult']:>4.1f}x {r['dd']:>4.0f}€ {r['ratio']:>5.1f}x {r['streak']:>2d}j {r['n_combos']:>3d}")

# Save
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/winamax_fr_sweep.json","w") as f:
    json.dump({"montantes": mt_viable, "classics": cls_viable}, f, indent=2)
print("\nSaved.")
