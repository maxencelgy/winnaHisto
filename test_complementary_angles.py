#!/usr/bin/env python3
"""6 angles complémentaires pour casser le trade-off PnL vs série rouge."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10",
        "bankroll":"100","bookmaker":"winamax_fr","dedup":"max1"}

def streak(daily):
    s=0;c=0
    for d in daily:
        if d["pnl"]<0: c+=1; s=max(s,c)
        else: c=0
    return s

variants = {
    "Multi_12safe (baseline)": {**base, "preset":"Multi_12safe"},

    # 1. EV3j ultra-tight cote 2-2.5 (au lieu de 2-3)
    "EV_tight_8x": {**base, "components":json.dumps([
        {"max_legs":3, "cote_min":2.0, "cote_max":2.5, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":8},
    ])},

    # 2. Stratified : 5 ultra-safe + 5 safe + 3 EV-tight
    "Stratified_3layers": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.05, "cote_max":1.3, "sort_by":"wr", "sports":[s], "max_combos":1}
        for s in ["football","basketball","ice-hockey","baseball","tennis"]
    ] + [
        {"max_legs":2, "cote_min":1.4, "cote_max":1.8, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":1.8, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
        {"max_legs":3, "cote_min":2.0, "cote_max":2.5, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":3},
    ])},

    # 3. Mega_volume_safe : 20+ combos safe multi-sport
    "Mega_volume_safe": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["basketball"], "max_combos":5},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["tennis"], "max_combos":4},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["baseball"], "max_combos":3},
    ])},

    # 4. Foot+Basket tight (que les 2 sports les plus liquides + cote serrée)
    "FootBasket_tight": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":1.7, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":2, "cote_min":1.4, "cote_max":1.7, "sort_by":"wr", "sports":["basketball"], "max_combos":5},
        {"max_legs":3, "cote_min":2.0, "cote_max":2.5, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":3},
    ])},

    # 5. Foot_only_volume : 12 combos foot uniquement (le sport le plus dispo Winamax)
    "Foot_only_volume": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["football"], "max_combos":8},
        {"max_legs":3, "cote_min":2.0, "cote_max":2.5, "sort_by":"ev", "sports":["football"], "max_combos":4},
    ])},

    # 6. EV_tight + safe (sandwich tight)
    "EV_tight_+safe": {**base, "components":json.dumps([
        {"max_legs":2, "cote_min":1.4, "cote_max":1.7, "sort_by":"wr", "sports":["football"], "max_combos":3},
        {"max_legs":2, "cote_min":1.4, "cote_max":1.7, "sort_by":"wr", "sports":["basketball"], "max_combos":3},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
        {"max_legs":3, "cote_min":2.0, "cote_max":2.5, "sort_by":"ev",
         "sports":["football","basketball"], "max_combos":4},
    ])},

    # 7. Disjoint dédup (test plus strict que max1)
    "Mega_volume_safe_disjoint": {**base, "dedup":"disjoint", "components":json.dumps([
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["football"], "max_combos":5},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["basketball"], "max_combos":5},
        {"max_legs":2, "cote_min":1.3, "cote_max":1.7, "sort_by":"wr", "sports":["tennis"], "max_combos":4},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":2},
        {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["baseball"], "max_combos":2},
    ])},
}

print(f"{'Stratégie':32s} {'n':>4s} {'jrs+/-':>9s} {'win%':>5s} {'PnL':>7s} {'DD':>5s} {'série':>6s} {'verdict':>7s}")
print("-" * 90)
for name, p in variants.items():
    try:
        d = run(p)
        if d.get("error"): print(f"{name:32s} ERR: {d['error'][:40]}"); continue
        s = streak(d["daily"])
        verdict = "✓" if (s <= 2 and d["pnl_total"] >= 500) else "≤2j" if s <= 2 else ""
        print(f"{name:32s} {d['n_combos_total']:>4d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<2d}    {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {d['max_drawdown']:>5.0f} {s:>4d}j {verdict:>7s}")
    except Exception as e:
        print(f"{name:32s} EX: {e}")
