import pandas as pd
import psycopg2
from dotenv import load_dotenv
import os

# Charger les variables depuis le fichier .env
load_dotenv()

# Configuration sécurisée
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT")
}


def clean_val(val):
    """Nettoie proprement les espaces et convertit les valeurs manquantes en NULL"""
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']:
        return None
    return str(val).strip()


def run_migration():
    print("Chargement des fichiers Excel...")
    bua = pd.read_excel("data/bua_cleaned.xlsx")
    buf = pd.read_excel("data/buf_cleaned.xlsx")

    # On ajoute une colonne pour garder la trace de la provenance originale si code_biblio est vide
    bua['source_camp'] = 'BUA'
    buf['source_camp'] = 'BUF'

    # Fusion complète des deux campus pour analyser les doublons de livres
    df_all = pd.concat([bua, buf], ignore_index=True)

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # ── 1. Remplissage des Tables de Référence (Lookups) ──

        print("Injection des référentiels (Langues, Éditeurs, Auteurs, Matières)...")

        # LANGUE
        unique_langues = {clean_val(x)
                          for x in df_all['langue'] if clean_val(x)}
        for lang in unique_langues:
            libelle = "Français" if lang == "fr" else "Arabe" if lang == "ar" else "Inconnu"
            cursor.execute(
                "INSERT INTO LANGUE (code_langue, libelle_langue) VALUES (%s, %s) ON CONFLICT (code_langue) DO NOTHING;", (lang, libelle))

        # EDITEUR
        editeur_map = {}
        for _, row in df_all.drop_duplicates(subset=['editeur']).iterrows():
            ed_name = clean_val(row['editeur'])
            lieu = clean_val(row['lieu'])
            if ed_name:
                cursor.execute(
                    "INSERT INTO EDITEUR (nom_editeur, ville_editeur) VALUES (%s, %s) ON CONFLICT (nom_editeur) DO UPDATE SET ville_editeur=EXCLUDED.ville_editeur RETURNING id_editeur;",
                    (ed_name, lieu)
                )
                editeur_map[ed_name] = cursor.fetchone()[0]

        # AUTEUR
        author_map = {}
        unique_auteurs = {clean_val(x)
                          for x in df_all['auteur'] if clean_val(x)}
        for aut in unique_auteurs:
            cursor.execute(
                "INSERT INTO AUTEUR (nom_auteur) VALUES (%s) ON CONFLICT (nom_auteur) DO UPDATE SET nom_auteur = EXCLUDED.nom_auteur RETURNING id_auteur;",
                (aut,)
            )
            author_map[aut] = cursor.fetchone()[0]

        # MATIERE
        matiere_map = {}
        unique_matieres = {clean_val(x)
                           for x in df_all['matiere'] if clean_val(x)}
        for mat in unique_matieres:
            cursor.execute(
                "INSERT INTO MATIERE (libelle_matiere) VALUES (%s) ON CONFLICT (libelle_matiere) DO UPDATE SET libelle_matiere = EXCLUDED.libelle_matiere RETURNING id_matiere;",
                (mat,)
            )
            matiere_map[mat] = cursor.fetchone()[0]

        # ── 2. Gestion Unique des NOTICES et de leurs EXEMPLAIRES ──
        print(" Traitement des Notices uniques et liaison des exemplaires...")

        # Dictionnaire pour mémoriser l'ID de la notice générée pour chaque couple (titre complet, année)
        notice_identity_registry = {}

        for _, row in df_all.iterrows():
            titre = clean_val(row['titre'])
            if not titre:
                continue

            # Extraction propre des métadonnées numériques
            try:
                annee = int(float(row['annee'])) if pd.notna(
                    row['annee']) else None
            except ValueError:
                annee = None
            try:
                nb_pages = int(float(row['nb_pages'])) if pd.notna(
                    row['nb_pages']) else None
            except ValueError:
                nb_pages = None

            code_biblio = clean_val(row['code_biblio']) if clean_val(
                row['code_biblio']) else row['source_camp']

            # Création d'une clé d'identification textuelle insensible à la casse
            lookup_key = (titre.lower().strip(), annee)

            # Étape A : Si la notice de ce livre n'a pas encore été créée, on l'insère une SEULE fois
            if lookup_key not in notice_identity_registry:
                ed_csv = clean_val(row['editeur'])
                mat_csv = clean_val(row['matiere'])
                aut_csv = clean_val(row['auteur'])
                lang_csv = clean_val(row['langue'])

                id_editeur = editeur_map.get(ed_csv) if ed_csv else None
                id_matiere = matiere_map.get(mat_csv) if mat_csv else None
                id_auteur = author_map.get(aut_csv) if aut_csv else None

                cursor.execute("""
                    INSERT INTO NOTICE (titre, annee, nb_pages, code_biblio, code_langue, id_editeur, id_matiere)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id_notice;
                """, (titre, annee, nb_pages, code_biblio, lang_csv, id_editeur, id_matiere))

                generated_id = cursor.fetchone()[0]
                notice_identity_registry[lookup_key] = generated_id

                # Ajout de la relation Auteur-Livre (REDIGER)
                if id_auteur:
                    cursor.execute(
                        "INSERT INTO REDIGER (id_notice, id_auteur) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (generated_id, id_auteur))

            # Étape B : On récupère l'ID unique de la notice
            parent_notice_id = notice_identity_registry[lookup_key]

            # Étape C : On insère l'exemplaire physique spécifique
            inventaire = clean_val(row['inventaire'])
            cote = clean_val(row['cote'])

            if inventaire and cote:
                cursor.execute("""
                    INSERT INTO EXEMPLAIRE (inventaire, cote, id_notice)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (inventaire) DO NOTHING;
                """, (str(inventaire), cote, parent_notice_id))

        conn.commit()
        print("Migration terminée avec succès ! Les notices sont désormais uniques et dédoublonnées.")

    except Exception as e:
        conn.rollback()
        print(f"Erreur durant la transaction, retour à l'état initial : {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
