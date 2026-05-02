#!/usr/bin/env python3
"""
Morning combos v2 — utilise un prior MARCHÉ (dataset football-data.co.uk
+ tennis OddsHarvester) au lieu de l'historique perso seul, pour éviter
l'overfit et la surestimation des winrates.

Pipeline :
  1. Charger dataset marché → table cote → wr_marché (n_marché)
  2. Charger historique perso → wr_user à cette cote
  3. Pour chaque sélection du calendar du jour :
       prior = Wilson_lower(wr_marché)
       skill_bonus = max(0, wr_user - wr_marché) si n_user>=20 et écart>5pts
       wr_estimée = prior + skill_bonus  (capé à 0.95)
       Inclure si wr_estimée × cote − 1 > 0
  4. Construire combos 2-3 jambes, cote totale 2.0-5.0, ranking par EV combo
  5. Output top 10 combos

Usage :
    python3 morning_combos_v2.py
    python3 morning_combos_v2.py --top 5 --min-ev 0.05 --cote-min 2 --cote-max 6
"""

import argparse
import ast
import csv
import glob
import math
import os
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path

FD_DIR = "/Users/maxenceleguay/Sites/winnaHisto/datasets/fd"
TENNIS_DIR = "/tmp/oh_dataset"
HIST_GLOB = str(Path.home() / "Downloads" / "winamax-history-*.classified.csv")
CAL_GLOB = str(Path.home() / "Downloads" / "winamax-calendar-*.csv")


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def find_latest(pattern):
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def wilson_lower(won, n, z=1.96):
    if n == 0:
        return 0.0
    p = won / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / denom


def round_cote(o, step=0.01):
    return round(round(o / step) * step, 2)


# ---- Build market prior ----

