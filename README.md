# Marrakech Career Finder

Plateforme web de recherche de stages et d'emplois à Marrakech : entreprises référencées, matching
CV ↔ offres explicable (TF-IDF + compétences), suivi des candidatures, favoris, assistant IA (Gemini),
génération de CV en PDF et tableau de bord.

**Stack :** Python · Flask · Jinja2 · Bootstrap · PostgreSQL (Neon) via psycopg · scikit-learn · pdfplumber · python-docx · reportlab.

## Fonctionnalités

| Domaine | Détail |
|---|---|
| Comptes | Inscription, vérification de l'email par code, connexion, mot de passe oublié, profil, avatar |
| CV | Import PDF/DOCX (signature du fichier vérifiée), voir/télécharger/supprimer, **analyse détaillée** (coordonnées, formation, expériences, projets, compétences techniques et personnelles, langues, certifications) et **recommandations** |
| Matching | Score 0-100 expliqué : 50 % compétences couvertes, 35 % similarité TF-IDF, 15 % intitulé du poste. Compétences communes, manquantes, à apprendre. Page *Recommandations* |
| Recherche | Entreprises/opportunités avec filtres secteur, ville, priorité, favoris |
| Suivi | Candidatures avec statuts (À postuler, Candidature envoyée, Relance, Entretien, Refusé, Accepté, Abandonné), remarques, dates, favoris |
| Assistant IA | Conversation, pièces jointes (PDF, DOCX, TXT, images), erreurs d'API gérées |
| CV | Génération/amélioration, adaptation à une offre, export PDF |
| Dashboard | Statistiques réelles issues de la base + graphiques + activité récente |

> Le score de matching ne repose que sur ce que contient réellement le CV. Quand une offre ne détaille pas
> ses compétences, celles « typiques du poste » sont utilisées et l'interface le précise.

## Installation locale

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate      Linux/macOS : source .venv/bin/activate
pip install -r requirements.txt
cp .env.example backend/.env        # Windows : copy .env.example backend\.env
# éditer backend/.env : SECRET_KEY, DATABASE_URL, GEMINI_API_KEY et paramètres email
python -c "import secrets; print(secrets.token_hex(32))"   # valeur pour SECRET_KEY
python database/appliquer_migration.py database/migrations/001_harmonisation.sql
python backend/app.py        # http://127.0.0.1:5000   (ou double-clic sur lancer.bat sous Windows)
```

## Base de données

Le schéma est créé/migré par `backend/migrate_sqlite_to_neon.py` (import initial depuis SQLite) puis par les
fichiers de `database/migrations/`. La migration **001** est idempotente, sauvegarde `applications` dans une table
de secours, convertit les anciens statuts, ajoute `cv.analyse_json`, des index et des contraintes (en `NOT VALID` :
aucune ligne existante n'est rejetée). Retour arrière : `001_rollback.sql`. Le script exporte aussi
`applications` et `cv` en CSV dans `database/sauvegardes/` avant d'appliquer.

L'application fonctionne **avant** l'application de la migration (l'analyse du CV est alors recalculée à la volée).

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests -q
```

## Sécurité

