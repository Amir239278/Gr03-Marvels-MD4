# Évaluation de la route `/questions-client` sur 30 cas de référence

Généré par `python evaluer.py` le 12/11/2026 à 21:35. Modèle de génération : `qwen2.5:1.5b`. Embeddings : `nomic-embed-text`. Données fictives.

## Résultat global

**29/30 cas réussis.**

| Famille de cas | Nombre | Réussis | Critère de réussite |
|---|---|---|---|
| Recherche (base vectorielle) | 12 | 12 | La fiche du bon client arrive en 1re position (top 3 : 12/12) |
| Nom du client | 12 | 12 | Nom approximatif reconnu, nom inconnu ou ambigu refusé |
| Génération V2 | 6 | 5 | 3 questions du modèle valides (bon format, sans vocabulaire interne), sans nom d'un autre client, au moins 1 question ancrée dans la fiche |

Questions du modèle retenues : 17/18. Les questions écartées (mal formées ou au vocabulaire interne) sont remplacées par des questions préparées.

Durée de génération V2 : médiane 34 s, maximum 50 s.

## Comparaison V1 / V2 (format respecté)

| Version | Méthode | Format respecté | Durée médiane |
|---|---|---|---|
| V1 | Prompt seul, JSON libre, lecture stricte | 0/6 | 16 s |
| V2 | Schéma JSON imposé à Ollama + lecture tolérante | 5/6 | 34 s |

## Détail : génération

| Client | Source | Questions du modèle | Catégories distinctes | Sans fuite | Questions ancrées | Durée | Réussi |
|---|---|---|---|---|---|---|---|
| Maison Nova Drinks | modele | 3/3 | 3/3 | ✅ | 3/3 | 50 s | ✅ |
| Nordic Food Industries | modele | 3/3 | 2/3 | ✅ | 2/3 | 34 s | ✅ |
| Alimenta Distribution | mixte | 2/3 | 3/3 | ✅ | 3/3 | 32 s | ❌ |
| PepsiCo | modele | 3/3 | 2/3 | ✅ | 3/3 | 41 s | ✅ |
| Danone | modele | 3/3 | 3/3 | ✅ | 3/3 | 34 s | ✅ |
| Nestlé | modele | 3/3 | 2/3 | ✅ | 2/3 | 33 s | ✅ |

### Questions générées par le modèle (à relire par un humain)

**Maison Nova Drinks**
- [Objectifs du client] Quelles sont les objectifs spécifiques de la nouvelle gamme de boissons fonctionnelles que nous avons discutées récemment ? *(Identifier les objectifs spécifiques de la nouvelle gamme de boissons fonctionnelles pour comprendre les besoins et les attentes du client.)*
- [Contraintes techniques] Quels sont les contraintes techniques spécifiques à la formulation de cette nouvelle gamme de boissons fonctionnelles ? *(Rechercher les contraintes techniques spécifiques à la formulation de la nouvelle gamme de boissons fonctionnelles pour faciliter la prise de décision.)*
- [Contraintes budgétaires] Quelles sont les contraintes budgétaires spécifiques à la mise en place de cette nouvelle gamme de boissons fonctionnelles ? *(Rechercher les contraintes budgétaires spécifiques à la mise en place de la nouvelle gamme de boissons fonctionnelles pour faciliter la prise de décision.)*

**Nordic Food Industries**
- [Objectifs du client] Quels sont les besoins spécifiques que vous avez identifiés pour votre entreprise actuelle ? *(Identifier les besoins spécifiques de la clientèle pour améliorer les produits Nordic Food Industries.)*
- [Contraintes techniques] Quels sont les contraintes techniques que vous rencontrez dans votre projet actuel ? *(Identifier les contraintes techniques spécifiques pour optimiser la formulation végétale.)*
- [Objectifs du client] Quels sont les objectifs de votre projet actuel pour améliorer la texture d'un produit existant ? *(Identifier les objectifs de la clientèle pour améliorer la texture d'un produit existant.)*

**Alimenta Distribution**
- [Objectifs du client] Quelles sont les principales tendances de consommation observées dans le secteur alimentaire ces derniers mois ? *(Identifier les tendances de consommation actuelles pour évaluer la faisabilité de la nouvelle référence aromatique.)*
- [Besoin réel] Quelle est la demande potentielle pour une nouvelle référence aromatique dans le marché de la distribution alimentaire ? *(Vérifier si la demande existe et si elle pourrait être satisfait par la nouvelle référence.)*

