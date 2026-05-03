#!/usr/bin/env python3
"""Serveur Flask — UI 3 onglets : Live picks / Stratégies / Backtest.

Port 5051. Endpoints :
  GET  /                              → page principale
  GET  /api/scrape-status              → état dernier scrape
  POST /api/scrape?day=&sports=        → trigger scrape (subprocess)
  GET  /api/picks?...                  → ranked picks (filtres dynamiques)
  GET  /api/strategies                 → liste stratégies
  GET  /api/strategies/<id>            → détail strat
  GET  /api/strategies/<id>/today?bankroll=  → applique strat aux picks scrapés
  GET  /api/backtest?strategy=&start=&end=&bankroll=  → run backtest
"""
import os, sys, json, time, threading, subprocess
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template

from picks.magic import Magic
from picks.extractor import rank_picks, load_picks_file
from picks.strategy_loader import load_all as load_strategies, load as load_strategy
from picks.live import apply_strategy
from picks.backtester import backtest as run_backtest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKS_FILE = os.path.join(ROOT, "datasets", "picks_today.json")

app = Flask(__name__, template_folder="templates")

_magic = None
def get_magic():
    global _magic
    if _magic is None:
        _magic = Magic()
    return _magic

_scrape_state = {"running": False, "start_time": None, "log_tail": [], "last_done": None}
_scrape_lock = threading.Lock()


# ── ROUTES UI ─────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


# ── SCRAPE ─────────────────────────────────────────────────────────────
@app.route("/api/recalibrate", methods=["POST"])
def trigger_recalibrate():
    """Lance recalibrate_now.py en subprocess pour mettre à jour la magic LIVE."""
    if _scrape_state.get("recal_running"):
        return jsonify({"error": "Recalibration en cours"}), 409
    def _run():
        with _scrape_lock:
            _scrape_state["recal_running"] = True
            _scrape_state["recal_start"] = time.time()
            _scrape_state["recal_log"] = []
        try:
            script = os.path.join(ROOT, "recalibrate_now.py")
            proc = subprocess.Popen(
                [sys.executable, "-u", script], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, cwd=ROOT,
            )
            for line in proc.stdout:
                _scrape_state["recal_log"].append(line.rstrip())
                if len(_scrape_state["recal_log"]) > 100:
                    _scrape_state["recal_log"].pop(0)
            proc.wait()
            _scrape_state["recal_done"] = time.time()
        finally:
            _scrape_state["recal_running"] = False
            # Reset magic cache
            global _magic
            _magic = None

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True})


@app.route("/api/recalibrate-status")
def recalibrate_status():
    out = {
        "running": _scrape_state.get("recal_running", False),
        "start_time": _scrape_state.get("recal_start"),
        "done_time": _scrape_state.get("recal_done"),
        "log_tail": _scrape_state.get("recal_log", [])[-15:],
    }
    return jsonify(out)


