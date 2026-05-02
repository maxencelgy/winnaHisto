#!/usr/bin/env python3
"""Test : matcher une PLAGE de cotes magiques au lieu de cote exacte ±0.01."""
import sys, json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, build_backtest_combos, round_cote
from morning_live import CATEGORIZERS, load_magic
import csv, os, glob

DATASETS = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
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

# Charger magic standard
magic_std = load_magic()

def aggregate_magic_by_range(magic, range_half=0.05):
    """Pour chaque cote magique, créer une magic_range qui matche dans [cote-h, cote+h].
    On agrège les WR pondérés par n si plusieurs cotes proches.
    Output : même format mais avec WR ajusté + nouvelle "halfwidth" pour le matching."""
    return magic, range_half  # passer juste le half-width, le matching se fait au runtime

def extract_picks_range(matches, magic_table, range_half=0.05):
    """Comme extract_picks mais matche cote ∈ [magic_cote - range_half, magic_cote + range_half]."""
    picks = []
    smart = magic_table.get("_smart", False)
    for m in matches:
        if smart:
            cf = CATEGORIZERS.get(m["sport"])
            bucket = cf(m.get("league",""), m.get("category","")) if cf else None
            magic = magic_table.get(m["sport"], {}).get(bucket, {})
        else:
            magic = magic_table.get(m["sport"], {})
        if not magic: continue
        for label, side, cf_field, won in [
            ("Home","1","odds_1",m["home_won"]),
            ("Away","2","odds_2",not m["home_won"] and not m["is_draw"]),
            ("Draw","X","odds_x",m["is_draw"]),
        ]:
            cote = m.get(cf_field)
            if not cote or cote <= 1: continue
            c_round = round_cote(cote)
            # Trouver la magic cote la plus proche dans la plage range_half
            best_match = None
            best_dist = float('inf')
            for mc_str, wr in magic.items():
                mc = float(mc_str)
                dist = abs(c_round - mc)
                if dist <= range_half and dist < best_dist:
                    best_dist = dist
                    best_match = (mc, wr)
            if best_match is None: continue
            mc, wr = best_match
            sel = m["home"] if side == "1" else (m["away"] if side == "2" else "Match nul")
            picks.append({
                "sport": m["sport"], "league": m["league"], "match": f'{m["home"]} vs {m["away"]}',
                "selection": sel, "side": side, "odds": cote, "wr": wr,
                "ev": wr * cote - 1, "won": won, "score": f'{m["hs"]}-{m["as"]}',
            })
    return picks

# Composition Multi_full
MULTI_FULL = [
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["football"]}, 2),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.0,"sort_by":"wr","sports_filter":["basketball"]}, 2),
    ({"max_legs":2,"cote_min":1.3,"cote_max":2.0,"sort_by":"wr","sports_filter":["tennis"]}, 1),
    ({"max_legs":2,"cote_min":1.4,"cote_max":2.5,"sort_by":"wr","sports_filter":["ice-hockey"]}, 1),
    ({"max_legs":3,"cote_min":2.0,"cote_max":5.0,"sort_by":"ev","sports_filter":["football","basketball"]}, 2),
    ({"max_legs":4,"cote_min":5.0,"cote_max":15.0,"sort_by":"ev","sports_filter":ALL_SPORTS}, 1),
    ({"max_legs":5,"cote_min":15.0,"cote_max":60.0,"sort_by":"ev","sports_filter":ALL_SPORTS}, 1),
]

def run_with_range(days, range_half):
    """Simule Multi_full avec extract_picks_range au lieu de extract exact."""
    idx = _get_index()
    daily_pnls = []
    for d in days:
        matches_full = idx.get(d, [])
        if not matches_full:
            continue
        used = Counter()
        day_pnl = 0.0
        for kwargs, mc in MULTI_FULL:
            sf = kwargs.get("sports_filter", ALL_SPORTS)
            matches_filt = [m for m in matches_full if m["sport"] in sf and league_ok(m["sport"], m.get("league",""))]
            picks = extract_picks_range(matches_filt, magic_std, range_half=range_half)
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

# Test sur 5 semestres
semesters = [
    ("S1-2024","2024-01-01","2024-06-30"),
    ("S2-2024","2024-07-01","2024-12-31"),
    ("S1-2025","2025-01-01","2025-06-30"),
    ("S2-2025","2025-07-01","2025-12-31"),
    ("S1-2026","2026-01-01","2026-05-02"),
]

print("=" * 95)
print("TEST : Plage de cotes magiques (au lieu de match exact ±0.01)")
print("=" * 95)
print(f"{'Semestre':10s} {'range_half':>11s} {'jours':>6s} {'jours+/-':>10s} {'PnL':>8s} {'série':>6s}")

for sem_name, sd, ed in semesters:
    days = list(gen_days(sd, ed))
    for rh_label, rh in [("0.01 (std)", 0.01), ("0.05", 0.05), ("0.10", 0.10), ("0.20", 0.20)]:
        pnls = run_with_range(days, rh)
        g = sum(1 for p in pnls if p > 0); r = sum(1 for p in pnls if p < 0)
        print(f"{sem_name:10s} {rh_label:>11s} {len(pnls):>6d} {g}/{r:<3d}      {sum(pnls):>+8.0f} {streak(pnls):>4d}j")
    print()
