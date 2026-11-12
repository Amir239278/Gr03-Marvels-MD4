# Fiche de travail – API RAG « nom du client → 3 questions »

Équipe G03 · Data : Amir Meraka, Ossama Farhaoui, Evrad Marold Okoue Nfane · fiche rédigée par Amir Meraka · mise à jour le 12/11/2026 à 23 h 40.
Cette fiche sert à **suivre, reproduire et expliquer** le travail. Toutes les données sont fictives.

## 1. La demande et son état

| # | Demande du formateur | État | Preuve |
|---|---|---|---|
| 1 | Modifier l'API `hmicn/example-rag` : une route prend le nom d'un client et retourne 3 questions | ✅ Fait | `clients.py`, routes `POST /questions-client` et `GET /questions-client/{client}` |
| 2 | Faire ingérer des fiches clients au modèle choisi | ✅ Fait | `ingest_clients.py` : 6 fiches, 36 morceaux dans ChromaDB |
| 3 | Partager le nouveau dépôt | ✅ Fait | `Amir239278/Gr03-Marvels-MD4`, branche `Amir` |
| 4 | Mettre temporairement en ligne avec ngrok | ✅ Fait | `https://vowel-paramount-lisp.ngrok-free.dev` (tant que le PC est allumé) |
| 5 | Envoyer le lien ngrok et le dépôt à Tech | ✅ Fait | Message à Kevin (section 6) |
| 6 | Livrable du jour avant 23 h 59 | ✅ Fait | `LIVRABLE_DATA_G03.md`, `docs/evaluation.md`, fusionnés dans `main` du dépôt de l'équipe (PR n° 2) |

## 2. Comment ça marche, en 5 phrases

