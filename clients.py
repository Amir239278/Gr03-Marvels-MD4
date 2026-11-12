"""Route « nom du client → 3 questions à poser avant le premier appel » (RAG + Ollama)."""

from __future__ import annotations

import json
import time
import unicodedata
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

import config
import rag

router = APIRouter(tags=["clients"])

INFOS = ["Objectifs du client", "Besoin réel", "Contraintes techniques",
         "Contraintes budgétaires", "Calendrier", "Critères de décision"]

SYSTEM_PROMPT = """Tu es l'assistant d'un commercial de Givaudan (arômes et parfums).
Tu prépares son PREMIER APPEL avec un client, à partir des extraits de la fiche client fournis.
Règles strictes :
- Utilise UNIQUEMENT les extraits fournis. N'invente aucun chiffre, aucun nom, aucun fait.
- Pose exactement 3 questions ouvertes, en français, une seule idée par question.
- Chaque question vise une information qui MANQUE dans la fiche (voir « À confirmer ») ;
  ne redemande jamais ce que la fiche dit déjà.
- Priorité aux opportunités « à qualifier » et de priorité haute, puis aux hypothèses à vérifier.
- Varie les informations recherchées.
- Les questions sont posées AU CLIENT : elles portent sur ses projets, ses objectifs, ses contraintes, son calendrier.
  N'emploie jamais le vocabulaire interne de la fiche (opportunité, signal, fiche, statut, priorité, « à qualifier »).
- Un signal « hypothèse » n'est jamais présenté comme un fait.
- Réponds UNIQUEMENT avec le JSON demandé."""

SCHEMA = {
    "type": "object",
    "properties": {"questions": {"type": "array", "minItems": 3, "maxItems": 3, "items": {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "objectif": {"type": "string"},
            "information_recherchee": {"type": "string", "enum": INFOS},
        },
        "required": ["question", "objectif", "information_recherchee"],
    }}},
    "required": ["questions"],
}


def normaliser(texte: str) -> str:
    sans_accent = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return " ".join(sans_accent.lower().replace("-", " ").split())


def charger_fiches() -> dict[str, dict]:
    """Fiches complètes (avec les questions préparées, utilisées seulement en plan B)."""
    chemin = config.CLIENTS_DIR / "fiches_clients.json"
    return {f["identite"]["id"]: f for f in json.loads(chemin.read_text(encoding="utf-8"))}


FICHES = charger_fiches()


def trouver_client(nom: str) -> dict:
    cible = normaliser(nom)
    exacts = [f for f in FICHES.values() if normaliser(f["identite"]["name"]) == cible]
    # Nom partiel accepté à partir de 3 lettres (« nordic food » → Nordic Food Industries)
    proches = [f for f in FICHES.values() if len(cible) >= 3 and cible in normaliser(f["identite"]["name"])]
    trouves = exacts or proches
    if len(trouves) != 1:
        noms = [f["identite"]["name"] for f in FICHES.values()]
        detail = "plusieurs clients correspondent" if len(trouves) > 1 else "client inconnu"
        raise HTTPException(404, f"{detail} : « {nom} ». Clients disponibles : {', '.join(noms)}")
    return trouves[0]


class Extrait(BaseModel):
    section: str
    texte: str
    score: float = Field(description="Similarité cosinus (1 = identique)")


class Question(BaseModel):
    question: str
    objectif: str
    information_recherchee: str
    origine: Literal["modele", "prepare"] = Field("modele", description="modele = rédigée par le LLM ; prepare = préparée par l'équipe Data")


class QuestionsClientDemande(BaseModel):
    client: str = Field(..., min_length=1, examples=["PepsiCo"], description="Nom du client (majuscules et accents ignorés)")
    model: str | None = Field(None, description=f"Modèle Ollama. Par défaut : {config.LLM_MODEL}")
    top_k: int = Field(config.CLIENTS_TOP_K, ge=1, le=10, description="Nombre de sections de la fiche à retrouver")


class QuestionsClientReponse(BaseModel):
    client_id: str
    client: str
    questions: list[Question]
    source: Literal["modele", "mixte", "simule"] = Field(
        description="modele = 3 questions du LLM ; mixte = questions du LLM complétées par des questions préparées ; "
                    "simule = 3 questions préparées (plan B)")
    model: str | None
    duree_s: float
    extraits: list[Extrait] = Field(description="Sections de la fiche retrouvées et données au modèle")


def retrouver(client: dict, top_k: int) -> list[Extrait]:
    collection = rag.get_collection(name=config.CLIENTS_COLLECTION)
    if collection.count() == 0:
        raise HTTPException(503, "La base des clients est vide : lance d'abord `python ingest_clients.py`.")
    requete = f"Préparer le premier appel avec {client['identite']['name']} : opportunités à qualifier, informations à confirmer"
    res = collection.query(
        query_embeddings=[rag.embed_query(requete)],
        n_results=top_k,
        where={"client_id": client["identite"]["id"]},  # jamais de mélange entre clients
    )
    return [Extrait(section=m["section"], texte=d, score=round(1 - dist, 4))
            for d, m, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])]


