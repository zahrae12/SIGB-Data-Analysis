import os
import psycopg2
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

MODEL_NAME = "intfloat/multilingual-e5-small"
BATCH = 64
PLACEHOLDERS = {"inconnu", "inconnue",
                "anonyme", "non spécifiée", "non specifiee"}

SELECT_TODO = """
    SELECT n.id_notice, n.titre, m.libelle_matiere,
           string_agg(a.nom_auteur, ' ; ') AS auteurs
    FROM notice n
    LEFT JOIN matiere m ON m.id_matiere = n.id_matiere
    LEFT JOIN rediger r ON r.id_notice = n.id_notice
    LEFT JOIN auteur a ON a.id_auteur = r.id_auteur
    WHERE n.embedding IS NULL
    GROUP BY n.id_notice, n.titre, m.libelle_matiere
    ORDER BY n.id_notice
"""


def keep(value):
    if value is None:
        return None
    value = str(value).strip()
    if not value or value.casefold() in PLACEHOLDERS:
        return None
    return value


def build_text(titre, matiere, auteurs):
    parts = [keep(titre)]
    if keep(matiere):
        parts.append(f"Sujet: {keep(matiere)}")
    if keep(auteurs):
        parts.append(f"Auteur: {keep(auteurs)}")
    return "passage: " + " | ".join(p for p in parts if p)


def to_vec(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def main():
    model = SentenceTransformer(MODEL_NAME)
    conn = psycopg2.connect(**DB_CONFIG)

    with conn, conn.cursor() as cur:
        cur.execute(SELECT_TODO)
        rows = cur.fetchall()
    print(f"{len(rows)} notices to embed")

    for i in range(0, len(rows), BATCH):
        chunk = rows[i: i + BATCH]
        texts = [build_text(r[1], r[2], r[3]) for r in chunk]
        vecs = model.encode(texts, normalize_embeddings=True)
        data = [(to_vec(v), r[0]) for v, r in zip(vecs, chunk)]
        with conn, conn.cursor() as cur:
            cur.executemany(
                "UPDATE notice SET embedding = %s::vector WHERE id_notice = %s", data
            )
        print(f"{min(i + BATCH, len(rows))}/{len(rows)}")

    conn.close()


if __name__ == "__main__":
    main()
