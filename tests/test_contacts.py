import importlib
import sys
from pathlib import Path

import pytest


BACKEND = Path(__file__).resolve().parent.parent / "backend"


class FauxConnexion:
    def __init__(self, entreprises):
        self.entreprises = entreprises
        self.requete = ""
        self.fermee = False

    def execute(self, requete, params=()):
        self.requete = requete
        return self

    def fetchall(self):
        return self.entreprises

    def close(self):
        self.fermee = True


@pytest.fixture
def application(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "cle-de-test-suffisamment-longue")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.syspath_prepend(str(BACKEND))
    return importlib.import_module("app")


def test_contacts_affiche_les_emails_valides_et_filtres(application, monkeypatch):
    connexion = FauxConnexion([
        {
            "id": 1,
            "nom_entreprise": "Data Marrakech",
            "domaine": "IA / Data",
            "secteur": "Informatique",
            "email": "recrutement@datamarrakech.ma",
            "telephone": "+212 600 000 000",
            "adresse": "Marrakech",
            "ville": "Marrakech",
            "site_web": "https://datamarrakech.ma",
        },
        {
            "id": 2,
            "nom_entreprise": "Entreprise Exemple",
            "domaine": "Web",
            "secteur": "Informatique",
            "email": "email@address.com",
            "telephone": None,
            "adresse": None,
            "ville": None,
            "site_web": "javascript:alert(1)",
        },
    ])
    monkeypatch.setattr(application, "get_db_connection", lambda: connexion)

    reponse = application.app.test_client().get("/contacts")

    assert reponse.status_code == 200
    contenu = reponse.get_data(as_text=True)
    assert "Data Marrakech" in contenu
    assert "recrutement@datamarrakech.ma" in contenu
    assert "Entreprise Exemple" not in contenu
    assert "filtre-domaine" in contenu
    assert "Voir la carte" not in contenu
    assert "Préparer avec Gmail" in contenu
    assert "javascript:alert" not in contenu
    assert "LIMIT 400" in connexion.requete
    assert connexion.fermee
