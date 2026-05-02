#!/usr/bin/env python3
"""Tester strats anti-corrélation : dédup + multi-sport."""
import urllib.request, urllib.parse, json, sys

URL = "http://127.0.0.1:5050/api/backtest-hybrid"

def run(params):
    qs = urllib.parse.urlencode(params)
    return json.loads(urllib.request.urlopen(URL + "?" + qs, timeout=120).read())

def fmt(d, name):
    return (f"{name:38s} | combos={d['n_combos_total']:>4d} | jours+ {d['n_days_green']:>2d}/{d['n_days_played']} ({d['daily_win_rate']*100:.0f}%) | "
            f"PnL {d['pnl_total']:>+5.0f}€ | DD {d['max_drawdown']:>4.0f}€ | volat = "
            + str(round(sum((day['pnl']-d['pnl_total']/d['n_days_played'])**2 for day in d['daily'])**0.5 / max(1,d['n_days_played']**0.5), 1)) + "€")

print("=" * 130)
print("AVRIL 2026 — Test stratégies anti-corrélation")
print("=" * 130)

base = {"date":"2026-04-01","end_date":"2026-05-02","sizing":"flat","stake":"10","bankroll":"100"}

# 1. H_daily_boost SANS et AVEC dédup max1
print(fmt(run({**base, "preset":"H_daily_boost"}), "H_daily_boost (sans dédup)"))
print(fmt(run({**base, "preset":"H_daily_boost", "dedup":"max1"}), "H_daily_boost + dédup max1"))
print(fmt(run({**base, "preset":"H_daily_boost", "dedup":"disjoint"}), "H_daily_boost + dédup disjoint"))

print()
# 2. H_balance avec dédup
print(fmt(run({**base, "preset":"H_balance"}), "H_balance (sans dédup)"))
print(fmt(run({**base, "preset":"H_balance", "dedup":"max1"}), "H_balance + dédup max1"))

print()
# 3. NOUVEAU : multi-sport diversifié (1 par sport, 5 sports différents)
multi_safe = [
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
    {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":2},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.5, "sort_by":"wr", "sports":["ice-hockey"], "max_combos":1},
]
print(fmt(run({**base, "components":json.dumps(multi_safe), "dedup":"max1"}),
          "Multi_safe (2foot+2bask+2tennis+1hockey, dédup)"))

# Variante : multi-sport avec EV3j
multi_balance = [
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":2},
    {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":1},
    {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
]
print(fmt(run({**base, "components":json.dumps(multi_balance), "dedup":"max1"}),
          "Multi_balance (2f+2b+1t+1ev3j, dédup)"))

# Variante : tennis dominant (anti-corrélation max)
tennis_heavy = [
    {"max_legs":2, "cote_min":1.3, "cote_max":2.0, "sort_by":"wr", "sports":["tennis"], "max_combos":3},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["football"], "max_combos":2},
    {"max_legs":2, "cote_min":1.4, "cote_max":2.0, "sort_by":"wr", "sports":["basketball"], "max_combos":1},
    {"max_legs":3, "cote_min":2.0, "cote_max":5.0, "sort_by":"ev", "sports":["football","basketball"], "max_combos":1},
]
print(fmt(run({**base, "components":json.dumps(tennis_heavy), "dedup":"max1"}),
          "Tennis_heavy (3t+2f+1b+1ev3j, dédup)"))

print()
print("=" * 130)
print("Détail jour-par-jour des 4 derniers jours pour la meilleure")
print("=" * 130)
d = run({**base, "components":json.dumps(multi_balance), "dedup":"max1"})
for day in d["daily"][-5:]:
    print(f"  {day['date']}: {day['n_combos']} combos, {day['n_won']} won, PnL {day['pnl']:+.0f}€, BR {day['bankroll_end']:.0f}€")
