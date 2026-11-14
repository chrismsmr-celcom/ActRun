# Exemple 02 : Leases et Deadlocks

Ce scénario démontre comment **ActRun** détecte et prévient les deadlocks dans les systèmes multi-agents.

## Le problème du deadlock

Un deadlock se produit quand plusieurs agents se bloquent mutuellement en attendant des ressources détenues par les autres.

### Scénario classique : Le dîner des philosophes
- **Agent A** détient la ressource `fourchette_gauche` et attend `fourchette_droite`
- **Agent B** détient la ressource `fourchette_droite` et attend `fourchette_gauche`
- → **DEADLOCK** : Les deux agents attendent indéfiniment

## Ce que fait ActRun

1. **Détection automatique** : ActRun construit un graphe d'attente (Wait-for Graph) et détecte les cycles
2. **Prévention** : Quand un deadlock est détecté, une exception `DeadlockError` est levée immédiatement
3. **Résolution** : L'agent peut alors libérer une ressource pour briser le cycle

## Démonstration

Lance le script :
```bash
python run.py
