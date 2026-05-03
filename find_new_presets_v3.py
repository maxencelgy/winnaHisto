#!/usr/bin/env python3
"""Sweep v3 — focus exhaustif sur ce qui pourrait casser le trade-off.

Critère "croustillant" :
  - PnL flat_pct (BR=100€, 10% bankroll) positif sur CHACUN des 4 mois (Jan/Feb/Mar/Apr 2026)
  - Streak rouge max ≤ 3j
  - DD < 25% BR
  - Au moins 30 combos joués sur la période (volume suffisant)

Phases :
  A. Hockey deep dive (toutes cote ranges étroites + sort + max_combos)
  B. Min_wr stricte cross-sport (≥ 0.65, 0.70, 0.75) avec cote 1.4-2.5
  C. 2j hockey safe (chaque jambe cote 1.20-1.50, sort wr)
  D. Cross-sport safe combos 2j (hockey+foot, hockey+basket)
  E. Per-league focus (NHL, NBA, Premier League, La Liga uniquement)
  F. BTTS oui foot par cote range étroit + sort
"""
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

def lok_specific(lg, league_substr):
    if not lg: return False
    return league_substr.lower() in lg.lower()

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
    """Max drawdown sur la série de pnl quotidiens."""
    cum = 0; peak = 0; dd = 0
    for p in daily:
        cum += p
        if cum > peak: peak = cum
        dd = max(dd, peak - cum)
    return dd

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

WINDOWS = {
    "Jan26": list(gen_days("2026-01-01","2026-01-31")),
    "Feb26": list(gen_days("2026-02-01","2026-02-28")),
    "Mar26": list(gen_days("2026-03-01","2026-03-31")),
    "Apr26": list(gen_days("2026-04-01","2026-04-30")),
}
ALL_DAYS = list(gen_days("2026-01-01","2026-04-30"))

def run_window(days, sports_list, market, cote_min, cote_max, max_legs, sort_by,
               max_combos, side_filter=None, min_wr=None, min_ev=None, league_substr=None,
               sizing="pct", br0=100):
    bankroll = br0
    daily = []
    n_combos = 0
    n_wins = 0
    m_ref = magic_ext if market in ("btts","over_1_5","over_2_5") or "+" in market or "-" in market else magic
    for d in days:
        idx = _get_index()
        ms = idx.get(d, [])
        if league_substr:
            ms = [m for m in ms if m["sport"] in sports_list and lok_specific(m.get("league",""), league_substr)]
        else:
            ms = [m for m in ms if m["sport"] in sports_list and lok(m["sport"], m.get("league",""))]
        if not ms: continue
        picks = extract_picks(ms, m_ref, market=market)
        if side_filter:
            picks = [p for p in picks if side_filter.lower() in p["selection"].lower()]
        if min_wr is not None:
            picks = [p for p in picks if p["wr"] >= min_wr]
        if min_ev is not None:
            picks = [p for p in picks if p["wr"]*p["odds"] >= min_ev]
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
            if c["won"]:
                day_pnl += stake * (c["cote_t"]-1)
                n_wins += 1
            else:
                day_pnl -= stake
        bankroll += day_pnl
        daily.append(day_pnl)
    pnl = sum(daily)
    return {"pnl": pnl, "br_final": bankroll,
            "ng": sum(1 for p in daily if p>0),
            "nr": sum(1 for p in daily if p<0),
            "n_combos": n_combos, "n_wins": n_wins,
            "streak": streak_red(daily), "dd": max_dd(daily)}

def run_full_eval(cfg):
    """Évalue cfg sur les 4 mois séparément + total. Retourne stats par mois."""
    results = {}
    for win_name, days in WINDOWS.items():
        results[win_name] = run_window(days=days, **cfg)
    results["TOTAL"] = run_window(days=ALL_DAYS, **cfg)
    return results

def is_croustillant(eval_res, min_pnl_total=80, max_streak=3, max_dd_pct=0.30, min_combos=30):
    """Critère strict pour être croustillant."""
    tot = eval_res["TOTAL"]
    if tot["pnl"] < min_pnl_total: return False
    if tot["streak"] > max_streak: return False
    if tot["dd"] > 100*max_dd_pct: return False
    if tot["n_combos"] < min_combos: return False
    # Au moins 3/4 mois positifs
    n_pos = sum(1 for w in ["Jan26","Feb26","Mar26","Apr26"] if eval_res[w]["pnl"] > 0)
    if n_pos < 3: return False
    return True

# ============== PHASES ==============
candidates = []

