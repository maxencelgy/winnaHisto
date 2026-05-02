#!/usr/bin/env python3
"""Tester skip-day post-perte et volume MASSIF pour casser le trade-off."""
import sys
from datetime import datetime, timedelta
from collections import Counter
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import run_backtest, _get_index
from morning_live import load_magic
magic = load_magic()
STAKE = 10.0
ALL_SPORTS = ["football","basketball","ice-hockey","baseball","tennis"]

# Leagues whitelist (Winamax FR)
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

# Composition Multi_full
MULTI_FULL = [
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["football"],"max_combos":2}, 2),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["basketball"],"max_combos":2}, 2),
    ({"max_legs":2,"cote_min":1.3,"cote_max":2.0,"sort_by":"wr","sports_filter":["tennis"],"max_combos":1}, 1),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.5,"sort_by":"wr","sports_filter":["ice-hockey"],"max_combos":1}, 1),
    ({"max_legs":3,"cote_min":2.0,"cote_max":5.0,"sort_by":"ev","sports_filter":["football","basketball"],"max_combos":2}, 2),
    ({"max_legs":4,"cote_min":5.0,"cote_max":15.0,"sort_by":"ev","sports_filter":ALL_SPORTS,"max_combos":1}, 1),
    ({"max_legs":5,"cote_min":15.0,"cote_max":60.0,"sort_by":"ev","sports_filter":ALL_SPORTS,"max_combos":1}, 1),
]

# Composition VOLUME_30 (30 combos très safe)
VOLUME_30 = [
    ({"max_legs":2,"cote_min":1.3,"cote_max":1.6,"sort_by":"wr","sports_filter":["football"],"max_combos":8}, 8),
    ({"max_legs":2,"cote_min":1.3,"cote_max":1.6,"sort_by":"wr","sports_filter":["basketball"],"max_combos":7}, 7),
    ({"max_legs":2,"cote_min":1.3,"cote_max":1.6,"sort_by":"wr","sports_filter":["tennis"],"max_combos":7}, 7),
    ({"max_legs":2,"cote_min":1.3,"cote_max":1.7,"sort_by":"wr","sports_filter":["ice-hockey"],"max_combos":4}, 4),
    ({"max_legs":2,"cote_min":1.3,"cote_max":1.7,"sort_by":"wr","sports_filter":["baseball"],"max_combos":4}, 4),
]

def simulate(strat_comps, days, skip_after_loss=False):
    """Run jour par jour avec optionnel skip-day après perte."""
    daily_pnls = []
    skip_next = False
    n_skipped = 0
    for d in days:
        if skip_next:
            n_skipped += 1
            skip_next = False
            continue
        used_picks = Counter()
        day_pnl = 0.0
        for kwargs, mc in strat_comps:
            r = run_backtest(d, magic, stake=STAKE, league_filter=league_ok, **kwargs)
            chosen = 0
            for combo in r["combos"]:
                if chosen >= mc: break
                lk = [(l["match"], l["selection"]) for l in combo["legs"]]
                if any(used_picks[k] >= 1 for k in lk): continue  # dedup max1
                for k in lk: used_picks[k] += 1
                day_pnl += STAKE*(combo["cote_t"]-1) if combo["won"] else -STAKE
                chosen += 1
        if day_pnl != 0:
            daily_pnls.append(day_pnl)
            if skip_after_loss and day_pnl < 0:
                skip_next = True
    return daily_pnls, n_skipped

# Test sur S2-2025 (6 mois pour avoir un vrai walk-forward sample)
days = list(gen_days("2025-07-01", "2025-12-31"))

print("=" * 90)
print("ANGLE 1 : SKIP-DAY après perte (Multi_full)")
print("=" * 90)
for label, skip in [("Sans skip", False), ("AVEC skip après perte", True)]:
    pnls, sk = simulate(MULTI_FULL, days, skip_after_loss=skip)
    g = sum(1 for p in pnls if p > 0); r = sum(1 for p in pnls if p < 0)
    print(f"{label:30s}: {len(pnls)} jours joués (+{sk} skipped) | "
          f"jours+/- {g}/{r} ({g/max(1,len(pnls))*100:.0f}%) | "
          f"PnL {sum(pnls):+.0f}€ | série rouge max {streak(pnls)}j")

print()
print("=" * 90)
print("ANGLE 2 : VOLUME MASSIF (30 combos cote 1.3-1.6 multi-sport)")
print("=" * 90)
pnls, _ = simulate(VOLUME_30, days, skip_after_loss=False)
g = sum(1 for p in pnls if p > 0); r = sum(1 for p in pnls if p < 0)
print(f"{'VOLUME_30 sans skip':30s}: {len(pnls)} jours | "
      f"jours+/- {g}/{r} ({g/max(1,len(pnls))*100:.0f}%) | "
      f"PnL {sum(pnls):+.0f}€ | série rouge max {streak(pnls)}j")

pnls, sk = simulate(VOLUME_30, days, skip_after_loss=True)
g = sum(1 for p in pnls if p > 0); r = sum(1 for p in pnls if p < 0)
print(f"{'VOLUME_30 + skip post-perte':30s}: {len(pnls)} jours (+{sk} skip) | "
      f"jours+/- {g}/{r} ({g/max(1,len(pnls))*100:.0f}%) | "
      f"PnL {sum(pnls):+.0f}€ | série rouge max {streak(pnls)}j")
