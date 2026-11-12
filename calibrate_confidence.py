"""

Purpose: print the ACTUAL top-chunk distances your retrieval returns,
so we set High/Medium/Low thresholds from real numbers instead of
guessing at a "cosine intuition" range that doesn't apply here
(collection uses squared L2, embeddings are not normalized).

How to run:
    1. Make sure this file sits in your ip-sakti-backend folder,
       next to retrieval.py and chroma_store/.
    2. Activate your venv.
    3. python calibrate_confidence.py
    4. Copy the full printed output back to Claude.

This script does NOT modify anything - it only reads and prints.
"""

from retrieval import query_chunks

# --- Queries you'd expect to match a mock chunk WELL (should be "high confidence") ---
# Each of these is written to closely echo one specific chunk in mock_chunks.py,
# so we can see the distance for a genuinely good match.
high_confidence_queries = [
    "Can I patent an invention that is just traditional knowledge?",       # -> patents_act_sec_3p
    "Do I need NBA approval before accessing biological resources in India?",  # -> bda_2023_abs_obligations
    "What makes a product eligible for geographical indication registration?",  # -> gi_act_1999_registration
    "Does a new drug from a plant source need clinical trial evidence?",   # -> dc_act_new_drug_definition
    "Is Ayurveda Aahara classified as food or medicine?",                  # -> fssai_ayurveda_aahara_2022
]

# --- Queries you'd expect to match POORLY (should be "low confidence") ---
# Off-topic, nothing in the 9 mock chunks should be semantically close to these.
low_confidence_queries = [
    "What is the weather like in Mumbai today?",
    "How do I bake a chocolate cake?",
    "What's the best way to train for a marathon?",
    "Can you recommend a good sci-fi movie?",
]


def show_distances(label, queries, jurisdiction):
    print(f"\n{'=' * 60}")
    print(f"{label}")
    print(f"{'=' * 60}")
    for q in queries:
        result = query_chunks(q, jurisdiction=jurisdiction)
        top_distance = result["distances"][0][0]
        top_doc_id = result["ids"][0][0]
        print(f"\nQuery: {q}")
        print(f"  Top chunk id : {top_doc_id}")
        print(f"  Top distance : {top_distance}")


if __name__ == "__main__":
    show_distances("HIGH-CONFIDENCE candidate queries", high_confidence_queries, jurisdiction="india")
    show_distances("LOW-CONFIDENCE candidate queries", low_confidence_queries, jurisdiction="india")
    print(f"\n{'=' * 60}")
    print("Copy everything above back to Claude to set thresholds.")
    print(f"{'=' * 60}")
