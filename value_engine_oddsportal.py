#!/usr/bin/env python3
"""
Value Engine OddsPortal — détecte les value bets en comparant Winamax (soft book)
à des sharp books (Pinnacle si dispo, sinon Stake.com / Roobet / Bets.io).

Input : CSV produit par OddsHarvester (oddsharvester upcoming -s tennis -m match_winner ...)
Output : value bets avec edge ≥ seuil + ranking par EV

Usage :
    python3 value_engine_oddsportal.py /tmp/oh-tennis.csv
    python3 value_engine_oddsportal.py /tmp/oh-foot.csv --min-edge 0.03 --soft winamax
"""

import argparse
import ast
import csv
import os
import sys
from collections import defaultdict


# Bookmakers considérés comme sharps (lignes les plus précises)
SHARP_BOOKIES = {"Pinnacle", "Pinnacle Sports", "Stake.com", "Roobet", "Bets.io", "Smarkets"}
# Soft books (cibles potentielles de value bet)
SOFT_BOOKIES_FR = {"Winamax", "Winamax.fr", "Betclic.fr", "bwin.fr", "Unibet.fr", "Bwin", "Unibet", "Betclic"}


def parse_market(raw):
    """Parse le champ 'match_winner_market' qui est une str repr d'une liste de dicts."""
    if not raw or raw.strip() == "":
        return []
    try:
        return ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        return []


def fnum(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def devig_multiplicative(odds_list):
    """Retire la marge bookmaker. odds_list = liste des cotes sur toutes les issues d'un même marché."""
    raw = [1 / o for o in odds_list if o and o > 0]
    if not raw:
        return []
    total = sum(raw)
    return [p / total for p in raw]


def get_sharp_fair_probs(bookies_quotes, has_draw=False):
    """Calcule fair probs en agrégeant les sharp books (moyenne des fair probs après devigging par bookie)."""
    sharp_quotes = [b for b in bookies_quotes if b.get("bookmaker_name") in SHARP_BOOKIES]
    if not sharp_quotes:
        return None

    # Pour chaque sharp book, devig ses propres cotes pour obtenir ses fair probs
    fair_p1, fair_pdraw, fair_p2 = [], [], []
    for b in sharp_quotes:
        p1 = fnum(b.get("player_1") or b.get("home"))
        p2 = fnum(b.get("player_2") or b.get("away"))
        pd = fnum(b.get("draw")) if has_draw else None

        odds = [p1, p2]
        if has_draw and pd:
            odds = [p1, pd, p2]
        odds = [o for o in odds if o]
        if len(odds) < 2:
            continue

        probs = devig_multiplicative(odds)
        if has_draw and pd and len(probs) == 3:
            fair_p1.append(probs[0])
            fair_pdraw.append(probs[1])
            fair_p2.append(probs[2])
        elif len(probs) == 2:
            fair_p1.append(probs[0])
            fair_p2.append(probs[1])

    if not fair_p1:
        return None

    avg_p1 = sum(fair_p1) / len(fair_p1)
    avg_p2 = sum(fair_p2) / len(fair_p2)
    avg_pd = sum(fair_pdraw) / len(fair_pdraw) if fair_pdraw else None
    return {"p1": avg_p1, "p2": avg_p2, "pdraw": avg_pd, "n_sharps": len(sharp_quotes)}


def find_value_bets(csv_path, soft_book_filter="Winamax", min_edge=0.03):
    if not os.path.exists(csv_path):
        print(f"❌ {csv_path} introuvable"); return []

    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Detect le marché présent dans le CSV (match_winner / 1x2 / etc.)
    market_cols = [c for c in rows[0].keys() if c.endswith("_market")]
    print(f"📂 {csv_path} : {len(rows)} matchs, marchés détectés : {market_cols}")

    values = []
    for r in rows:
        for mkt_col in market_cols:
            quotes = parse_market(r.get(mkt_col, ""))
            if not quotes:
                continue

            has_draw = any("draw" in q for q in quotes if isinstance(q, dict))
            fair = get_sharp_fair_probs(quotes, has_draw=has_draw)
            if not fair:
                continue

            # Cherche le soft book (Winamax par défaut)
            soft_quote = next(
                (q for q in quotes if soft_book_filter.lower() in q.get("bookmaker_name", "").lower()),
                None,
            )
            if not soft_quote:
                continue

            # Compare cote par cote
            checks = [
                ("home", soft_quote.get("player_1") or soft_quote.get("home"), fair["p1"], r["home_team"]),
                ("away", soft_quote.get("player_2") or soft_quote.get("away"), fair["p2"], r["away_team"]),
            ]
            if has_draw and fair.get("pdraw"):
                checks.insert(1, ("draw", soft_quote.get("draw"), fair["pdraw"], "Match nul"))

            for side, soft_cote_raw, fair_p, sel_label in checks:
                soft_cote = fnum(soft_cote_raw)
                if not soft_cote or not fair_p:
                    continue
                edge = fair_p * soft_cote - 1
                if edge >= min_edge:
                    values.append({
                        "match": f"{r['home_team']} vs {r['away_team']}",
                        "league": r.get("league_name", ""),
                        "match_date": r.get("match_date", ""),
                        "market": mkt_col.replace("_market", ""),
                        "side": side,
                        "selection": sel_label,
                        "soft_cote": soft_cote,
                        "fair_prob": fair_p,
                        "fair_cote": 1 / fair_p,
                        "edge": edge,
                        "n_sharps": fair["n_sharps"],
                        "kelly_quarter": kelly_quarter(fair_p, soft_cote),
                    })

    return values


def kelly_quarter(p, c, cap=0.05):
    b = c - 1
    if b <= 0:
        return 0.0
    f = (p * b - (1 - p)) / b
    return max(0.0, min(f * 0.25, cap))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV OddsHarvester (ex. /tmp/oh-tennis.csv)")
    ap.add_argument("--soft", default="Winamax", help="Bookmaker soft à analyser (default: Winamax)")
    ap.add_argument("--min-edge", type=float, default=0.03, help="Edge minimum (default: 0.03 = 3%%)")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    values = find_value_bets(args.csv, soft_book_filter=args.soft, min_edge=args.min_edge)
    if not values:
        print("\n❌ Aucun value bet détecté.")
        print("   Possibles raisons :")
        print(f"   - {args.soft} absent du CSV (peu de matchs FR ?)")
        print(f"   - Aucun sharp book (Pinnacle/Stake/Roobet) sur les matchs où {args.soft} est présent")
        print(f"   - Edges < {args.min_edge*100:.0f}% — relance avec --min-edge 0.01 pour voir tous les écarts")
        return

    values.sort(key=lambda v: -v["edge"])
    print(f"\n=== 🎯 {len(values)} VALUE BETS détectés ({args.soft} vs sharps) ===\n")
    print(f"{'Edge':>5} {'Cote':>5} {'Fair':>5} {'¼K':>5}  Match — Pick (Marché)")
    print("-" * 100)
    for v in values[:args.top]:
        m = v["match"][:40]
        print(f"{v['edge']*100:>+4.1f}% {v['soft_cote']:>5.2f} {v['fair_cote']:>5.2f} {v['kelly_quarter']*100:>4.1f}%  "
              f"{m} — {v['selection'][:25]} ({v['market']}) [{v['n_sharps']} sharps]")
        print(f"      {v['league'][:50]}  ·  {v['match_date'][:16]}")
        print()


if __name__ == "__main__":
    main()
