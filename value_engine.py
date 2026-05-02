#!/usr/bin/env python3
"""
Value Engine — détecte les paris à edge positif en croisant cotes soft books (Winamax) vs sharp book (Pinnacle).

Méthodologie (inspirée du process pro multi-books) :
1. Fetch odds Pinnacle via The Odds API (free tier 500 req/mois)
2. Calcule fair price = retire la marge bookmaker (devigging par power method ou multiplicative)
3. Compare cotes Winamax/1xBet/Bwin du calendar à fair_price
4. Edge = cote_soft × fair_prob - 1
5. Si edge > seuil (par défaut 3%), output value bet avec sizing ¼ Kelly

Usage :
    export ODDS_API_KEY="ta_clé_the-odds-api"
    python3 value_engine.py
    python3 value_engine.py --sport tennis_atp --min-edge 0.03
    python3 value_engine.py --markets h2h,spreads,totals --conservative
"""

import argparse
import csv
import glob
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime


THE_ODDS_API_BASE = "https://api.the-odds-api.com/v4"

# Sports clés à scanner — calibrés sur les ligues que le user parie réellement
DEFAULT_SPORTS = [
    "soccer_norway_eliteserien",        # Bodø/Glimt safe-leg
    "soccer_portugal_primeira_liga",     # Sporting
    "soccer_conmebol_libertadores",      # Mirassol, Platense
    "soccer_conmebol_sudamericana",      # Alianza, Cienciano
    "soccer_morocco_botola_pro",         # FUS Rabat, FAR
    "soccer_south_africa_premier_league", # Mamelodi
    "soccer_argentina_primera_division",
    "soccer_brazil_campeonato",
    "soccer_uefa_champs_league",
    "soccer_epl",
    "soccer_spain_la_liga",
    "soccer_italy_serie_a",
    "basketball_euroleague",
    "basketball_nba",
    "basketball_nbl",
    "basketball_france_lnb",
    "icehockey_nhl",
    "icehockey_ahl",
    "icehockey_liiga",
    "mma_mixed_martial_arts",
    "aussierules_afl",
    "tennis_atp",
    "tennis_wta",
]


def fetch_odds(sport, regions="eu", markets="h2h,spreads,totals", api_key=None):
    """Fetch live odds for a sport from The Odds API.
    Returns list of events with bookmakers nested."""
    if not api_key:
        return None
    params = {
        "apiKey": api_key,
        "regions": regions,
        "markets": markets,
        "oddsFormat": "decimal",
    }
    url = f"{THE_ODDS_API_BASE}/sports/{sport}/odds?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ⚠️ Fetch failed for {sport}: {e}")
        return None


def devigging(odds_list, method="multiplicative"):
    """Retire la marge bookmaker pour obtenir les fair prices.
    odds_list : liste de cotes décimales pour TOUTES les issues d'un marché.
    Returns : liste de probas réelles (somme = 1)."""
    if not odds_list:
        return []
    raw = [1 / o for o in odds_list if o > 0]
    if not raw:
        return []
    total = sum(raw)
    if method == "multiplicative":
        return [p / total for p in raw]
    elif method == "power":
        # Power method : trouve k tel que sum(p_i^k) = 1
        # Approximation : itère sur k ∈ [0.5, 2]
        best_k = 1.0
        best_diff = float("inf")
        for k_int in range(50, 200):
            k = k_int / 100
            s = sum(p**k for p in raw)
            d = abs(s - 1)
            if d < best_diff:
                best_diff = d
                best_k = k
        return [p**best_k for p in raw]
    return [p / total for p in raw]


def kelly_quarter(p, c):
    """¼ Kelly fraction. Cap à 5% bk pour sécurité."""
    b = c - 1
    if b <= 0:
        return 0.0
    f = (p * b - (1 - p)) / b
    return max(0.0, min(f * 0.25, 0.05))


