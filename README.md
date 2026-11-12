# IP-SAKTI Sahayak — RAG Backend

A citation-grounded retrieval-augmented generation (RAG) backend for an Ayurveda IP and regulatory guidance assistant, built for **Smart India Hackathon 2026, problem statement SIH26045**.

> **Status:** built and verified end to end against a **9-chunk mock corpus**. Integration with the real scraped legal corpus was never completed (see [Status and limitations](#status-and-limitations)).

This repository contains only the **AI/RAG backend**. The frontend, the scraped corpus, and final integration were handled by teammates and are not part of this repo (see [Credits](#credits)).

## What it does

The problem statement asks for more than a chatbot over documents: the assistant has to classify the product first, keep Indian and international law strictly separate, cite its sources, and admit when it doesn't know. This backend implements that Stage-1 core:

```
POST /classify                         POST /query
Q1-Q5 answers                          question + jurisdiction (+ ip_type, formulation_category)
      |                                         |
      v                                         v
 rule-based decision tree        metadata-filtered similarity search (ChromaDB)
 (no LLM)                        jurisdiction filter is mandatory
      |                                         |
      v                                         v
 category + IP/ABS posture        top-chunk distance -> High / Medium / Low
                                                |
                                   Low ----------+---------- High / Medium
                                    |                              |
                          fixed abstention message         grounded prompt -> LLM
                          (LLM never called)               inline citations + disclaimer
```

**Formulation classification (`classification.py`).** A deterministic Q1–Q5 decision tree sorts a product into one of six categories: classical medicine, new drug, proprietary medicine, phytopharmaceutical, Ayurveda-Aahar, or cosmetic. It is plain Python, not an LLM call, because a wrong classification cascades into wrong IP guidance and I wanted the behaviour to be auditable. Each category maps to a static, pre-written IP/ABS posture summary.

**Jurisdiction-isolated retrieval (`retrieval.py`).** Every chunk carries `jurisdiction`, `ip_type`, and `formulation_relevance` metadata. `build_where_clause()` always includes the jurisdiction condition, so there is no code path that queries without it. Isolation is enforced by the filter itself, not by asking the LLM to behave: the model never sees chunks from the other jurisdiction. `ip_type` and `formulation_relevance` (via ChromaDB's `$contains` on an array field) narrow the search further when provided.

**Confidence and abstention (`confidence.py`).** The top chunk's distance is bucketed into High / Medium / Low. A Low result bypasses generation entirely and returns a fixed abstention message; the LLM is not called, by construction. This is a retrieval-support proxy, not a calibrated probability.

**Grounded generation (`generation.py`).** The prompt restricts the model to the retrieved context, requires inline citations in the form `[Source: {document}, {section}, Jurisdiction: {jurisdiction}]` (built from chunk metadata, never hand-written), and requires a closing "not legal advice" disclaimer.

**API (`main.py`, `api_schemas.py`).** FastAPI with strict Pydantic request and response models. Invalid enum values are rejected with 422 before retrieval runs, and an incomplete `/classify` answer set returns a clean 422 naming the missing question instead of a 500.

## Repository layout

| File | Purpose |
|---|---|
| `classification.py` | Q1–Q5 decision tree and posture-summary lookup table |
| `retrieval.py` | `where`-clause builder, filtered similarity search, result flattening |
| `confidence.py` | Distance-to-confidence bucketing and the abstention gate |
| `generation.py` | Prompt assembly and LLM call (local Ollama) |
| `run_query.py` | Retrieve → gate → generate/abstain wiring |
| `main.py`, `api_schemas.py` | FastAPI app and API payload schemas |
| `schema.py` | Pydantic models for stored chunks |
| `mock_chunks.py`, `ingest.py` | The 9 mock chunks and the script that loads them into ChromaDB |
| `calibrate_confidence.py` | Prints real top-chunk distances for threshold calibration |
| `test_*.py` | Checkpoint tests for each stage |
| `docs/` | API contract (`openapi.json` + notes) and the chunk schema spec written for teammates |
| `labeled_calibration.py` | Labeled ground-truth queries, including deliberately ambiguous ones, for checking whether confidence buckets match actual correctness; writes a CSV |
## Setup and run

Requires Python 3.10+ and [Ollama](https://ollama.com) for local generation.

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate  (Git Bash: source venv/Scripts/activate)
pip install -r requirements.txt

python ingest.py                  # builds ./chroma_store from the mock chunks
                                  # (first run downloads the all-MiniLM-L6-v2 embedding model)

ollama pull llama3                # one-time
ollama serve                      # leave running in another terminal

uvicorn main:app --reload         # then open http://127.0.0.1:8000/docs
```

To rebuild the vector store from scratch, delete `chroma_store/` and re-run `python ingest.py`.

### Example requests

```bash
curl -X POST http://127.0.0.1:8000/classify -H "Content-Type: application/json" \
  -d '{"q1_from_first_schedule_text": false, "q2_requires_new_clinical_evidence": true}'
# -> category "new_drug" + label, ip_posture, abs_posture, prior_art_note

curl -X POST http://127.0.0.1:8000/query -H "Content-Type: application/json" \
  -d '{"query_text": "Can a classical Ayurvedic formulation be patented in India?", "jurisdiction": "india"}'
# -> {"text": "...cited answer...", "confidence": "medium", "abstained": false}
```

An out-of-scope query returns `"abstained": true`, `"confidence": "low"`, and the exact abstention message, without any call to the LLM. Request and response details are in `docs/API_Contract_for_Frontend.md` and `docs/openapi.json`.

### Tests

```bash
python test_classification.py     # 10 formulation cases, no services needed
python test_confidence.py         # 18 checks on bucketing and the abstention gate
python test_generation.py         # prompt structure + gate wiring; live Ollama check is skipped if Ollama isn't running
python test_retrieval.py          # jurisdiction isolation and filter combinations; run python ingest.py first
```

## Status and limitations

This was developed **mock-first**: every stage was built and tested against 9 hand-written chunks while a teammate prepared the real corpus. The real corpus was never delivered, so real-data integration is pending. Specifically:

- **The mock chunks are illustrative paraphrases, not verbatim statutory text**, and their `source_url` values are placeholders that may not resolve. Nothing the system says from this repo should be treated as legal content.
- **Confidence thresholds are calibrated on the mock corpus only.** The cutoffs in `confidence.py` (0.7 / 1.2, squared-L2 distance with unnormalized embeddings) came from `calibrate_confidence.py` runs on 9 chunks and will need recalibrating on a real corpus. `test_confidence.py` and `test_retrieval.py` also contain mock-specific fixtures.
- **Generation uses a local Llama 3 via Ollama.** Swapping to the Claude API means changing only `call_llm()`, but that swap was not done. Citation format and the closing disclaimer are required by the prompt, not enforced in code, so they depend on model behaviour.
- **Citations are inline in the answer text**, not returned as a structured field.
- **Posture summaries in `classification.py` are generic, hand-written, and not reviewed by a legal professional.**
- **`ip_type` is not validated at the API layer.** An unknown value matches no chunks and results in an abstention.
- **Stage 1 only.** Not implemented from the problem statement: multilingual support (Bhashini), the TKDL prior-art pointer and ABS helper flow, the human-escalation UI, and the later knowledge-graph / agentic / paid-source stages. No auth or CORS configuration.

This is general information tooling, not legal advice.

## Credits

Built by **Laksh Varshney** (AI/RAG backend: classification tree, filtered retrieval, confidence/abstention, generation, FastAPI endpoints) as part of a team for SIH 2026.

Teammates, who worked on parts that are not in this repository:

- **Atharva Raghuvanshi & Mohd Tabish Irfan**: data collection and the vector-store corpus
- **Aduitiya Srivastava**: frontend UI/UX
- **Lakshay Beniwal**: integration

Thanks to them for their work on the rest of the project. The chunk schema in `docs/Chunk_Schema_Spec_for_Data_Team.md` was written as the contract between the backend and the data side.
