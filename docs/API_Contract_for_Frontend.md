# IP-SAKTI Sahayak — Backend API Contract (for frontend integration)

The full machine-readable contract is in `openapi.json` (exported directly
from the running FastAPI app — always accurate, regenerate anytime with
`uvicorn main:app` then hit `/openapi.json`, or `app.openapi()` in Python).

This note covers the things Swagger/OpenAPI doesn't explain on its own —
read it alongside the spec, not instead of it.

---

## POST /classify

Send the Q1–Q5 answers you have so far (all fields optional — you don't
need to know Q4/Q5 if Q1 was already `true`).

**Important:** questions must be answered *in order*. If a question is
needed to reach a verdict and it's missing, you get a `422` naming which
one:

```json
{ "detail": "Q2 (new clinical evidence) not answered." }
```

Design this as a short wizard — ask Q1, only show Q2 if Q1 was `false`
(and so on), and stop as soon as `classify()` would short-circuit. That
mirrors exactly how the backend tree works, so you'll rarely hit the 422
in normal use — it's mainly a safety net for a skipped/malformed request.

On success (`200`), you get:

```json
{
  "category": "new_drug",
  "label": "New / Non-Classical Drug",
  "ip_posture": "...",
  "abs_posture": "...",
  "prior_art_note": "..."
}
```

`category` is always one of exactly six values:
`classical_medicine`, `new_drug`, `proprietary_medicine`,
`phytopharmaceutical`, `ayurveda_aahar`, `cosmetic`.

---

## POST /query

```json
{
  "query_text": "Can a classical Ayurvedic formulation be patented in India?",
  "jurisdiction": "india",
  "ip_type": null,
  "formulation_category": null,
  "n_results": 5
}
```

**`jurisdiction` is required** and must be exactly `"india"` or
`"international"` (lowercase, no other values) — this is the toggle from
the roadmap. Wrong value → `422`. There is no "both" option; if a user
wants both, send two separate requests. The backend enforces this at the
retrieval layer, not just in the prompt, so answers are genuinely never
blended.

**`formulation_category`, if sent, must be one of the six category
values** listed above (same enum as `/classify`'s `category` field) — send
the value straight from a prior `/classify` response if you have one. Any
other string gets rejected by validation before it ever reaches retrieval.

**`ip_type`, if sent**, narrows by IP category — one of: `patent`,
`trademark`, `gi`, `copyright`, `design`, `plant_variety`, `abs`,
`drug_regulatory`.

### Response

```json
{
  "text": "...",
  "confidence": "high",
  "abstained": false
}
```

**`confidence`** is `"high"`, `"medium"`, or `"low"`. This is a bucketed
retrieval-similarity score, not a calibrated probability — treat it as
"how well-supported is this answer by the corpus," not "how likely is
this to be correct." Good for a UI badge (High/Medium/Low), not for
anything more precise than that.

**`abstained`** is the field to build UI logic around, not string-matching
`text`. When `abstained: true`, `text` is *always* exactly this string,
byte-for-byte:

> "I don't have sufficient information in my reference documents to
> answer this accurately. Please consult official AYUSH/TKDL sources or
> escalate to a human IP facilitator."

Use `abstained` to trigger your escalation-CTA UI ("Talk to a human IP
facilitator") rather than checking `confidence === "low"` directly —
`abstained` is the actual gate the backend uses, and it's guaranteed
consistent with `text` when true.

When `abstained: false`, `text` is the real generated answer and always
ends with this disclaimer sentence (also byte-for-byte, per the system
prompt's rule 5):

> "This is general information, not legal advice. For formal guidance,
> consult a qualified IP professional."

Every substantive answer also embeds inline citations in this exact
format, straight from the retrieved chunk's real metadata:

```
[Source: {document_name}, {section}, Jurisdiction: {jurisdiction}]
```

If you want an "expandable citation" UI (per the roadmap's feature list),
these bracketed citation lines are currently embedded in the plain `text`
string — there's no separate structured `citations` field yet. Flag this
if you need them split out; that would be a small backend addition, not
something you can parse reliably out of free text.

---

## Error shape (both endpoints)

FastAPI's default validation error shape, e.g.:

```json
{
  "detail": [
    { "loc": ["body", "jurisdiction"], "msg": "...", "type": "..." }
  ]
}
```

for Pydantic-level validation failures (bad enum value, missing required
field), versus the plain `{"detail": "..."}` string shape for the
hand-raised `ClassificationError` / bad-jurisdiction cases described
above. Both are `422`.
