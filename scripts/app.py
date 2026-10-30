import psycopg2
import streamlit as st
from sentence_transformers import SentenceTransformer
from embed_notices import DB_CONFIG, MODEL_NAME
from search_notices import search
from answer_notices import dedupe, build_messages, ask_llm, pick_opener

st.set_page_config(page_title="SIGB Library Assistant", layout="wide")


@st.cache_resource
def load_model():
    return SentenceTransformer(MODEL_NAME)


st.title("SIGB library assistant")
st.caption(
    "RAG over the university library catalog: semantic search (pgvector) "
    "then a local LLM (Qwen3 via Ollama) that answers from the retrieved records only."
)

question = st.text_input(
    "Ask a question (French, Arabic or English)",
    placeholder="Quels livres parlent de l'histoire du Maroc ?",
)

if st.button("Ask") and question.strip():
    model = load_model()
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        records = dedupe(search(question, model, conn))
    finally:
        conn.close()

    left, right = st.columns([3, 2])
    with right:
        st.subheader("Retrieved records")
        st.dataframe(
            [
                {
                    "#": i,
                    "title": r["titre"],
                    "author": r["auteurs"],
                    "year": r["annee"],
                    "pages": r["nb_pages"],
                    "library": r["code_biblio"],
                    "score": round(float(r["score"]), 3),
                }
                for i, r in enumerate(records, 1)
            ],
            hide_index=True,
        )
    with left:
        st.subheader("Answer")
        with st.spinner("The model is writing the answer..."):
            answer = ask_llm(build_messages(
                question, records), pick_opener(question))
        st.markdown(answer.replace("\n", "  \n"))
