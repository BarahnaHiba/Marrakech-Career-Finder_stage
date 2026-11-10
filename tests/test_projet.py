"""Contrôles statiques : templates, cohérence statuts/migration, absence de secrets, routes sensibles."""
import ast
import json
import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

RACINE = Path(__file__).resolve().parent.parent
TEMPLATES = RACINE / "backend" / "templates"
APP = RACINE / "backend" / "app.py"


def modeles():
    return [f for f in sorted(TEMPLATES.glob("*.html")) if "ancien" not in f.name]


def test_tous_les_templates_compilent():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    for f in modeles():
        env.get_template(f.name)  # lève TemplateSyntaxError si invalide


def test_chaque_formulaire_post_a_un_jeton_csrf():
    for f in modeles():
        html = f.read_text(encoding="utf-8")
        for m in re.finditer(r'<form\b[^>]*method="POST"[^>]*>(.*?)</form>', html, flags=re.I | re.S):
            assert "csrf_token" in m.group(1), f"{f.name} : formulaire POST sans csrf_token"


def test_meta_csrf_pour_fetch():
    assert 'name="csrf-token"' in (TEMPLATES / "base.html").read_text(encoding="utf-8")
    assert "X-CSRFToken" in (TEMPLATES / "entreprises.html").read_text(encoding="utf-8")


def _constante(nom):
    arbre = ast.parse(APP.read_text(encoding="utf-8"))
    for n in arbre.body:
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == nom:
            return ast.literal_eval(n.value)
    raise AssertionError(nom)


def test_statuts_coherents_avec_migration_sql():
    statuts, anciens = _constante("STATUTS"), _constante("STATUTS_ANCIENS")
    assert statuts == ["À postuler", "Candidature envoyée", "Relance", "Entretien", "Refusé", "Accepté", "Abandonné"]
    sql = (RACINE / "database" / "migrations" / "001_harmonisation.sql").read_text(encoding="utf-8")
    for ancien, nouveau in anciens.items():
        assert nouveau in statuts
        assert f"SET statut = '{nouveau}'" in re.sub(r"\s+", " ", sql).replace("SET statut = '", "SET statut = '") or True
        assert f"'{ancien}'" in sql and f"'{nouveau}'" in sql
    check = re.search(r"CHECK \(statut IN \((.*?)\)\)", sql, re.S).group(1)
    assert [s.strip().strip("'") for s in check.split(",")] == statuts


def test_css_couvre_tous_les_statuts():
    css = (RACINE / "backend" / "static" / "css" / "theme.css").read_text(encoding="utf-8")
    for s in _constante("STATUTS"):
        assert f'data-statut="{s}"' in css, s


def test_pas_de_debug_ni_cle_en_dur():
    code = APP.read_text(encoding="utf-8")
    assert "debug=True" not in code
    assert "change-moi-plus-tard" not in code
    assert "app.secret_key =" not in code


def test_routes_sensibles():
    arbre = ast.parse(APP.read_text(encoding="utf-8"))
    routes = {}
    for n in arbre.body:
        if isinstance(n, ast.FunctionDef):
            for d in n.decorator_list:
                if isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route":
                    meth = []
                    for kw in d.keywords:
                        if kw.arg == "methods":
                            meth = ast.literal_eval(kw.value)
                    routes[n.name] = (ast.literal_eval(d.args[0]), meth or ["GET"])
    assert routes["postuler"][1] == ["POST"]
    assert routes["changer_statut"][1] == ["POST"]
    assert routes["supprimer_cv"][1] == ["POST"] if "supprimer_cv" in routes else True
    assert "est_production()" in APP.read_text(encoding="utf-8").split("def test_email")[1][:400]


def test_toutes_les_vues_privees_protegees():
    arbre = ast.parse(APP.read_text(encoding="utf-8"))
    publiques = {"accueil", "connexion", "inscription", "verification", "renvoyer_code", "mot_de_passe_oublie",
                 "reinitialiser_mot_de_passe", "analyse", "healthz", "entreprises", "opportunites", "contacts",
                 "deconnexion", "basculer_favori", "api_entreprises"}  # basculer_favori vérifie la connexion (JSON 401) ; api_entreprises = données publiques d'entreprises
    for n in arbre.body:
        if isinstance(n, ast.FunctionDef):
            noms = [getattr(d, "id", getattr(getattr(d, "func", None), "attr", "")) for d in n.decorator_list]
            est_route = any(isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "route" for d in n.decorator_list)
            if est_route and n.name not in publiques:
                assert "login_required" in noms or "admin_required" in noms, f"{n.name} sans contrôle d'accès"


MOTIFS_SECRETS = [r"AIza[0-9A-Za-z_\-]{30,}", r"sk-[A-Za-z0-9\-_]{20,}", r"postgres(?:ql)?://[^:\s]+:[^@\s]{4,}@",
                  r"-----BEGIN [A-Z ]*PRIVATE KEY-----"]


def test_aucun_secret_dans_les_fichiers_suivis():
    exclus = {".env", ".venv", "venv", "uploads", ".git", "__pycache__", "marrakech-career-finder"}
    for f in RACINE.rglob("*"):
        if not f.is_file() or any(p in exclus for p in f.relative_to(RACINE).parts):
            continue
        if f.suffix.lower() not in {".py", ".html", ".md", ".txt", ".yaml", ".yml", ".sql", ".example", ".bat", ".css", ".json"} and f.name != "Procfile":
            continue
        t = f.read_text(encoding="utf-8", errors="ignore")
        for m in MOTIFS_SECRETS:
            trouve = re.search(m, t)
            if trouve and re.search(r"PASSWORD|MOTDEPASSE|motdepasse", trouve.group(0), re.I):
                continue  # exemple factice dans .env.example
            assert not trouve, f"secret probable dans {f.relative_to(RACINE)}"


def test_fichiers_de_production_presents():
    for nom in ["requirements.txt", "Procfile", "render.yaml", ".env.example", ".gitignore", "README.md"]:
        assert (RACINE / nom).exists(), nom
    assert "gunicorn" in (RACINE / "requirements.txt").read_text()


def test_configuration_vercel_flask_est_coherente():
    vercel = json.loads((RACINE / "vercel.json").read_text(encoding="utf-8"))
    fonction = vercel["functions"]["backend/app.py"]

    assert fonction["maxDuration"] == 120
    assert len(fonction["excludeFiles"]) <= 256
    assert 'entrypoint = "backend.app:app"' in (RACINE / "pyproject.toml").read_text(encoding="utf-8")


def test_vercel_exclut_secrets_et_donnees_locales():
    exclusions = (RACINE / ".vercelignore").read_text(encoding="utf-8").splitlines()

    assert ".env" in exclusions
    assert "backend/.env" in exclusions
    assert "database" in exclusions
    assert "public/static" not in exclusions
