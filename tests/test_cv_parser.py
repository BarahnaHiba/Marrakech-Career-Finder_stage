import io

import cv_parser
from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

TEXTE = """SARA ALAOUI
Étudiante en Data Science
Marrakech, Maroc
+212 6 12 34 56 78
sara.alaoui@example.com
PROFIL
Étudiante motivée, rigoureuse, avec un esprit d'analyse.
FORMATION
Licence en Informatique — Université Cadi Ayyad 2022 – 2025
Baccalauréat Scientifique 2022
EXPÉRIENCE PROFESSIONNELLE
Stagiaire Data Analyst
Société X | Marrakech | Juillet 2025 – Août 2025
• Analyse de 12 000 lignes avec Python, pandas et SQL
• Tableau de bord Power BI
PROJETS
Prédiction de prix (Machine Learning)
• Modèle scikit-learn, précision 87 %
COMPÉTENCES
Python, SQL, Excel, Git, travail d'équipe
LANGUES
Arabe (langue maternelle) • Français (courant) • Anglais (B2)
CERTIFICATIONS
• Google Data Analytics — Coursera
• Python pour la data science — Udemy
"""


def test_coordonnees():
    a = cv_parser.analyser_texte_cv(TEXTE)
    assert a["nom"] == "Sara Alaoui"
    assert a["email"] == "sara.alaoui@example.com"
    assert a["telephone"] == "+212 6 12 34 56 78"
    assert a["localisation"].startswith("Marrakech")


def test_telephone_ignore_les_annees_et_formats_marocains():
    assert cv_parser.extraire_telephone("2018 - 2020 Licence") is None
    assert cv_parser.extraire_telephone("Tel : 06 79 99 04 35") == "06 79 99 04 35"
    assert cv_parser.extraire_telephone("0625625104 | Marrakech") == "0625625104"
    assert cv_parser.extraire_telephone("Note 12 / 20") is None
    assert cv_parser.extraire_telephone("") is None and cv_parser.extraire_telephone(None) is None


def test_sections_detectees():
    a = cv_parser.analyser_texte_cv(TEXTE)
    assert set(a["sections_detectees"]) == {"profil", "formation", "experience", "projets",
                                            "competences", "langues", "certifications"}


def test_formation_une_entree_par_ligne():
    a = cv_parser.analyser_texte_cv(TEXTE)
    assert len(a["formation"]) == 2
    assert a["formation"][0]["periode"] == "2022 – 2025"


def test_experiences_avec_periode_et_details():
    e = cv_parser.analyser_texte_cv(TEXTE)["experiences"]
    assert len(e) == 1 and e[0]["intitule"] == "Stagiaire Data Analyst"
    assert e[0]["periode"].lower().startswith("juillet 2025")
    assert any("pandas" in d for d in e[0]["details"])


def test_competences_techniques_et_personnelles():
    a = cv_parser.analyser_texte_cv(TEXTE)
    assert {"python", "sql", "excel", "git", "power bi", "pandas", "scikit-learn", "machine learning"} <= set(a["competences_techniques"])
    assert "travail d'équipe" in a["competences_personnelles"]
    assert "rigueur" in a["competences_personnelles"]
    assert "esprit d'analyse" in a["competences_personnelles"]


def test_langues_avec_niveau():
    langues = {l["langue"]: l["niveau"] for l in cv_parser.analyser_texte_cv(TEXTE)["langues"]}
    assert langues == {"Arabe": "langue maternelle", "Français": "courant", "Anglais": "B2"}


def test_certifications():
    c = cv_parser.analyser_texte_cv(TEXTE)["certifications"]
    assert len(c) == 2 and c[0].startswith("Google Data Analytics")


def test_recommandations_cv_complet_peu_de_conseils():
    reco = cv_parser.analyser_texte_cv(TEXTE)["recommandations"]
    assert not any("email" in r.lower() for r in reco)
    assert any("LinkedIn" in r for r in reco)            # aucun lien dans ce CV


def test_recommandations_cv_pauvre():
    a = cv_parser.analyser_texte_cv("Jean\nJe cherche du travail.")
    r = " ".join(a["recommandations"]).lower()
    assert "email" in r and "téléphone" in r and "formation" in r and "compétences" in r
    assert a["email"] is None and a["telephone"] is None and a["nom"] is None


def test_texte_vide_ne_plante_pas():
    a = cv_parser.analyser_texte_cv("")
    assert a["competences_techniques"] == [] and a["formation"] == [] and a["langues"] == []


def test_extraction_docx_paragraphes_tableaux_entetes(tmp_path):
    doc = Document()
    doc.sections[0].header.paragraphs[0].text = "NADIA BENANI"
    doc.add_paragraph("COMPÉTENCES")
    t = doc.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text = "Python"
    t.rows[0].cells[1].text = "SQL"
    doc.add_paragraph("LANGUES")
    doc.add_paragraph("Français (courant) • Anglais (B1)")
    chemin = tmp_path / "cv.docx"
    doc.save(chemin)
    r = cv_parser.analyser_cv(str(chemin))
    assert r["analyse"]["nom"] == "Nadia Benani"
    assert {"python", "sql"} <= set(r["analyse"]["competences_techniques"])
    assert [l["langue"] for l in r["analyse"]["langues"]] == ["Français", "Anglais"]


def test_extraction_pdf_aller_retour(tmp_path):
    chemin = tmp_path / "cv.pdf"
    c = canvas.Canvas(str(chemin), pagesize=A4)
    y = 800
    for ligne in ["YASSINE TAZI", "yassine@example.com", "COMPETENCES", "Python SQL Docker", "LANGUES", "Arabe (natif) - Anglais (B2)"]:
        c.drawString(60, y, ligne); y -= 20
    c.save()
    r = cv_parser.analyser_cv(str(chemin))
    assert r["email"] == "yassine@example.com"
    assert {"python", "sql", "docker"} <= set(r["analyse"]["competences_techniques"])
    assert r["analyse"]["nom"] == "Yassine Tazi"


def test_format_non_supporte(tmp_path):
    f = tmp_path / "cv.txt"; f.write_text("x")
    try:
        cv_parser.extraire_texte(str(f))
    except ValueError:
        return
    raise AssertionError("ValueError attendue")


def test_compat_ancienne_api(tmp_path):
    chemin = tmp_path / "c.pdf"
    c = canvas.Canvas(str(chemin)); c.drawString(50, 800, "a@b.ma Python"); c.save()
    r = cv_parser.analyser_cv(str(chemin))
    assert {"texte", "email", "telephone", "analyse"} <= set(r)
