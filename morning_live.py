#!/usr/bin/env python3
"""
Morning Live — récupère les matchs du jour via API Sofascore (instantané)
et croise avec les cotes magiques calibrées sur l'historique.

Output : top combos 2-3 jambes prêts à parier.

Usage :
    python3 morning_live.py
    python3 morning_live.py --date 2025-05-02
    python3 morning_live.py --top 10 --max-legs 3
"""

import argparse
import json
import os
import ssl
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from itertools import combinations
from pathlib import Path

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
HEADERS = {"User-Agent": "Mozilla/5.0"}

MAGIC_FILE = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes.json"
MAGIC_SMART_FILE = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json"


def categorize_tennis(league, category):
    txt = f"{league} {category}"
    txt_lower = txt.lower()
    if "women" in txt_lower or "wta" in txt_lower or league.endswith(" Women"):
        tour = "WTA"
    elif "atp" in txt_lower or "men" in txt_lower:
        tour = "ATP"
    elif "davis" in txt_lower:
        tour = "DAVIS"
    elif "billie" in txt_lower or "fed cup" in txt_lower:
        tour = "BJK_CUP"
    elif "united cup" in txt_lower or "hopman" in txt_lower:
        tour = "MIXED"
    elif "itf" in txt_lower:
        tour = "ITF"
    else:
        tour = "OTHER"
    if "qualifying" in txt_lower or "qualif" in txt_lower:
        level = "QUALIF"
    elif any(gs in txt for gs in ("Australian Open", "French Open", "Wimbledon", "US Open")):
        level = "GS"
    elif "challenger" in txt_lower:
        level = "CHL"
    elif "itf" in txt_lower:
        level = "ITF"
    elif any(m in txt for m in ("Madrid", "Rome", "Indian Wells", "Miami", "Cincinnati", "Canada", "Shanghai", "Paris", "Monte-Carlo")):
        level = "M1000"
    else:
        level = "M250-500"
    return f"{tour}_{level}"


def categorize_foot(league, category):
    league_l = league.lower()
    cat_l = (category or "").lower()
    suffix = "_W" if any(w in (league_l + " " + cat_l) for w in ("women", "féminine", "femenine", "femini", "kvinner", "frauen")) else ""
    # TOP5 strict : nom de ligue ET pays correspondant
    TOP5_COUNTRIES = {
        "premier league": "england",
        "laliga": "spain", "la liga": "spain",
        "bundesliga": "germany",
        "serie a": "italy",
        "ligue 1": "france",
    }
    for top_name, country in TOP5_COUNTRIES.items():
        if league_l == top_name and country in cat_l:
            return f"TOP5_{league.replace(' ','')}{suffix}"
    # UCL/Europa : strict UEFA spécifique (pas de match sur "championship round")
    if league_l == "uefa champions league" or league_l.startswith("uefa champions league,") or league_l == "ucl":
        return "UEFA_Champions" + suffix
    if league_l == "uefa europa league" or league_l.startswith("uefa europa league,"):
        return "UEFA_Europa" + suffix
    if "international" in cat_l or "world cup" in league_l or "uefa euro" in league_l:
        return "Intl" + suffix
    return league + suffix


def categorize_basket(league, category):
    is_women = "women" in (league + " " + (category or "")).lower()
    cat_l = (category or "").lower()
    phase = "_PO" if "playoffs" in cat_l else ("_RS" if "regular" in cat_l else "")
    return league + ("_W" if is_women else "") + phase


def categorize_hockey(league, category):
    cat_l = (category or "").lower()
    if "playoffs" in cat_l: return league + "_PO"
    if "regular" in cat_l: return league + "_RS"
    return league


def categorize_baseball(league, category):
    return league


CATEGORIZERS = {
    "tennis": categorize_tennis,
    "football": categorize_foot,
    "basketball": categorize_basket,
    "ice-hockey": categorize_hockey,
    "baseball": categorize_baseball,
}

