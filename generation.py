"""
generation.py — IP-SAKTI Sahayak (SIH26045)
the generation layer that plugs into
confidence.generate_or_abstain() as its `generate_fn`.

Scope : build_prompt() and call_llm() only. This
module does NOT re-implement classification, retrieval, or confidence
gating — it consumes their verified outputs.

Expected call pattern (later, in Phase F's FastAPI layer):

    from retrieval import query_chunks, flatten_query_result
    from classification import get_posture_summary
    from confidence import generate_or_abstain

    raw_results = query_chunks(query_text, jurisdiction, ip_type, formulation_category)
    chunks = flatten_query_result(raw_results)
    top_distance = chunks[0]["distance"] if chunks else float("inf")

    result = generate_or_abstain(
        top_distance,
        lambda: call_llm(build_prompt(query_text, jurisdiction, classification_result, chunks)),
    )
"""

from typing import Optional

import requests

# ---------------------------------------------------------------------------
# The verbatim system prompt template, copied EXACTLY from base_context.txt.
# Only the bracketed placeholders below are substituted — the surrounding
# wording is never reworded, per Phase E scope.
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT_TEMPLATE = """You are IP-SAKTI Sahayak, an assistant that provides information — not
legal advice — on Ayurveda intellectual property and regulatory matters,
using ONLY the provided reference documents.

Rules:
1. Answer using ONLY the context chunks provided below.
2. The user has selected jurisdiction: {jurisdiction}. Answer ONLY using
   context tagged for this jurisdiction. Do NOT blend India and
   international law in a single answer. If the user's question spans
   both, state that clearly and offer to answer for the other
   jurisdiction separately.
3. For every claim, cite the exact source:
   [Source: {{document_name}}, {{section}}, Jurisdiction: {jurisdiction}]
4. If the context does not sufficiently answer the question, respond
   exactly with:
   "I don't have sufficient information in my reference documents to
   answer this accurately. Please consult official AYUSH/TKDL sources
   or escalate to a human IP facilitator."
5. Always end substantive answers with:
   "This is general information, not legal advice. For formal guidance,
   consult a qualified IP professional."
6. Do not use outside knowledge not present in the context below, even
   if you believe you know the answer.

CONTEXT ({jurisdiction} only):
{context_block}

FORMULATION CLASSIFICATION (if known):
{classification_block}

QUESTION:
{question}
"""


# ---------------------------------------------------------------------------
# build_prompt()
# ---------------------------------------------------------------------------

def build_prompt(
    query_text: str,
    jurisdiction: str,
    classification_result: Optional[dict],
    retrieved_chunks: list[dict],
) -> str:
    """
    Assemble the full grounded-generation prompt.

    Args:
        query_text: the user's question, verbatim.
        jurisdiction: "india" | "international" — must match what was
            used to filter retrieval; substituted into the template
            wherever {jurisdiction} appears.
        classification_result: the dict returned by
            classification.get_posture_summary(), or None if the
            formulation hasn't been classified yet.
        retrieved_chunks: a FLAT list of chunk dicts, e.g. the output
            of retrieval.flatten_query_result() — NOT the raw
            ChromaDB batch-shaped query result. Each dict is expected
            to have "text" and "metadata" keys, where metadata has
            "document" and "section".

    Returns:
        The fully assembled prompt string, ready to pass to call_llm().
    """
    context_block = _build_context_block(retrieved_chunks, jurisdiction)
    classification_block = _build_classification_block(classification_result)

    return _SYSTEM_PROMPT_TEMPLATE.format(
        jurisdiction=jurisdiction,
        context_block=context_block,
        classification_block=classification_block,
        question=query_text,
    )


def _build_context_block(retrieved_chunks: list[dict], jurisdiction: str) -> str:
    """
    Render each chunk as its text followed by a citation line built
    STRICTLY from the chunk's real metadata — never hand-written —
    so citation correctness is verifiable against the source data.
    """
    if not retrieved_chunks:
        return "(No matching context chunks were retrieved.)"

    pieces = []
    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {}) or {}
        document = metadata.get("document", "Unknown document")
        section = metadata.get("section", "Unknown section")
        chunk_jurisdiction = metadata.get("jurisdiction", jurisdiction)

        citation = f"[Source: {document}, {section}, Jurisdiction: {chunk_jurisdiction}]"
        pieces.append(f"{chunk.get('text', '')}\n{citation}")

    return "\n\n".join(pieces)


def _build_classification_block(classification_result: Optional[dict]) -> str:
    """
    Render the formulation classification posture summary, or a
    plain "Not yet classified" fallback when none is available.
    """
    if classification_result is None:
        return "Not yet classified."

    label = classification_result.get("label", "Unknown category")
    ip_posture = classification_result.get("ip_posture", "")
    abs_posture = classification_result.get("abs_posture", "")
    prior_art_note = classification_result.get("prior_art_note", "")

    return (
        f"Category: {label}\n"
        f"IP posture: {ip_posture}\n"
        f"ABS posture: {abs_posture}\n"
        f"Prior-art note: {prior_art_note}"
    )


# ---------------------------------------------------------------------------
# call_llm()
# ---------------------------------------------------------------------------
# Thin wrapper around a local Ollama instance running llama3. This is the
# ONLY function in the whole pipeline that changes when swapping to the
# Claude API for final demo polish (per Phase E scope) — build_prompt()
# and everything upstream/downstream of it stays provider-agnostic.

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"


def call_llm(prompt: str) -> str:
    """
    Send `prompt` to a locally running Ollama instance (model: llama3)
    and return the generated text.

    Requires `ollama serve` running locally with llama3 already pulled
    (`ollama pull llama3`) — a one-time local setup step, not something
    this function manages.

    Raises RuntimeError with a clear message if Ollama isn't reachable,
    so failures during dev/testing are obvious rather than silent.
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as e:
        raise RuntimeError(
            "Could not reach Ollama at http://localhost:11434 — "
            "make sure `ollama serve` is running and `ollama pull llama3` "
            "has completed."
        ) from e

    data = response.json()
    return data.get("response", "")
