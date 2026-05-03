"""Backtester : applique une stratégie JSON sur un range de dates.

Wrap backtest_engine.run_backtest pour chaque composante puis agrège.

Usage:
    from picks.backtester import backtest
    r = backtest(strategy, "2026-01-01", "2026-04-30", bankroll0=100)
    # r = {daily: [...], summary: {...}}
"""
import os, sys
from datetime import datetime, timedelta
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_engine import run_backtest as bt_run_backtest, _get_index
from morning_live import CATEGORIZERS

# Whitelist Winamax FR (identique scraper.py)
WINAMAX_LEAGUES = {
    "football": ["premier league", "laliga", "la liga", "serie a", "bundesliga", "ligue 1",
                 "championship", "laliga 2", "serie b", "ligue 2", "champions league",
                 "europa league", "conference", "eredivisie", "liga portugal", "pro league",
                 "süper lig", "trendyol süper", "mls", "liga mx", "brasileirão", "brasileirao",
                 "coupe", "fa cup", "primeira liga", "primera división"],
    "basketball": ["nba", "wnba", "euroleague", "eurocup", "betclic élite", "pro a", "acb",
                   "liga endesa", "lega basket", "serie a", "bbl", "champions league"],
    "ice-hockey": ["nhl", "khl", "shl", "liiga", "ligue magnus", "del", "national league",
                   "extraliga", "swiss"],
    "baseball": ["mlb"],
    "tennis": ["atp", "wta", "grand slam", "masters", "australian open", "roland garros",
               "wimbledon", "us open", "miami", "indian wells", "monte carlo", "madrid",
               "rome", "cincinnati", "shanghai", "paris masters"],
}
REJECT = ["doubles", "qualifying", "u23", "u21", "u19", "u18", "reserve", "youth",
          "next pro", "regionalliga", "série c", "i-league", "exhibition"]


def _is_league_allowed(sport, league):
    if not league:
        return False
    l = league.lower()
    if any(r in l for r in REJECT):
        return False
    return any(p in l for p in WINAMAX_LEAGUES.get(sport, []))


def _gen_days(start, end):
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end, "%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)


def _streak_red(daily_pnls):
    s = c = 0
    for p in daily_pnls:
        if p < 0:
            c += 1
            s = max(s, c)
        else:
            c = 0
    return s


def _max_dd(daily_pnls):
    cum = peak = dd = 0
    for p in daily_pnls:
        cum += p
        if cum > peak:
            peak = cum
        dd = max(dd, peak - cum)
    return dd


def _load_magic():
    from picks.magic import Magic
    return Magic()