# Cotes magiques fallback (calibrées sur foot/tennis/NBA/NHL/MLB)
MAGIC_FALLBACK = {
    "football": {1.14: 0.89, 1.40: 0.72, 1.44: 0.72, 1.65: 0.63, 1.66: 0.60},
    "tennis_atp": {1.06: 0.95, 1.07: 0.94, 1.40: 0.72},
    "tennis_wta": {1.06: 0.97, 1.11: 0.93, 1.14: 0.89, 1.28: 0.81},
    "tennis": {1.06: 0.96, 1.07: 0.94, 1.11: 0.91, 1.14: 0.88, 1.28: 0.81, 1.40: 0.71},
    "basketball": {1.09: 0.95, 1.10: 0.94, 1.14: 0.93, 1.17: 0.96, 1.18: 0.86,
                   1.20: 0.84, 1.22: 0.83, 1.33: 0.88, 1.36: 0.74, 1.61: 0.76,
                   1.71: 0.64, 1.83: 0.62},
    "ice-hockey": {1.36: 0.89, 1.37: 0.80, 1.42: 0.73, 1.44: 0.77, 1.46: 0.70,
                   1.49: 0.73, 1.50: 0.67, 1.56: 0.73, 1.59: 0.64, 1.63: 0.62,
                   1.67: 0.62, 1.71: 0.59, 1.74: 0.58, 1.77: 0.57},
    "baseball": {1.38: 0.76, 1.42: 0.74, 1.43: 0.70, 1.44: 0.77, 1.48: 0.74,
                 1.49: 0.73, 1.59: 0.69, 1.74: 0.61, 1.83: 0.56},
}


def fetch(url, retries=2):
    """Délègue à sofascore_massive.fetch (Camoufox bypass Cloudflare)."""
    try:
        from sofascore_massive import fetch as _fetch
        return _fetch(url, retries=retries)
    except ImportError:
        # Fallback urllib (probablement bloqué par Cloudflare)
        for i in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, context=ctx, timeout=10) as r:
                    return json.loads(r.read())
            except Exception:
                if i == retries:
                    return None


def frac_to_dec(s):
    if not s or "/" not in str(s):
        return None
    try:
        n, d = str(s).split("/")
        return round((int(n) + int(d)) / int(d), 2)
    except (ValueError, ZeroDivisionError):
        return None


def round_cote(o):
    return round(round(o / 0.01) * 0.01, 2)


def _extract_wr(v):
    """Accepte wr direct (float) ou dict {wr, n, ev} et renvoie le float wr."""
    if isinstance(v, dict):
        return float(v.get("wr", 0))
    return float(v)


def load_magic():
    """Charge cotes magiques smart si dispo (sport×bucket→cote→wr), sinon fallback sport→cote→wr."""
    if os.path.exists(MAGIC_SMART_FILE):
        with open(MAGIC_SMART_FILE) as f:
            data = json.load(f)
        out = {}
        for sport, buckets in data.items():
            out[sport] = {bucket: {float(c): _extract_wr(wr) for c, wr in cotes.items()}
                          for bucket, cotes in buckets.items()}
        return {"_smart": True, **out}
    if os.path.exists(MAGIC_FILE):
        with open(MAGIC_FILE) as f:
            data = json.load(f)
        return {k: {float(c): _extract_wr(wr) for c, wr in v.items()} for k, v in data.items()}
    return MAGIC_FALLBACK


def list_today_events(sport, day_str):
    data = fetch(f"https://api.sofascore.com/api/v1/sport/{sport}/scheduled-events/{day_str}")
    if not data:
        return []
    out = []
    for e in data.get("events", []):
        # Events futurs uniquement (Not started)
        status = e.get("status", {}).get("type", "")
        if status not in ("notstarted", "inprogress"):
            continue
        out.append({
            "id": e["id"],
            "sport": sport,
            "league": e.get("tournament", {}).get("name", "?"),
            "category": e.get("tournament", {}).get("category", {}).get("name", "?"),
            "home": e["homeTeam"]["name"],
            "away": e["awayTeam"]["name"],
            "start_time": e.get("startTimestamp"),
        })
    return out


