# RAG API – Givaudan Opportunity Radar (équipe G03)

Fork de [hmicn/example-rag](https://github.com/hmicn/example-rag), modifié pour le Givaudan AI Challenge.

**Nouvelle route : `POST /questions-client`**. Elle prend le **nom d'un client** et retourne **3 questions à poser avant le premier appel**. Le modèle les génère à partir de la fiche du client, retrouvée dans la base vectorielle (RAG). **Toutes les données sont fictives.**

## Fonctionnement

```
nom du client ──► recherche de SA fiche (ChromaDB, filtrée sur ce client)
              ──► LLM Ollama avec un schéma JSON imposé (3 questions)
              ──► 3 questions {question, objectif, information_recherchee}
                  + les extraits de la fiche utilisés (traçabilité)
```

- **Ingestion** : `ingest_clients.py` découpe les 6 fiches (`fiches_clients/client_*.md`) par section (identité, ce qu'il faut savoir, projets, opportunités et signaux, historique, à confirmer), calcule leurs embeddings avec `nomic-embed-text` et les range dans la collection `clients`.
- **Pas de recopie** : les fiches ingérées ne contiennent pas les questions préparées par l'équipe. Le modèle doit donc écrire les siennes.
- **Pas de mélange** : la recherche est filtrée sur l'identifiant du client.
- **Contrôle des questions** : une question mal formée, ou qui emploie le vocabulaire interne (« opportunité », « signal », « à qualifier »…), est écartée : elle ne pourrait pas être posée telle quelle à un client.
- **Plan B** : les questions écartées sont remplacées par des questions préparées par l'équipe Data (`fiches_clients/fiches_clients.json`). Le champ `source` vaut `modele` (3 questions du LLM), `mixte` (LLM complété) ou `simule` (Ollama absent ou trop lent : 3 questions préparées). Chaque question porte son `origine` : `modele` ou `prepare`.

## Démarrage rapide (Git Bash, Windows)

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull qwen2.5:1.5b            # ou gemma2:2b, voir « Choix du modèle »
python ingest_clients.py            # charge les 6 fiches clients
python -m pytest -q                 # 16 tests (Ollama non nécessaire)
uvicorn api:app --port 8001         # Swagger : http://127.0.0.1:8001/docs
ngrok http 8001                     # mise en ligne temporaire
python evaluer.py                   # évaluation sur 30 cas → docs/evaluation.md
```

Exemple :
```bash
curl -s -X POST http://127.0.0.1:8001/questions-client -H "Content-Type: application/json" -d '{"client":"PepsiCo"}'
```
Le nom accepte les variantes de majuscules et d'accents (`nestle` donne Nestlé) et les noms partiels d'au moins 3 lettres (`nordic food`). Un nom inconnu ou ambigu est refusé (404), avec la liste des clients disponibles. `GET /clients` liste les noms disponibles. On peut choisir le modèle par requête avec `"model": "gemma2:2b"`.

## Routes ajoutées

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/clients` | Liste des 6 clients disponibles |
| POST | `/questions-client` | `{"client": "PepsiCo", "model": "optionnel", "top_k": 6}` → 3 questions, source, modèle, durée, extraits utilisés |
| GET | `/questions-client/{client}` | Même résultat, avec le nom dans l'adresse (pratique dans un navigateur) : `/questions-client/PepsiCo` |

Depuis un navigateur, à travers ngrok, ajouter l'en-tête `ngrok-skip-browser-warning: true`. Les appels entre domaines (CORS) sont autorisés.

## Fichiers ajoutés

| Fichier | Rôle |
|---|---|
| `clients.py` | Route `/questions-client` : recherche du client, prompt système, schéma JSON imposé, lecture tolérante, plan B |
| `ingest_clients.py` | Ingestion des fiches clients dans la collection `clients` |
| `fiches_clients/client_*.md` | Les 6 fiches ingérées (sans les questions préparées) |
| `fiches_clients/fiches_clients.json` | Les 6 fiches complètes, avec les questions préparées (plan B) |
| `fiches_clients/modele_fiche_client.json`, `prompt_fiche_client.md` | Modèle standard de fiche et prompt (livrables du formateur) |
| `fiches_clients/generer_fiches_md.py` | Régénère les fiches `.md` à partir du JSON |
| `test_clients.py` | 16 tests : ingestion sans recopie, pas de mélange entre clients, nom approximatif, noms refusés, plan B, réponse mal formée, évaluation |
| `evaluer.py` | Évaluation sur 30 cas de référence (12 recherche, 12 noms, 6 génération) et comparaison V1/V2. Écrit `docs/evaluation.md` |

## Choix du modèle (mesures du 12/11/2026, PC portable sans carte graphique)

| Modèle | Durée observée | Remarque |
|---|---|---|
| `qwen2.5:1.5b` (défaut) | ~45 s | Rapide, mais format moins fiable sans schéma |
| `gemma2:2b` | ~70 s | Meilleur respect du format |
| `llama3.2:1b`, `llama3.2:3b` | 27 s / 98 s | Format souvent non respecté sans schéma |

Ces mesures ont été faites sur une autre route, avant l'ajout du schéma JSON imposé. Les résultats à jour sont dans `docs/evaluation.md`, produit par `python evaluer.py --model <modèle>`.

## Limites
- Données fictives (6 clients, dont des noms de marques utilisés à titre d'illustration).
- Petit modèle local : qualité variable et temps de réponse long. Le plan B garantit une réponse.
- L'API tourne sur le PC de l'équipe : l'adresse ngrok n'est valable que pendant qu'il est allumé.

---

## Partie d'origine : questions sur une histoire (`story.txt`)


Pose des questions sur une histoire pour enfants (`story.txt`) via une API FastAPI.
Les passages pertinents sont retrouvés dans une base vectorielle (ChromaDB), puis un
LLM Ollama rédige la réponse.

## Fichiers du projet

| Fichier            | Rôle |
|--------------------|------|
| `story.txt`        | L'histoire pour enfants, source des réponses. Le titre est sur la première ligne, les chapitres commencent par « Chapitre N : … » ou « I. … ». |
| `ingest.py`        | Charge l'histoire dans la base : découpe le texte par chapitre en morceaux d'environ 800 caractères, calcule leurs embeddings avec Ollama et les enregistre dans ChromaDB. Peut être relancé sans créer de doublons. Accepte un autre fichier en argument : `python ingest.py autre.txt`. |
| `clean.py`         | Vide la base (supprime la collection ChromaDB), pour recharger l'histoire ou changer de modèle d'embeddings. |
| `api.py`           | L'API FastAPI avec son Swagger : retrouve les passages proches de la question, puis demande au LLM d'y répondre simplement, comme à un enfant. Contient aussi le prompt système. |
| `list.py`          | Affiche le contenu de la base : modèle d'embeddings utilisé, nombre de morceaux, puis chaque morceau (identifiant, taille, aperçu du texte) groupé par chapitre. Avec `--full`, affiche le texte complet. |
| `rag.py`           | Code partagé par les scripts : connexion à ChromaDB, calcul des embeddings et appel du LLM via Ollama. |
| `config.py`        | Tous les réglages (modèles, chemins, taille des morceaux, nombre de passages), modifiables par variables d'environnement. |
| `requirements.txt` | Dépendances Python : FastAPI, Uvicorn, Ollama, ChromaDB, pytest. |
| `.gitignore`       | Exclut de git le venv, la base `chroma_db/`, les caches Python et les fichiers locaux. |
| `chroma_db/`       | Base vectorielle créée par `ingest.py` (non versionnée). |

## Installation

Prérequis : Python 3.10+ et [Ollama](https://ollama.com) lancé en local.

### 1. Créer et activer un environnement virtuel

```bash
python -m venv .venv
```

Puis l'activer selon votre terminal :

| Terminal                  | Commande                          |
|---------------------------|-----------------------------------|
| Windows PowerShell        | `.venv\Scripts\Activate.ps1`      |
| Windows cmd               | `.venv\Scripts\activate.bat`      |
| Git Bash (Windows)        | `source .venv/Scripts/activate`   |
| macOS / Linux             | `source .venv/bin/activate`       |

Si PowerShell refuse d'exécuter le script d'activation, autorisez-le pour votre
utilisateur une fois pour toutes :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Le nom `(.venv)` apparaît alors au début de l'invite. Pour sortir du venv : `deactivate`.

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Télécharger les modèles Ollama

```bash
ollama pull nomic-embed-text   # modèle d'embeddings
ollama pull qwen2.5:1.5b         # LLM (ou un autre, voir Configuration)
```

## Utilisation

```bash
python ingest.py        # charge story.txt dans la base (chroma_db/)
python list.py          # affiche le contenu de la base (--full pour le texte complet)
python clean.py         # vide la base
python api.py           # lance l'API sur http://127.0.0.1:8000
```

Swagger : http://127.0.0.1:8000/docs

Pour recharger après modification de l'histoire : `python clean.py` puis `python ingest.py`.

## Endpoints

| Méthode | Route     | Rôle                                                   |
|---------|-----------|--------------------------------------------------------|
| GET     | `/health` | Nombre de morceaux en base et modèles utilisés         |
| POST    | `/search` | Passages retrouvés seulement (sans LLM), pour déboguer |
| POST    | `/ask`    | Réponse du LLM + passages sources                      |

Corps de requête : `{"question": "Comment s'appelle le cheval de Léo ?", "top_k": 4}`

## Configuration (variables d'environnement)

| Variable      | Défaut              |
|---------------|---------------------|
| `LLM_MODEL`   | `qwen2.5:1.5b`        |
| `EMBED_MODEL` | `nomic-embed-text`  |
| `OLLAMA_HOST` | `http://localhost:11434` |
| `CHROMA_DIR`  | `./chroma_db`       |
| `STORY_PATH`  | `./story.txt`       |
| `CHUNK_SIZE`  | `800` (caractères)  |
| `TOP_K`       | `4`                 |

Si vous changez `EMBED_MODEL`, relancez `clean.py` puis `ingest.py` : les vecteurs
de deux modèles différents ne sont pas compatibles.
