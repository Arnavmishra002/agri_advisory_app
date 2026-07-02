#!/usr/bin/env python3
"""
KrishiMitra — RAG Knowledge Base Ingestion v2
=============================================
Reads all .txt / .pdf files from knowledge_base/,
chunks them, embeds with nomic-embed-text via Ollama,
stores in ChromaDB using cosine similarity.

Run once after knowledge base generation:
    source ../phase1_env/bin/activate
    python3 rag/ingest.py

Re-run whenever new documents are added.
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT       = Path(__file__).parent.parent
KB_DIR     = ROOT / "knowledge_base"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION = "krishimitra_kb"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

# Chunk settings
CHUNK_SIZE    = 800   # characters (~600 words)
CHUNK_OVERLAP = 120


def embed(texts: list[str]) -> list[list[float]]:
    """Call Ollama nomic-embed-text to get embeddings for a batch of texts."""
    vectors = []
    for text in texts:
        payload = json.dumps({
            "model": EMBED_MODEL,
            "prompt": text,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            vectors.append(data["embedding"])
    return vectors


def chunk_text(text: str, source_file: str, category: str) -> list[dict]:
    """
    Split text into overlapping chunks, keeping section headings together
    with their content so pest/disease sections aren't split mid-way.
    """
    chunks = []

    # Split on major section headings (ALL CAPS lines or lines ending with :)
    # This keeps "MAJOR PESTS\nAphids..." together in one chunk
    section_pattern = re.compile(
        r"\n(?=[A-Z][A-Z\s/()]{3,}[\n:])",   # ALL-CAPS heading
    )

    sections = section_pattern.split(text)
    current = ""

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(current) + len(section) + 2 <= CHUNK_SIZE:
            current = (current + "\n\n" + section).strip()
        else:
            if current:
                chunks.append(current)
                # Overlap: carry last CHUNK_OVERLAP chars
                tail = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                current = (tail + "\n\n" + section).strip()
            else:
                # Section itself is too long — split at paragraph boundaries
                paras = [p.strip() for p in section.split("\n\n") if p.strip()]
                sub = ""
                for para in paras:
                    if len(sub) + len(para) + 2 <= CHUNK_SIZE:
                        sub = (sub + "\n\n" + para).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        sub = para
                if sub:
                    current = sub

    if current:
        chunks.append(current)

    return [
        {
            "text":        c,
            "source_file": source_file,
            "category":    category,
        }
        for c in chunks
        if len(c.strip()) > 50
    ]


def main():
    print("\n" + "═" * 55)
    print("  KrishiMitra RAG — Knowledge Base Ingestion v2")
    print("═" * 55 + "\n")

    # ── Check dependencies ────────────────────────────────────────────────────
    try:
        import chromadb
    except ImportError:
        print("❌  chromadb not installed. Run: pip install chromadb")
        sys.exit(1)

    # ── Check Ollama ──────────────────────────────────────────────────────────
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            models = [m["name"] for m in json.loads(resp.read()).get("models", [])]
        if not any(EMBED_MODEL in m for m in models):
            print(f"❌  {EMBED_MODEL} not found. Run: ollama pull {EMBED_MODEL}")
            sys.exit(1)
        print(f"✅  Ollama ready — {EMBED_MODEL} available")
    except Exception as e:
        print(f"❌  Ollama not running: {e}")
        print("   Start it with: ollama serve")
        sys.exit(1)

    # ── Load and chunk documents ──────────────────────────────────────────────
    txt_files = sorted(KB_DIR.rglob("*.txt"))
    pdf_files = sorted(KB_DIR.rglob("*.pdf"))
    print(f"📚  Found {len(txt_files)} text files + {len(pdf_files)} PDF files")

    all_chunks: list[dict] = []

    for path in txt_files:
        try:
            text     = path.read_text(encoding="utf-8")
            category = path.parent.name
            chunks   = chunk_text(text, path.name, category)
            all_chunks.extend(chunks)
        except Exception as e:
            print(f"  ⚠  Failed to load {path.name}: {e}")

    for path in pdf_files:
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            text   = "\n\n".join(p.extract_text() or "" for p in reader.pages)
            category = path.parent.name
            chunks   = chunk_text(text, path.name, category)
            all_chunks.extend(chunks)
            print(f"  📄  PDF {path.name}: {len(reader.pages)} pages → {len(chunks)} chunks")
        except ImportError:
            print("  ⚠  pypdf not installed — skipping PDFs")
            break
        except Exception as e:
            print(f"  ⚠  PDF failed {path.name}: {e}")

    print(f"✂   Total chunks: {len(all_chunks)}")

    if not all_chunks:
        print("❌  No chunks created. Check knowledge_base/ directory.")
        sys.exit(1)

    # ── Create ChromaDB collection (cosine similarity) ────────────────────────
    import chromadb as cdb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = cdb.PersistentClient(path=str(CHROMA_DIR))

    # Delete old collection if exists
    try:
        client.delete_collection(COLLECTION)
        print(f"🗑   Old collection '{COLLECTION}' deleted")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"✅  Created collection '{COLLECTION}' with cosine similarity")

    # ── Embed and store in batches ────────────────────────────────────────────
    print(f"\n🔢  Embedding {len(all_chunks)} chunks with {EMBED_MODEL}...")
    BATCH = 16
    t0    = time.time()
    total = len(all_chunks)

    for start in range(0, total, BATCH):
        batch  = all_chunks[start:start + BATCH]
        texts  = [c["text"] for c in batch]

        try:
            vectors = embed(texts)
        except Exception as e:
            print(f"  ❌  Embed batch {start}-{start+len(batch)} failed: {e}")
            continue

        ids       = [f"chunk_{start + i}" for i in range(len(batch))]
        metadatas = [{"source_file": c["source_file"], "category": c["category"]} for c in batch]

        collection.add(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metadatas,
        )

        done    = min(start + BATCH, total)
        elapsed = time.time() - t0
        eta     = (elapsed / done) * (total - done) if done > 0 else 0
        print(f"  [{done:3d}/{total}]  {round(elapsed, 1)}s elapsed, ~{round(eta)}s remaining")

    # ── Verify ────────────────────────────────────────────────────────────────
    final_count = collection.count()
    total_time  = round(time.time() - t0, 1)
    print(f"\n✅  Done — {final_count} vectors stored in {total_time}s")
    print(f"📦  Chroma DB: {CHROMA_DIR}")

    # ── Quick test ────────────────────────────────────────────────────────────
    print("\n🔍  Testing: 'mustard aphid control Dimethoate'")
    test_vec = embed(["mustard aphid control Dimethoate"])[0]
    results  = collection.query(
        query_embeddings=[test_vec],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )
    for i, (doc, meta, dist) in enumerate(zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ), 1):
        score = round(1 - dist, 3)   # cosine: distance → similarity
        print(f"  [{score}] {meta['source_file']}  /  {doc[:80]}...")

    print("\n🔍  Testing Hindi: 'सरसों माहू नियंत्रण mustard aphid'")
    test_vec2 = embed(["सरसों माहू नियंत्रण mustard aphid"])[0]
    results2  = collection.query(
        query_embeddings=[test_vec2],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )
    for i, (doc, meta, dist) in enumerate(zip(
        results2["documents"][0],
        results2["metadatas"][0],
        results2["distances"][0],
    ), 1):
        score = round(1 - dist, 3)
        print(f"  [{score}] {meta['source_file']}  /  {doc[:80]}...")

    print("\n" + "═" * 55)
    print("  Ingestion complete. Start the server:")
    print("  uvicorn main:app --port 8001 --reload")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    main()
