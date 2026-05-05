"""Extract picks d'events scrapés (toutes sélections magic-able).

Pour chaque event, sort toutes les sélections {market, selection, cote, wr, ev}
qui ont une magic cote correspondante.

Usage:
    from picks.extractor import extract_event_picks, rank_picks
    picks = extract_event_picks(event, magic)  # toutes sélections de cet event
    ranked = rank_picks(events, magic, sort="wr", min_wr=0.55, ...)
"""
import os, json, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.magic import Magic

# Mapping (cote_field, market_key magic, label, market display)
# Keys exactes dans magic_extended : 1x2, btts_y, btts_n, over_1_5, under_1_5, over_2_5, under_2_5
MARKETS = [
    ("odds_1",         "1x2",       lambda ev: ev["home"],          "1x2"),
    ("odds_2",         "1x2",       lambda ev: ev["away"],          "1x2"),
    ("odds_x",         "1x2",       lambda ev: "Match nul",         "1x2"),
    ("odds_btts_y",    "btts_y",    lambda ev: "BTTS Oui",          "btts"),
    ("odds_btts_n",    "btts_n",    lambda ev: "BTTS Non",          "btts"),
    ("odds_over_1_5",  "over_1_5",  lambda ev: "Over 1.5 buts",     "over_1_5"),
    ("odds_under_1_5", "under_1_5", lambda ev: "Under 1.5 buts",    "over_1_5"),
    ("odds_over_2_5",  "over_2_5",  lambda ev: "Over 2.5 buts",     "over_2_5"),
    ("odds_under_2_5", "under_2_5", lambda ev: "Under 2.5 buts",    "over_2_5"),
]


def extract_event_picks(ev, magic: Magic):
    """Retourne liste de picks (dict) pour un event scrapé."""
    out = []
    sport = ev["sport"]
    league = ev.get("league", "")
    cat = ev.get("category", "")
    match = f"{ev['home']} vs {ev['away']}"
    for cote_field, market_key, sel_fn, market_display in MARKETS:
        c = ev.get(cote_field)
        if not c:
            continue
        cote = float(c)
        # Matching strict round_cote ±0.01 (équivalent au backtest_engine.extract_picks)
        cm, wr = magic.lookup_strict(sport, league, market_key, cote, category=cat)
        if wr is None:
            continue
        out.append({
            "match": match,
            "sport": sport,
            "league": league,
            "market": market_display,
            "selection": sel_fn(ev),
            "cote": cote,
            "magic_cote": cm,
            "wr": wr,
            "ev": wr * cote,
            "start_time": ev.get("start_time"),
        })
    return out


def rank_picks(events, magic, sort="wr", min_wr=0.50, min_ev=1.0,
               cote_min=1.0, cote_max=999, sports=None, markets=None, top=None):
    """Extrait + filtre + trie picks de tous events."""
    from picks.league_filter import is_league_ok
    all_picks = []
    for ev in events:
        if sports and ev["sport"] not in sports:
            continue
        # Filtre centralisé Winamax FR (whitelist + pays + reject)
        if not is_league_ok(ev["sport"], ev.get("league", ""), category=ev.get("category", "")):
            continue
        all_picks.extend(extract_event_picks(ev, magic))

    filtered = [p for p in all_picks
                if p["wr"] >= min_wr
                and p["ev"] >= min_ev
                and cote_min <= p["cote"] <= cote_max]
    if markets:
        filtered = [p for p in filtered if p["market"] in markets]

    if sort == "wr":
        filtered.sort(key=lambda p: -p["wr"])
    elif sort == "ev":
        filtered.sort(key=lambda p: -p["ev"])
    elif sort == "cote":
        filtered.sort(key=lambda p: p["cote"])
    elif sort == "time":
        filtered.sort(key=lambda p: p.get("start_time") or 0)

    if top:
        filtered = filtered[:top]
    return {
        "n_total": len(all_picks),
        "n_filtered": len(filtered),
        "picks": filtered,
    }


def load_picks_file(path):
    with open(path) as f:
        return json.load(f)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--picks", default="datasets/picks_today.json")
    ap.add_argument("--sort", default="wr")
    ap.add_argument("--min-wr", type=float, default=0.55)
    ap.add_argument("--cote-min", type=float, default=1.4)
    ap.add_argument("--cote-max", type=float, default=2.5)
    ap.add_argument("--sport")
    ap.add_argument("--market")
    ap.add_argument("--top", type=int, default=20)
    args = ap.parse_args()

    data = load_picks_file(args.picks)
    magic = Magic()
    sports_f = args.sport.split(",") if args.sport else None
    markets_f = args.market.split(",") if args.market else None
    r = rank_picks(data["events"], magic, args.sort, args.min_wr,
                   1.0, args.cote_min, args.cote_max, sports_f, markets_f, args.top)
    print(f"\nDay: {data.get('day')} | total picks: {r['n_total']} | filtered: {r['n_filtered']}\n")
    print(f"{'Match':<55s} {'Sport':<8s} {'Mkt':<8s} {'Sél':<22s} {'Cote':>5s} {'WR':>5s} {'EV':>5s}")
    print("-" * 115)
    for p in r["picks"]:
        print(f"{p['match'][:54]:<55s} {p['sport'][:8]:<8s} {p['market'][:8]:<8s} "
              f"{p['selection'][:21]:<22s} {p['cote']:>5.2f} {p['wr']*100:>4.0f}% {p['ev']:>5.2f}")
