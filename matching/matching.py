from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def calculer_scores_matching(texte_cv, liste_entreprises):
    """
    texte_cv : le texte extrait du CV (string)
    liste_entreprises : liste de dicts avec au moins 'id' et 'texte_offre'
    Retourne un dict {id_entreprise: score_pourcentage}
    """
    if not texte_cv or not liste_entreprises:
        return {}

    # On construit la liste de tous les textes : CV en premier, puis chaque offre
    textes = [texte_cv] + [e['texte_offre'] for e in liste_entreprises]

    # TF-IDF transforme les textes en vecteurs numériques
    vectorizer = TfidfVectorizer(stop_words=None)
    matrice_tfidf = vectorizer.fit_transform(textes)

    # Le CV est la ligne 0, les entreprises sont les lignes 1, 2, 3...
    vecteur_cv = matrice_tfidf[0:1]
    vecteurs_entreprises = matrice_tfidf[1:]

    # Cosine similarity entre le CV et chaque entreprise
    similarites = cosine_similarity(vecteur_cv, vecteurs_entreprises)[0]

    scores = {}
    for i, entreprise in enumerate(liste_entreprises):
        scores[entreprise['id']] = round(similarites[i] * 100, 1)

    return scores