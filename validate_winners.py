#!/usr/bin/env python3
"""Validation finale des winners v5 avec la magic standard prod (train<2026-01-01).

Test sur :
  - S1-26 (Jan-Apr 2026) en flat_pct compounding BR=100
  - S1-26 en flat 10€ pour voir le PnL nominal
  - Mois par mois pour vérifier consistance
"""
import json, sys
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, extract_picks, build_backtest_combos

WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
        "laliga 2","serie b","ligue 2","champions league","europa league","conference",
        "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
        "mls","liga mx","brasileirão","brasileirao","coupe","fa cup",
        "primeira liga","primera división"],
    "basketball": ["nba","wnba","euroleague","eurocup","betclic élite","pro a","acb","liga endesa",
                   "lega basket","serie a","bbl","champions league"],
    "ice-hockey": ["nhl","khl","shl","liiga","ligue magnus","del","national league","extraliga","swiss"],
    "baseball": ["mlb"],
}
REJECT = ["doubles","qualifying","u23","u21","u19","u18","reserve","youth","next pro",
          "regionalliga","série c","i-league","exhibition"]

def lok(sport, lg):
    if not lg: return False
    l = lg.lower()
    if any(r in l for r in REJECT): return False
    return any(p in l for p in WHITELIST.get(sport, []))

def gen_days(sd, ed):
    s = datetime.strptime(sd,"%Y-%m-%d").date(); e = datetime.strptime(ed,"%Y-%m-%d").date()
    cur = s
    while cur <= e: yield cur.isoformat(); cur += timedelta(days=1)

def streak_red(daily):
    s=0;c=0
    for p in daily:
        if p < 0: c+=1; s=max(s,c)
        else: c=0
    return s

def max_dd(daily):
    cum=0;peak=0;dd=0
    for p in daily:
        cum+=p
        if cum>peak: peak=cum
        dd=max(dd, peak-cum)
    return dd

# Magic prod standard (train < 2026-01-01)
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json") as f:
    raw = json.load(f)
magic_prod = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic_prod[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                          for c,info in cotes.items()}
                      for b, cotes in buckets.items()}

# Magic 2025 (train < 2025-01-01) pour walk-forward strict
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart_2025.json") as f:
    raw = json.load(f)
magic_2025 = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic_2025[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                          for c,info in cotes.items()}
                      for b, cotes in buckets.items()}

def run(magic, days, sports_list, market, cote_min, cote_max, max_legs, sort_by,
        max_combos, side_filter=None, min_wr=None, sizing="pct", br0=100):
    bankroll = br0; daily = []; n_combos = 0; n_wins = 0
    for d in days:
        idx = _get_index()
        ms = idx.get(d, [])
        ms = [m for m in ms if m["sport"] in sports_list and lok(m["sport"], m.get("league",""))]
        if not ms: continue
        picks = extract_picks(ms, magic, market=market)
        if side_filter:
            picks = [p for p in picks if side_filter.lower() in p["selection"].lower()]
        if min_wr is not None:
            picks = [p for p in picks if p["wr"] >= min_wr]
        if max_legs == 1:
            picks = [p for p in picks if cote_min <= p["odds"] <= cote_max]
        if not picks: continue
        combos = build_backtest_combos(picks, max_legs=max_legs,
                                        cote_min=cote_min, cote_max=cote_max,
                                        max_combos=max_combos*5, sort_by=sort_by)
        chosen = combos[:max_combos]
        if not chosen: continue
        day_pnl = 0
        for c in chosen:
            stake = 10.0 if sizing=="flat" else max(0.5, bankroll*0.10)
            n_combos += 1
            if c["won"]: day_pnl += stake*(c["cote_t"]-1); n_wins += 1
            else: day_pnl -= stake
        bankroll += day_pnl
        daily.append(day_pnl)
    pnl = sum(daily)
    return {"pnl":pnl, "br_final":bankroll, "ng":sum(1 for p in daily if p>0),
            "nr":sum(1 for p in daily if p<0), "n_combos":n_combos, "n_wins":n_wins,
            "streak":streak_red(daily), "dd":max_dd(daily)}

