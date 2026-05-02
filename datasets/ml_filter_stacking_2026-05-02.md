# ML Filter Stacking sur Multi_full — S1-2026 walk-forward

**Date :** 2026-05-02
**Auteur :** Agent (mission stacking LightGBM × Multi_full)
**Hypothèse :** filtrer les legs de Multi_full avec une probabilité LightGBM minimale améliore-t-il le ROI ou réduit-il la série rouge ?

---

## 1. Setup expérimental

- **Datasets :** `/Users/maxenceleguay/Sites/winnaHisto/datasets/sofascore_unified/*.csv` (5 sports, 684 222 lignes brutes → 675 543 valides)
- **Train LightGBM :** 2024-01-01 → 2025-12-31 (541 040 matchs)
- **Test walk-forward S1-2026 :** 2026-01-01 → 2026-04-30 (134 503 matchs, 120 jours)
- **Features (15) :** `odds_1, odds_2, odds_x_filled, has_draw, 1/odds_1, 1/odds_2, odds_1/odds_2, dow, month, league_freq` (frequency-encoded sur train), one-hot des 5 sports
- **Hyperparams :** `objective=binary, lr=0.05, max_depth=6, num_leaves=31, n_estimators=400, early_stopping=20` sur 15 % val interne
- **Cible :** `home_won` binaire (Draw exclu de la cible mais conservé dans le pool de matchs)

**Performance LightGBM seul sur S1-2026 :** accuracy = **0.6869** (cohérent avec Agent A).

**Distribution P_LGB sur test :** p10=0.21 / p25=0.35 / p50=0.52 / p75=0.70 / p90=0.84
- Frac > 0.55 : 46 %  Frac > 0.65 : 32 %  Frac > 0.70 : 24 %

---

## 2. Méthodologie filtre ML

**Multi_full preset (web/app.py :272) — 7 composantes, dedup `max1`, bookmaker Winamax FR :**

| # | max_legs | cote_min | cote_max | sort_by | sports                                                       | max_combos |
|---|---------:|---------:|---------:|---------|--------------------------------------------------------------|-----------:|
| 1 |        2 |     1.40 |     2.00 | wr      | football                                                     |          2 |
| 2 |        2 |     1.40 |     2.00 | wr      | basketball                                                   |          2 |
| 3 |        2 |     1.30 |     2.00 | wr      | tennis                                                       |          1 |
| 4 |        2 |     1.40 |     2.50 | wr      | ice-hockey                                                   |          1 |
| 5 |        3 |     2.00 |     5.00 | ev      | football, basketball                                         |          2 |
| 6 |        4 |     5.00 |    15.00 | ev      | football, basketball, ice-hockey, baseball, tennis           |          1 |
| 7 |        5 |    15.00 |    60.00 | ev      | football, basketball, ice-hockey, baseball, tennis           |          1 |

