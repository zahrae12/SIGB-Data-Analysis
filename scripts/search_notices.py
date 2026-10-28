import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
from embed_notices import DB_CONFIG, MODEL_NAME, to_vec

TOP_K = 5

SEARCH_SQL = """
    SELECT n.id_notice, n.titre, m.libelle_matiere AS matiere, n.annee, n.code_biblio,
           (SELECT string_agg(a.nom_auteur, ' ; ')
            FROM rediger r JOIN auteur a ON a.id_auteur = r.id_auteur
            WHERE r.id_notice = n.id_notice) AS auteurs,
           1 - (n.embedding <=> %s::vector) AS score
    FROM notice n
    LEFT JOIN matiere m ON m.id_matiere = n.id_matiere
    WHERE n.embedding IS NOT NULL
    ORDER BY n.embedding <=> %s::vector
    LIMIT %s
"""


def search(question, model, conn, k=TOP_K):
    vec = model.encode(["query: " + question], normalize_embeddings=True)[0]
    v = to_vec(vec)
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(SEARCH_SQL, (v, v, k))
        return cur.fetchall()


if __name__ == "__main__":
    question = " ".join(sys.argv[1:])
    model = SentenceTransformer(MODEL_NAME)
    conn = psycopg2.connect(**DB_CONFIG)
    for r in search(question, model, conn):
        print(
            f"{r['score']:.3f} | {r['code_biblio']} | {r['titre']} | "
            f"{r['auteurs']} | {r['matiere']} | {r['annee']}"
        )
    conn.close()
