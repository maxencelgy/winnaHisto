#!/usr/bin/env python3
"""Trouver LE preset Winamax FR : gros gains, petite série rouge, petit DD."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10",
        "bankroll":"100","bookmaker":"winamax_fr","dedup":"max1"}

variants = {
    "Foot_pro (rappel)": {**base, "preset":"Foot_pro"},
    # 1. Foot_pro + lottery foot
    "Foot_pro_lottery": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football"], "max_combos":1},
        {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football"], "max_combos":1},
    ])},
    # 2. 6 safe foot + 3 EV (8 total)
    "Foot_safe_heavy": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":1.8, "sort_by":"wr", "sports":["football"], "max_combos":6},
        {"max_legs":3, "cote_min":2.0, "cote_max":4.0, "sort_by":"ev", "sports":["football"], "max_combos":2},
    ])},
    # 3. Mix foot + basket NBA + EV
    "Foot_NBA_pro": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
    ])},
    # 4. Foot très diversifié (cote 1.4-2.5)
    "Foot_wide": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["football"], "max_combos":7},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football"], "max_combos":2},
    ])},
    # 5. Multi-sport mais cote tight + EV3j fort
    "Multi_tight_ev": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.2, "cote_max":1.6, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.2, "cote_max":1.6, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":3, "cote_min":2.0, "cote_max":4.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":3},
    ])},
    # 6. Foot_pro + EV3j cote_max=8 (validé +11pts WF)
    "Foot_pro_cote8": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":3, "cote_min":2.0, "cote_max":8.0, "sort_by":"ev", "sports":["football"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football"], "max_combos":1},
    ])},
    # 7. 10 combos foot (max diversification interne via dédup)
    "Foot_10x": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":10},
    ])},
    # 8. Foot_pro mais cote_min relevée (1.5 au lieu de 1.3)
    "Foot_pro_1.5_2": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.5, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football"], "max_combos":1},
    ])},
    # 9. Foot+Basket avec 2 EV4j (push payout)
    "FootBasket_2lottery": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
    ])},
}

results = []
print(f"{'Stratégie':30s} {'n':>4s} {'jrs+/-':>9s} {'win%':>5s} {'PnL':>7s} {'DD':>5s} {'série':>6s} {'score':>7s}")
print("-" * 90)
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:30s} ERR"); continue
        streak = 0; cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0: cur += 1; streak = max(streak, cur)
            else: cur = 0
        # Score composite : PnL × win_pct / (DD + streak×30)
        score = d["pnl_total"] * d["daily_win_rate"] / max(1, d["max_drawdown"] + streak * 30)
        results.append({"name":name, "win_pct":d["daily_win_rate"]*100, "pnl":d["pnl_total"],
                        "dd":d["max_drawdown"], "streak":streak, "score":score,
                        "n":d["n_combos_total"], "n_red":d["n_days_red"], "n_green":d["n_days_green"]})
        print(f"{name:30s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {d['max_drawdown']:>5.0f} {streak:>4d}j {score:>7.1f}")
    except Exception as e:
        print(f"{name:30s} EX: {e}")

print()
print("=== Top 5 par score composite (PnL × win% / (DD + streak×30)) ===")
results.sort(key=lambda r: -r["score"])
for r in results[:5]:
    print(f"  ⭐ {r['name']:30s}: score {r['score']:.1f} | PnL +{r['pnl']:.0f}€ | jours+ {r['win_pct']:.0f}% | DD {r['dd']:.0f}€ | série {r['streak']}j")

print()
print("=== Top 5 par PnL ABSOLU ===")
results.sort(key=lambda r: -r["pnl"])
for r in results[:5]:
    print(f"  💰 {r['name']:30s}: PnL +{r['pnl']:.0f}€ | jours+ {r['win_pct']:.0f}% | DD {r['dd']:.0f}€ | série {r['streak']}j")
