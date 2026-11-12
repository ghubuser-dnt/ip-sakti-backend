"""
confidence.py — IP-SAKTI Sahayak (SIH26045)
confidence bucketing from top-chunk similarity
distance, plus the hard abstention path.

--- IMPORTANT: distance metric assumption (read before changing thresholds) ---
The 'ip_sakti_mock' collection (see ingest.py) does NOT set
metadata={"hnsw:space": ...}, so ChromaDB uses its default metric:
SQUARED L2, not cosine similarity. Additionally, retrieval.py's
_get_model().encode() call does NOT pass normalize_embeddings=True, so
embeddings are not unit-normalized.

The thresholds below were set by running real mock queries through
query_chunks() (see calibrate_confidence.py) and reading off the
actual distances returned — NOT by assuming a 0-1/0-2 cosine-style
range. Observed values:
    High-confidence candidate queries: 0.307 - 0.917
    Low-confidence candidate queries:  1.630 - 1.924
There's a wide gap (0.92 -> 1.63) with nothing in between, so the cutoffs
below sit safely inside that gap rather than on a fragile boundary.

If ingest.py is ever changed to add hnsw:space="cosine" or
normalize_embeddings=True is added to the encode() call, these
thresholds will silently stop making sense and must be recalibrated
by rerunning calibrate_confidence.py.
"""

from enum import Enum

# Thresholds are UPPER BOUNDS (inclusive) for each bucket, calibrated
# against real distances from calibrate_confidence.py. See module
# docstring above before changing these.
HIGH_CONFIDENCE_MAX_DISTANCE = 0.7
MEDIUM_CONFIDENCE_MAX_DISTANCE = 1.2


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# The exact required abstention string (byte-for-byte, per Phase D spec
# and base_context.txt's system prompt rule #4). Do not reword this.
ABSTENTION_MESSAGE = (
    "I don't have sufficient information in my reference documents to "
    "answer this accurately. Please consult official AYUSH/TKDL sources "
    "or escalate to a human IP facilitator."
)


def confidence_bucket(distance: float) -> ConfidenceLevel:
    """
    Pure function: map a single top-chunk distance to a confidence
    bucket. Takes a distance float directly (not the whole retrieval
    result), so it can be built and unit-tested against mock distance
    values without a live retrieval call.

    Lower distance = closer match = higher confidence, since this
    collection uses squared L2 distance (not cosine similarity).
    """
    if distance <= HIGH_CONFIDENCE_MAX_DISTANCE:
        return ConfidenceLevel.HIGH
    if distance <= MEDIUM_CONFIDENCE_MAX_DISTANCE:
        return ConfidenceLevel.MEDIUM
    return ConfidenceLevel.LOW


def should_abstain(distance: float) -> bool:
    """
    Convenience wrapper: True if the confidence bucket for this
    distance is LOW, meaning the generation step should be skipped
    entirely in favor of the hard abstention message.
    """
    return confidence_bucket(distance) is ConfidenceLevel.LOW


def generate_or_abstain(distance: float, generate_fn):
    """
    The hard abstention gate.

    - If confidence is LOW: returns ABSTENTION_MESSAGE immediately.
      generate_fn is NEVER called in this branch — no LLM call happens,
      by construction, not by convention.
    - Otherwise: calls generate_fn() and returns its result, tagged
      with the confidence bucket so the caller (later: FastAPI
      endpoint) can show the High/Medium badge.

    generate_fn is a zero-argument callable (later phase will pass in
    something like `lambda: call_claude(prompt)`). Kept generic here
    so this module has no dependency on the actual LLM client.

    Returns a dict: {"text": str, "confidence": ConfidenceLevel, "abstained": bool}
    """
    bucket = confidence_bucket(distance)

    if bucket is ConfidenceLevel.LOW:
        return {
            "text": ABSTENTION_MESSAGE,
            "confidence": bucket,
            "abstained": True,
        }

    generated_text = generate_fn()
    return {
        "text": generated_text,
        "confidence": bucket,
        "abstained": False,
    }
