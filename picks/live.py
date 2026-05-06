"""Live : applique une stratégie aux events scrapés du jour.

Supports:
  - Singles (max_legs=1) ET combos multi-jambes (max_legs>1)
  - Sizing modes : flat, flat_pct, risk_tiered, kelly_fraction, ev_proportional
  - Dédup inter-composantes (max1, max2, disjoint)
"""
import os, sys, math
from itertools import combinations
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from picks.magic import Magic
from picks.extractor import extract_event_picks


# Liste WFR par défaut : ligues douteuses exclues dans tous les sweeps backtest
# (alignement live ⇄ backtest). Source : sweep WFR_EXCL identique dans find_*.py
WFR_EXCL_DEFAULT = [
    "liga mx", "egyptian", "cyprus", "ligapro", "primera división, clausura",
    "brasileirão série d", "brasileirão série b", "scottish premiership",
    "first professional league", "danish superliga", "superliga", "niké liga",
    "swiss super league", "austrian bundesliga", "stoiximan super league",
    "czech first league", "canadian premier", "usl championship", "copa de la liga",
    "frauen-bundesliga", "serie a femminile", "uefa champions league, women",
    "liga acb", "germany bbl", "wnba preseason", "serie a2", "del, playoffs",
    "relegation round",
]


# ── Sizing ──────────────────────────────────────────────────────────────
def compute_stake(combo, bankroll, sizing):
    """combo : {legs:[{cote, wr}], cote_totale, wr_combo, ev_combo}.
    sizing : config dict.
    Retourne stake en euros (>= min_stake)."""
    mode = sizing.get("mode", "flat_pct")
    min_stake = sizing.get("min_stake", 0.5)
    cap = sizing.get("cap_abs")  # cap absolu €

    if mode == "flat":
        stake = sizing.get("flat", 10.0)

    elif mode == "flat_pct":
        pct = sizing.get("pct", 0.10)
        stake = bankroll * pct

    elif mode == "risk_tiered":
        # Stake décroît selon cote totale (plus risqué = moins de stake)
        # Tiers configurables : [{"cote_max": 2.0, "pct": 0.10}, {"cote_max": 3.0, "pct": 0.07}, ...]
        tiers = sizing.get("tiers", [
            {"cote_max": 2.0, "pct": 0.10},
            {"cote_max": 3.0, "pct": 0.07},
            {"cote_max": 5.0, "pct": 0.05},
            {"cote_max": 10.0, "pct": 0.03},
            {"cote_max": 999, "pct": 0.015},
        ])
        ct = combo["cote_totale"]
        pct = next((t["pct"] for t in tiers if ct <= t["cote_max"]), 0.01)
        stake = bankroll * pct

    elif mode == "kelly_fraction":
        # Kelly fractional : f* = (bp - q) / b ; on divise par kelly_div
        # b = cote - 1, p = WR_combo, q = 1 - p
        kelly_div = sizing.get("kelly_div", 4.0)
        cap_pct = sizing.get("cap_pct", 0.15)
        b = combo["cote_totale"] - 1
        p = combo["wr_combo"]
        q = 1 - p
        f = (b * p - q) / b if b > 0 else 0
        f = max(0, f) / kelly_div
        f = min(f, cap_pct)
        stake = bankroll * f

    elif mode == "ev_proportional":
        # Stake proportionnel à (EV - 1) avec base et cap
        base_pct = sizing.get("base_pct", 0.05)
        ev_factor = sizing.get("ev_factor", 0.30)  # +30% pour chaque +0.10 EV au-dessus de 1.0
        cap_pct = sizing.get("cap_pct", 0.15)
        ev = combo["ev_combo"]
        bonus = max(0, (ev - 1.0)) * (ev_factor / 0.10)
        pct = min(base_pct * (1 + bonus), cap_pct)
        stake = bankroll * pct

    else:
        stake = bankroll * 0.10  # fallback

    if cap:
        stake = min(stake, cap)
    return max(min_stake, round(stake, 2))