1. Chaque fiche client est un texte découpé en 6 sections (identité, ce qu'il faut savoir, projets, opportunités et signaux, historique, à confirmer).
2. Chaque section est transformée en vecteur par le modèle d'embeddings `nomic-embed-text` et rangée dans la base ChromaDB : c'est **l'ingestion**.
3. Quand on donne un nom de client, l'API retrouve les sections de **sa** fiche dans la base : c'est la **recherche** (le « R » de RAG).
4. Elle envoie ces sections au modèle de langage (`qwen2.5:1.5b`, via Ollama) avec un prompt et un **schéma JSON imposé** : le modèle doit rendre exactement 3 questions.
5. L'API contrôle les questions. Une question mal formée, ou au vocabulaire interne (« opportunité », « signal »…), est remplacée par une question préparée par l'équipe.

## 3. Ce qui a été fait, fichier par fichier

| Fichier | Rôle | Pourquoi |
|---|---|---|
| `fiches_clients/client_1.md` à `client_6.md` | Les 6 fiches ingérées | **Sans** les questions préparées, pour que le modèle écrive les siennes |
| `fiches_clients/fiches_clients.json` | Les fiches complètes, avec 3 questions préparées par client | Plan B si le modèle échoue |
| `fiches_clients/generer_fiches_md.py` | Fabrique les `.md` à partir du JSON | Reproductible |
| `ingest_clients.py` | Ingestion dans la collection `clients` | Demande n° 2 |
| `clients.py` | La route : recherche du client, prompt, schéma, contrôle, plan B | Demande n° 1 |
| `api.py` | Branche la route dans l'API d'origine, autorise les appels depuis un navigateur (CORS) | Les routes d'origine (`/ask`, `/search`) restent en place |
| `rag.py`, `config.py` | Délai maximal, choix du modèle par requête, schéma JSON | Réglages |
| `test_clients.py` | 16 tests automatiques | Preuve que ça marche, sans Ollama |
| `evaluer.py` | Évaluation sur 30 cas, comparaison V1/V2 | Métriques du livrable |

## 4. Reproduire de zéro (Git Bash, Windows)

Prérequis : Python 3.10 ou plus, Ollama **ouvert**, ngrok 3.29 ou plus.

```bash
git clone -b Amir https://github.com/Amir239278/Gr03-Marvels-MD4.git
cd Gr03-Marvels-MD4
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
ollama pull nomic-embed-text
ollama pull qwen2.5:1.5b
python ingest_clients.py        # attendu : OK : 36 morceaux
python -m pytest -q             # attendu : 16 passed
uvicorn api:app --port 8001     # laisser tourner
```
Dans un 2e terminal : `ngrok http 8001`. Dans un 3e :
```bash
curl -s --max-time 180 http://127.0.0.1:8001/questions-client/PepsiCo
python evaluer.py               # environ 10 minutes, écrit docs/evaluation.md
```

## 5. Relancer la démo (après un redémarrage du PC)

| Ordre | Action | Vérification |
|---|---|---|
| 1 | Ouvrir l'application Ollama | – |
| 2 | Terminal 1 : `cd ~/Desktop/Hackathon-GIVAUDON/Gr03-Marvels-MD4`, puis `source ../ia/.venv/Scripts/activate`, puis `uvicorn api:app --port 8001` | `Uvicorn running on http://127.0.0.1:8001` |
| 3 | Terminal 2 : `ngrok http 8001` | `Session Status online` |
| 4 | Terminal 3 : `curl -s https://vowel-paramount-lisp.ngrok-free.dev/health` | `"client_chunks":36` |

Pas besoin de refaire l'ingestion : la base `chroma_db/` reste sur le disque.

## 6. Pour Kevin (Tech)

- **Dépôt** : `https://github.com/Amir239278/Gr03-Marvels-MD4/tree/Amir`. **API** : `https://vowel-paramount-lisp.ngrok-free.dev` (Swagger sur `/docs`).
- **Pas de clé** sur cette API, comme dans le dépôt d'origine. Elle ne sert que des données fictives.
- **Délai** : 30 secondes à 2 minutes par appel avec le modèle. Prévoir un indicateur de chargement, ou appeler à l'ouverture de la page.

```ts
const r = await fetch(`${DATA_AI_URL}/questions-client`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
  body: JSON.stringify({ client: 'PepsiCo' }),
  signal: AbortSignal.timeout(150_000),
});
const { questions, source } = await r.json();
```

| Champ de la réponse | Sens |
|---|---|
| `questions[]` | `question`, `objectif`, `information_recherchee`, `origine` (`modele` ou `prepare`) |
| `source` | `modele` = 3 questions de l'IA ; `mixte` = IA complétée ; `simule` = 3 questions préparées |
| `model`, `duree_s` | Modèle utilisé et temps de génération |
| `extraits[]` | Les sections de la fiche données au modèle (traçabilité) |

Clients disponibles : `GET /clients` (Maison Nova Drinks, Nordic Food Industries, Alimenta Distribution, PepsiCo, Danone, Nestlé). Un nom inconnu renvoie une erreur 404 avec la liste.

## 7. Pour Frédéric (formateur) : questions probables

| Question | Réponse courte |
|---|---|
| Quel modèle avez-vous choisi, et pourquoi ? | `qwen2.5:1.5b` pour générer : c'est le modèle par défaut du dépôt d'origine, léger, et il a respecté le schéma en 48 s lors du test du 12/11. `nomic-embed-text` pour les embeddings. Les autres modèles (`gemma2:2b`…) se choisissent par requête ; ils n'ont pas encore été mesurés avec le schéma |
| Qu'est-ce que le modèle a « ingéré » ? | 6 fiches clients, découpées en 36 sections, vectorisées dans ChromaDB. Pas d'entraînement : c'est du RAG |
| Comment éviter que le modèle invente ? | Il ne reçoit que la fiche du client demandé (recherche filtrée), avec interdiction d'inventer, un schéma JSON imposé et un contrôle des questions |
| Et si le modèle se trompe ? | Exemple réel du 12/11 : 2 questions sur 3 utilisables, la 3e employait du vocabulaire interne. Depuis, ce cas est détecté et remplacé par une question préparée (`source: mixte`) |
| Comment mesurez-vous la qualité ? | 30 cas (`evaluer.py`) : 12 de recherche, 12 de reconnaissance du nom, 6 de génération. Résultat du 12/11 : **29/30**. Format respecté : 0/6 en V1, 5/6 en V2. Durée médiane : 34 s |
| Les questions de l'IA sont-elles bonnes ? | La forme oui (17 sur 18 retenues), le fond pas toujours : à la lecture, environ la moitié sont utilisables telles quelles, les autres sont génériques ou maladroites. C'est la limite d'un petit modèle local ; les questions préparées restent la référence |
| Quelles limites ? | Données fictives, petit modèle lent sur un PC sans carte graphique, questions non encore validées par un commercial senior |
| Comment passer aux vraies données ? | Section 8 du livrable : connecteurs en lecture seule vers le CRM et l'outil de projets, veille de marché, tout converti en « signaux » |

## 8. Problèmes rencontrés et solutions

| Problème | Cause | Solution |
|---|---|---|
| L'API répondait toujours `simule` | L'application Ollama n'était pas ouverte, puis le modèle `llama3.2:1b` n'était pas installé | Ouvrir Ollama ; `ollama pull` |
| Le modèle répondait dans une forme inutilisable | JSON libre | Schéma JSON imposé + lecture tolérante |
| `ngrok` refusait de démarrer | Version 3.3.1 trop ancienne | `ngrok update` |
| `ngrok` restait en `reconnecting` | Vérification de certificat bloquée par le réseau | `crl_noverify: true` dans la configuration |
| `curl` : « error parsing the body » | Accents mal envoyés par le terminal Windows | Passer le nom dans l'adresse (`/questions-client/PepsiCo`) |
| Fichier Python cassé | Copier-coller depuis une conversation | Récupérer les fichiers par Git, jamais par copier-coller |

## 9. Reste à faire

- [x] Push sur la branche `Amir`.
- [x] `python evaluer.py` : 29/30, chiffres reportés dans le livrable.
- [x] Pousser `docs/evaluation.md` et le livrable à jour.
- [x] Déposer `LIVRABLE_DATA_G03.md` dans le dépôt de l'équipe.
- [x] Envoyer le dépôt et le lien ngrok à Kevin.
- [ ] Vérifier la liste du document `2.livrables.pdf` (canal « ressources ») : elle n'a pas été relue ici.
- [ ] `benchmark_llm.pdf` à la racine du dépôt : absent pour l'instant.
- [ ] Faire relire les questions par un commercial senior.
