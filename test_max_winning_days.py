#!/usr/bin/env python3
"""Maximiser le % jours gagnants : tester strats ultra-safe + multi-sport."""
import urllib.request, urllib.parse, json

URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(params):
    return json.loads(urllib.request.urlopen(URL + "?" + urllib.parse.urlencode(params), timeout=120).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10","bankroll":"100"}

strategies = {
    # 1. Hyper safe : 5 combos 2j ultra-favori (cote 1.05-1.3)
    "Hyper_safe (5×2j cote 1.05-1.3)": {
        "components": [{"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr",
                        "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":5}],
        "dedup": "max1"
    },
    # 2. Hyper safe multi-sport : 1 par sport, cote 1.05-1.3
    "Hyper_5sports (1 par sport cote 1.05-1.3)": {
        "components": [
            {"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr", "sports":[s], "max_combos":1}
            for s in ["football","basketball","ice-hockey","baseball","tennis"]
        ],
        "dedup": "max1"
    },
    # 3. 7 combos par sport (foot+basket+tennis x2 + hockey + baseball)
    "Multi_7 (cote 1.4-1.8)": {
        "components": [
            {"max_legs":2, "cote_min":1.4, "cote_max":1.8, "sort_by":"wr", "sports":["football"], "max_combos":2},
            {"max_legs":2, "cote_min":1.4, "cote_max":1.8, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
            {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
            {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        ],
        "dedup": "max1"
    },
    # 4. 10 combos très diversifiés cote 1.3-2
    "Multi_10 (10×2j 1.3-2 multi)": {
        "components": [
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["baseball"], "max_combos":1},
        ],
        "dedup": "max1"
    },
    # 5. Uniquement tennis (vu qu'il marchait pendant les 4 jours rouges)
    "Tennis_only (8×2j tennis)": {
        "components": [
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":8}
        ],
        "dedup": "max1"
    },
    # 6. Tennis + foot (bons performeurs sur jours noirs)
    "Tennis+Foot_safe": {
        "components": [
            {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":4},
            {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
        ],
        "dedup": "max1"
    },
    # 7. Multi_balance (rappel)
    "Multi_balance (rappel)": {"preset": "Multi_balance"},
    "Multi_safe (rappel)": {"preset": "Multi_safe"},
}

results = []
print(f"{'Stratégie':45s} {'n':>4s} {'wr%':>5s} {'jrs+/-':>9s} {'win%':>5s} {'PnL€':>6s} {'DD':>4s} {'volat':>6s} {'meilleur série lose':>22s}")
print("-" * 130)

for name, spec in strategies.items():
    params = {**base}
    if "preset" in spec: params["preset"] = spec["preset"]
    if "components" in spec: params["components"] = json.dumps(spec["components"])
    if "dedup" in spec: params["dedup"] = spec["dedup"]
    try:
        d = run(params)
        if d.get("error"): print(f"{name:45s} ERR: {d['error'][:50]}"); continue
        # streaks losing
        max_streak = 0
        cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0:
                cur += 1
                max_streak = max(max_streak, cur)
            else:
                cur = 0
        # std
        if d["daily"]:
            mean_p = d["pnl_total"] / len(d["daily"])
            std = (sum((day["pnl"]-mean_p)**2 for day in d["daily"]) / len(d["daily"])) ** 0.5
        else: std = 0
        results.append({"name":name, "win_pct":d["daily_win_rate"]*100, "pnl":d["pnl_total"],
                        "dd":d["max_drawdown"], "n_red":d["n_days_red"], "max_streak":max_streak,
                        "std":std})
        print(f"{name:45s} {d['n_combos_total']:>4d} {d['wr_combos']*100:>5.1f} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+6.0f} {d['max_drawdown']:>4.0f} {std:>6.1f} "
              f"{max_streak:>20d}j")
    except Exception as e:
        print(f"{name:45s} EXCEPTION: {e}")

print()
print("=== Top 3 par % jours gagnants ===")
results.sort(key=lambda r: -r["win_pct"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: {r['win_pct']:.0f}% jours+ | PnL {r['pnl']:+.0f}€ | DD {r['dd']:.0f}€ | "
          f"pire série rouge {r['max_streak']}j")
print()
print("=== Top 3 par PIRE SÉRIE ROUGE (la plus courte) ===")
results.sort(key=lambda r: r["max_streak"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: pire série {r['max_streak']}j | {r['win_pct']:.0f}% jours+ | PnL {r['pnl']:+.0f}€")
