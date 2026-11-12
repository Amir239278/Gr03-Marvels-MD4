"""Évalue la route /questions-client sur 30 cas de référence et écrit docs/evaluation.md.

Les 30 cas :
  - 12 cas de RECHERCHE : pour chaque opportunité, la base vectorielle retrouve-t-elle la fiche du bon client ?
  - 12 cas de NOM : 6 noms approximatifs à reconnaître, 6 noms à refuser.
  -  6 cas de GÉNÉRATION : pour chaque client, le modèle rend-il 3 questions valides ?
     V2 = schéma JSON imposé + lecture tolérante (la route actuelle)
     V1 = même prompt, sans schéma imposé, lecture stricte (l'approche de départ)

Usage :
    python evaluer.py                      # modèle par défaut (config.LLM_MODEL)
    python evaluer.py --model gemma2:2b
    python evaluer.py --sans-v1            # plus rapide : pas de comparaison V1
Prérequis : Ollama lancé et `python ingest_clients.py` déjà exécuté.
"""

from __future__ import annotations

import argparse
import datetime
import json
import statistics
import time
from pathlib import Path

from fastapi import HTTPException

import clients
import config
import rag

NOMS_A_RECONNAITRE = [("pepsico", "4"), ("NESTLE", "6"), ("nordic food", "2"),
                      ("Maison Nova", "1"), ("  danone ", "5"), ("alimenta distribution", "3")]
NOMS_A_REFUSER = ["Coca-Cola", "Unilever", "xyz", "n", "", "Pepsi Danone"]
MOTS_GENERIQUES = {"client", "clients", "projet", "projets", "gamme", "produit", "produits", "nouvelle", "nouveau",
                   "existante", "existant", "opportunite", "opportunites", "confirmer", "qualifier", "verifier",
                   "hypothese", "faisabilite", "potentiel", "avant", "toute", "deux", "signal"}


def cas_recherche() -> list[dict]:
    col = rag.get_collection(name=config.CLIENTS_COLLECTION)
    resultats = []
    for fiche in clients.FICHES.values():
        for opp in fiche["opportunites"]:
            res = col.query(query_embeddings=[rag.embed_query(opp["title"])], n_results=3)
            trouves = [m["client_id"] for m in res["metadatas"][0]]
            attendu = fiche["identite"]["id"]
            resultats.append({"requete": opp["title"], "attendu": fiche["identite"]["name"],
                              "top1": trouves[0] == attendu, "top3": attendu in trouves})
    return resultats


def cas_noms() -> list[dict]:
    resultats = []
    for nom, attendu in NOMS_A_RECONNAITRE:
        try:
            ok = clients.trouver_client(nom)["identite"]["id"] == attendu
        except HTTPException:
            ok = False
        resultats.append({"nom": nom, "attendu": clients.FICHES[attendu]["identite"]["name"], "ok": ok})
    for nom in NOMS_A_REFUSER:
        try:
            clients.trouver_client(nom)
            ok = False
        except HTTPException:
            ok = True
        resultats.append({"nom": nom or "(vide)", "attendu": "refus", "ok": ok})
    return resultats


def mots_de_la_fiche(fiche: dict) -> set[str]:
    texte = " ".join([o["title"] for o in fiche["opportunites"]] + fiche["a_confirmer"] + [p["name"] for p in fiche["projets"]])
    return {m for m in clients.normaliser(texte).replace("«", " ").replace("»", " ").split()
            if len(m) >= 5 and m.strip(".,:;()") not in MOTS_GENERIQUES}


def cas_generation(modele: str, avec_v1: bool) -> list[dict]:
    resultats = []
    autres = {f["identite"]["id"]: clients.normaliser(f["identite"]["name"]) for f in clients.FICHES.values()}
    for fiche in clients.FICHES.values():
        nom, cid = fiche["identite"]["name"], fiche["identite"]["id"]
        print(f"  génération pour {nom}...", flush=True)
        r = clients.questions_client(clients.QuestionsClientDemande(client=nom, model=modele))
        textes = [clients.normaliser(q.question) for q in r.questions]
        mots = mots_de_la_fiche(fiche)
        ligne = {
            "client": nom,
            "v2_format": r.source == "modele",
            "source": r.source,
            "questions_du_modele": sum(q.origine == "modele" for q in r.questions),
            "v2_duree_s": r.duree_s,
            "categories_distinctes": len({q.information_recherchee for q in r.questions}),
            "sans_fuite": not any(n in t for i, n in autres.items() if i != cid for t in textes),
            "questions_ancrees": sum(any(m in t for m in mots) for t in textes),
            "questions": [q.model_dump() for q in r.questions if q.origine == "modele"],
        }
        ligne["reussi"] = ligne["v2_format"] and ligne["sans_fuite"] and ligne["questions_ancrees"] >= 1
        if avec_v1:
            debut = time.time()
            try:
                brut = rag.chat(clients.messages_pour(fiche, clients.retrouver(fiche, config.CLIENTS_TOP_K)), model=modele, format="json")
                qs = json.loads(brut).get("questions")
                ligne["v1_format"] = (isinstance(qs, list) and len(qs) == 3 and all(
                    isinstance(q, dict) and isinstance(q.get("question"), str) and isinstance(q.get("objectif"), str)
                    and q.get("information_recherchee") in clients.INFOS for q in qs))
            except Exception:
                ligne["v1_format"] = False
            ligne["v1_duree_s"] = round(time.time() - debut, 1)
        resultats.append(ligne)
    return resultats