# ── Build combos ────────────────────────────────────────────────────────
def build_combos(picks, max_legs, cote_min, cote_max, max_count=20, sort_by="ev"):
    """Construit combos à partir d'une liste de picks (un pick par match max).

    picks : list de picks {match, sport, league, market, selection, cote, wr, ev}
    max_legs : nombre exact de jambes
    cote_min/max : sur la cote totale (multiplicative)
    """
    if max_legs == 1:
        out = [{
            "legs": [p],
            "cote_totale": p["cote"],
            "wr_combo": p["wr"],
            "ev_combo": p["wr"] * p["cote"],
            "n_legs": 1,
        } for p in picks if cote_min <= p["cote"] <= cote_max]
    else:
        # Pour combos N-jambes, faut que les N legs viennent de matches différents
        # On limite la combinatoire en prenant que les top picks
        # Pré-tri par EV (ou WR) pour limiter l'explosion combinatoire
        sorted_picks = sorted(picks, key=lambda p: -p["wr"])[:30]  # cap 30 picks
        seen_matches_combos = []
        out = []
        for combo_legs in combinations(sorted_picks, max_legs):
            matches = {l["match"] for l in combo_legs}
            if len(matches) != max_legs:
                continue  # legs du même match → skip
            cote_t = 1.0
            wr_t = 1.0
            for l in combo_legs:
                cote_t *= l["cote"]
                wr_t *= l["wr"]
            if not (cote_min <= cote_t <= cote_max):
                continue
            out.append({
                "legs": list(combo_legs),
                "cote_totale": round(cote_t, 3),
                "wr_combo": round(wr_t, 4),
                "ev_combo": round(wr_t * cote_t, 3),
                "n_legs": max_legs,
            })

    # Tri
    if sort_by == "ev":
        out.sort(key=lambda c: -c["ev_combo"])
    elif sort_by == "wr":
        out.sort(key=lambda c: -c["wr_combo"])
    elif sort_by == "cote":
        out.sort(key=lambda c: c["cote_totale"])

    return out[:max_count]


