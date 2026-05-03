#!/usr/bin/env python3
"""Sweep META MIX — tester combinaisons multi-strats simulées en parallèle.

L'idée : si l'user lance K montantes en parallèle (capital indépendant 10€×K),
calculer le PnL net cumulé global sur S1-26 et Avril.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.montante_engine import simulate

INITIAL = 10
PERIODS = [("S1-26", "2026-01-01", "2026-04-30"),
           ("Apr",   "2026-04-01", "2026-04-30")]

# Top picks par profil (selon résultats sweeps)
TOP_PICKS = {
    "ultra_freq": {"id":"o15_x2p_80pct","sports":["football"],"market":"over_1_5",
                    "cmin":1.10,"cmax":1.25,"sort":"ev","legs":1,"n_p":2},
    "hk_super_freq": {"id":"hk_x3_71pct","sports":["ice-hockey"],"market":"1x2",
                       "cmin":1.10,"cmax":1.30,"sort":"wr","legs":1,"n_p":3},
    "o15_sweet": {"id":"o15_x3_63pct","sports":["football"],"market":"over_1_5",
                   "cmin":1.20,"cmax":1.40,"sort":"wr","legs":1,"n_p":3},
    "o15_x4": {"id":"o15_x4p_56pct","sports":["football"],"market":"over_1_5",
                "cmin":1.20,"cmax":1.40,"sort":"wr","legs":1,"n_p":4},
    "hk_combo3p": {"id":"hk_combo2j_x3p_top","sports":["ice-hockey"],"market":"1x2",
                    "cmin":1.30,"cmax":1.50,"sort":"wr","legs":2,"n_p":3},
    "fh_combo2x4p": {"id":"fh_combo3j_x4p_top","sports":["football","ice-hockey"],
                       "market":"1x2","cmin":1.20,"cmax":1.40,"sort":"wr","legs":3,"n_p":4},
    "hb_combo3x3p": {"id":"hb_combo3j_x3p_apr","sports":["ice-hockey","basketball"],
                       "market":"1x2","cmin":1.35,"cmax":1.60,"sort":"wr","legs":3,"n_p":3},
    "btts_combo2j_x6p": {"id":"btts_combo2j_x6p","sports":["football"],"market":"btts",
                          "cmin":1.55,"cmax":1.80,"sort":"wr","legs":2,"n_p":6},
    "o15_combo2j_x4p": {"id":"o15_combo2j_x4p_apr","sports":["football"],"market":"over_1_5",
                         "cmin":1.10,"cmax":1.25,"sort":"ev","legs":2,"n_p":4},
}

def make_strat(p):
    return {"id":p["id"],"label":p["id"],"components":[{
        "sports":p["sports"],"market":p["market"],
        "cote_min":p["cmin"],"cote_max":p["cmax"],
        "sort_by":p["sort"],"max_legs":p["legs"],"max_combos":1,
        "min_wr":None,"min_ev":None,"legs_per_palier":p["legs"]
    }],"montante":{"initial_stake":INITIAL,"n_paliers_target":p["n_p"],
                    "combo_legs_per_palier":p["legs"]}}

# Compute individual perfs
print("[META MIX] Mesure perfs individuelles...")
indiv = {}
for k, p in TOP_PICKS.items():
    s = make_strat(p)
    perfs = {}
    for pname, ps, pe in PERIODS:
        try:
            r = simulate(s, ps, pe, mode="intraday", initial_stake=INITIAL)
            perfs[pname] = {
                "pnl": round(r["final_pnl"], 1),
                "n_complete": r["n_cycles_complete"],
                "n_total": r["n_cycles_total"],
                "compl": round(r["completion_rate"]*100, 1),
                "avg_cap": round(r["avg_capital_complete"], 1),
            }
        except Exception as e:
            print(f"  err {k}: {e}")
            perfs[pname] = None
    indiv[k] = perfs

print("\n=== Perfs individuelles ===")
print(f"{'Profile':<20s} {'S1 PnL':>9s} {'S1 ✓/tot':>10s} {'S1 %':>5s} | {'Apr PnL':>9s} {'Apr ✓/tot':>10s}")
print("-"*90)
for k, p in indiv.items():
    s = p.get("S1-26") or {}
    a = p.get("Apr") or {}
    print(f"{k:<20s} {s.get('pnl',0):>+8.0f}€  {s.get('n_complete','?'):>3}/{s.get('n_total','?'):<3}  {s.get('compl',0):>4.0f}% | {a.get('pnl',0):>+7.0f}€  {a.get('n_complete','?'):>3}/{a.get('n_total','?'):<3}")

# Build mixes (combinations of 3 to 5)
import itertools
mixes = []
profiles = list(TOP_PICKS.keys())
# 3-mixes
for c in itertools.combinations(profiles, 3):
    mixes.append(("3mix", c))
# 5-mixes (sample)
for c in itertools.combinations(profiles, 5):
    mixes.append(("5mix", c))

print(f"\n[META MIX] {len(mixes)} mixes à évaluer (somme PnL indiv)")

mix_results = []
for k, c in mixes:
    s1 = sum(indiv[p]["S1-26"]["pnl"] for p in c if indiv[p].get("S1-26"))
    apr = sum(indiv[p].get("Apr",{}).get("pnl",0) for p in c if indiv[p].get("Apr"))
    capital_total = INITIAL * len(c)  # 10€ × N stratégies
    mix_results.append({
        "type": k, "profiles": c,
        "s1_pnl": s1, "apr_pnl": apr,
        "capital": capital_total,
        "monthly_s1_avg": s1/4,  # PnL mensuel moyen
    })

print("\n=== TOP 10 MIX par PnL S1-26 ===")
mix_results.sort(key=lambda r: -r["s1_pnl"])
for r in mix_results[:10]:
    print(f"  [{r['type']}] {' + '.join(r['profiles']):<70s}  S1 +{r['s1_pnl']:.0f}€ (~{r['monthly_s1_avg']:.0f}€/mois) Apr +{r['apr_pnl']:.0f}€  | capital {r['capital']}€/jour")

print("\n=== TOP 10 MIX par PnL Avril ===")
mix_results.sort(key=lambda r: -r["apr_pnl"])
for r in mix_results[:10]:
    print(f"  [{r['type']}] {' + '.join(r['profiles']):<70s}  Apr +{r['apr_pnl']:.0f}€ | S1 +{r['s1_pnl']:.0f}€ | capital {r['capital']}€/jour")

# ROI = pnl / capital_engaged_total (capital × n_jours)
print("\n=== TOP 10 MIX par ROI quotidien Avril (PnL/capital_jour×30) ===")
for r in mix_results:
    r["roi_apr"] = r["apr_pnl"] / max(r["capital"]*30, 1) * 100  # ROI mensuel
mix_results.sort(key=lambda r: -r["roi_apr"])
for r in mix_results[:10]:
    print(f"  [{r['type']}] ROI Apr {r['roi_apr']:>5.1f}%/jour  PnL +{r['apr_pnl']:.0f}€  capital {r['capital']}€  ({' + '.join(r['profiles'][:3])}...)")

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/meta_mix_results.json","w") as f:
    json.dump({"indiv": indiv, "mixes": mix_results[:30]}, f, indent=2, default=str)
print("\nSaved.")
