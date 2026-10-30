import json
import re
import sys
import unicodedata
import requests
import psycopg2
from sentence_transformers import SentenceTransformer
from embed_notices import DB_CONFIG, MODEL_NAME
from search_notices import search

OLLAMA_URL = "http://localhost:11434/api/generate"
LLM = "qwen3:4b"

SYSTEM_PROMPT = (
    "You are a university library assistant. "
    "Use ONLY the catalog records provided. Never invent a book, author, year or page count. "
    "Answer in the same language as the question (French, Arabic or English). "
    "Write one or two short sentences, never a list: the records are displayed separately. "
    "If the question asks about a topic, say briefly what the records cover and cite the record numbers like [1], [4]. "
    "If the question asks about one fact (pages, year, author), give the value and name the book. "
    "If the records cannot answer it (for example 'the first book', since the catalog has no order), say so. "
    "Do not explain your reasoning. Stop after the answer."
)


def normalize(text):
    text = unicodedata.normalize("NFKD", (text or "").casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"[\W_]+", "", text)


def dedupe(records):
    seen, unique = set(), []
    for r in records:
        key = (normalize(r["titre"])[:25], r["annee"])
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def format_record(i, r):
    fields = [
        f"[{i}] Title: {r['titre']}",
        f"Author(s): {r['auteurs'] or 'unknown'}",
        f"Subject: {r['matiere'] or 'unknown'}",
        f"Year: {r['annee'] or 'unknown'}",
        f"Pages: {r['nb_pages'] or 'unknown'}",
        f"Library: {r['code_biblio']}",
    ]
    return " | ".join(fields)


def build_messages(question, records):
    context = "\n".join(format_record(i, r) for i, r in enumerate(records, 1))
    user = f"Catalog records:\n{context}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def to_raw_prompt(messages, opener=""):
    parts = []
    for m in messages:
        parts.append(f"<|im_start|>{m['role']}\n{m['content']}<|im_end|>\n")
    parts.append("<|im_start|>assistant\n<think>\n\n</think>\n\n" + opener)
    return "".join(parts)


def fallback_list(records):
    lines = [
        f"[{i}] {r['titre']} - {r['auteurs'] or 'unknown'} ({r['annee'] or 'n/a'})"
        for i, r in enumerate(records, 1)
    ]
    return "(The model did not finish; here are the matching catalog records.)\n" + "\n".join(lines)


def ask_llm(messages, opener="", records=None):
    payload = {
        "model": LLM,
        "prompt": to_raw_prompt(messages, opener),
        "raw": True,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "repeat_penalty": 1.2,
            "num_ctx": 2048,
            "num_predict": 160,
            "stop": ["<|im_end|>"],
        },
    }
    text = opener
    cut_off = False
    print("Generating...", flush=True)
    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            text += chunk.get("response", "")
            if chunk.get("done_reason") == "length":
                cut_off = True
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
        cut_off = cut_off and not text.strip()
    final = text.strip()
    if cut_off and records:
        final = fallback_list(records)
    print(final)
    return final


ENGLISH_HINTS = {"the", "of", "what", "which", "how", "many",
                 "about", "book", "books", "is", "are", "any", "history"}


def pick_opener(question):
    if any("\u0600" <= c <= "\u06ff" for c in question):
        return "\u0627\u0633\u062a\u0646\u0627\u062f\u064b\u0627 \u0625\u0644\u0649 \u0627\u0644\u0633\u062c\u0644\u0627\u062a \u0627\u0644\u0645\u062a\u0648\u0641\u0631\u0629\u060c "
    words = set(question.lower().replace("?", " ").split())
    if words & ENGLISH_HINTS:
        return "Based on the catalog records, "
    return "D'apr\u00e8s les notices du catalogue, "


def main():
    question = " ".join(sys.argv[1:])
    model = SentenceTransformer(MODEL_NAME)
    conn = psycopg2.connect(**DB_CONFIG)
    records = dedupe(search(question, model, conn))
    conn.close()

    print("Retrieved records:")
    for i, r in enumerate(records, 1):
        print(format_record(i, r))
    print("\nAnswer:")
    ask_llm(build_messages(question, records), pick_opener(question), records)


if __name__ == "__main__":
    main()
