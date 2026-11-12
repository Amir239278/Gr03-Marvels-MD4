"""Génère les fiches texte client_<id>.md (ingérées par le RAG) à partir de fiches_clients.json.
Les questions préparées ne sont PAS recopiées : c'est le modèle qui doit les rédiger.
Usage (depuis fiches_clients/) : python generer_fiches_md.py"""
import json
from pathlib import Path

ICI = Path(__file__).parent
F = json.loads((ICI / "fiches_clients.json").read_text(encoding="utf-8"))
ST = {"a_qualifier": "à qualifier", "detectee": "détectée", "confirmee": "confirmée"}
d = lambda s: f"{s[8:10]}/{s[5:7]}/{s[:4]}" if len(s) == 10 and s[4] == "-" else s

for f in F:
    i, s, n = f["identite"], f["synthese"], f["indicateurs"]
    L = [f"# Fiche client : {i['name']}", "", "## Identité",
         f"Client : {i['name']}. Secteur : {i['sector']}. Pays : {i['country']}. Responsable commercial : {i['account_manager']}. "
         f"Statut de la relation : {i['relationship_status']}. Mise à jour : {i['last_updated']}.",
         f"Projets actifs : {n['projets_actifs']}. Opportunités détectées : {n['opportunites_detectees']}. Opportunités à qualifier : {n['opportunites_a_qualifier']}.",
         "", "## Ce qu'il faut savoir", s["situation"],
         "Besoins exprimés : " + " ; ".join(s["expressed_needs"]) + ".",
         "Signaux récents : " + " ; ".join(s["recent_signals"]) + ".",
         "Points d'attention : " + " ; ".join(s["attention_points"]) + ".", "", "## Projets"]
    L += [f"- {p['name']} ({p['status']}, depuis le {d(p['start_date'])}) : {p['description']}" for p in f["projets"]]
    L += ["", "## Opportunités et signaux"]
    for o in f["opportunites"]:
        L.append(f"- {o['title']} : statut {ST.get(o['status'], o['status'])}, priorité {o['priority']}, potentiel "
                 f"{o.get('estimated_potential') or 'non renseigné'}, faisabilité {o['feasibility']}. Prochaine action : {o['next_action']}")
        for x in o["signaux"]:
            nature = "fait" if x["evidence_type"] == "fait" else "hypothèse"
            L.append(f"  - Signal ({nature}, {x['source_type']}, {d(x['source_date'])}, fiabilité {x['confidence']}) : {x['description']}")
    L += ["", "## Historique"] + [f"- {d(h['date'])} : {h['event']}" for h in f["historique"]]
    L += ["", "## À confirmer"] + [f"- {a}" for a in f["a_confirmer"]]
    (ICI / f"client_{i['id']}.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("écrit :", f"client_{i['id']}.md")
