#!/usr/bin/env python3
"""Interface web simple pour les combos magiques du jour."""

import json
import os
import sys
from datetime import date
from pathlib import Path

# Importe les fonctions de morning_live.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from morning_live import (
    load_magic, list_today_events, fetch_event_odds, extract_picks, build_combos
)
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import Flask, jsonify, render_template, request

app = Flask(__name__, template_folder="templates", static_folder="static")


@app.route("/")
def home():
    from flask import make_response
    resp = make_response(render_template("index.html"))
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@app.route("/api/magic-cotes")
def api_magic():
    """Renvoie cotes magiques flat (sport→cote→wr) pour l'UI."""
    flat_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes.json"
    if os.path.exists(flat_path):
        with open(flat_path) as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route("/api/magic-cotes-smart")
def api_magic_smart():
    """Renvoie cotes magiques par bucket (sport→bucket→cote→wr)."""
    smart_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_smart.json"
    if os.path.exists(smart_path):
        with open(smart_path) as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route("/api/backtest")
def api_backtest():
    from backtest_engine import run_backtest, run_backtest_period
    cote_min = float(request.args.get("cote_min", 2.0))
    cote_max = float(request.args.get("cote_max", 5.0))
    max_legs = int(request.args.get("max_legs", 3))
    top = int(request.args.get("top", 5))
    sort_by = request.args.get("sort_by", "ev")
    stake = float(request.args.get("stake", 10.0))
    sports_filter = request.args.get("sports", "").split(",")
    sports_filter = [s for s in sports_filter if s] or None
    min_ev = request.args.get("min_ev")
    min_ev = float(min_ev) if min_ev else None
    min_wr = request.args.get("min_wr")
    min_wr = float(min_wr) if min_wr else None
    rigorous = request.args.get("rigorous", "0") in ("1", "true", "yes")
    magic = load_magic()

    end_date = request.args.get("end_date")
    target_date = request.args.get("date")

    common_kwargs = dict(max_legs=max_legs, cote_min=cote_min, cote_max=cote_max,
                        max_combos=top, sort_by=sort_by, stake=stake,
                        sports_filter=sports_filter, min_ev=min_ev, min_wr=min_wr,
                        rigorous=rigorous)

    if end_date and target_date and end_date != target_date:
        result = run_backtest_period(target_date, end_date, magic, **common_kwargs)
        result["mode"] = "period"
    else:
        result = run_backtest(target_date, magic, **common_kwargs)
        result["mode"] = "single"
    return jsonify(result)