# ── Apply strategy ──────────────────────────────────────────────────────
def apply_strategy(strategy, picks_data, bankroll, magic=None, excluded_leagues=None,
                   upcoming_only=False, now_ts=None):
    """Retourne dict avec combos sélectionnés + stakes.
    excluded_leagues : list de substrings (lowercase) — exclut tout pick dont la ligue contient un de ces patterns.
    upcoming_only    : si True, ne garde que les picks dont start_time > now_ts et trie les combos
                       sélectionnés du plus proche au plus lointain (chronologique).
    now_ts           : timestamp de référence (default time.time()).
    """
    import time as _time
    magic = magic or Magic()
    sizing = strategy.get("sizing", {"mode": "flat_pct", "pct": 0.10, "min_stake": 0.5})
    dedup = strategy.get("dedup", "none")
    components = strategy["components"]
    events = picks_data.get("events", [])

    # Extract toutes les sélections magic-able par event
    all_picks = []
    for ev in events:
        all_picks.extend(extract_event_picks(ev, magic))

    # Filtrage par ligues : filtre centralisé (whitelist + pays) + exclusions user
    from picks.league_filter import is_league_ok
    user_excl = None
    if excluded_leagues is None:
        user_excl = [e.lower() for e in WFR_EXCL_DEFAULT]
    elif excluded_leagues:
        user_excl = [e.lower() for e in excluded_leagues if e.strip()]
    all_picks = [p for p in all_picks
                 if is_league_ok(p["sport"], p.get("league",""),
                                 category=p.get("category",""),
                                 excluded_user_leagues=user_excl)]

    # Filtrage prochains matchs uniquement (start_time > now)
    if upcoming_only:
        now_ref = now_ts if now_ts is not None else _time.time()
        all_picks = [p for p in all_picks
                     if p.get("start_time") and p["start_time"] > now_ref]

    used_pick_keys = Counter()
    used_matches = set()
    selected = []

    for ci, comp in enumerate(components):
        # Support `sport` (single) ou `sports` (list, pour combos multi-sport)
        sports_allowed = comp.get("sports") or [comp.get("sport")] if comp.get("sport") else comp.get("sports") or []
        # Alias rétrocompatibilité : "hockey" → "ice-hockey" (nom standard du scrape Sofascore)
        sports_allowed = ["ice-hockey" if s == "hockey" else s for s in sports_allowed]
        sport = sports_allowed[0] if sports_allowed else None
        market = comp.get("market", "1x2")
        # Support market multi-séparé virgule (ex "btts,over_1_5,over_2_5")
        markets_allowed = [m.strip() for m in market.split(",") if m.strip()]
        cote_min = comp["cote_min"]
        cote_max = comp["cote_max"]
        sort_by = comp.get("sort_by", "wr")
        max_combos = comp.get("max_combos", 3)
        min_wr = comp.get("min_wr")
        min_ev = comp.get("min_ev")
        max_legs = comp.get("max_legs", 1)

        # Filtrer picks pour cette composante (peut accepter plusieurs sports + plusieurs markets)
        candidates = [p for p in all_picks
                      if p["sport"] in sports_allowed
                      and p["market"] in markets_allowed
                      and (min_wr is None or p["wr"] >= min_wr)
                      and (min_ev is None or p["ev"] >= min_ev)]

        # Filtre included_leagues (substring match lowercase) — opt-in via strategy JSON
        included_leagues = strategy.get("included_leagues") or comp.get("included_leagues")
        if included_leagues:
            incl_low = [l.lower() for l in included_leagues if l and l.strip()]
            candidates = [p for p in candidates
                          if any(i in (p.get("league") or "").lower() for i in incl_low)]

        # Pour singles, filtrer cote sur le pick. Pour combos, on filtre cote totale plus bas.
        if max_legs == 1:
            candidates = [p for p in candidates if cote_min <= p["cote"] <= cote_max]

        # Build combos
        combos = build_combos(candidates, max_legs, cote_min, cote_max,
                              max_count=max_combos*5, sort_by=sort_by)

        chosen = 0
        for c in combos:
            if chosen >= max_combos:
                break
            legs_keys = [(l["match"], l["selection"]) for l in c["legs"]]
            legs_matches = {l["match"] for l in c["legs"]}

            if dedup == "max1" and any(used_pick_keys[k] >= 1 for k in legs_keys):
                continue
            if dedup == "max2" and any(used_pick_keys[k] >= 2 for k in legs_keys):
                continue
            if dedup == "disjoint" and any(m in used_matches for m in legs_matches):
                continue
            for k in legs_keys:
                used_pick_keys[k] += 1
            used_matches |= legs_matches

            stake = compute_stake(c, bankroll, sizing)
            selected.append({
                **c,
                "stake": stake,
                "potential_gain": round(stake * (c["cote_totale"] - 1), 2),
                "potential_payout": round(stake * c["cote_totale"], 2),
                "component_index": ci,
                "component_label": comp.get("label", f"C{ci+1}: {sport} {market} {cote_min}-{cote_max} {max_legs}j"),
            })
            chosen += 1

    # Si upcoming_only, trie les combos sélectionnés par start_time du leg le plus proche
    if upcoming_only:
        def _combo_st(c):
            sts = [l.get("start_time") for l in c["legs"] if l.get("start_time")]
            return min(sts) if sts else float("inf")
        selected.sort(key=_combo_st)

    total_stake = sum(c["stake"] for c in selected)
    total_potential_gain = sum(c["potential_gain"] for c in selected)
    total_potential_payout = sum(c["potential_payout"] for c in selected)

    # Bankroll si tous gagnent / si tous perdent
    bankroll_all_win = bankroll - total_stake + total_potential_payout
    bankroll_all_lose = bankroll - total_stake

    return {
        "strategy_id": strategy.get("id"),
        "strategy_label": strategy.get("label"),
        "bankroll": bankroll,
        "n_combos": len(selected),
        "total_stake": round(total_stake, 2),
        "stake_pct_bankroll": round(total_stake / bankroll * 100, 1) if bankroll > 0 else 0,
        "total_potential_gain": round(total_potential_gain, 2),
        "total_potential_payout": round(total_potential_payout, 2),
        "bankroll_all_win": round(bankroll_all_win, 2),
        "bankroll_all_lose": round(bankroll_all_lose, 2),
        "sizing_mode": sizing.get("mode"),
        "combos": selected,
        "scraped_at": picks_data.get("scraped_at"),
        "scrape_day": picks_data.get("day"),
    }
