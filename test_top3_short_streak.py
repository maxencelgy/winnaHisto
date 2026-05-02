#!/usr/bin/env python3
"""Test rapide top 3 pistes prometteuses pour série ≤ 2j + gros PnL."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10",
        "bankroll":"100","bookmaker":"winamax_fr","dedup":"max1"}

variants = {
    "Multi_12safe (rappel)": {**base, "preset":"Multi_12safe"},
    "Multi_full (rappel)": {**base, "preset":"Multi_full"},

    # 1. Volume_max_smooth : 5 sports × 2 safe + 3 EV3j fb cote 2-3
    "Volume_max_smooth": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":3.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":3},
    ])},
    # 2. Smart_safe_+volEV
    "Smart_safe_+volEV": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
        {"max_legs":3, "cote_min":2.0, "cote_max":3.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":3},
        {"max_legs":4, "cote_min":5.0, "cote_max":10.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    ])},
    # 3. Volume_safe_18 : 18 combos safe multi-sport
    "Volume_safe_18": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":4},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":4},
        {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":4},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["baseball"], "max_combos":3},
    ])},
}

print(f"{'Stratégie':30s} {'n':>4s} {'jrs+/-':>9s} {'win%':>5s} {'PnL':>7s} {'DD':>5s} {'série':>6s}")
print("-" * 85)
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:30s} ERR"); continue
        s=0;c=0
        for day in d["daily"]:
            if day["pnl"] < 0: c+=1; s=max(s,c)
            else: c=0
        verdict = " ✓" if (s <= 2 and d["pnl_total"] >= 500) else ""
        print(f"{name:30s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {d['max_drawdown']:>5.0f} {s:>4d}j{verdict}")
    except Exception as e:
        print(f"{name:30s} EX: {e}")
