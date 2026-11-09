"""
Référentiel de compétences et outils de normalisation de texte (partagés par le matching
et l'analyse de CV). Tout est en français/anglais, orienté IT / data / digital.

Extension : pour ajouter une compétence, ajoute une entrée dans COMPETENCES
(nom canonique -> liste d'alias). Les alias sont comparés sans accents ni majuscules,
en mots entiers (ex. « r » ne matche pas « marrakech »).
"""
import re
import unicodedata

# nom canonique -> alias (déjà en minuscules, sans accents)
COMPETENCES = {
    # Langages
    "python": ["python"],
    "java": ["java", "java ee", "j2ee"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript"],
    "php": ["php"],
    "c": ["langage c"],
    "c++": ["c++", "cpp"],
    "c#": ["c#", "csharp"],
    "r": ["langage r", "rstudio"],
    "sql": ["sql", "t-sql", "pl/sql", "plsql"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "kotlin": ["kotlin"],
    "dart": ["dart"],
    # Web / frameworks
    "flask": ["flask"],
    "django": ["django"],
    "fastapi": ["fastapi"],
    "react": ["react", "reactjs", "react.js"],
    "angular": ["angular", "angularjs"],
    "vue.js": ["vue", "vuejs", "vue.js"],
    "node.js": ["node", "nodejs", "node.js", "express.js", "expressjs"],
    "laravel": ["laravel"],
    "symfony": ["symfony"],
    "spring": ["spring", "spring boot", "springboot"],
    "bootstrap": ["bootstrap"],
    "tailwind": ["tailwind", "tailwindcss"],
    "wordpress": ["wordpress"],
    "api rest": ["api rest", "rest api", "restful", "api"],
    "jinja2": ["jinja", "jinja2"],
    # Mobile
    "flutter": ["flutter"],
    "android": ["android", "android studio"],
    "react native": ["react native"],
    "ios": ["ios", "swift"],
    # Bases de données
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql", "mariadb"],
    "mongodb": ["mongodb", "mongo"],
    "sqlite": ["sqlite"],
    "oracle": ["oracle"],
    "sql server": ["sql server", "mssql"],
    "firebase": ["firebase"],
    # Data / IA
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "matplotlib": ["matplotlib", "seaborn"],
    "scikit-learn": ["scikit-learn", "scikit learn", "sklearn"],
    "tensorflow": ["tensorflow", "keras"],
    "pytorch": ["pytorch", "torch"],
    "machine learning": ["machine learning", "apprentissage automatique", "ml"],
    "deep learning": ["deep learning", "apprentissage profond", "reseaux de neurones"],
    "nlp": ["nlp", "traitement du langage"],
    "intelligence artificielle": ["intelligence artificielle", "ia", "ai"],
    "data analysis": ["data analysis", "analyse de donnees", "data analyst", "analyse des donnees"],
    "data science": ["data science", "science des donnees", "data scientist"],
    "data visualization": ["data visualization", "data visualisation", "visualisation de donnees", "dataviz"],
    "statistiques": ["statistiques", "statistique", "statistics"],
    "etl": ["etl", "talend", "airflow"],
    "big data": ["big data", "hadoop", "spark", "pyspark"],
    "power bi": ["power bi", "powerbi", "dax", "power query"],
    "tableau": ["tableau", "tableau software"],
    "excel": ["excel", "tableaux croises dynamiques", "vba"],
    "google analytics": ["google analytics", "ga4"],
    "jupyter": ["jupyter", "colab", "google colab"],
    "llm": ["llm", "gemini", "openai", "chatgpt", "prompt engineering"],
    # DevOps / systèmes / réseaux
    "git": ["git", "github", "gitlab"],
    "docker": ["docker", "conteneurs"],
    "kubernetes": ["kubernetes", "k8s"],
    "ci/cd": ["ci/cd", "cicd", "jenkins", "github actions"],
    "linux": ["linux", "ubuntu", "debian", "bash", "shell"],
    "windows server": ["windows server", "active directory"],
    "reseaux": ["reseaux", "reseau", "tcp/ip", "cisco", "routage", "vlan", "networking"],
    "cloud": ["cloud", "aws", "azure", "gcp", "google cloud", "render", "heroku", "netlify"],
    "virtualisation": ["virtualisation", "vmware", "virtualbox", "proxmox"],
    "support technique": ["support technique", "support informatique", "helpdesk", "help desk", "maintenance informatique", "assistance informatique"],
    # Sécurité
    "cybersecurite": ["cybersecurite", "securite informatique", "cyber securite", "cybersecurity", "securite des systemes"],
    "pentest": ["pentest", "test d'intrusion", "penetration testing", "kali linux", "owasp"],
    # Gestion / méthodes
    "uml": ["uml", "merise", "modelisation"],
    "agile": ["agile", "scrum", "kanban"],
    "gestion de projet": ["gestion de projet", "project management"],
    "algorithmique": ["algorithmique", "structures de donnees", "algorithmes"],
    "poo": ["poo", "programmation orientee objet", "oop"],
    "tests logiciels": ["tests unitaires", "pytest", "junit", "selenium", "tests logiciels"],
    "erp": ["erp", "odoo", "sage", "sap"],
    # Digital / marketing / design
    "seo": ["seo", "referencement", "referencement naturel"],
    "marketing digital": ["marketing digital", "digital marketing", "webmarketing"],
    "community management": ["community management", "community manager", "reseaux sociaux"],
    "communication": ["communication digitale", "communication visuelle"],
    "photoshop": ["photoshop"],
    "illustrator": ["illustrator"],
    "figma": ["figma", "adobe xd", "maquettage"],
    "ui/ux": ["ui/ux", "ux", "ui design", "ux design", "web design"],
    "canva": ["canva"],
    "montage video": ["montage video", "premiere pro", "after effects", "capcut"],
    "wix": ["wix", "shopify", "prestashop", "woocommerce"],
}

# Compétences attendues « typiques » selon des mots présents dans le titre du poste / domaine.
# (mot-clé normalisé -> compétences). Sert uniquement quand l'offre ne cite aucune compétence.
PROFILS_METIER = {
    "data analyst": ["sql", "excel", "power bi", "python", "pandas", "data visualization", "statistiques"],
    "analyste": ["sql", "excel", "power bi", "python", "data visualization"],
    "business intelligence": ["sql", "power bi", "excel", "etl", "data visualization"],
    "data scientist": ["python", "machine learning", "pandas", "scikit-learn", "sql", "statistiques"],
    "data science": ["python", "machine learning", "pandas", "scikit-learn", "sql", "statistiques"],
    "intelligence artificielle": ["python", "machine learning", "deep learning", "pandas", "scikit-learn"],
    "machine learning": ["python", "machine learning", "pandas", "scikit-learn", "statistiques"],
    "ia": ["python", "machine learning", "intelligence artificielle"],
    "big data": ["python", "sql", "big data", "etl"],
    "developpement web": ["html", "css", "javascript", "git", "sql"],
    "web development": ["html", "css", "javascript", "git", "sql"],
    "developpeur web": ["html", "css", "javascript", "git", "sql"],
    "full stack": ["html", "css", "javascript", "sql", "git", "api rest"],
    "front end": ["html", "css", "javascript", "react", "git"],
    "frontend": ["html", "css", "javascript", "react", "git"],
    "back end": ["sql", "api rest", "git", "python", "php"],
    "backend": ["sql", "api rest", "git", "python", "php"],
    "web": ["html", "css", "javascript", "git"],
    "mobile": ["flutter", "android", "git", "api rest"],
    "android": ["android", "kotlin", "java", "git"],
    "python": ["python", "git", "sql", "flask", "api rest"],
    "java": ["java", "spring", "sql", "git"],
    "php": ["php", "mysql", "laravel", "git"],
    "logiciel": ["git", "sql", "algorithmique", "poo", "uml"],
    "genie logiciel": ["git", "sql", "uml", "poo", "tests logiciels", "agile"],
    "developpement": ["git", "sql", "algorithmique", "poo"],
    "informatique": ["git", "sql", "algorithmique", "reseaux"],
    "support it": ["support technique", "windows server", "reseaux", "linux"],
    "support": ["support technique", "reseaux", "windows server"],
    "reseau": ["reseaux", "linux", "windows server", "cybersecurite"],
    "systeme": ["linux", "windows server", "reseaux", "virtualisation"],
    "devops": ["docker", "ci/cd", "linux", "git", "cloud"],
    "cloud": ["cloud", "docker", "linux", "git"],
    "cybersecurite": ["cybersecurite", "reseaux", "linux", "pentest"],
    "securite": ["cybersecurite", "reseaux", "linux"],
    "erp": ["erp", "sql", "gestion de projet"],
    "seo": ["seo", "google analytics", "marketing digital", "wordpress"],
    "marketing digital": ["marketing digital", "seo", "community management", "google analytics", "canva"],
    "community management": ["community management", "canva", "marketing digital", "communication"],
    "communication": ["communication", "community management", "canva", "marketing digital"],
    "design": ["figma", "photoshop", "illustrator", "ui/ux", "canva"],
    "web design": ["figma", "ui/ux", "html", "css", "photoshop"],
    "graphisme": ["photoshop", "illustrator", "canva"],
    "digital": ["marketing digital", "seo", "community management", "wordpress"],
}

MOTS_VIDES = {
    "de", "du", "des", "la", "le", "les", "un", "une", "et", "en", "au", "aux", "ou", "pour", "par",
    "sur", "dans", "avec", "sans", "a", "d", "l", "the", "and", "of", "for", "to", "in", "stage",
    "stagiaire", "poste", "pfe", "emploi", "offre", "type", "projet", "entreprise", "marrakech",
    "maroc", "none", "nan", "autre", "autres", "divers", "it",
}


def normaliser(texte):
    """minuscules, sans accents, ponctuation légère conservée pour c++ / c# / ci/cd / .net."""
    if not texte:
        return ""
    t = unicodedata.normalize("NFKD", str(texte))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = t.replace("’", "'")
    return re.sub(r"[ \t\r\f\v]+", " ", t)


def _motif_alias(alias):
    """Mot entier, en tolérant les alias à symboles (c++, c#, ci/cd, node.js)."""
    return re.compile(r"(?<![a-z0-9+#])" + re.escape(alias) + r"(?![a-z0-9+#])")


_MOTIFS = {nom: [_motif_alias(a) for a in aliases] for nom, aliases in COMPETENCES.items()}


def extraire_competences(texte):
    """Liste ordonnée (stable) des compétences canoniques trouvées dans `texte`."""
    t = normaliser(texte)
    if not t.strip():
        return []
    trouvees = []
    for nom, motifs in _MOTIFS.items():
        if any(m.search(t) for m in motifs):
            trouvees.append(nom)
    return trouvees


def competences_typiques(texte_offre):
    """Compétences typiques d'après les mots/expressions du poste. Vide si rien de reconnu."""
    t = normaliser(texte_offre)
    resultat = []
    for cle, comps in PROFILS_METIER.items():
        if _motif_alias(cle).search(t):
            for c in comps:
                if c not in resultat:
                    resultat.append(c)
    return resultat


def mots_cles(texte):
    """Mots significatifs (≥3 lettres, hors mots vides) d'un texte normalisé."""
    t = normaliser(texte)
    return [m for m in re.findall(r"[a-z0-9+#.]{3,}", t) if m not in MOTS_VIDES and not m.isdigit()]
