#!/usr/bin/env python3
"""
Pinnacle scraper — pré-match odds via API publique Arcadia.

Utilise le pattern Camoufox bootstrap (comme sofascore_massive.py) pour bypasser Cloudflare,
puis fetch l'API guest.api.arcadia.pinnacle.com via JS dans le contexte browser.

Sports : football (soccer 29), basketball (4), ice-hockey (19), baseball (3), tennis (33).
Marchés : 1x2 (moneyline 3-way), Home/Away (moneyline 2-way), Total (over/under), Spread (handicap).
         BTTS si exposé.

Output : datasets/pinnacle_odds.json
        {
          "captured_at": "2026-05-03T19:00:00Z",
          "events": [
            {
              "pinnacle_id": 1234,
              "sport": "football",
              "league": "Premier League",
              "starts": "2026-05-04T14:00:00Z",
              "home": "Arsenal",
              "away": "Chelsea",
              "captured_at": "2026-05-03T19:00:00Z",
              "moneyline": {"home": 1.95, "draw": 3.50, "away": 4.20},
              "totals": [{"line": 2.5, "over": 1.85, "under": 2.05}, ...],
              "spreads": [{"line": -0.5, "home": 1.90, "away": 2.00}, ...],
              "max_stake_moneyline": 1500.0
            }
          ]
        }

Usage :
    python3 pinnacle_scraper.py                    # tous sports, 24h à venir
    python3 pinnacle_scraper.py --sports football  # foot uniquement
    python3 pinnacle_scraper.py --dry-run          # ne fait pas le scrape, juste discovery
    python3 pinnacle_scraper.py --lookback 24h     # capture aussi matchs passés (debug)
    python3 pinnacle_scraper.py --max-events 50    # limite pour test rapide
"""

import argparse
import json
import os
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

OUT_PATH = "/Users/maxenceleguay/Sites/winnaHisto/datasets/pinnacle_odds.json"

# Pinnacle Arcadia public API (clé exposée publiquement par leur propre site)
PINNACLE_API = "https://guest.api.arcadia.pinnacle.com/0.1"
PINNACLE_API_KEY = "CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R"

# Sport ID mapping (côté Pinnacle)
SPORT_IDS = {
    "football": 29,    # Soccer
    "basketball": 4,
    "ice-hockey": 19,
    "baseball": 3,
    "tennis": 33,
}

# ---- Camoufox singleton (bypass Cloudflare) -------------------------------

_browser = None
_page = None
_browser_lock = threading.Lock()


def _ensure_browser():
    """Lance Camoufox une seule fois et navigue vers pinnacle.com pour valider Cloudflare."""
    global _browser, _page
    with _browser_lock:
        if _browser is None:
            from camoufox.sync_api import Camoufox
            print("  [auth] Lancement Camoufox + bootstrap pinnacle.com...")
            cm = Camoufox(headless=True, geoip=True)
            _browser = cm.__enter__()
            _page = _browser.new_page()
            _page.goto("https://www.pinnacle.com", wait_until="domcontentloaded", timeout=45000)
            time.sleep(3)
            print("  [auth] Browser ready, fetches via JS dans contexte browser")
        return _page


def _js_fetch(urls, retries=2, batch_size=20):
    """Batch fetch via JS dans le contexte browser. Headers x-api-key requis pour Arcadia."""
    page = _ensure_browser()
    out = {}
    with _browser_lock:
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            for attempt in range(retries + 1):
                try:
                    results = page.evaluate(
                        """
                        async ({urls, apiKey}) => {
                            return await Promise.all(urls.map(async u => {
                                try {
                                    const r = await fetch(u, {headers: {'x-api-key': apiKey, 'Accept': 'application/json'}});
                                    if (r.status !== 200) return {url: u, ok: false, status: r.status};
                                    return {url: u, ok: true, body: await r.text()};
                                } catch (e) {
                                    return {url: u, ok: false, status: 0, err: String(e)};
                                }
                            }));
                        }
                        """,
                        {"urls": batch, "apiKey": PINNACLE_API_KEY},
                    )
                    failed = 0
                    for r in results:
                        if r.get("ok"):
                            try:
                                out[r["url"]] = json.loads(r["body"])
                            except Exception:
                                out[r["url"]] = None
                        else:
                            out[r["url"]] = None
                            if r.get("status") in (403, 429, 0):
                                failed += 1
                    if failed > len(batch) * 0.5 and attempt < retries:
                        print(f"  [retry] {failed}/{len(batch)} échecs, pause 5s...")
                        time.sleep(5)
                        continue
                    break
                except Exception as e:
                    print(f"  [error] batch {i}: {e}")
                    time.sleep(2)
                    if attempt >= retries:
                        for u in batch:
                            out.setdefault(u, None)
    return out


