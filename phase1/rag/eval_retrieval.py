#!/usr/bin/env python3
"""
Phase 1 RAG retrieval regression harness.

CI-safe static mode:
    python3 phase1/rag/eval_retrieval.py --static

Live mode with local Ollama + Chroma:
    python3 phase1/rag/eval_retrieval.py --live
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rag.ingest import CHUNK_SIZE, chunk_text
else:
    from .ingest import CHUNK_SIZE, chunk_text

KB_DIR = Path(__file__).resolve().parents[1] / "knowledge_base"
OLLAMA_URL = "http://localhost:11434"

CASES = [
    ("wheat yellow rust control dose", {"wheat_diseases_rust_smut.txt", "wheat_icar.txt"}),
    ("गेहूं में पीला रतुआ क्या करें", {"wheat_diseases_rust_smut.txt", "wheat_icar.txt"}),
    ("rice blast management tricyclazole", {"rice_diseases_blast_blt_sheath.txt", "rice_icar.txt"}),
    ("धान में झुलसा रोग का इलाज", {"rice_diseases_blast_blt_sheath.txt", "rice_icar.txt"}),
    ("mustard aphid control Dimethoate", {"mustard_icar.txt", "ipm_guide.txt"}),
    ("सरसों माहू नियंत्रण", {"mustard_icar.txt", "ipm_guide.txt"}),
    ("cotton whitefly management ETL", {"cotton_icar.txt", "ipm_guide.txt"}),
    ("maize fall armyworm control", {"fall_armyworm_detailed.txt", "maize_icar.txt"}),
    ("sugarcane red rot seed treatment", {"sugarcane_icar.txt", "crop_disease_diagnosis.txt"}),
    ("tomato early blight mancozeb", {"tomato_potato_onion.txt", "crop_disease_diagnosis.txt"}),
    ("potato late blight spray", {"tomato_potato_onion.txt", "crop_disease_diagnosis.txt"}),
    (
        "onion fertilizer schedule",
        {"tomato_potato_onion.txt", "fertilizer_application_schedule.txt", "soil_health_fertilizer_guide.txt"},
    ),
    ("soybean seed treatment rhizobium", {"soybean_icar.txt"}),
    ("groundnut tikka disease management", {"groundnut_millets.txt", "crop_disease_diagnosis.txt"}),
    ("bajra downy mildew control", {"groundnut_millets.txt", "crop_disease_diagnosis.txt"}),
    ("drip irrigation subsidy and installation", {"drip_sprinkler_installation.txt", "government_schemes_complete.txt"}),
    ("soil test pH interpretation fertilizer", {"soil_testing_interpretation.txt", "soil_health_fertilizer_guide.txt"}),
    ("organic farming jeevamrut dose", {"organic_farming_guide.txt"}),
    ("PM Kisan eligibility", {"government_schemes_complete.txt"}),
    ("PMFBY claim process", {"crop_insurance_pmfby_detail.txt"}),
    ("KCC loan interest rate", {"kcc_loan_nabard_schemes.txt", "government_schemes_complete.txt"}),
    ("MSP wheat 2024 price", {"msp_market_prices_2024.txt"}),
    ("stored grain pest phosphine fumigation", {"stored_grain_pest_management.txt"}),
    ("banana fruit crop spacing fertilizer", {"horticulture_fruits.txt"}),
    ("polyhouse tomato cucumber subsidy", {"polyhouse_greenhouse_farming.txt", "government_schemes_complete.txt"}),
    ("cucumber french bean broccoli season and soil", {"indian_horticulture_extended.txt"}),
    ("tapioca elephant foot yam cultivation", {"indian_horticulture_extended.txt"}),
    ("बेर किन्नू नींबू बागवानी", {"indian_horticulture_extended.txt"}),
    ("saffron vanilla climate requirements", {"indian_horticulture_extended.txt"}),
]

REQUIRED_METADATA = {
    "source_file",
    "source_stem",
    "category",
    "chunk_index",
    "crops",
    "topics",
    "language",
    "char_count",
}


def _ollama_available() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        return any("nomic-embed-text" in model.get("name", "") for model in data.get("models", []))
    except Exception:
        return False


def run_static() -> dict:
    files = sorted(KB_DIR.glob("*/*.txt"))
    if not files:
        raise AssertionError(f"No knowledge files found in {KB_DIR}")

    all_sources = {path.name for path in files}
    missing_sources = {
        source
        for _, expected_sources in CASES
        for source in expected_sources
        if source not in all_sources
    }
    if missing_sources:
        raise AssertionError(f"Eval expected sources missing from KB: {sorted(missing_sources)}")

    chunk_count = 0
    max_len = 0
    missing_metadata = []
    for path in files:
        chunks = chunk_text(path.read_text(encoding="utf-8"), path.name, path.parent.name)
        for chunk in chunks:
            chunk_count += 1
            max_len = max(max_len, len(chunk["text"]))
            missing = REQUIRED_METADATA - set(chunk)
            if missing:
                missing_metadata.append((path.name, sorted(missing)))
            if len(chunk["text"]) > CHUNK_SIZE:
                raise AssertionError(f"Oversized chunk in {path.name}: {len(chunk['text'])}")

    if missing_metadata:
        raise AssertionError(f"Chunks missing metadata: {missing_metadata[:5]}")

    return {
        "mode": "static",
        "knowledge_files": len(files),
        "eval_cases": len(CASES),
        "chunks": chunk_count,
        "max_chunk_chars": max_len,
        "status": "passed",
    }


def run_live(min_top2: float) -> dict:
    if not _ollama_available():
        raise RuntimeError("Ollama/nomic-embed-text unavailable; start Ollama or run --static in CI")

    if __package__ in {None, ""}:
        from rag.retriever import clear_cache, retrieve_with_sources
    else:
        from .retriever import clear_cache, retrieve_with_sources

    clear_cache()
    rows = []
    started = time.time()
    for query, expected_sources in CASES:
        query_started = time.time()
        results = retrieve_with_sources(query, k=3)
        sources = [row.get("source_file") for row in results]
        rows.append({
            "query": query,
            "top1": bool(sources and sources[0] in expected_sources),
            "top2": any(source in expected_sources for source in sources[:2]),
            "sources": sources,
            "scores": [row.get("score") for row in results],
            "latency_ms": round((time.time() - query_started) * 1000),
        })

    top1 = sum(row["top1"] for row in rows)
    top2 = sum(row["top2"] for row in rows)
    top2_rate = top2 / len(rows)
    if top2_rate < min_top2:
        raise AssertionError(f"Top-2 retrieval {top2_rate:.2%} below required {min_top2:.2%}")

    return {
        "mode": "live",
        "eval_cases": len(rows),
        "top1": top1,
        "top2": top2,
        "top1_rate": round(top1 / len(rows), 3),
        "top2_rate": round(top2_rate, 3),
        "total_ms": round((time.time() - started) * 1000),
        "rows": rows,
        "status": "passed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Phase 1 RAG retrieval quality")
    parser.add_argument("--static", action="store_true", help="Run CI-safe KB/chunk metadata checks")
    parser.add_argument("--live", action="store_true", help="Run live retrieval checks through Chroma + Ollama")
    parser.add_argument("--min-top2", type=float, default=0.90, help="Minimum live top-2 pass rate")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    if not args.static and not args.live:
        args.static = True

    reports = []
    try:
        if args.static:
            reports.append(run_static())
        if args.live:
            reports.append(run_live(args.min_top2))
    except Exception as exc:
        if args.json:
            print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"RAG eval failed: {exc}", file=sys.stderr)
        return 1

    payload = {"status": "passed", "reports": reports}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            if report["mode"] == "static":
                print(
                    "Static RAG check passed: "
                    f"{report['knowledge_files']} files, {report['chunks']} chunks, "
                    f"max {report['max_chunk_chars']} chars"
                )
            else:
                print(
                    "Live RAG eval passed: "
                    f"top1={report['top1']}/{report['eval_cases']} "
                    f"top2={report['top2']}/{report['eval_cases']} "
                    f"in {report['total_ms']}ms"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
