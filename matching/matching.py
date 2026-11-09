"""
Matching CV <-> offres, explicable.

Principe (aucun score « artificiel » : chaque point s'explique) :

  1. On extrait du CV et de chaque offre les compétences reconnues dans un référentiel
     (voir `competences.py`).
  2. Pour une offre, les compétences « attendues » viennent (a) des compétences citées
     textuellement dans l'offre, et (b) à défaut, des compétences typiques du type de poste
     (ex. « Data Analyst » -> SQL, Excel, Power BI...). Le résultat indique laquelle des deux
     sources a été utilisée (`source_attendues`).
  3. Score de compatibilité 0-100 =
        50 % couverture des compétences attendues par le CV
      + 35 % similarité cosinus TF-IDF entre le CV et l'offre (pondération des compétences rares)
      + 15 % correspondance de l'intitulé du poste avec le texte du CV
     Si aucune compétence attendue n'est connue, la part « couverture » est redistribuée
     sur les deux autres critères.
  4. On renvoie compétences communes, manquantes, compétences à apprendre et une explication.

API :
  - analyser_matching(texte_cv, offres)        -> {id: détail complet}
  - calculer_scores_matching(texte_cv, offres) -> {id: score}  (compatible avec l'ancien code)
Chaque offre est un dict avec au moins 'id' et 'texte_offre' (poste + secteur + domaine).
"""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from competences import (
    MOTS_VIDES,
    competences_typiques,
    extraire_competences,
    mots_cles,
)

POIDS_COUVERTURE = 0.50
POIDS_TFIDF = 0.35
POIDS_TITRE = 0.15


def _jeton_competence(nom):
    return "skill_" + re.sub(r"\W+", "_", nom)


def _jetons_document(competences):
    """Représentation TF-IDF d'un document : uniquement ses compétences reconnues.
    (Les mots génériques comme « management » gonflaient artificiellement la similarité.)"""
    return [_jeton_competence(c) for c in competences]


def niveau_compatibilite(score):
    if score >= 65:
        return "Forte"
    if score >= 40:
        return "Moyenne"
    return "Faible"


def _explication(communes, manquantes, source, titre_pct):
    morceaux = []
    if communes:
        morceaux.append("Compétences en commun : " + ", ".join(communes[:6]) + ".")
    else:
        morceaux.append("Aucune compétence du référentiel n'apparaît à la fois dans ton CV et pour ce poste.")
    if manquantes:
        morceaux.append("À renforcer : " + ", ".join(manquantes[:5]) + ".")
    if source == "typiques":
        morceaux.append("(Compétences attendues estimées d'après le type de poste : l'offre n'en détaille pas.)")
    elif source == "aucune":
        morceaux.append("(Offre trop peu détaillée pour estimer les compétences attendues : score basé sur le vocabulaire.)")
    if titre_pct >= 0.5:
        morceaux.append("L'intitulé du poste correspond bien aux termes de ton CV.")
    return " ".join(morceaux)


def analyser_matching(texte_cv, offres):
    """Retourne {id_offre: détail}. Dict vide si le CV ou la liste d'offres est vide."""
    if not texte_cv or not texte_cv.strip() or not offres:
        return {}

    competences_cv = extraire_competences(texte_cv)
    mots_du_cv = set(mots_cles(texte_cv))

    # 1. compétences attendues par offre
    infos = []
    for o in offres:
        texte_offre = o.get("texte_offre") or ""
        citees = extraire_competences(texte_offre)
        if citees:
            attendues, source = citees, "offre"
        else:
            typiques = competences_typiques(texte_offre)
            attendues, source = (typiques, "typiques") if typiques else ([], "aucune")
        infos.append((o, texte_offre, attendues, source))

    # 2. TF-IDF sur les compétences : vocabulaire et IDF issus des OFFRES (une compétence rare compte plus) ;
    #    le CV est projeté sur ce vocabulaire (les mots du CV absents des offres sont ignorés,
    #    ce qui évite qu'un CV long dilue la similarité).
    docs_offres = [_jetons_document(attendues) for _, texte_offre, attendues, _ in infos]
    doc_cv = _jetons_document(competences_cv)
    try:
        vectoriseur = TfidfVectorizer(analyzer=lambda doc: doc, sublinear_tf=True)
        matrice_offres = vectoriseur.fit_transform(docs_offres)
        vecteur_cv = vectoriseur.transform([doc_cv])
        similarites = cosine_similarity(vecteur_cv, matrice_offres)[0]
    except ValueError:  # vocabulaire vide
        similarites = [0.0] * len(infos)

    # 3. assemblage
    resultats = {}
    for (offre, texte_offre, attendues, source), cos in zip(infos, similarites):
        communes = [c for c in attendues if c in competences_cv]
        manquantes = [c for c in attendues if c not in competences_cv]

        mots_titre = [m for m in mots_cles(texte_offre) if m not in MOTS_VIDES]
        titre_pct = (sum(1 for m in mots_titre if m in mots_du_cv) / len(mots_titre)) if mots_titre else 0.0

        cos = float(cos)
        if attendues:
            couverture = len(communes) / len(attendues)
            brut = POIDS_COUVERTURE * couverture + POIDS_TFIDF * cos + POIDS_TITRE * titre_pct
        else:
            couverture = None
            brut = (POIDS_TFIDF + POIDS_COUVERTURE * 0.6) * cos + (POIDS_TITRE + POIDS_COUVERTURE * 0.4) * titre_pct

        score = round(max(0.0, min(1.0, brut)) * 100, 1)
        resultats[offre["id"]] = {
            "score": score,
            "niveau": niveau_compatibilite(score),
            "competences_communes": communes,
            "competences_manquantes": manquantes,
            "a_apprendre": manquantes[:5],
            "source_attendues": source,
            "details_score": {
                "couverture_competences": None if couverture is None else round(couverture * 100, 1),
                "similarite_tfidf": round(cos * 100, 1),
                "correspondance_titre": round(titre_pct * 100, 1),
            },
            "explication": _explication(communes, manquantes, source, titre_pct),
        }
    return resultats


def calculer_scores_matching(texte_cv, liste_entreprises):
    """Compatibilité avec l'ancienne API : {id: score}."""
    return {i: d["score"] for i, d in analyser_matching(texte_cv, liste_entreprises).items()}
