#!/usr/bin/env python3
"""Walk-forward Over/Under sur S2-2025 + S1-2026 pour valider l'EV.
Compare 4 stratégies isolées (Over_1_5, Under_1_5, Over_2_5, Under_2_5)
puis tente une intégration dans Multi_full."""
import sys, json
from collections import Counter
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, run_backtest, build_backtest_combos, extract_picks
from morning_live import load_magic

STAKE = 10.0
ALL_SPORTS = ["football"]

WHITELIST = {"football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
    "laliga 2","serie b","ligue 2","champions league","europa league","conference",
    "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
    "mls","liga mx","brasileirão série a","brasileirao série a","coupe","fa cup"]}
REJECT = ["doubles","qualifying","u23","u21","u19","u18","reserve","youth","next pro","utr ","ptt ",
          "regionalliga","série c","i-league","exhibition","national league,"]

def league_ok(sport, league):
    if not league: return False
    lg = league.lower()
    if any(r in lg for r in REJECT): return False
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

def run_simple(magic, days, market, cote_min, cote_max, max_picks_per_day=4, sort_by="ev"):
    """Backteste UN seul marché en isolé, max N picks/jour foot whitelisted."""
    daily_pnls = []
    for d in days:
        idx = _get_index()
        matches = idx.get(d, [])
        matches = [m for m in matches if m["sport"] == "football" and league_ok("football", m.get("league",""))]
        if not matches: continue
        picks = extract_picks(matches, magic, market=market)
        # Filtre cotes
        picks = [p for p in picks if cote_min <= p["odds"] <= cote_max]
        if not picks: continue
        if sort_by == "wr":
            picks.sort(key=lambda p: -p["wr"])
        else:
            picks.sort(key=lambda p: -p["ev"])
        # Dédup match
        seen_matches = set()
        chosen = []
        for p in picks:
            if p["match"] in seen_matches: continue
            seen_matches.add(p["match"])
            chosen.append(p)
            if len(chosen) >= max_picks_per_day: break
        # Simple paris = 1 jambe par pick
        day_pnl = 0.0
        for p in chosen:
            day_pnl += STAKE * (p["odds"] - 1) if p["won"] else -STAKE
        if day_pnl != 0:
            daily_pnls.append(day_pnl)
    return daily_pnls

# Charger magic étendu
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json") as f:
    raw = json.load(f)
# Wrap pour run_backtest format (sport→bucket→sub→cote→wr)
magic = {"_smart": True}
for sport, buckets in raw.items():
    if sport == "_smart": continue
    magic[sport] = {bucket: {sub: {float(c): wr for c, wr in cotes.items()}
                              for sub, cotes in subs.items() if isinstance(cotes, dict)}
                    for bucket, subs in buckets.items()}

# Périodes : OOS strict (calibration train_end = 2026-01-01)
periods = [
    ("S2-25 OOS", "2025-07-01", "2025-12-31"),
    ("S1-26 OOS", "2026-01-01", "2026-05-02"),
]

print(f"\n{'Période':12s} {'Stratégie':30s} {'jours':>6s} {'g/r':>10s} {'PnL':>9s} {'série':>6s} {'cote moy':>9s}")
print("-" * 90)

scenarios = [
    ("Over 1.5 cote 1.20-1.40 sort=ev", "over_1_5", 1.20, 1.40, "ev"),
    ("Over 1.5 cote 1.20-1.40 sort=wr", "over_1_5", 1.20, 1.40, "wr"),
    ("Over 1.5 cote 1.40-1.80 sort=ev", "over_1_5", 1.40, 1.80, "ev"),
    ("Over 2.5 cote 1.50-2.00 sort=ev", "over_2_5", 1.50, 2.00, "ev"),
    ("Over 2.5 cote 1.80-2.30 sort=ev", "over_2_5", 1.80, 2.30, "ev"),
    ("Under 1.5 cote 3.00-7.00 sort=ev", "under_1_5", 3.00, 7.00, "ev"),
    ("Under 2.5 cote 1.50-2.20 sort=ev", "under_2_5", 1.50, 2.20, "ev"),
]

for sem_name, sd, ed in periods:
    days = list(gen_days(sd, ed))
    for label, market, cmin, cmax, sb in scenarios:
        pnls = run_simple(magic, days, market, cmin, cmax, max_picks_per_day=4, sort_by=sb)
        if not pnls:
            print(f"{sem_name:12s} {label:30s} {'(no picks)':>40s}")
            continue
        g = sum(1 for p in pnls if p > 0)
        r = sum(1 for p in pnls if p < 0)
        pnl_total = sum(pnls)
        st = streak(pnls)
        print(f"{sem_name:12s} {label:30s} {len(pnls):>6d} {g}/{r:<3d}      {pnl_total:>+9.0f} {st:>4d}j")
    print()
