#!/usr/bin/env python3
"""
CLV (Closing Line Value) — de-vigging + filtre value vs Pinnacle.

Fonctions principales :
- power_devig(odds_list)        → probas no-vig (méthode de Shin / power, robuste)
- logarithmic_devig(odds_list)  → probas no-vig (méthode log, souvent plus précise sur favorites)
- multiplicative_devig(odds_list) → méthode naïve (proba = (1/cote) / sum(1/cotes_i))
- filter_clv_value(cote_winamax, p_true_devig, threshold=1.05) → True si cote_winamax × p_true ≥ threshold
- match_event(pinn_event, wina_event, tol_minutes=60) → True si même match

Pourquoi de-vig ?
    Les cotes Pinnacle incluent une marge (~1-3%). Pour estimer la "vraie" proba implicite,
    on retire la marge — c'est le "no-vig price". Cette proba est notre référence pour juger
    si la cote Winamax (ou autre) est value.

Lequel choisir ?
- multiplicative : simple, biaisé vers favorites (sur-estime petites cotes).
- logarithmic    : Adler/Shin variant, meilleur sur 2-way (tennis, totals, BTTS).
- power          : pondération racine, robuste sur 3-way (foot 1x2). Recommandé par défaut.

Usage rapide :
    >>> from clv_devig import power_devig, filter_clv_value
    >>> probs = power_devig([2.05, 3.40, 3.80])  # cotes Pinnacle 1x2
    >>> # probs ~ [0.488, 0.291, 0.262] (somme = 1.0, sans marge)
    >>> filter_clv_value(cote_winamax=2.20, p_true_devig=0.488)
    True  # 2.20 × 0.488 = 1.074 > 1.05 → value confirmée
"""

from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from math import log


# ---- De-vigging methods ----------------------------------------------------

def _implied_probs(odds_list):
    """Probas implicites brutes (avec marge bookmaker)."""
    return [1.0 / o for o in odds_list if o and o > 1.0]


def multiplicative_devig(odds_list):
    """Méthode naïve : normalise les probas implicites pour qu'elles somment à 1.

    Biais : sur-estime favorites, sous-estime outsiders (favorite-longshot bias).
    Acceptable pour 2-way équilibrés (tennis cote ~2.0 vs ~2.0).
    """
    raw = _implied_probs(odds_list)
    if not raw:
        return None
    s = sum(raw)
    if s <= 0:
        return None
    return [p / s for p in raw]


def logarithmic_devig(odds_list):
    """Logarithmic devig (Shin variant log) : applique racine n-ème pour réduire biais.

    Calcul : p_i_true = p_i_implied ^ k, où k tel que sum(p_i^k) = 1
    Résolution numérique par bissection.
    """
    raw = _implied_probs(odds_list)
    if not raw or len(raw) < 2:
        return None
    # Bissection sur k : k=1 → somme = 1+marge, k > 1 réduit la somme à 1.
    lo, hi = 0.5, 5.0
    for _ in range(60):
        k = (lo + hi) / 2
        s = sum(p ** k for p in raw)
        if s > 1.0:
            lo = k
        else:
            hi = k
        if abs(s - 1.0) < 1e-9:
            break
    return [p ** k for p in raw]


def power_devig(odds_list):
    """Power devig (méthode de Shin / pondération racine).

    Plus robuste sur 3-way (foot 1N2) : applique k tel que sum(p_i ^ (1/k)) = 1
    avec k > 1. Équivalent à log devig en pratique mais formulation différente.

    Recommandé par défaut pour markets 1x2 et totals avec ligne pas symétrique.
    """
    raw = _implied_probs(odds_list)
    if not raw or len(raw) < 2:
        return None
    # Cherche exponent e tel que sum(p_i ^ e) = 1.0
    # Si margin > 0, somme(raw) > 1, donc e > 1.
    lo, hi = 0.5, 5.0
    e = 1.0
    for _ in range(80):
        e = (lo + hi) / 2
        s = sum(p ** e for p in raw)
        if s > 1.0:
            lo = e
        else:
            hi = e
        if abs(s - 1.0) < 1e-10:
            break
    return [p ** e for p in raw]


