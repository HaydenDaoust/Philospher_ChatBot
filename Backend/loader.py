"""
One-time script: fetch the Nicomachean Ethics from the internet,
extract only the specified chapters, chunk, embed, and load into ChromaDB.

Selected chapters:
  Book I   — 1, 2, 7, 10          (eudaimonia)
  Book II  — 1, 2, 6, 9           (doctrine_of_mean)
  Book III — 6–12                 (doctrine_of_mean)
  Book VI  — 5, 7, 12, 13        (phronesis)
  Book X   — 9                    (habit_and_practice)

Run once before starting the app:
    python backend/loader.py

Re-run only if you change the chapter selection or chunking parameters.
"""

import os
import re
import sys
import urllib.request

import chromadb
from chromadb.utils import embedding_functions

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SOURCE_URL = "http://classics.mit.edu/Aristotle/nicomachaen.mb.txt"
DB_PATH    = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

COLLECTION_NAME = "aristotle"
EMBED_MODEL     = "all-MiniLM-L6-v2"
CHUNK_WORDS     = 400
OVERLAP_WORDS   = 60

# ---------------------------------------------------------------------------
# Chapter selection  →  (chapter list, topic label)
# ---------------------------------------------------------------------------

CHAPTER_SELECTION: dict[str, tuple[list[int], str]] = {
    "I":   ([1, 2, 7, 10],      "eudaimonia"),
    "II":  ([1, 2, 6, 9],       "doctrine_of_mean"),
    "III": (list(range(6, 13)), "doctrine_of_mean"),  # chapters 6–12
    "VI":  ([5, 7, 12, 13],     "phronesis"),
    "X":   ([9],                "habit_and_practice"),
}

# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_text(url: str) -> str:
    """Download the source text from the internet."""
    print(f"Fetching text from {url} …")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_bytes = resp.read()
    except Exception as exc:
        print(f"ERROR: Could not fetch text: {exc}", file=sys.stderr)
        sys.exit(1)
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return raw_bytes.decode("latin-1")


# ---------------------------------------------------------------------------
# Parse books and chapters
# ---------------------------------------------------------------------------

def _parse_chapters(text: str) -> dict[str, dict[int, str]]:
    """
    Parse the MIT plain-text Nicomachean Ethics into:
        { "I": {1: "chapter text", 2: "chapter text", ...}, "II": {...}, ... }

    The MIT Internet Classics Archive text uses the format:
        BOOK I\\n\\n1 \\n\\nEvery art and every inquiry...
    i.e. "BOOK <ROMAN>" on its own line (all-caps), then chapter numbers as
    "<digits> " (number + trailing space) on a line surrounded by blank lines.
    """
    # Normalise line endings and collapse runs of 3+ newlines to 2
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Book header: "BOOK" + roman numerals on a line by themselves (all-caps in MIT text)
    book_re = re.compile(r"^BOOK\s+([IVXLCDM]+)\s*$", re.MULTILINE)

    # Chapter marker: a bare number (with optional trailing space) on a line
    # surrounded by blank lines — e.g. "\n\n7 \n\n" or "\n\n7\n\n"
    chapter_re = re.compile(r"\n\n(\d{1,2}) ?\n\n")

    # Locate all book start positions
    book_spans: list[tuple[int, str]] = [
        (m.start(), m.group(1).upper()) for m in book_re.finditer(text)
    ]
    if not book_spans:
        print("ERROR: No book headers found — the text format may have changed.",
              file=sys.stderr)
        sys.exit(1)

    book_spans.append((len(text), "__END__"))  # sentinel

    result: dict[str, dict[int, str]] = {}

    for idx, (book_start, book_name) in enumerate(book_spans[:-1]):
        book_end   = book_spans[idx + 1][0]
        book_body  = text[book_start:book_end]

        # Locate all chapter markers within this book section
        chapter_spans: list[tuple[int, int]] = [
            (m.start(), int(m.group(1))) for m in chapter_re.finditer(book_body)
        ]
        chapter_spans.append((len(book_body), -1))  # sentinel

        result[book_name] = {}
        for cidx, (ch_start, ch_num) in enumerate(chapter_spans[:-1]):
            ch_end       = chapter_spans[cidx + 1][0]
            chapter_text = book_body[ch_start:ch_end].strip()
            result[book_name][ch_num] = chapter_text

    return result


# ---------------------------------------------------------------------------
# Extract selected chapters
# ---------------------------------------------------------------------------

