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
import uuid
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rag.kb_fingerprint import knowledge_fingerprint
else:
    from .kb_fingerprint import knowledge_fingerprint

ROOT       = Path(__file__).parent.parent
KB_DIR     = ROOT / "knowledge_base"
CHROMA_DIR = ROOT / "chroma_db"
COLLECTION = "krishimitra_kb"
FINGERPRINT_FILE = CHROMA_DIR / "kb_fingerprint.txt"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

# Chunk settings
CHUNK_SIZE    = 800   # characters (~600 words)
CHUNK_OVERLAP = 120

_CROP_TERMS = {
    "rice": ("rice", "paddy", "धान", "चावल"),
    "wheat": ("wheat", "गेहूँ", "गेहू", "गेहुं"),
    "maize": ("maize", "corn", "मक्का"),
    "barley": ("barley", "जौ"),
    "jowar": ("jowar", "sorghum", "ज्वार"),
    "bajra": ("bajra", "pearl millet", "बाजरा"),
    "ragi": ("ragi", "finger millet", "रागी"),
    "mustard": ("mustard", "rapeseed", "सरसों"),
    "soybean": ("soybean", "सोयाबीन"),
    "groundnut": ("groundnut", "peanut", "मूंगफली", "मूँगफली"),
    "sunflower": ("sunflower", "सूरजमुखी"),
    "cotton": ("cotton", "कपास"),
    "sugarcane": ("sugarcane", "गन्ना"),
    "gram": ("gram", "chickpea", "चना"),
    "arhar": ("arhar", "pigeonpea", "tur", "अरहर", "तूर"),
    "moong": ("moong", "green gram", "मूंग", "मूँग"),
    "urad": ("urad", "black gram", "उड़द"),
    "lentil": ("lentil", "masoor", "मसूर"),
    "tomato": ("tomato", "टमाटर"),
    "potato": ("potato", "आलू"),
    "onion": ("onion", "प्याज"),
    "brinjal": ("brinjal", "eggplant", "बैंगन"),
    "chilli": ("chilli", "chili", "pepper", "मिर्च"),
    "okra": ("okra", "bhindi", "भिंडी"),
    "cucumber": ("cucumber", "khira", "खीरा"),
    "french_bean": ("french bean", "green bean", "फ्रेंच बीन"),
    "broccoli": ("broccoli", "ब्रोकली"),
    "turnip": ("turnip", "shaljam", "शलजम"),
    "leafy_greens": ("amaranth greens", "bathua", "mustard greens", "fenugreek greens", "बथुआ", "मेथी"),
    "tapioca": ("tapioca", "cassava", "कसावा"),
    "yam": ("elephant foot yam", "greater yam", "suran", "सूरन"),
    "pear": ("pear", "nashpati", "नाशपाती"),
    "citrus": ("lemon", "acid lime", "kinnow", "mandarin", "sweet lime", "mosambi", "किन्नू", "मौसम्बी"),
    "ber": ("ber", "indian jujube", "बेर"),
    "bael": ("bael", "bel fruit", "बेल"),
    "underutilized_fruit": ("phalsa", "karonda", "passion fruit", "rambutan", "mangosteen", "करौंदा", "फालसा"),
    "saffron": ("saffron", "kesar", "केसर"),
    "vanilla": ("vanilla", "वेनिला"),
    "mango": ("mango", "आम"),
    "banana": ("banana", "केला"),
    "pomegranate": ("pomegranate", "अनार"),
    "turmeric": ("turmeric", "हल्दी"),
    "ginger": ("ginger", "अदरक"),
    "garlic": ("garlic", "लहसुन"),
}

_TOPIC_TERMS = {
    "disease": ("disease", "blast", "blight", "rust", "rot", "wilt", "smut", "रोग", "झुलसा", "रतुआ"),
    "pest": ("pest", "aphid", "borer", "whitefly", "thrips", "weevil", "mite", "कीट", "माहू", "सुंडी"),
    "irrigation": ("irrigation", "drip", "sprinkler", "rainfall", "water", "सिंचाई", "पानी"),
    "fertilizer": ("fertilizer", "urea", "dap", "npk", "nutrient", "खाद", "उर्वरक"),
    "seed": ("seed", "variety", "sowing", "planting", "बीज", "बुवाई"),
    "market": ("msp", "mandi", "market", "price", "मंडी", "भाव", "एमएसपी"),
    "scheme": ("scheme", "subsidy", "loan", "insurance", "yojana", "योजना", "सब्सिडी", "बीमा"),
    "soil": ("soil", "ph", "organic carbon", "salinity", "मिट्टी"),
    "weather": ("weather", "rain", "temperature", "humidity", "मौसम", "बारिश", "तापमान"),
    "storage": ("storage", "warehouse", "cold storage", "fumigation", "भंडारण"),
    "protected_cultivation": ("polyhouse", "greenhouse", "shade net", "cucumber", "protected cultivation"),
}


