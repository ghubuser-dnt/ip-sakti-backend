"""
Labeled calibration script.

Extends calibrate_confidence.py with GROUND TRUTH: each query now has
an expected_chunk_id (or None, meaning "should abstain / no chunk
should match"). This is what's needed to actually validate a
calibration metric (ECE / Brier score) — confidence_bucket() alone
tells you the bucket, but calibration needs to know whether the top
result was CORRECT, not just what bucket it landed in.

Includes deliberately AMBIGUOUS queries (plausible-but-wrong matches)
— without these, every query is either obviously-right or
obviously-wrong, and a trivial system looks perfectly calibrated by
accident. The ambiguous cases are where calibration actually gets
tested.

How to run:
    1. Make sure this file sits in your ip-sakti-backend folder,
       next to retrieval.py, confidence.py, and chroma_store/.
    2. Activate your venv.
    3. python labeled_calibration.py
    4. Copy the full printed output back to Claude, or keep the CSV
       (labeled_calibration_results.csv) for the eval harness's own
       test data later — this is meant to double as that fixture.

This script does NOT modify anything - it only reads, queries, and
writes one output CSV.
"""

import csv

from confidence import confidence_bucket, ConfidenceLevel
from retrieval import query_chunks

# --- Ground-truth labeled set --------------------------------------------
# One entry per mock chunk (clear positive), a few clearly-off-topic
# negatives (expected_chunk_id=None -> should abstain), and a handful
# of AMBIGUOUS cases where a plausible-but-wrong chunk could be
# returned with deceptively high confidence.
#
# expected_chunk_id=None means: no chunk in the corpus should be
# considered a correct answer to this query (an out-of-scope /
# should-abstain case), NOT "we don't know the answer."

LABELED_QUERIES = [
    # --- Clear positives: one per mock chunk (india) ---
    {
        "query": "Can I patent an invention that is just traditional knowledge?",
        "expected_chunk_id": "patents_act_sec_3p",
        "jurisdiction": "india",
    },
    {
        "query": "Do I need NBA approval before accessing biological resources in India?",
        "expected_chunk_id": "bda_2023_abs_obligations",
        "jurisdiction": "india",
    },
    {
        "query": "What makes a product eligible for geographical indication registration?",
        "expected_chunk_id": "gi_act_1999_registration",
        "jurisdiction": "india",
    },
    {
        "query": "Does a new drug from a plant source need clinical trial evidence?",
        "expected_chunk_id": "dc_act_new_drug_definition",
        "jurisdiction": "india",
    },
    {
        "query": "Is Ayurveda Aahara classified as food or medicine?",
        "expected_chunk_id": "fssai_ayurveda_aahara_2022",
        "jurisdiction": "india",
    },
    {
        "query": "Does copyright protect the underlying traditional knowledge in a formulation?",
        "expected_chunk_id": "copyright_act_1957_originality",
        "jurisdiction": "india",
    },
    # --- Clear positives: one per mock chunk (international) ---
    {
        "query": "What are the basic patentability requirements under TRIPS?",
        "expected_chunk_id": "trips_art27_patentability",
        "jurisdiction": "international",
    },
    {
        "query": "Does the Nagoya Protocol require prior informed consent for genetic resources?",
        "expected_chunk_id": "nagoya_protocol_abs",
        "jurisdiction": "international",
    },
    {
        "query": "Can I file one trademark application to cover multiple countries?",
        "expected_chunk_id": "madrid_system_trademark_filing",
        "jurisdiction": "international",
    },
    # --- Clear negatives: off-topic, should abstain ---
    {
        "query": "What is the weather like in Mumbai today?",
        "expected_chunk_id": None,
        "jurisdiction": "india",
    },
    {
        "query": "How do I bake a chocolate cake?",
        "expected_chunk_id": None,
        "jurisdiction": "india",
    },
    {
        "query": "What's the best way to train for a marathon?",
        "expected_chunk_id": None,
        "jurisdiction": "india",
    },
    {
        "query": "Can you recommend a good sci-fi movie?",
        "expected_chunk_id": None,
        "jurisdiction": "international",
    },
    # --- Ambiguous / plausible-but-wrong: the cases that actually
    #     test calibration, not just bucket-threshold placement ---
    {
        # Both bda_2023_abs_obligations and nagoya_protocol_abs cover
        # ABS/prior-informed-consent — this could plausibly match the
        # WRONG one if phrased generically enough.
        "query": "What are the requirements for benefit-sharing when using genetic resources?",
        "expected_chunk_id": "bda_2023_abs_obligations",
        "jurisdiction": "india",
    },
    {
        # Trademark-shaped question, but jurisdiction=india — the only
        # india trademark-adjacent content is thin, so this could
        # plausibly pull in madrid_system_trademark_filing (wrong
        # jurisdiction) or gi_act (wrong ip_type) with unwarranted
        # confidence.
        "query": "How do I register a trademark for my Ayurvedic brand?",
        "expected_chunk_id": None,  # no india-trademark chunk exists in this mock set
        "jurisdiction": "india",
    },
    {
        # dc_act_new_drug_definition mentions clinical trials; a
        # classical-medicine question phrased around "evidence" could
        # plausibly misfire onto it instead of patents_act_sec_3p.
        "query": "What evidence is needed to market a classical Ayurvedic medicine?",
        "expected_chunk_id": "patents_act_sec_3p",
        "jurisdiction": "india",
    },
]