HYBRID_PRESETS = {
    "H3": {
        "label": "H3 — SAFE + 2×EV3j multi (3 combos/j) [+137% ROI]",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 2},
        ],
    },
    "H5": {
        "label": "H5 — 2×EV3j fb + 1×EV4j multi (3 combos/j) [+200% ROI]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
    },
    "H7": {
        "label": "H7 — 2×EV3j fb + 2×EV4j multi (4 combos/j) [+225% ROI]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 2},
        ],
    },
    "H8": {
        "label": "H8 — 2×EV3j fb + 1×EV4j + 1×EV5j multi (4 combos/j) [+295% ROI ⭐]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 20.0, "cote_max": 100.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
    },
    "H8_cote8": {
        "label": "H8_cote8 — H8 mais EV3j cote 2-8 (4 combos/j) [+307% ROI, +11pts vs H8 ✓]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 8.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 20.0, "cote_max": 100.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
    },
    "H9": {
        "label": "H9 — H8 + 1×EV6j multi 50-300 (5 combos/j) [+368% ROI ⭐⭐]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 20.0, "cote_max": 100.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 6, "cote_min": 50.0, "cote_max": 300.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
    },
    "H9_div": {
        "label": "H9_div — H9 mais aucun pick partagé entre combos (5 combos/j) [diversifié = drawdown réduit]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 20.0, "cote_max": 100.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 6, "cote_min": 50.0, "cote_max": 300.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "H_daily": {
        "label": "H_daily — 5×WR2j safe + 2×WR3j (74% jours+ , ROI +27%/mois)",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["football", "basketball"], "max_combos": 5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 4.0, "sort_by": "wr",
             "sports": ["football", "basketball"], "max_combos": 2},
        ],
    },
    "H_daily_boost": {
        "label": "H_daily_boost — H_daily + 1×EV3j (71% jours+ , ROI +35%/mois) ⭐",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["football", "basketball"], "max_combos": 5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 4.0, "sort_by": "wr",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
        ],
    },
    "H_balance": {
        "label": "H_balance — 4×WR2j + 1×EV3j + 1×EV4j (ROI +70%/mois mais corrélation cachée)",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football", "basketball"], "max_combos": 4},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
    },
    "Foot_over_1_5_focused": {
        "label": "Foot_over_1_5_focused — 4 singles Over 1.5 buts cote 1.4-1.8 foot only [walk-forward OOS : +717€/+354€ sem, EV+ stable mais modeste ⭐]",
        "components": [
            {"max_legs": 1, "cote_min": 1.40, "cote_max": 1.80, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4, "market": "over_1_5+plus"},
        ],
        "dedup": "max1",
    },
    "Foot_safe_18_21": {
        "label": "Foot_safe_18_21 — 4 singles foot 1x2 cote 1.85-2.10 sort EV [edges 8 ans : TOP5/UEFA/Brasileirão A cote moyenne, n>100 buckets]",
        "components": [
            {"max_legs": 1, "cote_min": 1.85, "cote_max": 2.10, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4},
        ],
        "dedup": "max1",
    },
    "Foot_outsiders_4_6": {
        "label": "Foot_outsiders_4_6 — 3 singles foot 1x2 cote 4-6 sort EV [edges persistantes : LaLiga 2 / Ligue 2 / Serie B / Brasileirão B, EV +30%]",
        "components": [
            {"max_legs": 1, "cote_min": 4.0, "cote_max": 6.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 3},
        ],
        "dedup": "max1",
    },
    "Foot_dual_edge_8ans": {
        "label": "Foot_dual_edge_8ans — combos 2j (1× cote 1.85-2.10 + 1× cote 4-6) [exploite les 2 edges persistantes simultanément]",
        "components": [
            {"max_legs": 2, "cote_min": 7.4, "cote_max": 12.6, "sort_by": "ev",
             "sports": ["football"], "max_combos": 3},
        ],
        "dedup": "max1",
    },
    "Basket_persistent_edge": {
        "label": "Basket_persistent_edge — 2 singles basket cote 2.5-3.5 sort EV [BBL/Euroleague edges 8 ans]",
        "components": [
            {"max_legs": 1, "cote_min": 2.5, "cote_max": 3.5, "sort_by": "ev",
             "sports": ["basketball"], "max_combos": 2},
        ],
        "dedup": "max1",
    },
    "Multi_8ans_persistent": {
        "label": "Multi_8ans_persistent — 4 foot safe 1.85-2.10 + 2 foot outsiders 4-6 + 2 basket 2.5-3.5 [combo des 3 edges 8 ans]",
        "components": [
            {"max_legs": 1, "cote_min": 1.85, "cote_max": 2.10, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4},
            {"max_legs": 1, "cote_min": 4.0, "cote_max": 6.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 1, "cote_min": 2.5, "cote_max": 3.5, "sort_by": "ev",
             "sports": ["basketball"], "max_combos": 2},
        ],
        "dedup": "max1",
    },
    "Survivor_over25_22_30": {
        "label": "Survivor_over25_22_30 — 4 singles Over 2.5 buts foot cote 2.2-3.0 [walk-forward S1-26 OOS strict 8 ans : +472€, série 4j ⭐⭐]",
        "components": [
            {"max_legs": 1, "cote_min": 2.20, "cote_max": 3.00, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4, "market": "over_2_5+plus"},
        ],
        "dedup": "max1",
    },
    "Survivor_over15_13_155": {
        "label": "Survivor_over15_13_155 — 4 singles Over 1.5 buts foot cote 1.30-1.55 [+397€ OOS strict 8 ans, série 4j ⭐]",
        "components": [
            {"max_legs": 1, "cote_min": 1.30, "cote_max": 1.55, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4, "market": "over_1_5+plus"},
        ],
        "dedup": "max1",
    },
    "Survivor_basket_21_25": {
        "label": "Survivor_basket_21_25 — 4 singles basket 1x2 cote 2.10-2.50 [+318€ OOS strict 8 ans, série 4j]",
        "components": [
            {"max_legs": 1, "cote_min": 2.10, "cote_max": 2.50, "sort_by": "ev",
             "sports": ["basketball"], "max_combos": 4},
        ],
        "dedup": "max1",
    },
    "Survivor_hockey_125_15": {
        "label": "Survivor_hockey_125_15 — 4 singles hockey 1x2 cote 1.25-1.50 sort WR [+304€ OOS strict, série 2j ⭐⭐⭐ DD réduit]",
        "components": [
            {"max_legs": 1, "cote_min": 1.25, "cote_max": 1.50, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 4},
        ],
        "dedup": "max1",
    },
    "Survivor_btts_oui": {
        "label": "Survivor_btts_oui — 4 singles BTTS Oui foot cote 1.90-2.30 [+292€ OOS strict 8 ans, série 4j]",
        "components": [
            {"max_legs": 1, "cote_min": 1.90, "cote_max": 2.30, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4, "market": "btts+oui"},
        ],
        "dedup": "max1",
    },
    "Survivor_MEGA": {
        "label": "Survivor_MEGA — 6 stratégies combinées (Over 1.5/2.5 + basket + hockey + BTTS) dedup max1 [théorique +2100€ OOS si pas de chevauchement combos]",
        "components": [
            {"max_legs": 1, "cote_min": 1.25, "cote_max": 1.50, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 4},
            {"max_legs": 1, "cote_min": 2.20, "cote_max": 3.00, "sort_by": "ev",
             "sports": ["football"], "max_combos": 3, "market": "over_2_5+plus"},
            {"max_legs": 1, "cote_min": 1.30, "cote_max": 1.55, "sort_by": "ev",
             "sports": ["football"], "max_combos": 3, "market": "over_1_5+plus"},
            {"max_legs": 1, "cote_min": 2.10, "cote_max": 2.50, "sort_by": "ev",
             "sports": ["basketball"], "max_combos": 3},
            {"max_legs": 1, "cote_min": 1.85, "cote_max": 2.20, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2, "market": "over_2_5+plus"},
            {"max_legs": 1, "cote_min": 1.90, "cote_max": 2.30, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2, "market": "btts+oui"},
        ],
        "dedup": "max1",
    },
    "Foot_mix_3j_over15": {
        "label": "Foot_mix_3j_over15 — 3 combos 3j MIX (Over 1.5 + 1x2 safe Home/Away) cote totale 2.5-5.0 [walk-forward OOS : +4423€/+3166€ sem, série rouge 3j max ⭐⭐⭐⭐]",
        "components": [
            {"max_legs": 3, "cote_min": 2.5, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 3, "market": "over_1_5+plus,1x2-nul"},
        ],
        "dedup": "max1",
    },
    "Foot_mix_2j_over15": {
        "label": "Foot_mix_2j_over15 — 4 combos 2j MIX (Over 1.5 + 1x2 safe) cote totale 1.7-3.0 [walk-forward OOS : +3318€/+2424€ sem, série 4-5j ⭐⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.7, "cote_max": 3.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 4, "market": "over_1_5+plus,1x2-nul"},
        ],
        "dedup": "max1",
    },
    "Multi_full_with_Over_1_5": {
        "label": "Multi_full_with_Over_1_5 — Multi_full_BTTS_optimal + 2 singles Over 1.5 cote 1.4-1.8 (×0.8) [+90€/mois additionnel modeste]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2, "stake_multiplier": 1.5},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2, "stake_multiplier": 1.5},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1, "stake_multiplier": 1.5},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1, "stake_multiplier": 1.5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2, "stake_multiplier": 1.2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1, "stake_multiplier": 0.8},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1, "stake_multiplier": 0.5},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.5, "sort_by": "ev",
             "sports": ["football"], "max_combos": 1, "stake_multiplier": 0.8, "market": "btts"},
            {"max_legs": 1, "cote_min": 1.40, "cote_max": 1.80, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2, "stake_multiplier": 0.8, "market": "over_1_5"},
        ],
        "dedup": "max1",
    },
    "Multi_full_BTTS_optimal": {
        "label": "Multi_full_BTTS_optimal — multipliers calibrés (safe ×1.5, EV4j ×0.8, EV5j ×0.5, BTTS ×0.8) [DD réduit, PnL préservé]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2, "stake_multiplier": 1.5},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2, "stake_multiplier": 1.5},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1, "stake_multiplier": 1.5},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1, "stake_multiplier": 1.5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2, "stake_multiplier": 1.2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1, "stake_multiplier": 0.8},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1, "stake_multiplier": 0.5},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.5, "sort_by": "ev",
             "sports": ["football"], "max_combos": 1, "stake_multiplier": 0.8, "market": "btts"},
        ],
        "dedup": "max1",
    },
    "Mix_diversified": {
        "label": "Mix_diversified — 2 ultra-safe + 4 safe + 2 EV3j + 1 EV4j + 1 BTTS (10 combos/j) [worst case minimisé : -15% PnL mais DD réduit -48 à -77€ tous semestres ⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["football"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.5, "sort_by": "ev",
             "sports": ["football"], "max_combos": 1, "market": "btts"},
        ],
        "dedup": "max1",
    },
    "Multi_full_BTTS": {
        "label": "Multi_full_BTTS — Multi_full + 2 picks BTTS foot (PnL +24% sur 5 sem, mais DD +54% ⚠️ variance plus élevée)",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.5, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2, "market": "btts"},
        ],
        "dedup": "max1",
    },
    "Multi_3stable": {
        "label": "Multi_3stable — Multi_full restreint à foot+basket+hockey (sports POSITIFS sur 5/5 semestres) [-8% PnL, série rouge réduite parfois -2 à -3j]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 2},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey"], "max_combos": 1},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Sandwich_stable": {
        "label": "Sandwich_stable — 6 safe + 5 EV3j 2-3 + 1 EV4j 5-10 (12 combos/j) [Winamax FR : +500-650€/mois sem, série 4-10j sem ⚖️]",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 1.8, "sort_by": "wr",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 6},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 3.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 5},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 10.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_safe_ext": {
        "label": "Multi_safe_ext — 9 safe multi-sport (3f+3b+2t+1h) [Winamax FR : +218€/mois, 77% jours+, série 2j ⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_12safe": {
        "label": "Multi_12safe — 12 safe multi-sport (3+3+3+2+1) [Winamax FR : +168€/mois, 84% jours+, série 2j ⭐⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 1.8, "sort_by": "wr",
             "sports": ["football"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 1.8, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 1.8, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["baseball"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_full": {
        "label": "Multi_full — 6 safe multi-sport + 2 EV3j + 1 EV4j + 1 EV5j (10 combos/j) [Winamax FR : +1593€/mois, walk-forward +66% ROI/semestre ⭐⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_wide_pro": {
        "label": "Multi_wide_pro — 6 safe (cote large) + EV3j + EV4j + EV5j (10 combos/j) [Winamax FR : +1819€/mois, +61% ROI/sem]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["football"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Foot_pro_lottery": {
        "label": "Foot_pro_lottery — 5 safe + 2 EV3j + 1 EV4j + 1 EV5j foot only [Winamax FR : +1121€/mois, walk-forward +57% ROI/semestre ⭐⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 1},
            {"max_legs": 5, "cote_min": 15.0, "cote_max": 60.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Foot_NBA_pro": {
        "label": "Foot_NBA_pro — 4 foot + 3 NBA safe + 2 EV3j + 1 EV4j (Winamax FR : +910€/mois, 65% jours+)",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 4},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 3},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Foot_pro": {
        "label": "Foot_pro — 8 combos foot only (5 safe + 2 EV3j + 1 EV4j) [Winamax FR : +717€/mois, 61% jours+, série 3j ⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 5},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Hyper_loose": {
        "label": "Hyper_loose — 5 fav par sport 1.1-1.7 + EV3j + EV4j (Winamax FR : +910€/mois, 52% jours+)",
        "components": [
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.7, "sort_by": "wr",
             "sports": ["football"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.7, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.7, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.7, "sort_by": "wr",
             "sports": ["baseball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.7, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Hyper_massive": {
        "label": "Hyper_massive — 3 fav par sport cote 1.05-1.5 (Winamax FR : 89% jours+, série 1j, gains modérés)",
        "components": [
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.5, "sort_by": "wr",
             "sports": [s], "max_combos": 3}
            for s in ["football", "basketball", "ice-hockey", "baseball", "tennis"]
        ],
        "dedup": "max1",
    },
    "Hyper_pro": {
        "label": "Hyper_pro — 5 ultra-safe + 1×EV3j + 1×EV4j (7 combos/j) [+1205€/mois, 65% jours+, série rouge 3j ⭐⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["football"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["baseball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
            {"max_legs": 4, "cote_min": 5.0, "cote_max": 15.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Iron_2j": {
        "label": "Iron_2j — 9 combos foot+basket+hockey cote 1.1-1.4 [Winamax FR : SÉRIE ROUGE ≤ 2j garantie sur 5 semestres ✓ — mais +6€/mois seulement]",
        "components": [
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.4, "sort_by": "wr",
             "sports": ["football"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.4, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.1, "cote_max": 1.4, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 3},
        ],
        "dedup": "max1",
    },
    "Hyper_5sports": {
        "label": "Hyper_5sports — 1 par sport cote 1.05-1.3 (ultra-safe) [88% jours+, série rouge max 2j ⭐⭐⭐]",
        "components": [
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["football"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["baseball"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.05, "cote_max": 1.3, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_10": {
        "label": "Multi_10 — 10 combos 2j safe multi-sports (cote 1.3-2) [67% jours+, série rouge 3j max, ROI +178€/mois]",
        "components": [
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 3},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["baseball"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_safe": {
        "label": "Multi_safe — 1 par sport (2f+2b+2t+1h, dédup) [DD 38€, volat 15€/j ⭐ courbe ultra-lisse]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.5, "sort_by": "wr",
             "sports": ["ice-hockey"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "Multi_balance": {
        "label": "Multi_balance — 2f+2b+1t safe + 1×EV3j fb (dédup) [+543€/mois, DD 63€ ⭐⭐ best lisse + gains]",
        "components": [
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["football"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.4, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["basketball"], "max_combos": 2},
            {"max_legs": 2, "cote_min": 1.3, "cote_max": 2.0, "sort_by": "wr",
             "sports": ["tennis"], "max_combos": 1},
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
        ],
        "dedup": "max1",
    },
    "H_stable": {
        "label": "H_stable — 2×EV3j + 3×EV4j multi (4 combos/j) [+258% ROI, std 36pts ⚖️]",
        "components": [
            {"max_legs": 3, "cote_min": 2.0, "cote_max": 5.0, "sort_by": "ev",
             "sports": ["football", "basketball"], "max_combos": 1},
            {"max_legs": 4, "cote_min": 10.0, "cote_max": 50.0, "sort_by": "ev",
             "sports": ["football", "basketball", "ice-hockey", "baseball", "tennis"],
             "max_combos": 3},
        ],
    },
}


def _kelly_fraction(p, c):
    if c <= 1:
        return 0.0
    return max(0.0, (p * (c - 1) - (1 - p)) / (c - 1))


def _compute_stake(sizing_mode, bankroll, base_stake, kelly_div, cap_pct, stake_cap_abs, p, c, bankroll0=None):
    """Calcule la mise selon le mode de sizing.
    flat_pct: mise = bankroll * (base_stake / bankroll0)
      → mise SCALE proportionnellement avec la bankroll (monte si BR↑, descend si BR↓).
      → BR=BR0 → mise=base_stake. BR=2×BR0 → mise=2×base_stake. BR=BR0/2 → mise=base_stake/2.
      → utiliser stake_cap_abs pour limiter la mise max (réalisme bookmaker).
    """
    if sizing_mode == "flat":
        s = base_stake
    elif sizing_mode == "flat_pct":
        if bankroll0 and bankroll0 > 0:
            s = bankroll * (base_stake / bankroll0)
        else:
            s = bankroll * (cap_pct / 100.0)
    elif sizing_mode == "kelly":
        f = _kelly_fraction(p, c) / max(kelly_div, 1)
        f = min(f, cap_pct / 100.0)
        s = bankroll * f
    else:
        s = base_stake
    s = max(0.01, s)
    if stake_cap_abs > 0:
        s = min(s, stake_cap_abs)
    return s


# Tags qualité des presets
# - "validated_oos" : performance confirmée OOS strict (calibration train < 2026)
# - "marginal_oos" : performance OOS faible mais non négative
# - "negative_oos" : performance OOS négative
# - "repaint" : anciens chiffres inflated par data leakage, vraie perf inconnue/marginale
PRESET_QUALITY = {
    "Foot_mix_3j_over15": ("validated_oos", "✅ +18% ROI strict OOS"),
    "Foot_mix_2j_over15": ("validated_oos", "✅ +13% ROI strict OOS"),
    "Foot_over_1_5_focused": ("validated_oos", "✅ +9% ROI strict OOS, DD réduit"),
    "Multi_full_with_Over_1_5": ("marginal_oos", "🟡 +2.6% ROI strict OOS"),
    "Multi_full_BTTS_optimal": ("marginal_oos", "🟡 +1.6% ROI strict OOS (était repaint à +38%)"),
    "Multi_full": ("marginal_oos", "🟡 +2.2% ROI strict OOS (était repaint)"),
    "Multi_safe_ext": ("marginal_oos", "🟡 +0.9% ROI strict OOS"),
    "Multi_12safe": ("negative_oos", "🔴 −2.1% ROI strict OOS — déconseillé"),
    "Hyper_5sports": ("negative_oos", "🔴 −2.2% ROI strict OOS"),
    "Iron_2j": ("marginal_oos", "🟡 +1.9% ROI strict OOS"),
}

@app.route("/api/backtest-presets")
def api_presets():
    out = {}
    for k, v in HYBRID_PRESETS.items():
        quality, quality_note = PRESET_QUALITY.get(k, ("repaint", "⚠️ non re-validé strict OOS, perf historique probablement inflated"))
        out[k] = {
            "label": v["label"],
            "components": v["components"],
            "dedup": v.get("dedup", "none"),
            "quality": quality,
            "quality_note": quality_note,
        }
    return jsonify(out)


VALID_SPORTS = {"football", "basketball", "ice-hockey", "baseball", "tennis"}
VALID_SORT = {"ev", "wr", "cote"}

# Whitelist leagues dispos sur Winamax / Betclic / Unibet (FR).
# Format : sport -> list de patterns substring (case-insensitive). Match si la string league
# contient au moins un des patterns. Refuse les "Doubles", "Qualifying", "U23", "Reserve".
WINAMAX_LEAGUES = {
    "football": [
        "premier league", "laliga", "la liga", "serie a", "bundesliga", "ligue 1",
        "championship", "laliga 2", "la liga 2", "serie b", "bundesliga 2", "ligue 2",
        "champions league", "europa league", "conference league", "uefa",
        "eredivisie", "liga portugal", "pro league", "süper lig", "premier liga",
        "trendyol süper", "russian premier",
        "mls", "liga mx", "brasileirão série a", "brasileirao série a", "primera división",
        "coupe de france", "fa cup", "copa del rey", "coppa italia", "dfb-pokal",
        "world cup", "euro 2", "copa america", "africa cup",
    ],
    "basketball": [
        "nba", "wnba", "euroleague", "eurocup", "betclic élite", "pro a",
        "acb", "liga endesa", "lega basket", "serie a", "bbl",
        "champions league",
    ],
    "ice-hockey": [
        "nhl", "khl", "shl", "liiga", "ligue magnus", "del", "national league",
        "extraliga", "elite league", "swiss",
    ],
    "baseball": [
        "mlb",
    ],
    "tennis": [
        # ATP / WTA Tour seulement (pas ITF, pas UTR, pas Challenger basique, pas Doubles, pas Qualifying)
        "atp", "wta", "grand slam", "masters",
        # Tournois majeurs par nom
        "australian open", "roland garros", "wimbledon", "us open",
        "miami", "indian wells", "monte carlo", "madrid", "rome", "cincinnati",
        "shanghai", "paris masters",
    ],
}

REJECT_PATTERNS = ["doubles", "qualifying", "u23", "u21", "u19", "u18", "u17", "reserve",
                   "youth", "women, qualif", "men, qualif", "challenger round",
                   "regionalliga", "national league" + ",", "serie c", "série c",
                   "i-league", "k league 2", "league 1, championship",
                   "championship round", "knockout stage qualifying",
                   "primera b nacional", "next pro", "utr ", "ptt ", "exhibition"]


def _is_league_allowed(sport, league):
    """Renvoie True si la league est probablement dispo sur Winamax/Betclic/Unibet FR."""
    if not league:
        return False
    lg_lower = league.lower()
    # Reject patterns first
    for rej in REJECT_PATTERNS:
        if rej in lg_lower:
            return False
    # Whitelist par sport
    patterns = WINAMAX_LEAGUES.get(sport, [])
    for pat in patterns:
        if pat in lg_lower:
            return True
    return False


def _validate_components(comps):
    """Renvoie (cleaned_components, error_msg). cleaned est utilisable, error_msg est None si OK."""
    if not isinstance(comps, list) or not comps:
        return None, "components doit être une liste non vide"
    if len(comps) > 8:
        return None, "max 8 composantes"
    cleaned = []
    for i, c in enumerate(comps):
        if not isinstance(c, dict):
            return None, f"composante #{i+1} doit être un objet"
        try:
            ml = int(c.get("max_legs", 0))
            cmin = float(c.get("cote_min", 0))
            cmax = float(c.get("cote_max", 0))
            sb = str(c.get("sort_by", "ev"))
            sp = c.get("sports", [])
            mc = int(c.get("max_combos", 1))
        except (TypeError, ValueError) as e:
            return None, f"composante #{i+1} types invalides: {e}"
        if ml not in (1, 2, 3, 4, 5, 6):
            return None, f"composante #{i+1}: max_legs doit être ∈ {{1,2,3,4,5,6}}, reçu {ml}"
        if sb not in VALID_SORT:
            return None, f"composante #{i+1}: sort_by doit être ∈ {VALID_SORT}, reçu {sb}"
        if cmin <= 1.0 or cmax <= cmin:
            return None, f"composante #{i+1}: cote_min ({cmin}) doit être > 1 et < cote_max ({cmax})"
        if not isinstance(sp, list) or not sp:
            return None, f"composante #{i+1}: sports doit être une liste non vide"
        bad = [s for s in sp if s not in VALID_SPORTS]
        if bad:
            return None, f"composante #{i+1}: sports inconnus {bad}"
        if mc < 1 or mc > 10:
            return None, f"composante #{i+1}: max_combos ∈ [1,10], reçu {mc}"
        market = str(c.get("market", "1x2"))
        valid = {"1x2", "btts", "over_1_5", "over_2_5"}
        # Support multi-markets et filtres : "over_1_5+plus,1x2-nul"
        parts = []
        for m in market.split(","):
            m = m.strip()
            base = m.split("+", 1)[0].split("-", 1)[0].strip()
            parts.append(base)
        bad = [p for p in parts if p not in valid]
        if bad:
            return None, f"composante #{i+1}: market(s) inconnus {bad}"
        try:
            sm = float(c.get("stake_multiplier", 1.0))
        except (TypeError, ValueError):
            sm = 1.0
        if sm <= 0 or sm > 5:
            return None, f"composante #{i+1}: stake_multiplier ∈ ]0, 5], reçu {sm}"
        cleaned.append({"max_legs": ml, "cote_min": cmin, "cote_max": cmax,
                        "sort_by": sb, "sports": list(sp), "max_combos": mc,
                        "market": market, "stake_multiplier": sm})
    return cleaned, None


# Magic cotes étendues (1x2 + BTTS) chargé au démarrage si dispo
_MAGIC_EXTENDED = None
def _get_magic_extended():
    global _MAGIC_EXTENDED
    if _MAGIC_EXTENDED is None:
        ext_path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_extended.json"
        if os.path.exists(ext_path):
            with open(ext_path) as f:
                _MAGIC_EXTENDED = json.load(f)
        else:
            _MAGIC_EXTENDED = {}
    return _MAGIC_EXTENDED


# Magic cotes par league (granularité maximale, 326 leagues × 2502 cotes)
_MAGIC_BY_LEAGUE = None
def _get_magic_by_league():
    global _MAGIC_BY_LEAGUE
    if _MAGIC_BY_LEAGUE is None:
        path = "/Users/maxenceleguay/Sites/winnaHisto/datasets/magic_cotes_by_league.json"
        if os.path.exists(path):
            with open(path) as f:
                raw = json.load(f)
            out = {"_smart": True}
            for sport, leagues in raw.items():
                if sport == "_smart":
                    continue
                out[sport] = {lg: {str(c): wr for c, wr in cotes.items()}
                              for lg, cotes in leagues.items() if isinstance(cotes, dict)}
            _MAGIC_BY_LEAGUE = out
        else:
            _MAGIC_BY_LEAGUE = {}
    return _MAGIC_BY_LEAGUE


def _league_as_bucket(sport, league, category):
    """Bucket function utilisé en mode by_league : retourne directement le league."""
    return league


@app.route("/api/backtest-hybrid")
def api_backtest_hybrid():
    import json
    from datetime import datetime, timedelta
    from backtest_engine import run_backtest

    components_raw = request.args.get("components")
    if components_raw:
        try:
            parsed = json.loads(components_raw)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"components JSON invalide: {e}"}), 400
        cleaned, err = _validate_components(parsed)
        if err:
            return jsonify({"error": err}), 400
        preset = {"label": "Configuration custom", "components": cleaned}
        preset_id = "custom"
    else:
        preset_id = request.args.get("preset", "H8")
        preset = HYBRID_PRESETS.get(preset_id)
        if not preset:
            return jsonify({"error": f"Preset '{preset_id}' inconnu"}), 400

    start_date = request.args.get("date")
    end_date = request.args.get("end_date") or start_date
    if not start_date:
        return jsonify({"error": "Param 'date' requis"}), 400

    sizing_mode = request.args.get("sizing", "flat")  # flat | flat_pct | kelly
    base_stake = float(request.args.get("stake", 10.0))
    bankroll0 = float(request.args.get("bankroll", 100.0))
    cap_pct = float(request.args.get("cap_pct", 1.0))   # % bankroll par mise
    kelly_div = float(request.args.get("kelly_div", 4.0))  # Kelly/N
    stake_cap_abs = float(request.args.get("stake_cap", 0.0))  # cap absolu, 0 = pas de cap
    # Dédup inter-composantes : 'none' | 'max2' | 'max1' (no shared picks) | 'disjoint' (no shared matches)
    dedup_mode = request.args.get("dedup", preset.get("dedup", "none"))
    # Bookmaker filter : 'all' (Sofascore complet) | 'winamax_fr' (whitelist Winamax/Betclic/Unibet FR)
    bookmaker = request.args.get("bookmaker", "all")
    league_filter = _is_league_allowed if bookmaker == "winamax_fr" else None
    # Skip-day après perte : si True, jour suivant un jour rouge est skippé (réduit série rouge)
    skip_after_loss = request.args.get("skip_after_loss", "0") in ("1", "true", "yes")
    # Magic source : 'smart' (bucket par sport, default) ou 'by_league' (granulaire 326 leagues, +33% PnL / -4j série)
    magic_source = request.args.get("magic_source", "smart")

    s = datetime.strptime(start_date, "%Y-%m-%d").date()
    e = datetime.strptime(end_date, "%Y-%m-%d").date()
    days = []
    cur = s
    while cur <= e:
        days.append(cur.isoformat())
        cur += timedelta(days=1)

    magic = load_magic()

    # 1ère passe : génère candidats puis applique dédup inter-composantes par jour.
    from collections import Counter
    combos_seq = []
    daily = {d: {"date": d, "n_combos": 0, "n_won": 0, "pnl": 0.0, "stake": 0.0,
                 "bankroll_end": 0.0, "combos": []} for d in days}
    breakdown_acc = [{"component": i + 1, "config": comp} for i, comp in enumerate(preset["components"])]

    # Pré-fetch tous les candidats par (composante, jour). Plus de candidats si dedup actif.
    candidate_pool_size = 12 if dedup_mode != "none" else 3
    cand_by_day_comp = {}
    for i, comp in enumerate(preset["components"]):
        comp_market = comp.get("market", "1x2")
        # Sélection magic + bucket_fn selon market et magic_source
        if comp_market in ("btts", "over_1_5", "over_2_5"):
            comp_magic = _get_magic_extended()
            bucket_fn_arg = None
        elif magic_source == "by_league":
            comp_magic = _get_magic_by_league()
            bucket_fn_arg = _league_as_bucket
        else:
            comp_magic = magic
            bucket_fn_arg = None
        kwargs = dict(max_legs=comp["max_legs"], cote_min=comp["cote_min"],
                      cote_max=comp["cote_max"], sort_by=comp["sort_by"],
                      sports_filter=comp["sports"],
                      max_combos=comp["max_combos"] * candidate_pool_size,
                      stake=base_stake, league_filter=league_filter,
                      market=comp_market, bucket_fn=bucket_fn_arg)
        for d in days:
            r = run_backtest(d, comp_magic, **kwargs)
            cand_by_day_comp[(d, i + 1)] = r["combos"]

    # Sélection : pour chaque jour, on parcourt les composantes dans l'ordre, on prend max_combos
    # par composante en filtrant selon dedup_mode (picks partagés inter-composantes).
    for d in days:
        used_picks = Counter()
        used_matches = set()
        for i, comp in enumerate(preset["components"]):
            chosen = 0
            for combo in cand_by_day_comp.get((d, i + 1), []):
                if chosen >= comp["max_combos"]:
                    break
                legs_keys = [(l["match"], l["selection"]) for l in combo["legs"]]
                legs_matches = {l["match"] for l in combo["legs"]}
                if dedup_mode == "max1" and any(used_picks[k] >= 1 for k in legs_keys):
                    continue
                if dedup_mode == "max2" and any(used_picks[k] >= 2 for k in legs_keys):
                    continue
                if dedup_mode == "disjoint" and (legs_matches & used_matches):
                    continue
                for k in legs_keys:
                    used_picks[k] += 1
                used_matches |= legs_matches
                combos_seq.append({"date": d, "component": i + 1, "combo": combo})
                chosen += 1

    # 2ème passe : applique le sizing avec compounding
    bankroll = bankroll0
    bankroll_curve = [bankroll0]
    bankroll_min = bankroll0
    bankroll_max = bankroll0
    peak_bankroll = bankroll0
    max_drawdown = 0.0
    max_drawdown_date = None
    n_total, won_total, pnl_total, stake_total = 0, 0, 0.0, 0.0
    bust = False
    bust_date = None
    comp_stats = {b["component"]: {"n": 0, "won": 0, "pnl": 0.0, "stake": 0.0}
                  for b in breakdown_acc}

    # Pré-calcul : si skip_after_loss, on doit savoir quels jours skipper.
    # On regroupe par date dans l'ordre, puis on calcule les pertes du jour précédent.
    skipped_days = set()
    if skip_after_loss:
        # 1ère passe : pré-calc des PnL/jour SANS sizing pour identifier les jours rouges
        prelim_daily = {}
        for entry in combos_seq:
            d = entry["date"]
            combo = entry["combo"]
            pnl = base_stake * (combo["cote_t"] - 1) if combo["won"] else -base_stake
            prelim_daily[d] = prelim_daily.get(d, 0) + pnl
        sorted_days = sorted(prelim_daily.keys())
        for i, d in enumerate(sorted_days):
            if i > 0:
                prev_d = sorted_days[i - 1]
                if prelim_daily[prev_d] < 0:
                    skipped_days.add(d)

    for entry in combos_seq:
        # En mode flat, mise = constante 10€ peu importe la bankroll → pas de bust qui tue la sim.
        # En compounding (flat_pct/kelly), bust réel = arrêt simulation.
        if bust and sizing_mode != "flat":
            break
        d = entry["date"]
        # Skip-day : si jour précédent rouge, on saute ce jour
        if d in skipped_days:
            continue
        ci = entry["component"]
        combo = entry["combo"]
        p = combo["wr_t"]
        c = combo["cote_t"]
        # Récupère le stake_multiplier de la composante (1.0 par défaut)
        comp_cfg = preset["components"][ci - 1] if ci - 1 < len(preset["components"]) else {}
        sm = comp_cfg.get("stake_multiplier", 1.0)
        stake = _compute_stake(sizing_mode, bankroll, base_stake,
                               kelly_div, cap_pct, stake_cap_abs, p, c, bankroll0=bankroll0)
        stake = stake * sm
        if combo["won"]:
            pnl = stake * (c - 1)
            bankroll += pnl
            won_total += 1
            comp_stats[ci]["won"] += 1
            daily[d]["n_won"] += 1
        else:
            pnl = -stake
            bankroll += pnl
        n_total += 1
        stake_total += stake
        pnl_total += pnl
        comp_stats[ci]["n"] += 1
        comp_stats[ci]["pnl"] += pnl
        comp_stats[ci]["stake"] += stake
        daily[d]["n_combos"] += 1
        daily[d]["pnl"] += pnl
        daily[d]["stake"] += stake
        daily[d]["combos"].append({
            "component": ci,
            "stake": stake,
            "cote_t": c,
            "wr_t": p,
            "ev": combo["ev"],
            "won": combo["won"],
            "legs": combo["legs"],
        })
        bankroll_curve.append(bankroll)
        bankroll_min = min(bankroll_min, bankroll)
        bankroll_max = max(bankroll_max, bankroll)
        # Max drawdown = peak-to-trough max sur la courbe
        if bankroll > peak_bankroll:
            peak_bankroll = bankroll
        cur_dd = peak_bankroll - bankroll
        if cur_dd > max_drawdown:
            max_drawdown = cur_dd
            max_drawdown_date = d
        daily[d]["bankroll_end"] = bankroll
        if bankroll < 0.5:
            bust = True
            bust_date = d

    breakdown = []
    for b in breakdown_acc:
        st = comp_stats[b["component"]]
        roi = st["pnl"] / st["stake"] if st["stake"] else 0
        breakdown.append({**b, "n_combos": st["n"], "n_won": st["won"],
                          "pnl": st["pnl"], "stake": st["stake"],
                          "wr": st["won"] / st["n"] if st["n"] else 0,
                          "roi": roi})

    daily_list = [d for d in daily.values() if d["n_combos"] > 0]
    n_days_green = sum(1 for d in daily_list if d["pnl"] > 0)
    n_days_red = sum(1 for d in daily_list if d["pnl"] < 0)
    n_days_flat = sum(1 for d in daily_list if d["pnl"] == 0)

    return jsonify({
        "mode": "hybrid",
        "preset": preset_id,
        "preset_label": preset["label"],
        "start_date": start_date,
        "end_date": end_date,
        "sizing_mode": sizing_mode,
        "base_stake": base_stake,
        "bankroll0": bankroll0,
        "cap_pct": cap_pct,
        "kelly_div": kelly_div,
        "stake_cap_abs": stake_cap_abs,
        "n_days_total": len(days),
        "n_days_played": len(daily_list),
        "n_days_green": n_days_green,
        "n_days_red": n_days_red,
        "n_days_flat": n_days_flat,
        "daily_win_rate": n_days_green / len(daily_list) if daily_list else 0,
        "n_combos_total": n_total,
        "n_won_total": won_total,
        "wr_combos": won_total / n_total if n_total else 0,
        "stake_total": stake_total,
        "pnl_total": pnl_total,
        "roi": pnl_total / stake_total if stake_total else 0,
        "bankroll_final": bankroll,
        "bankroll_min": bankroll_min,
        "bankroll_max": bankroll_max,
        "bankroll_multiplier": bankroll / bankroll0 if bankroll0 else 0,
        "max_drawdown": max_drawdown,
        "max_drawdown_pct": max_drawdown / peak_bankroll if peak_bankroll > 0 else 0,
        "max_drawdown_date": max_drawdown_date,
        "peak_bankroll": peak_bankroll,
        "dedup_mode": dedup_mode,
        "bust": bust,
        "bust_date": bust_date,
        "breakdown": breakdown,
        "daily": daily_list,
        "bankroll_curve": bankroll_curve,
    })


@app.route("/api/datasets")
def api_datasets():
    """Liste tous les CSV scrapés avec stats."""
    import csv
    base = "/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified"
    if not os.path.exists(base):
        return jsonify({"datasets": []})

    out = []
    for fname in sorted(os.listdir(base)):
        if not fname.endswith(".csv"):
            continue
        path = os.path.join(base, fname)
        size = os.path.getsize(path)
        mtime = os.path.getmtime(path)

        # Compte les lignes et extrait la période + leagues
        n = 0
        first_date = None
        last_date = None
        leagues = set()
        try:
            with open(path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    n += 1
                    d = r.get("date", "")
                    if d:
                        if first_date is None or d < first_date:
                            first_date = d
                        if last_date is None or d > last_date:
                            last_date = d
                    lg = r.get("league", "")
                    if lg:
                        leagues.add(lg)
        except Exception:
            pass

        out.append({
            "sport": fname.replace(".csv", ""),
            "filename": fname,
            "size_mb": round(size / 1024 / 1024, 2),
            "n_matches": n,
            "n_leagues": len(leagues),
            "leagues_sample": sorted(leagues)[:30],
            "first_date": first_date,
            "last_date": last_date,
            "mtime": mtime,
        })
    return jsonify({"datasets": out})


@app.route("/api/scrape-status")
def api_scrape_status():
    """Parse les logs de scraping (/tmp/sofa_*.log) et renvoie progression par sport.
    Sport key suffixée _ou pour le log Over/Under (sinon collision avec un scrape complet)."""
    import re, glob
    log_paths = sorted(set(glob.glob("/tmp/sofa_unified.log") + glob.glob("/tmp/sofa_foot_overunder.log") +
                           glob.glob("/tmp/sofa_*.log")))
    if not log_paths:
        return jsonify({"running": False, "log_missing": True})

    lines = []
    for p in log_paths:
        try:
            tag = "_OU" if "overunder" in p else ""
            with open(p, errors="ignore") as f:
                for line in f:
                    # Tag les sports dans le log Over/Under pour les distinguer
                    if tag:
                        line = re.sub(r"^(\s*)\[(\w+\-?\w*)\]",
                                       lambda m: f"{m.group(1)}[{m.group(2)}{tag}]",
                                       line, count=1)
                    lines.append(line)
        except Exception:
            continue

    # État par sport : phase 1 (listing) ou phase 2 (odds)
    sports = {}
    current_sport = None
    for line in lines:
        m = re.match(r"\[(\w+\-?\w*)\] === (\d{4}-\d{2}-\d{2}) → (\d{4}-\d{2}-\d{2}) ===", line)
        if m:
            current_sport = m.group(1)
            sports[current_sport] = {"phase": "listing", "list_done": 0, "list_total": 0,
                                      "list_events": 0, "odds_done": 0, "odds_total": 0,
                                      "odds_ok": 0, "rate": 0, "eta_sec": 0,
                                      "phase_complete": False, "saved": 0,
                                      "start_date": m.group(2), "end_date": m.group(3)}
            continue

        # Listing phase
        m = re.match(r"\s*\[(\w+\-?\w*)\] events listés : (\d+)/(\d+) jours, (\d+) events", line)
        if m:
            s = m.group(1)
            if s in sports:
                sports[s]["list_done"] = int(m.group(2))
                sports[s]["list_total"] = int(m.group(3))
                sports[s]["list_events"] = int(m.group(4))
            continue

        m = re.match(r"\[(\w+\-?\w*)\] Total events ENDED listés : (\d+) en", line)
        if m:
            s = m.group(1)
            if s in sports:
                sports[s]["odds_total"] = int(m.group(2))
                sports[s]["phase"] = "odds"
            continue

        # Odds phase
        m = re.match(r"\s*\[(\w+\-?\w*)\] odds : (\d+)/(\d+) \((\d+)/s, ETA (\d+)s\), (\d+) ok", line)
        if m:
            s = m.group(1)
            if s in sports:
                sports[s]["odds_done"] = int(m.group(2))
                sports[s]["odds_total"] = int(m.group(3))
                sports[s]["rate"] = int(m.group(4))
                sports[s]["eta_sec"] = int(m.group(5))
                sports[s]["odds_ok"] = int(m.group(6))
            continue

        m = re.match(r"\[(\w+\-?\w*)\] Sauvé (\d+) matchs", line)
        if m:
            s = m.group(1)
            if s in sports:
                sports[s]["phase_complete"] = True
                sports[s]["saved"] = int(m.group(2))

    # Process running : matche tous les scripts de scraping (sofascore_*, rescrape_*)
    import subprocess
    try:
        r = subprocess.run(["pgrep", "-f", "rescrape_|sofascore_unified|sofascore_massive"],
                           capture_output=True, text=True, timeout=2)
        running = bool((r.stdout or "").strip())
    except Exception:
        running = False

    return jsonify({"running": running, "sports": sports})


@app.route("/api/live-combos")
def api_live_combos():
    """Génère combos LIVE pour aujourd'hui avec la même logique que le backtest hybride.
    Param obligatoires : preset (ou components), bankroll.
    Retourne combos avec stake calculé pour chaque combo."""
    from datetime import datetime
    from collections import Counter
    from backtest_engine import extract_picks as bt_extract_picks, build_backtest_combos

    # Validation params
    components_raw = request.args.get("components")
    if components_raw:
        try:
            parsed = json.loads(components_raw)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"components JSON invalide: {e}"}), 400
        cleaned, err = _validate_components(parsed)
        if err:
            return jsonify({"error": err}), 400
        preset = {"label": "Configuration custom", "components": cleaned}
        preset_id = "custom"
    else:
        preset_id = request.args.get("preset", "Multi_full_BTTS_optimal")
        preset = HYBRID_PRESETS.get(preset_id)
        if not preset:
            return jsonify({"error": f"Preset '{preset_id}' inconnu"}), 400

    day_str = request.args.get("date") or date.today().isoformat()
    sizing_mode = request.args.get("sizing", "flat_pct")
    base_stake = float(request.args.get("stake", 10.0))
    bankroll = float(request.args.get("bankroll", 100.0))
    bankroll0 = float(request.args.get("bankroll0", 100.0))
    cap_pct = float(request.args.get("cap_pct", 1.0))
    kelly_div = float(request.args.get("kelly_div", 4.0))
    stake_cap_abs = float(request.args.get("stake_cap", 0.0))
    dedup_mode = request.args.get("dedup", preset.get("dedup", "none"))
    bookmaker = request.args.get("bookmaker", "winamax_fr")
    league_filter = _is_league_allowed if bookmaker == "winamax_fr" else None
    magic_source = request.args.get("magic_source", "smart")

    # Phase 1 : liste events live (5 sports en parallèle)
    sports_needed = set()
    for c in preset["components"]:
        for s in c["sports"]:
            sports_needed.add(s)
    all_events = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for evs in pool.map(lambda s: list_today_events(s, day_str), sports_needed):
            all_events.extend(evs)

    # Filtrage temporel : on garde seulement les matchs
    #  (a) qui n'ont pas encore commencé (now < start_time)
    #  (b) dont la date locale = day_str (Sofascore renvoie parfois des matchs UTC du lendemain)
    from datetime import datetime as _dt
    req_date = _dt.strptime(day_str, "%Y-%m-%d").date()
    now_ts = _dt.now().timestamp()
    n_dropped_started = 0
    n_dropped_other_date = 0
    kept_events = []
    for e in all_events:
        st = e.get("start_time")
        if st is not None:
            if st < now_ts - 60:
                n_dropped_started += 1
                continue
            ev_date = _dt.fromtimestamp(st).date()
            if ev_date != req_date:
                n_dropped_other_date += 1
                continue
        kept_events.append(e)
    all_events = kept_events

    # Phase 2 : odds en parallèle
    events_with_odds = []
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = [pool.submit(fetch_event_odds, e) for e in all_events]
        for f in as_completed(futures):
            r = f.result()
            if r and (r.get("odds_1") or r.get("odds_2")):
                events_with_odds.append(r)

    # Phase 3 : convertir events en match-dicts compatibles avec backtest_engine.extract_picks
    matches = []
    for e in events_with_odds:
        m = {
            "sport": e["sport"],
            "league": e.get("league", ""),
            "category": e.get("category", ""),
            "home": e["home"],
            "away": e["away"],
            "hs": 0, "as": 0,
            "home_won": False, "is_draw": False,
            "odds_1": e.get("odds_1"),
            "odds_2": e.get("odds_2"),
            "odds_x": e.get("odds_x"),
            "btts_yes": False,
            "odds_btts_y": e.get("odds_btts_y"),
            "odds_btts_n": e.get("odds_btts_n"),
            "over_1_5": False, "over_2_5": False, "over_3_5": False,
            "odds_over_1_5": e.get("odds_over_1_5"),
            "odds_under_1_5": e.get("odds_under_1_5"),
            "odds_over_2_5": e.get("odds_over_2_5"),
            "odds_under_2_5": e.get("odds_under_2_5"),
            "start_time": e.get("start_time"),
        }
        matches.append(m)

    if league_filter:
        matches = [m for m in matches if league_filter(m["sport"], m.get("league", ""))]

    # Map match -> start_time pour ré-attacher au pick
    start_time_by_match = {f'{m["home"]} vs {m["away"]}': m.get("start_time") for m in matches}

    # Phase 4 : générer combos par composante (même logique que backtest-hybrid)
    magic = load_magic()
    cand_by_comp = {}
    candidate_pool_size = 12 if dedup_mode != "none" else 3
    for i, comp in enumerate(preset["components"]):
        comp_market = comp.get("market", "1x2")
        if comp_market in ("btts", "over_1_5", "over_2_5"):
            comp_magic = _get_magic_extended()
            bucket_fn_arg = None
        elif magic_source == "by_league":
            comp_magic = _get_magic_by_league()
            bucket_fn_arg = _league_as_bucket
        else:
            comp_magic = magic
            bucket_fn_arg = None
        sf = comp["sports"]
        matches_filt = [m for m in matches if m["sport"] in sf]
        picks = bt_extract_picks(matches_filt, comp_magic, market=comp_market, bucket_fn=bucket_fn_arg)
        combos = build_backtest_combos(picks, max_legs=comp["max_legs"],
                                       cote_min=comp["cote_min"], cote_max=comp["cote_max"],
                                       max_combos=comp["max_combos"] * candidate_pool_size,
                                       sort_by=comp["sort_by"])
        cand_by_comp[i + 1] = combos

    # Phase 5 : sélection avec dédup inter-composantes
    used_picks = Counter()
    used_matches = set()
    selected = []
    for i, comp in enumerate(preset["components"]):
        chosen = 0
        for combo in cand_by_comp.get(i + 1, []):
            if chosen >= comp["max_combos"]:
                break
            legs_keys = [(l["match"], l["selection"]) for l in combo["legs"]]
            legs_matches = {l["match"] for l in combo["legs"]}
            if dedup_mode == "max1" and any(used_picks[k] >= 1 for k in legs_keys):
                continue
            if dedup_mode == "max2" and any(used_picks[k] >= 2 for k in legs_keys):
                continue
            if dedup_mode == "disjoint" and (legs_matches & used_matches):
                continue
            for k in legs_keys:
                used_picks[k] += 1
            used_matches |= legs_matches
            sm = comp.get("stake_multiplier", 1.0)
            stake = _compute_stake(sizing_mode, bankroll, base_stake,
                                   kelly_div, cap_pct, stake_cap_abs,
                                   combo["wr_t"], combo["cote_t"], bankroll0=bankroll0)
            stake = stake * sm
            stake = round(stake, 2)
            # Réattache start_time aux legs
            legs_out = []
            for l in combo["legs"]:
                l2 = dict(l)
                l2["start_time"] = start_time_by_match.get(l["match"])
                legs_out.append(l2)
            selected.append({
                "component": i + 1,
                "stake": stake,
                "stake_multiplier": sm,
                "potential_gain": round(stake * (combo["cote_t"] - 1), 2),
                "cote_t": combo["cote_t"],
                "wr_t": combo["wr_t"],
                "ev": combo["ev"],
                "legs": legs_out,
            })
            chosen += 1

    total_stake = round(sum(c["stake"] for c in selected), 2)
    total_potential = round(sum(c["potential_gain"] for c in selected), 2)

    return jsonify({
        "date": day_str,
        "preset": preset_id,
        "preset_label": preset["label"],
        "bankroll": bankroll,
        "sizing_mode": sizing_mode,
        "base_stake": base_stake,
        "stake_cap_abs": stake_cap_abs,
        "dedup_mode": dedup_mode,
        "bookmaker": bookmaker,
        "magic_source": magic_source,
        "n_events": len(events_with_odds),
        "n_events_filtered": len(matches),
        "n_dropped_started": n_dropped_started,
        "n_dropped_other_date": n_dropped_other_date,
        "n_combos": len(selected),
        "total_stake": total_stake,
        "total_potential_gain": total_potential,
        "bankroll_after_all_win": round(bankroll + total_potential, 2),
        "bankroll_after_all_lose": round(bankroll - total_stake, 2),
        "combos": selected,
    })


@app.route("/api/combos")
def api_combos():
    day_str = request.args.get("date") or date.today().isoformat()
    cote_min = float(request.args.get("cote_min", 2.0))
    cote_max = float(request.args.get("cote_max", 5.0))
    max_legs = int(request.args.get("max_legs", 3))
    top = int(request.args.get("top", 10))
    sort_by = request.args.get("sort_by", "ev")

    magic = load_magic()
    sports = ["football", "basketball", "ice-hockey", "baseball", "tennis"]

    # Liste events
    all_events = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        for evs in pool.map(lambda s: list_today_events(s, day_str), sports):
            all_events.extend(evs)

    # Odds parallèles
    events_with_odds = []
    with ThreadPoolExecutor(max_workers=30) as pool:
        futures = [pool.submit(fetch_event_odds, e) for e in all_events]
        for f in as_completed(futures):
            r = f.result()
            if r and (r.get("odds_1") or r.get("odds_2")):
                events_with_odds.append(r)

    # Picks
    picks = []
    for e in events_with_odds:
        picks.extend(extract_picks(e, magic))
    picks.sort(key=lambda p: -p["ev"])

    # Combos
    combos = build_combos(picks, max_legs=max_legs, cote_min=cote_min,
                         cote_max=cote_max, max_combos=top, sort_by=sort_by)
    combos_serializable = []
    for c in combos:
        combos_serializable.append({
            "cote_t": c["cote_t"],
            "wr_t": c["wr_t"],
            "ev": c["ev"],
            "legs": c["legs"],
        })

    return jsonify({
        "date": day_str,
        "total_matches": len(all_events),
        "matches_with_odds": len(events_with_odds),
        "picks": picks[:50],
        "combos": combos_serializable,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)