**Règle filtre ML appliquée à chaque leg :**
- side = "1" (home) → on exige `P_LGB > seuil`
- side = "2" (away) → on exige `1 − P_LGB > seuil`
- side = "X" (draw) → pas de filtre (LightGBM n'a pas appris la classe nul)

Si **au moins 1 leg** échoue, le combo entier est skippé et le candidat suivant de la même composante est tenté (pool = 12× max_combos). La dedup `max1` est appliquée *après* l'acceptation ML pour ne pas bloquer les picks rejetés.

**Stake :** flat 10 €/combo. Pas de `skip_after_loss`. Bankroll initiale 100 €.

---

## 3. Résultats comparatifs (S1-2026, 120 jours)

| Version              | n_combos | n_won | WR combos | Stake total | PnL total  | ROI       | Daily WR | Série rouge max | Max DD   | n_jours_joués |
|----------------------|---------:|------:|----------:|------------:|-----------:|----------:|---------:|----------------:|---------:|--------------:|
| **Standard (no filter)** | **621** | 293 | 47.18 %   | 6 210 €     | **+5 384,04 €** | **+86.70 %** | **66.67 %** | **4**           | 178,19 € | 120 |
| Filter P_LGB > 0.55  |      402 |   235 | 58.46 %   | 4 020 €     | +1 578,21 € | +39.26 %  | 60.83 %  | 4               |  90,85 € | 120 |
| Filter P_LGB > 0.65  |      302 |   181 | 59.93 %   | 3 020 €     | +1 052,25 € | +34.84 %  | 58.41 %  | 5               |  98,98 € | 113 |
| Filter P_LGB > 0.75  |      229 |   138 | 60.26 %   | 2 290 €     |   +719,88 € | +31.44 %  | 52.83 %  | **9**           |  97,03 € | 106 |

**Note :** la 4e ligne testée à 0.70 (et non 0.75 — ajusté pour comparer 3 seuils répartis 0.55 / 0.65 / 0.70).

### Combien de combos filtrés par seuil ?

| Seuil | Combos examinés | Combos rejetés ML | Taux rejet |
|-------|----------------:|------------------:|-----------:|
| 0.55  | 2 334           | 1 932             | 82.78 %    |
| 0.65  | 3 242           | 2 940             | 90.68 %    |
| 0.70  | 4 001           | 3 772             | 94.28 %    |

(Le pool de candidats grossit avec le seuil parce que la sélection consomme plus de candidats avant de remplir les `max_combos` par composante.)

---

## 4. Analyse

### Effets du filtre ML

1. **Win-rate par combo** : passe de 47.2 % → 60.3 % au seuil 0.70 (+13 pts). Le filtre identifie bien les legs solides.
2. **PnL total s'effondre** : −70 % à seuil 0.55, −80 % à 0.65, **−87 %** à 0.70.
3. **Drawdown réduit** : 178 € → ≈97 € sur les versions filtrées (−45 %), donc gestion du risque améliorée *en niveau absolu*.
4. **Série rouge** : stable à 4 pour seuil 0.55, mais **dégrade à 5 puis 9** pour 0.65/0.70. Contre-intuitif : moins de combos par jour = plus de variance de blanchissage par jour.
5. **Daily WR** : baisse continue 66.7 % → 52.8 %. À 0.70 on perd 14 jours non-joués (zéro combo retenu).

### Pourquoi le filtre détruit le PnL malgré une meilleure WR

Les combos Multi_full sont triés par **wr** ou **ev**, donc le système choisit déjà par construction les meilleures cotes magiques (cotes ⊂ buckets `wr ≥ 0.55-0.65` côté safe, `ev > 0.5` côté EV). Filtrer encore par `P_LGB > 0.65/0.70` :

- **Élimine les EV3j/EV4j/EV5j multi-sport** : cotes 5–60 → P_LGB(home) typiquement < 0.50 sur le favori d'une cote 5.0+. Les jambes longues sont presque toujours rejetées.
- **Casse la compounding multi-jambe** : un combo 5 jambes a P(toutes_legs_passent_filtre) ≈ p^5. Même p=0.5 ⇒ 3 % survie.
- **Sélectionne des picks sur-favoris** dont la cote magique a déjà capturé l'edge → on paie 2× la même information et on perd l'effet "cotes magiques contraires" qui faisait le ROI Multi_full.

### Verdict

**Le ML filter NE PAS améliore Multi_full.** Standard : +86.7 % ROI. Toutes les versions filtrées font moins bien sur les 4 métriques composites :

| Métrique         | Vainqueur    |
|------------------|--------------|
| ROI %            | Standard ⭐  |
| PnL absolu       | Standard ⭐  |
| Daily WR         | Standard ⭐  |
| Série rouge max  | Standard / 0.55 (égalité) |
| Max DD           | 0.55         |
| WR par combo     | 0.70         |

Seul **Filter > 0.55** garde un comportement défendable (ROI +39 %, DD divisé par 2, série rouge 4) — utilisable comme **mode défensif** pour les phases bankroll fragile, mais le coût d'opportunité est −3 800 € sur le semestre.

Pour 0.65/0.70 : filtrage trop agressif, dégrade aussi la série rouge (+25 % à +125 %).

### Pistes alternatives à explorer (non testées ici)

- Filtre asymétrique : ML filter **uniquement** sur les legs `wr`-sort (composantes 1-4 safe), pas sur les EV-sort (composantes 5-7).
- Seuil glissant par sport : +0.65 sur ice-hockey (où Agent A a observé +4.97 % ROI), +0.55 sur foot, pas de filtre tennis/baseball.
- Seuil sur **somme** des P_LGB du combo plutôt que par leg (effet portfolio).

---

## 5. Conclusion

**Sur S1-2026 walk-forward, ajouter un filtre LightGBM sur les legs de Multi_full dégrade le PnL total dans toutes les configurations testées.** L'amélioration de la WR par combo (+13 pts à seuil 0.70) ne compense pas la chute du nombre de combos joués et la perte des EV-multi long-shot. Multi_full standard reste la baseline à battre. Une approche d'ensemble plus fine (filtre asymétrique safe-only, seuils par sport) reste à tester avant de conclure que le stacking est inutile.

**Recommandation actionnable :** garder Multi_full standard. Si volonté de réduire le DD, utiliser `Filter P_LGB > 0.55` en mode défensif (ROI +39 %, DD divisé par 2) — pas comme remplaçant.
