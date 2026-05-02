#!/usr/bin/env python3
"""Quelles leagues utilise Hyper_pro sur avril 2026 ? Lesquelles sont sur Winamax ?"""
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import run_backtest, build_backtest_combos, extract_picks, _get_index
from morning_live import load_magic
magic = load_magic()
ALL_SPORTS = ["football","basketball","ice-hockey","baseball","tennis"]

idx = _get_index()
def gen_days(s, e):
    s = datetime.strptime(s, "%Y-%m-%d").date()
    e = datetime.strptime(e, "%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)

# Composition Hyper_pro
HYPER_PRO = [
    ({"max_legs":2,"cote_min":1.05,"cote_max":1.3,"sort_by":"wr","sports_filter":["football"],"max_combos":1}, 1),
    ({"max_legs":2,"cote_min":1.05,"cote_max":1.3,"sort_by":"wr","sports_filter":["basketball"],"max_combos":1}, 1),
    ({"max_legs":2,"cote_min":1.05,"cote_max":1.3,"sort_by":"wr","sports_filter":["ice-hockey"],"max_combos":1}, 1),
    ({"max_legs":2,"cote_min":1.05,"cote_max":1.3,"sort_by":"wr","sports_filter":["baseball"],"max_combos":1}, 1),
    ({"max_legs":2,"cote_min":1.05,"cote_max":1.3,"sort_by":"wr","sports_filter":["tennis"],"max_combos":1}, 1),
    ({"max_legs":3,"cote_min":2.0,"cote_max":5.0,"sort_by":"ev","sports_filter":["football","basketball"],"max_combos":1}, 1),
    ({"max_legs":4,"cote_min":5.0,"cote_max":15.0,"sort_by":"ev","sports_filter":ALL_SPORTS,"max_combos":1}, 1),
]

leagues_used = defaultdict(Counter)  # sport -> league -> count

for d in gen_days("2026-04-01", "2026-05-02"):
    for kwargs, max_c in HYPER_PRO:
        r = run_backtest(d, magic, stake=10.0, **kwargs)
        for combo in r["combos"][:max_c]:
            for leg in combo["legs"]:
                leagues_used[leg["sport"]][leg["league"]] += 1

print("Leagues utilisées par Hyper_pro sur avril 2026 (par sport, top 30) :")
print()
for sport in ALL_SPORTS:
    print(f"\n=== {sport.upper()} ===")
    leagues = leagues_used[sport].most_common(30)
    total = sum(leagues_used[sport].values())
    for lg, n in leagues:
        pct = n / total * 100 if total else 0
        print(f"  {n:>4d}× ({pct:>4.1f}%)  {lg}")
    print(f"  ---  Total {total} picks dans {len(leagues_used[sport])} leagues distinctes")
