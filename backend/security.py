"""
Sécurité de Marrakech Career Finder.

Ce module regroupe, sans dépendance externe (Flask suffit) :
  - la configuration sûre des sessions / cookies / taille des uploads ;
  - la protection CSRF (jeton en session, vérifié sur toutes les requêtes POST/PUT/PATCH/DELETE) ;
  - les en-têtes HTTP de sécurité ;
  - la vérification du contenu réel des fichiers envoyés (signatures PDF, DOCX, images) ;
  - une limitation simple des tentatives (anti force brute) ;
  - des gestionnaires d'erreurs propres (400 CSRF, 413 fichier trop gros).

Utilisation dans app.py :
    from security import init_security, limiter_tentatives, contenu_fichier_valide
    init_security(app)
"""
import hmac
import os
import secrets
import time
import zipfile
from collections import defaultdict, deque
from functools import wraps

from flask import abort, flash, jsonify, redirect, request, session, url_for

METHODES_PROTEGEES = {"POST", "PUT", "PATCH", "DELETE"}
TAILLE_MAX_REQUETE = 12 * 1024 * 1024  # 12 Mo (CV : 10 Mo max côté assistant)


# ---------------------------------------------------------------------------
# Environnement
# ---------------------------------------------------------------------------
def est_production():
    """Production = APP_ENV=production, ou plateforme Render détectée."""
    env = os.environ.get("APP_ENV", "").strip().lower()
    if env:
        return env == "production"
    return bool(os.environ.get("RENDER"))


def charger_secret_key():
    """
    Retourne la SECRET_KEY. En production elle est OBLIGATOIRE (sinon l'appli refuse
    de démarrer). En développement une clé aléatoire éphémère est générée : les sessions
    sont alors perdues à chaque redémarrage, ce qui est sans danger.
    """
    cle = os.environ.get("SECRET_KEY", "").strip()
    faibles = {"", "change-moi-plus-tard-avec-une-vraie-cle-secrete", "changeme", "secret"}
    if cle in faibles or len(cle) < 24:
        if est_production():
            raise RuntimeError(
                "SECRET_KEY absente ou trop faible (24 caractères minimum). "
                "Génère-en une avec : python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        print("[sécurité] SECRET_KEY absente/faible : clé aléatoire temporaire utilisée (dev uniquement).")
        return secrets.token_hex(32)
    return cle


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------
def generer_jeton_csrf():
    jeton = session.get("_csrf_token")
    if not jeton:
        jeton = secrets.token_hex(32)
        session["_csrf_token"] = jeton
    return jeton


def _verifier_csrf():
    if request.method not in METHODES_PROTEGEES:
        return
    attendu = session.get("_csrf_token")
    recu = request.form.get("csrf_token") or request.headers.get("X-CSRFToken") or ""
    if not attendu or not hmac.compare_digest(str(attendu), str(recu)):
        abort(400, description="CSRF")


# ---------------------------------------------------------------------------
# Signatures de fichiers
# ---------------------------------------------------------------------------
def contenu_fichier_valide(donnees, extension):
    """
    Vérifie que le contenu correspond vraiment à l'extension annoncée.
    `donnees` : bytes (début du fichier suffisant sauf pour docx qui est un zip complet).
    """
    ext = (extension or "").lower().lstrip(".")
    if ext == "pdf":
        return donnees[:5] == b"%PDF-"
    if ext == "docx":
        import io

        if donnees[:4] != b"PK\x03\x04":
            return False
        try:
            with zipfile.ZipFile(io.BytesIO(donnees)) as z:
                return "word/document.xml" in z.namelist()
        except zipfile.BadZipFile:
            return False
    if ext == "png":
        return donnees[:8] == b"\x89PNG\r\n\x1a\n"
    if ext in ("jpg", "jpeg"):
        return donnees[:3] == b"\xff\xd8\xff"
    if ext == "webp":
        return donnees[:4] == b"RIFF" and donnees[8:12] == b"WEBP"
    if ext == "txt":
        return b"\x00" not in donnees[:4096]
    return False


# ---------------------------------------------------------------------------
# Limitation des tentatives (en mémoire, par processus)
# ---------------------------------------------------------------------------
_tentatives = defaultdict(deque)


def _ip_client():
    # ProxyFix (activé dans init_security) place la vraie IP dans remote_addr sur Render.
    return request.remote_addr or "inconnue"


def limiter_tentatives(maximum=8, fenetre=300):
    """
    Décorateur : au-delà de `maximum` requêtes POST en `fenetre` secondes depuis la même IP
    sur la même route, répond « trop de tentatives ». À placer SOUS @app.route.
    Note : compteur par processus. Avec plusieurs workers gunicorn la limite effective est
    maximum × workers ; pour une limite globale, utiliser Redis (Flask-Limiter).
    """

    def decorateur(vue):
        @wraps(vue)
        def enveloppe(*args, **kwargs):
            if request.method == "POST":
                cle = (_ip_client(), request.endpoint)
                maintenant = time.time()
                file = _tentatives[cle]
                while file and maintenant - file[0] > fenetre:
                    file.popleft()
                if len(file) >= maximum:
                    flash("Trop de tentatives. Patiente quelques minutes avant de réessayer.")
                    return redirect(request.url), 303
                file.append(maintenant)
            return vue(*args, **kwargs)

        return enveloppe

    return decorateur


def reinitialiser_limiteur():
    """Utilisé par les tests."""
    _tentatives.clear()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
def init_security(app):
    prod = est_production()
    app.secret_key = charger_secret_key()
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=prod,  # cookies uniquement en HTTPS en production
        REMEMBER_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SECURE=prod,
        REMEMBER_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
        MAX_CONTENT_LENGTH=TAILLE_MAX_REQUETE,
    )

    if prod:
        # Render termine le HTTPS devant l'appli : on fait confiance à X-Forwarded-*.
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    app.jinja_env.globals["csrf_token"] = generer_jeton_csrf
    app.before_request(_verifier_csrf)

    @app.after_request
    def en_tetes(reponse):
        reponse.headers.setdefault("X-Content-Type-Options", "nosniff")
        reponse.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        reponse.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        reponse.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if prod:
            reponse.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        if request.endpoint not in ("static", None):
            reponse.headers.setdefault("Cache-Control", "no-store")
        return reponse

    def _reponse_erreur(message, code):
        if request.accept_mimetypes.best == "application/json" or request.path.startswith("/favoris/"):
            return jsonify(erreur=message), code
        flash(message)
        cible = request.referrer or url_for("accueil")
        return redirect(cible)

    @app.errorhandler(400)
    def erreur_400(e):
        if getattr(e, "description", "") == "CSRF":
            return _reponse_erreur("Session expirée ou formulaire invalide. Recharge la page et réessaie.", 400)
        return e

    @app.errorhandler(413)
    def erreur_413(e):
        return _reponse_erreur("Fichier trop volumineux (12 Mo maximum).", 413)
