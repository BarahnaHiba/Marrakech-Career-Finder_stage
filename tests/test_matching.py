import matching
from competences import competences_typiques, extraire_competences

CV_DATA = """
Étudiante en Intelligence Artificielle et Data Analyst.
Compétences : Python, pandas, SQL, Excel, Power BI, Machine Learning, scikit-learn, Git.
Projets : prédiction de prix avec scikit-learn, tableau de bord Power BI.
"""
CV_CUISINIER = "Chef de partie. Cuisine poisson et viande, normes HACCP, gestion d'équipe, service en restaurant."

OFFRES = [
    {"id": 1, "texte_offre": "Data Analyst SQL Excel Power BI"},
    {"id": 2, "texte_offre": "Développement Web PHP Laravel React"},
    {"id": 3, "texte_offre": "Marketing Digital, Community Management"},
    {"id": 4, "texte_offre": "Support IT"},
    {"id": 5, "texte_offre": ""},
]


def test_extraction_competences_mots_entiers():
    c = extraire_competences("Python, SQL et C++ ; je vis à Marrakech ; Node.js ; Power BI")
    assert {"python", "sql", "c++", "node.js", "power bi"} <= set(c)
    assert "r" not in c          # « r » ne doit pas matcher « marrakech »
    assert "java" not in extraire_competences("javascript seulement")


def test_scores_entre_0_et_100():
    res = matching.analyser_matching(CV_DATA, OFFRES)
    assert set(res) == {1, 2, 3, 4, 5}
    assert all(0 <= d["score"] <= 100 for d in res.values())


def test_offre_pertinente_mieux_classee():
    res = matching.analyser_matching(CV_DATA, OFFRES)
    assert res[1]["score"] > res[2]["score"]
    assert res[1]["score"] > res[3]["score"]
    assert res[1]["niveau"] == "Forte"


def test_competences_communes_et_manquantes_exactes():
    d = matching.analyser_matching(CV_DATA, OFFRES)[1]
    assert set(d["competences_communes"]) == {"sql", "excel", "power bi", "data analysis"}
    assert d["competences_manquantes"] == []
    d2 = matching.analyser_matching(CV_DATA, OFFRES)[2]
    assert d2["competences_communes"] == []
    assert set(d2["competences_manquantes"]) == {"php", "laravel", "react"}
    assert d2["a_apprendre"] == d2["competences_manquantes"][:5]


def test_explication_presente_et_coherente():
    d = matching.analyser_matching(CV_DATA, OFFRES)[1]
    assert "sql" in d["explication"] and "En commun" not in d["explication"] or "commun" in d["explication"]
    d2 = matching.analyser_matching(CV_DATA, OFFRES)[2]
    assert "php" in d2["explication"]


def test_source_des_competences_attendues_declaree():
    res = matching.analyser_matching(CV_DATA, OFFRES)
    assert res[1]["source_attendues"] == "offre"       # compétences citées dans l'offre
    assert res[4]["source_attendues"] == "typiques"    # « Support IT » -> compétences typiques du poste
    assert res[5]["source_attendues"] == "aucune"      # offre vide : rien n'est inventé
    assert res[5]["competences_manquantes"] == []


def test_cv_hors_sujet_score_bas_partout():
    res = matching.analyser_matching(CV_CUISINIER, OFFRES)
    assert max(d["score"] for d in res.values()) < 15


def test_poids_documentes_et_somme_a_100():
    assert abs(matching.POIDS_COUVERTURE + matching.POIDS_TFIDF + matching.POIDS_TITRE - 1.0) < 1e-9


def test_score_reproductible_et_decomposition():
    a = matching.analyser_matching(CV_DATA, OFFRES)
    b = matching.analyser_matching(CV_DATA, OFFRES)
    assert a == b
    d = a[1]
    ds = d["details_score"]
    attendu = (0.5 * ds["couverture_competences"] + 0.35 * ds["similarite_tfidf"]
               + 0.15 * ds["correspondance_titre"]) 
    assert abs(d["score"] - attendu) < 0.6   # arrondis des composantes


def test_entrees_vides():
    assert matching.analyser_matching("", OFFRES) == {}
    assert matching.analyser_matching("   ", OFFRES) == {}
    assert matching.analyser_matching(CV_DATA, []) == {}


def test_ancienne_api_compatible():
    scores = matching.calculer_scores_matching(CV_DATA, OFFRES)
    assert set(scores) == {1, 2, 3, 4, 5} and all(isinstance(v, float) for v in scores.values())
    assert matching.calculer_scores_matching(None, OFFRES) == {}


def test_offre_sans_cle_texte_offre_ne_plante_pas():
    res = matching.analyser_matching(CV_DATA, [{"id": 9}])
    assert res[9]["source_attendues"] == "aucune"


def test_competences_typiques_vide_si_inconnu():
    assert competences_typiques("zzz qqq") == []
    assert "sql" in competences_typiques("Data Analyst")
