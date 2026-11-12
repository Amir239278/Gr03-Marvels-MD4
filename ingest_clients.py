"""Charge les fiches clients (fiches_clients/client_*.md) dans la base vectorielle.

Chaque fiche est découpée par section (Identité, Ce qu'il faut savoir, Projets,
Opportunités et signaux, Historique, À confirmer). Chaque morceau garde le nom et
l'identifiant du client, pour que la recherche ne mélange jamais deux clients.

Les fiches ingérées ne contiennent PAS les questions préparées : c'est le modèle
qui doit les rédiger. Les questions préparées (fiches_clients.json) servent
seulement de plan B.

Usage :
    python ingest_clients.py
"""

import re

import config
import rag


def lire_fiche(texte: str) -> tuple[str, list[tuple[str, str]]]:
    """Retourne (nom du client, [(titre de section, contenu)])."""
    nom = re.search(r"^# Fiche client : (.+)$", texte, re.M).group(1).strip()
    sections = []
    for bloc in re.split(r"^## ", texte, flags=re.M)[1:]:
        titre, _, contenu = bloc.partition("\n")
        if contenu.strip():
            sections.append((titre.strip(), contenu.strip()))
    return nom, sections


def main() -> None:
    fichiers = sorted(config.CLIENTS_DIR.glob("client_*.md"))
    if not fichiers:
        raise SystemExit(f"Aucune fiche trouvée dans {config.CLIENTS_DIR}")

    ids, documents, metadatas = [], [], []
    for f in fichiers:
        client_id = f.stem.removeprefix("client_")
        nom, sections = lire_fiche(f.read_text(encoding="utf-8"))
        for i, (titre, contenu) in enumerate(sections):
            ids.append(f"client-{client_id}-{i:02d}")
            documents.append(contenu)
            metadatas.append({"client_id": client_id, "client_name": nom, "section": titre, "source": f.name})
        print(f"- {nom} : {len(sections)} sections")

    print(f"Calcul des embeddings de {len(documents)} morceaux avec '{config.EMBED_MODEL}'...")
    # Le nom du client et la section sont ajoutés au texte embarqué pour aider la recherche
    a_embarquer = [f"{m['client_name']} – {m['section']}\n{d}" for d, m in zip(documents, metadatas)]
    embeddings = rag.embed_documents(a_embarquer)

    collection = rag.get_collection(name=config.CLIENTS_COLLECTION)
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    print(f"OK : {collection.count()} morceaux dans la collection '{config.CLIENTS_COLLECTION}' ({config.CHROMA_DIR})")


if __name__ == "__main__":
    main()
