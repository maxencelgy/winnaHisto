"""Engine montante : simule des montantes en mode interday OU intraday.

Mode interday  : 1 palier par jour (cycle dure plusieurs jours)
Mode intraday  : N paliers en 1 seule journée (ordonnés par start_time)
"""
import os, sys, json
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_engine import _get_index, extract_picks

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from picks.league_filter import is_league_ok


def _load_magic(use_oos=True):
    name = "magic_cotes_smart_oos.json" if use_oos else "magic_cotes_smart.json"
    path = os.path.join(ROOT, "datasets", name)
    if not os.path.exists(path):
        path = os.path.join(ROOT, "datasets", "magic_cotes_smart.json")
    with open(path) as f:
        raw = json.load(f)
    out = {"_smart": True}
    for sp, buckets in raw.items():
        if sp == "_smart": continue
        out[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                       for c,info in cotes.items()}
                   for b, cotes in buckets.items()}
    return out


def _gen_days(start, end):
    s = datetime.strptime(start,"%Y-%m-%d").date()
    e = datetime.strptime(end,"%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)


def simulate(strategy, start_date, end_date, mode="interday", initial_stake=10,
              use_oos_magic=True, excluded_leagues=None, included_leagues=None):
    """Simule une montante.
    strategy : dict avec components[0] = {sports, market, cote_min, cote_max, sort_by, min_wr}
                + montante = {n_paliers_target, ...}
    mode : "interday" (1 palier/jour) ou "intraday" (N paliers/jour)
    initial_stake : € de départ par cycle
    excluded_leagues : list de substrings (lowercase) — exclut les ligues correspondantes.
    included_leagues : list de substrings (lowercase) — UNIQUEMENT ces ligues.
    """
    excl = [e.lower() for e in (excluded_leagues or []) if e and e.strip()]
    incl = [i.lower() for i in (included_leagues or []) if i and i.strip()]
    magic = _load_magic(use_oos=use_oos_magic)
    comp = strategy["components"][0]
    montante_cfg = strategy.get("montante", {})
    n_target = montante_cfg.get("n_paliers_target", 5)
    sports = comp.get("sports") or [comp["sport"]]
    markets = comp.get("markets") or [comp.get("market", "1x2")]
    cmin, cmax = comp["cote_min"], comp["cote_max"]
    sort_by = comp.get("sort_by", "wr")
    min_wr = comp.get("min_wr")
    min_ev = comp.get("min_ev")
    legs_per_palier = montante_cfg.get("combo_legs_per_palier") or comp.get("legs_per_palier") or comp.get("max_legs", 1)
    # Charger magic extended si on a des markets non-1x2
    magic_ext = None
    if any(m in ("btts","over_1_5","over_2_5") for m in markets):
        ext_path = os.path.join(ROOT, "datasets",
            "magic_cotes_extended_oos.json" if use_oos_magic else "magic_cotes_extended.json")
        if not os.path.exists(ext_path):
            ext_path = os.path.join(ROOT, "datasets", "magic_cotes_extended.json")
        with open(ext_path) as f:
            magic_ext = json.load(f)
        magic_ext["_smart"] = True

    days = list(_gen_days(start_date, end_date))
    capital = initial_stake
    palier = 0
    cycles_log = []
    n_paliers_won = 0
    n_paliers_total = 0
    total_invested = initial_stake
    final_pnl = 0
    current_cycle_legs = []  # picks du cycle courant (pour debug)

    def reset_cycle(reason):
        nonlocal capital, palier, current_cycle_legs, total_invested, final_pnl
        if reason == "complete":
            final_pnl += capital - initial_stake
        elif reason == "loss":
            final_pnl -= initial_stake
        cycles_log.append({
            "outcome": reason,
            "n_paliers_won": palier if reason == "complete" else palier,
            "final_capital": capital if reason == "complete" else 0,
            "legs": current_cycle_legs[:],
        })
        capital = initial_stake
        palier = 0
        current_cycle_legs = []
        if reason in ("complete", "loss"):
            total_invested += initial_stake

    for d in days:
        idx = _get_index()
        ms = idx.get(d, [])
        ms = [m for m in ms if m["sport"] in sports and is_league_ok(m["sport"], m.get("league",""), category=m.get("category",""), excluded_user_leagues=excl)]
        if incl:
            ms = [m for m in ms if any(i in m.get("league","").lower() for i in incl)]
        if not ms:
            continue
        picks = []
        for mkt in markets:
            ref = magic_ext if mkt in ("btts","over_1_5","over_2_5","over_0_5","1x","x2") else magic
            ps = extract_picks(ms, ref, market=mkt)
            picks.extend(ps)
        picks = [p for p in picks if cmin <= p["odds"] <= cmax]
        if min_wr is not None:
            picks = [p for p in picks if p["wr"] >= min_wr]
        if min_ev is not None:
            picks = [p for p in picks if p["wr"]*p["odds"] >= min_ev]

        # Nouveau : Cross-Validation
        val_mkt = comp.get("validation_market")
        val_wr = comp.get("validation_min_wr")
        if val_mkt and val_wr:
            # On charge le marché de validation pour les mêmes matchs
            ref_val = magic_ext if val_mkt in ("btts","over_1_5","over_2_5") else magic
            v_picks = extract_picks(ms, ref_val, market=val_mkt)
            v_by_m = {vp["match"]: vp["wr"] for vp in v_picks if vp["selection"] in ("Plus de 2.5 buts", "Plus de 1.5 buts", "BTTS Oui", "Oui")}
            picks = [p for p in picks if v_by_m.get(p["match"], 0) >= val_wr]
        # Dédup par (match, selection) pour éviter doubles
        seen_ms = set()
        unique = []
        for p in picks:
            k = (p["match"], p["selection"])
            if k in seen_ms: continue
            seen_ms.add(k)
            unique.append(p)
        picks = unique
        if not picks:
            continue

        # Sort
        if sort_by == "wr": picks.sort(key=lambda p: -p["wr"])
        elif sort_by == "ev": picks.sort(key=lambda p: -p["wr"]*p["odds"])

        # Si combo par palier (legs_per_palier > 1), on aggrège N picks en 1 palier
        def make_palier_pick(picks_for_palier):
            """Combine N picks en 1 'palier' synthétique."""
            if len(picks_for_palier) == 1:
                return picks_for_palier[0]
            cote_t = 1.0
            won_all = True
            matches = []
            sels = []
            sports_p = []
            for p in picks_for_palier:
                cote_t *= p["odds"]
                if not p.get("won", False):
                    won_all = False
                matches.append(p["match"])
                sels.append(p["selection"])
                sports_p.append(p.get("sport", ""))
            return {
                "match": " + ".join(matches),
                "selection": " / ".join(sels),
                "sport": "/".join(set(sports_p)),
                "odds": cote_t,
                "wr": won_all and 1.0 or 0.0,  # placeholder
                "won": won_all,
                "start_time": picks_for_palier[0].get("start_time"),
            }

        if mode == "interday":
            # 1 palier ce jour
            if legs_per_palier > 1 and len(picks) >= legs_per_palier:
                # Dédup par match pour les jambes du combo
                seen_m = set(); ds = []
                for p in picks:
                    if p["match"] in seen_m: continue
                    seen_m.add(p["match"]); ds.append(p)
                if len(ds) < legs_per_palier:
                    continue
                pick = make_palier_pick(ds[:legs_per_palier])
            else:
                pick = picks[0]
            palier += 1
            n_paliers_total += 1
            current_cycle_legs.append({
                "date": d, "match": pick["match"], "selection": pick["selection"],
                "odds": pick["odds"], "wr": pick["wr"], "won": pick.get("won")
            })
            if pick.get("won", False):
                n_paliers_won += 1
                capital = capital * pick["odds"]
                if palier >= n_target:
                    reset_cycle("complete")
            else:
                reset_cycle("loss")

        elif mode in ("intraday", "intraday_wr"):
            # Mode "intraday"     : ordonné chronologiquement (start_time) — orig
            # Mode "intraday_wr"  : trie par WR/EV décroissant, pas par chrono.
            #                       Note : les picks sont déjà triés par WR/EV plus haut (lignes 142-143)
            if mode == "intraday":
                picks_sorted = sorted(picks, key=lambda p: p.get("start_time") or 0)
            else:
                # Garde le tri WR/EV existant — picks est déjà trié plus haut
                picks_sorted = list(picks)
            # Dédup par match (1 pick par match max)
            seen_matches = set()
            picks_unique = []
            for p in picks_sorted:
                if p["match"] in seen_matches: continue
                seen_matches.add(p["match"])
                picks_unique.append(p)
            # Si combo par palier : grouper picks en chunks de legs_per_palier
            if legs_per_palier > 1:
                paliers_picks = []
                i = 0
                while i + legs_per_palier <= len(picks_unique):
                    paliers_picks.append(make_palier_pick(picks_unique[i:i+legs_per_palier]))
                    i += legs_per_palier
                picks_unique = paliers_picks
            # Tenter de monter les paliers dans la journée
            for pick in picks_unique:
                if palier >= n_target: break
                palier += 1
                n_paliers_total += 1
                current_cycle_legs.append({
                    "date": d, "match": pick["match"], "selection": pick["selection"],
                    "odds": pick["odds"], "wr": pick["wr"], "won": pick.get("won")
                })
                if pick.get("won", False):
                    n_paliers_won += 1
                    capital = capital * pick["odds"]
                    if palier >= n_target:
                        reset_cycle("complete")
                        break
                else:
                    reset_cycle("loss")
                    break

    # Stats
    n_complete = sum(1 for c in cycles_log if c["outcome"] == "complete")
    n_loss = sum(1 for c in cycles_log if c["outcome"] == "loss")
    n_total_cycles = n_complete + n_loss
    avg_capital_complete = (sum(c["final_capital"] for c in cycles_log if c["outcome"] == "complete")
                            / max(n_complete, 1))
    return {
        "mode": mode,
        "n_paliers_target": n_target,
        "initial_stake": initial_stake,
        "n_cycles_complete": n_complete,
        "n_cycles_loss": n_loss,
        "n_cycles_total": n_total_cycles,
        "completion_rate": n_complete / max(n_total_cycles, 1),
        "wr_palier": n_paliers_won / max(n_paliers_total, 1),
        "n_paliers_total": n_paliers_total,
        "avg_capital_complete": round(avg_capital_complete, 2),
        "final_pnl": round(final_pnl, 2),
        "total_invested": total_invested,
        "roi": round(final_pnl / max(total_invested, 1) * 100, 2),
        "cycles": cycles_log[-20:],  # 20 derniers pour affichage
    }
