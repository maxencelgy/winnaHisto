#!/usr/bin/env python3
"""Test combos Over 1.5 : standalone (2j pur) et mixé (Over 1.5 + 1x2 safe / BTTS)."""
import sys, json
from itertools import combinations
from datetime import datetime, timedelta
sys.path.insert(0, "/Users/maxenceleguay/Sites/winnaHisto")
from backtest_engine import _get_index, extract_picks

WHITELIST = ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
    "laliga 2","serie b","ligue 2","champions league","europa league","conference",
    "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
    "mls","liga mx","brasileirão série a","brasileirao série a","coupe","fa cup"]
REJECT = ["doubles","qualifying","u23","u21","u19","u18","reserve","youth","next pro","utr ","ptt ",
          "regionalliga","série c","i-league","exhibition"]

def lok(lg):
    if not lg: return False
    l = lg.lower()
    if any(r in l for r in REJECT): return False
    return any(p in l for p in WHITELIST)

with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json") as f:
    magic = json.load(f)

def gen_days(sd, ed):
    s = datetime.strptime(sd,"%Y-%m-%d").date(); e = datetime.strptime(ed,"%Y-%m-%d").date()
    cur = s
    while cur <= e: yield cur.isoformat(); cur += timedelta(days=1)

STAKE = 10
def streak_red(daily):
    s=0;c=0
    for p in daily:
        if p < 0: c+=1; s=max(s,c)
        else: c=0
    return s

def filter_picks(picks, side_substr, cmin, cmax):
    return [p for p in picks if side_substr in p["selection"] and cmin <= p["odds"] <= cmax]

def make_combos(picks, n_legs, cmin, cmax, max_combos):
    """Combine picks en combos n-jambes, dedup match, sort EV."""
    cands = []
    for combo in combinations(picks, n_legs):
        if len({p["match"] for p in combo}) < n_legs: continue
        cote = 1; wr = 1; won = True
        for p in combo:
            cote *= p["odds"]; wr *= p["wr"]
            if not p["won"]: won = False
        if cmin <= cote <= cmax:
            cands.append({"legs": combo, "cote": cote, "wr": wr, "won": won, "ev": wr*cote-1})
    cands.sort(key=lambda c: -c["ev"])
    sel = []; used = set()
    for c in cands:
        keys = {(p["match"], p["selection"]) for p in c["legs"]}
        if any(len(keys & {(p["match"], p["selection"]) for p in s["legs"]}) >= 1 for s in sel):
            continue
        sel.append(c)
        if len(sel) >= max_combos: break
    return sel

def run_strategy(days, build_picks_fn, n_legs, cmin, cmax, max_combos, label):
    """build_picks_fn(matches) -> list of picks."""
    pnl = 0; ng=0; nr=0; n_combos=0; daily=[]
    for d in days:
        matches = _get_index().get(d, [])
        foot = [m for m in matches if m["sport"]=="football" and lok(m.get("league",""))]
        if not foot: continue
        picks = build_picks_fn(foot)
        combos = make_combos(picks, n_legs, cmin, cmax, max_combos)
        if not combos: continue
        day_pnl = sum(STAKE*(c["cote"]-1) if c["won"] else -STAKE for c in combos)
        pnl += day_pnl; n_combos += len(combos)
        if day_pnl > 0: ng+=1
        elif day_pnl < 0: nr+=1
        daily.append(day_pnl)
    return {"label": label, "pnl": pnl, "ng": ng, "nr": nr, "n": n_combos, "streak": streak_red(daily)}

# Build picks fonctions
def picks_over15_safe(matches):
    p = extract_picks(matches, magic, market="over_1_5")
    return [x for x in p if "Plus de 1.5" in x["selection"] and 1.40 <= x["odds"] <= 1.80]

def picks_1x2_safe(matches):
    p = extract_picks(matches, magic, market="1x2")
    return [x for x in p if x["selection"] != "Match nul" and 1.30 <= x["odds"] <= 1.80]

def picks_btts_yes(matches):
    p = extract_picks(matches, magic, market="btts")
    return [x for x in p if "Oui" in x["selection"] and 1.40 <= x["odds"] <= 2.00]

# Mixed: combine 2 listes de picks pour générer des combos hétérogènes
def picks_mixed_over15_x2(matches):
    return picks_over15_safe(matches) + picks_1x2_safe(matches)

def picks_mixed_over15_btts(matches):
    return picks_over15_safe(matches) + picks_btts_yes(matches)

# Test
print(f"\n{'Période':12s} {'Stratégie':50s} {'jours+/-':>10s} {'combos':>7s} {'PnL':>9s} {'série':>6s}")
print("-"*100)

for plabel, sd, ed in [("S2-25 OOS","2025-07-01","2025-12-31"), ("S1-26 OOS","2026-01-01","2026-05-02")]:
    days = list(gen_days(sd, ed))

    # A1: 2j Over 1.5 pur, cote totale 1.96-3.24
    r = run_strategy(days, picks_over15_safe, 2, 1.96, 3.24, 4, "2j Over1.5 pur cote 1.96-3.24")
    print(f"{plabel:12s} {r['label']:50s} {r['ng']}/{r['nr']:<3d}      {r['n']:>7d} {r['pnl']:>+9.0f} {r['streak']:>4d}j")

    # A2: 3j Over 1.5 pur, cote totale 2.74-5.83
    r = run_strategy(days, picks_over15_safe, 3, 2.74, 5.83, 2, "3j Over1.5 pur cote 2.74-5.83")
    print(f"{plabel:12s} {r['label']:50s} {r['ng']}/{r['nr']:<3d}      {r['n']:>7d} {r['pnl']:>+9.0f} {r['streak']:>4d}j")

    # B1: Mixed 2j Over1.5 + 1x2 safe (peut être 2x Over, 2x 1x2, ou 1+1)
    r = run_strategy(days, picks_mixed_over15_x2, 2, 1.7, 3.0, 4, "2j MIX Over1.5+1x2safe cote 1.7-3.0")
    print(f"{plabel:12s} {r['label']:50s} {r['ng']}/{r['nr']:<3d}      {r['n']:>7d} {r['pnl']:>+9.0f} {r['streak']:>4d}j")

    # B2: Mixed 3j Over1.5 + 1x2 safe
    r = run_strategy(days, picks_mixed_over15_x2, 3, 2.5, 5.0, 3, "3j MIX Over1.5+1x2safe cote 2.5-5.0")
    print(f"{plabel:12s} {r['label']:50s} {r['ng']}/{r['nr']:<3d}      {r['n']:>7d} {r['pnl']:>+9.0f} {r['streak']:>4d}j")

    # B3: Mixed 2j Over1.5 + BTTS
    r = run_strategy(days, picks_mixed_over15_btts, 2, 1.96, 3.6, 4, "2j MIX Over1.5+BTTS cote 1.96-3.6")
    print(f"{plabel:12s} {r['label']:50s} {r['ng']}/{r['nr']:<3d}      {r['n']:>7d} {r['pnl']:>+9.0f} {r['streak']:>4d}j")

    print()
