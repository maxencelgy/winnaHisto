#!/usr/bin/env python3
"""Pistes 3 (BR-aware stratification) et 4 (sport-specific edge) sans bias."""
import sys
from datetime import datetime, timedelta
from collections import Counter
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import run_backtest, _get_index
from morning_live import load_magic
magic = load_magic()
STAKE = 10.0
ALL_SPORTS = ["football","basketball","ice-hockey","baseball","tennis"]

WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
                 "laliga 2","serie b","ligue 2","champions league","europa league","conference",
                 "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
                 "mls","liga mx","brasileirão série a","brasileirao série a","coupe","fa cup",
                 "world cup","euro 2","copa america","africa cup"],
    "basketball": ["nba","wnba","euroleague","eurocup","betclic élite","pro a","acb","liga endesa",
                   "lega basket","serie a","bbl","champions league"],
    "ice-hockey": ["nhl","khl","shl","liiga","ligue magnus","del","national league","extraliga","swiss"],
    "baseball": ["mlb"],
    "tennis": ["atp","wta","grand slam","masters","australian open","roland garros","wimbledon",
               "us open","miami","indian wells","monte carlo","madrid","rome","cincinnati","shanghai"],
}
REJECT = ["doubles","qualifying","u23","u21","u19","u18","reserve","youth","next pro","utr ","ptt ",
          "regionalliga","série c","i-league","exhibition","national league,"]

def league_ok(sport, league):
    if not league: return False
    lg = league.lower()
    for r in REJECT:
        if r in lg: return False
    return any(p in lg for p in WHITELIST.get(sport, []))

def gen_days(start, end):
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)

def streak(daily_pnls):
    s=0;c=0
    for p in daily_pnls:
        if p < 0: c+=1; s=max(s,c)
        else: c=0
    return s

# Multi_full split safe vs lottery (pour piste 3 BR-aware)
SAFE_COMPS = [
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["football"]}, 2),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["basketball"]}, 2),
    ({"max_legs":2,"cote_min":1.3,"cote_max":2.0,"sort_by":"wr","sports_filter":["tennis"]}, 1),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.5,"sort_by":"wr","sports_filter":["ice-hockey"]}, 1),
    ({"max_legs":3,"cote_min":2.0,"cote_max":5.0,"sort_by":"ev","sports_filter":["football","basketball"]}, 2),
]
LOTTERY_COMPS = [
    ({"max_legs":4,"cote_min":5.0,"cote_max":15.0,"sort_by":"ev","sports_filter":ALL_SPORTS}, 1),
    ({"max_legs":5,"cote_min":15.0,"cote_max":60.0,"sort_by":"ev","sports_filter":ALL_SPORTS}, 1),
]

def simulate_BR_aware(days, br0, threshold_pct):
    """Si BR < threshold * BR0 → skip lottery (EV4j/EV5j)."""
    br = br0
    daily_pnls = []
    n_lottery_skipped = 0
    for d in days:
        used = Counter()
        day_pnl = 0.0
        in_safe_only = (br < br0 * threshold_pct)
        comps = SAFE_COMPS + ([] if in_safe_only else LOTTERY_COMPS)
        if in_safe_only:
            n_lottery_skipped += 1
        for kwargs, mc in comps:
            r = run_backtest(d, magic, stake=STAKE, league_filter=league_ok, max_combos=mc*5, **kwargs)
            chosen = 0
            for combo in r["combos"]:
                if chosen >= mc: break
                lk = [(l["match"], l["selection"]) for l in combo["legs"]]
                if any(used[k] >= 1 for k in lk): continue
                for k in lk: used[k] += 1
                day_pnl += STAKE*(combo["cote_t"]-1) if combo["won"] else -STAKE
                chosen += 1
        if day_pnl != 0:
            daily_pnls.append(day_pnl)
            br += day_pnl
    return daily_pnls, br, n_lottery_skipped

def simulate_simple(comps, days):
    daily = []
    for d in days:
        used = Counter()
        pnl = 0.0
        for kwargs, mc in comps:
            r = run_backtest(d, magic, stake=STAKE, league_filter=league_ok, max_combos=mc*5, **kwargs)
            ch = 0
            for c in r["combos"]:
                if ch >= mc: break
                lk = [(l["match"],l["selection"]) for l in c["legs"]]
                if any(used[k]>=1 for k in lk): continue
                for k in lk: used[k]+=1
                pnl += STAKE*(c["cote_t"]-1) if c["won"] else -STAKE
                ch += 1
        if pnl != 0: daily.append(pnl)
    return daily

semesters = [
    ("S1-2024","2024-01-01","2024-06-30"),
    ("S2-2024","2024-07-01","2024-12-31"),
    ("S1-2025","2025-01-01","2025-06-30"),
    ("S2-2025","2025-07-01","2025-12-31"),
    ("S1-2026","2026-01-01","2026-05-02"),
]

# === PISTE 3 : BR-aware stratification ===
print("=" * 95)
print("PISTE 3 : BR-aware stratification (Multi_full mais skip EV4j/EV5j si BR < 80% initial)")
print("=" * 95)
print(f"{'Semestre':10s} {'Mode':20s} {'jours+/-':>10s} {'PnL':>8s} {'série':>6s} {'lottery_skip':>13s}")
for name, sd, ed in semesters:
    days = list(gen_days(sd, ed))
    # Sans BR-aware (full Multi_full)
    full = simulate_simple(SAFE_COMPS + LOTTERY_COMPS, days)
    g = sum(1 for p in full if p > 0); r = sum(1 for p in full if p < 0)
    print(f"{name:10s} {'Multi_full all':20s} {g}/{r:<3d}      {sum(full):>+8.0f} {streak(full):>4d}j {'-':>13s}")
    # BR-aware
    pnls, br, n_skip = simulate_BR_aware(days, 100.0, 0.8)
    g = sum(1 for p in pnls if p > 0); r = sum(1 for p in pnls if p < 0)
    print(f"{name:10s} {'BR-aware (≤80€)':20s} {g}/{r:<3d}      {sum(pnls):>+8.0f} {streak(pnls):>4d}j {n_skip:>13d}")
    print()

# === PISTE 4 : Sport-specific edge ===
print("=" * 95)
print("PISTE 4 : Sport-specific edge (chaque sport en isolation, Multi_safe-style)")
print("=" * 95)
print(f"{'Semestre':10s}   " + "  ".join([f"{s:>9s}" for s in ALL_SPORTS]) + "  TOTAL")
for name, sd, ed in semesters:
    days = list(gen_days(sd, ed))
    pnls = []
    for sport in ALL_SPORTS:
        comps = [({"max_legs":2,"cote_min":1.3,"cote_max":2.0,"sort_by":"wr","sports_filter":[sport]}, 5),
                 ({"max_legs":3,"cote_min":2.0,"cote_max":5.0,"sort_by":"ev","sports_filter":[sport]}, 2)]
        d = simulate_simple(comps, days)
        pnls.append(sum(d))
    total = sum(pnls)
    print(f"{name:10s}   " + "  ".join([f"{p:>+9.0f}" for p in pnls]) + f"  {total:+.0f}€")
