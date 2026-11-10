import io
import re
import zipfile

import pytest
from flask import Flask, jsonify, render_template_string, session

import security


def creer_app(monkeypatch, env="development", secret="x" * 40, max_len=None):
    monkeypatch.setenv("APP_ENV", env)
    if secret is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", secret)
    app = Flask(__name__)
    security.init_security(app)
    if max_len:
        app.config["MAX_CONTENT_LENGTH"] = max_len
    security.reinitialiser_limiteur()

    @app.route("/")
    def accueil():
        return "accueil"

    @app.route("/form")
    def form():
        return render_template_string('<form method="POST">{{ csrf_token() }}</form>')

    @app.route("/poster", methods=["POST"])
    def poster():
        return "ok"

    @app.route("/favoris/<int:i>", methods=["POST"])
    def favoris(i):
        return jsonify(favori=True)

    @app.route("/connexion", methods=["GET", "POST"])
    @security.limiter_tentatives(3, 60)
    def connexion():
        return "tentative"

    return app


def jeton(client):
    html = client.get("/form").get_data(as_text=True)
    return re.search(r"[0-9a-f]{64}", html).group(0)


# ---------------- CSRF
def test_post_sans_jeton_refuse(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    r = c.post("/poster")
    assert r.status_code == 302  # redirigé avec message, action non exécutée
    assert b"ok" not in r.data


def test_post_jeton_invalide_refuse(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    jeton(c)
    r = c.post("/poster", data={"csrf_token": "faux"})
    assert r.status_code == 302


def test_post_jeton_valide_accepte(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    t = jeton(c)
    assert c.post("/poster", data={"csrf_token": t}).get_data(as_text=True) == "ok"


def test_post_jeton_en_en_tete(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    t = jeton(c)
    assert c.post("/favoris/3", headers={"X-CSRFToken": t}).get_json() == {"favori": True}


def test_post_json_sans_jeton_renvoie_400_json(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    r = c.post("/favoris/3")
    assert r.status_code == 400 and "erreur" in r.get_json()


def test_get_non_concerne(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    assert c.get("/").status_code == 200


def test_jeton_d_une_autre_session_refuse(monkeypatch):
    app = creer_app(monkeypatch)
    t1 = jeton(app.test_client())
    c2 = app.test_client()
    jeton(c2)
    assert c2.post("/poster", data={"csrf_token": t1}).status_code == 302


# ---------------- SECRET_KEY / cookies / en-têtes
def test_production_sans_secret_key_refuse_de_demarrer(monkeypatch):
    with pytest.raises(RuntimeError):
        creer_app(monkeypatch, env="production", secret=None)


def test_vercel_est_detecte_comme_production_sans_app_env(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        security.init_security(Flask(__name__))


def test_production_secret_par_defaut_ou_court_refuse(monkeypatch):
    with pytest.raises(RuntimeError):
        creer_app(monkeypatch, env="production", secret="change-moi-plus-tard-avec-une-vraie-cle-secrete")
    with pytest.raises(RuntimeError):
        creer_app(monkeypatch, env="production", secret="court")


def test_developpement_sans_secret_genere_cle_aleatoire(monkeypatch):
    a = creer_app(monkeypatch, secret=None)
    b = creer_app(monkeypatch, secret=None)
    assert a.secret_key and a.secret_key != b.secret_key


def test_cookies_securises_en_production(monkeypatch):
    app = creer_app(monkeypatch, env="production")
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"


def test_cookie_non_secure_en_local(monkeypatch):
    assert creer_app(monkeypatch).config["SESSION_COOKIE_SECURE"] is False


def test_en_tetes_http(monkeypatch):
    r = creer_app(monkeypatch, env="production").test_client().get("/")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert "Strict-Transport-Security" in r.headers


def test_cookie_de_session_httponly(monkeypatch):
    r = creer_app(monkeypatch).test_client().get("/form")
    assert "HttpOnly" in r.headers["Set-Cookie"]


# ---------------- uploads
def test_413_si_requete_trop_grosse(monkeypatch):
    app = creer_app(monkeypatch, max_len=100)
    c = app.test_client()
    t = jeton(c)
    r = c.post("/poster", data={"csrf_token": t, "f": (io.BytesIO(b"a" * 5000), "a.pdf")},
               content_type="multipart/form-data")
    assert r.status_code in (302, 413)
    assert b"ok" not in r.data


def faux_docx(avec_document=True):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml" if avec_document else "autre.xml", "<x/>")
    return buf.getvalue()


def test_signature_pdf():
    assert security.contenu_fichier_valide(b"%PDF-1.7\n...", "pdf")
    assert not security.contenu_fichier_valide(b"MZ\x90\x00 exe deguise", "pdf")
    assert not security.contenu_fichier_valide(b"<html>", "pdf")


def test_signature_docx():
    assert security.contenu_fichier_valide(faux_docx(), "docx")
    assert not security.contenu_fichier_valide(faux_docx(False), "docx")
    assert not security.contenu_fichier_valide(b"PK\x03\x04pas un zip valide", "docx")
    assert not security.contenu_fichier_valide(b"%PDF-1.4", "docx")


def test_signatures_images():
    assert security.contenu_fichier_valide(b"\x89PNG\r\n\x1a\n" + b"0" * 8, "png")
    assert security.contenu_fichier_valide(b"\xff\xd8\xff\xe0" + b"0" * 8, "jpg")
    assert security.contenu_fichier_valide(b"\xff\xd8\xff\xe0" + b"0" * 8, "jpeg")
    assert security.contenu_fichier_valide(b"RIFF\x00\x00\x00\x00WEBPVP8 ", "webp")
    assert not security.contenu_fichier_valide(b"<svg onload=alert(1)>", "png")
    assert not security.contenu_fichier_valide(b"GIF89a", "jpg")


def test_extension_inconnue_refusee():
    assert not security.contenu_fichier_valide(b"%PDF-", "exe")
    assert not security.contenu_fichier_valide(b"%PDF-", "")


def test_txt_binaire_refuse():
    assert security.contenu_fichier_valide("bonjour".encode(), "txt")
    assert not security.contenu_fichier_valide(b"abc\x00def", "txt")


# ---------------- limiteur de tentatives
def test_limiteur_bloque_apres_n_tentatives(monkeypatch):
    app = creer_app(monkeypatch)
    c = app.test_client()
    t = jeton(c)
    codes = []
    for _ in range(5):
        r = c.post("/connexion", data={"csrf_token": t})
        codes.append((r.status_code, b"tentative" in r.data))
    assert codes[:3] == [(200, True)] * 3
    assert all(not ok for _, ok in codes[3:])


def test_limiteur_ignore_les_get(monkeypatch):
    c = creer_app(monkeypatch).test_client()
    for _ in range(10):
        assert c.get("/connexion").status_code == 200