print("Phase A : Hockey deep dive (cote étroites + sort + max_combos)...")
for cmin, cmax in [(1.10,1.20),(1.20,1.30),(1.25,1.40),(1.30,1.45),(1.40,1.55),(1.50,1.65),(1.60,1.80),(1.25,1.50)]:
    for sort in ["wr","ev"]:
        for mc in [1,2,3,4,5]:
            cfg = dict(sports_list=["ice-hockey"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"H_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

print("Phase B : Min_wr stricte cross-sport...")
for sport in ["football","basketball","ice-hockey"]:
    for cmin, cmax in [(1.40,1.80),(1.50,2.00),(1.80,2.30),(1.50,2.50)]:
        for mwr in [0.65, 0.70, 0.75]:
            cfg = dict(sports_list=[sport], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by="ev", max_combos=4, min_wr=mwr)
            candidates.append((f"WR{mwr}_{sport[:6]}_{cmin}-{cmax}", cfg))

print("Phase C : 2j hockey safe...")
for cmin, cmax in [(1.20,1.50),(1.25,1.45),(1.30,1.50),(1.40,1.65)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["ice-hockey"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=2, sort_by=sort, max_combos=mc)
            candidates.append((f"H2j_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

print("Phase D : Cross-sport multi-sport (hockey+foot+basket safe)...")
for cmin, cmax in [(1.30,1.60),(1.40,1.80)]:
    for sort in ["wr","ev"]:
        for mc in [4,6,8]:
            cfg = dict(sports_list=["ice-hockey","football"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"HF_{cmin}-{cmax}_{sort}_mc{mc}", cfg))
            cfg2 = dict(sports_list=["ice-hockey","football","basketball"], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc)
            candidates.append((f"HFB_{cmin}-{cmax}_{sort}_mc{mc}", cfg2))

print("Phase E : Per-league focus...")
PER_LEAGUE = [
    ("ice-hockey","NHL"),
    ("ice-hockey","KHL"),
    ("ice-hockey","SHL"),
    ("basketball","NBA"),
    ("basketball","Euroleague"),
    ("football","Premier League"),
    ("football","LaLiga"),
    ("football","Bundesliga"),
    ("football","Serie A"),
    ("football","Ligue 1"),
]
for sport, lg in PER_LEAGUE:
    for cmin, cmax in [(1.20,1.50),(1.30,1.60),(1.40,1.80),(1.50,2.00)]:
        for sort in ["wr","ev"]:
            cfg = dict(sports_list=[sport], market="1x2", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=3, league_substr=lg)
            candidates.append((f"L_{lg[:8]}_{cmin}-{cmax}_{sort}", cfg))

print("Phase F : BTTS oui foot par cote range étroit...")
for cmin, cmax in [(1.40,1.55),(1.50,1.70),(1.55,1.75),(1.70,1.90),(1.80,2.00)]:
    for sort in ["wr","ev"]:
        for mc in [2,3,4]:
            cfg = dict(sports_list=["football"], market="btts", cote_min=cmin, cote_max=cmax,
                       max_legs=1, sort_by=sort, max_combos=mc, side_filter="oui")
            candidates.append((f"BO_{cmin}-{cmax}_{sort}_mc{mc}", cfg))

print(f"\nTotal candidats : {len(candidates)}\n")
print("="*90)

# Eval rapide d'abord (TOTAL only) puis full eval seulement sur les top survivants
quick = []
for name, cfg in candidates:
    r = run_window(days=ALL_DAYS, **cfg)
    quick.append((name, cfg, r))

# Filtrage : PnL TOTAL >= 50€ (BR0=100), streak <= 3, n_combos >= 30
filtered = [(n,c,r) for n,c,r in quick if r["pnl"]>=50 and r["streak"]<=3 and r["n_combos"]>=30]
filtered.sort(key=lambda x: -x[2]["pnl"])

print(f"\n=== {len(filtered)} candidats passent filtre rapide (PnL>=50, streak<=3, combos>=30) ===")
print(f"{'Preset':45s} {'PnL':>7s} {'BR':>7s} {'streak':>6s} {'DD':>6s} {'combos':>6s}")
print("-"*88)
for n,c,r in filtered[:30]:
    print(f"  {n:43s} {r['pnl']:>+6.0f}€ {r['br_final']:>6.0f}€ {r['streak']:>5d}j {r['dd']:>5.0f}€ {r['n_combos']:>6d}")

# Full eval mois par mois sur top 15
print(f"\n\n=== FULL EVAL MOIS PAR MOIS (top 15) ===\n")
print(f"{'Preset':40s} {'Jan':>7s} {'Feb':>7s} {'Mar':>7s} {'Apr':>7s} {'TOT':>7s} {'BR_fin':>7s} {'streak':>6s}")
print("-"*100)
top_full = []
for n, c, r in filtered[:15]:
    full = run_full_eval(c)
    top_full.append((n, c, full))
    j,f,m,a = (full[w]["pnl"] for w in ["Jan26","Feb26","Mar26","Apr26"])
    t = full["TOTAL"]
    is_c = is_croustillant(full)
    flag = "★" if is_c else " "
    print(f"{flag} {n:38s} {j:>+5.0f}€ {f:>+5.0f}€ {m:>+5.0f}€ {a:>+5.0f}€ {t['pnl']:>+5.0f}€ {t['br_final']:>6.0f}€ {t['streak']:>5d}j")

# Croustillants seulement
print(f"\n\n=== ★ CROUSTILLANTS (3/4 mois +, streak <= 3, DD < 30%) ===\n")
crous = [(n,c,f) for n,c,f in top_full if is_croustillant(f)]
if not crous:
    print("AUCUN candidat ne passe le critère croustillant.\n")
else:
    print(f"{'Preset':40s} {'Jan':>7s} {'Feb':>7s} {'Mar':>7s} {'Apr':>7s} {'TOT':>7s} {'streak':>6s}")
    for n,c,f in crous:
        j,fb,m,a = (f[w]["pnl"] for w in ["Jan26","Feb26","Mar26","Apr26"])
        t = f["TOTAL"]
        print(f"  {n:38s} {j:>+5.0f}€ {fb:>+5.0f}€ {m:>+5.0f}€ {a:>+5.0f}€ {t['pnl']:>+5.0f}€ {t['streak']:>5d}j")
        print(f"      cfg: {c}")

# Sauvegarder en JSON pour analyse ultérieure
out = {
    "all_quick": [{"name":n, "cfg":c, "result":r} for n,c,r in quick],
    "top_full": [{"name":n, "cfg":c, "monthly":f} for n,c,f in top_full],
    "croustillants": [{"name":n, "cfg":c, "monthly":f} for n,c,f in crous],
}
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/sweep_v3_results.json","w") as f:
    json.dump(out, f, indent=2, default=str)
print(f"\n💾 Résultats sauvegardés dans datasets/sweep_v3_results.json")