def margin(odds_list):
    """Marge bookmaker en pourcentage. Pinnacle vise ~1-3%, soft books 5-10%."""
    raw = _implied_probs(odds_list)
    if not raw:
        return None
    return sum(raw) - 1.0


# ---- Filtre value CLV ------------------------------------------------------

def filter_clv_value(cote_winamax, p_true_devig, threshold=1.05):
    """Retourne True si cote Winamax représente une value vs Pinnacle no-vig.

    Calcul : EV multiplier = cote_winamax × p_true_devig
        Si EV > threshold (1.05 = 5% edge minimum), c'est une value.
        Si EV < 1.0, c'est mathématiquement perdant à long terme.

    Args:
        cote_winamax (float): cote décimale prise sur Winamax
        p_true_devig (float): probabilité no-vig estimée via Pinnacle
        threshold (float): seuil minimum d'EV pour valider (default 1.05 = 5% edge)

    Returns:
        bool: True si pick passe le filtre CLV
    """
    if not cote_winamax or not p_true_devig:
        return False
    if cote_winamax <= 1.0 or p_true_devig <= 0 or p_true_devig >= 1.0:
        return False
    return (cote_winamax * p_true_devig) >= threshold


def ev_multiplier(cote_winamax, p_true_devig):
    """Retourne EV ratio. > 1.0 = profitable long-terme. None si inputs invalides."""
    if not cote_winamax or not p_true_devig:
        return None
    if cote_winamax <= 1.0 or p_true_devig <= 0:
        return None
    return cote_winamax * p_true_devig


# ---- Fuzzy match Pinnacle ↔ Winamax ----------------------------------------

def _norm_team(name):
    """Normalise nom équipe pour matching : lowercase, drop accents/punctuation."""
    if not name:
        return ""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    # Supprime suffixes communs
    for suffix in [" fc", " cf", " sc", " ac", " bc", " club", " united", " utd"]:
        if s.endswith(suffix):
            s = s[:-len(suffix)]
    s = "".join(c if c.isalnum() else " " for c in s)
    return " ".join(s.split())