def fetch_event_odds(event):
    eid = event["id"]
    odds = fetch(f"https://api.sofascore.com/api/v1/event/{eid}/odds/1/all")
    if not odds:
        return None
    markets = odds.get("markets", [])
    out = dict(event)

    ft = next((m for m in markets if m.get("marketName") == "Full time"), None)
    if ft:
        for c in ft.get("choices", []):
            n = c.get("name")
            cote = frac_to_dec(c.get("fractionalValue"))
            if n == "1" and cote: out["odds_1"] = cote
            if n == "2" and cote: out["odds_2"] = cote
            if n == "X" and cote: out["odds_x"] = cote

    btts = next((m for m in markets if m.get("marketName") == "Both teams to score"), None)
    if btts:
        for c in btts.get("choices", []):
            n = (c.get("name") or "").lower()
            cote = frac_to_dec(c.get("fractionalValue"))
            if n == "yes" and cote: out["odds_btts_y"] = cote
            if n == "no" and cote: out["odds_btts_n"] = cote

    # Match goals (Over/Under multi-thresholds)
    for mg in markets:
        if mg.get("marketName") != "Match goals":
            continue
        thr = (mg.get("choiceGroup") or "").strip()
        if thr not in ("0.5", "1.5", "2.5", "3.5"):
            continue
        suffix = thr.replace(".", "_")
        for c in mg.get("choices", []):
            n = c.get("name")
            cote = frac_to_dec(c.get("fractionalValue"))
            if n == "Over" and cote: out[f"odds_over_{suffix}"] = cote
            if n == "Under" and cote: out[f"odds_under_{suffix}"] = cote

    return out


def extract_picks(event, magic_table):
    """Renvoie les sélections (label, cote, wr_estimée) qui matchent une cote magique."""
    sport = event["sport"]
    smart_mode = magic_table.get("_smart", False)
    if smart_mode:
        cat_fn = CATEGORIZERS.get(sport)
        bucket = cat_fn(event.get("league", ""), event.get("category", "")) if cat_fn else None
        bucket_magic = magic_table.get(sport, {}).get(bucket, {})
        # Fallback : agrège tous les buckets du sport si bucket spécifique vide
        if not bucket_magic:
            magic = {}
            for b_cotes in magic_table.get(sport, {}).values():
                if isinstance(b_cotes, dict):
                    for c, wr in b_cotes.items():
                        if c not in magic or wr > magic[c]:
                            magic[c] = wr
        else:
            magic = bucket_magic
    else:
        magic = magic_table.get(sport, {})
    if not magic:
        return []

    picks = []
    home_team = event["home"]
    away_team = event["away"]

    for label, side_key in (("Home", "odds_1"), ("Away", "odds_2"), ("Draw", "odds_x")):
        cote = event.get(side_key)
        if not cote:
            continue
        c_round = round_cote(cote)
        for mc, wr in magic.items():
            if abs(c_round - mc) <= 0.01:
                team = home_team if label == "Home" else (away_team if label == "Away" else "Match nul")
                picks.append({
                    "match": f"{home_team} vs {away_team}",
                    "league": event["league"],
                    "sport": sport,
                    "selection": team,
                    "side": label,
                    "odds": cote,
                    "wr": wr,
                    "ev": wr * cote - 1,
                    "start_time": event.get("start_time"),
                })
                break
    return picks


