"""
KrishiMitra RAG Retriever v3
============================
Uses native chromadb + Ollama directly — no LangChain wrapper.
This avoids the LangChain deprecation chain and the 0-vector bug.

Key features:
- Cosine similarity (correct for semantic search)
- Hindi query augmentation: appends English equivalents before embedding
  so "सरसों माहू" correctly retrieves mustard_icar.txt
- Lazy singleton: collection loaded once per process
"""

from __future__ import annotations
import json
import logging
import re
import urllib.request
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

CHROMA_DIR  = Path(__file__).parent.parent / "chroma_db"
COLLECTION  = "krishimitra_kb"
EMBED_MODEL = "nomic-embed-text"
OLLAMA_URL  = "http://localhost:11434"

_client     = None
_collection = None

# ── Hindi → English keyword expansion ────────────────────────────────────────
_HI_EN: dict = {
    "गेहूँ": "wheat", "गेहू": "wheat", "गेहुं": "wheat",
    "धान": "rice paddy", "चावल": "rice",
    "मक्का": "maize corn", "ज्वार": "jowar sorghum",
    "बाजरा": "bajra pearl millet",
    "सरसों": "mustard rapeseed",
    "कपास": "cotton", "गन्ना": "sugarcane",
    "सोयाबीन": "soybean",
    "मूँगफली": "groundnut peanut",
    "चना": "chickpea gram",
    "अरहर": "pigeonpea arhar tur",
    "मूँग": "moong green gram",
    "उड़द": "urad black gram",
    "हल्दी": "turmeric", "अदरक": "ginger",
    "लहसुन": "garlic", "प्याज": "onion",
    "आलू": "potato", "टमाटर": "tomato",
    "बैंगन": "brinjal eggplant",
    "मिर्च": "chilli pepper",
    "आम": "mango", "केला": "banana",
    "अनार": "pomegranate",
    "धनिया": "coriander",
    # Pests / diseases
    "माहू": "aphid",
    "सुंडी": "caterpillar larva worm",
    "तना छेदक": "stem borer",
    "सफेद मक्खी": "whitefly",
    "थ्रिप्स": "thrips",
    "दीमक": "termite",
    "झुलसा": "blight",
    "फफूंदी": "fungal disease mold",
    "जड़ सड़न": "root rot",
    "पीलापन": "yellowing chlorosis",
    "रोग": "disease",
    "कीट": "pest insect",
    "कीटनाशक": "pesticide insecticide",
    "दवाई": "pesticide treatment",
    "नीम": "neem",
    # Farming
    "सिंचाई": "irrigation water",
    "बुवाई": "sowing planting",
    "खाद": "fertilizer manure",
    "उर्वरक": "fertilizer",
    "मिट्टी": "soil",
    "उपज": "yield",
    "कटाई": "harvest",
    "बीज": "seed",
    "फसल": "crop",
    # Weather / schemes
    "बारिश": "rain rainfall",
    "मौसम": "weather season",
    "तापमान": "temperature",
    "नमी": "moisture humidity",
    "योजना": "scheme",
    "सब्सिडी": "subsidy",
    "बीमा": "insurance",
    "किसान": "farmer",
    "मंडी": "mandi market",
    "एमएसपी": "msp minimum support price",
}


def _augment(query: str) -> str:
    """Append English equivalents for Hindi terms found in query."""
    if not re.search(r"[\u0900-\u097F]", query):
        return query   # no Devanagari — return as-is
    extras = [eng for hi, eng in _HI_EN.items() if hi in query]
    if extras:
        return query + " " + " ".join(extras)
    return query


def _embed(text: str) -> list:
    """Get embedding vector for a single text via Ollama."""
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())["embedding"]


def _get_collection():
    global _client, _collection
    if _collection is None:
        try:
            import chromadb
            _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            _collection = _client.get_collection(name=COLLECTION)
            count = _collection.count()
            logger.info("ChromaDB ready — %d vectors in '%s'", count, COLLECTION)
        except Exception as exc:
            logger.error("ChromaDB load failed: %s", exc)
            _collection = None
    return _collection


def retrieve(query: str, k: int = 4, category: Optional[str] = None) -> List[str]:
    """
    Return top-k relevant text chunks.
    query can be Hindi, English, or Hinglish.
    """
    col = _get_collection()
    if col is None:
        return []
    try:
        aug = _augment(query)
        vec = _embed(aug)
        kwargs: dict = {"query_embeddings": [vec], "n_results": k, "include": ["documents"]}
        if category:
            kwargs["where"] = {"category": category}
        res = col.query(**kwargs)
        return res["documents"][0] if res["documents"] else []
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        return []


def retrieve_with_sources(query: str, k: int = 4) -> List[dict]:
    """Return top-k chunks with source metadata and cosine similarity score."""
    col = _get_collection()
    if col is None:
        return []
    try:
        aug = _augment(query)
        vec = _embed(aug)
        res = col.query(
            query_embeddings=[vec],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for doc, meta, dist in zip(
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):
            output.append({
                "text":        doc,
                "source_file": meta.get("source_file", "unknown"),
                "category":    meta.get("category", "general"),
                "score":       round(1 - dist, 3),   # cosine distance → similarity
            })
        return output
    except Exception as exc:
        logger.error("Retrieval with sources failed: %s", exc)
        return []


def is_available() -> bool:
    col = _get_collection()
    return col is not None and col.count() > 0
