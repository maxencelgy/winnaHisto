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

# Session curl_cffi initialisée via Camoufox (bootstrap cookies + fingerprint Firefox)
_session = None
_session_lock = threading.Lock()


def _bootstrap_session():
    """Lance Camoufox une fois pour récupérer cookies + UA, puis crée une session curl_cffi
    qui peut faire des centaines de requêtes/sec en imitant Firefox."""
    from camoufox.sync_api import Camoufox
    print("  [auth] Bootstrap Camoufox (cookies sofascore)...")
    with Camoufox(headless=True, geoip=True) as browser:
        ctx = browser.contexts[0] if browser.contexts else browser.new_context()
        page = ctx.new_page()
        page.goto("https://www.sofascore.com", wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        cookies = ctx.cookies()
        ua = page.evaluate("navigator.userAgent")
    s = cf_requests.Session()
    for c in cookies:
        if 'sofascore' in c.get('domain', ''):
            s.cookies.update({c['name']: c['value']})
    s.headers.update({"User-Agent": ua})
    return s


def _get_session():
    global _session
    with _session_lock:
        if _session is None:
            _session = _bootstrap_session()
        return _session


def _reset_session():
    global _session
    with _session_lock:
        _session = None


def fetch(url, retries=2):
    s = _get_session()
    for i in range(retries + 1):
        try:
            r = s.get(url, impersonate="firefox135", timeout=15)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 403:
                # Cookies probablement expirés → re-bootstrap au prochain appel
                _reset_session()
                s = _get_session()
        except Exception:
            pass
        if i < retries:
            time.sleep(0.5)
    return None


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


def list_events(sport, day):
    """Liste tous les events ENDED d'un sport pour un jour donné, toutes leagues."""
    data = fetch(f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{day.isoformat()}")
    if not data:
        return []
    out = []
    for e in data.get("events", []):
        if e.get("status", {}).get("description") != "Ended":
            continue
        hs = e.get("homeScore", {}).get("current")
        as_ = e.get("awayScore", {}).get("current")
        if hs is None or as_ is None:
            continue
        out.append({
            "id": e["id"],
            "date": day.isoformat(),
            "sport": sport,
            "league": e.get("tournament", {}).get("name", "?"),
            "category": e.get("tournament", {}).get("category", {}).get("name", "?"),
            "home": e["homeTeam"]["name"],
            "away": e["awayTeam"]["name"],
            "hs": hs, "as": as_,
        })
    return out


def fetch_event_odds(event):
    """Récupère plusieurs marchés pour un event."""
    eid = event["id"]
    odds = fetch(f"https://api.sofascore.com/api/v1/event/{eid}/odds/1/all")
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


def scrape_sport(sport, start_d, end_d, max_workers=30):
    print(f"\n[{sport}] === {start_d} → {end_d} ===")
    t0 = time.time()

    # Phase 1 : liste tous les events
    all_events = []
    with ThreadPoolExecutor(max_workers=15) as pool:
        futures = {pool.submit(list_events, sport, d): d for d in daterange(start_d, end_d)}
        done = 0
        for f in as_completed(futures):
            evs = f.result() or []
            all_events.extend(evs)
            done += 1
            if done % 30 == 0:
                print(f"  [{sport}] events listés : {done}/{len(futures)} jours, {len(all_events)} events")
    print(f"[{sport}] Total events ENDED listés : {len(all_events)} en {time.time()-t0:.0f}s")

    # Phase 2 : odds (plus lourd)
    rows = []
    t1 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(fetch_event_odds, e) for e in all_events]
        for i, f in enumerate(as_completed(futures), 1):
            r = f.result()
            if r:
                rows.append(r)
            if i % 1000 == 0:
                rate = i / max(time.time() - t1, 1)
                eta = (len(all_events) - i) / max(rate, 0.1)
                print(f"  [{sport}] odds : {i}/{len(all_events)} ({rate:.0f}/s, ETA {eta:.0f}s), {len(rows)} ok")

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
