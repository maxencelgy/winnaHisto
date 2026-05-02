#!/usr/bin/env python3
"""Trouver multi-sport qui combine gains de Foot_pro_lottery + lissesse de Multi_safe."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10",
        "bankroll":"100","bookmaker":"winamax_fr","dedup":"max1"}

variants = {
    "Multi_safe (rappel)": {**base, "preset":"Multi_safe"},
    "Multi_balance (rappel)": {**base, "preset":"Multi_balance"},
    "Foot_pro_lottery (rappel)": {**base, "preset":"Foot_pro_lottery"},

    # 1. Multi_safe + 1 EV3j fb (boost gains)
    "Multi_safe_boost": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
    ])},
    # 2. Multi_safe_boost + EV4j (encore plus de gains)
    "Multi_safe_pro": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
    # 3. Multi_full = 5 sports safe + 2 EV3j + 1 EV4j + 1 EV5j (gros volume)
    "Multi_full": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
        {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
    # 4. Mix sports moderate (3+3+EV3j+EV4j)
    "Multi_3+3+ev": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
    ])},
    # 5. Multi heavy lottery (EV4j x2 + EV5j multi)
    "Multi_heavy_lottery": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
        {"max_legs":4, "cote_min":10.0, "cote_max":30.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
        {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
    # 6. Multi 4 sports + EV3j fb + EV4j fb
    "Multi_4sports_pro": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
    # 7. Multi safe wide + EV multi (cote_max 2.5 sur 2j)
    "Multi_wide_pro": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
        {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
        {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
}

results = []
print(f"{'Stratégie':30s} {'n':>4s} {'jrs+/-':>9s} {'win%':>5s} {'PnL':>7s} {'DD':>5s} {'série':>6s} {'volat':>6s}")
print("-" * 90)
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:30s} ERR"); continue
        streak = 0; cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0: cur += 1; streak = max(streak, cur)
            else: cur = 0
        if d["daily"]:
            mean_p = d["pnl_total"] / len(d["daily"])
            std = (sum((day["pnl"]-mean_p)**2 for day in d["daily"]) / len(d["daily"])) ** 0.5
        else: std = 0
        score = d["pnl_total"] * d["daily_win_rate"] / max(1, d["max_drawdown"] + streak * 30)
        results.append({"name":name, "win_pct":d["daily_win_rate"]*100, "pnl":d["pnl_total"],
                        "dd":d["max_drawdown"], "streak":streak, "std":std, "score":score})
        print(f"{name:30s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {d['max_drawdown']:>5.0f} {streak:>4d}j {std:>6.1f}")
    except Exception as e:
        print(f"{name:30s} EX: {e}")

print()
print("=== Top 5 par score (PnL × win% / (DD+série×30)) ===")
results.sort(key=lambda r: -r["score"])
for r in results[:5]:
    print(f"  ⭐ {r['name']:30s}: score {r['score']:.1f} | PnL +{r['pnl']:.0f}€ | jours+ {r['win_pct']:.0f}% | série {r['streak']}j | DD {r['dd']:.0f}€ | volat {r['std']:.0f}€/j")

print()
print("=== Top 5 par GAINS / LISSE (PnL / std) ===")
results.sort(key=lambda r: -(r["pnl"] / max(1, r["std"])))
for r in results[:5]:
    ratio = r["pnl"] / max(1, r["std"])
    print(f"  💎 {r['name']:30s}: ratio {ratio:.1f} | PnL +{r['pnl']:.0f}€ | volat {r['std']:.0f}€/j | série {r['streak']}j")
