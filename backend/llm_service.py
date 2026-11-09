import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


# Charger le fichier .env depuis la racine du projet
RACINE = Path(__file__).resolve().parent.parent
load_dotenv(RACINE / ".env")


SYSTEM_PROMPT = """
Tu es un assistant IA polyvalent, chaleureux et naturel, intégré à
l'application Marrakech Career Finder (recherche de stages et d'emplois à Marrakech).

Tu peux discuter de tout, comme un assistant conversationnel généraliste :
répondre à des questions de culture générale, expliquer des cours, aider en
programmation, écrire, traduire, donner des idées, ou simplement bavarder.

Tu as aussi une spécialité : aider à améliorer un CV, rédiger une lettre de
motivation, préparer un entretien, comprendre une offre et trouver un stage.
Mets cette expertise en avant quand l'utilisateur parle de stage, d'emploi ou
d'études, mais ne ramène jamais la conversation vers le stage s'il parle d'autre chose.

Règles importantes :
- Réponds dans la langue ou le dialecte de l'utilisateur (français, arabe, darija, anglais...).
- Si l'utilisateur te dit bonjour, réponds par un salut court et chaleureux
  et demande-lui ce qu'il veut faire, sans énumérer tes services.
- Adapte la longueur : court pour un message simple, détaillé pour une question complexe.
  Tes réponses peuvent être lues à voix haute : évite la mise en forme lourde quand ce n'est pas utile.
- Tiens compte des messages précédents ("il", "elle", "ce CV", "ce stage"...).
- Si un fichier est joint (PDF, image, document), lis-le attentivement et base ta réponse sur son contenu.
- Sois honnête : n'invente rien, et dis-le quand tu ne sais pas.
- Pour la santé, le droit ou l'argent, donne des informations utiles et rappelle de consulter un professionnel quand c'est nécessaire.
- Termine tes réponses de manière naturelle et complète.
"""

# Modèle principal et modèles de secours (modifiables dans le fichier .env)
MODELE_PRINCIPAL_DEFAUT = "gemini-3.8-flash"
MODELES_SECOURS_DEFAUT = "gemini-3.6-flash,gemini-3.1-flash-lite"

# Délai maximum d'attente d'une réponse Gemini, en secondes (modifiable dans le .env :
# GEMINI_TIMEOUT_SECONDES=30). Sans limite, la page pouvait rester bloquée très longtemps.
TIMEOUT_DEFAUT_SECONDES = 30


def _est_temporaire(e):
    """Surcharge ou quota : une nouvelle tentative peut réussir."""
    code = getattr(e, "code", None)
    texte = str(e)
    return code in (429, 500, 502, 503, 504) or "UNAVAILABLE" in texte or "RESOURCE_EXHAUSTED" in texte


def _est_timeout(e):
    """Délai dépassé : Gemini a mis trop de temps à répondre."""
    nom = type(e).__name__.lower()
    texte = str(e).lower()
    return "timeout" in nom or "timed out" in texte or "timeout" in texte


def _generer(client, contents, config):
    """Appelle Gemini. Si le modèle est surchargé ou trop lent : réessaie, puis passe à un modèle de secours."""
    principal = os.getenv("GEMINI_MODEL", MODELE_PRINCIPAL_DEFAUT)
    secours = [m.strip() for m in os.getenv("GEMINI_MODELES_SECOURS", MODELES_SECOURS_DEFAUT).split(",") if m.strip()]
    modeles = [principal] + [m for m in secours if m != principal]

    derniere_erreur = None
    for rang, modele in enumerate(modeles):
        for essai in range(2 if rang == 0 else 1):
            debut = time.time()
            try:
                reponse = client.models.generate_content(
                    model=modele, contents=contents, config=config
                )
                duree = time.time() - debut
                print(f"Gemini : réponse de {modele} en {duree:.1f} s")
                if rang > 0:
                    print(f"Gemini : modèle de secours utilisé ({modele})")
                return reponse
            except Exception as e:
                derniere_erreur = e
                duree = time.time() - debut
                introuvable = getattr(e, "code", None) == 404
                trop_lent = _est_timeout(e)
                if rang == 0 and not (_est_temporaire(e) or trop_lent):
                    raise
                if rang > 0 and not (_est_temporaire(e) or introuvable or trop_lent):
                    raise
                motif = "délai dépassé" if trop_lent else getattr(e, "code", "?")
                print(f"Gemini : {modele} indisponible ({motif}) après {duree:.1f} s, on essaie la suite…")
                if trop_lent:
                    break  # inutile de réessayer le même modèle : on passe au suivant
                if rang == 0 and essai == 0:
                    time.sleep(1.5)
    raise derniere_erreur


MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_CARACTERES_TEXTE = 30000


def _part_fichier(path, mime, nom):
    """Transforme un fichier du disque en élément Gemini (None si illisible)."""
    try:
        if mime == MIME_DOCX:
            # Gemini ne lit pas le Word directement : on extrait le texte
            from docx import Document
            doc = Document(path)
            lignes = [p.text for p in doc.paragraphs if p.text.strip()]
            for tableau in doc.tables:
                for ligne in tableau.rows:
                    lignes.append(" | ".join(c.text.strip() for c in ligne.cells))
            texte = "\n".join(lignes)
            return types.Part(text=f"[Contenu du fichier « {nom} »]\n{texte[:MAX_CARACTERES_TEXTE]}")

        if mime == "text/plain":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                texte = f.read()
            return types.Part(text=f"[Contenu du fichier « {nom} »]\n{texte[:MAX_CARACTERES_TEXTE]}")

        # PDF et images : envoyés tels quels
        with open(path, "rb") as f:
            return types.Part.from_bytes(data=f.read(), mime_type=mime)

    except Exception as e:
        print("Fichier joint illisible :", repr(e))
        return None


def demander_au_llm(question, provider="gemini", historique=None, fichier=None):
    """Envoie une question à Gemini avec l'historique et, si besoin, un fichier.

    fichier : dict {"nom": ..., "path": ..., "mime": ...} joint à la nouvelle question.
    Sans nouveau fichier, le dernier fichier de la conversation reste joint
    pour que Gemini puisse répondre aux questions de suivi.
    """

    if not isinstance(question, str) or not question.strip():
        raise ValueError("La question ne peut pas être vide.")

    if provider.lower().strip() != "gemini":
        raise ValueError("Cette version utilise Gemini uniquement.")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY est absente du fichier .env."
        )

    try:
        timeout_secondes = float(os.getenv("GEMINI_TIMEOUT_SECONDES", TIMEOUT_DEFAUT_SECONDES))
    except ValueError:
        timeout_secondes = TIMEOUT_DEFAUT_SECONDES

    # Le délai de la bibliothèque Gemini est exprimé en millisecondes
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=int(timeout_secondes * 1000)),
    )

    # Messages valides de l'historique (20 derniers)
    messages = []
    for message in (historique or [])[-20:]:
        if not isinstance(message, dict):
            continue
        if message.get("role") not in ("user", "assistant"):
            continue
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            continue
        messages.append(message)

    # Indice du dernier message de l'historique qui avait un fichier
    index_fichier = None
    if not fichier:
        for i, message in enumerate(messages):
            if message["role"] == "user" and message.get("fichier_path"):
                index_fichier = i

    # Convertir l'historique en messages Gemini
    contents = []
    for i, message in enumerate(messages):
        parts = []
        if i == index_fichier:
            part = _part_fichier(
                message["fichier_path"],
                message.get("fichier_mime"),
                message.get("fichier_nom") or "fichier",
            )
            if part:
                parts.append(part)
        parts.append(types.Part(text=message["content"].strip()))

        contents.append(
            types.Content(
                role="user" if message["role"] == "user" else "model",
                parts=parts
            )
        )

    # Ajouter la nouvelle question (avec son fichier éventuel)
    parts = []
    if fichier:
        part = _part_fichier(fichier["path"], fichier["mime"], fichier["nom"])
        if not part:
            raise ValueError("Impossible de lire le fichier joint.")
        parts.append(part)
    parts.append(types.Part(text=question.strip()))

    contents.append(types.Content(role="user", parts=parts))

    response = _generer(
        client,
        contents,
        types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=4096,
            temperature=0.7,
        ),
    )

    texte = response.text

    if not texte or not texte.strip():
        # Expliquer pourquoi la réponse est vide (limite atteinte, filtre de sécurité...)
        raison = ""
        try:
            if response.candidates:
                raison = str(response.candidates[0].finish_reason)
            else:
                raison = str(response.prompt_feedback)
        except Exception:
            pass
        raise RuntimeError(
            f"Gemini n'a retourné aucune réponse ({raison or 'raison inconnue'}). "
            "Réessaie ou reformule ta question."
        )

    return texte.strip()