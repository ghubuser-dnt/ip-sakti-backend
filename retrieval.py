"""
retrieval.py — IP-SAKTI Sahayak (SIH26045)
metadata-filtered retrieval against the mock
ChromaDB collection built in Phase A (ingest.py -> collection
'ip_sakti_mock', persisted at './chroma_store').

Scope: the metadata `where`-clause filter —
jurisdiction required, ip_type optional, formulation_relevance
optional via $contains against the array field — plus a thin
retrieval function that runs similarity search inside that filter.
Classification, generation, and FastAPI endpoints are out of scope
here and live in other phases.
"""

from typing import Optional

import chromadb

COLLECTION_NAME = "ip_sakti_mock"
PERSIST_PATH = "./chroma_store"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Lazily initialized so importing this module (e.g. for tests that only
# need build_where_clause) doesn't force a ChromaDB connection or a
# sentence-transformers model load.
_client = None
_collection = None
_model = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=PERSIST_PATH)
        _collection = _client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def _get_model():
    global _model
    if _model is None:
        # Imported lazily so that importing this module (or calling
        # build_where_clause / get_by_filter, which never touch
        # embeddings) doesn't require sentence-transformers to be
        # installed at all. Only query_chunks() needs it.
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _model


# ---------------------------------------------------------------------------
# The metadata where-clause builder — this is the core Phase C logic
# ---------------------------------------------------------------------------

def build_where_clause(
    jurisdiction: str,
    ip_type: Optional[str] = None,
    formulation_category: Optional[str] = None,
) -> dict:
    """
    Build a ChromaDB `where` filter for jurisdiction-isolated,
    optionally IP-type- and formulation-scoped retrieval.

    - jurisdiction is REQUIRED and always enforced. This is the hard
      isolation boundary between "india" and "international" data —
      there is no way to call this function and get a where-clause
      that omits it, which is what makes isolation a property of the
      filter itself rather than something callers have to remember.
    - ip_type is an optional equality filter (e.g. "patent", "abs").
    - formulation_category is an optional membership check against the
      array-valued formulation_relevance field, using Chroma 1.5.0+'s
      native $contains operator — no boolean-flattening needed. Pass
      a FormulationCategory.value string (e.g. "classical_medicine")
      straight from classify(), no translation layer required.

    Returns a dict ready to pass as ChromaDB's `where` argument.
    """
    if jurisdiction not in ("india", "international"):
        raise ValueError(
            f"Invalid jurisdiction: {jurisdiction!r} "
            "(must be 'india' or 'international')"
        )

    conditions: list[dict] = [{"jurisdiction": {"$eq": jurisdiction}}]

    if ip_type is not None:
        conditions.append({"ip_type": {"$eq": ip_type}})

    if formulation_category is not None:
        conditions.append(
            {"formulation_relevance": {"$contains": formulation_category}}
        )

    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


# ---------------------------------------------------------------------------
# Pure metadata retrieval — no embeddings involved, used for filter
# correctness checks (e.g. the jurisdiction-isolation test) and for any
# case where you want "all chunks matching this filter" rather than a
# similarity-ranked subset.
# ---------------------------------------------------------------------------

def get_by_filter(
    jurisdiction: str,
    ip_type: Optional[str] = None,
    formulation_category: Optional[str] = None,
) -> dict:
    """
    Fetch all chunks matching the metadata filter, ignoring semantic
    similarity entirely. Uses ChromaDB's .get() rather than .query(),
    so no embedding model is needed for this path.
    """
    collection = _get_collection()
    where = build_where_clause(jurisdiction, ip_type, formulation_category)
    return collection.get(where=where, include=["metadatas", "documents"])


# ---------------------------------------------------------------------------
# Real retrieval — embeds the query text and runs similarity search
# restricted to the metadata filter. This is what the generation step
# (later phase) will actually call.
# ---------------------------------------------------------------------------

def query_chunks(
    query_text: str,
    jurisdiction: str,
    ip_type: Optional[str] = None,
    formulation_category: Optional[str] = None,
    n_results: int = 5,
) -> dict:
    """
    Embed query_text and run a similarity search restricted to the
    given metadata filter. jurisdiction is mandatory here too — there
    is no code path in this module that queries without it.
    """
    collection = _get_collection()
    model = _get_model()
    where = build_where_clause(jurisdiction, ip_type, formulation_category)

    query_embedding = model.encode([query_text]).tolist()

    return collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where,
    )


# ---------------------------------------------------------------------------
# Shape normalization — this is where ChromaDB's batch-query result shape
# gets unwrapped, ONCE, in the module that already owns and understands
# that shape. Downstream consumers (Phase E's build_prompt(), future
# FastAPI response formatting, debug scripts, etc.) should use this
# instead of each independently re-deriving the [0]-indexing convention.
# ---------------------------------------------------------------------------

def flatten_query_result(query_result: dict) -> list[dict]:
    """
    Normalize ChromaDB's .query() output (always shaped as one outer
    list-slot per query embedding, even for a single query) into a flat
    list of per-chunk dicts.

    Input shape (from query_chunks()):
        {
            "documents": [[text, text, ...]],
            "metadatas": [[{...}, {...}, ...]],
            "distances": [[0.31, 0.55, ...]],
            "ids": [["chunk_id_1", "chunk_id_2", ...]],
            ...
        }

    Output shape:
        [
            {"chunk_id": "...", "text": "...", "metadata": {...}, "distance": 0.31},
            ...
        ]

    Only unwraps the FIRST query's results (index [0]) — this project
    never issues batched multi-query calls, so that's the only case
    that needs handling. If query_result contains no results at all
    (e.g. an empty ChromaDB response), returns an empty list rather
    than raising.
    """
    documents = (query_result.get("documents") or [[]])[0]
    metadatas = (query_result.get("metadatas") or [[]])[0]
    distances = (query_result.get("distances") or [[]])[0]
    ids = (query_result.get("ids") or [[]])[0]

    flattened = []
    for i, text in enumerate(documents):
        flattened.append({
            "chunk_id": ids[i] if i < len(ids) else None,
            "text": text,
            "metadata": metadatas[i] if i < len(metadatas) else {},
            "distance": distances[i] if i < len(distances) else None,
        })
    return flattened
