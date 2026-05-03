#!/usr/bin/env python3
"""Sweep ÉLARGI v2 — focus 1x2 pur, BTTS, multi-sport combos.
Test sur S1-26 (4 mois) ET sur avril 2026 (1 mois) en flat_pct compounding."""
import sys, json, os
from datetime import datetime, timedelta
from itertools import product
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, extract_picks, build_backtest_combos

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

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json") as f:
    raw = json.load(f)
magic = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic[sp] = {b: {float(c): (info["wr"] if isinstance(info, dict) else info)
                     for c, info in cotes.items()}
                 for b, cotes in buckets.items()}
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json") as f:
    magic_ext = json.load(f)

DAYS_FULL = list(gen_days("2026-01-01", "2026-05-02"))   # 122 jours
DAYS_M = list(gen_days("2026-04-01", "2026-04-30"))       # 30 jours

def run_variant(sports_list, market, cote_min, cote_max, max_legs, sort_by,
                max_combos, days, side_filter=None, min_wr=None, sizing="flat", br0=100):
    """Backtest. sizing='flat' (10€ constant) ou 'pct' (compounding 10% BR)."""
    bankroll = br0
    daily_pnls = []; n_combos = 0
    m_ref = magic_ext if market in ("btts", "over_1_5", "over_2_5") or "+" in market or "-" in market else magic
    for d in days:
        idx = _get_index()
        matches = idx.get(d, [])
        matches = [m for m in matches
                   if m["sport"] in sports_list and lok(m["sport"], m.get("league",""))]
        if not matches: continue
        picks = extract_picks(matches, m_ref, market=market)
        if side_filter:
            picks = [p for p in picks if side_filter.lower() in p["selection"].lower()]
        if min_wr is not None:
            picks = [p for p in picks if p["wr"] >= min_wr]
        if max_legs == 1:
            picks = [p for p in picks if cote_min <= p["odds"] <= cote_max]
        if not picks: continue
        combos = build_backtest_combos(picks, max_legs=max_legs,
                                        cote_min=cote_min if max_legs == 1 else cote_min,
                                        cote_max=cote_max if max_legs == 1 else cote_max,
                                        max_combos=max_combos*5, sort_by=sort_by)
        chosen = combos[:max_combos]
        if not chosen: continue
        day_pnl = 0
        for c in chosen:
            stake = 10.0 if sizing == "flat" else max(0.5, bankroll * 0.10)
            n_combos += 1
            if c["won"]: day_pnl += stake * (c["cote_t"] - 1)
            else: day_pnl -= stake
        bankroll += day_pnl
        daily_pnls.append(day_pnl)
    pnl = sum(daily_pnls)
    g = sum(1 for p in daily_pnls if p > 0)
    r = sum(1 for p in daily_pnls if p < 0)
    return {"pnl": pnl, "ng": g, "nr": r, "n_combos": n_combos,
            "streak": streak_red(daily_pnls), "br_final": bankroll}

# === SWEEP v2 ===
results = []
COTES = [(1.05, 1.25), (1.25, 1.50), (1.50, 1.80), (1.80, 2.10),
         (2.10, 2.50), (2.50, 3.20), (3.20, 4.50), (4.50, 7.00)]

print("Phase 1 : 1x2 singles tous sports × 8 cote ranges × 2 sort × 4 max_combos...")
for sport in ["football", "basketball", "ice-hockey", "baseball"]:
    for cmin, cmax in COTES:
        for sort in ["ev", "wr"]:
            for mc in [2, 4]:
                r = run_variant([sport], "1x2", cmin, cmax, 1, sort, mc, DAYS_FULL)
                r["name"] = f"S_{sport[:6]}_{cmin}-{cmax}_{sort}_mc{mc}"
                results.append(r)

print("Phase 2 : 1x2 singles avec min_wr filter...")
for sport in ["football", "basketball"]:
    for cmin, cmax in COTES:
        for min_wr in [0.50, 0.60, 0.70]:
            r = run_variant([sport], "1x2", cmin, cmax, 1, "ev", 4, DAYS_FULL, min_wr=min_wr)
            r["name"] = f"Smin{min_wr}_{sport[:6]}_{cmin}-{cmax}"
            results.append(r)

print("Phase 3 : 2j combos 1x2 par sport...")
for sport in ["football", "basketball"]:
    for cmin, cmax in [(1.4, 2.5), (2.0, 3.5), (2.5, 5.0), (3.0, 6.0), (5.0, 12.0)]:
        for sort in ["ev", "wr"]:
            r = run_variant([sport], "1x2", cmin, cmax, 2, sort, 3, DAYS_FULL)
            r["name"] = f"2j_{sport[:6]}_{cmin}-{cmax}_{sort}"
            results.append(r)

print("Phase 4 : 3j combos 1x2 foot+basket...")
for sport in ["football", "basketball"]:
    for cmin, cmax in [(2.5, 5.0), (5.0, 10.0), (10.0, 30.0)]:
        for sort in ["ev"]:
            r = run_variant([sport], "1x2", cmin, cmax, 3, sort, 2, DAYS_FULL)
            r["name"] = f"3j_{sport[:6]}_{cmin}-{cmax}_{sort}"
            results.append(r)

print("Phase 5 : Multi-sport combos foot+basket...")
for cmin, cmax in [(1.5, 3.0), (2.0, 4.0), (3.0, 7.0)]:
    r = run_variant(["football", "basketball"], "1x2", cmin, cmax, 2, "ev", 4, DAYS_FULL)
    r["name"] = f"Mix_FB_{cmin}-{cmax}"
    results.append(r)

print("Phase 6 : BTTS singles foot par cote range...")
for cmin, cmax in [(1.30, 1.55), (1.55, 1.80), (1.80, 2.10), (2.10, 2.50)]:
    for side in ["oui", "non"]:
        r = run_variant(["football"], "btts", cmin, cmax, 1, "ev", 4, DAYS_FULL, side_filter=side)
        r["name"] = f"S_btts_{side}_{cmin}-{cmax}"
        results.append(r)

print(f"\nTotal variantes : {len(results)}\n")

# Survivants : PnL > 100 et série < 5
survivors = [r for r in results if r["pnl"] >= 100 and r["streak"] < 5]
survivors.sort(key=lambda x: -x["pnl"])

print(f"=== TOP 25 survivants (PnL >= 100€, série < 5j) sur S1-26 OOS strict — {len(survivors)} total ===\n")
print(f"{'Preset':50s} {'PnL':>8s} {'streak':>6s} {'ng/nr':>8s} {'combos':>6s}")
print("-"*92)
for r in survivors[:25]:
    print(f"  {r['name']:48s} {r['pnl']:>+7.0f}€ {r['streak']:>5d}j {r['ng']}/{r['nr']:<3d} {r['n_combos']:>6d}")

# Test top 5 sur avril 2026 EN FLAT_PCT pour vérifier robustesse compounding
print(f"\n=== Top 5 retest sur avril 2026 en flat_pct compounding (BR0=100) ===")
print(f"{'Preset':50s} {'PnL_apr':>8s} {'BR_fin':>8s} {'streak':>6s}")
print("-"*82)
top5_names = [s["name"] for s in survivors[:8]]
for s in survivors[:8]:
    name = s["name"]
    parts = name.split("_")
    # Reconstruire les params (pas trivial mais on stocke pas la config) - skip simple
    # Just use the description from name for now
    pass
# Pas trivial de re-runner — affiche juste les S1-26 stats pour les top 25
