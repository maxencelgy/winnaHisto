#!/usr/bin/env python3
"""
Sofascore scraper massif — toutes leagues, multi-marchés, saison 2024-2025.

Sports : foot, basket, hockey, baseball (toutes leagues mondiales)
Marchés : Full time (1x2), Game total (over/under), Both Teams To Score

Output : /Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_massive/
"""

import csv
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from pathlib import Path

from curl_cffi import requests as cf_requests

OUT_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_massive"

# Whitelist leagues dispos sur Winamax / Betclic / Unibet FR.
# On filtre au listing pour éviter de fetch les odds de leagues inutiles.
WINAMAX_LEAGUES = {
    "football": [
        "premier league", "laliga", "la liga", "serie a", "bundesliga", "ligue 1",
        "championship", "laliga 2", "la liga 2", "serie b", "bundesliga 2", "ligue 2",
        "champions league", "europa league", "conference league", "uefa",
        "eredivisie", "liga portugal", "primeira liga", "pro league", "süper lig",
        "premier liga", "trendyol süper", "russian premier",
        "mls", "liga mx", "brasileirão", "brasileirao", "primera división",
        "primera a", "primera b", "argentina", "ecuador serie a",
        "coupe de france", "fa cup", "copa del rey", "coppa italia", "dfb-pokal",
        "world cup", "euro 2", "copa america", "africa cup",
        "saudi", "qatar stars", "j1 league", "j2 league", "k league 1",
        "fifa intercontinental",
    ],
    "basketball": [
        "nba", "wnba", "euroleague", "eurocup", "betclic élite", "pro a",
        "acb", "liga endesa", "lega basket", "serie a", "bbl", "champions league",
    ],
    "ice-hockey": [
        "nhl", "khl", "shl", "liiga", "ligue magnus", "del", "national league",
        "extraliga", "elite league", "swiss",
    ],
    "baseball": ["mlb"],
    "tennis": [
        "atp", "wta", "grand slam", "masters",
        "australian open", "roland garros", "wimbledon", "us open",
        "miami", "indian wells", "monte carlo", "madrid", "rome", "cincinnati",
        "shanghai", "paris masters",
    ],
}
REJECT_PATTERNS = ["doubles", "qualifying", "u23", "u21", "u19", "u18", "u17", "reserve",
                   "youth", "women, qualif", "men, qualif", "challenger round",
                   "regionalliga", "national league,", "serie c", "série c",
                   "i-league", "k league 2", "league 1, championship",
                   "championship round", "knockout stage qualifying",
                   "primera b nacional", "next pro", "utr ", "ptt ", "exhibition"]


def is_league_allowed(sport, league):
    """Renvoie True si la league est dispo sur Winamax/Betclic/Unibet FR."""
    if not league:
        return False
    lg_lower = league.lower()
    for rej in REJECT_PATTERNS:
        if rej in lg_lower:
            return False
    patterns = WINAMAX_LEAGUES.get(sport, [])
    for pat in patterns:
        if pat in lg_lower:
            return True
    return False

# Camoufox browser persistant + page pour batch JS fetch
# (bypass Cloudflare en utilisant fetch() native dans le contexte browser)
_browser = None
_page = None
_browser_lock = threading.Lock()


_browser_cm = None
_request_count = 0
_BROWSER_ROTATION_THRESHOLD = 5000  # rotate browser tous les 5000 fetches pour éviter memory leak


def _ensure_browser(force_rotate=False):
    global _browser, _page, _browser_cm, _request_count
    with _browser_lock:
        if force_rotate or _request_count >= _BROWSER_ROTATION_THRESHOLD:
            if _browser_cm is not None:
                try: _browser_cm.__exit__(None, None, None)
                except Exception: pass
                _browser, _page, _browser_cm = None, None, None
                _request_count = 0
                print("  [auth] Browser rotation (libère mémoire Camoufox)")
        if _browser is None:
            from camoufox.sync_api import Camoufox
            print("  [auth] Lancement Camoufox + bootstrap sofascore.com...")
            _browser_cm = Camoufox(headless=True, geoip=True)
            _browser = _browser_cm.__enter__()
            _page = _browser.new_page()
            _page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            print("  [auth] Browser ready, fetches via JS dans contexte browser")
        return _page


def fetch(url, retries=2):
    """Single URL fetch via browser JS fetch (compat ancienne API)."""
    results = batch_fetch([url], retries=retries)
    return results.get(url)