def team_similarity(a, b):
    """Ratio similarité entre 2 noms d'équipe normalisés. 0.0 = différent, 1.0 = identique.

    Heuristique cumulative :
    - identique → 1.0
    - substring → 0.9
    - tous tokens du nom court ⊂ nom long → 0.85 (couvre 'Paris SG' vs 'Paris Saint Germain')
    - sinon → SequenceMatcher
    """
    na, nb = _norm_team(a), _norm_team(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.9
    tokens_a, tokens_b = set(na.split()), set(nb.split())
    if tokens_a and tokens_b:
        short, long_ = (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
        # Tous tokens du court présents dans le long, OU initiales matchent
        if short.issubset(long_):
            return 0.85
        # Match initiales : 'PSG' vs 'Paris Saint Germain' → initials 'p s g' présents
        joined_short = "".join(t[0] for t in short if t)
        joined_long_initials = "".join(t[0] for t in long_ if t)
        if joined_short and joined_short in joined_long_initials:
            return 0.8
    return SequenceMatcher(None, na, nb).ratio()


def match_event(pinn_event, target_event, tol_minutes=60, min_similarity=0.75):
    """True si pinn_event et target_event représentent le même match.

    Critères :
    - kickoff dans tol_minutes (default ±60min)
    - home & away avec similarité ≥ min_similarity (default 0.75)

    Args:
        pinn_event (dict): event Pinnacle avec keys 'home', 'away', 'starts' (ISO)
        target_event (dict): event Winamax/Sofascore avec mêmes keys (ou 'kickoff')
        tol_minutes (int): tolérance temporelle
        min_similarity (float): seuil similarité noms équipes

    Returns:
        bool
    """
    p_start = pinn_event.get("starts") or pinn_event.get("kickoff")
    t_start = target_event.get("starts") or target_event.get("kickoff") or target_event.get("startsAt")
    if not p_start or not t_start:
        return False
    try:
        p_dt = datetime.fromisoformat(str(p_start).replace("Z", "+00:00"))
        t_dt = datetime.fromisoformat(str(t_start).replace("Z", "+00:00"))
    except ValueError:
        return False
    if abs((p_dt - t_dt).total_seconds()) > tol_minutes * 60:
        return False

    sim_home = team_similarity(pinn_event.get("home"), target_event.get("home"))
    sim_away = team_similarity(pinn_event.get("away"), target_event.get("away"))
    if sim_home < min_similarity or sim_away < min_similarity:
        # Tente swap (cas où Pinnacle inverse home/away)
        sim_h2 = team_similarity(pinn_event.get("home"), target_event.get("away"))
        sim_a2 = team_similarity(pinn_event.get("away"), target_event.get("home"))
        if sim_h2 < min_similarity or sim_a2 < min_similarity:
            return False
    return True


def find_matching(pinnacle_events, target_event, tol_minutes=60, min_similarity=0.75):
    """Cherche dans liste pinnacle_events le meilleur match pour target_event.

    Returns:
        dict | None: l'event Pinnacle correspondant, ou None si aucun match.
    """
    best = None
    best_score = 0.0
    for p in pinnacle_events:
        if not match_event(p, target_event, tol_minutes, min_similarity):
            continue
        sh = team_similarity(p.get("home"), target_event.get("home"))
        sa = team_similarity(p.get("away"), target_event.get("away"))
        score = sh + sa
        if score > best_score:
            best_score = score
            best = p
    return best


# ---- CLI rapide pour tests manuels -----------------------------------------

if __name__ == "__main__":
    import sys

    print("=== Tests de-vigging ===\n")
    # Exemple 1x2 foot Premier League
    cotes_1x2 = [2.05, 3.40, 3.80]
    print(f"Cotes 1x2 Pinnacle : {cotes_1x2}")
    print(f"  marge brute       : {margin(cotes_1x2)*100:.2f}%")
    print(f"  multiplicative    : {[round(p, 4) for p in multiplicative_devig(cotes_1x2)]}")
    print(f"  logarithmic       : {[round(p, 4) for p in logarithmic_devig(cotes_1x2)]}")
    print(f"  power             : {[round(p, 4) for p in power_devig(cotes_1x2)]}")

    # Exemple Over/Under tennis
    cotes_ou = [1.85, 2.05]
    print(f"\nCotes O/U 2.5 : {cotes_ou}")
    print(f"  power             : {[round(p, 4) for p in power_devig(cotes_ou)]}")

    # Exemple filtre CLV
    print("\n=== Test filter_clv_value ===")
    p_true = power_devig([2.05, 3.40, 3.80])[0]  # proba home no-vig
    print(f"Pinnacle home no-vig : {p_true:.4f}")
    for cote_wina in [1.95, 2.05, 2.15, 2.25]:
        ev = ev_multiplier(cote_wina, p_true)
        ok = filter_clv_value(cote_wina, p_true, threshold=1.05)
        print(f"  Winamax {cote_wina} → EV mult {ev:.4f} → value? {ok}")

    # Exemple fuzzy match
    print("\n=== Test fuzzy match ===")
    print(f"  'Paris SG' vs 'Paris Saint-Germain' : {team_similarity('Paris SG', 'Paris Saint-Germain'):.3f}")
    print(f"  'Man Utd' vs 'Manchester United'    : {team_similarity('Man Utd', 'Manchester United'):.3f}")
    print(f"  'Bayern' vs 'Bayern München'        : {team_similarity('Bayern', 'Bayern München'):.3f}")
