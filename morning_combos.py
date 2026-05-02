#!/usr/bin/env python3
"""
Script matinal — sort 5-10 combinés prêts à parier basés sur les "cotes perfect match"
de l'historique du user croisées avec les matchs Winamax du jour.

Logique :
1. Identifie les cotes (wr ≥ 90%, n ≥ 10, EV > 0) dans ton historique = "cotes perfect"
2. Bonus : triplets exacts (cote + sport + marché) wr ≥ 90%, n ≥ 5
3. Charge le calendar Winamax du jour
4. Pour chaque sélection : check si sa cote tombe sur une cote perfect (±0.02)
5. Génère combinés 2-3 jambes en visant cote totale dans [2.0 ; 5.0] (zone PnL optimale)
6. Output top 10 combinés rankés par EV estimée

Usage :
    python3 morning_combos.py
    python3 morning_combos.py --hist /path/history.csv --cal /path/calendar.csv
    python3 morning_combos.py --top 10 --min-wr 0.90 --min-n 10
"""

import argparse
import csv
import glob
import os
import re
from collections import defaultdict
from itertools import combinations
from pathlib import Path


def fnum(s):
    try:
        return float((s or "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def find_latest(pattern):
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def load_history(path):
    with open(path, encoding="utf-8-sig") as f:
        return [r for r in csv.DictReader(f) if r.get("selection_status") in ("Gagné", "Perdu")]


def load_calendar(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


SPORT_PAT = [
    ("Tennis", r"\b(ATP|WTA|Madrid|Roland|Wimbledon|Open|Set|Simples|Doubles|Challenger|ITF)\b"),
    ("Football", r"\b(Ligue|Liga|Bundesliga|Serie A|Süper|Premier League|Eredivisie|Ekstraklasa|J\d{1,2}|UCL|UEFA|MLS|Eliteserien|Brazil|Libertadores|Copa)\b"),
    ("Basket", r"\b(NBA|EuroLeague|Pro A|Betclic Élite|BNXT|ACB)\b"),
    ("Hockey", r"\b(NHL|KHL|SHL|Liiga|DEL|Magnus|AHL)\b"),
    ("MMA", r"\b(UFC|Bellator|PFL)\b"),
    ("F1", r"\b(F1|Formule|Grand Prix)\b"),
    ("Baseball", r"\b(MLB|NPB|KBO)\b"),
    ("AFL", r"\b(AFL)\b"),
    ("Volley", r"\b(Volley|VNL)\b"),
    ("Handball", r"\b(Handball|EHF|LSH)\b"),
]


def reclassify_sport(row):
    if row.get("sport") and row["sport"] not in ("?", ""):
        return row["sport"]
    txt = f"{row.get('match','')} {row.get('competition','')}"
    for name, pat in SPORT_PAT:
        if re.search(pat, txt, re.I):
            return name
    return "?"


def calibrate_perfect_cotes(hist, min_n=10, min_wr=0.90):
    """Cotes (n>=min_n, wr>=min_wr, EV>0) → 'perfect cotes'."""
    g = defaultdict(lambda: [0, 0])  # cote_str -> [n, won]
    for r in hist:
        o = fnum(r["selection_odds"])
        if not o:
            continue
        k = f"{o:.2f}"
        g[k][0] += 1
        if r["selection_status"] == "Gagné":
            g[k][1] += 1
    perfect = {}
    for k, (n, w) in g.items():
        if n < min_n:
            continue
        wr = w / n
        ev = wr * float(k) - 1
        if wr >= min_wr and ev > 0:
            perfect[float(k)] = {"n": n, "wr": wr, "ev": ev}
    return perfect


def calibrate_triplets(hist, min_n=5, min_wr=0.90):
    g = defaultdict(lambda: [0, 0])
    for r in hist:
        o = fnum(r["selection_odds"])
        if not o:
            continue
        s = (r.get("selection_sport") or "?").strip()
        m = (r.get("selection_market") or "?").strip()
        k = (f"{o:.2f}", s, m)
        g[k][0] += 1
        if r["selection_status"] == "Gagné":
            g[k][1] += 1
    triplets = {}
    for k, (n, w) in g.items():
        if n < min_n:
            continue
        wr = w / n
        if wr >= min_wr and wr * float(k[0]) - 1 > 0:
            triplets[k] = {"n": n, "wr": wr}
    return triplets


def calibrate_bad_sports(hist, min_n=30, max_ev=-0.10):
    g = defaultdict(lambda: [0, 0, 0.0])
    for r in hist:
        o = fnum(r["selection_odds"])
        s = (r.get("selection_sport") or "?").strip()
        if not o:
            continue
        g[s][0] += 1
        if r["selection_status"] == "Gagné":
            g[s][1] += 1
        g[s][2] += o
    bad = set()
    for s, (n, w, so) in g.items():
        if n >= min_n:
            wr = w / n
            ev = wr * (so / n) - 1
            if ev < max_ev:
                bad.add(s)
    return bad


def score_selection(sel, perfect, triplets, bad_sports, tol=0.02):
    """Renvoie (wr, sources) si la sélection match une zone d'edge ; None sinon."""
    o = sel["odds_f"]
    if not o:
        return None
    sport = sel["sport_clean"]
    if sport in bad_sports:
        return None
    market = (sel.get("selection_clean") or "").strip()

    best_wr = None
    sources = []

    # Triplet exact (priorité)
    for (oc_str, sc, mc), v in triplets.items():
        oc = float(oc_str)
        if abs(o - oc) <= 0.005 and sport == sc:
            best_wr = max(best_wr or 0, v["wr"])
            sources.append(f"triplet {sc}/{mc} cote {oc:.2f} : {v['wr']*100:.0f}% n={v['n']}")

    # Cote perfect (±tol)
    for oc, v in perfect.items():
        if abs(o - oc) <= tol:
            best_wr = max(best_wr or 0, v["wr"])
            sources.append(f"cote {oc:.2f} : wr {v['wr']*100:.0f}% n={v['n']} EV{v['ev']*100:+.0f}%")

    if best_wr is None:
        return None
    return best_wr, sources


def build_combos(picks, max_legs=3, min_total_odds=2.0, max_total_odds=5.0,
                 max_combos=10):
    """Génère combinés, filtre par cote totale, classe par EV décroissant."""
    candidates = []
    for n_legs in (2, 3):
        if n_legs > max_legs:
            break
        for combo in combinations(picks, n_legs):
            # pas 2 picks même match
            matches_in_combo = [p["match"] for p in combo]
            if len(set(matches_in_combo)) < n_legs:
                continue
            cote_t = 1.0
            wr_t = 1.0
            for p in combo:
                cote_t *= p["odds_f"]
                wr_t *= p["wr"]
            if cote_t < min_total_odds or cote_t > max_total_odds:
                continue
            ev = wr_t * cote_t - 1
            candidates.append({
                "legs": combo,
                "cote_t": cote_t,
                "wr_t": wr_t,
                "ev": ev,
            })

    candidates.sort(key=lambda c: -c["ev"])

    # Dédupliquer : éviter combos qui partagent ≥ 2 jambes avec un déjà retenu
    selected = []
    for c in candidates:
        keys_c = {(p["match"], p["selection_clean"]) for p in c["legs"]}
        clash = False
        for s in selected:
            keys_s = {(p["match"], p["selection_clean"]) for p in s["legs"]}
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
    ap.add_argument("--hist", default=None)
    ap.add_argument("--cal", default=None)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--min-wr", type=float, default=0.90)
    ap.add_argument("--min-n", type=int, default=10)
    ap.add_argument("--cote-min", type=float, default=2.0)
    ap.add_argument("--cote-max", type=float, default=5.0)
    ap.add_argument("--max-legs", type=int, default=3)
    args = ap.parse_args()

    hist_path = args.hist or find_latest(str(Path.home() / "Downloads" / "winamax-history-*.classified.csv")) \
                          or find_latest(str(Path.home() / "Downloads" / "winamax-history-*.csv"))
    cal_path = args.cal or find_latest(str(Path.home() / "Downloads" / "winamax-calendar-*.csv"))

    if not hist_path or not os.path.exists(hist_path):
        print("Historique introuvable. --hist /path.csv")
        return
    if not cal_path or not os.path.exists(cal_path):
        print("Calendar introuvable. Lance winamax-calendar.js puis donne --cal /path.csv")
        return

    print(f"Historique : {hist_path}")
    print(f"Calendar   : {cal_path}")

    hist = load_history(hist_path)
    print(f"Paris settled : {len(hist)}")

    perfect = calibrate_perfect_cotes(hist, min_n=args.min_n, min_wr=args.min_wr)
    triplets = calibrate_triplets(hist, min_n=5, min_wr=args.min_wr)
    bad_sports = calibrate_bad_sports(hist)
    print(f"Cotes perfect : {len(perfect)} | Triplets : {len(triplets)} | Bad sports : {sorted(bad_sports)}")
    print(f"  Top 5 cotes perfect : ", end="")
    top5 = sorted(perfect.items(), key=lambda x: -x[1]["wr"] * x[0])[:5]
    print(", ".join(f"{c:.2f}({v['wr']*100:.0f}%n={v['n']})" for c, v in top5))

    cal = load_calendar(cal_path)
    for r in cal:
        r["sport_clean"] = reclassify_sport(r)
        r["odds_f"] = fnum(r.get("odds"))
        r["selection_clean"] = re.sub(r"^\d{1,4}", "", r.get("selection") or "").strip()

    # Group selections par match
    matches = defaultdict(list)
    for r in cal:
        if r["odds_f"] and r["odds_f"] >= 1.05:
            matches[r["match"]].append(r)

    # Picks par match : favori si match cote perfect
    picks = []
    for m, lines in matches.items():
        for sel in lines:
            res = score_selection(sel, perfect, triplets, bad_sports)
            if res:
                wr, sources = res
                picks.append({
                    "match": m,
                    "sport_clean": sel["sport_clean"],
                    "competition": sel.get("competition", ""),
                    "selection_clean": sel["selection_clean"],
                    "odds_f": sel["odds_f"],
                    "wr": wr,
                    "sources": sources,
                    "when": sel.get("when", ""),
                    "url": sel.get("url", ""),
                })

    picks.sort(key=lambda p: -(p["wr"] * p["odds_f"] - 1))

    print(f"\n=== {len(picks)} sélections matchent une zone d'edge ===")
    for i, p in enumerate(picks[:15], 1):
        print(f"  {i:>2}. [{p['sport_clean']:<8}] {p['match'][:45]:<45} → {p['selection_clean'][:25]:<25} @ {p['odds_f']:.2f} (wr {p['wr']*100:.0f}%)")

    if not picks:
        print("\n❌ Aucune sélection ne matche les zones d'edge. Élargis avec --min-wr 0.85.")
        return

    combos = build_combos(picks, max_legs=args.max_legs,
                          min_total_odds=args.cote_min, max_total_odds=args.cote_max,
                          max_combos=args.top)

    print(f"\n=== TOP {len(combos)} COMBINÉS DU JOUR ===")
    print(f"Cible cote totale : {args.cote_min} à {args.cote_max} (zone PnL optimale historique)")
    print()
    for i, c in enumerate(combos, 1):
        print(f"{'='*80}")
        print(f"COMBO #{i} — cote totale {c['cote_t']:.2f} | WR estimée {c['wr_t']*100:.1f}% | EV {c['ev']*100:+.1f}%")
        print(f"{'='*80}")
        for j, leg in enumerate(c["legs"], 1):
            print(f"  {j}. [{leg['sport_clean']}] {leg['match']}")
            print(f"     → {leg['selection_clean']} @ {leg['odds_f']:.2f} | wr {leg['wr']*100:.0f}%")
            print(f"     {leg['competition']}  ·  {leg['when']}")
        # Sizing suggéré : 2% bk × 10€ = 0.20€... non, plutôt mise fixe que le user choisit
        print(f"  💰 Mise suggérée : 2-5€ (combo cote {c['cote_t']:.2f} → gain potentiel {2*c['cote_t']:.1f}-{5*c['cote_t']:.1f}€)")
        print()

    print("Note : WR estimée = produit des wr individuelles (indépendance présumée).")
    print("Filtre cote totale 2-5 fondé sur ton analyse combo_analysis.py (zone PnL +782€).")


if __name__ == "__main__":
    main()