def backtest(strategy, start_date, end_date, bankroll0=100,
             bookmaker="winamax_fr", base_stake=10, excluded_leagues=None):
    """Run backtest sur strat JSON. Retourne {daily, summary}.
    excluded_leagues : list de substrings (lowercase) — exclut tout pick dont la ligue contient un de ces patterns.
    """
    sizing = strategy.get("sizing", {"mode": "flat_pct", "pct": 0.10, "min_stake": 0.5})
    pct = sizing.get("pct", 0.10)
    min_stake = sizing.get("min_stake", 0.5)
    sizing_mode = sizing.get("mode", "flat_pct")

    dedup = strategy.get("dedup", "none")
    components = strategy["components"]

    excl = [e.lower() for e in (excluded_leagues or []) if e and e.strip()]
    base_filter = _is_league_allowed if bookmaker == "winamax_fr" else None
    if excl:
        def league_filter(sport, league):
            if base_filter and not base_filter(sport, league):
                return False
            if not league:
                return True
            ll = league.lower()
            if any(e in ll for e in excl):
                return False
            return True
    else:
        league_filter = base_filter
    days = list(_gen_days(start_date, end_date))

    # Magic ref : utilise version OOS (train<2026-01-01) pour backtest si dispo,
    # sinon fallback sur la magic LIVE (qui peut être plus récente).
    import json
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    smart_path = os.path.join(root, "datasets", "magic_cotes_smart_oos.json")
    ext_path = os.path.join(root, "datasets", "magic_cotes_extended_oos.json")
    if not os.path.exists(smart_path):
        smart_path = os.path.join(root, "datasets", "magic_cotes_smart.json")
        ext_path = os.path.join(root, "datasets", "magic_cotes_extended.json")
    with open(smart_path) as f:
        raw_smart = json.load(f)
    magic_smart = {"_smart": True}
    for sp, buckets in raw_smart.items():
        if sp == "_smart": continue
        magic_smart[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                               for c,info in cotes.items()}
                           for b, cotes in buckets.items()}
    with open(ext_path) as f:
        magic_ext = json.load(f)

    # Pré-fetch candidats par (jour, composante). Plus large si dedup actif.
    candidate_pool_size = 12 if dedup != "none" else 3
    cand_by_day_comp = {}

    for i, comp in enumerate(components):
        market = comp.get("market", "1x2")
        m_ref = magic_ext if market in ("btts", "over_1_5", "over_2_5") else magic_smart
        # Support `sport` (single) ou `sports` (list, pour combos multi-sport)
        sports_list = comp.get("sports") or [comp["sport"]]
        kwargs = dict(
            max_legs=comp.get("max_legs", 1),
            cote_min=comp["cote_min"],
            cote_max=comp["cote_max"],
            sort_by=comp.get("sort_by", "wr"),
            sports_filter=sports_list,
            max_combos=comp.get("max_combos", 3) * candidate_pool_size,
            stake=base_stake,
            league_filter=league_filter,
            market=market,
            min_wr=comp.get("min_wr"),
            min_ev=comp.get("min_ev"),
        )
        for d in days:
            try:
                r = bt_run_backtest(d, m_ref, **kwargs)
                cand_by_day_comp[(d, i)] = r["combos"]
            except Exception:
                cand_by_day_comp[(d, i)] = []

    # Sélection avec dédup inter-composantes
    daily_results = []
    bankroll = bankroll0

    for d in days:
        used_picks = Counter()
        used_matches = set()
        day_combos = []
        for i, comp in enumerate(components):
            chosen = 0
            for combo in cand_by_day_comp.get((d, i), []):
                if chosen >= comp.get("max_combos", 3):
                    break
                legs_keys = [(l["match"], l["selection"]) for l in combo["legs"]]
                legs_matches = {l["match"] for l in combo["legs"]}
                if dedup == "max1" and any(used_picks[k] >= 1 for k in legs_keys):
                    continue
                if dedup == "max2" and any(used_picks[k] >= 2 for k in legs_keys):
                    continue
                if dedup == "disjoint" and any(m in used_matches for m in legs_matches):
                    continue
                for k in legs_keys:
                    used_picks[k] += 1
                used_matches |= legs_matches
                day_combos.append(combo)
                chosen += 1

        if not day_combos:
            daily_results.append({
                "date": d, "n_combos": 0, "n_won": 0, "pnl": 0.0,
                "stake": 0.0, "bankroll_end": bankroll, "combos": [],
            })
            continue

        day_pnl = 0
        day_stake = 0
        n_won = 0
        combo_details = []
        for c in day_combos:
            stake = base_stake if sizing_mode == "flat" else max(min_stake, bankroll * pct)
            day_stake += stake
            won = c["won"]
            if won:
                gain = stake * (c["cote_t"] - 1)
                day_pnl += gain
                n_won += 1
            else:
                gain = -stake
                day_pnl -= stake
            combo_details.append({
                "cote_t": c["cote_t"],
                "won": won,
                "stake": round(stake, 2),
                "gain": round(gain, 2),
                "legs": [
                    {"match": l.get("match"), "selection": l.get("selection"),
                     "cote": l.get("odds") or l.get("cote"),
                     "won": l.get("won"),
                     "sport": l.get("sport"),
                     "league": l.get("league"),
                    } for l in c.get("legs", [])
                ],
            })
        bankroll += day_pnl

        daily_results.append({
            "date": d, "n_combos": len(day_combos), "n_won": n_won,
            "pnl": day_pnl, "stake": day_stake, "bankroll_end": bankroll,
            "combos": combo_details,
        })

    # Summary
    pnls = [d["pnl"] for d in daily_results]
    n_total_combos = sum(d["n_combos"] for d in daily_results)
    n_total_won = sum(d["n_won"] for d in daily_results)
    total_pnl = sum(pnls)
    total_stake = sum(d["stake"] for d in daily_results)

    summary = {
        "pnl": total_pnl,
        "bankroll_initial": bankroll0,
        "bankroll_final": bankroll,
        "roi": (total_pnl / total_stake * 100) if total_stake > 0 else 0.0,
        "n_days_played": sum(1 for d in daily_results if d["n_combos"] > 0),
        "n_days_total": len(days),
        "n_days_positive": sum(1 for p in pnls if p > 0),
        "n_days_negative": sum(1 for p in pnls if p < 0),
        "n_combos": n_total_combos,
        "n_won": n_total_won,
        "wr_combos": (n_total_won / n_total_combos) if n_total_combos else 0.0,
        "streak_red_max": _streak_red(pnls),
        "dd_max": _max_dd(pnls),
        "total_stake": total_stake,
    }

    return {"daily": daily_results, "summary": summary}