def batch_fetch(urls, retries=2, batch_size=50):
    """Fetch parallèle via JS fetch dans Camoufox (50 URLs en // = ~100 req/s).
    Retourne dict {url: parsed_json | None}."""
    global _request_count
    page = _ensure_browser()
    out = {}
    with _browser_lock:
        _request_count += len(urls)
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i+batch_size]
            for attempt in range(retries + 1):
                try:
                    results = page.evaluate("""
                        async (urls) => {
                            return await Promise.all(urls.map(async u => {
                                try {
                                    const r = await fetch(u);
                                    if (r.status !== 200) return {url: u, ok: false, status: r.status};
                                    return {url: u, ok: true, body: await r.text()};
                                } catch (e) {
                                    return {url: u, ok: false, status: 0};
                                }
                            }));
                        }
                    """, batch)
                    failed_403 = 0
                    for r in results:
                        if r['ok']:
                            try: out[r['url']] = json.loads(r['body'])
                            except: out[r['url']] = None
                        else:
                            out[r['url']] = None
                            if r.get('status') == 403:
                                failed_403 += 1
                    # Si beaucoup de 403, on retry une fois après pause
                    if failed_403 > batch_size * 0.5 and attempt < retries:
                        print(f"  [warn] {failed_403}/{batch_size} 403, retry après pause 5s...")
                        time.sleep(5)
                        continue
                    break
                except Exception as e:
                    if attempt < retries:
                        time.sleep(1)
                        continue
                    for u in batch:
                        out[u] = None
    return out


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


def parse_listing_data(data, sport, day_iso, whitelist_only=True):
    """Parse une réponse listing en events ENDED."""
    if not data: return []
    out = []
    for e in data.get("events", []):
        if e.get("status", {}).get("description") != "Ended":
            continue
        hs = e.get("homeScore", {}).get("current")
        as_ = e.get("awayScore", {}).get("current")
        if hs is None or as_ is None:
            continue
        league = e.get("tournament", {}).get("name", "?")
        if whitelist_only and not is_league_allowed(sport, league):
            continue
        out.append({
            "id": e["id"], "date": day_iso, "sport": sport,
            "league": league,
            "category": e.get("tournament", {}).get("category", {}).get("name", "?"),
            "home": e["homeTeam"]["name"], "away": e["awayTeam"]["name"],
            "hs": hs, "as": as_,
        })
    return out