def oui(b: bool) -> str:
    return "✅" if b else "❌"


def rapport(modele: str, rech: list[dict], noms: list[dict], gen: list[dict], avec_v1: bool) -> str:
    n1, n3 = sum(r["top1"] for r in rech), sum(r["top3"] for r in rech)
    nn, ng = sum(r["ok"] for r in noms), sum(g["reussi"] for g in gen)
    total = n1 + nn + ng
    durees = [g["v2_duree_s"] for g in gen]
    L = [
        "# Évaluation de la route `/questions-client` sur 30 cas de référence", "",
        f"Généré par `python evaluer.py` le {datetime.datetime.now():%d/%m/%Y à %H:%M}. "
        f"Modèle de génération : `{modele}`. Embeddings : `{config.EMBED_MODEL}`. Données fictives.", "",
        "## Résultat global", "",
        f"**{total}/30 cas réussis.**", "",
        "| Famille de cas | Nombre | Réussis | Critère de réussite |", "|---|---|---|---|",
        f"| Recherche (base vectorielle) | {len(rech)} | {n1} | La fiche du bon client arrive en 1re position (top 3 : {n3}/{len(rech)}) |",
        f"| Nom du client | {len(noms)} | {nn} | Nom approximatif reconnu, nom inconnu ou ambigu refusé |",
        f"| Génération V2 | {len(gen)} | {ng} | 3 questions du modèle valides (bon format, sans vocabulaire interne), sans nom d'un autre client, au moins 1 question ancrée dans la fiche |",
        "",
        f"Questions du modèle retenues : {sum(g['questions_du_modele'] for g in gen)}/{3 * len(gen)}. "
        "Les questions écartées (mal formées ou au vocabulaire interne) sont remplacées par des questions préparées.",
        "",
        f"Durée de génération V2 : médiane {statistics.median(durees):.0f} s, maximum {max(durees):.0f} s.", "",
    ]
    if avec_v1:
        v1, v2 = sum(g["v1_format"] for g in gen), sum(g["v2_format"] for g in gen)
        L += ["## Comparaison V1 / V2 (format respecté)", "",
              "| Version | Méthode | Format respecté | Durée médiane |", "|---|---|---|---|",
              f"| V1 | Prompt seul, JSON libre, lecture stricte | {v1}/{len(gen)} | {statistics.median(g['v1_duree_s'] for g in gen):.0f} s |",
              f"| V2 | Schéma JSON imposé à Ollama + lecture tolérante | {v2}/{len(gen)} | {statistics.median(durees):.0f} s |", ""]
    L += ["## Détail : génération", "",
          "| Client | Source | Questions du modèle | Catégories distinctes | Sans fuite | Questions ancrées | Durée | Réussi |", "|---|---|---|---|---|---|---|---|"]
    L += [f"| {g['client']} | {g['source']} | {g['questions_du_modele']}/3 | {g['categories_distinctes']}/3 | {oui(g['sans_fuite'])} | {g['questions_ancrees']}/3 | {g['v2_duree_s']:.0f} s | {oui(g['reussi'])} |" for g in gen]
    L += ["", "### Questions générées par le modèle (à relire par un humain)", ""]
    for g in gen:
        L.append(f"**{g['client']}**" + ("" if g["questions"] else " : aucune question du modèle retenue, plan B utilisé"))
        L += [f"- [{q['information_recherchee']}] {q['question']} *({q['objectif']})*" for q in g["questions"]] + [""]
    L += ["## Détail : recherche", "", "| Requête (intitulé de l'opportunité) | Client attendu | Top 1 | Top 3 |", "|---|---|---|---|"]
    L += [f"| {r['requete']} | {r['attendu']} | {oui(r['top1'])} | {oui(r['top3'])} |" for r in rech]
    L += ["", "## Détail : nom du client", "", "| Nom saisi | Résultat attendu | Réussi |", "|---|---|---|"]
    L += [f"| `{r['nom']}` | {r['attendu']} | {oui(r['ok'])} |" for r in noms]
    L += ["", "## Limites de cette évaluation", "",
          "- Les cas sont écrits par l'équipe Data, sur 6 clients fictifs : les résultats ne se généralisent pas.",
          "- « Ancrée » et « sans fuite » sont des contrôles automatiques par mots-clés. Ils ne jugent pas la pertinence.",
          "- La pertinence des questions doit être relue par un humain, idéalement un commercial senior.",
          "- Une seule exécution par cas : un petit modèle peut donner un résultat différent d'une fois à l'autre.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", default=config.LLM_MODEL)
    p.add_argument("--sans-v1", action="store_true")
    p.add_argument("--sortie", default=str(config.BASE_DIR / "docs"))
    a = p.parse_args(argv)

    print("1/3 Recherche (12 cas)...", flush=True)
    rech = cas_recherche()
    print("2/3 Noms (12 cas)...", flush=True)
    noms = cas_noms()
    print(f"3/3 Génération avec {a.model} (6 cas" + ("" if a.sans_v1 else ", V2 puis V1") + ")...", flush=True)
    gen = cas_generation(a.model, not a.sans_v1)

    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    texte = rapport(a.model, rech, noms, gen, not a.sans_v1)
    (sortie / "evaluation.md").write_text(texte, encoding="utf-8")
    (sortie / "evaluation.json").write_text(json.dumps({"modele": a.model, "recherche": rech, "noms": noms, "generation": gen},
                                                       ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + texte.split("## Détail : génération")[0])
    print(f"Rapport complet : {sortie / 'evaluation.md'}")


if __name__ == "__main__":
    main()
