# 🪜 Montantes PROGRESSIVES — Adaptation par palier

**Concept** : à chaque palier, changer les critères (cote, sport, market) selon le capital actuel.

Validé sur S1-26 OOS strict + Winamax FR.

---

## 🏆 TOP 5 PROGRESSIVES (ordonnées par PnL)

### #1 Multi-sport progressive 4p (+422€ !)
| Palier | Sports | Cote | Logique |
|--------|--------|------|---------|
| 1 | Foot+Hockey | 1.20-1.40 | Démarrage safe |
| 2 | Foot+Hockey | 1.30-1.50 | Mid-cote, capital ×1.3 |
| 3 | Foot+Hockey+Basket | 1.35-1.55 | Élargit le pool |
| 4 | Foot+Hockey+Basket | 1.45-1.70 | Aggressive en finale |

**Résultat** : 38 cycles ✓ / 105 (36%), cap 39€, **PnL +422€** S1-26
**Logique** : élargir le pool de matchs disponibles à mesure que les paliers avancent.

### #2 Foot O 1.5 prudent then aggro 3p (+313€)
| Palier | Cote | |
|--------|------|---|
| 1 | 1.30-1.45 | Safe, ~85% WR |
| 2 | 1.40-1.60 | Mid-cote |
| 3 | 1.50-1.75 | Pousse plus loin |

**Résultat** : 31/62 (50% completion !), cap 30€, **+313€**

### #3 Hockey aggressive then safer 3p (+308€)
| Palier | Cote | |
|--------|------|---|
| 1 | 1.45-1.70 | Aggressive (capital initial petit, ok de risquer) |
| 2 | 1.30-1.50 | Mid-cote |
| 3 | 1.20-1.40 | Safe (consolide les gains) |

**Résultat** : 39/73 (53% completion), cap 27€, **+308€**
**Contre-intuitif mais valide** : commence aggressive (peu à perdre), termine safe (capital gros à protéger).

### #4 Foot O 1.5 progressive 4p (+272€)
| Palier | Cote |
|--------|------|
| 1 | 1.10-1.25 |
| 2 | 1.20-1.40 |
| 3 | 1.30-1.50 |
| 4 | 1.45-1.70 |

**Résultat** : 33/70 (47%), cap 29€, **+272€**

### #5 Foot O 1.5 progressive 3p (+267€, 60% completion ★)
| Palier | Cote |
|--------|------|
| 1 | 1.10-1.25 |
| 2 | 1.25-1.45 |
| 3 | 1.40-1.65 |

**Résultat** : 58/97 (**60% completion !**), cap 21€, **+267€**
**Top completion** des progressives.

---

## ❌ Patterns qui MARCHENT MOINS BIEN

| Config | PnL | Pourquoi |
|--------|-----|----------|
| Foot O 1.5 single → combo 2j → 3j | +139€ | Combos rendent les paliers fragiles |
| Foot xmkt progressive (OU 1.5 → OU 2.5 → BTTS) | +76€ | Markets différents = bruit |
| Foot p1 → Hockey p2 → Basket p3 | -31€ | Changer de sport tue le timing |

**Leçon** : les progressions les plus efficaces gardent **le même sport/market** et n'augmentent que la **cote** progressivement. Changer trop de variables casse la cohérence.

---

## 📊 Comparaison avec montantes "fixes"

| Stratégie | Type | PnL S1 | Completion |
|-----------|------|--------|------------|
| Multi-sport progressive 4p | progressive | +422€ | 36% |
| `montante_o25_x2p_TOP_PRACTICAL` | fixe | +528€ | 44% |
| `montante_hockey_combo2j_x3p_top_pnl` | fixe | +731€ | 36% |

**Verdict** : Les montantes progressives sont **équivalentes ou légèrement inférieures** aux meilleures montantes fixes en termes de PnL. Mais elles offrent plus de flexibilité et permettent de **mixer plusieurs sports/cotes** en une seule stratégie.

---

## Implementation

Pour utiliser ces progressives dans le live, il faudrait étendre `montante_engine.py` pour accepter un format :

```json
{
  "id": "montante_progressive_multisport_4p",
  "mode": "montante",
  "montante": {
    "n_paliers_target": 4,
    "preferred_mode": "intraday",
    "palier_configs": [
      {"sports": ["football","ice-hockey"], "market": "1x2", "cote_min": 1.20, "cote_max": 1.40},
      {"sports": ["football","ice-hockey"], "market": "1x2", "cote_min": 1.30, "cote_max": 1.50},
      {"sports": ["football","ice-hockey","basketball"], "market": "1x2", "cote_min": 1.35, "cote_max": 1.55},
      {"sports": ["football","ice-hockey","basketball"], "market": "1x2", "cote_min": 1.45, "cote_max": 1.70}
    ]
  }
}
```

**Status** : sauvegardé dans `datasets/progressive_montantes.json` pour analyses futures, pas encore en prod.

## Conclusion

Les progressives sont **un outil intéressant mais pas un game-changer** dans cette lib. Les top winners restent les montantes fixes courtes (×2P-×3P) avec ≥40% completion. Mais le pattern "**aggressive then safer**" sur Hockey est un nouveau profil intéressant — protéger le capital quand il grossit.