def list_events(sport, day, whitelist_only=True):
    """Liste les events ENDED d'un sport pour un jour donné (single fetch). Compat ancienne API."""
    data = fetch(f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{day.isoformat()}")
    return parse_listing_data(data, sport, day.isoformat(), whitelist_only)


def parse_odds_data(odds, event):
    """Parse une réponse odds en row enrichi."""
    if not odds:
        return None
    markets = odds.get("markets", [])
    out = dict(event)
    out["home_won"] = event["hs"] > event["as"]
    out["total_score"] = event["hs"] + event["as"]
    out["btts"] = event["hs"] > 0 and event["as"] > 0

    # Full time (1x2 / home-away)
    ft = next((m for m in markets if m.get("marketName") == "Full time"), None)
    if ft:
        choices = ft.get("choices", [])
        c1 = next((c for c in choices if c.get("name") == "1"), None)
        c2 = next((c for c in choices if c.get("name") == "2"), None)
        cx = next((c for c in choices if c.get("name") == "X"), None)
        if c1: out["odds_1"] = frac_to_dec(c1.get("fractionalValue"))
        if c2: out["odds_2"] = frac_to_dec(c2.get("fractionalValue"))
        if cx: out["odds_x"] = frac_to_dec(cx.get("fractionalValue"))

    # Match goals (over/under multi-threshold) — Sofascore actuel utilise choiceGroup
    for mg in markets:
        if mg.get("marketName") != "Match goals":
            continue
        thr = (mg.get("choiceGroup") or "").strip()
        if thr not in ("0.5", "1.5", "2.5", "3.5"):
            continue
        suffix = thr.replace(".", "_")
        choices = mg.get("choices", [])
        co = next((c for c in choices if c.get("name") == "Over"), None)
        cu = next((c for c in choices if c.get("name") == "Under"), None)
        if co: out[f"odds_over_{suffix}"] = frac_to_dec(co.get("fractionalValue"))
        if cu: out[f"odds_under_{suffix}"] = frac_to_dec(cu.get("fractionalValue"))

    # BTTS
    btts_m = next((m for m in markets if m.get("marketName") == "Both teams to score"), None)
    if btts_m:
        choices = btts_m.get("choices", [])
        cy = next((c for c in choices if c.get("name") == "Yes"), None)
        cn = next((c for c in choices if c.get("name") == "No"), None)
        if cy: out["odds_btts_y"] = frac_to_dec(cy.get("fractionalValue"))
        if cn: out["odds_btts_n"] = frac_to_dec(cn.get("fractionalValue"))

    if not (out.get("odds_1") or out.get("odds_2") or out.get("odds_over_2_5")):
        return None
    return out


def fetch_event_odds(event):
    """Compat : fetch single event odds."""
    eid = event["id"]
    odds = fetch(f"https://api.sofascore.com/api/v1/event/{eid}/odds/1/all")
    return parse_odds_data(odds, event)


def scrape_sport(sport, start_d, end_d, max_workers=None, batch_size=50):
    """Scrape via Camoufox JS-fetch parallèle. max_workers ignoré (parallélisme côté browser)."""
    print(f"\n[{sport}] === {start_d} → {end_d} ===")
    t0 = time.time()

    # Phase 1 : listing par batches de 50 jours en parallèle browser
    all_days = list(daterange(start_d, end_d))
    all_events = []
    listing_urls = [f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{d.isoformat()}"
                    for d in all_days]
    listing_results = {}
    for i in range(0, len(listing_urls), batch_size):
        batch_urls = listing_urls[i:i+batch_size]
        listing_results.update(batch_fetch(batch_urls, batch_size=batch_size))
        # Parse au fur et à mesure
        for u in batch_urls:
            day_iso = u.rsplit("/", 1)[-1]
            data = listing_results.get(u)
            evs = parse_listing_data(data, sport, day_iso, whitelist_only=True)
            all_events.extend(evs)
        done = min(i + batch_size, len(listing_urls))
        if done % 200 == 0 or done >= len(listing_urls):
            print(f"  [{sport}] events listés : {done}/{len(listing_urls)} jours, {len(all_events)} events")
    print(f"[{sport}] Total events ENDED listés : {len(all_events)} en {time.time()-t0:.0f}s")

    if not all_events:
        print(f"[{sport}] ⚠️ aucun event listé, abort")
        return

    # Phase 2 : odds par batches de 50 events en parallèle browser
    rows = []
    t1 = time.time()
    odds_urls = [f"https://api.sofascore.com/api/v1/event/{e['id']}/odds/1/all" for e in all_events]
    event_by_url = {odds_urls[i]: all_events[i] for i in range(len(all_events))}
    for i in range(0, len(odds_urls), batch_size):
        batch_urls = odds_urls[i:i+batch_size]
        results = batch_fetch(batch_urls, batch_size=batch_size)
        for u in batch_urls:
            r = parse_odds_data(results.get(u), event_by_url[u])
            if r: rows.append(r)
        done = min(i + batch_size, len(odds_urls))
        if done % 500 == 0 or done >= len(odds_urls):
            rate = done / max(time.time() - t1, 1)
            eta = (len(odds_urls) - done) / max(rate, 0.1)
            print(f"  [{sport}] odds : {done}/{len(odds_urls)} ({rate:.0f}/s, ETA {eta:.0f}s), {len(rows)} ok")

    # SAFETY : refuse d'écraser le CSV existant si on a < 100 matchs (probable ban/challenge)
    out_path = os.path.join(OUT_DIR, f"{sport}.csv")
    if len(rows) < 100 and os.path.exists(out_path):
        existing_lines = sum(1 for _ in open(out_path)) - 1
        if existing_lines > len(rows):
            print(f"[{sport}] ⚠️ ABORT WRITE : seulement {len(rows)} matchs scrapés, "
                  f"existing CSV a {existing_lines} matchs → préservé. Vérifie ban/challenge Sofascore.")
            return

    # Écriture vers fichier temp puis rename atomique (pas de wipe partiel)
    fields = ["date", "sport", "league", "category", "home", "away", "hs", "as",
              "home_won", "total_score", "btts",
              "odds_1", "odds_x", "odds_2",
              "odds_over_0_5", "odds_under_0_5",
              "odds_over_1_5", "odds_under_1_5",
              "odds_over_2_5", "odds_under_2_5",
              "odds_over_3_5", "odds_under_3_5",
              "odds_btts_y", "odds_btts_n"]
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in sorted(rows, key=lambda x: x["date"]):
            w.writerow({k: r.get(k, "") for k in fields})
    os.replace(tmp_path, out_path)
    print(f"[{sport}] Sauvé {len(rows)} matchs en {time.time()-t0:.0f}s → {out_path}")


def main():
    Path(OUT_DIR).mkdir(parents=True, exist_ok=True)
    targets = [
        ("basketball", date(2024, 10, 1), date(2025, 5, 1)),
        ("ice-hockey", date(2024, 9, 1), date(2025, 5, 1)),
        ("baseball", date(2024, 3, 1), date(2024, 10, 1)),
    ]
    import sys
    sys.stdout.reconfigure(line_buffering=True)
    t0 = time.time()
    for sport, sd, ed in targets:
        scrape_sport(sport, sd, ed)
    print(f"\n========== TOTAL TIME: {(time.time()-t0)/60:.1f} min ==========")


if __name__ == "__main__":
    main()
