-- Retour arrière de 001_harmonisation.sql : restaure les anciens statuts depuis la sauvegarde.
-- (La colonne cv.analyse_json et les index sont inoffensifs et conservés.)
BEGIN;
ALTER TABLE applications DROP CONSTRAINT IF EXISTS applications_statut_check;
ALTER TABLE applications ALTER COLUMN statut SET DEFAULT 'À préparer';
UPDATE applications a
   SET statut = b.statut
  FROM applications_backup_20261109 b
 WHERE a.id = b.id;
COMMIT;
