"""
run_query.py — IP-SAKTI Sahayak (SIH26045)

This is glue only — it does NOT add new gating logic. confidence.py's
generate_or_abstain() already owns the abstain-vs-generate decision;
this module just shows the intended call shape end-to-end, from a raw
query through to a final answer (or abstention).

Not a FastAPI endpoint — that's Phase F. This is the plain-Python
wiring that a future endpoint will call into.
"""

from typing import Optional

from retrieval import query_chunks, flatten_query_result
from classification import get_posture_summary, FormulationCategory
from confidence import generate_or_abstain
from generation import build_prompt, call_llm


def answer_query(
    query_text: str,
    jurisdiction: str,
    ip_type: Optional[str] = None,
    formulation_category: Optional[FormulationCategory] = None,
    n_results: int = 5,
) -> dict:
    """
    End-to-end: retrieve -> gate on confidence -> generate (or abstain).

    Returns the dict shape from generate_or_abstain():
        {"text": str, "confidence": ConfidenceLevel, "abstained": bool}
    """
    # Step 1: retrieve (Phase C, untouched)
    formulation_value = (
        formulation_category.value if formulation_category is not None else None
    )
    raw_results = query_chunks(
        query_text=query_text,
        jurisdiction=jurisdiction,
        ip_type=ip_type,
        formulation_category=formulation_value,
        n_results=n_results,
    )
    chunks = flatten_query_result(raw_results)

    # Step 2: determine top-chunk distance for the confidence gate.
    # No chunks at all -> treat as worst-case distance so
    # generate_or_abstain() correctly routes to abstention rather than
    # calling generate_fn on an empty context.
    top_distance = chunks[0]["distance"] if chunks else float("inf")

    # Step 3: optional classification context
    classification_result = (
        get_posture_summary(formulation_category)
        if formulation_category is not None
        else None
    )

    # Step 4: the generate_fn closure — this is the only new "logic"
    # Phase E contributes; everything else here is calling verified
    # functions from prior phases.
    def generate_fn():
        prompt = build_prompt(
            query_text=query_text,
            jurisdiction=jurisdiction,
            classification_result=classification_result,
            retrieved_chunks=chunks,
        )
        return call_llm(prompt)

    return generate_or_abstain(top_distance, generate_fn)


if __name__ == "__main__":
    # Manual smoke test against the real ChromaDB mock collection.
    # Requires: ingest.py already run (Phase A), Ollama running with
    # llama3 pulled (Step 1).
    result = answer_query(
        query_text="Can a classical Ayurvedic formulation be patented in India?",
        jurisdiction="india",
    )
    print(f"Confidence: {result['confidence']}")
    print(f"Abstained: {result['abstained']}")
    print()
    print(result["text"])
