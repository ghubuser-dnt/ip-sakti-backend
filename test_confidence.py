"""
test_confidence.py — IP-SAKTI Sahayak (SIH26045)

Verifies:
1. confidence_bucket() sorts real calibrated distances into the right
   bucket (High / Medium / Low).
2. generate_or_abstain() reaches the generation path on a High-
   confidence distance (fake LLM call happens, gets counted).
3. generate_or_abstain() returns ABSTENTION_MESSAGE byte-for-byte on a
   Low-confidence distance, WITHOUT calling the (fake) LLM at all.

Uses a fake generate_fn (no real Claude/Ollama call) so this test runs
instantly, with zero API cost, and proves the gating logic on its own
merits — independent of whether the actual LLM client works.
"""

from confidence import (
    ConfidenceLevel,
    ABSTENTION_MESSAGE,
    confidence_bucket,
    generate_or_abstain,
)

passed = 0
failed = 0


def check(label, condition):
    global passed, failed
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if condition:
        passed += 1
    else:
        failed += 1


# --- Part 1: bucket sorting against real observed distances ---
# (from calibrate_confidence.py output against the real mock collection)
print("=" * 60)
print("Part 1: confidence_bucket() sorting")
print("=" * 60)

check("0.307 (fssai match) -> HIGH",
      confidence_bucket(0.307) is ConfidenceLevel.HIGH)
check("0.390 (dc_act match) -> HIGH",
      confidence_bucket(0.390) is ConfidenceLevel.HIGH)
check("0.653 (bda match) -> HIGH",
      confidence_bucket(0.653) is ConfidenceLevel.HIGH)
check("0.656 (gi_act match) -> HIGH",
      confidence_bucket(0.656) is ConfidenceLevel.HIGH)
check("0.917 (patents_act paraphrase) -> MEDIUM",
      confidence_bucket(0.917) is ConfidenceLevel.MEDIUM)
check("1.630 (off-topic: sci-fi) -> LOW",
      confidence_bucket(1.630) is ConfidenceLevel.LOW)
check("1.924 (off-topic: cake) -> LOW",
      confidence_bucket(1.924) is ConfidenceLevel.LOW)

# Boundary edge cases
check("exactly 0.7 -> HIGH (inclusive)",
      confidence_bucket(0.7) is ConfidenceLevel.HIGH)
check("exactly 1.2 -> MEDIUM (inclusive)",
      confidence_bucket(1.2) is ConfidenceLevel.MEDIUM)
check("just above 1.2 -> LOW",
      confidence_bucket(1.2001) is ConfidenceLevel.LOW)


# --- Part 2: generate_or_abstain() checkpoint cases ---
print("\n" + "=" * 60)
print("Part 2: generate_or_abstain() checkpoint")
print("=" * 60)

llm_call_count = {"n": 0}


def fake_generate_fn():
    """Stands in for the real Claude/Ollama call in later phases."""
    llm_call_count["n"] += 1
    return "This is a fake grounded answer with citations."


# Checkpoint case A: HIGH confidence -> generation path IS reached
llm_call_count["n"] = 0
result_high = generate_or_abstain(0.307, fake_generate_fn)

check("High-confidence: reaches generation (fake LLM called once)",
      llm_call_count["n"] == 1)
check("High-confidence: result not abstained",
      result_high["abstained"] is False)
check("High-confidence: bucket is HIGH",
      result_high["confidence"] is ConfidenceLevel.HIGH)
check("High-confidence: text is the fake generated text",
      result_high["text"] == "This is a fake grounded answer with citations.")

# Checkpoint case B: LOW confidence -> hard abstention, ZERO LLM calls
llm_call_count["n"] = 0
result_low = generate_or_abstain(1.924, fake_generate_fn)

check("Low-confidence: fake LLM NEVER called (zero LLM calls)",
      llm_call_count["n"] == 0)
check("Low-confidence: result IS abstained",
      result_low["abstained"] is True)
check("Low-confidence: bucket is LOW",
      result_low["confidence"] is ConfidenceLevel.LOW)
check("Low-confidence: text matches ABSTENTION_MESSAGE byte-for-byte",
      result_low["text"] == ABSTENTION_MESSAGE)


# --- Summary ---
print("\n" + "=" * 60)
total = passed + failed
print(f"RESULT: {passed}/{total} checks passed")
print("=" * 60)
if failed == 0:
    print("Phase D checkpoint reached: high-confidence query reaches")
    print("generation, low-confidence query abstains with zero LLM calls.")