@app.route("/api/scrape-status")
def scrape_status():
    out = dict(_scrape_state)
    if os.path.exists(PICKS_FILE):
        with open(PICKS_FILE) as f:
            d = json.load(f)
        out["last_scrape_day"] = d.get("day")
        out["last_scrape_n_events"] = d.get("n_events")
        out["last_scrape_at"] = d.get("scraped_at")
    else:
        out["last_scrape_day"] = None
    return jsonify(out)


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    day = request.args.get("day", date.today().isoformat())
    sports = request.args.get("sports", "football,basketball,ice-hockey,baseball")
    if _scrape_state["running"]:
        return jsonify({"error": "Scrape déjà en cours", "started_at": _scrape_state["start_time"]}), 409

    def _run():
        with _scrape_lock:
            _scrape_state["running"] = True
            _scrape_state["start_time"] = time.time()
            _scrape_state["log_tail"] = []
        try:
            script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper.py")
            proc = subprocess.Popen(
                [sys.executable, "-u", script, "--day", day, "--sports", sports],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT,
            )
            for line in proc.stdout:
                line = line.rstrip()
                _scrape_state["log_tail"].append(line)
                if len(_scrape_state["log_tail"]) > 100:
                    _scrape_state["log_tail"].pop(0)
            proc.wait()
            _scrape_state["last_done"] = time.time()
        finally:
            _scrape_state["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True, "day": day, "sports": sports})


# ── PICKS ──────────────────────────────────────────────────────────────
@app.route("/api/picks")
def api_picks():
    sort = request.args.get("sort", "wr")
    min_wr = float(request.args.get("min_wr", 0.50))
    min_ev = float(request.args.get("min_ev", 1.0))
    cote_min = float(request.args.get("cote_min", 1.0))
    cote_max = float(request.args.get("cote_max", 999))
    top = int(request.args.get("top", 50))
    sport = request.args.get("sport")
    market = request.args.get("market")
    sports_f = [s for s in sport.split(",") if s] if sport else None
    markets_f = [m for m in market.split(",") if m] if market else None

    if not os.path.exists(PICKS_FILE):
        return jsonify({"error": "Aucun scrape encore. Cliquer 'Scraper aujourd'hui'."}), 404

    data = load_picks_file(PICKS_FILE)
    r = rank_picks(data["events"], get_magic(), sort, min_wr, min_ev,
                   cote_min, cote_max, sports_f, markets_f, top)
    r["day"] = data.get("day")
    r["scraped_at"] = data.get("scraped_at")
    return jsonify(r)


# ── STRATÉGIES ────────────────────────────────────────────────────────
@app.route("/api/strategies")
def api_strategies():
    strats = load_strategies()
    return jsonify({sid: s for sid, s in strats.items()})


@app.route("/api/strategies/<sid>")
def api_strategy_detail(sid):
    s = load_strategy(sid)
    if not s:
        return jsonify({"error": f"Stratégie '{sid}' inconnue"}), 404
    return jsonify(s)


@app.route("/api/strategies/<sid>/today")
def api_strategy_today(sid):
    s = load_strategy(sid)
    if not s:
        return jsonify({"error": f"Stratégie '{sid}' inconnue"}), 404
    if not os.path.exists(PICKS_FILE):
        return jsonify({"error": "Aucun scrape. Lancer 'Scraper aujourd'hui' d'abord."}), 404

    bankroll = float(request.args.get("bankroll", 100))
    data = load_picks_file(PICKS_FILE)
    r = apply_strategy(s, data, bankroll, magic=get_magic())
    return jsonify(r)


# ── BACKTEST ──────────────────────────────────────────────────────────
@app.route("/api/backtest")
def _is_montante(strat):
    return strat.get("mode") == "montante" or "montante" in strat


@app.route("/api/montante-strategies")
def api_montante_strategies():
    """Liste des stratégies de type montante."""
    all_s = load_strategies()
    return jsonify({sid: s for sid, s in all_s.items() if _is_montante(s)})


@app.route("/api/montante-simulate")
def api_montante_simulate():
    """Simule une stratégie montante en mode interday ou intraday."""
    sid = request.args.get("strategy")
    start = request.args.get("start")
    end = request.args.get("end")
    mode = request.args.get("mode", "interday")
    initial_stake = float(request.args.get("initial_stake", 10))
    n_paliers_target = request.args.get("n_paliers")
    if not (sid and start and end):
        return jsonify({"error": "params requis: strategy, start, end"}), 400
    s = load_strategy(sid)
    if not s:
        return jsonify({"error": f"Stratégie '{sid}' inconnue"}), 404
    if not _is_montante(s):
        return jsonify({"error": f"'{sid}' n'est pas une stratégie montante"}), 400

    # Override n_paliers si fourni
    if n_paliers_target:
        s = dict(s)
        s["montante"] = dict(s.get("montante", {}))
        s["montante"]["n_paliers_target"] = int(n_paliers_target)

    try:
        from picks.montante_engine import simulate
        r = simulate(s, start, end, mode=mode, initial_stake=initial_stake)
        r["strategy"] = {"id": sid, "label": s.get("label")}
        return jsonify(r)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"montante err: {type(e).__name__}: {e}"}), 500


@app.route("/api/backtest")
def api_backtest():
    sid = request.args.get("strategy")
    start = request.args.get("start")
    end = request.args.get("end")
    bankroll = float(request.args.get("bankroll", 100))
    if not (sid and start and end):
        return jsonify({"error": "params requis: strategy, start, end"}), 400
    s = load_strategy(sid)
    if not s:
        return jsonify({"error": f"Stratégie '{sid}' inconnue"}), 404
    try:
        r = run_backtest(s, start, end, bankroll0=bankroll)
        r["strategy"] = {"id": sid, "label": s.get("label")}
        return jsonify(r)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"backtest err: {type(e).__name__}: {e}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051, debug=False)
