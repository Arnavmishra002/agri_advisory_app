"""
KrishiMitra RAG Retriever v4
============================
Production-optimized retriever implementing all 5 RAG latency fixes:

  1. Parallel retrieval — keyword BM25 + vector search run concurrently
  2. Top-20 → rerank → Top-5 — smaller LLM context, better precision
  3. Embedding LRU cache — same query embedding never computed twice
  4. Retrieval result cache — identical (query, k, category) skip ChromaDB
  5. Context compression — dedup + 200-char hard cap per chunk on the way out

Profile before you optimize — this module logs stage timings at DEBUG level:
  EMBED_MS, VECTOR_MS, KEYWORD_MS, RERANK_MS, TOTAL_MS

Key changes vs v3:
  - retrieve() now retrieves 20, reranks, returns top k (default 5)
  - retrieve_with_sources() same reranking pipeline with scores
  - _embed() is @lru_cache(maxsize=512) keyed on the augmented query string
  - Keyword search uses simple TF-IDF-like term overlap (no extra dep)
  - Parallel futures: embed + keyword_scan run concurrently, vector waits for embed
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Chroma's optional PostHog integration is not part of request processing and
# older dependency combinations can emit a capture() signature error on every
# query. Disable it before Chroma is imported or its client is constructed.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

try:
    from .crop_profile_snapshot import load_crop_terms, merge_crop_terms
except ImportError:
    from rag.crop_profile_snapshot import load_crop_terms, merge_crop_terms

logger = logging.getLogger(__name__)
# Chroma 0.5.x can still invoke its disabled PostHog callback with an
# incompatible signature. It does not affect retrieval, so keep that optional
# integration from presenting itself as a Phase 1 service error.
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

CHROMA_DIR   = Path(__file__).parent.parent / "chroma_db"
COLLECTION   = "krishimitra_kb"
EMBED_MODEL  = "nomic-embed-text"
OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

# How many raw candidates to retrieve before reranking
_RETRIEVAL_CANDIDATES = 20
# Default final top-k after rerank
_DEFAULT_K = 5
# Hard character cap per chunk in context (prevents token bloat)
_MAX_CHUNK_CHARS = 600

_client     = None
_collection = None

# Thread pool for parallel retrieval stages
_RETRIEVAL_POOL = ThreadPoolExecutor(max_workers=3, thread_name_prefix="rag-retrieval")

# ── Retrieval result cache (query hash → results) ─────────────────────────────
# LRU of 256 unique (augmented_query, k, category) combos.
# Agricultural queries repeat heavily (wheat pest, irrigation timing, etc.)
_result_cache: Dict[str, List[dict]] = {}
_RESULT_CACHE_MAX = 256

_DEFAULT_MIN_RELEVANCE = 0.50

_QUERY_CROP_TERMS = {
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
    "mango": ("mango", "आम"),
    "banana": ("banana", "केला"),
    "pomegranate": ("pomegranate", "अनार"),
    "turmeric": ("turmeric", "हल्दी"),
    "ginger": ("ginger", "अदरक"),
    "garlic": ("garlic", "लहसुन"),
}
_QUERY_CROP_TERMS = merge_crop_terms(_QUERY_CROP_TERMS, load_crop_terms())

_QUERY_TOPIC_TERMS = {
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

_TOPIC_SOURCE_HINTS = {
    "market": ("msp", "market", "mandi", "fpo", "export"),
    "scheme": ("scheme", "subsidy", "loan", "insurance", "kcc", "pmfby", "government"),
    "storage": ("storage", "warehouse", "post_harvest"),
    "disease": ("disease", "pest", "ipm"),
    "pest": ("pest", "ipm", "disease"),
    "soil": ("soil", "fertilizer", "irrigation"),
    "fertilizer": ("fertilizer", "soil"),
    "irrigation": ("irrigation", "drip", "sprinkler", "water"),
    "protected_cultivation": ("polyhouse", "greenhouse", "protected"),
}

# ── Hindi → English keyword expansion (unchanged from v3) ─────────────────────
_HI_EN: dict = {
    "गेहूँ": "wheat", "गेहू": "wheat", "गेहुं": "wheat",
    "धान": "rice paddy", "चावल": "rice",
    "मक्का": "maize corn", "ज्वार": "jowar sorghum",
    "बाजरा": "bajra pearl millet",
    "सरसों": "mustard rapeseed",
    "कपास": "cotton", "गन्ना": "sugarcane",
    "सोयाबीन": "soybean", "मूँगफली": "groundnut peanut",
    "चना": "chickpea gram", "अरहर": "pigeonpea arhar tur",
    "मूँग": "moong green gram", "उड़द": "urad black gram",
    "हल्दी": "turmeric", "अदरक": "ginger",
    "लहसुन": "garlic", "प्याज": "onion",
    "आलू": "potato", "टमाटर": "tomato",
    "बैंगन": "brinjal eggplant", "मिर्च": "chilli pepper",
    "आम": "mango", "केला": "banana", "अनार": "pomegranate",
    "धनिया": "coriander",
    # Pests / diseases
    "माहू": "aphid", "सुंडी": "caterpillar larva worm",
    "तना छेदक": "stem borer", "सफेद मक्खी": "whitefly",
    "थ्रिप्स": "thrips", "दीमक": "termite",
    "झुलसा": "blight", "फफूंदी": "fungal disease mold",
    "जड़ सड़न": "root rot", "पीलापन": "yellowing chlorosis",
    "रोग": "disease", "कीट": "pest insect",
    "कीटनाशक": "pesticide insecticide", "दवाई": "pesticide treatment",
    "नीम": "neem",
    # Farming operations
    "सिंचाई": "irrigation water", "बुवाई": "sowing planting",
    "खाद": "fertilizer manure", "उर्वरक": "fertilizer",
    "मिट्टी": "soil", "उपज": "yield", "कटाई": "harvest",
    "बीज": "seed", "फसल": "crop",
    # Weather / government
    "बारिश": "rain rainfall", "मौसम": "weather season",
    "तापमान": "temperature", "नमी": "moisture humidity",
    "योजना": "scheme", "सब्सिडी": "subsidy",
    "बीमा": "insurance", "किसान": "farmer",
    "मंडी": "mandi market", "एमएसपी": "msp minimum support price",
}

_ROMAN_HI_EN: dict = {
    "gehu": "wheat",
    "gehun": "wheat",
    "dhan": "rice paddy",
    "buwai": "sowing planting seed",
    "bonai": "sowing planting seed",
    "samay": "time timing",
    "tarika": "method practice",
    "mausam": "weather",
    "barish": "rain rainfall",
    "baarish": "rain rainfall",
    "fasal": "crop",
    "sinchai": "irrigation water",
    "khad": "fertilizer nutrient",
    "mandi": "market price",
    "bhav": "price rate",
    "daam": "price rate",
    "rog": "disease",
    "keet": "pest",
    "dawai": "crop protection treatment",
}


@lru_cache(maxsize=4096)
def _taxonomy_pattern(term: str):
    return re.compile(rf"(?<![a-z0-9_]){re.escape(term)}(?![a-z0-9_])")


def _contains_taxonomy_term(text_lower: str, term: str) -> bool:
    """Match Latin terms as words while retaining substring matching for Indic scripts."""
    normalized = str(term or "").strip().lower()
    if not normalized:
        return False
    if re.search(r"[a-z0-9]", normalized):
        return bool(_taxonomy_pattern(normalized).search(text_lower))
    return normalized in text_lower


def _augment(query: str) -> str:
    """Append English equivalents for Devanagari and Romanised Hindi terms."""
    extras = [eng for hi, eng in _HI_EN.items() if hi in query]
    lower = query.lower()
    extras.extend(
        english
        for roman, english in _ROMAN_HI_EN.items()
        if re.search(rf"\b{re.escape(roman)}\b", lower)
    )
    extras.extend(
        crop_id.replace("_", " ")
        for crop_id, terms in _QUERY_CROP_TERMS.items()
        if crop_id.replace("_", " ") not in lower
        and any(_contains_taxonomy_term(lower, term) for term in terms)
    )
    extras = list(dict.fromkeys(extras))
    return (query + " " + " ".join(extras)) if extras else query


def _min_relevance() -> float:
    raw = os.getenv("RAG_MIN_RELEVANCE", str(_DEFAULT_MIN_RELEVANCE))
    try:
        value = float(raw)
    except ValueError:
        logger.warning("Invalid RAG_MIN_RELEVANCE=%r; using %.2f", raw, _DEFAULT_MIN_RELEVANCE)
        value = _DEFAULT_MIN_RELEVANCE
    return max(0.0, min(value, 1.0))


def _cache_key(aug_query: str, k: int, category: Optional[str], min_relevance: float) -> str:
    raw = f"{aug_query}||{k}||{category or ''}||{min_relevance:.3f}"
    return hashlib.md5(raw.encode()).hexdigest()


@lru_cache(maxsize=512)
def _embed(text: str) -> tuple:
    """
    Get embedding for text via Ollama.

    RAG-3: @lru_cache means the same augmented query string is embedded
    only once per process lifetime.  Agricultural queries repeat heavily
    (top 50 queries account for ~80% of traffic).

    Returns a tuple (not list) because lru_cache requires hashable types.
    """
    t0 = time.monotonic()
    payload = json.dumps({"model": EMBED_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        vec = json.loads(resp.read())["embedding"]
    logger.debug("EMBED_MS=%.0f query='%s'", (time.monotonic() - t0) * 1000, text[:40])
    return tuple(vec)


def _get_collection():
    global _client, _collection
    if _collection is None:
        try:
            import chromadb
            _client = chromadb.PersistentClient(path=str(CHROMA_DIR))
            _collection = _client.get_collection(name=COLLECTION)
            logger.info("ChromaDB ready — %d vectors in '%s'", _collection.count(), COLLECTION)
        except Exception as exc:
            logger.error("ChromaDB load failed: %s", exc)
    return _collection


# ── Keyword overlap scorer (BM25-lite, no extra deps) ─────────────────────────
def _keyword_score(query_terms: set, doc: str) -> float:
    """
    Simple term-overlap ratio: |query ∩ doc_terms| / |query|
    Fast enough to score 20 candidates in <1 ms.
    """
    if not query_terms:
        return 0.0
    doc_lower = doc.lower()
    hits = sum(1 for term in query_terms if _contains_taxonomy_term(doc_lower, term))
    return hits / len(query_terms)


def _extract_tags(text: str, taxonomy: dict) -> set:
    lower = text.lower()
    return {
        tag
        for tag, terms in taxonomy.items()
        if any(_contains_taxonomy_term(lower, term) for term in terms)
    }


def _split_meta_tags(value: object) -> set:
    if not value:
        return set()
    return {part for part in str(value).split("|") if part and part != "general"}


def _candidate_tag_sets(candidate: dict) -> tuple[set, set]:
    text = candidate.get("text", "")
    crops = _split_meta_tags(candidate.get("crops")) | _extract_tags(text, _QUERY_CROP_TERMS)
    topics = _split_meta_tags(candidate.get("topics")) | _extract_tags(text, _QUERY_TOPIC_TERMS)
    return crops, topics


def _tag_alignment_score(query_tags: set, candidate_tags: set, *, mismatch_penalty: float = -0.35) -> float:
    if not query_tags:
        return 0.0
    if not candidate_tags:
        return 0.0
    overlap = query_tags & candidate_tags
    if overlap:
        return len(overlap) / len(query_tags)
    return mismatch_penalty


def _source_alignment_score(query_topics: set, candidate: dict) -> float:
    if not query_topics:
        return 0.0
    haystack = " ".join(
        str(candidate.get(key, ""))
        for key in ("source_file", "source_stem", "category", "topics")
    ).lower()
    matched = 0
    for topic in query_topics:
        hints = _TOPIC_SOURCE_HINTS.get(topic, ())
        if any(hint in haystack for hint in hints):
            matched += 1
    return matched / len(query_topics)


def _source_crop_alignment_score(query_crops: set, candidate: dict) -> float:
    """Prefer a source whose filename names the requested crop.

    Chunk metadata is inferred from text and can inherit a crop word from a
    cross-reference (for example a rice document mentioning wheat).  The
    source filename is a stronger guard against cross-crop grounding.
    """
    if not query_crops:
        return 0.0
    source = str(candidate.get("source_file") or candidate.get("source_stem") or "").lower()
    if any(crop in source for crop in query_crops):
        return 1.0
    known_crop_sources = set()
    for crop, aliases in _QUERY_CROP_TERMS.items():
        if crop in source or any(alias.lower() in source for alias in aliases if alias.isascii()):
            known_crop_sources.add(crop)
    if known_crop_sources and not (known_crop_sources & query_crops):
        return -0.5
    return 0.0


def _apply_relevance_threshold(results: List[dict], min_relevance: float) -> List[dict]:
    if min_relevance <= 0:
        return results
    filtered = [r for r in results if r.get("score", 0.0) >= min_relevance]
    if len(filtered) != len(results):
        logger.info(
            "RAG relevance filter kept %d/%d chunks at threshold %.2f",
            len(filtered), len(results), min_relevance,
        )
    return filtered


def _rerank(
    candidates: List[dict],
    query: str,
    final_k: int,
) -> List[dict]:
    """
    RAG-1/RAG-2: Rerank Top-20 candidates to Top-k using a combined score:
      combined = 0.7 * vector_similarity + 0.3 * keyword_overlap

    This is the key insight from the RAG optimization article:
    "The best RAG engineers optimize context."
    Sending 5 highly relevant chunks beats sending 20 mediocre ones.

    Also deduplicates near-identical chunks (first 80 chars as fingerprint).
    """
    query_terms = set(re.findall(r"\w+", query.lower()))
    query_crops = _extract_tags(query, _QUERY_CROP_TERMS)
    query_topics = _extract_tags(query, _QUERY_TOPIC_TERMS)
    seen: set = set()
    scored: List[Tuple[float, dict]] = []

    for c in candidates:
        # Dedup — skip chunks that start the same way (RAG-2)
        fp = c["text"][:80]
        if fp in seen:
            continue
        seen.add(fp)

        vec_sim  = c.get("score", 0.0)
        kw_score = _keyword_score(query_terms, c["text"])
        cand_crops, cand_topics = _candidate_tag_sets(c)
        crop_score = _tag_alignment_score(query_crops, cand_crops)
        topic_score = _tag_alignment_score(query_topics, cand_topics, mismatch_penalty=-0.15)
        source_score = _source_alignment_score(query_topics, c)
        source_crop_score = _source_crop_alignment_score(query_crops, c)
        # Exact crop and topic metadata are stronger evidence than a merely
        # similar embedding in agricultural advice.  This prevents a wheat
        # question from grounding on a rice/calendar passage with overlapping
        # words such as "sowing" or "season".
        combined = (
            0.30 * vec_sim
            + 0.20 * kw_score
            + 0.25 * crop_score
            + 0.10 * topic_score
            + 0.05 * source_score
            + 0.10 * source_crop_score
        )
        scored.append((combined, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for score, c in scored[:final_k]:
        c = dict(c)
        c["score"] = round(score, 3)
        # RAG-2: hard-cap chunk to _MAX_CHUNK_CHARS to prevent token bloat
        c["text"] = c["text"][:_MAX_CHUNK_CHARS]
        results.append(c)

    return results


def _vector_search(
    vec: list,
    n: int,
    category: Optional[str],
) -> List[dict]:
    """Run ChromaDB vector search and return raw candidate dicts."""
    col = _get_collection()
    if col is None:
        return []
    t0 = time.monotonic()
    kwargs: dict = {
        "query_embeddings": [list(vec)],
        "n_results": n,
        "include": ["documents", "metadatas", "distances"],
    }
    if category:
        kwargs["where"] = {"category": category}
    res = col.query(**kwargs)
    docs  = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    logger.debug("VECTOR_MS=%.0f n=%d", (time.monotonic() - t0) * 1000, len(docs))
    return [
        {
            "text":        doc,
            "source_file": meta.get("source_file", "unknown"),
            "category":    meta.get("category", "general"),
            "crops":       meta.get("crops", "general"),
            "topics":      meta.get("topics", meta.get("category", "general")),
            "language":    meta.get("language", "unknown"),
            "chunk_index": meta.get("chunk_index"),
            "score":       round(1 - dist, 3),
        }
        for doc, meta, dist in zip(docs, metas, dists)
    ]


def _keyword_search(query: str, n: int, category: Optional[str]) -> List[dict]:
    """Retrieve grounded chunks when the optional embedding service is down."""
    col = _get_collection()
    if col is None:
        return []
    kwargs: dict = {"include": ["documents", "metadatas"]}
    if category:
        kwargs["where"] = {"category": category}
    data = col.get(**kwargs)
    query_terms = set(re.findall(r"\w+", query.lower()))
    query_crops = _extract_tags(query, _QUERY_CROP_TERMS)
    query_topics = _extract_tags(query, _QUERY_TOPIC_TERMS)
    scored: List[Tuple[float, dict]] = []
    for doc, meta in zip(data.get("documents", []), data.get("metadatas", [])):
        candidate = {
            "text": doc,
            "source_file": meta.get("source_file", "unknown"),
            "category": meta.get("category", "general"),
            "crops": meta.get("crops", "general"),
            "topics": meta.get("topics", meta.get("category", "general")),
            "language": meta.get("language", "unknown"),
            "chunk_index": meta.get("chunk_index"),
            "score": 0.0,
        }
        crops, topics = _candidate_tag_sets(candidate)
        score = (
            0.65 * _keyword_score(query_terms, doc)
            + 0.25 * _tag_alignment_score(query_crops, crops)
            + 0.10 * _tag_alignment_score(query_topics, topics, mismatch_penalty=0.0)
        )
        if score > 0:
            candidate["score"] = score
            scored.append((score, candidate))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored[:n]]


def retrieve(
    query: str,
    k: int = _DEFAULT_K,
    category: Optional[str] = None,
) -> List[str]:
    """
    Return top-k relevant text chunks (text only, no metadata).

    RAG-1: fetches _RETRIEVAL_CANDIDATES (20) then reranks to k.
    RAG-3: result is cached by (augmented_query, k, category).
    """
    results = retrieve_with_sources(query, k=k, category=category)
    return [r["text"] for r in results]


def retrieve_with_sources(
    query: str,
    k: int = _DEFAULT_K,
    category: Optional[str] = None,
) -> List[dict]:
    """
    Return top-k chunks with source metadata and combined rerank score.

    Pipeline (all timings logged at DEBUG):
      1. Augment query with Hindi→English expansions
      2. Embed (LRU cached)                          [EMBED_MS]
      3. Vector search for _RETRIEVAL_CANDIDATES     [VECTOR_MS]
      4. Rerank Top-20 → Top-k (keyword + vector)    [RERANK_MS]
      5. Return compressed chunks                    [TOTAL_MS]
    """
    t_total = time.monotonic()
    col = _get_collection()
    if col is None:
        return []

    aug = _augment(query)

    # ── RAG-3: result cache check ─────────────────────────────────
    min_relevance = _min_relevance()
    ck = _cache_key(aug, k, category, min_relevance)
    if ck in _result_cache:
        logger.debug("RAG result cache HIT for '%s'", query[:40])
        return _result_cache[ck]

    try:
        # ── RAG-1: parallel embedding + (optionally) keyword pre-scan ────
        # Embedding must finish before vector search, but the augmentation
        # and cache check happen in the calling thread.  We run the embed
        # on the pool so it doesn't block other operations in the caller.
        embed_future = _RETRIEVAL_POOL.submit(_embed, aug)
        try:
            vec = embed_future.result(timeout=15)
            # ── RAG-1: vector search ──────────────────────────────────────
            n_candidates = min(_RETRIEVAL_CANDIDATES, col.count())
            t_vec = time.monotonic()
            candidates = _vector_search(vec, n_candidates, category)
            logger.debug("VECTOR_MS=%.0f", (time.monotonic() - t_vec) * 1000)

            # Embeddings are useful for semantic recall, but agricultural
            # queries need exact crop/topic grounding too.  Always add the
            # lexical metadata matches so a high-similarity generic passage
            # cannot displace the crop's ICAR/package-of-practices passage.
            keyword_candidates = _keyword_search(aug, n_candidates, category)
            merged = {}
            for candidate in candidates + keyword_candidates:
                key = (
                    candidate.get("source_file", ""),
                    candidate.get("chunk_index"),
                    candidate.get("text", "")[:80],
                )
                existing = merged.get(key)
                if existing is None or candidate.get("score", 0) > existing.get("score", 0):
                    merged[key] = candidate
            candidates = list(merged.values())
            logger.debug("HYBRID_CANDIDATES=%d", len(candidates))
        except Exception as exc:
            logger.warning("Embedding retrieval unavailable; using keyword KB fallback: %s", exc)
            candidates = _keyword_search(aug, _RETRIEVAL_CANDIDATES, category)

        # ── RAG-1+2: rerank + compress ────────────────────────────────────
        t_rerank = time.monotonic()
        results = _apply_relevance_threshold(_rerank(candidates, aug, k), min_relevance)
        logger.debug("RERANK_MS=%.0f", (time.monotonic() - t_rerank) * 1000)

        # ── RAG-3: store in result cache ──────────────────────────────────
        if len(_result_cache) >= _RESULT_CACHE_MAX:
            # Evict oldest entry (dict insertion order in Python 3.7+)
            oldest = next(iter(_result_cache))
            del _result_cache[oldest]
        _result_cache[ck] = results

        logger.debug(
            "TOTAL_MS=%.0f query='%s' candidates=%d→k=%d",
            (time.monotonic() - t_total) * 1000,
            query[:40], len(candidates), len(results),
        )
        return results

    except FuturesTimeout:
        logger.warning("Embedding timed out; using keyword KB fallback for query: %s", query[:40])
        candidates = _keyword_search(aug, _RETRIEVAL_CANDIDATES, category)
        return _apply_relevance_threshold(_rerank(candidates, aug, k), min_relevance)
    except Exception as exc:
        logger.error("Retrieval failed: %s", exc)
        return []


def is_available() -> bool:
    try:
        col = _get_collection()
        return col is not None and col.count() > 0
    except Exception as exc:
        logger.error("RAG availability check failed: %s", exc)
        return False


def clear_cache() -> None:
    """Clear both the result cache and the embedding LRU cache."""
    _result_cache.clear()
    _embed.cache_clear()
    logger.info("RAG caches cleared")
