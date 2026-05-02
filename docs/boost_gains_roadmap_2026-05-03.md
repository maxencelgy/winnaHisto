# Roadmap Boost Gains — État pipeline + leviers manquants

Date : 2026-05-03. Analyse basée sur tout ce qui a été codé jusqu'ici.

## Ce que tu as déjà (très solide)

- **Magic cotes** : table sport×bucket×cote → WR (`magic_cotes_smart.json`)
- **Magic range** : match cote ∈ [m-h, m+h] avec WR pondéré (`test_magic_range.py`)
- **Stats refinements** : Wilson lower bound + Bayesian shrinkage (`test_bootstrap_bayes.py`)
- **Hybrid presets** : H3→H9, Foot_pro_lottery, Multi_safe/balance/full
- **Walk-forward backtest** : 5 semestres, ROI calculé par stratégie
- **Sizing adaptatif** : 10% BR courante, default 100€
- **App Flask** : `/api/backtest`, `/api/backtest-hybrid`, UI combos jour
- **Scraping** : Sofascore 5 sports + historique Winamax + football-data.co.uk

H9 = pépite confirmée walk-forward (+368% ROI, +5591€/mois flat 10€).

## Faiblesses identifiées

1. **Pas de CLV** — magic cotes calibrées sur passé Winamax, pas vérifiées contre cotes "vraies" (Pinnacle no-vig). Risque overfit.
2. **Mono-bookmaker** — uniquement Winamax. Tu rates 2-5% ROI rien qu'en line shopping.
3. **Combos 5-6 jambes** — H9 a un combo cote 50-300. Variance énorme, dépend de chance que TOUTES les jambes passent.
4. **Pas de live trigger** — tout est pre-match. Tu rates l'edge in-play (lag book sur carton/blessure).
5. **Limitation Winamax probable** — 5 combos high-EV/jour = profil gagnant flagué. Pas de "noise" stratégique.
6. **Marchés sous-exploités** — 1x2 + Over/Under. Tu rates Asian Handicap (variance plus faible) et Total équipe.
7. **Sizing flat 10%** — sous-optimal vs Kelly fractionnaire calibré sur EV par pick.
8. **Pas de stop-loss / TP** — exposé au bust si série rouge longue.

## Leviers BOOST — par ROI/effort

### 🥇 NIVEAU 1 (ROI massif, effort moyen)

**A. Couche CLV Pinnacle**
- Scraper Pinnacle pré-match (1h avant kick-off)
- De-vig (retirer marge ~2-3%) → estime vraie proba
- **Filtre H9** : ne retenir un pick que si `cote_winamax × (1 - margin) > 1 / p_pinnacle_devig`
- Effet : élimine les "faux edges" magic cote, ROI réel + drawdown ↓
- Implémentation : `pinnacle_scraper.py` + filtre dans `extract_picks`

**B. Line shopping multi-books**
- Étendre scraper à : Unibet, Betclic, PMU, Pasino (cotes France)
- Pour chaque pick H9 : prendre le meilleur book
- Effet : +2 à 5% ROI immédiat, aucun risque
- Note : Winamax limite, donc passer paris sharp sur autres books

**C. Asian Handicap remplace 1x2**
- Variance ~30% inférieure vs 1x2 (forums Pronosoft confirment)
- Réécrire un sous-modèle H9 sur AH ±0.5 / ±1 / ±1.5
- Effet : courbe ROI plus lisse, série rouge réduite

### 🥈 NIVEAU 2 (ROI bon, effort moyen)

**D. Kelly fractionnaire calibré**
- `f* = (p×c - 1) / (c - 1)`, mise = `0.25 × f* × BR` (1/4 Kelly)
- Plafond 5% BR même si Kelly dit +
- Effet : sizing optimal sur edges variables, +10-20% ROI long terme

**E. Stop-loss / take-profit**
- BR < 80€ → mise 5% (au lieu de 10%)
- BR > 200€ → retirer 50% des gains, reset stake
- Effet : évite bust, sécurise gains

**F. Anti-detection Winamax**
- 20% picks "publics" en bruit (cote < 1.4 favoris évidents)
- Mises arrondies (€10, €25 — pas €13.47)
- Étaler paris sur la journée
- Effet : prolonge durée de vie compte (12 mois → 36 mois)

### 🥉 NIVEAU 3 (ROI niche, effort élevé)

**G. Live trigger bot**
- Détecter carton rouge / blessure / chgmt gardien live
- Calculer cote attendue, comparer Winamax → alerte si edge
- Placer pari avant mise à jour book
- Effet : 5-10 paris/jour à edge énorme

**H. Modèles externes stackés**
- xG soccer (StatsBomb, FBref)
- ELO surface tennis (paper Cornell ROI 3%)
- Stack avec magic cote via Random Forest / XGBoost
- Effet : edge supplémentaire 2-3%

**I. Diversification capitale**
- 50% BR → H9 (pépite confirmée)
- 30% BR → value betting CLV-validated (Pinnacle filter)
- 20% BR → live opportunist + niche markets

## Quick wins ce soir

1. **Filtre EV minimum réaliste** : rejeter pick si `WR × cote < 1.05` (5% edge minimum)
2. **Cap stake absolu** : `max(stake, 50€)` même si %BR dit plus → Winamax cap
3. **Dedup inter-jour** : ne pas miser 2j de suite sur même équipe (anti-corrélation perdue)
4. **Affiner Wilson** : threshold 0.55 minimum sur magic cotes (au lieu de 0.50)

## Commandes prêtes

```bash
# Test Wilson 0.55 sur H9
python3 test_bootstrap_bayes.py --threshold 0.55 --preset H9

# Backtest avec filtre EV minimum
python3 -c "from backtest_engine import run_backtest; ..."
```

## Priorité recommandée

1. **CLV Pinnacle** (semaine 1) — change tout
2. **Asian Handicap** (semaine 2) — réduit variance H9
3. **Kelly fractionnaire** (semaine 2) — +10-20% ROI
4. **Stop-loss/TP** (semaine 3) — anti-bust
5. **Anti-detection** (semaine 3) — survie compte
