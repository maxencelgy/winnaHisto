# Red Days Forensics — Multi_full_BTTS_optimal

Date: 2026-05-02
Auteur: enquete data forensique automatisée
Sandbox: Winamax FR whitelist + dedup max1 + flat 10€ + stake_multiplier par composante
Cache calculé: `/tmp/global_cand.pkl`, `/tmp/red_days_sim.pkl`, `/tmp/final_blacklist_summary.json`

## Setup

- **Preset**: 8 composantes Multi_full_BTTS_optimal (cf input)
- **In-sample (IS)** : 4 semestres = 730 jours joués (2024-01-01 → 2025-12-31)
- **Out-of-sample (OOS)** : S1-2026 = 121 jours joués (2026-01-01 → 2026-05-01)
- Baseline IS : PnL=+20 746€, red%=35.6%, **max red streak=6**, max DD=188€
- Baseline OOS : PnL=+5 430€, red%=28.1%, **max red streak=3**, max DD=150€

## Étape 2 — Top patterns signifiants (IS)

| # | Dimension | Signal | Statistique | p-value |
|---|---|---|---|---|
| 1 | **MLB days vs sans MLB** | days WITH MLB pick = **48.9% rouge** vs 31.4% sans | z=+4.21 | **<0.0001** |
| 2 | **Volume combos faible** | 1-4 combos/j → **51.1% rouge** ; 5-7 → 30.5% ; 8-10 → 17.2% | z=+5.73 | **<0.0001** |
| 3 | **Summer mid-week** | Tue/Wed/Thu en mai-août → **54.3% rouge** vs 32.5% reste | z=+4.32 | **<0.0001** |
| 4 | **Cote moyenne picks haute** | Q4 cote∈[2.23,3.69] → **46.2% rouge** vs Q1-Q3 ≈30% | z=+3.43 | **0.001** |
| 5 | **Mois juin** | 55.0% rouge (n=60) ; juillet 46.8% | z=+3.27 | **0.001** |
| 6 (bonus) | Leagues "Qualification"/"Knockout" | 43.9% rouge sur 123 jours | z=+2.10 | 0.035 |
| 7 (bonus) | Mardi+Jeudi | 46% rouge ; **week-end seulement 25% rouge** | z multiples | <0.05 |

**Lecture causale** : ces signaux ne sont pas indépendants — ils décrivent le même phénomène : *en été mid-week, le volume football/basket EU s'effondre, le système est forcé de piocher dans MLB et qualifs CL/EL avec cotes plus élevées et moins fiables*. Le scoring devient mécaniquement plus volatile.

## Étape 3 — Blacklists construites et testées

| Stratégie | IS PnL | IS red% | IS max streak | IS DD | OOS PnL | OOS red% | OOS streak | OOS DD |
|---|---|---|---|---|---|---|---|---|
| **Baseline** | +20 746€ | 35.6% | **6** | 188€ | **+5 430€** | 28.1% | **3** | 150€ |
| V1: Block MLB picks | +20 934€ | 34.0% | 6 | 188€ | +5 247€ | 28.1% | 3 | 150€ |
| V2: Skip si <5 candidats jour | +20 771€ | 35.3% | 6 | 188€ | +5 430€ | 28.1% | 3 | 150€ |
| V3: Skip si <6 candidats jour | +20 803€ | 35.0% | 6 | 188€ | +5 430€ | 28.1% | 3 | 150€ |
| V4: Block MLB + skip <6 | +20 913€ | 33.4% | 6 | 188€ | +5 247€ | 28.1% | 3 | 150€ |
| V5: Skip Tue/Wed/Thu mai-août | +18 813€ | 32.5% | 6 | 188€ | +5 430€ | 28.1% | 3 | 150€ |
| V6: Block MLB+qualif+knockout legs + skip <8 | +18 823€ | 32.6% | **7** ⚠ | 204€ | +5 176€ | 30.8% | **4** ⚠ | 150€ |

## Étape 4 — Validation OOS S1-2026

**Aucune** des blacklists ne réduit la série rouge max OOS. La série rouge max OOS = 3 jours, identique au baseline. La V6 (la plus agressive) **dégrade** OOS : red% passe de 28.1% à 30.8%, streak de 3 à 4, PnL -4.7%.

## Verdict

**PATTERN STATISTIQUEMENT RÉEL MAIS NON EXPLOITABLE** (overfit à éviter).

Mécanique :
- Les 5 signaux IS sont tous statistiquement significatifs (p<0.05 jusqu'à <0.0001) — ils existent vraiment.
- Mais ils sont **corrélés** entre eux et ne capturent que la queue de distribution : ils différencient les jours joués (35-50% rouge) sans faire chuter la fréquence de séries 4-6 jours.
- Les pires séries IS (May 2024 6-streak, Feb 2025 6-streak) ne sont **pas** captées par ces filtres :
  - May 2024 : foot fin de saison (Pro League/Saudi/relegation playoffs), volume normal, pas de MLB
  - Feb 2025 : Champions League knockout phase + 4-leg lottery loose, **75 candidats/jour** (volume normal)
- Sur OOS S1-2026 (qui contient justement majoritairement des mois Q1 + avril, donc **peu de fenêtre summer-mid-week**), aucune blacklist ne change la dynamique. La série rouge max=3 OOS est *déjà* meilleure que IS sans filtre.
- V6 (la plus restrictive) **augmente** la série rouge IS de 6 → 7 : skipper des jours coupe les streaks mais en colle d'autres ensemble.

**Conclusion technique** : les séries rouges 4-6j observées sont du **risque queue de Bernoulli** intrinsèque à un système 4-7 combos/j à WR ~64% global, pas un pattern blacklistable. À WR=0.64 sur 6 paris indépendants : P(streak≥4) sur 730 jours ≈ 30-40% naturellement, ce qu'on observe.

**Recommandation pratique** :
1. **Ne pas implémenter de blacklist date/category** : aucune ne tient OOS.
2. Si réduction de série rouge prioritaire : utiliser le `skip_after_loss` natif de l'API (déjà implémenté dans web/app.py) — éprouvé pour casser les momentum.
3. Sinon, accepter que red streak 4-6j fait partie de la signature statistique du preset et **dimensionner la bankroll** pour absorber DD≈190€ (≈19× stake).

## Annexes

- Script forensique reproductible : `/tmp/global_cand.pkl` cache toutes les pools candidats par (jour, composante)
- Sources analysées : `/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified/*.csv` (852 jours indexés)
- Ground truth preset : `/Users/maxenceleguay/Sites/winnaHisto/web/app.py` lignes 725-900 + `_is_league_allowed` ligne 647
