#!/usr/bin/env python3
"""Test H8 avec bankroll réelle limitée — voir si on bust."""
import sys, time
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import run_backtest
from morning_live import load_magic

magic = load_magic()
STAKE = 10.0
ALL_SPORTS = ["football","basketball","ice-hockey","baseball","tennis"]

def gen_days(start, end):
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)

H8_COMPS = [
    {"label":"EV3j", "max_combos":2, "kwargs":dict(max_legs=3, cote_min=2.0, cote_max=5.0, sort_by="ev",
                                                    sports_filter=["football","basketball"], max_combos=10)},
    {"label":"EV4j", "max_combos":1, "kwargs":dict(max_legs=4, cote_min=10.0, cote_max=50.0, sort_by="ev",
                                                    sports_filter=ALL_SPORTS, max_combos=10)},
    {"label":"EV5j", "max_combos":1, "kwargs":dict(max_legs=5, cote_min=20.0, cote_max=100.0, sort_by="ev",
                                                    sports_filter=ALL_SPORTS, max_combos=10)},
]

def sim(comps, bankroll0, mode, start="2024-01-01", end="2026-05-02"):
    """
    mode:
      'illimite'   : bankroll virtuelle, jamais bust (= H8 actuel, ROI overstated)
      'strict'     : skip combo si BR < 10€, BUST si BR <= 0
      'safe_only'  : tant que BR < BR0 → skip EV4j+EV5j (rebuild safe)
      'half_safe'  : tant que BR < BR0/2 → skip EV5j (le plus risqué)
      'prudent'    : mise = min(10, max(1, BR/20)) → jamais bust
    """
    br = bankroll0
    n, won, skip = 0, 0, 0
    bust_date = None
    br_min = br
    for d in gen_days(start, end):
        if mode != 'illimite' and br <= 0:
            bust_date = d
            break
        in_rebuild = (mode == "safe_only" and br < bankroll0) or (mode == "half_safe" and br < bankroll0 / 2)
        for comp in comps:
            if mode in ("safe_only","half_safe") and in_rebuild:
                if mode == "safe_only" and comp["label"] != "EV3j": continue
                if mode == "half_safe" and comp["label"] == "EV5j": continue
            r = run_backtest(d, magic, stake=STAKE, **comp["kwargs"])
            chosen = 0
            for combo in r["combos"]:
                if chosen >= comp["max_combos"]: break
                if mode == 'prudent':
                    stake = max(1.0, min(STAKE, br / 20))
                else:
                    stake = STAKE
                if mode != 'illimite' and br < stake:
                    skip += 1
                    continue
                if combo["won"]:
                    br += stake * (combo["cote_t"] - 1)
                    won += 1
                else:
                    br -= stake
                br_min = min(br_min, br)
                n += 1
                chosen += 1
                if mode not in ('illimite','prudent') and br <= 0:
                    bust_date = d
                    return n, won, skip, br, br_min, bust_date
    return n, won, skip, br, br_min, bust_date


print("=" * 110)
print("H8 sur 28 mois avec bankroll réelle limitée (pas illimitée)")
print("=" * 110)
print(f"{'BR0':>5s}€ {'mode':12s} {'n':>5s} {'won':>4s} {'wr%':>5s} {'finalBR':>10s} {'×':>5s} {'minBR':>8s} {'skip':>5s} {'bust?':>12s}")
print("-" * 110)

t0 = time.time()
# Baseline illimité
n, w, sk, br, br_min, bust = sim(H8_COMPS, 100, 'illimite')
print(f"{'100':>5s}€ {'illimite':12s} {n:>5d} {w:>4d} {w/n*100:>5.1f} {br:>+10.0f} {br/100:>5.1f} {br_min:>+8.0f} {sk:>5d} {'(virtual)':>12s}")

# Strict avec différentes bankroll
for br0 in [50, 100, 200, 300, 500, 1000]:
    n, w, sk, br, br_min, bust = sim(H8_COMPS, br0, 'strict')
    wr = w/n*100 if n else 0
    bust_str = bust if bust else "—"
    print(f"{br0:>5d}€ {'strict':12s} {n:>5d} {w:>4d} {wr:>5.1f} {br:>+10.0f} {br/br0:>5.1f} {br_min:>+8.0f} {sk:>5d} {bust_str:>12s}")
print(f"... strict elapsed {time.time()-t0:.0f}s")

print("\n=== Modes intelligents (skip risky composantes pendant rebuild) ===")
print(f"{'BR0':>5s}€ {'mode':12s} {'n':>5s} {'won':>4s} {'wr%':>5s} {'finalBR':>10s} {'×':>5s} {'minBR':>8s} {'skip':>5s} {'bust?':>12s}")
for br0 in [100, 200, 500]:
    for mode in ['safe_only','half_safe','prudent']:
        n, w, sk, br, br_min, bust = sim(H8_COMPS, br0, mode)
        wr = w/n*100 if n else 0
        bust_str = bust if bust else "—"
        print(f"{br0:>5d}€ {mode:12s} {n:>5d} {w:>4d} {wr:>5.1f} {br:>+10.0f} {br/br0:>5.1f} {br_min:>+8.0f} {sk:>5d} {bust_str:>12s}")

print(f"\nTotal {time.time()-t0:.0f}s")
