"""
Rendu réel des pages modifiées avec de vraies données (analyse de CV + matching).
L'application complète (Flask-Login, PostgreSQL) n'est pas importée : on monte une mini-appli Flask
qui enregistre des routes factices portant les mêmes noms que celles de app.py.
"""
import re
from pathlib import Path

from flask import Flask, render_template

import cv_parser
import matching
import security
from admin_access import email_est_administrateur

RACINE = Path(__file__).resolve().parent.parent
TEMPLATES = RACINE / "backend" / "templates"

PARAMS = {"postuler": "<path:nom_entreprise>", "changer_statut": "<int:application_id>",
          "changer_notes": "<int:application_id>", "candidature": None, "reinitialiser_mot_de_passe": "<jeton>",
          "carte_entreprise": "<int:company_id>", "admin_changer_statut": "<int:application_id>"}

CV = """AMINA LAHLOU
Étudiante Data Analyst
Marrakech, Maroc
+212 6 11 22 33 44
amina@example.com
COMPÉTENCES
Python, SQL, Excel, Power BI, Git
LANGUES
Français (courant) • Anglais (B2)
"""
OFFRES = [
    {"id": 1, "nom_entreprise": "Alpha Data", "titre_poste": "Data Analyst SQL", "domaine": "Data", "secteur": "IT",
     "texte_offre": "Data Analyst SQL Power BI"},
    {"id": 2, "nom_entreprise": "Beta Web", "titre_poste": "Développement Web PHP", "domaine": "Web", "secteur": "IT",
     "texte_offre": "Développement Web PHP Laravel"},
]


def app_test():
    app = Flask(__name__, template_folder=str(TEMPLATES), static_folder=str(RACINE / "backend" / "static"))
    app.secret_key = "x" * 40
    app.jinja_env.globals["csrf_token"] = security.generer_jeton_csrf
    app.jinja_env.globals["email_est_administrateur"] = email_est_administrateur

    class Anonyme:
        is_authenticated = False
        id = None

    app.context_processor(lambda: {"current_user": Anonyme()})
    noms = set()
    for f in TEMPLATES.glob("*.html"):
        if "ancien" not in f.name:
            noms |= set(re.findall(r"url_for\('([a-z_]+)'", f.read_text(encoding="utf-8")))
    noms.discard("static")
    for nom in noms:
        suffixe = PARAMS.get(nom)
        regle = f"/{nom}" + (f"/{suffixe}" if suffixe else "")
        app.add_url_rule(regle, nom, lambda **k: "", methods=["GET", "POST"])
    return app


def rendre(nom, **ctx):
    app = app_test()
    with app.test_request_context("/"):
        return render_template(nom, **ctx)


def test_page_analyse_cv():
    a = cv_parser.analyser_texte_cv(CV)
    html = rendre("analyse_cv.html", cv={"nom_fichier": "cv.pdf"}, a=a)
    assert "Amina Lahlou" in html and "amina@example.com" in html
    assert "power bi" in html and "Recommandations" in html


def test_page_recommandations_avec_vrai_matching():
    res = matching.analyser_matching(CV, OFFRES)
    offres = []
    for o in OFFRES:
        d = dict(o); d["matching"] = res[o["id"]]; d["score_matching"] = res[o["id"]]["score"]; offres.append(d)
    offres.sort(key=lambda e: -e["score_matching"])
    html = rendre("recommandations.html", offres=offres, a_apprendre=[("php", 1), ("laravel", 1)])
    assert html.index("Alpha Data") < html.index("Beta Web")
    assert "php (1)" in html and "csrf_token" in html


def test_page_mes_candidatures_statuts_et_remarques():
    statuts = ["À postuler", "Candidature envoyée", "Relance", "Entretien", "Refusé", "Accepté", "Abandonné"]
    c = [{"id": 5, "nom_entreprise": "Alpha", "secteur": "IT", "ville": "Marrakech", "statut": "Relance",
          "date_candidature": "09/11/2026", "notes": "Rappeler lundi"}]
    html = rendre("mes_candidatures.html", candidatures=c, statuts=statuts)
    for s in statuts:
        assert f'value="{s}"' in html
    assert "Rappeler lundi" in html and 'name="notes"' in html
    assert html.count('name="csrf_token"') == 2   # formulaire statut + formulaire remarque


def test_dashboard_nouvelles_statistiques():
    html = rendre("dashboard.html", total_candidatures=3, total_entretiens=1, total_entreprises=217,
                  total_favoris=4, offres_compatibles=12,
                  activites=[{"entreprise": "Alpha", "statut": "Entretien", "date": "09/11/2026"}],
                  statuts_labels=["Entretien"], statuts_valeurs=[1], secteurs_labels=["IT"], secteurs_valeurs=[1])
    assert "217" in html and "Favoris" in html and "Activité récente" in html and "12" in html
    html2 = rendre("dashboard.html", total_candidatures=0, total_entretiens=0, total_entreprises=1, total_favoris=0,
                   offres_compatibles=None, activites=[], statuts_labels=[], statuts_valeurs=[],
                   secteurs_labels=[], secteurs_valeurs=[])
    assert "Importe ton CV" in html2 and "Aucune candidature" in html2


def test_carte_entreprise_affiche_le_marqueur_openstreetmap():
    html = rendre(
        "carte_entreprise.html",
        entreprise={"nom_entreprise": "Entreprise Exemple", "adresse": "Guéliz", "ville": "Marrakech"},
        coordonnees={"latitude": 31.6295, "longitude": -7.9811, "libelle": "Marrakech, Maroc"},
        erreur_carte=None,
    )
    assert "Entreprise Exemple" in html
    assert "tile.openstreetmap.org" in html
    assert "[31.6295, 31.6295]" not in html
    assert "[31.6295, -7.9811]" in html
    assert "OpenStreetMap" in html


def test_tableau_admin_affiche_stats_et_formulaire_csrf():
    html = rendre(
        "admin.html",
        totaux={"utilisateurs": 12, "emails_verifies": 9, "entreprises": 217, "candidatures": 5},
        utilisateurs=[{"nom": "Amina Exemple", "email": "amina@example.com",
                       "date_creation": "2026-11-09", "email_verifie": True}],
        candidatures=[{"id": 3, "nom_utilisateur": "Amina Exemple", "email": "amina@example.com",
                       "nom_entreprise": "Entreprise Exemple", "statut": "Relance",
                       "date_candidature": "2026-11-09"}],
        statuts_labels=["Relance"], statuts_valeurs=[1],
        secteurs_labels=["Informatique"], secteurs_valeurs=[1],
        statuts=["À postuler", "Relance"],
        formater_date=lambda valeur: valeur,
        normaliser_statut=lambda valeur: valeur,
    )
    assert "Utilisateurs récents" in html
    assert "Entreprise Exemple" in html and "amina@example.com" in html
    assert 'name="csrf_token"' in html
