"""
test_generation.py — IP-SAKTI Sahayak (SIH26045)

Reuses the SAME 9 mock chunks (mock_chunks.py) and the SAME calibrated
distance thresholds already validated in Phase D (confidence.py) — no
new test fixtures invented, per Phase E scope.

Run: python3 test_generation.py

Structure:
  - Checkpoints 1-6: structural tests on build_prompt(). No I/O, no
    ChromaDB, no Ollama required — these always run.
  - Checkpoint 7: the confidence-gate wiring (generate_or_abstain +
    a fake generate_fn) — confirms generate_fn is/isn't called
    correctly. No live LLM needed.
  - Checkpoint 8 (optional/live): an actual call_llm() round trip
    against Ollama, checking the disclaimer sentence appears in real
    model output. Skips with a clear message if Ollama isn't running
    rather than failing the whole suite — this is an integration
    check, not a unit check, since it depends on live model behavior.
"""

from classification import get_posture_summary, FormulationCategory
from confidence import (
    generate_or_abstain,
    HIGH_CONFIDENCE_MAX_DISTANCE,
    MEDIUM_CONFIDENCE_MAX_DISTANCE,
    ABSTENTION_MESSAGE,
)
from generation import build_prompt, call_llm
from mock_chunks import MOCK_CHUNKS

passed = 0
failed = 0


def check(condition: bool, description: str):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {description}")
    else:
        failed += 1
        print(f"  FAIL: {description}")


def chunk_to_flat_dict(chunk) -> dict:
    """Convert a mock_chunks.py Chunk (pydantic) into the flat dict
    shape build_prompt() expects — the same shape
    retrieval.flatten_query_result() produces from a live ChromaDB
    query, so this test exercises build_prompt() exactly as it will
    really be called."""
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "metadata": chunk.metadata.model_dump(),
        "distance": None,
    }


# ---------------------------------------------------------------------------
# Checkpoints 1-6: build_prompt() structural checks
# ---------------------------------------------------------------------------

print("Checkpoints 1-6: build_prompt() structural tests")

india_chunks = [
    chunk_to_flat_dict(c) for c in MOCK_CHUNKS if c.metadata.jurisdiction == "india"
]
international_chunks = [
    chunk_to_flat_dict(c) for c in MOCK_CHUNKS if c.metadata.jurisdiction == "international"
]

india_prompt = build_prompt(
    query_text="Can a classical Ayurvedic formulation be patented in India?",
    jurisdiction="india",
    classification_result=get_posture_summary(FormulationCategory.CLASSICAL),
    retrieved_chunks=india_chunks,
)

# 1. Every india-tagged mock chunk's document name appears in the prompt
check(
    all(c.text.split(",")[0] in india_prompt or c.metadata.document in india_prompt
        for c in MOCK_CHUNKS if c.metadata.jurisdiction == "india"),
    "All India-jurisdiction document names appear in the India-filtered prompt",
)

# 2. No international document names leak into an india-jurisdiction prompt
check(
    all(c.metadata.document not in india_prompt
        for c in MOCK_CHUNKS if c.metadata.jurisdiction == "international"),
    "No international-jurisdiction document names leak into the India prompt",
)

# 3. Citation lines are built from real metadata, not placeholder text
check(
    "[Source: Patents Act, 1970 (as amended), Section 3(p), Jurisdiction: india]" in india_prompt,
    "Citation line for patents_act_sec_3p is built correctly from real metadata",
)

# 4. Classification block reflects the passed-in category, not a placeholder
check(
    "Classical / Generic Medicine" in india_prompt
    and "Section 3(p)" in india_prompt,
    "Classification posture summary is correctly slotted into the prompt",
)

# 5. classification_result=None renders the documented fallback
no_classification_prompt = build_prompt(
    query_text="What IP protection applies to this product?",
    jurisdiction="india",
    classification_result=None,
    retrieved_chunks=india_chunks,
)
check(
    "Not yet classified." in no_classification_prompt,
    "classification_result=None renders 'Not yet classified.' fallback",
)

# 6. Jurisdiction-separation instruction (rule 2) is present verbatim,
#    for ANY jurisdiction — this is what makes cross-jurisdiction
#    questions get a non-blended answer; a full dual-jurisdiction LLM
#    test is a nice-to-have here per the Phase E doc, not required.
check(
    "Do NOT blend India and\n   international law in a single answer." in india_prompt,
    "Rule 2 (no blending jurisdictions) instruction present verbatim",
)

# Also confirm the disclaimer RULE (rule 5) is present in the system
# prompt instructions themselves — note this checks the instruction is
# given to the LLM, not that the LLM obeyed it (that's Checkpoint 8,
# the live test).
check(
    "This is general information, not legal advice. For formal guidance,\n"
    "   consult a qualified IP professional." in india_prompt,
    "Rule 5 (disclaimer) instruction present verbatim in system prompt",
)

print()

# ---------------------------------------------------------------------------
# Checkpoint 7: confidence-gate wiring (no live LLM needed)
# ---------------------------------------------------------------------------

print("Checkpoint 7: generate_or_abstain() wiring")

calls = []


def fake_generate_fn():
    calls.append(1)
    return "fake generated answer"


# High-confidence distance (well inside the calibrated High bucket)
high_conf_distance = HIGH_CONFIDENCE_MAX_DISTANCE - 0.1
calls.clear()
result_high = generate_or_abstain(high_conf_distance, fake_generate_fn)
check(
    result_high["abstained"] is False and len(calls) == 1,
    "High-confidence distance calls generate_fn exactly once and does not abstain",
)

# Low-confidence distance (well past the Medium cutoff)
low_conf_distance = MEDIUM_CONFIDENCE_MAX_DISTANCE + 0.5
calls.clear()
result_low = generate_or_abstain(low_conf_distance, fake_generate_fn)
check(
    result_low["abstained"] is True
    and result_low["text"] == ABSTENTION_MESSAGE
    and len(calls) == 0,
    "Low-confidence distance abstains and NEVER calls generate_fn",
)

print()

# ---------------------------------------------------------------------------
# Checkpoint 8 (optional/live): real call_llm() round trip via Ollama
# ---------------------------------------------------------------------------

print("Checkpoint 8 (optional): live call_llm() round trip via Ollama")

try:
    live_prompt = build_prompt(
        query_text="Can a classical Ayurvedic formulation be patented in India?",
        jurisdiction="india",
        classification_result=get_posture_summary(FormulationCategory.CLASSICAL),
        retrieved_chunks=india_chunks,
    )
    live_answer = call_llm(live_prompt)
    check(
        len(live_answer.strip()) > 0,
        "Live call_llm() returned a non-empty response from Ollama",
    )
    # Note: whether llama3 actually reproduces the disclaimer sentence
    # verbatim is model-behavior-dependent, not something build_prompt()
    # controls — print it for manual inspection rather than hard-asserting.
    print(f"  (manual check) disclaimer present in live output: "
          f"{'consult a qualified IP professional' in live_answer}")
    print()
    print("  --- live model output ---")
    print(f"  {live_answer}")
    print("  --------------------------")
except RuntimeError as e:
    print(f"  SKIPPED: {e}")

print()
print(f"Result: {passed}/{passed + failed} checkpoints passed")
