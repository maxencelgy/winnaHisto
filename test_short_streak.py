#!/usr/bin/env python3
"""Trouver des stratégies avec série rouge ≤ 2 jours + gains corrects."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10",
        "bankroll":"100","bookmaker":"winamax_fr","dedup":"max1"}

variants = {
    "Multi_full (rappel)": {**base, "preset":"Multi_full"},
    "Multi_safe (rappel)": {**base, "preset":"Multi_safe"},
    "Hyper_5sports (rappel)": {**base, "preset":"Hyper_5sports"},
    "Hyper_massive (rappel)": {**base, "preset":"Hyper_massive"},

    # 1. 12 safe ultra-couverture (3 par sport sauf baseball)
    "Multi_12safe (3+3+3+2+1)": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["tennis"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["baseball"], "max_combos":1},
    ])},

    # 2. Multi_safe + 1 EV3j cote 2-3 (pas 2-5, plus safe)
    "Multi_safe_lowEV": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":3.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
    ])},

    # 3. Hyper_5sports + 1 EV3j cote 2-3
    "Hyper_5sports_+evlow": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":3, "cote_min":2.0, "cote_max":3.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
    ])},

    # 4. Multi_safe étendu : 3 par sport sport principaux
    "Multi_safe_extended": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
    ])},

    # 5. 10 ultra-favoris (cote 1.05-1.4) toute sports
    "Hyper_10favs": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.4, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.05, "cote_max":1.4, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":2, "cote_min":1.05, "cote_max":1.4, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.05, "cote_max":1.4, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":2, "cote_min":1.05, "cote_max":1.4, "sort_by":"wr", "sports":["baseball"], "max_combos":1},
    ])},

    # 6. Multi_safe_extended + 1 EV3j 2-3 (booster gains sans casser)
    "Multi_safe_ext_+evlow": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":3.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
    ])},

    # 7. 15 combos très safe
    "Multi_15safe": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["football"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["basketball"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["tennis"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["baseball"], "max_combos":2},
    ])},
}

results = []
print(f"{'Stratégie':30s} {'n':>4s} {'jrs+/-':>9s} {'win%':>5s} {'PnL':>7s} {'DD':>5s} {'série':>6s}")
print("-" * 85)
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:30s} ERR: {d['error'][:30]}"); continue
        streak = 0; cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0: cur += 1; streak = max(streak, cur)
            else: cur = 0
        results.append({"name":name, "win_pct":d["daily_win_rate"]*100, "pnl":d["pnl_total"],
                        "dd":d["max_drawdown"], "streak":streak, "n":d["n_combos_total"]})
        print(f"{name:30s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {d['max_drawdown']:>5.0f} {streak:>4d}j")
    except Exception as e:
        print(f"{name:30s} EX: {e}")

print()
print("=== Stratégies avec série rouge ≤ 2j (CRITÈRE FORT) ===")
short = [r for r in results if r["streak"] <= 2]
short.sort(key=lambda r: -r["pnl"])
for r in short:
    print(f"  ⭐ {r['name']:30s}: PnL +{r['pnl']:.0f}€ | jours+ {r['win_pct']:.0f}% | série {r['streak']}j | DD {r['dd']:.0f}€")

print()
print("=== Stratégies avec série rouge ≤ 3j triées par PnL ===")
short3 = [r for r in results if r["streak"] <= 3]
short3.sort(key=lambda r: -r["pnl"])
for r in short3[:5]:
    print(f"  💰 {r['name']:30s}: PnL +{r['pnl']:.0f}€ | jours+ {r['win_pct']:.0f}% | série {r['streak']}j | DD {r['dd']:.0f}€")
