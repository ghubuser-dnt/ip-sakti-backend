"""
test_retrieval.py 

"Isolation test passes; all filter combinations (jurisdiction alone /
+ip_type / +formulation $contains / all three) return correct mock
chunks only." 

Uses get_by_filter() (metadata-only, via ChromaDB .get()) rather than
query_chunks(), so this test verifies filter correctness directly
without depending on embedding/similarity behavior at all — exactly
what "correct mock chunks only" is asking for. Run directly with
`python3 test_retrieval.py` (no pytest required) against your real
./chroma_store / 'ip_sakti_mock' collection from ingest.py.
"""

from retrieval import get_by_filter


def _ids(result: dict) -> set:
    return set(result["ids"])


def run_checkpoint() -> None:
    failures = []

    # -----------------------------------------------------------------
    # 1. Jurisdiction-isolation test — the non-negotiable one.
    #    Per mock_chunks.py: 6 chunks are jurisdiction="india",
    #    3 are jurisdiction="international". Neither query may return
    #    even one chunk from the other jurisdiction.
    # -----------------------------------------------------------------
    india_ids = _ids(get_by_filter(jurisdiction="india"))
    intl_ids = _ids(get_by_filter(jurisdiction="international"))

    expected_india = {
        "patents_act_sec_3p", "bda_2023_abs_obligations",
        "gi_act_1999_registration", "dc_act_new_drug_definition",
        "fssai_ayurveda_aahara_2022", "copyright_act_1957_originality",
    }
    expected_intl = {
        "trips_art27_patentability", "nagoya_protocol_abs",
        "madrid_system_trademark_filing",
    }

    print(f"[india]         got {len(india_ids)} chunks, expected {len(expected_india)}")
    print(f"[international] got {len(intl_ids)} chunks, expected {len(expected_intl)}")

    if india_ids != expected_india:
        failures.append(f"india filter mismatch: {india_ids} != {expected_india}")
    if intl_ids != expected_intl:
        failures.append(f"international filter mismatch: {intl_ids} != {expected_intl}")
    if india_ids & intl_ids:
        failures.append(f"CROSS-CONTAMINATION between jurisdictions: {india_ids & intl_ids}")

    isolation_ok = not failures
    print(f"[{'PASS' if isolation_ok else 'FAIL'}] jurisdiction isolation "
          f"(india ∩ international = {india_ids & intl_ids or '∅'})")

    # -----------------------------------------------------------------
    # 2. jurisdiction + ip_type
    # -----------------------------------------------------------------
    result = get_by_filter(jurisdiction="india", ip_type="abs")
    expected = {"bda_2023_abs_obligations"}
    ok = _ids(result) == expected
    print(f"[{'PASS' if ok else 'FAIL'}] india + ip_type=abs -> {_ids(result)}")
    if not ok:
        failures.append(f"india+abs mismatch: {_ids(result)} != {expected}")

    result = get_by_filter(jurisdiction="international", ip_type="patent")
    expected = {"trips_art27_patentability"}
    ok = _ids(result) == expected
    print(f"[{'PASS' if ok else 'FAIL'}] international + ip_type=patent -> {_ids(result)}")
    if not ok:
        failures.append(f"intl+patent mismatch: {_ids(result)} != {expected}")

    # -----------------------------------------------------------------
    # 3. jurisdiction + formulation_relevance ($contains)
    # -----------------------------------------------------------------
    result = get_by_filter(jurisdiction="india", formulation_category="new_drug")
    expected = {"bda_2023_abs_obligations", "dc_act_new_drug_definition"}
    ok = _ids(result) == expected
    print(f"[{'PASS' if ok else 'FAIL'}] india + formulation=new_drug -> {_ids(result)}")
    if not ok:
        failures.append(f"india+new_drug mismatch: {_ids(result)} != {expected}")

    result = get_by_filter(jurisdiction="international", formulation_category="proprietary_medicine")
    expected = {"trips_art27_patentability", "madrid_system_trademark_filing"}
    ok = _ids(result) == expected
    print(f"[{'PASS' if ok else 'FAIL'}] international + formulation=proprietary_medicine -> {_ids(result)}")
    if not ok:
        failures.append(f"intl+proprietary mismatch: {_ids(result)} != {expected}")

    # -----------------------------------------------------------------
    # 4. jurisdiction + ip_type + formulation_relevance (all three)
    # -----------------------------------------------------------------
    result = get_by_filter(
        jurisdiction="india", ip_type="drug_regulatory", formulation_category="new_drug"
    )
    expected = {"dc_act_new_drug_definition"}
    ok = _ids(result) == expected
    print(f"[{'PASS' if ok else 'FAIL'}] india + drug_regulatory + new_drug -> {_ids(result)}")
    if not ok:
        failures.append(f"all-three mismatch: {_ids(result)} != {expected}")

    # A combination expected to return nothing (no chunk satisfies all three)
    result = get_by_filter(
        jurisdiction="india", ip_type="patent", formulation_category="ayurveda_aahar"
    )
    ok = _ids(result) == set()
    print(f"[{'PASS' if ok else 'FAIL'}] india + patent + ayurveda_aahar (expect empty) -> {_ids(result)}")
    if not ok:
        failures.append(f"expected-empty mismatch: {_ids(result)}")

    # -----------------------------------------------------------------
    # 5. Invalid jurisdiction must raise, not silently return everything
    # -----------------------------------------------------------------
    try:
        get_by_filter(jurisdiction="martian")
        failures.append("Expected ValueError for invalid jurisdiction, none raised")
        print("[FAIL] invalid jurisdiction guard")
    except ValueError:
        print("[PASS] invalid jurisdiction guard (ValueError raised as expected)")

    # -----------------------------------------------------------------
    print()
    if failures:
        print(f"{len(failures)} CHECK(S) FAILED:")
        for f in failures:
            print(f"  - {f}")
        raise SystemExit(1)
    else:
        print("All filter combinations returned correct mock chunks only. "
              "Jurisdiction isolation holds.")


if __name__ == "__main__":
    run_checkpoint()
