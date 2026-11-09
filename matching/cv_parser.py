"""
Lecture et analyse de CV (PDF / DOCX).

`analyser_cv(chemin)` renvoie un dict compatible avec l'ancien code
(clés 'texte', 'email', 'telephone') enrichi d'une clé 'analyse' :

    nom, email, telephone, localisation,
    formation[], experiences[], projets[], competences_techniques[],
    competences_personnelles[], langues[{langue, niveau}], certifications[],
    sections_detectees[], recommandations[]

Aucune donnée n'est inventée : un champ non trouvé reste vide (None ou liste vide).
"""
import os
import re
import unicodedata

import pdfplumber
from docx import Document
from docx.oxml.ns import qn

from competences import extraire_competences, normaliser


# ---------------------------------------------------------------------------
# Lecture des fichiers
# ---------------------------------------------------------------------------
def extraire_texte_pdf(chemin_fichier):
    morceaux = []
    with pdfplumber.open(chemin_fichier) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                morceaux.append(t)
    return "\n".join(morceaux) + ("\n" if morceaux else "")


def _texte_paragraphe(p):
    morceaux = []
    for noeud in p.iter():
        if noeud.tag == qn("w:t") and noeud.text:
            morceaux.append(noeud.text)
        elif noeud.tag == qn("w:tab"):
            morceaux.append("\t")
        elif noeud.tag == qn("w:br"):
            morceaux.append("\n")
    return "".join(morceaux)


def _dans_fallback(element):
    parent = element.getparent()
    while parent is not None:
        if parent.tag.endswith("}Fallback"):
            return True
        parent = parent.getparent()
    return False


def extraire_texte_docx(chemin_fichier):
    """Paragraphes + tableaux + zones de texte, dans l'ordre du document (sans doublons)."""
    doc = Document(chemin_fichier)
    lignes = []
    for p in doc.element.body.iter(qn("w:p")):
        if _dans_fallback(p):
            continue
        t = _texte_paragraphe(p).strip()
        if t:
            lignes.append(t)
    # en-têtes (souvent le nom ou les coordonnées)
    entetes = []
    for section in doc.sections:
        for p in section.header.paragraphs:
            if p.text.strip():
                entetes.append(p.text.strip())
    return "\n".join(entetes + lignes)


def extraire_texte(chemin_fichier):
    extension = os.path.splitext(chemin_fichier)[1].lower()
    if extension == ".pdf":
        return extraire_texte_pdf(chemin_fichier)
    if extension == ".docx":
        return extraire_texte_docx(chemin_fichier)
    raise ValueError("Format de fichier non supporté (PDF ou DOCX uniquement)")


# ---------------------------------------------------------------------------
# Coordonnées
# ---------------------------------------------------------------------------
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# +212 6 79 99 04 35 | 0679990435 | 06 79 99 04 35 | +33 6 12 34 56 78 ...
_RE_TEL = re.compile(r"(?<![\d/])(\+?\d[\d\s.\-()]{7,19}\d)(?![\d/])")


def extraire_email(texte):
    m = _RE_EMAIL.search(texte or "")
    return m.group(0) if m else None


