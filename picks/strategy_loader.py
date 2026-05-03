"""Charge les fichiers strategies/*.json en dict {id: strat}."""
import os, json, glob

ROOT = os.path.dirname(os.path.abspath(__file__))
STRAT_DIR = os.path.join(ROOT, "strategies")


def load_all():
    out = {}
    for path in sorted(glob.glob(os.path.join(STRAT_DIR, "*.json"))):
        try:
            with open(path) as f:
                strat = json.load(f)
            sid = strat.get("id") or os.path.splitext(os.path.basename(path))[0]
            out[sid] = strat
        except Exception as e:
            print(f"  [strategy_loader] err {path}: {e}")
    return out


def load(strategy_id):
    all_s = load_all()
    return all_s.get(strategy_id)