def find_value_bets(events, soft_book_names=("winamax", "1xbet", "bwin", "unibet", "betclic", "betfair", "marathonbet"),
                     sharp_book_name="pinnacle", min_edge=0.03):
    """Pour chaque event, compare cotes des soft books à Pinnacle (devigged).
    Match par substring sur key (winamax_fr matche 'winamax').
    Returns : liste de value bets avec sport, match, market, selection, soft_cote, fair_p, edge, kelly_size."""
    values = []
    for ev in events or []:
        sport = ev.get("sport_key", "?")
        match = f"{ev.get('home_team','?')} vs {ev.get('away_team','?')}"
        commence = ev.get("commence_time", "")

        sharp = next((b for b in ev.get("bookmakers", []) if b["key"] == sharp_book_name), None)
        if not sharp:
            continue

        # Pour chaque marché, calcule fair prices via devigging des cotes Pinnacle
        sharp_markets = {m["key"]: m for m in sharp.get("markets", [])}
        if not sharp_markets:
            continue

        for soft_book in ev.get("bookmakers", []):
            sk = soft_book["key"]
            if not any(sn in sk for sn in soft_book_names):
                continue
            for soft_market in soft_book.get("markets", []):
                mkey = soft_market["key"]
                sharp_m = sharp_markets.get(mkey)
                if not sharp_m:
                    continue

                sharp_outcomes = {o["name"]: o["price"] for o in sharp_m["outcomes"]}
                if mkey == "spreads":
                    # Pour les handicaps, key = name + point
                    sharp_outcomes = {(o["name"], o.get("point")): o["price"] for o in sharp_m["outcomes"]}
                elif mkey == "totals":
                    sharp_outcomes = {(o["name"], o.get("point")): o["price"] for o in sharp_m["outcomes"]}

                fair_probs = {}
                if sharp_outcomes:
                    keys = list(sharp_outcomes.keys())
                    odds = [sharp_outcomes[k] for k in keys]
                    probs = devigging(odds)
                    fair_probs = dict(zip(keys, probs))

                for soft_o in soft_market["outcomes"]:
                    if mkey == "spreads":
                        k = (soft_o["name"], soft_o.get("point"))
                    elif mkey == "totals":
                        k = (soft_o["name"], soft_o.get("point"))
                    else:
                        k = soft_o["name"]
                    fair_p = fair_probs.get(k)
                    if fair_p is None:
                        continue
                    soft_cote = soft_o["price"]
                    edge = fair_p * soft_cote - 1
                    if edge >= min_edge:
                        values.append({
                            "sport": sport,
                            "match": match,
                            "commence": commence,
                            "market": mkey,
                            "selection": str(k),
                            "soft_book": soft_book["key"],
                            "soft_cote": soft_cote,
                            "fair_prob": fair_p,
                            "fair_cote": 1 / fair_p if fair_p > 0 else 0,
                            "edge": edge,
                            "kelly_q": kelly_quarter(fair_p, soft_cote),
                        })
    return values


