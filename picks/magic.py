"""Helper magic cotes : chargement + lookup avec tolérance.

Usage:
    from picks.magic import Magic
    m = Magic()
    cm, wr = m.lookup("football", "Premier League", "1x2", 1.65)
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from morning_live import CATEGORIZERS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAGIC_SMART = os.path.join(ROOT, "datasets", "magic_cotes_smart.json")
MAGIC_EXT = os.path.join(ROOT, "datasets", "magic_cotes_extended.json")


def _wr_of(v):
    return float(v["wr"]) if isinstance(v, dict) else float(v)


class Magic:
    def __init__(self):
        with open(MAGIC_SMART) as f:
            raw = json.load(f)
        self.smart = {}
        for sp, buckets in raw.items():
            if sp == "_smart":
                continue
            self.smart[sp] = {b: {float(c): _wr_of(v) for c, v in cotes.items()}
                              for b, cotes in buckets.items()}
        with open(MAGIC_EXT) as f:
            self.ext = json.load(f)

    def bucket_for(self, sport, league, category=""):
        cat_fn = CATEGORIZERS.get(sport)
        return cat_fn(league or "", category or "") if cat_fn else (league or "")

    def lookup(self, sport, league, market_key, cote, tol=0.30, category=""):
        """Retourne (cote_magic, wr) ou (None, None)."""
        bucket = self.bucket_for(sport, league, category)
        cotes_dict = None
        if market_key == "1x2":
            cotes_dict = self.smart.get(sport, {}).get(bucket)
        else:
            ext_bucket = self.ext.get(sport, {}).get(bucket, {})
            sub = ext_bucket.get(market_key)
            if sub:
                cotes_dict = {float(k): _wr_of(v) for k, v in sub.items()}
        if not cotes_dict:
            return None, None
        target = float(cote)
        best = min(cotes_dict.keys(), key=lambda c: abs(c - target))
        if abs(best - target) > tol:
            return None, None
        return best, cotes_dict[best]

    def has_market(self, sport, league, market_key, category=""):
        cm, wr = self.lookup(sport, league, market_key, 2.0, tol=10.0, category=category)
        return wr is not None


def load() -> Magic:
    return Magic()
