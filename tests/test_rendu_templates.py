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

RACINE = Path(__file__).resolve().parent.parent
TEMPLATES = RACINE / "backend" / "templates"

PARAMS = {"postuler": "<path:nom_entreprise>", "changer_statut": "<int:application_id>",
          "changer_notes": "<int:application_id>", "candidature": None, "reinitialiser_mot_de_passe": "<jeton>"}

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