- `SECRET_KEY` obligatoire en production (l'appli refuse de démarrer sinon) ; cookies HttpOnly, SameSite=Lax, Secure en production.
- Protection CSRF sur tous les POST (champ `csrf_token`, en-tête `X-CSRFToken` pour le JavaScript).
- Envoi de candidature (`/postuler`) en POST uniquement ; `/test-email` désactivé en production.
- Uploads : extension + signature réelle du fichier (PDF/DOCX/PNG/JPG/WEBP), taille limitée à 12 Mo.
- Limitation des tentatives sur connexion, inscription, vérification et réinitialisation (par processus).
- Requêtes SQL paramétrées, mots de passe hachés (Werkzeug), en-têtes de sécurité (HSTS en production).
- Aucun secret dans le dépôt : `backend/.env` est ignoré par git. **Si un `.env` a déjà été partagé, régénère toutes les clés.**

## Déploiement (GitHub + Render + Neon)

1. Régénérer les clés (Gemini, mot de passe d'application Gmail, mot de passe Neon) si elles ont été exposées.
2. Pousser le code sur GitHub (commandes dans la section ci-dessous).
3. Sur Render : *New + → Blueprint* → choisir le dépôt (`render.yaml`), ou *Web Service* manuel :
   - Build : `pip install -r requirements.txt`
   - Start : `gunicorn --chdir backend app:app --workers 2 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT`
   - Variables : `APP_ENV=production`, `SECRET_KEY`, `DATABASE_URL` (Neon, `sslmode=require`), `GEMINI_API_KEY`, `ADMIN_EMAILS` (adresses autorisées, séparées par des virgules), `MODE_ENVOI=test` et une configuration email complète.
     Vérification : Brevo (`BREVO_SMTP_LOGIN`, `BREVO_SMTP_KEY`, `EMAIL_EXPEDITEUR`, adresse validée dans Brevo) ou Gmail (`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, mot de passe d'application). Brevo est prioritaire si ses trois paramètres sont définis. Gmail reste aussi nécessaire pour les autres emails de l'application.
   - Health check : `/healthz`
4. Appliquer la migration sur Neon (depuis ta machine, avec `DATABASE_URL` de Neon dans `backend/.env`).
5. Tester l'URL publique : inscription → vérification email → CV → recommandations → favoris → candidature.

### Déploiement Vercel

1. Pousser le dépôt sur GitHub puis l'importer dans Vercel. Garder `Root Directory` sur `./` ; le projet est configuré pour le preset Flask.
2. Dans **Settings → Environment Variables**, ajouter les variables nécessaires :
   `APP_ENV=production`, `SECRET_KEY` (au moins 24 caractères aléatoires), `DATABASE_URL` (Neon avec `sslmode=require`),
   `GEMINI_API_KEY`, `ADMIN_EMAILS` (ajouter `kamiliyaclientcare@gmail.com` pour autoriser ton compte admin) et les variables SMTP décrites ci-dessus.
   Pour Brevo : `BREVO_SMTP_LOGIN`, `BREVO_SMTP_KEY`, `EMAIL_EXPEDITEUR`. Gmail reste nécessaire pour les autres emails : `GMAIL_ADDRESS` et `GMAIL_APP_PASSWORD`.
3. Laisser Vercel utiliser `requirements.txt` pour installer les dépendances, puis lancer **Deploy**.
   `pyproject.toml` pointe vers l'application Flask et `vercel.json` configure la fonction Python.
4. Les fichiers envoyés sont stockés temporairement dans `/tmp` sur Vercel. Ils peuvent disparaître entre deux requêtes ou déploiements ;
   configure un stockage persistant (par exemple Vercel Blob ou S3) avant de dépendre de la consultation/téléchargement des CV et avatars.
5. Après le déploiement, vérifier `/healthz`, l'inscription et la réception d'un code sur une vraie adresse.
6. La carte des entreprises utilise Leaflet/OpenStreetMap et le géocodeur public Nominatim à la demande ; un seul emplacement est recherché par ouverture de carte, avec cache local à la fonction et limitation à une requête par seconde. L'adresse/nom de l'entreprise est transmis à OpenStreetMap pour la recherche.

L'espace `/admin` est réservé aux utilisateurs connectés dont l'adresse figure dans `ADMIN_EMAILS`. Il affiche des statistiques, les utilisateurs et les candidatures récentes, et permet de modifier le statut des candidatures. Il ne permet pas de supprimer des comptes ni des candidatures.

### Limites à connaître en production

- **Fichiers uploadés éphémères sur Render** : les CV et avatars enregistrés sur disque disparaissent à chaque redéploiement
  (le texte extrait et l'analyse restent en base, donc matching et analyse continuent de fonctionner ; seul « Voir/Télécharger le CV »
  échoue). Solutions : disque persistant Render (payant) monté sur `backend/uploads` et `backend/static/avatars`, ou stockage objet (S3, Cloudflare R2).
- Le limiteur de tentatives est en mémoire (une limite par worker). Pour une limite globale : Flask-Limiter + Redis.
- `MODE_ENVOI=reel` envoie de vrais emails aux entreprises : à n'activer qu'en connaissance de cause.
- Sources de données : respecter les conditions d'utilisation de chaque plateforme (pas de scraping interdit).

## Structure

```
backend/        application Flask (app.py, security.py, llm_service.py, templates/, static/)
matching/       matching.py (score explicable), competences.py (référentiel), cv_parser.py (analyse de CV)
database/       migrations SQL, script d'application, init SQLite historique
scripts/        scripts ponctuels (import Excel, vérifications) — chemins à adapter si besoin
tests/          tests automatisés
DATA SUR EXCEL/ sources de données et rapports Excel d'origine
```
