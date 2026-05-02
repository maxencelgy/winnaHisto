#!/usr/bin/env python3
"""Tester compositions optimisées POUR le filtre Winamax FR."""
import urllib.request, urllib.parse, json

URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10",
        "bankroll":"100","bookmaker":"winamax_fr","dedup":"max1"}

variants = {
    "Hyper_pro (rappel)": {**base, "preset":"Hyper_pro"},
    "Multi_balance (rappel)": {**base, "preset":"Multi_balance"},
    "H9 (rappel)": {**base, "preset":"H9"},

    # 1. Hyper massif : 3 favoris/sport au lieu de 1
    "Hyper_massive (3 fav par sport)": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.5, "sort_by":"wr", "sports":[s], "max_combos":3}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ])},

    # 2. Foot massif (le sport avec le plus de leagues dispos en FR)
    "Foot_massive (foot only safe)": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":7}
    ])},

    # 3. Foot + basket safe + EV3j fb
    "Foot_basket_pro": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
    ])},

    # 4. Foot exclusif boost
    "Foot_pro": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football"], "max_combos":1},
    ])},

    # 5. NBA + Top 5 foot (les 2 marchés les plus liquides)
    "Top_liquide": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey"], "max_combos":1},
    ])},

    # 6. Hyper_pro mais cote_max élargie pour avoir plus de matches
    "Hyper_pro_loose": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.1, "cote_max":1.7, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
}

print(f"{'Stratégie':35s} {'n':>4s} {'jrs+/-':>9s} {'win%':>5s} {'PnL':>7s} {'DD':>5s} {'série':>5s}")
print("-" * 90)
results = []
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:35s} ERR: {d['error'][:40]}"); continue
        streak = 0; cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0: cur += 1; streak = max(streak, cur)
            else: cur = 0
        results.append({"name":name, "win_pct":d["daily_win_rate"]*100, "pnl":d["pnl_total"],
                        "dd":d["max_drawdown"], "streak":streak, "n":d["n_combos_total"],
                        "n_red":d["n_days_red"], "n_green":d["n_days_green"]})
        print(f"{name:35s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {d['max_drawdown']:>5.0f} {streak:>4d}j")
    except Exception as e:
        print(f"{name:35s} EX: {e}")

print()
print("=== Top 3 par PnL absolu (filtre Winamax FR actif) ===")
results.sort(key=lambda r: -r["pnl"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: PnL {r['pnl']:+.0f}€ | jours+ {r['win_pct']:.0f}% | série rouge {r['streak']}j | DD {r['dd']:.0f}€")
print()
print("=== Top 3 par % jours gagnants ===")
results.sort(key=lambda r: -r["win_pct"])
for r in results[:3]:
    print(f"  ⭐ {r['name']}: {r['win_pct']:.0f}% jours+ | PnL {r['pnl']:+.0f}€ | série rouge {r['streak']}j")
