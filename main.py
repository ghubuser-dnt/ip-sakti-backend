"""
main.py — IP-SAKTI Sahayak (SIH26045)
FastAPI app exposing POST /classify and POST /query.

This file is glue only, per Phase F scope. It does not reimplement or
alter any logic from Phases A-E:
  - /classify wraps classification.classify() + get_posture_summary()
  - /query wraps run_query.answer_query() (retrieve -> confidence gate
    -> generate/abstain), unchanged.

No CORS, auth, or deployment config — explicitly out of scope for this
hackathon phase.
"""

from fastapi import FastAPI, HTTPException

from api_schemas import (
    ClassifyRequest,
    ClassifyResponse,
    QueryRequest,
    QueryResponse,
)
from classification import (
    ClassificationAnswers,
    ClassificationError,
    classify,
    get_posture_summary,
)
from run_query import answer_query

app = FastAPI(
    title="IP-SAKTI Sahayak API",
    description="RAG backend for Ayurveda IP/regulatory guidance (SIH26045).",
    version="0.1.0",
)


@app.post("/classify", response_model=ClassifyResponse)
def classify_formulation(request: ClassifyRequest) -> ClassifyResponse:
    """
    Thin wrapper: build ClassificationAnswers from the request body,
    run the existing Q1-Q5 decision tree, and return its posture
    summary. A ClassificationError (an answer needed to reach a
    verdict was missing) becomes a clean 422, not a raw 500.
    """
    answers = ClassificationAnswers(
        q1_from_first_schedule_text=request.q1_from_first_schedule_text,
        q2_requires_new_clinical_evidence=request.q2_requires_new_clinical_evidence,
        q3_proprietary_blend_marketed_as_medicine=request.q3_proprietary_blend_marketed_as_medicine,
        q4_extraction_standardized_phytomedicine=request.q4_extraction_standardized_phytomedicine,
        q5_consumed_as_food_or_supplement=request.q5_consumed_as_food_or_supplement,
    )

    try:
        category = classify(answers)
    except ClassificationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    posture = get_posture_summary(category)

    return ClassifyResponse(
        category=category,
        label=posture["label"],
        ip_posture=posture["ip_posture"],
        abs_posture=posture["abs_posture"],
        prior_art_note=posture["prior_art_note"],
    )


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    """
    Thin wrapper around run_query.answer_query() — the exact
    retrieve -> confidence-gate -> generate/abstain wiring already
    smoke-tested in Phase E. formulation_category, if present, is
    already validated to be a real FormulationCategory by Pydantic
    before it ever reaches this function.
    """
    try:
        result = answer_query(
            query_text=request.query_text,
            jurisdiction=request.jurisdiction,
            ip_type=request.ip_type,
            formulation_category=request.formulation_category,
            n_results=request.n_results,
        )
    except ValueError as e:
        # e.g. build_where_clause() rejecting an invalid jurisdiction
        # string that isn't "india"/"international".
        raise HTTPException(status_code=422, detail=str(e)) from e

    return QueryResponse(**result)