**PepsiCo**
- [Objectifs du client] Quel est le niveau de réduction de sucre que vous souhaitez atteindre pour votre gamme de boissons ? *(Identifier les objectifs de réduction de sucre que le client souhaite atteindre pour une gamme de boissons.)*
- [Contraintes techniques] Quelles sont les contraintes techniques liées à la réduction du sucre dans votre gamme de boissons ? *(Vérifier les contraintes techniques liées à la réduction du sucre pour une gamme de boissons.)*
- [Objectifs du client] Quelle est la date de la prochaine action pour la réduction du sucre dans votre gamme de boissons ? *(Confirmer les objectifs de réduction de sucre et les contraintes de goût pour une gamme de boissons.)*

**Danone**
- [Objectifs du client] Quels sont les avantages potentiels de la production d'un produit laitier végétal pour Danone ? *(Identifier les avantages potentiels de la production d'un produit laitier végétal pour comprendre l'intérêt du client pour cette alternative.)*
- [Contraintes techniques] Quelles sont les principales contraintes techniques à considérer pour la production d'un produit laitier végétal ? *(Analyser les contraintes techniques pour évaluer la faisabilité de la production d'un produit laitier végétal.)*
- [Calendrier] Quelle est la date de début de l'opération de production de produits laitiers végétaux pour Danone ? *(Confirmer la date de début de l'opération de production de produits laitiers végétaux pour Danone, afin de planifier les actions futures.)*

**Nestlé**
- [Objectifs du client] Quels sont les besoins spécifiques de la clientèle de Nestlé en matière de goût pour les produits de la nutrition ? *(Identifier les besoins spécifiques de la clientèle pour les produits de la nutrition.)*
- [Contraintes techniques] Quels sont les contraintes techniques de la formulation actuellement à confirmer pour la boisson nutritionnelle ? *(Rappeler les contraintes techniques de la formulation à confirmer.)*
- [Objectifs du client] Quels sont les intérêts exprimés par la clientèle de Nestlé pour de nouveaux goûts dans le contexte du projet de barre protéinée ? *(Identifier les intérêts exprimés par la clientèle pour de nouveaux goûts.)*

## Détail : recherche

| Requête (intitulé de l'opportunité) | Client attendu | Top 1 | Top 3 |
|---|---|---|---|
| Nouvelle gamme de boissons fonctionnelles | Maison Nova Drinks | ✅ | ✅ |
| Extension d'une gamme aromatique | Maison Nova Drinks | ✅ | ✅ |
| Développement d'une formulation végétale | Nordic Food Industries | ✅ | ✅ |
| Amélioration de la texture d'un produit | Nordic Food Industries | ✅ | ✅ |
| Optimisation d'une formulation existante | Nordic Food Industries | ✅ | ✅ |
| Nouvelle référence aromatique pour une marque de distributeur | Alimenta Distribution | ✅ | ✅ |
| Réduction du sucre sur une gamme de boissons | PepsiCo | ✅ | ✅ |
| Snacks à teneur réduite en sel | PepsiCo | ✅ | ✅ |
| Nouvelle saveur saisonnière pour une boisson | PepsiCo | ✅ | ✅ |
| Alternative végétale à un produit laitier | Danone | ✅ | ✅ |
| Masquage d'amertume sur une boisson enrichie en protéines | Nestlé | ✅ | ✅ |
| Extension de la gamme de barres protéinées | Nestlé | ✅ | ✅ |

## Détail : nom du client

| Nom saisi | Résultat attendu | Réussi |
|---|---|---|
| `pepsico` | PepsiCo | ✅ |
| `NESTLE` | Nestlé | ✅ |
| `nordic food` | Nordic Food Industries | ✅ |
| `Maison Nova` | Maison Nova Drinks | ✅ |
| `  danone ` | Danone | ✅ |
| `alimenta distribution` | Alimenta Distribution | ✅ |
| `Coca-Cola` | refus | ✅ |
| `Unilever` | refus | ✅ |
| `xyz` | refus | ✅ |
| `n` | refus | ✅ |
| `(vide)` | refus | ✅ |
| `Pepsi Danone` | refus | ✅ |

## Limites de cette évaluation

- Les cas sont écrits par l'équipe Data, sur 6 clients fictifs : les résultats ne se généralisent pas.
- « Ancrée » et « sans fuite » sont des contrôles automatiques par mots-clés. Ils ne jugent pas la pertinence.
- La pertinence des questions doit être relue par un humain, idéalement un commercial senior.
- Une seule exécution par cas : un petit modèle peut donner un résultat différent d'une fois à l'autre.