def cross_with_winamax_calendar(values, calendar_path):
    """Filtre les value bets qui apparaissent aussi dans le calendar Winamax scrapé.
    Match flou par nom d'équipe/joueur."""
    if not calendar_path or not os.path.exists(calendar_path):
        return values
    with open(calendar_path, encoding="utf-8") as f:
        cal = list(csv.DictReader(f))
    cal_matches = set()
    for r in cal:
        m = (r.get("match") or "").lower()
        for token in m.split():
            if len(token) > 4:
                cal_matches.add(token)

    filtered = []
    for v in values:
        m_lower = v["match"].lower()
        if any(token in m_lower for token in cal_matches):
            filtered.append(v)
    return filtered


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="all", help="all, ou ex. tennis_atp, soccer_epl")
    ap.add_argument("--markets", default="h2h,spreads,totals")
    ap.add_argument("--regions", default="eu")
    ap.add_argument("--min-edge", type=float, default=0.03)
    ap.add_argument("--api-key", default=os.getenv("ODDS_API_KEY"))
    ap.add_argument("--cross-winamax", action="store_true",
                    help="Filtre uniquement les events qui apparaissent dans winamax-calendar-*.csv")
    args = ap.parse_args()

    if not args.api_key:
        print("⚠️  Pas de clé API. Inscris-toi gratuit sur https://the-odds-api.com/")
        print("    puis : export ODDS_API_KEY=ta_clé")
        print("    Ou passe --api-key=...")
        print()
        print("=== MODE DÉMO (simulation des données) ===")
        # Démo : on construit des fake events pour montrer la sortie
        fake = [{
            "sport_key": "tennis_wta",
            "home_team": "Marta Kostyuk",
            "away_team": "Linda Noskova",
            "commence_time": "2026-04-29T19:00:00Z",
            "bookmakers": [
                {"key": "pinnacle", "markets": [
                    {"key": "h2h", "outcomes": [
                        {"name": "Marta Kostyuk", "price": 1.55},
                        {"name": "Linda Noskova", "price": 2.45}
                    ]},
                    {"key": "spreads", "outcomes": [
                        {"name": "Linda Noskova", "point": 3.0, "price": 1.93},
                        {"name": "Marta Kostyuk", "point": -3.0, "price": 1.93}
                    ]},
                ]},
                {"key": "winamax", "markets": [
                    {"key": "h2h", "outcomes": [
                        {"name": "Marta Kostyuk", "price": 1.62},
                        {"name": "Linda Noskova", "price": 2.30}
                    ]},
                    {"key": "spreads", "outcomes": [
                        {"name": "Linda Noskova", "point": 3.5, "price": 1.70},
                        {"name": "Marta Kostyuk", "point": -3.5, "price": 2.10}
                    ]},
                ]},
            ]
        }]
        values = find_value_bets(fake, min_edge=args.min_edge)
        print_values(values)
        return

    print(f"🔍 Scan via The Odds API (regions={args.regions}, markets={args.markets}, min_edge={args.min_edge*100:.1f}%)")
    sports = DEFAULT_SPORTS if args.sport == "all" else [args.sport]
    all_events = []
    for sp in sports:
        evts = fetch_odds(sp, regions=args.regions, markets=args.markets, api_key=args.api_key)
        if evts:
            print(f"  ✓ {sp}: {len(evts)} events")
            all_events.extend(evts)

    print(f"\nTotal events fetched : {len(all_events)}")
    values = find_value_bets(all_events, min_edge=args.min_edge)

    if args.cross_winamax:
        cal = sorted(glob.glob(os.path.expanduser("~/Downloads/winamax-calendar-*.csv")),
                     key=os.path.getmtime, reverse=True)
        if cal:
            before = len(values)
            values = cross_with_winamax_calendar(values, cal[0])
            print(f"  Filtre calendar Winamax : {before} → {len(values)} value bets")

    print_values(values)


def print_values(values):
    if not values:
        print("\n❌ Aucun value bet détecté. Élargis --min-edge ou ajoute des sports.")
        return
    values.sort(key=lambda v: -v["edge"])
    print(f"\n=== 🎯 {len(values)} VALUE BETS DÉTECTÉS ===\n")
    print(f"{'Sport':17} {'Match':40} {'Marché':10} {'Sélection':25} {'Book':9} {'Cote':>5} {'Fair':>5} {'Edge':>6} {'¼K%':>5}")
    print("-" * 130)
    for v in values[:25]:
        print(f"{v['sport']:17} {v['match'][:40]:40} {v['market']:10} {v['selection'][:25]:25} "
              f"{v['soft_book']:9} {v['soft_cote']:>5.2f} {v['fair_cote']:>5.2f} "
              f"{v['edge']*100:>+5.1f}% {v['kelly_q']*100:>4.1f}%")
    print()
    print("📊 Distribution par sport :")
    by_sport = defaultdict(int)
    for v in values:
        by_sport[v["sport"]] += 1
    for s, n in sorted(by_sport.items(), key=lambda x: -x[1]):
        print(f"  {s:30}  {n}")
    print()
    print("📋 Stratégie d'exécution :")
    print(f"  • Top {min(5,len(values))} value bets : mises ¼ Kelly cumulées = {sum(v['kelly_q'] for v in values[:5])*100:.2f}% bk/jour")
    print(f"  • Bk recommandé pour démarrer : 100-200€ → mises 0.50 à 5€ par pari")
    print(f"  • Tracker post-match : log cote pari, cote close (Pinnacle), résultat → calcule CLV")


if __name__ == "__main__":
    main()
