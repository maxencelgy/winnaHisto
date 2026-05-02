#!/usr/bin/env python3
"""
Backtest engine — simule à une date passée ce que `morning_combos` aurait proposé,
et vérifie quels combos auraient passé (résultats déjà connus dans le dataset).
"""

import csv
import glob
import os
from collections import defaultdict
from itertools import combinations
from pathlib import Path

DATASETS_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"


def fnum(s):
    try:
        return float(str(s).replace(",", "."))
    except (TypeError, ValueError):
        return None


def round_cote(o):
    return round(round(o / 0.01) * 0.01, 2)


_INDEX = None
_INDEX_MTIME = None


def _index_mtime():
    """Renvoie max mtime des CSV pour invalider le cache si ça change."""
    return max((os.path.getmtime(p) for p in glob.glob(os.path.join(DATASETS_DIR, "*.csv"))), default=0)


def _build_index():
    """Charge tous les CSV en mémoire indexés par date. Une seule fois."""
    idx = defaultdict(list)
    for path in glob.glob(os.path.join(DATASETS_DIR, "*.csv")):
        sport = os.path.basename(path).replace(".csv", "")
        try:
            with open(path, encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    try:
                        hs = int(r.get("hs", 0) or 0)
                        asc = int(r.get("as", 0) or 0)
                    except (TypeError, ValueError):
                        continue
                    if hs == 0 and asc == 0:
                        continue
                    btts_str = (r.get("btts") or "").strip().lower()
                    btts_yes = btts_str in ("true", "1", "yes")
                    total = hs + asc
                    idx[r.get("date", "").strip()].append({
                        "sport": sport,
                        "league": r.get("league", ""),
                        "category": r.get("category", ""),
                        "home": r.get("home", ""),
                        "away": r.get("away", ""),
                        "hs": hs, "as": asc,
                        "home_won": hs > asc, "is_draw": hs == asc,
                        "odds_1": fnum(r.get("odds_1")),
                        "odds_2": fnum(r.get("odds_2")),
                        "odds_x": fnum(r.get("odds_x")),
                        # Marchés étendus : BTTS (Both Teams To Score)
                        "btts_yes": btts_yes,
                        "odds_btts_y": fnum(r.get("odds_btts_y")),
                        "odds_btts_n": fnum(r.get("odds_btts_n")),
                        # Marchés Over/Under : résultats déduits du score
                        "over_1_5": total >= 2,
                        "over_2_5": total >= 3,
                        "over_3_5": total >= 4,
                        "odds_over_1_5": fnum(r.get("odds_over_1_5")),
                        "odds_under_1_5": fnum(r.get("odds_under_1_5")),
                        "odds_over_2_5": fnum(r.get("odds_over_2_5")),
                        "odds_under_2_5": fnum(r.get("odds_under_2_5")),
                        "odds_over_3_5": fnum(r.get("odds_over_3_5")),
                        "odds_under_3_5": fnum(r.get("odds_under_3_5")),
                    })
        except Exception:
            continue
    return idx


def _get_index():
    """Lazy load + invalidation cache."""
    global _INDEX, _INDEX_MTIME
    cur_mtime = _index_mtime()
    if _INDEX is None or _INDEX_MTIME != cur_mtime:
        _INDEX = _build_index()
        _INDEX_MTIME = cur_mtime
    return _INDEX


def load_matches_for_date(target_date):
    """Renvoie matchs d'une date depuis l'index global (zero IO disque après le 1er appel)."""
    return _get_index().get(target_date, [])


def extract_picks(matches, magic_table, market="1x2", bucket_fn=None):
    """Pour chaque match, identifie les sélections matchant une cote magique.
    market: '1x2'|'btts'|'over_1_5'|'over_2_5' OU une liste séparée par virgules
            (ex 'over_1_5,1x2') pour combiner plusieurs marchés.
    bucket_fn: optionnel, fonction (sport, league, category) -> bucket_str. Si None, utilise CATEGORIZERS.
    Si magic_table est étendu (structure {sport: {bucket: {sub_market: {cote: ...}}}}),
    chaque side cherche dans le sub_market correspondant."""
    # Multi-markets : union des picks. Supporte aussi un filtre par selection :
    # "over_1_5+plus,1x2-nul" → over_1_5 où selection contient "plus" + 1x2 où selection ne contient pas "nul"
    if isinstance(market, str) and ("," in market or "+" in market or "-" in market):
        all_picks = []
        for m in market.split(","):
            m = m.strip()
            include = None; exclude = None
            if "+" in m:
                m, include = m.split("+", 1)
                include = include.lower()
            elif "-" in m:
                m, exclude = m.split("-", 1)
                exclude = exclude.lower()
            sub_picks = extract_picks(matches, magic_table, market=m.strip(), bucket_fn=bucket_fn)
            if include:
                sub_picks = [p for p in sub_picks if include in p["selection"].lower()]
            elif exclude:
                sub_picks = [p for p in sub_picks if exclude not in p["selection"].lower()]
            all_picks.extend(sub_picks)
        return all_picks
    from morning_live import CATEGORIZERS
    picks = []
    smart_mode = magic_table.get("_smart", False)
    # Format des sides : (label, side, cote_field, won_fn, sub_market)
    if market == "btts":
        sides = [
            ("BTTS_yes", "BTTS_Y", "odds_btts_y", lambda m: m.get("btts_yes", False), "btts_y"),
            ("BTTS_no", "BTTS_N", "odds_btts_n", lambda m: not m.get("btts_yes", False), "btts_n"),
        ]
    elif market == "over_1_5":
        sides = [
            ("Over 1.5", "OV15", "odds_over_1_5", lambda m: m.get("over_1_5", False), "over_1_5"),
            ("Under 1.5", "UN15", "odds_under_1_5", lambda m: not m.get("over_1_5", False), "under_1_5"),
        ]
    elif market == "over_2_5":
        sides = [
            ("Over 2.5", "OV25", "odds_over_2_5", lambda m: m.get("over_2_5", False), "over_2_5"),
            ("Under 2.5", "UN25", "odds_under_2_5", lambda m: not m.get("over_2_5", False), "under_2_5"),
        ]
    else:
        sides = [
            ("Home", "1", "odds_1", lambda m: m["home_won"], "1x2"),
            ("Away", "2", "odds_2", lambda m: not m["home_won"] and not m["is_draw"], "1x2"),
            ("Draw", "X", "odds_x", lambda m: m["is_draw"], "1x2"),
        ]
    for m in matches:
        if smart_mode:
            if bucket_fn is not None:
                bucket = bucket_fn(m["sport"], m.get("league", ""), m.get("category", ""))
            else:
                cat_fn = CATEGORIZERS.get(m["sport"])
                bucket = cat_fn(m.get("league", ""), m.get("category", "")) if cat_fn else None
            bucket_data = magic_table.get(m["sport"], {}).get(bucket, {})
        else:
            bucket_data = magic_table.get(m["sport"], {})
        if not bucket_data:
            continue
        # Détection format étendu : si bucket_data a des clés "1x2"/"btts_y"/"btts_n"
        is_extended = isinstance(bucket_data, dict) and any(
            k in bucket_data for k in ("1x2", "btts_y", "btts_n", "over_1_5", "under_1_5", "over_2_5", "under_2_5"))
        for label, side, cote_field, won_fn, sub_market in sides:
            magic = bucket_data.get(sub_market, {}) if is_extended else bucket_data
            if not magic:
                continue
            won = won_fn(m)
            cote = m.get(cote_field)
            if not cote or cote <= 1:
                continue
            c_round = round_cote(cote)
            for mc, val in magic.items():
                mc = float(mc)
                if abs(c_round - mc) <= 0.01:
                    wr = val["wr"] if isinstance(val, dict) else val
                    if side == "1": selection = m["home"]
                    elif side == "2": selection = m["away"]
                    elif side == "X": selection = "Match nul"
                    elif side == "BTTS_Y": selection = "Les 2 marquent (Oui)"
                    elif side == "BTTS_N": selection = "Les 2 marquent (Non)"
                    elif side == "OV15": selection = "Plus de 1.5 buts"
                    elif side == "UN15": selection = "Moins de 1.5 buts"
                    elif side == "OV25": selection = "Plus de 2.5 buts"
                    elif side == "UN25": selection = "Moins de 2.5 buts"
                    else: selection = side
                    picks.append({
                        "sport": m["sport"],
                        "league": m["league"],
                        "match": f'{m["home"]} vs {m["away"]}',
                        "selection": selection,
                        "side": side,
                        "odds": cote,
                        "wr": wr,
                        "ev": wr * cote - 1,
                        "won": won,
                        "score": f'{m["hs"]}-{m["as"]}',
                    })
                    break
    return picks


def build_backtest_combos(picks, max_legs=3, cote_min=2.0, cote_max=5.0,
                          max_combos=10, sort_by="ev", rigorous=False):
    # Cap adaptatif selon max_legs pour éviter explosion combinatoire 4-5 jambes.
    # C(40,4)=91k vs C(100,4)=3.9M (×40 plus rapide). Picks au-delà du top sont marginaux.
    ADAPTIVE_TOP = {1: 200, 2: 200, 3: 100, 4: 40, 5: 25, 6: 15}
    top_n = ADAPTIVE_TOP.get(max_legs, 50)
    if not rigorous and len(picks) > top_n:
        if sort_by == "wr":
            picks = sorted(picks, key=lambda p: -p["wr"])[:top_n]
        elif sort_by == "cote":
            picks = sorted(picks, key=lambda p: -p["odds"])[:top_n]
        else:
            picks = sorted(picks, key=lambda p: -p["ev"])[:top_n]
    candidates = []
    for n_legs in (1, 2, 3, 4, 5, 6):
        if n_legs > max_legs:
            break
        for combo in combinations(picks, n_legs):
            if len({p["match"] for p in combo}) < n_legs:
                continue
            cote_t = 1.0
            wr_t = 1.0
            all_won = True
            for p in combo:
                cote_t *= p["odds"]
                wr_t *= p["wr"]
                if not p["won"]:
                    all_won = False
            if cote_t < cote_min or cote_t > cote_max:
                continue
            ev = wr_t * cote_t - 1
            candidates.append({
                "legs": list(combo),
                "cote_t": cote_t,
                "wr_t": wr_t,
                "ev": ev,
                "won": all_won,
            })

    if sort_by == "wr":
        candidates.sort(key=lambda c: -c["wr_t"])
    elif sort_by == "cote":
        candidates.sort(key=lambda c: -c["cote_t"])
    else:
        candidates.sort(key=lambda c: -c["ev"])

    selected = []
    selected_matches_single = set()  # utilisé pour max_legs=1 : dédup par match
    for c in candidates:
        if max_legs == 1:
            m_key = c["legs"][0]["match"]
            if m_key in selected_matches_single:
                continue
            selected.append(c)
            selected_matches_single.add(m_key)
        else:
            keys_c = {(p["match"], p["selection"]) for p in c["legs"]}
            if any(len(keys_c & {(p["match"], p["selection"]) for p in s["legs"]}) >= 2 for s in selected):
                continue
            selected.append(c)
        if len(selected) >= max_combos:
            break
    return selected


def run_backtest(target_date, magic_table, max_legs=3, cote_min=2.0,
                 cote_max=5.0, max_combos=10, sort_by="ev", stake=10.0,
                 sports_filter=None, min_ev=None, min_wr=None, rigorous=False,
                 league_filter=None, market="1x2", bucket_fn=None):
    matches = load_matches_for_date(target_date)
    if sports_filter:
        matches = [m for m in matches if m["sport"] in sports_filter]
    if league_filter:
        matches = [m for m in matches if league_filter(m["sport"], m.get("league", ""))]
    picks = extract_picks(matches, magic_table, market=market, bucket_fn=bucket_fn)
    if min_wr is not None:
        picks = [p for p in picks if p["wr"] >= min_wr]
    if min_ev is not None:
        picks = [p for p in picks if p["ev"] >= min_ev]
    combos = build_backtest_combos(picks, max_legs=max_legs, cote_min=cote_min,
                                   cote_max=cote_max, max_combos=max_combos,
                                   sort_by=sort_by, rigorous=rigorous)

    n_won = sum(1 for c in combos if c["won"])
    pnl = sum(stake * (c["cote_t"] - 1) if c["won"] else -stake for c in combos)
    total_stake = stake * len(combos)

    return {
        "date": target_date,
        "n_matches": len(matches),
        "n_picks": len(picks),
        "n_combos": len(combos),
        "n_won": n_won,
        "wr_combos": n_won / len(combos) if combos else 0,
        "stake": stake,
        "total_stake": total_stake,
        "pnl": pnl,
        "roi": pnl / total_stake if total_stake else 0,
        "combos": combos,
        "picks": picks[:50],
    }


def run_backtest_period(start_date, end_date, magic_table, **kwargs):
    """Backtest sur période. Renvoie stats agrégées + jour par jour."""
    from datetime import datetime, timedelta
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    days = []
    cur = start
    while cur <= end:
        days.append(cur.isoformat())
        cur += timedelta(days=1)

    daily_results = []
    total_n_combos = 0
    total_n_won = 0
    total_pnl = 0.0
    total_stake = 0.0
    n_days_played = 0
    bankroll_curve = [0]
    streak_won = 0
    streak_lost = 0
    max_streak_won = 0
    max_streak_lost = 0
    best_day_pnl = 0
    worst_day_pnl = 0
    best_day = ""
    worst_day = ""

    for d in days:
        r = run_backtest(d, magic_table, **kwargs)
        daily_results.append({
            "date": d,
            "n_matches": r["n_matches"],
            "n_picks": r["n_picks"],
            "n_combos": r["n_combos"],
            "n_won": r["n_won"],
            "pnl": r["pnl"],
            "combos": r["combos"],
        })
        if r["n_combos"] > 0:
            n_days_played += 1
            total_n_combos += r["n_combos"]
            total_n_won += r["n_won"]
            total_pnl += r["pnl"]
            total_stake += r["total_stake"]
            bankroll_curve.append(total_pnl)
            if r["pnl"] > best_day_pnl:
                best_day_pnl = r["pnl"]
                best_day = d
            if r["pnl"] < worst_day_pnl:
                worst_day_pnl = r["pnl"]
                worst_day = d
            if r["n_won"] == r["n_combos"]:
                streak_won += 1
                streak_lost = 0
                max_streak_won = max(max_streak_won, streak_won)
            elif r["n_won"] == 0:
                streak_lost += 1
                streak_won = 0
                max_streak_lost = max(max_streak_lost, streak_lost)
            else:
                streak_won = 0
                streak_lost = 0

    return {
        "start_date": start_date,
        "end_date": end_date,
        "n_days_total": len(days),
        "n_days_played": n_days_played,
        "n_combos_total": total_n_combos,
        "n_won_total": total_n_won,
        "wr_combos": total_n_won / total_n_combos if total_n_combos else 0,
        "pnl_total": total_pnl,
        "stake_total": total_stake,
        "roi": total_pnl / total_stake if total_stake else 0,
        "best_day": best_day,
        "best_day_pnl": best_day_pnl,
        "worst_day": worst_day,
        "worst_day_pnl": worst_day_pnl,
        "max_streak_won": max_streak_won,
        "max_streak_lost": max_streak_lost,
        "daily": daily_results,
        "bankroll_curve": bankroll_curve,
    }