def _extract_selected(
    parsed: dict[str, dict[int, str]]
) -> list[tuple[str, int, str, str]]:
    """
    Return list of (book_roman, chapter_num, text, topic) for the chapters
    listed in CHAPTER_SELECTION.
    """
    selected: list[tuple[str, int, str, str]] = []
    for book_roman, (chapters, topic) in CHAPTER_SELECTION.items():
        if book_roman not in parsed:
            print(f"WARNING: Book {book_roman} not found in parsed text.", file=sys.stderr)
            continue
        for ch in chapters:
            if ch not in parsed[book_roman]:
                print(f"WARNING: Book {book_roman}, Chapter {ch} not found.", file=sys.stderr)
                continue
            selected.append((book_roman, ch, parsed[book_roman][ch], topic))
    return selected


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _words(text: str) -> list[str]:
    return text.split()


def _chunk_text(text: str, chunk_words: int, overlap_words: int) -> list[str]:
    """Split text into overlapping word-count chunks."""
    words = _words(text)
    chunks: list[str] = []
    step  = chunk_words - overlap_words
    start = 0
    while start < len(words):
        end = start + chunk_words
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start += step
    return chunks


# ---------------------------------------------------------------------------
# Main loader
# ---------------------------------------------------------------------------

def load() -> None:
    raw  = _fetch_text(SOURCE_URL)
    text = re.sub(r"\r\n?", "\n", raw)
    text = re.sub(r"\n{3,}", "\n\n", text)
    print(f"Fetched {len(_words(text)):,} words total.")

    print("\nParsing books and chapters …")
    parsed = _parse_chapters(text)
    for book in sorted(parsed.keys()):
        chs = sorted(parsed[book].keys())
        print(f"  Book {book}: {len(chs)} chapters found ({min(chs)}–{max(chs)})")

    print("\nExtracting selected chapters …")
    selected = _extract_selected(parsed)
    if not selected:
        print("ERROR: No chapters were extracted. Aborting.", file=sys.stderr)
        sys.exit(1)
    for book, ch, body, topic in selected:
        print(f"  Book {book} Ch.{ch:>2}  ({topic}, {len(_words(body))} words)")

    # Build chunk + topic lists, prepending a header to each chapter so that
    # context is identifiable in retrieval results.
    all_chunks: list[str] = []
    all_topics: list[str] = []

    for book, ch, body, topic in selected:
        header        = f"[Nicomachean Ethics — Book {book}, Chapter {ch}]\n\n"
        chapter_chunks = _chunk_text(header + body, CHUNK_WORDS, OVERLAP_WORDS)
        all_chunks.extend(chapter_chunks)
        all_topics.extend([topic] * len(chapter_chunks))

    print(f"\nTotal chunks: {len(all_chunks)}")
    topic_counts: dict[str, int] = {}
    for t in all_topics:
        topic_counts[t] = topic_counts.get(t, 0) + 1
    for t, c in sorted(topic_counts.items()):
        print(f"  {t}: {c} chunks")

    print(f"\nLoading sentence-transformer model '{EMBED_MODEL}' …")
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )

    print(f"Connecting to ChromaDB at {DB_PATH} …")
    client = chromadb.PersistentClient(path=DB_PATH)

    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Deleted existing '{COLLECTION_NAME}' collection.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch_chunks = all_chunks[i : i + batch_size]
        batch_topics = all_topics[i : i + batch_size]
        batch_ids    = [str(j) for j in range(i, i + len(batch_chunks))]
        batch_meta   = [
            {"topic": t, "chunk_id": i + k}
            for k, t in enumerate(batch_topics)
        ]
        collection.add(
            documents=batch_chunks,
            metadatas=batch_meta,
            ids=batch_ids,
        )
        print(f"  Inserted chunks {i}–{i + len(batch_chunks) - 1}")

    print(f"\nDone. {len(all_chunks)} chunks loaded into collection '{COLLECTION_NAME}'.")

    # Sanity check
    print("\nSanity check — querying 'what is the highest good?' (eudaimonia) …")
    results = collection.query(
        query_texts=["what is the highest good?"],
        n_results=3,
        where={"topic": "eudaimonia"},
        include=["documents"],
    )
    for idx, doc in enumerate(results["documents"][0]):
        preview = " ".join(doc.split()[:20])
        print(f"  [{idx + 1}] {preview} …")


if __name__ == "__main__":
    load()
