#!/usr/bin/env python3
"""Sweep tennis WR strict isolé — angle jamais testé en isolation.
Tennis 1x2 favoris, WR ≥70/75/80%, classique + montante."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.backtester import backtest
from picks.montante_engine import simulate

WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

# === Classique tennis isolé ===
print("=== TENNIS CLASSIQUE WR strict ===")
CL_CANDS = []
for cmin, cmax in [(1.20, 1.40), (1.20, 1.50), (1.30, 1.60), (1.40, 1.80)]:
    for mc in [1, 2, 3, 5]:
        for mwr in [0.70, 0.75, 0.80]:
            for pct in [0.05, 0.07, 0.10]:
                CL_CANDS.append({
                    "id": f"TWR_T_{cmin}-{cmax}_mc{mc}_wr{mwr}_pct{int(pct*100)}",
                    "components": [{
                        "sport": "tennis", "market": "1x2",
                        "cote_min": cmin, "cote_max": cmax,
                        "sort_by": "wr", "max_legs": 1, "max_combos": mc,
                        "min_wr": mwr, "min_ev": None,
                    }],
                    "dedup": "max1",
                    "sizing": {"mode": "flat_pct", "pct": pct, "min_stake": 0.5},
                })

print(f"[Tennis classique] {len(CL_CANDS)} configs")
cl_results = []
for i, s in enumerate(CL_CANDS):
    if i % 30 == 0: print(f"  [{i}/{len(CL_CANDS)}]")
    try:
        r = backtest(s, "2026-01-01", "2026-04-30", bankroll0=100, excluded_leagues=WFR_EXCL)
        sm = r["summary"]
        if sm["n_combos"] == 0: continue
        cl_results.append({
            "id": s["id"], "strat": s,
            "pnl": round(sm["pnl"], 1),
            "br_mult": round(sm["bankroll_final"]/100, 2),
            "dd": round(sm["dd_max"], 1),
            "ratio": round(sm["pnl"]/max(sm["dd_max"],1), 2),
            "n_combos": sm["n_combos"],
        })
    except Exception:
        pass

cl_viable = [r for r in cl_results if r["ratio"] >= 5 and r["br_mult"] >= 1.5]
cl_viable.sort(key=lambda r: -r["ratio"])
print(f"\n[Tennis CL] {len(cl_viable)} viables (ratio≥5, BR×≥1.5)")
print("=== TOP 15 par RATIO ===")
for r in cl_viable[:15]:
    print(f"  Ratio {r['ratio']:>5.1f} | BR×{r['br_mult']:>5.1f} | +{r['pnl']:>5.0f}€ DD {r['dd']:>4.0f}€ #{r['n_combos']:>3d} | {r['id'][:55]}")

# === Montantes tennis ===
print("\n=== TENNIS MONTANTES WR strict ===")
MT_CANDS = []
for cmin, cmax in [(1.20, 1.40), (1.30, 1.60), (1.40, 1.80)]:
    for n_p in [3, 4, 5, 6]:
        for mwr in [0.70, 0.75, 0.80]:
            MT_CANDS.append({
                "id": f"TWR_MT_T_{cmin}-{cmax}_p{n_p}_wr{mwr}",
                "label": "Tennis montante WR strict",
                "components": [{
                    "sports": ["tennis"], "market": "1x2",
                    "cote_min": cmin, "cote_max": cmax,
                    "sort_by": "wr", "max_legs": 1, "max_combos": 1,
                    "min_wr": mwr, "min_ev": None,
                    "legs_per_palier": 1,
                }],
                "montante": {"initial_stake": INITIAL, "n_paliers_target": n_p,
                              "combo_legs_per_palier": 1},
            })

print(f"[Tennis montantes] {len(MT_CANDS)} configs")
mt_results = []
for i, s in enumerate(MT_CANDS):
    if i % 15 == 0: print(f"  [{i}/{len(MT_CANDS)}]")
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL,
                         excluded_leagues=WFR_EXCL)
            perfs[pname] = {
                "n_complete": r["n_cycles_complete"],
                "n_total": r["n_cycles_total"],
                "compl": round(r["completion_rate"]*100, 1),
                "avg_cap": round(r["avg_capital_complete"], 1),
                "pnl": round(r["final_pnl"], 1),
            }
        except Exception:
            perfs[pname] = None
    if perfs.get("S1-26") and perfs["S1-26"]["n_total"] >= 3:
        mt_results.append({"id": s["id"], "perfs": perfs, "strat": s})

def s1(r): return r["perfs"]["S1-26"]
def apr(r): return r["perfs"].get("Apr") or {"pnl":0}

mt_viable = [r for r in mt_results if s1(r)["compl"] >= 40]
mt_viable.sort(key=lambda r: -s1(r)["compl"])
print(f"\n[Tennis MT] {len(mt_viable)} viables (compl≥40%)")
print("=== TOP 15 par COMPLETION ===")
for r in mt_viable[:15]:
    s = s1(r); a = apr(r)
    print(f"  Compl {s['compl']:>5.1f}% | +{s['pnl']:>4.0f}€ cap{s['avg_cap']:>4.0f}€ #{s['n_complete']}/{s['n_total']} | Apr {a['pnl']:+5.0f}€ | {r['id'][:55]}")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/tennis_wr.json","w") as f:
    json.dump({"classique": cl_viable[:30], "montantes": mt_viable[:30]}, f, indent=2)
print("\nSaved to datasets/tennis_wr.json")