def _normalize_spaces(text: str) -> str:
    """Keep paragraph breaks, but remove repeated whitespace inside lines."""
    lines = [" ".join(line.split()) for line in text.splitlines()]
    compact = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", compact).strip()


def _detect_heading(section: str) -> tuple[str, str]:
    """Return (heading, body) for long-section splitting."""
    lines = section.splitlines()
    first_idx = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first_idx is None:
        return "", section

    first = lines[first_idx].strip()
    is_heading = (
        first.startswith("#")
        or first.endswith(":")
        or bool(re.fullmatch(r"[A-Z][A-Z\s/()\-]{3,}", first))
    )
    if is_heading and len(first) <= 140:
        body = "\n".join(lines[first_idx + 1:]).strip()
        return first, body
    return "", section


def _safe_windows(text: str, limit: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split long text with sentence/paragraph-aware boundaries."""
    text = _normalize_spaces(text)
    if len(text) <= limit:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            breakpoints = [
                text.rfind("\n\n", start, end),
                text.rfind(". ", start, end),
                text.rfind("। ", start, end),
                text.rfind("; ", start, end),
                text.rfind(", ", start, end),
            ]
            split_at = max(breakpoints)
            if split_at > start + int(limit * 0.55):
                end = split_at + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break

        next_start = max(end - overlap, start + 1)
        while next_start < len(text) and text[next_start].isspace():
            next_start += 1
        start = next_start

    return chunks


def _split_section(section: str) -> list[str]:
    section = _normalize_spaces(section)
    if len(section) <= CHUNK_SIZE:
        return [section] if section else []

    heading, body = _detect_heading(section)
    base = body or section
    parts = _safe_windows(base)
    if not heading:
        return parts

    headed = []
    for part in parts:
        candidate = f"{heading}\n\n{part}".strip()
        if len(candidate) <= CHUNK_SIZE:
            headed.append(candidate)
        else:
            headed.extend(_safe_windows(candidate))
    return headed


def _metadata_for_chunk(text: str, source_file: str, category: str, chunk_index: int) -> dict:
    lower = text.lower()
    crops = [
        crop
        for crop, terms in _CROP_TERMS.items()
        if any(term.lower() in lower for term in terms)
    ]
    topics = [
        topic
        for topic, terms in _TOPIC_TERMS.items()
        if any(term.lower() in lower for term in terms)
    ]
    language = "hi-en" if re.search(r"[\u0900-\u097F]", text) and re.search(r"[A-Za-z]", text) else (
        "hi" if re.search(r"[\u0900-\u097F]", text) else "en"
    )
    return {
        "source_file": source_file,
        "source_stem": Path(source_file).stem,
        "category": category,
        "chunk_index": chunk_index,
        "crops": "|".join(sorted(crops)) if crops else "general",
        "topics": "|".join(sorted(topics)) if topics else category,
        "language": language,
        "char_count": len(text),
    }


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

    sections = section_pattern.split(_normalize_spaces(text))
    current = ""

    for section in sections:
        for part in _split_section(section):
            if len(current) + len(part) + 2 <= CHUNK_SIZE:
                current = (current + "\n\n" + part).strip()
                continue

            if current:
                chunks.append(current)
                tail = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                candidate = (tail + "\n\n" + part).strip()
                current = candidate if len(candidate) <= CHUNK_SIZE else part
            else:
                current = part

    if current:
        chunks.append(current)

    return [
        {
            "text": c,
            **_metadata_for_chunk(c, source_file, category, idx),
        }
        for idx, c in enumerate(chunks)
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

    build_collection_name = f"krishimitra_build_{uuid.uuid4().hex[:12]}"
    collection = client.create_collection(
        name=build_collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"✅  Created temporary collection '{build_collection_name}'")

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
            client.delete_collection(build_collection_name)
            print("  Existing RAG collection was preserved")
            return 1

        ids       = [f"chunk_{start + i}" for i in range(len(batch))]
        metadatas = [{k: v for k, v in c.items() if k != "text"} for c in batch]

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
    if final_count != total:
        client.delete_collection(build_collection_name)
        print(f"❌  Incomplete build: expected {total} vectors, stored {final_count}")
        print("  Existing RAG collection was preserved")
        return 1

    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection.modify(name=COLLECTION)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    fingerprint = knowledge_fingerprint(KB_DIR)
    temporary_marker = FINGERPRINT_FILE.with_suffix(".tmp")
    temporary_marker.write_text(fingerprint + "\n", encoding="ascii")
    temporary_marker.replace(FINGERPRINT_FILE)

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
