-- =====================================================================
-- Migration 001 — harmonisation du schéma (PostgreSQL / Neon)
-- Idempotente : peut être relancée sans risque. Ne supprime AUCUNE donnée.
--
--   * sauvegarde de la table applications avant tout changement
--   * nouvelle colonne cv.analyse_json (analyse détaillée du CV)
--   * statuts de candidature harmonisés (anciens libellés convertis)
--   * index de performance
--   * contraintes d'intégrité ajoutées en NOT VALID (n'affectent que les NOUVELLES lignes ;
--     les lignes existantes ne sont jamais rejetées)
--
-- Retour arrière : voir 001_rollback.sql
-- =====================================================================

BEGIN;

-- 0. Sauvegarde (créée une seule fois)
CREATE TABLE IF NOT EXISTS applications_backup_20261109 AS TABLE applications;

-- 1. Analyse du CV stockée en JSON (texte)
ALTER TABLE cv ADD COLUMN IF NOT EXISTS analyse_json TEXT;

-- 2. Statuts : anciens libellés -> libellés officiels
UPDATE applications SET statut = 'À postuler'           WHERE statut = 'À préparer' OR statut IS NULL;
UPDATE applications SET statut = 'Candidature envoyée'  WHERE statut = 'Envoyée';
UPDATE applications SET statut = 'Relance'              WHERE statut = 'En attente';
UPDATE applications SET statut = 'Accepté'              WHERE statut = 'Acceptée';
UPDATE applications SET statut = 'Refusé'               WHERE statut = 'Refusée';
ALTER TABLE applications ALTER COLUMN statut SET DEFAULT 'À postuler';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'applications_statut_check') THEN
        ALTER TABLE applications ADD CONSTRAINT applications_statut_check
            CHECK (statut IN ('À postuler', 'Candidature envoyée', 'Relance', 'Entretien',
                              'Refusé', 'Accepté', 'Abandonné')) NOT VALID;
    END IF;
END $$;

-- 3. Index
CREATE INDEX IF NOT EXISTS idx_applications_user      ON applications (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_company   ON applications (company_id);
CREATE INDEX IF NOT EXISTS idx_cv_user_date           ON cv (user_id, date_upload DESC);
CREATE INDEX IF NOT EXISTS idx_companies_secteur      ON companies (secteur);
CREATE INDEX IF NOT EXISTS idx_companies_ville        ON companies (ville);
CREATE INDEX IF NOT EXISTS idx_companies_score        ON companies (score_total DESC);
CREATE INDEX IF NOT EXISTS idx_assistant_user         ON assistant_messages (user_id);

-- 4. Intégrité : clés étrangères manquantes (NOT VALID = lignes existantes non contrôlées)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_favorites_user') THEN
        ALTER TABLE favorites ADD CONSTRAINT fk_favorites_user
            FOREIGN KEY (user_id) REFERENCES users (id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_favorites_company') THEN
        ALTER TABLE favorites ADD CONSTRAINT fk_favorites_company
            FOREIGN KEY (company_id) REFERENCES companies (id) NOT VALID;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_assistant_user') THEN
        ALTER TABLE assistant_messages ADD CONSTRAINT fk_assistant_user
            FOREIGN KEY (user_id) REFERENCES users (id) NOT VALID;
    END IF;
END $$;

-- 5. Unicité : créées seulement si les données actuelles le permettent (sinon simple avis)
DO $$
BEGIN
    BEGIN
        CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email_lower ON users (lower(email));
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'ux_users_email_lower non créé : des emails identiques (casse différente) existent déjà.';
    END;
    BEGIN
        CREATE UNIQUE INDEX IF NOT EXISTS ux_applications_user_company ON applications (user_id, company_id);
    EXCEPTION WHEN unique_violation THEN
        RAISE NOTICE 'ux_applications_user_company non créé : des candidatures en double existent déjà.';
    END;
END $$;

COMMIT;
