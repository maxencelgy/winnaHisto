#!/usr/bin/env python3
"""Sweep MONTANTE PROGRESSIVE — chaque palier peut avoir cote/sport différent.
Concept :
  - Palier 1 : ultra-safe (cote 1.20-1.35 single)
  - Palier 2 : safe (1.30-1.50 single)
  - Palier 3 : mid (1.40-1.65 single)
  → Augmente le risque progressivement quand le capital grandit.
"""
import sys, os, json, itertools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backtest_engine import _get_index, extract_picks
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHITELIST = {
    "football": ["premier league","laliga","la liga","serie a","bundesliga","ligue 1","championship","laliga 2","serie b","ligue 2","champions league","europa league","conference","eredivisie","liga portugal","pro league","süper lig","trendyol süper","mls","liga mx","brasileirão","brasileirao","coupe","fa cup","primeira liga","primera división"],
    "basketball": ["nba","wnba","euroleague","eurocup","betclic élite","pro a","acb","liga endesa","lega basket","serie a","bbl","champions league"],
    "ice-hockey": ["nhl","khl","shl","liiga","ligue magnus","del","national league","extraliga","swiss"],
    "baseball": ["mlb"],
}
WFR_EXCL = ["liga mx","egyptian","cyprus","ligapro","primera división, clausura","brasileirão série d","brasileirão série b","scottish premiership","first professional league","danish superliga","superliga","niké liga","swiss super league","austrian bundesliga","stoiximan super league","czech first league","canadian premier","usl championship","copa de la liga","frauen-bundesliga","serie a femminile","uefa champions league, women","liga acb","germany bbl","wnba preseason","serie a2","del, playoffs","relegation round"]

def _lok(sport, lg):
    if not lg: return False
    l = lg.lower()
    if any(e in l for e in WFR_EXCL): return False
    return any(p in l for p in WHITELIST.get(sport, []))

def _load_magic():
    with open(os.path.join(ROOT, "datasets", "magic_cotes_smart_oos.json")) as f:
        raw = json.load(f)
    out = {"_smart": True}
    for sp, buckets in raw.items():
        if sp == "_smart": continue
        out[sp] = {b: {float(c): (info["wr"] if isinstance(info,dict) else info)
                       for c,info in cotes.items()}
                   for b, cotes in buckets.items()}
    return out

def _load_magic_ext():
    with open(os.path.join(ROOT, "datasets", "magic_cotes_extended_oos.json")) as f:
        return json.load(f)

magic = _load_magic()
magic_ext = _load_magic_ext()

