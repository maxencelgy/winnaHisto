#!/usr/bin/env python3
"""Simule des stratégies MONTANTES sur les données historiques.

Une montante : on part de N€, all-in sur palier 1, si gagne → all-in sur palier 2, etc.
Si un palier perd, on perd la mise et on redémarre avec N€ frais le lendemain.
Objectif : atteindre target_multiplier × initial_stake.

Pour qu'une montante soit profitable il faut un EDGE SIGNIFICATIF sur les cotes basses.
"""
import sys, os, json, math
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_engine import _get_index, extract_picks, build_backtest_combos

WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship",
        "laliga 2","serie b","ligue 2","champions league","europa league","conference",
        "eredivisie","liga portugal","pro league","süper lig","trendyol süper",
        "mls","liga mx","brasileirão","brasileirao","coupe","fa cup","primeira liga","primera división"],
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

# Charger magic OOS (train<2026-01-01)
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart_oos.json") as f:
    raw = json.load(f)
magic = {"_smart": True}
for sp, buckets in raw.items():
    if sp == "_smart": continue
    magic[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                     for c,info in cotes.items()}
                 for b, cotes in buckets.items()}


def simulate_montante(sports, cote_min, cote_max, target_mult, initial_stake,
                       start_date, end_date, sort_by="wr", min_wr=None):
    """Simule une montante.
    Chaque jour : prend top 1 pick selon critères, mise totale courante.
    Si gagne : capital × cote. Si atteint target → cash out, redémarre avec initial_stake.
    Si perd : reset à initial_stake.
    """
    s = datetime.strptime(start_date,"%Y-%m-%d").date()
    e = datetime.strptime(end_date,"%Y-%m-%d").date()
    days = []
    cur = s
    while cur <= e: days.append(cur.isoformat()); cur += timedelta(days=1)

    capital = initial_stake
    palier = 0
    n_palier_target = math.ceil(math.log(target_mult) / math.log((cote_min+cote_max)/2))
    total_invested = initial_stake  # tracking total mises in

    n_cycles = 0
    n_success = 0
    n_paliers_total = 0
    n_paliers_won = 0
    final_pnl = 0
    trace = []  # (date, palier, capital, action, won)

    for d in days:
        idx = _get_index()
        ms = idx.get(d, [])
        ms = [m for m in ms if m["sport"] in sports and lok(m["sport"], m.get("league",""))]
        if not ms: continue
        picks = extract_picks(ms, magic, market="1x2")
        picks = [p for p in picks if cote_min <= p["odds"] <= cote_max]
        if min_wr is not None:
            picks = [p for p in picks if p["wr"] >= min_wr]
        if not picks: continue

        # Sort
        if sort_by == "wr":
            picks.sort(key=lambda p: -p["wr"])
        elif sort_by == "ev":
            picks.sort(key=lambda p: -p["wr"]*p["odds"])

        pick = picks[0]
        palier += 1
        n_paliers_total += 1
        won = pick.get("won", False)

        if won:
            new_capital = capital * pick["odds"]
            n_paliers_won += 1
            if new_capital >= initial_stake * target_mult:
                # Cash out
                final_pnl += new_capital - initial_stake
                trace.append((d, palier, new_capital, "CASHOUT", True))
                n_success += 1
                n_cycles += 1
                capital = initial_stake
                palier = 0
                total_invested += initial_stake
            else:
                trace.append((d, palier, new_capital, "win", True))
                capital = new_capital
        else:
            # Perd, reset
            final_pnl -= capital  # perd la mise courante (qui était capital)
            # Wait, capital était déjà investi. PnL = -capital_avant_pari + 0 = -capital_avant_pari
            # Mais total_invested déjà compte initial_stake au début. Après chaque cycle perdu, on réinvestit initial_stake.
            trace.append((d, palier, 0, "LOSE", False))
            n_cycles += 1
            capital = initial_stake
            palier = 0
            total_invested += initial_stake

    return {
        "n_cycles": n_cycles,
        "n_success": n_success,
        "success_rate": n_success / max(n_cycles, 1),
        "n_paliers_total": n_paliers_total,
        "n_paliers_won": n_paliers_won,
        "wr_paliers": n_paliers_won / max(n_paliers_total, 1),
        "n_palier_needed": n_palier_target,
        "total_invested": total_invested,
        "final_pnl": final_pnl,
        "roi": final_pnl / max(total_invested, 1) * 100,
        "trace_last": trace[-10:],
    }


# Tests sur S1-26 (4 mois OOS strict)
START = "2026-01-01"
END = "2026-04-30"
INITIAL = 10  # 10€ par cycle

print(f"=== Simulation montantes sur {START} → {END} (BR initiale {INITIAL}€/cycle) ===\n")
print(f"{'Stratégie':50s} {'cycles':>6s} {'success':>7s} {'wr_palier':>9s} {'PnL':>7s} {'ROI':>6s}")
print("-"*95)

# 1. Hockey safe cote 1.25-1.40 → ×10 (besoin ~10 paliers)
for sport, smin, smax, tgt, name in [
    (["ice-hockey"], 1.20, 1.40, 10, "Hockey ×10 cote 1.20-1.40"),
    (["ice-hockey"], 1.25, 1.45, 10, "Hockey ×10 cote 1.25-1.45"),
    (["ice-hockey"], 1.30, 1.50, 10, "Hockey ×10 cote 1.30-1.50"),
    (["ice-hockey"], 1.40, 1.60, 5, "Hockey ×5 cote 1.40-1.60"),
    (["basketball"], 1.20, 1.40, 10, "Basket ×10 cote 1.20-1.40"),
    (["basketball"], 1.10, 1.30, 10, "Basket ×10 cote 1.10-1.30"),
    (["football"], 1.30, 1.50, 10, "Foot ×10 cote 1.30-1.50"),
    (["football"], 1.40, 1.60, 5, "Foot ×5 cote 1.40-1.60"),
    (["football"], 1.50, 1.70, 5, "Foot ×5 cote 1.50-1.70"),
    (["football", "ice-hockey"], 1.30, 1.50, 10, "Foot+Hockey ×10 cote 1.30-1.50"),
    (["football", "ice-hockey", "basketball"], 1.25, 1.45, 10, "FHB ×10 cote 1.25-1.45"),
    (["football", "ice-hockey", "basketball"], 1.20, 1.40, 10, "FHB ×10 cote 1.20-1.40"),
    (["football", "ice-hockey", "basketball"], 1.40, 1.60, 5, "FHB ×5 cote 1.40-1.60"),
]:
    r = simulate_montante(sport, smin, smax, tgt, INITIAL, START, END, sort_by="wr")
    flag = "🌟" if r["roi"] > 100 else "★" if r["roi"] > 0 else "✗" if r["roi"] < -50 else " "
    print(f"{flag} {name:48s} {r['n_cycles']:>6d} {r['n_success']:>2d}/{r['n_cycles']:<3d} "
          f"{r['wr_paliers']*100:>6.0f}%  {r['final_pnl']:>+5.0f}€ {r['roi']:>+5.0f}%")
