#!/usr/bin/env python3
"""
Sofascore API scraper rapide — parallèle 15 threads.
NBA + NHL + MLB sur saison 2024-2025.

Output : /Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore/{sport}.csv
"""

import csv
import json
import os
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

OUT_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore"
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
        return json.loads(r.read())


def frac_to_dec(s):
    if not s or "/" not in str(s):
        return None
    try:
        n, d = str(s).split("/")
        return round((int(n) + int(d)) / int(d), 2)
    except (ValueError, ZeroDivisionError):
        return None


def daterange(start, end):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def list_events(sport, day, league_filter):
    url = f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{day.isoformat()}"
    try:
        data = fetch(url)
    except Exception:
        return []
    out = []
    for e in data.get("events", []):
        if league_filter and e.get("tournament", {}).get("name", "") not in league_filter:
            continue
        if e.get("status", {}).get("description") != "Ended":
            continue
        hs = e.get("homeScore", {}).get("current")
        as_ = e.get("awayScore", {}).get("current")
        if hs is None or as_ is None:
            continue
        out.append({
            "id": e["id"],
            "date": day.isoformat(),
            "league": e.get("tournament", {}).get("name", "?"),
            "home": e["homeTeam"]["name"],
            "away": e["awayTeam"]["name"],
            "hs": hs, "as": as_,
        })
    return out


def fetch_odds(event):
    eid = event["id"]
    try:
        odds = fetch(f"https://api.sofascore.com/api/v1/event/{eid}/odds/1/all")
    except Exception:
        return None
    ft = next((m for m in odds.get("markets", []) if m.get("marketName") == "Full time"), None)
    if not ft:
        return None
    choices = ft.get("choices", [])
    c1 = next((c for c in choices if c.get("name") == "1"), None)
    c2 = next((c for c in choices if c.get("name") == "2"), None)
    if not c1 or not c2:
        return None
    oh = frac_to_dec(c1.get("fractionalValue"))
    oa = frac_to_dec(c2.get("fractionalValue"))
    if not oh or not oa:
        return None
    event["home_odds"] = oh
    event["away_odds"] = oa
    event["home_won"] = event["hs"] > event["as"]
    return event


def scrape_sport(sport, league_filter, start_d, end_d, out_path, max_workers=15):
    print(f"[{sport}] Liste events {start_d} → {end_d} (filter={league_filter})…")

    all_events = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(list_events, sport, d, league_filter): d for d in daterange(start_d, end_d)}
        for f in as_completed(futures):
            evs = f.result()
            all_events.extend(evs)
    print(f"[{sport}] {len(all_events)} events à traiter")

    rows = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fetch_odds, e) for e in all_events]
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            if r:
                rows.append(r)
            if i % 200 == 0:
                print(f"[{sport}] {i}/{len(all_events)} traités, {len(rows)} avec cotes")

    # Sauvegarde
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "league", "home", "away", "hs", "as", "home_odds", "away_odds", "home_won"])
        for r in sorted(rows, key=lambda x: x["date"]):
            w.writerow([r["date"], r["league"], r["home"], r["away"],
                        r["hs"], r["as"], r["home_odds"], r["away_odds"],
                        1 if r["home_won"] else 0])
    print(f"[{sport}] Sauvé {len(rows)} matchs avec cotes → {out_path}")


def main():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    targets = [
        ("basketball", {"NBA"}, date(2024, 10, 22), date(2025, 4, 13),
         os.path.join(OUT_DIR, "nba.csv")),
        ("ice-hockey", {"NHL"}, date(2024, 10, 8), date(2025, 4, 17),
         os.path.join(OUT_DIR, "nhl.csv")),
        ("baseball", {"MLB"}, date(2024, 3, 28), date(2024, 9, 30),
         os.path.join(OUT_DIR, "mlb.csv")),
    ]

    import time
    t0 = time.time()
    for sport, leagues, sd, ed, outp in targets:
        scrape_sport(sport, leagues, sd, ed, outp)
    print(f"\nTOTAL TIME: {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
