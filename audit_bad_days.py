#!/usr/bin/env python3
"""Audit des 4 jours perdants 2026-04-28 → 2026-05-01."""
import sys
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import run_backtest, _get_index
from morning_live import load_magic
magic = load_magic()
ALL_SPORTS = ["football","basketball","ice-hockey","baseball","tennis"]
BAD_DAYS = ["2026-04-28","2026-04-29","2026-04-30","2026-05-01"]

idx = _get_index()

print("=" * 100)
print("PARTIE 1 : Volume + sport repartition par jour")
print("=" * 100)
for d in BAD_DAYS:
    matches = idx.get(d, [])
    by_sport = {}
    for m in matches:
        s = m["sport"]
        by_sport[s] = by_sport.get(s, 0) + 1
    print(f"{d}: {len(matches)} matchs | {by_sport}")

print()
print("=" * 100)
print("PARTIE 2 : Test multiple stratégies sur ces 4 jours")
print("=" * 100)

strategies = {
    "H_daily_boost": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.4, cote_max=2.5, sort_by="wr", sports_filter=["football","basketball"], max_combos=10)},
        {"max_combos":2, "kwargs":dict(max_legs=3, cote_min=2.0, cote_max=4.0, sort_by="wr", sports_filter=["football","basketball"], max_combos=10)},
        {"max_combos":1, "kwargs":dict(max_legs=3, cote_min=2.0, cote_max=5.0, sort_by="ev", sports_filter=["football","basketball"], max_combos=10)},
    ],
    "H_balance": [
        {"max_combos":4, "kwargs":dict(max_legs=2, cote_min=1.4, cote_max=2.0, sort_by="wr", sports_filter=["football","basketball"], max_combos=10)},
        {"max_combos":1, "kwargs":dict(max_legs=3, cote_min=2.0, cote_max=5.0, sort_by="ev", sports_filter=["football","basketball"], max_combos=10)},
        {"max_combos":1, "kwargs":dict(max_legs=4, cote_min=5.0, cote_max=15.0, sort_by="ev", sports_filter=ALL_SPORTS, max_combos=10)},
    ],
    "Foot_only_safe": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.4, cote_max=2.0, sort_by="wr", sports_filter=["football"], max_combos=10)},
    ],
    "Basket_only_safe": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.4, cote_max=2.0, sort_by="wr", sports_filter=["basketball"], max_combos=10)},
    ],
    "Tennis_safe": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.3, cote_max=2.0, sort_by="wr", sports_filter=["tennis"], max_combos=10)},
    ],
    "Hockey_safe": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.4, cote_max=2.5, sort_by="wr", sports_filter=["ice-hockey"], max_combos=10)},
    ],
    "WR_3j_2-5_fb": [
        {"max_combos":5, "kwargs":dict(max_legs=3, cote_min=2.0, cote_max=5.0, sort_by="wr", sports_filter=["football","basketball"], max_combos=10)},
    ],
    "Cote_safe_1j": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.05, cote_max=1.5, sort_by="wr", sports_filter=["football","basketball","ice-hockey","tennis"], max_combos=10)},
    ],
    "All_sports_WR2j": [
        {"max_combos":5, "kwargs":dict(max_legs=2, cote_min=1.4, cote_max=2.5, sort_by="wr", sports_filter=ALL_SPORTS, max_combos=10)},
    ],
}

print()
print(f"{'Stratégie':25s} | " + " | ".join([f"{d[5:]:>5s}" for d in BAD_DAYS]) + " | total")
print("-" * 100)
for name, comps in strategies.items():
    pnls = []
    for d in BAD_DAYS:
        day_pnl = 0.0
        for c in comps:
            r = run_backtest(d, magic, stake=10.0, **c["kwargs"])
            for combo in r["combos"][:c["max_combos"]]:
                day_pnl += 10.0 * (combo["cote_t"]-1) if combo["won"] else -10.0
        pnls.append(day_pnl)
    total = sum(pnls)
    pnls_str = " | ".join([f"{p:>+5.0f}" for p in pnls])
    color = "✅" if total > 0 else "❌"
    print(f"{name:25s} | {pnls_str} | {total:+5.0f}€ {color}")

print()
print("=" * 100)
print("PARTIE 3 : Picks foncés H_daily_boost le 2026-04-28 (1er jour rouge)")
print("=" * 100)
d = "2026-04-28"
print(f"\nMatchs basket disponibles ce jour:")
matches_b = [m for m in idx.get(d, []) if m["sport"]=="basketball"]
for m in matches_b[:10]:
    print(f"  [{m['league'][:30]}] {m['home']} vs {m['away']}: {m['hs']}-{m['as']} (odds 1={m['odds_1']}, 2={m['odds_2']})")

print(f"\nPicks générés H_daily_boost composante WR2j foot+basket cote 1.4-2.5:")
r = run_backtest(d, magic, max_legs=2, cote_min=1.4, cote_max=2.5, sort_by="wr",
                 sports_filter=["football","basketball"], max_combos=10, stake=10.0)
for i, c in enumerate(r["combos"][:5], 1):
    won = "✅" if c["won"] else "❌"
    legs_str = " + ".join([f'{l["sport"][:3]} {l["selection"][:18]} @{l["odds"]:.2f} {"✓" if l["won"] else "✗"}' for l in c["legs"]])
    print(f"  {won} #{i} cote {c['cote_t']:.2f} wr {c['wr_t']*100:.0f}%: {legs_str}")
