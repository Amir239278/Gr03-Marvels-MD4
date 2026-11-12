"""Tests de la route /questions-client. Lancer : python -m pytest -q (Ollama non nécessaire)."""

import hashlib
import json
import os
import tempfile

os.environ["CHROMA_DIR"] = tempfile.mkdtemp()

import pytest
from fastapi.testclient import TestClient

import api
import clients
import ingest_clients
import rag


def faux_embedding(textes, prefix=""):
    return [[b / 255 for b in hashlib.sha256((prefix + t).encode()).digest()] for t in textes]


@pytest.fixture(autouse=True)
def base(monkeypatch):
    monkeypatch.setattr(rag, "embed", faux_embedding)
    ingest_clients.main()


c = TestClient(api.app)
Q = lambda i, info: {"question": f"Question {i} ?", "objectif": "objectif", "information_recherchee": info}


def test_six_clients_ingeres_sans_questions_preparatoires():
    col = rag.get_collection(name="clients")
    docs = col.get()["documents"]
    assert len({m["client_id"] for m in col.get()["metadatas"]}) == 6
    for f in clients.FICHES.values():  # le modèle ne doit pas recopier les questions préparées
        for q in f["questions_preparatoires"]:
            assert not any(q["question"] in d for d in docs)


def test_liste_des_clients():
    assert len(c.get("/clients").json()) == 6


def test_nom_insensible_aux_accents_et_majuscules(monkeypatch):
    monkeypatch.setattr(rag, "chat", lambda *a, **k: json.dumps({"questions": [Q(1, "Calendrier"), Q(2, "Besoin réel"), Q(3, "Critères de décision")]}))
    r = c.post("/questions-client", json={"client": "nestle"}).json()
    assert r["client"] == "Nestlé" and r["source"] == "modele" and len(r["questions"]) == 3


def test_extraits_uniquement_du_bon_client(monkeypatch):
    monkeypatch.setattr(rag, "chat", lambda *a, **k: "{}")
    r = c.post("/questions-client", json={"client": "PepsiCo"}).json()
    assert r["extraits"] and all("Nestlé" not in e["texte"] for e in r["extraits"])


def test_client_inconnu():
    r = c.post("/questions-client", json={"client": "Coca"})
    assert r.status_code == 404 and "Clients disponibles" in r.json()["detail"]


def test_plan_b_si_ollama_absent(monkeypatch):
    def panne(*a, **k):
        raise ConnectionError("Ollama absent")
    monkeypatch.setattr(rag, "chat", panne)
    r = c.post("/questions-client", json={"client": "Danone"}).json()
    assert r["source"] == "simule" and len(r["questions"]) == 3


def test_plan_b_si_reponse_invalide(monkeypatch):
    monkeypatch.setattr(rag, "chat", lambda *a, **k: json.dumps({"questions": [Q(1, "Météo")]}))
    assert c.post("/questions-client", json={"client": "PepsiCo"}).json()["source"] == "simule"


def test_reponse_mal_rangee_recuperee(monkeypatch):
    brut = {"questions": [Q(1, "['Calendrier', 'Lancement']")], "autre": Q(2, "Besoin réel"), "question": "Question 3 ?",
            "objectif": "budget", "information_recherchee": "Contraintes budgétaires"}
    monkeypatch.setattr(rag, "chat", lambda *a, **k: json.dumps(brut))
    r = c.post("/questions-client", json={"client": "PepsiCo"}).json()
    assert r["source"] == "modele"
    assert {q["information_recherchee"] for q in r["questions"]} == {"Calendrier", "Besoin réel", "Contraintes budgétaires"}


def test_schema_impose_au_modele(monkeypatch):
    vu = {}
    monkeypatch.setattr(rag, "chat", lambda m, model=None, format=None: vu.update(f=format, m=model, msg=m) or "{}")
    c.post("/questions-client", json={"client": "PepsiCo", "model": "gemma2:2b"})
    assert vu["f"]["properties"]["questions"]["minItems"] == 3 and vu["m"] == "gemma2:2b"
    assert "À confirmer" in vu["msg"][1]["content"] and "PepsiCo" in vu["msg"][1]["content"]


def test_route_get(monkeypatch):
    monkeypatch.setattr(rag, "chat", lambda *a, **k: "{}")
    r = c.get("/questions-client/nordic food")
    assert r.status_code == 200 and r.json()["client"] == "Nordic Food Industries" and len(r.json()["questions"]) == 3


@pytest.mark.parametrize("nom", ["Pepsi Danone", "n", "xy", "Unilever"])
def test_noms_refuses(nom):
    assert c.post("/questions-client", json={"client": nom}).status_code == 404


def test_evaluation_30_cas(monkeypatch, tmp_path):
    import evaluer
    bon = json.dumps({"questions": [{"question": "Quel taux de réduction du sucre visez-vous ?", "objectif": "o", "information_recherchee": "Calendrier"},
                                    Q(2, "Besoin réel"), Q(3, "Critères de décision")]})
    monkeypatch.setattr(rag, "chat", lambda m, model=None, format=None: bon)
    evaluer.main(["--sortie", str(tmp_path)])
    d = json.loads((tmp_path / "evaluation.json").read_text(encoding="utf-8"))
    assert len(d["recherche"]) + len(d["noms"]) + len(d["generation"]) == 30
    assert all(n["ok"] for n in d["noms"])
    assert "/30 cas réussis" in (tmp_path / "evaluation.md").read_text(encoding="utf-8")


def test_question_au_vocabulaire_interne_ecartee_et_completee(monkeypatch):
    # Réponse réelle de qwen2.5:1.5b le 12/11 : la 3e question ne peut pas être posée à un client
    brut = {"questions": [
        {"question": "Quel est le niveau de réduction attendu pour les snacks à teneur réduite en sel ?", "objectif": "o", "information_recherchee": "Contraintes techniques"},
        {"question": "Quels sont les objectifs de réduction de sucre que vous visez ?", "objectif": "o", "information_recherchee": "Objectifs du client"},
        {"question": "Quelles sont les deux opportunités à qualifier qui ont été détectées lors de la dernière mise à jour ?", "objectif": "o", "information_recherchee": "Objectifs du client"}]}
    monkeypatch.setattr(rag, "chat", lambda *a, **k: json.dumps(brut))
    r = c.post("/questions-client", json={"client": "PepsiCo"}).json()
    assert r["source"] == "mixte" and len(r["questions"]) == 3
    assert [q["origine"] for q in r["questions"]] == ["modele", "modele", "prepare"]
    assert not any("opportunit" in q["question"] for q in r["questions"])
    assert r["questions"][2]["information_recherchee"] not in {"Contraintes techniques", "Objectifs du client"}