def messages_pour(client: dict, extraits: list[Extrait]) -> list[dict]:
    contexte = "\n\n---\n\n".join(f"[{e.section}]\n{e.texte}" for e in extraits)
    consigne = (
        f"Extraits de la fiche de {client['identite']['name']} :\n\n{contexte}\n\n"
        "Rédige les 3 questions du premier appel, au format JSON demandé. Rappels : "
        "chaque question porte sur un point de la section « À confirmer » ou sur une information absente de la fiche ; "
        "« objectif » explique en une phrase pourquoi la question est utile ; "
        f"« information_recherchee » vaut exactement une de ces valeurs : {', '.join(INFOS)}."
    )
    return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": consigne}]


# Vocabulaire interne : une question qui l'emploie ne peut pas être posée telle quelle à un client
JARGON = ("opportunite", "signal", "fiche", "qualifier", "statut", "priorite", "mise a jour")


def extraire(brut: str) -> list[Question]:
    """Lit la réponse du modèle avec tolérance (petits modèles), normalise la catégorie
    et écarte les questions qui emploient le vocabulaire interne."""
    try:
        data = json.loads(brut)
    except (json.JSONDecodeError, TypeError):
        return []
    trouvees: list[dict] = []

    def parcourir(x):
        if isinstance(x, dict):
            if isinstance(x.get("question"), str):
                trouvees.append(x)
            for v in x.values():
                parcourir(v)
        elif isinstance(x, list):
            for v in x:
                parcourir(v)

    parcourir(data)
    propres: list[Question] = []
    for q in trouvees:
        texte = " ".join(q["question"].split())
        objectif = " ".join(str(q.get("objectif", "")).split())
        info = next((i for i in INFOS if normaliser(i) in normaliser(str(q.get("information_recherchee", "")))), None)
        interne = any(mot in normaliser(texte) for mot in JARGON)
        if texte.endswith("?") and objectif and info and not interne and texte not in [p.question for p in propres]:
            propres.append(Question(question=texte, objectif=objectif[0].upper() + objectif[1:], information_recherchee=info))
    return propres[:3]


def plan_b(client: dict) -> list[Question]:
    return [Question(question=q["question"], objectif=q["pourquoi"], information_recherchee=q["information_recherchee"], origine="prepare")
            for q in client["questions_preparatoires"][:3]]


def completer(du_modele: list[Question], client: dict) -> list[Question]:
    """Complète jusqu'à 3 questions avec les questions préparées, en privilégiant les catégories absentes."""
    prises = {q.information_recherchee for q in du_modele}
    reserve = sorted(plan_b(client), key=lambda q: q.information_recherchee in prises)
    return (du_modele + reserve)[:3]


@router.get("/clients")
def lister_clients() -> list[dict]:
    """Clients disponibles (noms à utiliser dans /questions-client)."""
    return [{"id": f["identite"]["id"], "name": f["identite"]["name"], "sector": f["identite"]["sector"]} for f in FICHES.values()]


@router.post("/questions-client", response_model=QuestionsClientReponse)
def questions_client(req: QuestionsClientDemande):
    """Prend le nom d'un client et retourne 3 questions à poser avant le premier appel.

    1. Retrouve les sections de SA fiche dans la base vectorielle (RAG).
    2. Le LLM rédige 3 questions sur les informations manquantes, au format imposé.
    3. Les questions mal formées ou qui emploient le vocabulaire interne sont écartées.
    4. S'il manque des questions, elles sont complétées par les questions préparées (source = mixte).
       Si le modèle échoue ou est trop lent : 3 questions préparées (source = simule).
    """
    client = trouver_client(req.client)
    extraits = retrouver(client, req.top_k)
    modele = req.model or config.LLM_MODEL
    debut = time.time()
    try:
        questions = extraire(rag.chat(messages_pour(client, extraits), model=modele, format=SCHEMA))
    except Exception:  # Ollama absent, modèle manquant, délai dépassé...
        questions = []
    duree = round(time.time() - debut, 1)
    source = "modele" if len(questions) == 3 else "mixte" if questions else "simule"
    return QuestionsClientReponse(client_id=client["identite"]["id"], client=client["identite"]["name"],
                                  questions=completer(questions, client), source=source,
                                  model=modele if questions else None, duree_s=duree, extraits=extraits)


@router.get("/questions-client/{client}", response_model=QuestionsClientReponse)
def questions_client_get(client: str, model: str | None = None):
    """Même résultat que POST /questions-client, avec le nom du client dans l'adresse (pratique dans un navigateur)."""
    return questions_client(QuestionsClientDemande(client=client, model=model))