def run_labeled_calibration():
    rows = []

    print(f"{'=' * 70}")
    print(f"Running {len(LABELED_QUERIES)} labeled queries")
    print(f"{'=' * 70}")

    for item in LABELED_QUERIES:
        result = query_chunks(item["query"], jurisdiction=item["jurisdiction"])

        # query_chunks() always returns Chroma's batch shape — [0] is
        # the first (only) query's results. No results at all -> treat
        # as an implicit "abstain" match (top_id=None, distance=inf),
        # matching how confidence.py's should_abstain path is reached
        # via run_query.py's own float("inf") convention on empty results.
        ids = result.get("ids") or [[]]
        distances = result.get("distances") or [[]]

        top_id = ids[0][0] if ids[0] else None
        top_distance = distances[0][0] if distances[0] else float("inf")

        bucket = confidence_bucket(top_distance)

        # Correctness means two different things depending on the case:
        # - expected_chunk_id is a real id: correct = retrieval got that
        #   exact chunk.
        # - expected_chunk_id is None (should-abstain case): Chroma ALWAYS
        #   returns a top-k match regardless of quality — there is no
        #   "empty result" case here. So correctness for these rows means
        #   "the confidence bucket correctly signals LOW / don't trust
        #   this", NOT "top_id happened to be None". Comparing top_id to
        #   None directly would mislabel every correctly-low-confidence
        #   off-topic query as a miss.
        if item["expected_chunk_id"] is None:
            is_correct = (bucket == ConfidenceLevel.LOW)
        else:
            is_correct = (top_id == item["expected_chunk_id"])

        rows.append({
            "query": item["query"],
            "jurisdiction": item["jurisdiction"],
            "expected_chunk_id": item["expected_chunk_id"],
            "top_chunk_id": top_id,
            "top_distance": top_distance,
            "confidence_bucket": bucket.value,
            "is_correct": is_correct,
        })

        status = "OK " if is_correct else "MISS"
        print(f"[{status}] ({bucket.value:6s}, dist={top_distance:.3f}) "
              f"{item['query']}")
        print(f"       expected={item['expected_chunk_id']!r}  got={top_id!r}")

    # --- Per-bucket accuracy summary — the actual calibration signal ---
    print(f"\n{'=' * 70}")
    print("Accuracy per confidence bucket (this is what ECE/Brier consume)")
    print(f"{'=' * 70}")

    from collections import defaultdict
    bucket_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        b = row["confidence_bucket"]
        bucket_stats[b]["total"] += 1
        if row["is_correct"]:
            bucket_stats[b]["correct"] += 1

    for bucket in ("high", "medium", "low"):
        stats = bucket_stats.get(bucket, {"correct": 0, "total": 0})
        if stats["total"] == 0:
            print(f"  {bucket:6s}: (no queries landed in this bucket)")
            continue
        acc = stats["correct"] / stats["total"]
        print(f"  {bucket:6s}: {stats['correct']}/{stats['total']} correct "
              f"({acc:.0%}) — well-calibrated if this roughly tracks "
              f"'high' being closer to 100% than 'low'")

    # --- Write CSV for later reuse (eval harness test fixture) ---
    out_path = "labeled_calibration_results.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {out_path}")
    print("Copy the full output above back to Claude, or keep the CSV —")
    print("this same labeled set doubles as calibration-metric test data.")


if __name__ == "__main__":
    run_labeled_calibration()
