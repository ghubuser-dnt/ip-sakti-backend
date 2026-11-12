"""
api_schemas.py — IP-SAKTI Sahayak (SIH26045)


These are API PAYLOAD schemas — distinct from schema.py's Chunk /
ChunkMetadata, which describe stored chunk data, not HTTP request/
response shapes. No new logic lives here: field types are drawn
directly from classification.py, confidence.py, and run_query.py so
FastAPI/Pydantic can validate and document the existing verified
pipeline without reimplementing any of it.
"""

from typing import Optional

from pydantic import BaseModel, Field

from classification import FormulationCategory
from confidence import ConfidenceLevel


# ---------------------------------------------------------------------------
# POST /classify
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    """
    Mirrors classification.ClassificationAnswers field-for-field.
    All fields are optional at the API layer too — classify() itself
    is what enforces "this question was needed but unanswered" via
    ClassificationError, which the endpoint translates into a 422.
    """
    q1_from_first_schedule_text: Optional[bool] = None
    q2_requires_new_clinical_evidence: Optional[bool] = None
    q3_proprietary_blend_marketed_as_medicine: Optional[bool] = None
    q4_extraction_standardized_phytomedicine: Optional[bool] = None
    q5_consumed_as_food_or_supplement: Optional[bool] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "q1_from_first_schedule_text": False,
                "q2_requires_new_clinical_evidence": True,
            }
        }
    }


class ClassifyResponse(BaseModel):
    """
    category + the full POSTURE_SUMMARY dict for that category,
    flattened into named fields (label, ip_posture, abs_posture,
    prior_art_note) rather than passed through as a raw dict.
    """
    category: FormulationCategory
    label: str
    ip_posture: str
    abs_posture: str
    prior_art_note: str


# ---------------------------------------------------------------------------
# POST /query
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    query_text: str
    jurisdiction: str = Field(
        ...,
        description='Must be "india" or "international". Enforced at the '
        "retrieval layer by build_where_clause(); FastAPI just passes it "
        "through here.",
    )
    ip_type: Optional[str] = None
    formulation_category: Optional[FormulationCategory] = Field(
        default=None,
        description="If provided, must be one of FormulationCategory's "
        "values — arbitrary strings are rejected by Pydantic before this "
        "ever reaches retrieval.",
    )
    n_results: int = 5

    model_config = {
        "json_schema_extra": {
            "example": {
                "query_text": "Can a classical Ayurvedic formulation be patented in India?",
                "jurisdiction": "india",
            }
        }
    }


class QueryResponse(BaseModel):
    """Typed mirror of answer_query()'s return dict."""
    text: str
    confidence: ConfidenceLevel
    abstained: bool