def extraire_telephone(texte):
    """Premier numéro plausible (9 à 15 chiffres). Ignore les plages d'années (2018 - 2020)."""
    for m in _RE_TEL.finditer(texte or ""):
        brut = m.group(1).strip()
        chiffres = re.sub(r"\D", "", brut)
        if not 9 <= len(chiffres) <= 15:
            continue
        if re.fullmatch(r"(?:19|20)\d{2}\s*[-–.]\s*(?:19|20)\d{2}", brut):
            continue
        if not (brut.startswith("+") or chiffres.startswith("0") or chiffres.startswith("212")):
            continue
        return re.sub(r"\s+", " ", brut)
    return None


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------
TITRES_SECTIONS = {
    "profil": ["profil", "profil professionnel", "resume", "resume professionnel", "professional summary",
               "summary", "about me", "a propos", "objectif", "objectif professionnel", "career objective"],
    "formation": ["formation", "formations", "education", "etudes", "parcours academique",
                  "parcours scolaire", "diplomes", "academic background"],
    "experience": ["experience", "experiences", "experience professionnelle", "experiences professionnelles",
                   "professional experience", "work experience", "parcours professionnel", "stages",
                   "stages et experiences", "employment history"],
    "projets": ["projets", "projet", "projets personnels", "projets academiques", "projects", "personal projects"],
    "competences": ["competences", "competences techniques", "competences cles", "skills", "technical skills",
                    "hard skills", "soft skills", "competences personnelles", "outils", "technologies"],
    "langues": ["langues", "langue", "languages", "language skills"],
    "certifications": ["certifications", "certification", "certificats", "certifications formations en ligne",
                       "certifications et formations", "certifications formations en ligne",
                       "formations en ligne", "courses", "licenses", "certifications and courses"],
    "engagement": ["engagement associatif", "vie associative", "benevolat", "activites extra-scolaires",
                   "activites extrascolaires", "volunteering", "extracurricular activities"],
    "interets": ["centres d'interet", "centres d interet", "loisirs", "interets", "hobbies", "interests"],
}


