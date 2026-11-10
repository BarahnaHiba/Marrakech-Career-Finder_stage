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

La base utilisée par l'application est PostgreSQL sur Neon. Le schéma existant est mis à jour avec les scripts SQL
de `database/migrations/`; la migration **001** est idempotente et ajoute notamment `cv.analyse_json`, des index
et des contraintes sans rejeter les lignes existantes. Pour l'appliquer à Neon depuis ton ordinateur, configure
`DATABASE_URL` dans `backend/.env`, puis exécute :

```bash
python database/appliquer_migration.py database/migrations/001_harmonisation.sql
```

Les anciennes sauvegardes locales ne sont ni suivies par Git ni envoyées à Vercel.

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

## Déploiement Vercel + GitHub + Neon

### Avant l'import

1. Vérifie que le projet Neon est actif et que `DATABASE_URL` correspond à la base qui contient le schéma PostgreSQL de l'application. L'URL doit inclure `sslmode=require`.
2. Si nécessaire, applique les migrations SQL depuis ton ordinateur, jamais au démarrage de chaque fonction Vercel :
   `python database/appliquer_migration.py database/migrations/001_harmonisation.sql`.
3. Pousse le dépôt sur GitHub. Les bases et sauvegardes locales sont ignorées et exclues du déploiement ; elles ne servent pas à Vercel.

### Import et configuration Vercel

1. Dans Vercel, choisis **Add New → Project** et importe le dépôt GitHub. Garde **Root Directory** sur `./`.
2. Laisse Vercel détecter Flask/Python. `pyproject.toml` déclare le point d'entrée `backend.app:app`, `requirements.txt` liste les dépendances et `vercel.json` configure la fonction Python.
3. Dans **Settings → Environment Variables**, ajoute les variables nécessaires dans les environnements où tu déploies :
   - `APP_ENV=production`
   - `SECRET_KEY` : valeur aléatoire d'au moins 24 caractères ; génère-la localement avec `python -c "import secrets; print(secrets.token_hex(32))"`
   - `DATABASE_URL` : chaîne Neon PostgreSQL avec `sslmode=require`
   - `GEMINI_API_KEY` : nécessaire pour les fonctions d'assistance IA
   - `ADMIN_EMAILS` : liste des adresses admin séparées par des virgules
   - Email de vérification et de réinitialisation : configuration Brevo complète (`BREVO_SMTP_LOGIN`, `BREVO_SMTP_KEY`, `EMAIL_EXPEDITEUR`) ou Gmail (`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`)
   - `MODE_ENVOI=test` pour commencer ; passe à `reel` seulement après avoir vérifié que les candidatures doivent réellement être envoyées aux entreprises.
4. N'ajoute jamais `backend/.env` à Git ni aux fichiers de déploiement. Vercel fournit automatiquement `VERCEL`; l'application l'utilise pour activer les protections de production.
5. Lance **Deploy**. Dans **Deployments → Build Logs**, vérifie l'installation des dépendances et la détection du point d'entrée.
6. Vérifie ensuite `/healthz`, l'accueil, la page **Contacts**, puis teste inscription, vérification email, connexion et fonctions qui utilisent Neon.

### Limites de l'hébergement

- Les fichiers uploadés sont écrits dans `/tmp` sur Vercel ; ce stockage est temporaire et n'est pas partagé entre les invocations. Configure un stockage objet persistant avant de dépendre de la consultation ultérieure des CV et avatars.
- La carte des entreprises utilise Leaflet/OpenStreetMap et le géocodeur public Nominatim à la demande. Le nom et l'adresse de l'entreprise sont transmis à OpenStreetMap lors de la recherche.
- Le limiteur de tentatives est en mémoire et ne fournit pas de quota global partagé entre plusieurs instances.
- Consulte les conditions d'utilisation des services email, de Neon et des sources de données avant la mise en production.

L'espace `/admin` est réservé aux utilisateurs connectés dont l'adresse figure dans `ADMIN_EMAILS`. Il affiche des statistiques, les utilisateurs et les candidatures récentes, et permet de modifier le statut des candidatures. Il ne permet pas de supprimer des comptes ni des candidatures.

## Structure

```
backend/        application Flask (app.py, security.py, llm_service.py, templates/, static/)
matching/       matching.py (score explicable), competences.py (référentiel), cv_parser.py (analyse de CV)
database/       migrations PostgreSQL et script d'application local
tests/          tests automatisés
DATA SUR EXCEL/ sources locales, exclues du déploiement
```