# ---- Conversions cotes -----------------------------------------------------

def american_to_decimal(american):
    """Pinnacle Arcadia renvoie souvent les prix en american. Convertit en décimal."""
    if american is None:
        return None
    try:
        a = float(american)
    except (TypeError, ValueError):
        return None
    if a > 0:
        return round(1 + a / 100, 4)
    if a < 0:
        return round(1 + 100 / abs(a), 4)
    return None


def parse_price(price_obj):
    """Tente decimal d'abord, sinon convertit american. Pinnacle expose les deux selon endpoint."""
    if not isinstance(price_obj, dict):
        return None
    if "decimal" in price_obj and price_obj["decimal"]:
        try:
            return round(float(price_obj["decimal"]), 4)
        except (TypeError, ValueError):
            pass
    if "price" in price_obj:
        # Format Arcadia : 'price' = american
        return american_to_decimal(price_obj["price"])
    if "american" in price_obj:
        return american_to_decimal(price_obj["american"])
    return None


# ---- API discovery / parse -------------------------------------------------

def list_matchups(sport_key, lookback_hours=0):
    """Liste les matchups upcoming pour un sport. Retourne liste brute Arcadia."""
    sid = SPORT_IDS[sport_key]
    url = f"{PINNACLE_API}/sports/{sid}/matchups?withSpecials=false&brandId=0"
    data = _js_fetch([url]).get(url)
    if not data:
        return []
    if not isinstance(data, list):
        return []
    now = datetime.now(timezone.utc)
    cutoff_past = now - timedelta(hours=lookback_hours)
    cutoff_future = now + timedelta(days=7)
    out = []
    for m in data:
        if m.get("type") != "matchup":
            continue
        if m.get("isLive"):
            continue
        starts = m.get("startTime")
        if not starts:
            continue
        try:
            start_dt = datetime.fromisoformat(starts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if start_dt < cutoff_past or start_dt > cutoff_future:
            continue
        participants = m.get("participants") or []
        home = next((p["name"] for p in participants if p.get("alignment") == "home"), None)
        away = next((p["name"] for p in participants if p.get("alignment") == "away"), None)
        if not home or not away:
            continue
        league = (m.get("league") or {}).get("name", "?")
        out.append({
            "pinnacle_id": m["id"],
            "sport": sport_key,
            "league": league,
            "starts": starts,
            "home": home,
            "away": away,
        })
    return out


def fetch_markets(matchup_ids):
    """Fetch markets straight pour une liste de matchup IDs. Parallèle via JS."""
    urls = [f"{PINNACLE_API}/matchups/{mid}/markets/related/straight" for mid in matchup_ids]
    raw = _js_fetch(urls, batch_size=20)
    return {url.rsplit("/markets/")[0].rsplit("/", 1)[-1]: data for url, data in raw.items()}


def parse_markets(markets_data):
    """Parse la liste de markets Arcadia pour un matchup. Retourne dict structuré."""
    out = {"moneyline": None, "totals": [], "spreads": [], "max_stake_moneyline": None}
    if not markets_data or not isinstance(markets_data, list):
        return out
    for m in markets_data:
        period = m.get("period")
        if period != 0:  # 0 = full match (pas mi-temps, pas sets)
            continue
        if m.get("status") != "open":
            continue
        mtype = m.get("type")
        prices = m.get("prices") or []
        max_limit = m.get("limits", [{}])[0].get("amount") if m.get("limits") else None

        if mtype == "moneyline":
            ml = {}
            for p in prices:
                designation = p.get("designation")
                price_dec = parse_price(p)
                if not price_dec:
                    continue
                if designation == "home":
                    ml["home"] = price_dec
                elif designation == "away":
                    ml["away"] = price_dec
                elif designation == "draw":
                    ml["draw"] = price_dec
            if ml:
                out["moneyline"] = ml
                if max_limit:
                    out["max_stake_moneyline"] = max_limit

        elif mtype == "total":
            line = m.get("points")
            if line is None:
                continue
            ou = {"line": line}
            for p in prices:
                designation = p.get("designation")
                price_dec = parse_price(p)
                if not price_dec:
                    continue
                if designation == "over":
                    ou["over"] = price_dec
                elif designation == "under":
                    ou["under"] = price_dec
            if "over" in ou or "under" in ou:
                out["totals"].append(ou)

        elif mtype == "spread":
            line = m.get("points")
            if line is None:
                continue
            sp = {"line": line}
            for p in prices:
                designation = p.get("designation")
                price_dec = parse_price(p)
                if not price_dec:
                    continue
                if designation == "home":
                    sp["home"] = price_dec
                elif designation == "away":
                    sp["away"] = price_dec
            if "home" in sp or "away" in sp:
                out["spreads"].append(sp)

    return out


# ---- Pipeline principal ----------------------------------------------------

def scrape(sports, lookback_hours, max_events, dry_run):
    """Pipeline complet : list events → fetch markets → parse → save."""
    captured_at = datetime.now(timezone.utc).isoformat()
    all_events = []

    for sport in sports:
        if sport not in SPORT_IDS:
            print(f"  [skip] sport inconnu : {sport}")
            continue
        print(f"\n[{sport}] discovery upcoming events...")
        events = list_matchups(sport, lookback_hours=lookback_hours)
        print(f"  {len(events)} matchs trouvés")
        if max_events:
            events = events[:max_events]
        if dry_run:
            for e in events[:5]:
                print(f"    - {e['home']} vs {e['away']} | {e['league']} | {e['starts']}")
            all_events.extend(events)
            continue

        ids = [e["pinnacle_id"] for e in events]
        print(f"  fetch markets pour {len(ids)} matchs...")
        markets_by_id = fetch_markets(ids)
        for e in events:
            e["captured_at"] = captured_at
            mid = str(e["pinnacle_id"])
            md = markets_by_id.get(mid)
            parsed = parse_markets(md)
            e.update(parsed)
            all_events.append(e)
        ml_count = sum(1 for e in events if e.get("moneyline"))
        print(f"  {ml_count}/{len(events)} avec moneyline parsée")

    payload = {"captured_at": captured_at, "events": all_events}
    if dry_run:
        print(f"\n[dry-run] {len(all_events)} events listés, fichier NON écrit")
        return payload

    Path(OUT_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"\n✓ Sauvé {len(all_events)} events → {OUT_PATH}")
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sports", nargs="+", default=list(SPORT_IDS.keys()),
                    help=f"Sports à scraper (default: tous). Choix : {list(SPORT_IDS.keys())}")
    ap.add_argument("--lookback", default="0h",
                    help="Heures à regarder en arrière (default 0h, format ex: 24h)")
    ap.add_argument("--max-events", type=int, default=None,
                    help="Limite par sport pour test rapide")
    ap.add_argument("--dry-run", action="store_true",
                    help="Liste events sans fetch markets ni écriture")
    args = ap.parse_args()

    lookback_hours = int(args.lookback.rstrip("h")) if args.lookback.endswith("h") else int(args.lookback)
    scrape(args.sports, lookback_hours, args.max_events, args.dry_run)


if __name__ == "__main__":
    main()