def _cle_titre(ligne):
    n = normaliser(ligne).strip(" :-–—•\t")
    n = re.sub(r"[&/,+]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    if not n or len(n) > 60:
        return None
    for cle, titres in TITRES_SECTIONS.items():
        for t in titres:
            if n == re.sub(r"\s+", " ", re.sub(r"[&/,+]", " ", t)):
                return cle
    return None


def decouper_sections(texte):
    """{section: [lignes]} ; la clé 'entete' regroupe ce qui précède la première section."""
    sections = {"entete": []}
    courante = "entete"
    for brute in (texte or "").splitlines():
        ligne = brute.strip()
        if not ligne:
            continue
        cle = _cle_titre(ligne)
        if cle:
            courante = cle
            sections.setdefault(cle, [])
            continue
        sections.setdefault(courante, []).append(ligne)
    return sections


_PUCE = re.compile(r"^\s*[•\-–—·▪●*◦]\s*")


def _est_puce(ligne):
    return bool(_PUCE.match(ligne))


def _nettoyer(ligne):
    return re.sub(r"\s+", " ", _PUCE.sub("", ligne)).strip()


_RE_PERIODE = re.compile(
    r"((?:(?:jan|feb|fev|mar|apr|avr|may|mai|juin|june|juil|jul|aug|aout|sep|oct|nov|dec)[a-z.]*\.?\s+)?(?:19|20)\d{2}"
    r"(?:\s*[-–—]\s*(?:(?:(?:jan|feb|fev|mar|apr|avr|may|mai|juin|june|juil|jul|aug|aout|sep|oct|nov|dec)[a-z.]*\.?\s+)?(?:19|20)\d{2}"
    r"|present|aujourd'hui|en cours|actuel|now))?"
    r"|\d+\s*(?:mois|ans?|semaines?|months?|years?))",
    re.IGNORECASE,
)


def _a_periode(ligne):
    return bool(_RE_PERIODE.search(normaliser(ligne)))


def _entrees(lignes, une_par_ligne=False):
    """
    Regroupe les lignes en entrées.
    - une_par_ligne=True (formation) : chaque ligne non-puce est une entrée.
    - sinon : une entrée commence sur une ligne non-puce qui suit le début ou une puce, ou
      dont la ligne suivante contient une période (ex. « Restaurant X | Janvier 2025 – Juin 2025 »).
      Limite connue : sans puces ni dates, deux entrées consécutives restent regroupées.
    """
    entrees, courante, derniere_puce = [], None, True
    for i, l in enumerate(lignes):
        if _est_puce(l):
            if courante is None:
                courante = {"intitule": "", "details": []}
                entrees.append(courante)
            courante["details"].append(_nettoyer(l))
            derniere_puce = True
            continue
        suivante = lignes[i + 1] if i + 1 < len(lignes) else ""
        nouvelle = (
            une_par_ligne
            or courante is None
            or derniere_puce
            or (_a_periode(suivante) and not _a_periode(l) and not _est_puce(suivante))
        )
        if nouvelle:
            courante = {"intitule": _nettoyer(l), "details": []}
            entrees.append(courante)
        else:
            courante["details"].append(_nettoyer(l))
        derniere_puce = False
    for e in entrees:
        m = _RE_PERIODE.search(normaliser(" ".join([e["intitule"]] + e["details"])))
        e["periode"] = m.group(1).strip() if m else None
    return entrees


# ---------------------------------------------------------------------------
# Langues, compétences personnelles, nom
# ---------------------------------------------------------------------------
LANGUES_CONNUES = {
    "arabe": "Arabe", "arabic": "Arabe", "francais": "Français", "french": "Français",
    "anglais": "Anglais", "english": "Anglais", "espagnol": "Espagnol", "spanish": "Espagnol",
    "allemand": "Allemand", "german": "Allemand", "italien": "Italien", "italian": "Italien",
    "amazigh": "Amazigh", "berbere": "Amazigh", "tamazight": "Amazigh", "portugais": "Portugais",
    "chinois": "Chinois", "turc": "Turc", "russe": "Russe", "darija": "Darija",
}

SOFT_SKILLS = {
    "travail d'équipe": ["travail d'equipe", "esprit d'equipe", "teamwork", "team work", "collaboration"],
    "communication": ["communication", "aisance relationnelle", "relationnel"],
    "rigueur": ["rigueur", "rigoureux", "rigoureuse", "organisation", "organise", "organisee", "organized"],
    "autonomie": ["autonomie", "autonome", "self-motivated", "independent"],
    "adaptabilité": ["adaptabilite", "adaptable", "flexibilite", "flexible"],
    "esprit d'analyse": ["esprit d'analyse", "esprit analytique", "analytique", "sens de l'analyse", "analytical"],
    "résolution de problèmes": ["resolution de problemes", "problem solving", "problem-solving"],
    "gestion du temps": ["gestion du temps", "time management", "gestion des priorites"],
    "leadership": ["leadership", "encadrement", "supervise", "supervision"],
    "créativité": ["creativite", "creatif", "creative"],
    "curiosité": ["curiosite", "curieux", "curieuse", "curious"],
    "sens des responsabilités": ["responsabilite", "responsable", "fiable", "reliable"],
    "gestion de projets": ["gestion de projets", "gestion de projet", "project management"],
    "esprit critique": ["esprit critique", "critical thinking"],
}


def extraire_langues(sections, texte):
    source = " • ".join(sections.get("langues", [])) or ""
    trouvees, vues = [], set()
    morceaux = re.split(r"[•|;,\n·/]|\s{3,}", source) if source else []
    for m in morceaux:
        n = normaliser(m)
        for cle, nom in LANGUES_CONNUES.items():
            if re.search(r"(?<![a-z])" + cle + r"(?![a-z])", n) and nom not in vues:
                niveau = None
                parens = re.search(r"\(([^)]+)\)", m)
                if parens:
                    niveau = parens.group(1).strip()
                else:
                    reste = re.sub(r"(?i)" + re.escape(cle), "", unicodedata.normalize("NFKD", m))
                    reste = "".join(c for c in reste if not unicodedata.combining(c))
                    reste = reste.strip(" -–—:()")
                    niveau = reste or None
                trouvees.append({"langue": nom, "niveau": niveau})
                vues.add(nom)
    return trouvees


def extraire_competences_personnelles(texte):
    t = normaliser(texte)
    trouvees = []
    for nom, aliases in SOFT_SKILLS.items():
        if any(re.search(r"(?<![a-z])" + re.escape(a) + r"(?![a-z])", t) for a in aliases):
            trouvees.append(nom)
    return trouvees


def extraire_nom(sections, texte):
    """Nom = première ligne de l'en-tête qui ressemble à un nom (2 à 4 mots alphabétiques)."""
    candidats = (sections.get("entete") or [])[:6]
    for l in candidats:
        if "@" in l or re.search(r"\d", l):
            continue
        mots = l.replace("’", "'").split()
        if 2 <= len(mots) <= 4 and all(re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿ'\-]+", m) for m in mots):
            if not any(normaliser(m) in {"etudiant", "etudiante", "stagiaire", "developpeur", "ingenieur",
                                         "professional", "cook", "chef", "cv", "curriculum", "vitae"}
                       for m in mots):
                if l.isupper() or all(m[0].isupper() for m in mots):
                    return " ".join(w.capitalize() if l.isupper() else w for w in mots)
    return None


def extraire_localisation(texte):
    n = (texte or "")[:600]
    m = re.search(r"\b(Marrakech|Casablanca|Rabat|Tanger|Tangier|Agadir|Fès|Fes|Meknès|Oujda|Kénitra|Tétouan|Essaouira)\b[^\n|•]*", n)
    return m.group(0).strip(" ,-|•") if m else None


# ---------------------------------------------------------------------------
# Recommandations (règles déterministes, expliquées)
# ---------------------------------------------------------------------------
def recommandations_cv(a, texte):
    reco = []
    sd = set(a["sections_detectees"])
    if not a["email"]:
        reco.append("Ajoute une adresse email professionnelle bien visible en haut du CV.")
    if not a["telephone"]:
        reco.append("Ajoute un numéro de téléphone (format +212 6 XX XX XX XX).")
    for cle, msg in (("profil", "Ajoute un court profil (3-4 lignes) qui résume ton objectif et ta spécialité."),
                     ("formation", "Ajoute une section « Formation » avec tes diplômes et leurs années."),
                     ("competences", "Ajoute une section « Compétences » listant clairement tes outils et technologies."),
                     ("langues", "Ajoute une section « Langues » avec ton niveau pour chacune.")):
        if cle not in sd:
            reco.append(msg)
    if not a["experiences"] and not a["projets"]:
        reco.append("Ajoute au moins un stage ou un projet concret pour montrer ce que tu sais faire.")
    if len(a["competences_techniques"]) < 5:
        reco.append("Peu de compétences techniques détectées : cite explicitement tes outils "
                    "(ex. Python, SQL, Excel, Power BI, Git) pour être repéré(e) par les recruteurs.")
    if a["projets"] and not any(re.search(r"\d", " ".join(p["details"])) for p in a["projets"]):
        reco.append("Chiffre tes projets (taille des données, précision obtenue, durée) : "
                    "les résultats mesurables sont plus convaincants.")
    if "github" not in normaliser(texte) and "linkedin" not in normaliser(texte):
        reco.append("Ajoute un lien LinkedIn et/ou GitHub pour que les recruteurs voient tes réalisations.")
    nb_mots = len(texte.split())
    if nb_mots < 150:
        reco.append("Le CV est très court : développe tes expériences et projets.")
    elif nb_mots > 900:
        reco.append("Le CV est long : vise une page (deux au maximum) en gardant l'essentiel.")
    if not a["certifications"]:
        reco.append("Mentionne tes certifications et formations en ligne si tu en as.")
    return reco


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def analyser_texte_cv(texte):
    sections = decouper_sections(texte)
    sections_detectees = [k for k in sections if k != "entete" and sections[k]]
    cert = [_nettoyer(l) for l in sections.get("certifications", [])]
    analyse = {
        "nom": extraire_nom(sections, texte),
        "email": extraire_email(texte),
        "telephone": extraire_telephone(texte),
        "localisation": extraire_localisation(texte),
        "profil": " ".join(sections.get("profil", [])) or None,
        "formation": _entrees(sections.get("formation", []), une_par_ligne=True),
        "experiences": _entrees(sections.get("experience", [])),
        "projets": _entrees(sections.get("projets", [])),
        "competences_techniques": extraire_competences(texte),
        "competences_personnelles": extraire_competences_personnelles(texte),
        "langues": extraire_langues(sections, texte),
        "certifications": cert,
        "sections_detectees": sections_detectees,
    }
    analyse["recommandations"] = recommandations_cv(analyse, texte)
    return analyse


def analyser_cv(chemin_fichier):
    texte = extraire_texte(chemin_fichier)
    analyse = analyser_texte_cv(texte)
    return {
        "texte": texte,
        "email": analyse["email"],
        "telephone": analyse["telephone"],
        "analyse": analyse,
    }
