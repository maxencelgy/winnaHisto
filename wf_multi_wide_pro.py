#!/usr/bin/env python3
"""Walk-forward Multi_wide_pro et Multi_full sur 5 semestres sous Winamax FR."""
import urllib.request, urllib.parse, json
URL = "http://127.0.0.1:5050/api/backtest-hybrid"
def run(p): return json.loads(urllib.request.urlopen(URL+"?"+urllib.parse.urlencode(p), timeout=180).read())

multi_wide_pro = json.dumps([
    {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["football"], "max_combos":3},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
    {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
    {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
    {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
])
multi_full = json.dumps([
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
    {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
    {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":2},
    {"max_legs":4, "cote_min":5.0, "cote_max":15.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
    {"max_legs":5, "cote_min":15.0, "cote_max":60.0, "sort_by":"ev", "sports":["football","basketball","ice-hockey","baseball","tennis"], "max_combos":1},
])

semesters = [
    ("S1-2024", "2024-01-01", "2024-06-30"),
    ("S2-2024", "2024-07-01", "2024-12-31"),
    ("S1-2025", "2025-01-01", "2025-06-30"),
    ("S2-2025", "2025-07-01", "2025-12-31"),
    ("S1-2026", "2026-01-01", "2026-05-02"),
]

for label, comps in [("Multi_wide_pro", multi_wide_pro), ("Multi_full", multi_full)]:
    print(f"\n=== WALK-FORWARD {label} (Winamax FR + dédup max1) ===")
    print(f"{'Semestre':10s} {'n':>5s} {'jours+/-':>10s} {'win%':>5s} {'PnL':>7s} {'ROI%':>7s} {'DD':>5s} {'série':>6s}")
    rois = []
    for name, sd, ed in semesters:
        p = {"components":comps, "date":sd, "end_date":ed, "sizing":"flat",
             "stake":"10", "bankroll":"100", "bookmaker":"winamax_fr", "dedup":"max1"}
        d = run(p)
        if d.get("error"): print(f"{name:10s} ERR"); continue
        streak = 0; cur = 0
        for day in d["daily"]:
            if day["pnl"] < 0: cur += 1; streak = max(streak, cur)
            else: cur = 0
        roi = d["roi"]*100
        rois.append(roi)
        print(f"{name:10s} {d['n_combos_total']:>5d} "
              f"{d['n_days_green']:>2d}/{d['n_days_red']:<3d}     {d['daily_win_rate']*100:>5.0f} "
              f"{d['pnl_total']:>+7.0f} {roi:>+7.1f} {d['max_drawdown']:>5.0f} {streak:>4d}j")
    if rois:
        print(f"  Moyen: {sum(rois)/len(rois):+.1f}% ROI | min {min(rois):+.1f}% | std {(sum((r-sum(rois)/len(rois))**2 for r in rois)/len(rois))**0.5:.1f}pts")
        print(f"  Tous > +30% : {'✓ VALIDÉ' if all(r > 30 for r in rois) else '✗ DRIFT'}")
