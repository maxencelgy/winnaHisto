# Stratégies parieurs — sources Reddit / Telegram / Discord / forums FR

Synthèse 2026-05-03. Pistes exploitables pour le pipeline H9 (au-delà du flat 10% sur edges détectés).

## 1. CLV (Closing Line Value) — métrique nº1

- Le CLV sépare les 3-5% de parieurs profitables du reste.
- **Action pipeline** : logger pour chaque pick H9 la cote prise vs cote de fermeture Pinnacle. ROI sans CLV+ = bruit.
- Outil de référence : Pinnacle Odds Dropper (alerte quand Pinnacle baisse une cote → soft books en retard 20s-3min).

## 2. Sharp follower (copie Pinnacle)

- Pinnacle = book sharp, ne limite pas les gagnants, marge faible. Ses cotes sont la "vraie" proba.
- Stratégie : prendre la cote de-vigée Pinnacle, comparer à Winamax. Si Winamax > Pinnacle no-vig → value.
- **Action** : ajouter scraper Pinnacle au pipeline. Croiser avec Winamax pré-match.

## 3. Marchés inefficaces

- Tennis de table, e-sports, sports féminins, lignes basses ATP/WTA → bookies copient sharps avec lag.
- Tennis : ELO pondéré par surface = ROI 2.93-3.56% prouvé (papiers académiques 2012-2020).
- **Action** : étendre `sofascore_massive.py` pour capturer ITF/Challenger tennis + ligues mineures foot.

## 4. Live betting — exploiter le lag

- Algos sportsbooks réagissent en retard sur : carton rouge, blessure, momentum shift.
- Edge : feed temps réel (stadium scout) + execution rapide < délai book.
- Risqué mais exploitable sur Winamax in-play foot/tennis premiers points/minutes.

## 5. Modèles open-source à étudier

- `georgedouzas/sports-betting` (PyPI) — backtest CLV systématique.
- `emm5317/betbot` — NHL xG + goalie, MLB/NBA/NFL ML, calibration reports.
- Poisson sur Over/Under 2.5 foot = baseline solide.

## 6. Trading Betfair (alternative Winamax)

- Scalping pré-match (10-15min avant) = haute liquidité, ticks 2.14→2.12.
- Pas soumis à limitations comme Winamax. Premium Charge 20-60% si gros gagnant.
- Outil : Geeks Toy. Adapté pour scalper trading H9 si tu veux scaler.

## 7. Anti-limitation Winamax

- Winamax limite même les perdants (cf thread Club Poker 227565).
- Mitigations forum :
  - Pas que des values bets, alterner avec mises "publiques"
  - Mise variable (pas toujours flat 10%)
  - Pas de cash-out systématique
  - Étaler les paris sur la journée
- ARJEL refuse bonus hunting cross-comptes (fraude).

## 8. Telegram / Discord — sources brutes

- **Sharp App Discord** (9k+ membres) — +EV alerts, scan 100+ books.
- **SEVA Discord** — Sharp/EV/Arbitrage.
- Tipsters Telegram = 95% du bruit. Ignorer sauf preuve CLV+ historique.

## 9. Strats Pronosoft / Clubpoker FR

- Handicap asiatique réduit variance vs 1N2 → courbe ROI plus propre, moins de séries négatives.
- Value bet Serie A historique (thread 2005+) : ROI 12% sur 5 ans en spécialisation niche.
- Live foot Ligue 1 — analyser 15 premières minutes pour cotes gonflées.

## 10. Pistes à tester pour H9

1. **Filtre CLV** : rejeter pick si cote Winamax < cote no-vig Pinnacle au moment T-1h.
2. **Étendre niches** : ITF tennis, ligues mineures foot, table tennis (volume edges Sofascore).
3. **Anti-detection Winamax** : bruit dans la sélection (10% picks "mainstream" non-edge).
4. **Handicap asiatique** : réécrire un sous-modèle H9 sur AH ±0.5 / ±1 plutôt que 1N2 pour réduire variance.
5. **Live trigger** : alerte Telegram bot si edge > seuil détecté en in-play (carton, blessure non pricée).

## Sources principales

- [Reddit Ultimate Guide](https://worldinsport.com/reddits-ultimate-guide-to-sports-betting-strategies-you-cant-miss/)
- [Pinnacle Odds Dropper](https://www.pinnacleoddsdropper.com/)
- [Sharp App Discord](https://www.sharp.app/discord)
- [Pronosoft Forum](https://www.pronosoft.com/forums/)
- [Clubpoker thread limitation Winamax](https://www.clubpoker.net/forum-poker/topic/227565)
- [Underdog Chance — inefficient markets](https://www.underdogchance.com/less-efficient-betting-markets/)
- [betstamp tennis ELO surface](https://betstamp.com/education/tennis-betting-strategy-guide)
- [georgedouzas/sports-betting GitHub](https://github.com/georgedouzas/sports-betting)
