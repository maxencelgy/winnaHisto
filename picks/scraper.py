#!/usr/bin/env python3
"""Scrape SÉQUENTIEL events + cotes Sofascore du jour pour tous sports.

Markets scrapés par event :
  - 1x2 (Full time)
  - BTTS (Both teams to score)
  - Match goals (Over/Under) seuils 0.5 / 1.5 / 2.5 / 3.5

Usage:
  python3 picks/scraper.py [--day YYYY-MM-DD] [--sports foot,basket,...] [--out path]
"""
import sys, os, json, argparse, time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sofascore_massive import fetch as ss_fetch

from picks.league_filter import is_league_ok

def league_ok(sport, lg, category=""):
    return is_league_ok(sport, lg, category=category)


def frac_to_dec(s):
    if not s or "/" not in str(s):
        return None
    try:
        n, d = str(s).split("/")
        return round((int(n) + int(d)) / int(d), 2)
    except (ValueError, ZeroDivisionError):
        return None


def list_events(sport, day_str):
    """Liste events upcoming d'un sport pour un jour. Filtré whitelist."""
    data = ss_fetch(f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{day_str}")
    if not data:
        return []
    out = []
    for e in data.get("events", []):
        status = e.get("status", {}).get("type", "")
        if status not in ("notstarted", "inprogress"):
            continue
        league = e.get("tournament", {}).get("name", "")
        category = e.get("tournament", {}).get("category", {}).get("name", "")
        if not league_ok(sport, league, category=category):
            continue
        out.append({
            "id": e["id"],
            "sport": sport,
            "league": league,
            "category": category,
            "home": e["homeTeam"]["name"],
            "away": e["awayTeam"]["name"],
            "start_time": e.get("startTimestamp"),
        })
    return out


def fetch_odds(event):
    """Récupère cotes 1x2 / BTTS / Over-Under (0.5/1.5/2.5/3.5) pour un event."""
    odds = ss_fetch(f"https://api.sofascore.com/api/v1/event/{event['id']}/odds/1/all")
    if not odds:
        return None
    markets = odds.get("markets", [])
    out = dict(event)

    # Full time 1x2
    ft = next((m for m in markets if m.get("marketName") == "Full time"), None)
    if ft:
        for c in ft.get("choices", []):
            d = frac_to_dec(c.get("fractionalValue"))
            if not d:
                continue
            n = c.get("name")
            if n == "1":
                out["odds_1"] = d
            elif n == "2":
                out["odds_2"] = d
            elif n == "X":
                out["odds_x"] = d

    # BTTS
    btts = next((m for m in markets if m.get("marketName") == "Both teams to score"), None)
    if btts:
        for c in btts.get("choices", []):
            d = frac_to_dec(c.get("fractionalValue"))
            if not d:
                continue
            n = c.get("name")
            if n == "Yes":
                out["odds_btts_y"] = d
            elif n == "No":
                out["odds_btts_n"] = d

    # Match goals — 0.5 / 1.5 / 2.5 / 3.5
    for mg in markets:
        if mg.get("marketName") != "Match goals":
            continue
        thr = (mg.get("choiceGroup") or "").strip()
        if thr not in ("0.5", "1.5", "2.5", "3.5"):
            continue
        suffix = thr.replace(".", "_")
        for c in mg.get("choices", []):
            d = frac_to_dec(c.get("fractionalValue"))
            if not d:
                continue
            n = c.get("name")
            if n == "Over":
                out[f"odds_over_{suffix}"] = d
            elif n == "Under":
                out[f"odds_under_{suffix}"] = d

    return out


def scrape(day_str, sports, log=print):
    """Scrape séquentiel tous sports demandés."""
    log(f"[scrape] day={day_str} sports={sports}")
    all_events = []
    for sport in sports:
        try:
            evs = list_events(sport, day_str)
            log(f"  {sport}: {len(evs)} events")
            all_events.extend(evs)
        except Exception as e:
            log(f"  {sport}: ERROR {type(e).__name__}: {e}")

    log(f"[scrape] Fetching odds séquentiellement pour {len(all_events)} events…")
    enriched = []
    for i, ev in enumerate(all_events):
        if i % 25 == 0:
            log(f"  {i}/{len(all_events)}")
        try:
            r = fetch_odds(ev)
            if r and (r.get("odds_1") or r.get("odds_2")):
                enriched.append(r)
        except Exception as e:
            log(f"  fetch_odds err on {ev.get('id')}: {e}")
    log(f"[scrape] {len(enriched)} events avec cotes")
    return enriched


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=date.today().isoformat())
    ap.add_argument("--sports", default="football,basketball,ice-hockey,baseball")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    sports = [s.strip() for s in args.sports.split(",") if s.strip()]
    out_path = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "datasets", "picks_today.json"
    )
    enriched = scrape(args.day, sports)
    payload = {
        "day": args.day,
        "scraped_at": time.time(),
        "n_events": len(enriched),
        "events": enriched,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    print(f"[scrape] Saved {out_path}")


if __name__ == "__main__":
    main()
