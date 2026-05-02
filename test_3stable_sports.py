#!/usr/bin/env python3
"""Test Multi_full restreint à foot+basket+hockey (les 3 sports stables)."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

def streak(daily):
    s=0;c=0
    for d in daily:
        if d["pnl"]<0: c+=1; s=max(s,c)
        else: c=0
    return s

# Multi_full restreint aux 3 sports stables
THREE_STABLE = json.dumps([
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":3},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":2},
    {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
    {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey"], "max_combos":1},
    {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey"], "max_combos":1},
])

semesters = [
    ("S1-2024","2024-01-01","2024-06-30"),
    ("S2-2024","2024-07-01","2024-12-31"),
    ("S1-2025","2025-01-01","2025-06-30"),
    ("S2-2025","2025-07-01","2025-12-31"),
    ("S1-2026","2026-01-01","2026-05-02"),
]

print("=== Multi_full original vs 3_stable_sports ===\n")
print(f"{'Semestre':10s} {'Mode':20s} {'jours+/-':>10s} {'win%':>5s} {'PnL':>8s} {'ROI%':>7s} {'série':>6s} {'DD':>5s}")
print("-"*85)

for name, sd, ed in semesters:
    base = {"date":sd,"end_date":ed,"sizing":"flat","stake":"10","bankroll":"100",
            "bookmaker":"winamax_fr","dedup":"max1"}
    # Multi_full standard
    d1 = run({**base, "preset":"Multi_full"})
    s1 = streak(d1["daily"])
    print(f"{name:10s} {'Multi_full all 5':20s} {d1['n_days_green']}/{d1['n_days_red']:<3d}      "
          f"{d1['daily_win_rate']*100:>5.0f} {d1['pnl_total']:>+8.0f} {d1['roi']*100:>+7.1f} {s1:>4d}j {d1['max_drawdown']:>5.0f}")
    # 3_stable_sports
    d2 = run({**base, "components":THREE_STABLE})
    s2 = streak(d2["daily"])
    print(f"{name:10s} {'3 stable (f+b+h)':20s} {d2['n_days_green']}/{d2['n_days_red']:<3d}      "
          f"{d2['daily_win_rate']*100:>5.0f} {d2['pnl_total']:>+8.0f} {d2['roi']*100:>+7.1f} {s2:>4d}j {d2['max_drawdown']:>5.0f}")
    print()
