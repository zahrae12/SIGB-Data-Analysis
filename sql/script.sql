BEGIN;

-- 1. Table: LANGUE
CREATE TABLE IF NOT EXISTS LANGUE (
    code_langue VARCHAR(10) PRIMARY KEY,
    libelle_langue VARCHAR(100)
);

-- 2. Table: EDITEUR
CREATE TABLE IF NOT EXISTS EDITEUR (
    id_editeur SERIAL PRIMARY KEY,
    nom_editeur VARCHAR(255) UNIQUE NOT NULL,
    ville_editeur VARCHAR(255)
);

-- 3. Table: AUTEUR
CREATE TABLE IF NOT EXISTS AUTEUR (
    id_auteur SERIAL PRIMARY KEY,
    nom_auteur VARCHAR(255) UNIQUE NOT NULL,
    type_auteur VARCHAR(100) DEFAULT 'Auteur Principal'
);

-- 4. Table: MATIERE
CREATE TABLE IF NOT EXISTS MATIERE (
    id_matiere SERIAL PRIMARY KEY,
    libelle_matiere VARCHAR(255) UNIQUE NOT NULL
);

-- 5. Table: NOTICE (Updated: code_biblio added here)
CREATE TABLE IF NOT EXISTS NOTICE (
    id_notice SERIAL PRIMARY KEY,
    titre TEXT NOT NULL,
    annee INT,
    nb_pages INT,
    niveau_biblio VARCHAR(100),
    code_biblio VARCHAR(10) NOT NULL,    -- Moved from Exemplaire to Notice
    code_langue VARCHAR(10) REFERENCES LANGUE(code_langue) ON DELETE SET NULL,
    id_editeur INT REFERENCES EDITEUR(id_editeur) ON DELETE SET NULL,
    id_matiere INT REFERENCES MATIERE(id_matiere) ON DELETE SET NULL
);

-- Many-to-Many Bridge Table (Relationship: REDIGER)
CREATE TABLE IF NOT EXISTS REDIGER (
    id_notice INT REFERENCES NOTICE(id_notice) ON DELETE CASCADE,
    id_auteur INT REFERENCES AUTEUR(id_auteur) ON DELETE CASCADE,
    PRIMARY KEY (id_notice, id_auteur)
);

-- 6. Table: EXEMPLAIRE (Updated: Only tracking the copy specific items)
CREATE TABLE IF NOT EXISTS EXEMPLAIRE (
    id_exemplaire SERIAL PRIMARY KEY,
    inventaire VARCHAR(100) UNIQUE NOT NULL, -- Named 'inventaire' to match your prompt exactly
    cote VARCHAR(100) NOT NULL,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    id_notice INT NOT NULL REFERENCES NOTICE(id_notice) ON DELETE CASCADE
);

COMMIT;