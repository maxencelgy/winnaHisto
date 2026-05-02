#!/usr/bin/env python3
"""
Monte Carlo simulator — stratégies 10€ → 100€ basées sur les edges historiques du user.

Usage :
    python3 montecarlo_strategies.py
    python3 montecarlo_strategies.py --runs 50000
    python3 montecarlo_strategies.py --conservative   # utilise borne basse Wilson IC95%
"""

import argparse
import csv
import glob
import math
import os
import random
import re
import statistics
from collections import defaultdict


def find_latest(pattern, base="~/Downloads"):
    p = sorted(glob.glob(os.path.expanduser(f"{base}/{pattern}")), key=os.path.getmtime, reverse=True)
    return p[0] if p else None


def fnum(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def load_history(path):
    with open(path, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r["selection_status"] in ("Gagné", "Perdu")]


def wilson_lower(won, n, z=1.96):
    if n == 0:
        return 0.0
    phat = won / n
    denom = 1 + z * z / n
    center = phat + z * z / (2 * n)
    margin = z * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (center - margin) / denom


def build_prob_lookup(hist, conservative=False):
    """Lookup empirique : (sport, market, bucket0.05) → p, avec fallback."""
    exact = defaultdict(lambda: {"n": 0, "won": 0})
    sport_cote = defaultdict(lambda: {"n": 0, "won": 0})
    sport_g = defaultdict(lambda: {"n": 0, "won": 0})
    cote_only = defaultdict(lambda: {"n": 0, "won": 0})

    for r in hist:
        o = fnum(r["selection_odds"])
        if o is None:
            continue
        s = (r.get("selection_sport") or "?").strip() or "?"
        m = (r.get("selection_market") or "?").strip() or "?"
        b05 = round(math.floor(o / 0.05) * 0.05, 2)
        b10 = round(math.floor(o / 0.1) * 0.1, 1)
        won = 1 if r["selection_status"] == "Gagné" else 0
        for d, key in [(exact, (s, m, b05)), (sport_cote, (s, b10)), (sport_g, s), (cote_only, b10)]:
            d[key]["n"] += 1
            d[key]["won"] += won

    def estim(d):
        if conservative:
            return wilson_lower(d["won"], d["n"])
        return d["won"] / d["n"] if d["n"] else 0

    return exact, sport_cote, sport_g, cote_only, estim


def get_prob(exact, sport_cote, sport_g, cote_only, estim, sport, market, cote, min_n=(10, 20, 30, 50)):
    b05 = round(math.floor(cote / 0.05) * 0.05, 2)
    b10 = round(math.floor(cote / 0.1) * 0.1, 1)
    e = exact.get((sport, market, b05))
    if e and e["n"] >= min_n[0]:
        return estim(e), f"exact {sport}/{market}/{b05} n={e['n']}/{e['won']}"
    sc = sport_cote.get((sport, b10))
    if sc and sc["n"] >= min_n[1]:
        return estim(sc), f"sport+cote {sport}/{b10} n={sc['n']}/{sc['won']}"
    sg = sport_g.get(sport)
    if sg and sg["n"] >= min_n[2]:
        return estim(sg), f"sport {sport} n={sg['n']}/{sg['won']}"
    co = cote_only.get(b10)
    if co and co["n"] >= min_n[3]:
        return estim(co), f"cote_only {b10} n={co['n']}/{co['won']}"
    return min(0.95, 1 / cote * 0.95), "implicit (no data)"


def kelly_fraction(p, c, multiplier=0.5, cap=0.5):
    b = c - 1
    if b <= 0:
        return 0.0
    f = (p * b - (1 - p)) / b
    return max(0.0, min(f * multiplier, cap))


# Jambes candidates : sport × marché × cote où l'historique du user montre un edge positif.
# Les cotes sont choisies dans les zones d'edge connues (Tennis 1.5-1.6 sets, Foot Résultat 1.7-1.8, etc.)
CANDIDATE_LEGS = [
    ("Football", "Résultat", 1.78),
    ("Football", "Résultat", 1.75),
    ("Tennis",   "Nombre de sets", 1.55),
    ("Tennis",   "Nombre de sets", 1.60),
    ("Football", "Résultat", 1.45),
    ("Football", "Vainqueur", 1.30),
    ("Tennis",   "Vainqueur", 1.40),
    ("Hockey",   "Vainqueur", 1.50),
    ("MMA",      "Vainqueur", 1.50),
]

BAD_SPORTS = {"Snooker", "Baseball"}


def pick_best_legs(n, prob_fn, target_cote=None):
    """Sélectionne n jambes avec le meilleur EV."""
    candidates = []
    for sport, market, cote in CANDIDATE_LEGS:
        if sport in BAD_SPORTS:
            continue
        p, src = prob_fn(sport, market, cote)
        ev = p * cote - 1
        candidates.append((ev, sport, market, cote, p, src))
    candidates.sort(key=lambda x: -x[0])
    # Pour combos, on duplique le meilleur edge (même type de pari plusieurs fois sur matchs différents)
    best = candidates[0]
    return [best] * n


def combo_p_c(legs):
    p = 1.0
    c = 1.0
    for ev, sport, market, cote, leg_p, src in legs:
        p *= leg_p
        c *= cote
    return p, c


# ---- Stratégies ----

def strat_single_shot(prob_fn):
    legs = pick_best_legs(4, prob_fn)
    p, c = combo_p_c(legs)
    def step(bankroll, n_bets):
        if n_bets >= 1:
            return None
        return bankroll, p, c
    return step, {"p": p, "c": c, "legs": legs}


def strat_compound_allin(prob_fn):
    legs = pick_best_legs(1, prob_fn)
    p, c = combo_p_c(legs)
    def step(bankroll, n_bets):
        return bankroll, p, c
    return step, {"p": p, "c": c, "legs": legs}


def strat_hk_n(prob_fn, n):
    legs = pick_best_legs(n, prob_fn)
    p, c = combo_p_c(legs)
    f = kelly_fraction(p, c)
    def step(bankroll, n_bets):
        if f <= 0:
            return None
        stake = round(bankroll * f, 2)
        return stake, p, c
    return step, {"p": p, "c": c, "f": f, "legs": legs}


def strat_hybrid(prob_fn, threshold=30):
    legs3 = pick_best_legs(3, prob_fn)
    legs2 = pick_best_legs(2, prob_fn)
    p3, c3 = combo_p_c(legs3)
    p2, c2 = combo_p_c(legs2)
    f3 = kelly_fraction(p3, c3)
    f2 = kelly_fraction(p2, c2)
    def step(bankroll, n_bets):
        if bankroll < threshold:
            return (round(bankroll * f3, 2), p3, c3) if f3 > 0 else None
        return (round(bankroll * f2, 2), p2, c2) if f2 > 0 else None
    return step, {"p3": p3, "c3": c3, "p2": p2, "c2": c2, "f3": f3, "f2": f2}


# ---- Simulation ----

def simulate_path(step_fn, bankroll0=10.0, target=100.0, max_bets=200, min_bet=1.0):
    bankroll = bankroll0
    bets = 0
    while bankroll < target and bets < max_bets and bankroll >= min_bet:
        action = step_fn(bankroll, bets)
        if action is None:
            break
        stake, p, c = action
        if stake < min_bet or stake > bankroll + 1e-9:
            break
        if random.random() < p:
            bankroll = bankroll - stake + stake * c
        else:
            bankroll = bankroll - stake
        bets += 1
    return min(bankroll, target * 5), bets  # cap pour éviter outliers


def run_sim(name, step_fn, n_runs=10000, target=100.0):
    finals = []
    bets_to_target = []
    for _ in range(n_runs):
        b, t = simulate_path(step_fn, target=target)
        finals.append(b)
        if b >= target:
            bets_to_target.append(t)
    p_succ = sum(1 for f in finals if f >= target) / n_runs
    p_bust = sum(1 for f in finals if f < 1) / n_runs
    median = statistics.median(finals)
    finals_sorted = sorted(finals)
    p5 = finals_sorted[max(0, n_runs // 20 - 1)]
    e_t = statistics.mean(bets_to_target) if bets_to_target else float("inf")
    return {"name": name, "p_succ": p_succ, "p_bust": p_bust,
            "median": median, "p5": p5, "e_t": e_t}


# ---- Calendar : picks concrets ----

CAL_SPORT_PAT = [
    ("Basket",   r"\b(NBA|WNBA|EuroLeague|Euroligue|EuroCup|BCL|Pro A|Pro B|Betclic Élite|BNXT|ACB|Liga ACB|Liga ENDESA|LFB|LNB|VTB|Serie A2|Lega Basket)\b"),
    ("Basket",   r"\b(Unicaja|Real Madrid Baloncesto|Bilbao Basket|Joventut|Valencia Basket|Baskonia|Lyon ASVEL|ASVEL|Monaco Basket|Cholet|Limoges CSP|Strasbourg IG|Le Mans Sarthe|Roanne|Dijon Basket|Gravelines|Paris Basketball|Juvi Cremona|Reale Mutua|Libertas Livorno|Urania Milano|Flammes Carolo|Lattes-Montpellier)\b"),
    ("Hockey",   r"\b(NHL|AHL|KHL|SHL|Liiga|DEL|Magnus|Czech Extraliga|Slovak Tipsport)\b"),
    ("Handball", r"\b(LNH|Starligue|Liqui Moly|EHF|Ligue Butagaz|European League|Handball)\b"),
    ("Handball", r"\b(Szeged|Flensburg-Handewitt|Hanovre Burgdorf|Veszprém|Kielce|PSG Handball|Nantes HBC|HBC Nantes|Nimes Handball|Montpellier Handball)\b"),
    ("Volley",   r"\b(Tauron Liga|Plusliga|CEV|Volley|Volleyball|DevelopRes|Bogdanka LUK|Lüneburg|Luneburg)\b"),
    ("AFL",      r"\bAFL\b|\b(Collingwood Magpies|Hawthorn|Sydney Swans|Geelong Cats|Richmond Tigers)\b"),
    ("MMA",      r"\b(UFC|Bellator|PFL|MMA|ONE Championship)\b"),
    ("Boxe",     r"\b(Boxe|Boxing|WBA|WBC|IBF|WBO)\b"),
    ("F1",       r"\b(F1|Formule\s?1|Grand Prix|MotoGP)\b"),
    ("Baseball", r"\b(MLB|NPB|KBO|Baseball)\b"),
    ("Snooker",  r"\b(Snooker|Crucible)\b"),
    ("Rugby",    r"\b(Top 14|Six Nations|Champions Cup|Pro D2|Super Rugby|United Rugby)\b"),
    ("Badminton",r"\b(Thomas Cup|Uber Cup|Sudirman|Badminton|BWF)\b"),
    ("Tennis",   r"\b(ATP|WTA|Madrid Open|Roland|Wimbledon|US Open|Tennis|Challenger|ITF|Simples|Doubles)\b"),
    ("Football", r"\b(Ligue 1|Ligue 2|Liga(?!\s?ACB|\sENDESA)|La Liga|Bundesliga|Serie A(?!\s?2)|Süper Lig|Premier League|Championship|Eredivisie|Ekstraklasa|MLS|UEFA|UCL|Champions League|Europa League|Conference League|Liga Portugal|Eliteserien|Veikkausliiga|Allsvenskan|Ligat ha'Al|CONCACAF|Copa Libertadores|Copa Sudamericana|Arkema|Botola)\b"),
    ("Football", r"\b(PSG|Real Madrid(?! Baloncesto)|Bayern|Dortmund|Manchester|Liverpool|Chelsea|Arsenal|Juventus|Sporting Portugal|Benfica|Porto|Ajax|Mirassol|FUS Rabat|Mamelodi|Polokwane|Atletico Madrid)\b"),
]


def reclass_calendar(row):
    if row.get("sport") and row["sport"] not in ("?", ""):
        return row["sport"]
    txt = f"{row.get('match','')} {row.get('competition','')} {row.get('selection','')}"
    for name, pat in CAL_SPORT_PAT:
        if re.search(pat, txt, re.I):
            return name
    return "?"


def find_picks_for_strategy(prob_fn, calendar_path, target_cote, n_legs, sport_filter=None, tolerance=0.15):
    """Trouve n_legs picks dans le calendar dont la cote ≈ target_cote et le sport est dans good_sports."""
    if not calendar_path:
        return []
    with open(calendar_path, encoding="utf-8") as f:
        cal = list(csv.DictReader(f))
    by_match = defaultdict(list)
    for r in cal:
        if "Demain" in r.get("match", ""):
            continue
        o = fnum(r.get("odds"))
        if o is None or o < 1.05:
            continue
        r["odds_f"] = o
        r["sport_clean"] = reclass_calendar(r)
        by_match[r.get("match", "")].append(r)
    candidates = []
    for match, lines in by_match.items():
        fav = min(lines, key=lambda x: x["odds_f"])
        sp = fav["sport_clean"]
        if sp in BAD_SPORTS or sp == "?":
            continue
        if sport_filter and sp not in sport_filter:
            continue
        cote = fav["odds_f"]
        if abs(cote - target_cote) > tolerance:
            continue
        market = fav.get("market") or "Vainqueur"
        p, src = prob_fn(sp, market, cote)
        ev = p * cote - 1
        if ev <= 0:
            continue
        candidates.append({
            "sport": sp, "match": match, "selection": fav.get("selection", ""),
            "cote": cote, "p": p, "ev": ev, "src": src,
            "competition": fav.get("competition", ""),
        })
    candidates.sort(key=lambda x: -x["ev"])
    # Diversifier : pas plus de 2 picks du même sport pour limiter corrélation
    picks = []
    sport_count = defaultdict(int)
    for c in candidates:
        if sport_count[c["sport"]] >= 2:
            continue
        picks.append(c)
        sport_count[c["sport"]] += 1
        if len(picks) >= n_legs:
            break
    return picks


# ---- Main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10000)
    ap.add_argument("--conservative", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    hist_path = find_latest("winamax-history-*.classified.csv") or find_latest("winamax-history-*.csv")
    cal_path = find_latest("winamax-calendar-*.csv")
    print(f"📂 Historique : {hist_path}")
    print(f"📂 Calendar  : {cal_path or '(aucun)'}")
    hist = load_history(hist_path)
    print(f"📊 Settled   : {len(hist)} paris{'  [mode CONSERVATEUR Wilson IC95%]' if args.conservative else ''}")

    exact, sport_cote, sport_g, cote_only, estim = build_prob_lookup(hist, conservative=args.conservative)
    def prob_fn(s, m, c):
        return get_prob(exact, sport_cote, sport_g, cote_only, estim, s, m, c)

    print("\n=== Calibration des jambes candidates ===")
    print(f"{'Jambe':35} {'p':>6} {'cote':>5} {'EV':>7}  source")
    for sport, market, cote in CANDIDATE_LEGS:
        p, src = prob_fn(sport, market, cote)
        ev = p * cote - 1
        print(f"  {sport:10} {market:18} {cote:.2f} →  {p:.3f}  {cote:.2f}  {ev:+.3f}  ({src})")

    strategies = [
        ("1. Single-shot combo cote 10",   strat_single_shot(prob_fn)),
        ("2. Compound all-in × N steps",   strat_compound_allin(prob_fn)),
        ("3. Half-Kelly mono-jambe",       strat_hk_n(prob_fn, 1)),
        ("4. Half-Kelly 2-leg combo",      strat_hk_n(prob_fn, 2)),
        ("5. Half-Kelly 3-leg combo",      strat_hk_n(prob_fn, 3)),
        ("6. Hybrid Pareto (3-leg→2-leg)", strat_hybrid(prob_fn)),
    ]

    print(f"\n=== Monte Carlo · {args.runs:,} runs · 10€ → 100€ ===")
    print(f"{'Stratégie':35} {'P(100€)':>9} {'P(bust)':>9} {'E[T]':>8} {'Médiane':>10} {'Pire 5%':>10}")
    print("-" * 84)
    sim_results = []
    for name, (step_fn, meta) in strategies:
        r = run_sim(name, step_fn, n_runs=args.runs)
        sim_results.append((r, meta))
        e_t_str = f"{r['e_t']:.1f}" if r["e_t"] != float("inf") else "—"
        print(f"{r['name']:35} {r['p_succ']*100:>7.1f}% {r['p_bust']*100:>7.1f}% {e_t_str:>8} {r['median']:>8.1f}€ {r['p5']:>8.1f}€")

    # Recommandation : maximise P(succès) - 2×P(bust) - 0.005×E[T] (pénalise vitesse modérément, bust fortement)
    def score(r):
        et = r["e_t"] if r["e_t"] != float("inf") else 200
        return r["p_succ"] - 2 * r["p_bust"] - 0.005 * et
    best, best_meta = max(sim_results, key=lambda x: score(x[0]))

    print(f"\n=== ✅ Stratégie recommandée ===")
    print(f"  ▶ {best['name']}")
    print(f"     P(100€)  = {best['p_succ']*100:.1f}%")
    print(f"     P(bust)  = {best['p_bust']*100:.1f}%")
    print(f"     E[T]     = {best['e_t']:.1f} paris")
    print(f"     Médiane  = {best['median']:.1f}€   |   Pire 5% = {best['p5']:.1f}€")

    # Picks concrets ce soir alignés avec la stratégie recommandée
    print(f"\n=== 🎯 Picks concrets ce soir ===")
    if not cal_path:
        print("  ⚠️  Pas de calendar trouvé. Rescrape via winamax-calendar.js")
        return

    # Détermine n_legs et target_cote selon la stratégie gagnante
    if "1." in best["name"]:
        n_legs, target = 4, 1.78
    elif "2." in best["name"]:
        n_legs, target = 1, 1.78  # 1 pari à la fois, à répéter 4 fois
    elif "3." in best["name"]:
        n_legs, target = 1, 1.78
    elif "4." in best["name"]:
        n_legs, target = 2, 1.78
    elif "5." in best["name"]:
        n_legs, target = 3, 1.78
    else:
        n_legs, target = 3, 1.78

    good_sports = {"Football", "Tennis", "Hockey", "MMA", "F1"}
    picks = find_picks_for_strategy(prob_fn, cal_path, target, n_legs,
                                    sport_filter=good_sports, tolerance=0.15)

    if not picks:
        print("  ⚠️  Pas de picks alignés avec target cote ≈ 1.78. Élargis la recherche.")
        picks = find_picks_for_strategy(prob_fn, cal_path, target, n_legs,
                                        sport_filter=good_sports, tolerance=0.30)
    if not picks:
        print("  ⚠️  Toujours rien. Le calendar est peut-être vide ou périmé. Rescrape via winamax-calendar.js")
        return

    combo_p = 1.0
    combo_c = 1.0
    print(f"  Stratégie {best['name']} → {n_legs}-leg combo, cote cible/jambe ≈ {target}")
    print(f"  {'#':>2} {'Sport':10} {'Pick':25} {'Cote':>6} {'p':>6} {'EV':>7}")
    for i, p in enumerate(picks, 1):
        sel = re.sub(r"^\d{1,4}", "", p["selection"]).strip()[:25]
        print(f"  {i:>2} {p['sport']:10} {sel:25} {p['cote']:>6.2f} {p['p']:>6.3f} {p['ev']:>+6.3f}")
        combo_p *= p["p"]
        combo_c *= p["cote"]
    print(f"\n  Combo {n_legs} jambes : cote {combo_c:.2f}, p ≈ {combo_p*100:.0f}%, EV {combo_p*combo_c-1:+.2f}€/€")

    # Mise recommandée
    if "Half-Kelly" in best["name"] or "Hybrid" in best["name"]:
        f = kelly_fraction(combo_p, combo_c)
        stake = round(10.0 * f, 2)
        print(f"  Mise recommandée (½ Kelly) : {stake}€ sur 10€ de bankroll")
    elif "Single-shot" in best["name"]:
        print(f"  Mise recommandée (all-in) : 10€")
    elif "Compound" in best["name"]:
        print(f"  Mise recommandée (compound all-in) : 10€ sur 1 pari → réinvestir gains")

    print("\n=== ⚠️  Limites ===")
    print("  • Cotes peuvent avoir bougé depuis le scrape — vérifier sur Winamax avant de miser.")
    print("  • Si combo Foot Résultat 1.7-1.8 (n=14) → IC95% large. Run --conservative pour stress-test.")
    print("  • Skip un soir sans match aligné > forcer un pari hors edge.")


if __name__ == "__main__":
    main()