def build_market_prior_foot():
    """Lit /datasets/fd/*.csv et renvoie cote → [n, won]."""
    g = defaultdict(lambda: [0, 0])
    for path in sorted(glob.glob(os.path.join(FD_DIR, "*.csv"))):
        try:
            with open(path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        for r in rows:
            ftr = r.get("FTR")
            fthg = fnum(r.get("FTHG"))
            ftag = fnum(r.get("FTAG"))
            if ftr is None or fthg is None or ftag is None:
                continue
            for col, won in (("PSH", ftr == "H"), ("PSD", ftr == "D"), ("PSA", ftr == "A"),
                             ("B365H", ftr == "H"), ("B365D", ftr == "D"), ("B365A", ftr == "A")):
                c = fnum(r.get(col))
                if c and c > 1:
                    k = round_cote(c)
                    g[k][0] += 1
                    if won:
                        g[k][1] += 1
            total = fthg + ftag
            for col, won in (("P>2.5", total > 2.5), ("P<2.5", total < 2.5),
                             ("B365>2.5", total > 2.5), ("B365<2.5", total < 2.5)):
                c = fnum(r.get(col))
                if c and c > 1:
                    k = round_cote(c)
                    g[k][0] += 1
                    if won:
                        g[k][1] += 1
    return g


def build_market_prior_tennis():
    """Lit /tmp/oh_dataset/*.csv (OddsHarvester tennis) et complète."""
    g = defaultdict(lambda: [0, 0])
    for path in sorted(glob.glob(os.path.join(TENNIS_DIR, "*.csv"))):
        try:
            with open(path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        except Exception:
            continue
        for r in rows:
            try:
                hs = int(r.get("home_score") or -1)
                as_ = int(r.get("away_score") or -1)
            except (TypeError, ValueError):
                continue
            if hs < 0 or as_ < 0:
                continue
            home_won = hs > as_
            try:
                quotes = ast.literal_eval(r.get("match_winner_market", ""))
            except (ValueError, SyntaxError):
                continue
            if not quotes:
                continue
            # Pinnacle priorité, fallback first available
            ph, pa = None, None
            for q in quotes:
                if q.get("bookmaker_name") in ("Pinnacle", "Pinnacle Sports"):
                    ph = fnum(q.get("home"))
                    pa = fnum(q.get("away"))
                    break
            if not (ph and pa):
                for q in quotes:
                    ph = fnum(q.get("home"))
                    pa = fnum(q.get("away"))
                    if ph and pa:
                        break
            if ph and ph > 1:
                k = round_cote(ph)
                g[k][0] += 1
                if home_won:
                    g[k][1] += 1
            if pa and pa > 1:
                k = round_cote(pa)
                g[k][0] += 1
                if not home_won:
                    g[k][1] += 1
    return g


def merge_priors(*priors):
    out = defaultdict(lambda: [0, 0])
    for p in priors:
        for k, (n, w) in p.items():
            out[k][0] += n
            out[k][1] += w
    return out


# ---- User history ----

def build_user_hist():
    path = find_latest(HIST_GLOB)
    if not path:
        return defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    g_cote = defaultdict(lambda: [0, 0])
    g_triplet = defaultdict(lambda: [0, 0])
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            if r.get("selection_status") not in ("Gagné", "Perdu"):
                continue
            o = fnum(r.get("selection_odds"))
            if not o:
                continue
            won = r["selection_status"] == "Gagné"
            c = round_cote(o)
            g_cote[c][0] += 1
            if won:
                g_cote[c][1] += 1
            sport = (r.get("selection_sport") or "?").strip()
            market = (r.get("selection_market") or "?").strip()
            tk = (c, sport, market)
            g_triplet[tk][0] += 1
            if won:
                g_triplet[tk][1] += 1
    return g_cote, g_triplet


# ---- Sport classifier (calendar fallback) ----

SPORT_PAT = [
    ("Basket", r"\b(NBA|EuroLeague|Pro A|Betclic Élite|BNXT|ACB|Real Madrid|Barcelona Basket)\b"),
    ("Hockey", r"\b(NHL|KHL|SHL|Liiga|DEL|Magnus|AHL)\b"),
    ("MMA", r"\b(UFC|Bellator|PFL)\b"),
    ("F1", r"\b(F1|Formule|Grand Prix)\b"),
    ("Baseball", r"\b(MLB|NPB|KBO)\b"),
    ("AFL", r"\b(AFL)\b"),
    ("Volley", r"\b(VNL|Volley)\b"),
    ("Handball", r"\b(EHF|LSH|Liqui Moly|Starligue|Handball)\b"),
    ("Tennis", r"\b(ATP|WTA|Roland|Wimbledon|Open|Set|Simples|Doubles|Challenger|ITF)\b"),
    ("Football", r"\b(Ligue|Liga|Bundesliga|Serie A|Süper|Premier League|Eredivisie|Ekstraklasa|J\d{1,2}|UCL|UEFA|MLS|Eliteserien|Brazil|Libertadores|Copa)\b"),
    ("Rugby", r"\b(Top 14|Six Nations|Champions Cup|Pro D2|Super Rugby|Hurricanes|Crusaders|Leeds Rhinos)\b"),
]


def reclassify_sport(row):
    if row.get("sport") and row["sport"] not in ("?", ""):
        return row["sport"]
    txt = f"{row.get('match','')} {row.get('competition','')}"
    for name, pat in SPORT_PAT:
        if re.search(pat, txt, re.I):
            return name
    return "?"


def estimate_wr(cote, sport, market, prior_market, hist_cote, hist_triplet,
                tol=0.02, min_n_market=30, min_n_user=20):
    """Renvoie (wr_estimée, wr_lo, sources) ou None.

    Méthode :
      - prior = Wilson_lower(prior_market à cote)
      - bonus = max(0, wr_user - wr_marché) si triplet ou cote_user n suffisants
      - wr = prior + bonus, capé à 0.95
    """
    sources = []
    # 1. wr marché (point + Wilson lo)
    wr_market, n_market = None, 0
    for c_test, (n, w) in prior_market.items():
        if abs(c_test - cote) <= tol:
            n_market += n
            if wr_market is None:
                wr_market = w / n if n else 0
                # fusionne pondéré sur tolerance
    # plus simple : agréger les cotes dans la fenêtre
    n_m, w_m = 0, 0
    for c_test, (n, w) in prior_market.items():
        if abs(c_test - cote) <= tol:
            n_m += n
            w_m += w
    if n_m >= min_n_market:
        wr_market = w_m / n_m
        wr_lo_m = wilson_lower(w_m, n_m)
        sources.append(f"marché {n_m} obs : wr {wr_market*100:.0f}% (Wilson lo {wr_lo_m*100:.0f}%)")
    else:
        wr_lo_m = None

    # 2. Triplet user (cote+sport+marché)
    wr_triplet = None
    n_triplet = 0
    tk = (round_cote(cote), sport, market)
    if tk in hist_triplet:
        nt, wt = hist_triplet[tk]
        if nt >= 5:
            wr_triplet = wt / nt
            n_triplet = nt
            sources.append(f"triplet toi {sport}/{market} cote {cote:.2f}: {wt}/{nt} ({wr_triplet*100:.0f}%)")

    # 3. Cote user
    wr_user = None
    n_user = 0
    for c_test, (n, w) in hist_cote.items():
        if abs(c_test - cote) <= 0.005:
            n_user += n
            wr_user = w / n if n else 0
    if n_user >= min_n_user:
        sources.append(f"toi {n_user} paris cote {cote:.2f}: wr {wr_user*100:.0f}%")
    else:
        wr_user = None

    # Combinaison
    if wr_lo_m is None and wr_user is None and wr_triplet is None:
        return None

    base = wr_lo_m if wr_lo_m is not None else (wr_user or 0)
    bonus = 0
    if wr_triplet is not None and wr_market is not None:
        diff = wr_triplet - wr_market
        if diff > 0.05:
            bonus = min(diff, 0.10)  # cap bonus à +10pts pour rester prudent
            sources.append(f"skill bonus +{bonus*100:.0f}pts (triplet > marché)")
    elif wr_user is not None and wr_market is not None:
        diff = wr_user - wr_market
        if diff > 0.05 and n_user >= 30:
            bonus = min(diff, 0.10)
            sources.append(f"skill bonus +{bonus*100:.0f}pts (user > marché)")

    wr_est = min(0.95, base + bonus)
    wr_lo = base  # garde la version sans bonus comme prudent

    if wr_est * cote - 1 < 0:
        return None  # filtre EV<0

    return wr_est, wr_lo, sources


# ---- Combos builder ----

def build_combos(picks, max_legs=3, cote_min=2.0, cote_max=5.0, max_combos=10):
    candidates = []
    for n_legs in (2, 3):
        if n_legs > max_legs:
            break
        for combo in combinations(picks, n_legs):
            if len({p["match"] for p in combo}) < n_legs:
                continue
            cote_t = 1.0
            wr_t = 1.0
            wr_lo_t = 1.0
            for p in combo:
                cote_t *= p["odds"]
                wr_t *= p["wr"]
                wr_lo_t *= p["wr_lo"]
            if cote_t < cote_min or cote_t > cote_max:
                continue
            ev = wr_t * cote_t - 1
            ev_lo = wr_lo_t * cote_t - 1
            candidates.append({
                "legs": combo,
                "cote_t": cote_t,
                "wr_t": wr_t,
                "wr_lo_t": wr_lo_t,
                "ev": ev,
                "ev_lo": ev_lo,
            })
    candidates.sort(key=lambda c: -c["ev"])  # tri par EV point estimate

    selected = []
    for c in candidates:
        keys_c = {(p["match"], p["selection"]) for p in c["legs"]}
        clash = False
        for s in selected:
            keys_s = {(p["match"], p["selection"]) for p in s["legs"]}
            if len(keys_c & keys_s) >= 2:
                clash = True
                break
        if not clash:
            selected.append(c)
        if len(selected) >= max_combos:
            break
    return selected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cal", default=None)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--cote-min", type=float, default=2.0)
    ap.add_argument("--cote-max", type=float, default=5.0)
    ap.add_argument("--max-legs", type=int, default=3)
    ap.add_argument("--min-ev", type=float, default=0.0,
                    help="EV minimum requis (Wilson lo) sur le combo")
    args = ap.parse_args()

    print("Construction prior marché (foot + tennis)…")
    p_foot = build_market_prior_foot()
    p_tennis = build_market_prior_tennis()
    market = merge_priors(p_foot, p_tennis)
    print(f"  Foot : {sum(n for n, _ in p_foot.values())} obs sur {len(p_foot)} cotes")
    print(f"  Tennis : {sum(n for n, _ in p_tennis.values())} obs sur {len(p_tennis)} cotes")

    hist_cote, hist_triplet = build_user_hist()
    print(f"Historique perso : {sum(n for n, _ in hist_cote.values())} paris settled")

    cal_path = args.cal or find_latest(CAL_GLOB)
    if not cal_path:
        print("Calendar introuvable. Lance winamax-calendar.js puis donne --cal /path.csv")
        return
    print(f"Calendar : {cal_path}")

    with open(cal_path, encoding="utf-8") as f:
        cal = list(csv.DictReader(f))
    for r in cal:
        r["sport_clean"] = reclassify_sport(r)
        r["odds_f"] = fnum(r.get("odds"))
        r["selection_clean"] = re.sub(r"^\d{1,4}", "", r.get("selection") or "").strip()

    matches = defaultdict(list)
    for r in cal:
        if r["odds_f"] and r["odds_f"] >= 1.05:
            matches[r["match"]].append(r)

    picks = []
    for m, lines in matches.items():
        for sel in lines:
            est = estimate_wr(sel["odds_f"], sel["sport_clean"],
                              sel["selection_clean"], market, hist_cote, hist_triplet)
            if est is None:
                continue
            wr, wr_lo, sources = est
            picks.append({
                "match": m,
                "sport": sel["sport_clean"],
                "competition": sel.get("competition", ""),
                "selection": sel["selection_clean"],
                "odds": sel["odds_f"],
                "wr": wr,
                "wr_lo": wr_lo,
                "sources": sources,
                "when": sel.get("when", ""),
                "url": sel.get("url", ""),
            })

    picks.sort(key=lambda p: -(p["wr_lo"] * p["odds"] - 1))
    print(f"\n=== {len(picks)} sélections avec EV ≥ 0 (point estimate) ===")
    for i, p in enumerate(picks[:20], 1):
        print(f"  {i:>2}. [{p['sport']:<8}] {p['match'][:40]:<40} → {p['selection'][:25]:<25} @ {p['odds']:.2f} | "
              f"wr_est {p['wr']*100:.0f}% wr_lo {p['wr_lo']*100:.0f}% EV_lo {(p['wr_lo']*p['odds']-1)*100:+.1f}%")

    if not picks:
        print("\nAucun pick passe les filtres. Le marché est efficient sur ce calendar.")
        return

    combos = build_combos(picks, max_legs=args.max_legs,
                          cote_min=args.cote_min, cote_max=args.cote_max,
                          max_combos=args.top)

    combos = [c for c in combos if c["ev"] >= args.min_ev]

    print(f"\n=== TOP {len(combos)} COMBINÉS (EV_lo ≥ {args.min_ev*100:.0f}%, cote {args.cote_min}-{args.cote_max}) ===\n")
    for i, c in enumerate(combos, 1):
        print(f"--- COMBO #{i} | cote totale {c['cote_t']:.2f} | "
              f"WR estimée {c['wr_t']*100:.0f}% (lo {c['wr_lo_t']*100:.0f}%) | "
              f"EV {c['ev']*100:+.1f}% (lo {c['ev_lo']*100:+.1f}%) ---")
        for j, leg in enumerate(c["legs"], 1):
            print(f"  {j}. [{leg['sport']}] {leg['match']}")
            print(f"     → {leg['selection']} @ {leg['odds']:.2f}  "
                  f"(wr_est {leg['wr']*100:.0f}%, lo {leg['wr_lo']*100:.0f}%)")
            for s in leg["sources"][:2]:
                print(f"       · {s}")
        print()


if __name__ == "__main__":
    main()
