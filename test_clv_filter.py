#!/usr/bin/env python3
"""
Test CLV filter — comparaison cote_winamax vs cote_pinnacle_devig sur 10 matchs récents.

Workflow :
    1. Charge datasets/pinnacle_odds.json (créé par pinnacle_scraper.py)
    2. Charge events Sofascore upcoming via morning_live (proxy pour cotes Winamax si live)
    3. Pour chaque event Sofascore, fuzzy match avec Pinnacle event
    4. De-vig Pinnacle, calcule EV multiplier vs cote affichée Winamax/Sofascore
    5. Affiche tableau : match | cote_wina | p_pinn | EV | passe filtre 5%

Usage :
    python3 test_clv_filter.py                      # 10 matchs foot upcoming
    python3 test_clv_filter.py --sport tennis       # tennis
    python3 test_clv_filter.py --threshold 1.03     # seuil 3% au lieu de 5%
    python3 test_clv_filter.py --max 30             # 30 matchs

Pré-requis :
    - pinnacle_scraper.py a tourné au moins une fois et a peuplé datasets/pinnacle_odds.json
    - Si pas de pinnacle_odds.json, le script propose de le générer.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from clv_devig import (
    power_devig,
    logarithmic_devig,
    multiplicative_devig,
    margin,
    ev_multiplier,
    filter_clv_value,
    find_matching,
)

PINNACLE_PATH = "/Users/maxenceleguay/Sites/winnaHisto/datasets/pinnacle_odds.json"


def load_pinnacle():
    if not os.path.exists(PINNACLE_PATH):
        print(f"❌ {PINNACLE_PATH} introuvable.")
        print(f"   Lance d'abord : python3 pinnacle_scraper.py --max-events 30")
        sys.exit(1)
    with open(PINNACLE_PATH) as f:
        data = json.load(f)
    captured = data.get("captured_at", "?")
    events = data.get("events", [])
    print(f"📂 Pinnacle cotes capturées le {captured} ({len(events)} events)")
    return events


def load_sofa_upcoming(sport, max_events):
    """Récupère cotes Sofascore upcoming (proxy de Winamax pré-match) pour comparaison."""
    try:
        from morning_live import list_today_events, fetch_event_odds
    except ImportError as e:
        print(f"❌ Import morning_live impossible : {e}")
        sys.exit(1)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    events = list_today_events(sport, today)
    print(f"📅 Sofascore {sport} aujourd'hui : {len(events)} events")
    out = []
    for e in events[:max_events]:
        odds = fetch_event_odds(e)
        if odds:
            out.append(odds)
    return out


def compare(pinnacle_events, sofa_events, threshold=1.05, devig_method="power"):
    """Imprime tableau comparatif. Méthode de-vig configurable."""
    devig_fn = {
        "power": power_devig,
        "log": logarithmic_devig,
        "mult": multiplicative_devig,
    }[devig_method]

    print(f"\n=== Comparaison CLV (threshold {threshold}, devig {devig_method}) ===\n")
    print(f"{'Match':45s} {'Side':6s} {'C_wina':>7s} {'C_pinn':>7s} {'p_pinn':>7s} {'EV':>6s} {'Pass?':>6s}")
    print("-" * 95)

    matched = 0
    passed = 0
    for sofa in sofa_events:
        target = {
            "home": sofa.get("home"),
            "away": sofa.get("away"),
            "starts": sofa.get("startTime") or sofa.get("startsAt") or sofa.get("kickoff"),
        }
        # morning_live n'inclut pas startTime — on fallback sur date du jour si manquant
        if not target["starts"]:
            target["starts"] = datetime.now(timezone.utc).isoformat()

        pinn = find_matching(pinnacle_events, target, tol_minutes=180, min_similarity=0.65)
        if not pinn or not pinn.get("moneyline"):
            continue
        matched += 1

        ml = pinn["moneyline"]
        # Construit liste cotes pour de-vig (3-way si draw, sinon 2-way)
        if "draw" in ml:
            pinn_odds = [ml.get("home"), ml.get("draw"), ml.get("away")]
            labels = [("Home", "odds_1", "home"), ("Draw", "odds_x", "draw"), ("Away", "odds_2", "away")]
        else:
            pinn_odds = [ml.get("home"), ml.get("away")]
            labels = [("Home", "odds_1", "home"), ("Away", "odds_2", "away")]

        if not all(pinn_odds):
            continue
        probs = devig_fn(pinn_odds)
        if not probs:
            continue

        match_str = f"{sofa.get('home')} vs {sofa.get('away')}"[:43]
        for i, (label, wina_field, pinn_key) in enumerate(labels):
            c_wina = sofa.get(wina_field)
            c_pinn = ml.get(pinn_key)
            p = probs[i]
            if not c_wina:
                continue
            ev = ev_multiplier(c_wina, p)
            if ev is None:
                continue
            ok = filter_clv_value(c_wina, p, threshold=threshold)
            if ok:
                passed += 1
            mark = "✓" if ok else "·"
            print(f"{match_str:45s} {label:6s} {c_wina:>7.2f} {c_pinn:>7.2f} {p:>7.3f} {ev:>6.3f} {mark:>6s}")

    print("-" * 95)
    print(f"\nRécap : {matched}/{len(sofa_events)} matchs Sofascore matchés avec Pinnacle.")
    print(f"        {passed} picks passent le filtre CLV ≥ {threshold}.")
    if matched == 0:
        print("\n⚠ Aucun match. Vérifications :")
        print("   - pinnacle_odds.json a bien des moneylines parsées ?")
        print("   - Les events Pinnacle et Sofascore se chevauchent en horaire ?")
        print("   - Tester avec --tol 360 (6h) si fuseaux décalés")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sport", default="football",
                    choices=["football", "basketball", "tennis", "ice-hockey", "baseball"])
    ap.add_argument("--max", type=int, default=10, help="Nombre max events Sofascore à comparer")
    ap.add_argument("--threshold", type=float, default=1.05, help="Seuil EV pour value (default 1.05)")
    ap.add_argument("--devig", default="power", choices=["power", "log", "mult"])
    args = ap.parse_args()

    pinnacle = load_pinnacle()
    if args.sport != "all":
        pinnacle = [e for e in pinnacle if e.get("sport") == args.sport]
        print(f"   filtré sport={args.sport} : {len(pinnacle)} events Pinnacle")

    sofa = load_sofa_upcoming(args.sport, args.max)
    if not sofa:
        print("❌ Aucun event Sofascore. Pas de cotes upcoming aujourd'hui ?")
        sys.exit(1)

    compare(pinnacle, sofa, threshold=args.threshold, devig_method=args.devig)


if __name__ == "__main__":
    main()
