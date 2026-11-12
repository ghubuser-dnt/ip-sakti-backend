# IP-SAKTI Sahayak — Chunk Schema Spec (for data/scraping handoff)

This is the exact shape every scraped-and-cleaned chunk needs to be in
before it can be ingested into the vector store. It's a direct
translation of `schema.py`'s `Chunk` / `ChunkMetadata` Pydantic models —
those are the actual validation the backend runs, this doc just explains
them and flags the specific mistakes that have already happened once on
this project so they don't happen again on your side.

## Required shape

```json
{
  "chunk_id": "patents_act_sec_3p",
  "text": "Section 3(p) bars patenting of inventions that are traditional knowledge...",
  "metadata": {
    "document": "Patents Act, 1970 (as amended)",
    "section": "Section 3(p)",
    "jurisdiction": "india",
    "ip_type": "patent",
    "page": 12,
    "source_url": "https://www.indiacode.nic.in/patents-act-1970",
    "formulation_relevance": ["classical_medicine"]
  }
}
```

## Field-by-field rules

| Field | Type | Rules |
|---|---|---|
| `chunk_id` | string | Should be unique and stable — used as the ChromaDB record ID. A short slug (e.g. `bda_2023_abs_obligations`) is easier to debug than a random UUID. |
| `text` | string | The actual chunk content that gets embedded and shown to the LLM as context. |
| `document` | string | Full document name, e.g. `"Biological Diversity (Amendment) Act, 2023"`. |
| `section` | string | Section/clause identifier, e.g. `"Section 3 - Access and Benefit Sharing"`. This is what appears in the citation line the LLM outputs, so it should be human-readable, not an internal code. |
| `jurisdiction` | string | **Exactly** `"india"` or `"international"` — lowercase, no variants (`"India"`, `"IN"`, etc. will be rejected). This is a hard `Literal` type; anything else fails validation. |
| `ip_type` | string | **Exactly one of:** `patent`, `trademark`, `gi`, `copyright`, `design`, `plant_variety`, `abs`, `drug_regulatory`. Also a hard `Literal` — no free text. |
| `page` | integer | Not a string — `12`, not `"12"`. |
| `source_url` | string | Full URL to the original source document. |
| `formulation_relevance` | list of strings, **optional** | See below — this is the field most likely to cause problems if the rule isn't followed. |

## `formulation_relevance` — read this carefully

This field says which formulation-classification categories (from the
Q1–Q5 decision tree) this chunk is relevant to. It has one rule that's
easy to get wrong:

**If a chunk has no formulation ties at all, omit the field entirely —
do not send an empty list.**

```json
// CORRECT — field omitted entirely
{
  "chunk_id": "copyright_act_1957_originality",
  "text": "...",
  "metadata": {
    "document": "Copyright Act, 1957",
    "section": "Section 13",
    "jurisdiction": "india",
    "ip_type": "copyright",
    "page": 6,
    "source_url": "https://www.indiacode.nic.in/copyright-act-1957"
  }
}
```

```json
// WRONG — will be rejected by ChromaDB at ingest time
{
  "metadata": {
    ...,
    "formulation_relevance": []
  }
}
```

ChromaDB doesn't allow empty array-valued metadata fields, so if your
export step defaults to `[]` for "no relevance found" rather than
dropping the key, ingestion will fail on those chunks. If you're
generating this from a dataframe/CSV pipeline, make sure the export step
explicitly checks "is this list empty?" and drops the key rather than
serializing `[]`.

**When `formulation_relevance` IS present, every value must exactly
match one of these six strings** (case-sensitive, exact spelling):

```
classical_medicine
new_drug
proprietary_medicine
phytopharmaceutical
ayurveda_aahar
cosmetic
```

A chunk can list more than one if it's relevant to multiple categories:

```json
"formulation_relevance": ["classical_medicine", "new_drug"]
```

This exact mismatch (schema listing slightly different strings than the
classification categories actually used) has already happened once on
this project and was caught and fixed — so if your extraction pipeline
derives these tags with any fuzzy matching, LLM tagging, or hand-typing,
double check the output against this exact list before handoff. A typo
here won't throw an obvious error — it'll just mean that chunk silently
never gets returned when someone filters retrieval by that formulation
category.

## Before sending a batch over

If at all possible, validate your chunks against the real Pydantic model
before handoff rather than after — this catches every rule above in one
pass instead of one failed ingest at a time. If you have Python access to
`schema.py`, this is literally:

```python
from schema import Chunk

for raw_chunk in your_scraped_chunks:
    Chunk(**raw_chunk)  # raises a clear error naming the exact bad field
```

If that's not convenient on your end, sending a small sample batch (5–10
chunks) first so it can be validated on the backend side before you run
the full corpus through your pipeline is a reasonable alternative.