def _gen_days(start, end):
    s = datetime.strptime(start,"%Y-%m-%d").date()
    e = datetime.strptime(end,"%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur.isoformat()
        cur += timedelta(days=1)


def get_picks_day(d, palier_cfg):
    """Extract picks pour un palier_cfg (dict avec sports, market, cote_min, cote_max)."""
    idx = _get_index()
    ms = idx.get(d, [])
    sports = palier_cfg["sports"]
    ms = [m for m in ms if m["sport"] in sports and _lok(m["sport"], m.get("league",""))]
    if not ms: return []
    market_str = palier_cfg["market"]
    markets = [m.strip() for m in market_str.split(",")]
    picks = []
    for mkt in markets:
        ref = magic_ext if mkt in ("btts","over_1_5","over_2_5") else magic
        ps = extract_picks(ms, ref, market=mkt)
        picks.extend(ps)
    cmin, cmax = palier_cfg["cote_min"], palier_cfg["cote_max"]
    picks = [p for p in picks if cmin <= p["odds"] <= cmax]
    # Dédup match+selection
    seen = set(); unique = []
    for p in picks:
        k = (p["match"], p["selection"])
        if k in seen: continue
        seen.add(k); unique.append(p)
    return unique


def simulate_progressive(palier_configs, start_date, end_date, mode="intraday", initial_stake=10, n_target=None):
    """palier_configs = list de dicts par palier ou {"default":..., "1": {...}, "2": {...}}.
    Si list, len(list) = n_paliers."""
    if isinstance(palier_configs, list):
        n_target = n_target or len(palier_configs)
    days = list(_gen_days(start_date, end_date))
    capital = initial_stake
    palier = 0
    cycles_log = []
    n_paliers_won = 0
    n_paliers_total = 0
    final_pnl = 0
    current_cycle_legs = []

    def reset_cycle(reason):
        nonlocal capital, palier, current_cycle_legs, final_pnl
        if reason == "complete":
            final_pnl += capital - initial_stake
        elif reason == "loss":
            final_pnl -= initial_stake
        cycles_log.append({
            "outcome": reason,
            "n_paliers_won": palier,
            "final_capital": capital if reason == "complete" else 0,
        })
        capital = initial_stake
        palier = 0
        current_cycle_legs[:] = []

    for d in days:
        # Pour chaque palier en cours, get picks selon config palier
        # En intraday : tous les paliers du jour font partie du même cycle
        if mode == "intraday":
            day_done = False
            while palier < n_target and not day_done:
                cfg = palier_configs[palier]
                picks = get_picks_day(d, cfg)
                # Sort + dédup match
                if cfg.get("sort_by", "wr") == "ev":
                    picks.sort(key=lambda p: -p["wr"]*p["odds"])
                else:
                    picks.sort(key=lambda p: -p["wr"])
                # Re-sort chrono
                picks.sort(key=lambda p: p.get("start_time") or 0)
                # Dédup par match
                seen_m = set(); unique = []
                for p in picks:
                    if p["match"] in seen_m: continue
                    seen_m.add(p["match"]); unique.append(p)
                # Skip matchs déjà utilisés ce cycle
                used_matches = set(l["match"] for l in current_cycle_legs)
                unique = [p for p in unique if p["match"] not in used_matches]
                legs_pp = cfg.get("legs_per_palier", 1)
                if len(unique) < legs_pp:
                    day_done = True; break
                combo_legs = unique[:legs_pp]
                cote_t = 1.0; won_all = True
                for l in combo_legs:
                    cote_t *= l["odds"]
                    if not l.get("won", False): won_all = False
                palier += 1
                n_paliers_total += 1
                current_cycle_legs.extend(combo_legs)
                if won_all:
                    n_paliers_won += 1
                    capital = capital * cote_t
                    if palier >= n_target:
                        reset_cycle("complete")
                        break
                else:
                    reset_cycle("loss")
                    break

    n_complete = sum(1 for c in cycles_log if c["outcome"] == "complete")
    n_loss = sum(1 for c in cycles_log if c["outcome"] == "loss")
    n_total_cycles = n_complete + n_loss
    avg_cap = sum(c["final_capital"] for c in cycles_log if c["outcome"] == "complete") / max(n_complete, 1)
    return {
        "n_complete": n_complete,
        "n_total": n_total_cycles,
        "completion_rate": n_complete / max(n_total_cycles, 1),
        "wr_palier": n_paliers_won / max(n_paliers_total, 1),
        "n_paliers_total": n_paliers_total,
        "avg_capital_complete": round(avg_cap, 2),
        "final_pnl": round(final_pnl, 2),
    }


# === Tester quelques configs progressives ===
PERIODS = [("S1-26", "2026-01-01", "2026-04-30")]

# Config helper
def cfg(sports, market, cmin, cmax, legs=1, sort="wr"):
    return {"sports": sports, "market": market, "cote_min": cmin,
            "cote_max": cmax, "legs_per_palier": legs, "sort_by": sort}

CONFIGS = [
    # 1. Progressive Hockey safe → moyen → mid
    ("Hockey progressive 3p", [
        cfg(["ice-hockey"], "1x2", 1.20, 1.40),
        cfg(["ice-hockey"], "1x2", 1.30, 1.55),
        cfg(["ice-hockey"], "1x2", 1.40, 1.70),
    ]),
    # 2. Foot O 1.5 progressive
    ("Foot O 1.5 progressive 3p", [
        cfg(["football"], "over_1_5", 1.10, 1.25),
        cfg(["football"], "over_1_5", 1.25, 1.45),
        cfg(["football"], "over_1_5", 1.40, 1.65),
    ]),
    # 3. Foot O 1.5 progressive 4p
    ("Foot O 1.5 progressive 4p", [
        cfg(["football"], "over_1_5", 1.10, 1.25),
        cfg(["football"], "over_1_5", 1.20, 1.40),
        cfg(["football"], "over_1_5", 1.30, 1.50),
        cfg(["football"], "over_1_5", 1.45, 1.70),
    ]),
    # 4. Hockey safe → combo 2j safer
    ("Hockey single → combo 2j", [
        cfg(["ice-hockey"], "1x2", 1.20, 1.40, legs=1),
        cfg(["ice-hockey"], "1x2", 1.20, 1.40, legs=2),
        cfg(["ice-hockey"], "1x2", 1.25, 1.45, legs=2),
    ]),
    # 5. Foot O 1.5 → Foot O 1.5 combo 2j → combo 3j
    ("Foot O 1.5 single → combo 2j → 3j", [
        cfg(["football"], "over_1_5", 1.20, 1.35, legs=1),
        cfg(["football"], "over_1_5", 1.15, 1.30, legs=2),
        cfg(["football"], "over_1_5", 1.10, 1.25, legs=3),
    ]),
    # 6. Multi-sport progressive
    ("Multi-sport progressive 4p", [
        cfg(["football", "ice-hockey"], "1x2", 1.20, 1.40),
        cfg(["football", "ice-hockey"], "1x2", 1.30, 1.50),
        cfg(["football", "ice-hockey", "basketball"], "1x2", 1.35, 1.55),
        cfg(["football", "ice-hockey", "basketball"], "1x2", 1.45, 1.70),
    ]),
    # 7. Foot xmkt progressive
    ("Foot xmkt progressive 3p", [
        cfg(["football"], "over_1_5", 1.20, 1.35),
        cfg(["football"], "over_2_5", 1.40, 1.65),
        cfg(["football"], "btts", 1.55, 1.80),
    ]),
    # 8. Foot O 1.5 single → combo (sweep accumulation prudente)
    ("Foot O 1.5 prudent then aggro", [
        cfg(["football"], "over_1_5", 1.30, 1.45),
        cfg(["football"], "over_1_5", 1.40, 1.60),
        cfg(["football"], "over_1_5", 1.50, 1.75),
    ]),
    # 9. Hockey aggressive → safer
    ("Hockey aggressive then safer 3p", [
        cfg(["ice-hockey"], "1x2", 1.45, 1.70),
        cfg(["ice-hockey"], "1x2", 1.30, 1.50),
        cfg(["ice-hockey"], "1x2", 1.20, 1.40),
    ]),
    # 10. Multi-sport hybrid (différent sport par palier)
    ("Foot p1 → Hockey p2 → Basket p3", [
        cfg(["football"], "over_1_5", 1.20, 1.40),
        cfg(["ice-hockey"], "1x2", 1.25, 1.50),
        cfg(["basketball"], "1x2", 1.30, 1.55),
    ]),
]

print("=== TESTS MONTANTE PROGRESSIVE Winamax FR strict ===\n")
print(f"{'Config':<45s} {'#✓/tot':>10s} {'%':>5s} {'Cap':>7s} {'PnL':>9s}")
print("-"*90)
results = []
for name, paliers in CONFIGS:
    r = simulate_progressive(paliers, "2026-01-01", "2026-04-30", mode="intraday", initial_stake=10)
    results.append({"name": name, "config": [p for p in paliers], **r})
    print(f"{name:<45s} {r['n_complete']:>3d}/{r['n_total']:<3d} {r['completion_rate']*100:>4.0f}% {r['avg_capital_complete']:>6.0f}€ +{r['final_pnl']:>5.0f}€")

print("\nSaved.")
with open("/Users/maxenceleguay/Sites/winnaHisto/datasets/progressive_montantes.json","w") as f:
    json.dump(results, f, indent=2, default=str)