WINNERS = [
    ("F_1.6-1.9_ev_mc3", dict(sports_list=["football"], market="1x2", cote_min=1.6, cote_max=1.9,
                              max_legs=1, sort_by="ev", max_combos=3)),
    ("F_1.6-1.9_wr_mc3", dict(sports_list=["football"], market="1x2", cote_min=1.6, cote_max=1.9,
                              max_legs=1, sort_by="wr", max_combos=3)),
    ("F_1.6-1.9_ev_mc4", dict(sports_list=["football"], market="1x2", cote_min=1.6, cote_max=1.9,
                              max_legs=1, sort_by="ev", max_combos=4)),
    ("F_1.6-1.9_wr_mc4", dict(sports_list=["football"], market="1x2", cote_min=1.6, cote_max=1.9,
                              max_legs=1, sort_by="wr", max_combos=4)),
    ("WR0.7_foot_2.0-2.8", dict(sports_list=["football"], market="1x2", cote_min=2.0, cote_max=2.8,
                                max_legs=1, sort_by="ev", max_combos=4, min_wr=0.70)),
    ("WR0.7_foot_1.8-2.5", dict(sports_list=["football"], market="1x2", cote_min=1.8, cote_max=2.5,
                                max_legs=1, sort_by="ev", max_combos=4, min_wr=0.70)),
]

MONTHS_26 = {
    "Jan26": list(gen_days("2026-01-01","2026-01-31")),
    "Feb26": list(gen_days("2026-02-01","2026-02-28")),
    "Mar26": list(gen_days("2026-03-01","2026-03-31")),
    "Apr26": list(gen_days("2026-04-01","2026-04-30")),
}
S1_26 = list(gen_days("2026-01-01","2026-04-30"))

print("="*100)
print("VALIDATION FINALE — Winners v5 retestés avec magic PROD (train<2026)")
print("="*100)

for name, cfg in WINNERS:
    print(f"\n=== {name} ===")
    print(f"  cfg: {cfg}\n")

    print("  Magic PROD (train<2026-01-01) sur S1-26 :")
    for mname, days in MONTHS_26.items():
        # flat_pct
        rp = run(magic_prod, days=days, sizing="pct", br0=100, **cfg)
        # flat 10€
        rf = run(magic_prod, days=days, sizing="flat", br0=100, **cfg)
        print(f"    {mname}: pct PnL +{rp['pnl']:.0f}€ BR_fin {rp['br_final']:.0f}€ "
              f"flat10 +{rf['pnl']:.0f}€ streak {rp['streak']}j combos {rp['n_combos']}")
    # Total S1-26
    rp_t = run(magic_prod, days=S1_26, sizing="pct", br0=100, **cfg)
    rf_t = run(magic_prod, days=S1_26, sizing="flat", br0=100, **cfg)
    rf500 = run(magic_prod, days=S1_26, sizing="pct", br0=500, **cfg)
    rf1000 = run(magic_prod, days=S1_26, sizing="pct", br0=1000, **cfg)
    print(f"  S1-26 TOTAL pct100: PnL +{rp_t['pnl']:.0f}€ BR_fin {rp_t['br_final']:.0f}€ "
          f"streak {rp_t['streak']}j DD {rp_t['dd']:.0f}€ {rp_t['n_combos']} combos")
    print(f"  S1-26 TOTAL flat10: PnL +{rf_t['pnl']:.0f}€ ")
    print(f"  S1-26 pct BR0=500 : BR_fin {rf500['br_final']:.0f}€ (+{rf500['pnl']:.0f}€)")
    print(f"  S1-26 pct BR0=1000: BR_fin {rf1000['br_final']:.0f}€ (+{rf1000['pnl']:.0f}€)")
