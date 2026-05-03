#!/usr/bin/env python3
"""Sweep systématique de presets candidats sur S1-26 OOS strict.
Magic recalibrée 8 ans (train < 2026-01-01). On cherche les configurations
qui survivent réellement en OOS, pas juste en backtest repaint."""
import sys, json, os
from datetime import datetime, timedelta
from collections import Counter
from itertools import combinations
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, extract_picks, build_backtest_combos

# Whitelist Winamax FR
WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
        "laliga 2","serie b","ligue 2","champions league","europa league","conference",
        "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
        "mls","liga mx","brasileirão","brasileirao","coupe","fa cup",
        "primeira liga", "primera división"],
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

# Magic 8 ans
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json") as f:
    raw = json.load(f)
magic = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic[sp] = {b: {float(c): (info["wr"] if isinstance(info, dict) else info)
                     for c, info in cotes.items()}
                 for b, cotes in buckets.items()}

# Magic extended pour marchés over/btts
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json") as f:
    magic_ext = json.load(f)

STAKE = 10
DAYS = list(gen_days("2026-01-01", "2026-05-02"))

def run_variant(sports_list, market, cote_min, cote_max, max_legs, sort_by,
                max_combos, side_filter=None):
    """Run a backtest variant on S1-26 OOS, return stats."""
    pnl = 0; ng = 0; nr = 0; n_combos = 0; daily = []; n_days = 0
    for d in DAYS:
        idx = _get_index()
        matches = idx.get(d, [])
        matches = [m for m in matches
                   if m["sport"] in sports_list and lok(m["sport"], m.get("league",""))]
        if not matches: continue
        m_ref = magic_ext if market in ("btts", "over_1_5", "over_2_5") else magic
        picks = extract_picks(matches, m_ref, market=market)
        if side_filter:
            picks = [p for p in picks if side_filter.lower() in p["selection"].lower()]
        # Cote filter
        picks = [p for p in picks if cote_min <= p["odds"] <= cote_max] if max_legs == 1 else picks
        if not picks: continue
        combos = build_backtest_combos(picks, max_legs=max_legs,
                                        cote_min=cote_min if max_legs == 1 else (cote_min**max_legs),
                                        cote_max=cote_max if max_legs == 1 else (cote_max**max_legs),
                                        max_combos=max_combos*5, sort_by=sort_by)
        chosen = combos[:max_combos]
        if not chosen: continue
        n_days += 1
        day_pnl = 0
        for c in chosen:
            n_combos += 1
            day_pnl += STAKE*(c["cote_t"]-1) if c["won"] else -STAKE
        pnl += day_pnl
        daily.append(day_pnl)
        if day_pnl > 0: ng += 1
        elif day_pnl < 0: nr += 1
    return {"pnl": pnl, "ng": ng, "nr": nr, "n_combos": n_combos, "n_days": n_days,
            "streak": streak_red(daily)}

# === Sweep ===
results = []
COTES_RANGES = [
    (1.05, 1.25), (1.25, 1.50), (1.50, 1.80), (1.80, 2.10),
    (2.10, 2.50), (2.50, 3.20), (3.20, 4.50), (4.50, 7.00), (7.00, 15.0),
]

# 1) Singles 1x2 par sport × cote range × sort
print("[1] Singles 1x2 par sport × cote range × sort EV/WR...")
for sport in ["football", "basketball", "ice-hockey", "baseball"]:
    for cmin, cmax in COTES_RANGES:
        for sort in ["ev", "wr"]:
            r = run_variant([sport], "1x2", cmin, cmax, 1, sort, 4)
            r["name"] = f"Single_{sport[:6]}_{cmin}-{cmax}_{sort}"
            results.append(r)

# 2) Singles Over 1.5 / 2.5 foot par cote range
print("[2] Singles Over markets foot...")
for cmin, cmax in [(1.10, 1.30), (1.30, 1.55), (1.55, 1.85), (1.85, 2.20), (2.20, 3.00)]:
    for market in ["over_1_5", "over_2_5"]:
        for side in ["plus", "moins"]:
            r = run_variant(["football"], market, cmin, cmax, 1, "ev", 4, side_filter=side)
            r["name"] = f"Single_foot_{market}_{cmin}-{cmax}_{side}"
            results.append(r)

# 3) Singles BTTS foot par cote range
print("[3] Singles BTTS foot...")
for cmin, cmax in [(1.30, 1.60), (1.60, 1.90), (1.90, 2.30)]:
    for side in ["oui", "non"]:
        r = run_variant(["football"], "btts", cmin, cmax, 1, "ev", 4, side_filter=side)
        r["name"] = f"Single_foot_btts_{cmin}-{cmax}_{side}"
        results.append(r)

# 4) Combos 2j 1x2 par sport
print("[4] Combos 2j 1x2 par sport × cote range...")
for sport in ["football", "basketball"]:
    for cmin, cmax in [(1.40, 2.50), (2.50, 5.0), (5.0, 12.0)]:
        for sort in ["ev", "wr"]:
            r = run_variant([sport], "1x2", cmin, cmax, 2, sort, 3)
            r["name"] = f"2j_{sport[:6]}_{cmin}-{cmax}_{sort}"
            results.append(r)

# Display top
print(f"\n=== Top 25 par PnL (sur {len(results)} variantes) ===\n")
print(f"{'Preset':50s} {'combos':>6s} {'jours+/-':>8s} {'PnL':>8s} {'série':>6s}")
print("-"*92)
results.sort(key=lambda x: -x["pnl"])
for r in results[:25]:
    flag = "✅" if r["pnl"] > 0 else "🔴"
    print(f"{flag} {r['name']:48s} {r['n_combos']:>6d} {r['ng']}/{r['nr']:<3d}    {r['pnl']:>+8.0f} {r['streak']:>4d}j")

# Filtrer survivants : PnL > 100 ET série < 5
print(f"\n=== Survivants (PnL >= 100€ ET série rouge < 5j) ===\n")
survivors = [r for r in results if r["pnl"] >= 100 and r["streak"] < 5]
print(f"  {len(survivors)} variantes survivent\n")
for r in survivors[:15]:
    print(f"  ✓ {r['name']:48s} PnL {r['pnl']:>+5.0f} streak {r['streak']:>2d}j combos {r['n_combos']}")
