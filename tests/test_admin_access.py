from flask import Flask
from flask_login import LoginManager, UserMixin, login_user

from admin_access import admin_required, email_est_administrateur


class Utilisateur(UserMixin):
    def __init__(self, identifiant, email):
        self.id = identifiant
        self.email = email


def creer_app():
    app = Flask(__name__)
    app.secret_key = "cle-de-test-suffisamment-longue"
    gestionnaire = LoginManager()
    gestionnaire.init_app(app)

    @gestionnaire.user_loader
    def charger_utilisateur(identifiant):
        return Utilisateur(identifiant, identifiant)

    @app.route("/connexion-test/<email>")
    def connexion_test(email):
        login_user(Utilisateur(email, email))
        return "ok"

    @app.route("/admin")
    @admin_required
    def tableau_admin():
        return "admin"

    return app


def test_email_admin_est_normalise(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", " admin@example.com, autre@example.com ")

    assert email_est_administrateur("ADMIN@example.com")
    assert email_est_administrateur(" autre@example.com ")
    assert not email_est_administrateur("visiteur@example.com")


def test_liste_admin_vide_refuse_tout_acces(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)

    assert not email_est_administrateur("admin@example.com")


def test_route_admin_exige_authentification_et_email_autorise(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "admin@example.com")
    client = creer_app().test_client()

    assert client.get("/admin").status_code == 401
    client.get("/connexion-test/visiteur@example.com")
    assert client.get("/admin").status_code == 403
    client.get("/connexion-test/admin@example.com")
    assert client.get("/admin").get_data(as_text=True) == "admin"
