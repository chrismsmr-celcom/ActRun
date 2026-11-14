# Exemple 01 : Conflit entre deux agents

Ce scénario démontre comment **ActRun** gère la coordination de deux agents IA qui travaillent en parallèle sur le même état partagé.

## Scénario
Deux agents collaborent pour organiser un événement :
- **Agent Marketing** : Gère le budget et la liste d'invités marketing
- **Agent Logistique** : Gère le lieu et la liste d'invités logistique

## Démonstration
1. Les deux agents créent des branches et travaillent en parallèle
2. Ils modifient des clés différentes → **Auto-merge réussi** (coopération)
3. Les deux essaient de modifier le lieu → **Conflit détecté** (protection)
4. Utilisation des leases pour prévenir les conflits
