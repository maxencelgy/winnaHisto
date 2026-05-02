#!/usr/bin/env python3
"""Combiner stabilité (Hyper_5sports) + gains (boost EV)."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10","bankroll":"100"}
base_adapt = {**base, "sizing":"flat_pct", "stake_cap":"500"}

variants = {
    # Hyper_5sports rappel
    "Hyper_5sports flat": {**base, "preset":"Hyper_5sports"},
    "Hyper_5sports adaptif": {**base_adapt, "preset":"Hyper_5sports"},

    # Boost: Hyper + 1 EV3j
    "Hyper + 1 EV3j fb 2-5": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":1}
    ]), "dedup":"max1"},

    # Boost: Hyper + 2 EV3j
    "Hyper + 2 EV3j fb 2-5": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":2}
    ]), "dedup":"max1"},

    # Hyper élargi cote 1.05-1.5 (un peu plus de payout)
    "Hyper 1.05-1.5 + 2 EV3j": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.5, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":2}
    ]), "dedup":"max1"},

    # Hyper + EV4j multi (ajout lottery sans casser le safe)
    "Hyper + 1 EV3j + 1 EV4j 5-15": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":1},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev",
         "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ]), "dedup":"max1"},

    # Multi_balance rappel
    "Multi_balance (rappel)": {**base, "preset":"Multi_balance"},
    "Multi_balance adaptif": {**base_adapt, "preset":"Multi_balance"},
}

print(f"{'Stratégie':45s} {'sizing':6s} {'n':>4s} {'jrs+/-':>9s} {'win%':>4s} {'BR_fin':>7s} {'PnL':>6s} {'DD':>4s} {'pireSérie':>9s}")
print("-" * 120)
results = []
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:45s} ERR"); continue
        max_streak = 0; cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0: cur += 1; max_streak = max(max_streak, cur)
            else: cur = 0
        results.append({"name":name, "win_pct":d["daily_win_rate"]*100, "br":d["bankroll_final"],
                        "pnl":d["pnl_total"], "dd":d["max_drawdown"], "streak":max_streak,
                        "n":d["n_combos_total"], "n_red":d["n_days_red"], "n_green":d["n_days_green"]})
        print(f"{name:45s} {p.get('sizing','flat'):6s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>4.0f} "
              f"{d['bankroll_final']:>7.0f} {d['pnl_total']:>+6.0f} {d['max_drawdown']:>4.0f} "
              f"{max_streak:>7d}j")
    except Exception as e:
        print(f"{name:45s} EX: {e}")

print()
print("Top 3 par PnL absolu (BR final - 100€) :")
results.sort(key=lambda r: -r["pnl"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: BR final {r['br']:.0f}€ | jours+ {r['win_pct']:.0f}% | "
          f"pire série rouge {r['streak']}j | DD {r['dd']:.0f}€")

print()
print("Top 3 score composite (PnL × win%) :")
results.sort(key=lambda r: -(r["pnl"] * r["win_pct"]))
for r in results[:3]:
    print(f"  ⭐ {r['name']}: BR {r['br']:.0f}€ ({r['win_pct']:.0f}% jours+) | série rouge max {r['streak']}j")