def build_combos(picks, max_legs=3, cote_min=2.0, cote_max=5.0, max_combos=10, sort_by="ev"):
    candidates = []
    for n_legs in (2, 3, 4):
        if n_legs > max_legs:
            break
        for combo in combinations(picks, n_legs):
            if len({p["match"] for p in combo}) < n_legs:
                continue
            cote_t = 1.0
            wr_t = 1.0
            for p in combo:
                cote_t *= p["odds"]
                wr_t *= p["wr"]
            if cote_t < cote_min or cote_t > cote_max:
                continue
            ev = wr_t * cote_t - 1
            candidates.append({"legs": combo, "cote_t": cote_t, "wr_t": wr_t, "ev": ev})

    if sort_by == "wr":
        candidates.sort(key=lambda c: -c["wr_t"])
    elif sort_by == "cote":
        candidates.sort(key=lambda c: -c["cote_t"])
    else:
        candidates.sort(key=lambda c: -c["ev"])

    selected = []
    for c in candidates:
        keys_c = {(p["match"], p["selection"]) for p in c["legs"]}
        if any(len(keys_c & {(p["match"], p["selection"]) for p in s["legs"]}) >= 2 for s in selected):
            continue
        selected.append(c)
        if len(selected) >= max_combos:
            break
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (default: today)")
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--max-legs", type=int, default=3)
    ap.add_argument("--cote-min", type=float, default=2.0)
    ap.add_argument("--cote-max", type=float, default=5.0)
    args = ap.parse_args()

    day_str = args.date or date.today().isoformat()
    magic = load_magic()
    print(f"📅 Date : {day_str}")
    print(f"🔮 Cotes magiques chargées : {sum(len(v) for v in magic.values())} sur {len(magic)} sports")

    sports = ["football", "basketball", "ice-hockey", "baseball", "tennis"]

    # Phase 1 : liste events
    print("\n⏳ Récupération calendar Sofascore (5 sports)…")
    all_events = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for evs in pool.map(lambda s: list_today_events(s, day_str), sports):
            all_events.extend(evs)
    print(f"   {len(all_events)} matchs upcoming/inprogress")

    if not all_events:
        print("Aucun match. Vérifie la date ou réessaie plus tard.")
        return

    # Phase 2 : odds en parallèle
    print("⏳ Récupération cotes pre-match (parallèle 30 threads)…")
    events_with_odds = []
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = [pool.submit(fetch_event_odds, e) for e in all_events]
        for f in as_completed(futures):
            r = f.result()
            if r and (r.get("odds_1") or r.get("odds_2")):
                events_with_odds.append(r)
    print(f"   {len(events_with_odds)} matchs avec cotes")

    # Phase 3 : extraction picks
    picks = []
    for e in events_with_odds:
        picks.extend(extract_picks(e, magic))
    print(f"\n🎯 {len(picks)} sélections matchent une cote magique :\n")

    picks.sort(key=lambda p: -p["ev"])
    for i, p in enumerate(picks[:30], 1):
        print(f"  {i:>2}. [{p['sport']:<10}] {p['match'][:42]:<42} → {p['selection'][:22]:<22} @ {p['odds']:.2f}  wr {p['wr']*100:.0f}%  EV {p['ev']*100:+.1f}%")
        print(f"      {p['league']}")

    if not picks:
        print("Aucune cote magique sur les matchs du jour. Reviens plus tard.")
        return

    combos = build_combos(picks, max_legs=args.max_legs,
                         cote_min=args.cote_min, cote_max=args.cote_max,
                         max_combos=args.top)
    print(f"\n{'='*70}")
    print(f"🏆 TOP {len(combos)} COMBINÉS DU JOUR (cote totale {args.cote_min}-{args.cote_max})")
    print(f"{'='*70}\n")
    for i, c in enumerate(combos, 1):
        print(f"--- COMBO #{i} | cote totale {c['cote_t']:.2f} | WR estimée {c['wr_t']*100:.0f}% | EV {c['ev']*100:+.0f}% ---")
        for j, leg in enumerate(c["legs"], 1):
            print(f"  {j}. [{leg['sport']}] {leg['match']}")
            print(f"     → {leg['selection']} @ {leg['odds']:.2f}  ({leg['league']})")
        print()


if __name__ == "__main__":
    main()
