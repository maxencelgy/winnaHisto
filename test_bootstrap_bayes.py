#!/usr/bin/env python3
"""Test : Wilson lower bound filter + Bayesian shrinkage sur magic cotes."""
import sys, json
from math import sqrt
from collections import defaultdict, Counter
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, build_backtest_combos, extract_picks
from morning_live import CATEGORIZERS

STAKE = 10.0
ALL_SPORTS = ["football","basketball","ice-hockey","baseball","tennis"]

WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
                 "laliga 2","serie b","ligue 2","champions league","europa league","conference",
                 "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
                 "mls","liga mx","brasileirão série a","brasileirao série a","coupe","fa cup"],
    "basketball": ["nba","wnba","euroleague","eurocup","betclic élite","pro a","acb","liga endesa",
                   "lega basket","serie a","bbl","champions league"],
    "ice-hockey": ["nhl","khl","shl","liiga","ligue magnus","del","national league","extraliga","swiss"],
    "baseball": ["mlb"],
    "tennis": ["atp","wta","grand slam","masters","australian open","roland garros","wimbledon",
               "us open","miami","indian wells","monte carlo","madrid","rome"],
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

# === Charger magic raw avec n ===
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json") as f:
    magic_raw = json.load(f)

def wilson_lower(wr, n, z=1.96):
    if n == 0: return 0
    denom = 1 + z**2/n
    center = (wr + z**2/(2*n)) / denom
    margin = z * sqrt((wr*(1-wr) + z**2/(4*n))/n) / denom
    return max(0, center - margin)

def build_magic_standard(raw):
    """Format extract_picks : {_smart: True, sport: {bucket: {cote_str: wr_float}}}"""
    out = {"_smart": True}
    for sport, buckets in raw.items():
        out[sport] = {}
        for bucket, cotes in buckets.items():
            out[sport][bucket] = {}
            for cote_str, info in cotes.items():
                out[sport][bucket][cote_str] = info["wr"]
    return out

def build_magic_wilson(raw, threshold=0.50):
    """Filter : ne garder que cotes avec wilson_lower > threshold."""
    out = {"_smart": True}
    kept = 0; total = 0
    for sport, buckets in raw.items():
        out[sport] = {}
        for bucket, cotes in buckets.items():
            out[sport][bucket] = {}
            for cote_str, info in cotes.items():
                total += 1
                wl = wilson_lower(info["wr"], info["n"])
                if wl > threshold:
                    out[sport][bucket][cote_str] = info["wr"]
                    kept += 1
    print(f"  Wilson filter (>{threshold}): kept {kept}/{total} ({kept/total*100:.0f}%)")
    return out

def build_magic_bayes(raw, alpha0=20):
    """Bayesian shrinkage vers prior sport-level."""
    # Calculer WR prior par sport (moyenne pondérée par n)
    prior_per_sport = {}
    for sport, buckets in raw.items():
        total_n, total_wins = 0, 0
        for bucket, cotes in buckets.items():
            for cs, info in cotes.items():
                total_n += info["n"]; total_wins += info["wr"] * info["n"]
        prior_per_sport[sport] = total_wins / max(1, total_n)
    # Apply shrinkage
    out = {"_smart": True}
    for sport, buckets in raw.items():
        prior = prior_per_sport[sport]
        out[sport] = {}
        for bucket, cotes in buckets.items():
            out[sport][bucket] = {}
            for cs, info in cotes.items():
                wins = info["wr"] * info["n"]
                wr_bayes = (wins + alpha0 * prior) / (info["n"] + alpha0)
                out[sport][bucket][cs] = wr_bayes
    return out

# === Composition Multi_full ===
MULTI_FULL = [
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["football"]}, 2),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["basketball"]}, 2),
    ({"max_legs":2,"cote_min":1.3,"cote_max":2.0,"sort_by":"wr","sports_filter":["tennis"]}, 1),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.5,"sort_by":"wr","sports_filter":["ice-hockey"]}, 1),
    ({"max_legs":3,"cote_min":2.0,"cote_max":5.0,"sort_by":"ev","sports_filter":["football","basketball"]}, 2),
    ({"max_legs":4,"cote_min":5.0,"cote_max":15.0,"sort_by":"ev","sports_filter":ALL_SPORTS}, 1),
    ({"max_legs":5,"cote_min":15.0,"cote_max":60.0,"sort_by":"ev","sports_filter":ALL_SPORTS}, 1),
]

def run_with_magic(magic_table, days):
    idx = _get_index()
    daily_pnls = []
    for d in days:
        matches_full = idx.get(d, [])
        if not matches_full: continue
        used = Counter()
        day_pnl = 0.0
        for kwargs, mc in MULTI_FULL:
            sf = kwargs.get("sports_filter", ALL_SPORTS)
            matches_filt = [m for m in matches_full
                            if m["sport"] in sf and league_ok(m["sport"], m.get("league",""))]
            picks = extract_picks(matches_filt, magic_table)
            combos = build_backtest_combos(picks, max_legs=kwargs["max_legs"], cote_min=kwargs["cote_min"],
                                           cote_max=kwargs["cote_max"], max_combos=mc*5,
                                           sort_by=kwargs["sort_by"])
            chosen = 0
            for combo in combos:
                if chosen >= mc: break
                lk = [(l["match"],l["selection"]) for l in combo["legs"]]
                if any(used[k]>=1 for k in lk): continue
                for k in lk: used[k]+=1
                day_pnl += STAKE*(combo["cote_t"]-1) if combo["won"] else -STAKE
                chosen += 1
        if day_pnl != 0: daily_pnls.append(day_pnl)
    return daily_pnls

# === Build magic variantes ===
print("Construction des magic tables...")
m_std = build_magic_standard(magic_raw)
m_wilson_50 = build_magic_wilson(magic_raw, 0.50)
m_wilson_55 = build_magic_wilson(magic_raw, 0.55)
m_bayes_20 = build_magic_bayes(magic_raw, alpha0=20)
m_bayes_50 = build_magic_bayes(magic_raw, alpha0=50)

# === Test sur 5 semestres ===
semesters = [
    ("S1-2024","2024-01-01","2024-06-30"),
    ("S2-2024","2024-07-01","2024-12-31"),
    ("S1-2025","2025-01-01","2025-06-30"),
    ("S2-2025","2025-07-01","2025-12-31"),
    ("S1-2026","2026-01-01","2026-05-02"),
]

print(f"\n{'Semestre':10s} {'Variante':20s} {'jours':>6s} {'jours+/-':>10s} {'PnL':>8s} {'série':>6s}")
print("-" * 80)

for sem_name, sd, ed in semesters:
    days = list(gen_days(sd, ed))
    for label, magic in [("standard", m_std), ("wilson>0.50", m_wilson_50),
                          ("wilson>0.55", m_wilson_55), ("bayes α=20", m_bayes_20),
                          ("bayes α=50", m_bayes_50)]:
        pnls = run_with_magic(magic, days)
        g = sum(1 for p in pnls if p > 0); r = sum(1 for p in pnls if p < 0)
        print(f"{sem_name:10s} {label:20s} {len(pnls):>6d} {g}/{r:<3d}      "
              f"{sum(pnls):>+8.0f} {streak(pnls):>4d}j")
    print()
