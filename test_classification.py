"""
test_classification.py

"8-10 hand-written example formulations all classify into the expected
category" (per Phase B doc). Plain assert-based script — run directly
with `python3 test_classification.py`, no pytest dependency required,
but it also works fine under pytest if that's already in the env.
"""

from classification import (
    ClassificationAnswers,
    ClassificationError,
    FormulationCategory,
    classify,
    get_posture_summary,
)


# Each case: (label, answers, expected_category)
CASES = [
    (
        "Chyawanprash made per Sharangdhar Samhita, unchanged recipe",
        ClassificationAnswers(q1_from_first_schedule_text=True),
        FormulationCategory.CLASSICAL,
    ),
    (
        "Classical Triphala churna, standard classical-text ratio",
        ClassificationAnswers(q1_from_first_schedule_text=True),
        FormulationCategory.CLASSICAL,
    ),
    (
        "Novel herbo-mineral complex for diabetes, requires fresh clinical trials",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=True,
        ),
        FormulationCategory.NEW_DRUG,
    ),
    (
        "New synthesized Ashwagandha-derivative compound pending Phase II trials",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=True,
        ),
        FormulationCategory.NEW_DRUG,
    ),
    (
        "Branded proprietary joint-pain blend, unique ratio, sold as medicine, no new trials required",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=False,
            q3_proprietary_blend_marketed_as_medicine=True,
        ),
        FormulationCategory.PROPRIETARY,
    ),
    (
        "House-brand digestive tonic, unique in-house formula, marketed as medicinal",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=False,
            q3_proprietary_blend_marketed_as_medicine=True,
        ),
        FormulationCategory.PROPRIETARY,
    ),
    (
        "Standardized Boswellia serrata extract, evidence-based phyto-formulation",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=False,
            q3_proprietary_blend_marketed_as_medicine=False,
            q4_extraction_standardized_phytomedicine=True,
        ),
        FormulationCategory.PHYTOPHARMACEUTICAL,
    ),
    (
        "Standardized Curcumin extract with defined marker-compound assay",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=False,
            q3_proprietary_blend_marketed_as_medicine=False,
            q4_extraction_standardized_phytomedicine=True,
        ),
        FormulationCategory.PHYTOPHARMACEUTICAL,
    ),
    (
        "Herbal wellness drink mix sold as a dietary supplement, not a medicine",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=False,
            q3_proprietary_blend_marketed_as_medicine=False,
            q4_extraction_standardized_phytomedicine=False,
            q5_consumed_as_food_or_supplement=True,
        ),
        FormulationCategory.AYURVEDA_AAHAR,
    ),
    (
        "Herbal face cream with neem and turmeric, applied topically, no medicinal claim",
        ClassificationAnswers(
            q1_from_first_schedule_text=False,
            q2_requires_new_clinical_evidence=False,
            q3_proprietary_blend_marketed_as_medicine=False,
            q4_extraction_standardized_phytomedicine=False,
            q5_consumed_as_food_or_supplement=False,
        ),
        FormulationCategory.COSMETIC,
    ),
]


def run_checkpoint() -> None:
    passed = 0
    for label, answers, expected in CASES:
        result = classify(answers)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        print(f"[{status}] {label}\n         -> got {result.value}, expected {expected.value}")
        assert result == expected, f"Mismatch for: {label}"

    print(f"\n{passed}/{len(CASES)} example formulations classified correctly.")

    # Sanity check: every category in the enum has a posture summary entry.
    for category in FormulationCategory:
        summary = get_posture_summary(category)
        assert "label" in summary and "ip_posture" in summary and "abs_posture" in summary
    print(f"{len(FormulationCategory)}/6 categories have complete posture summaries.")

    # Error-path check: missing answer must raise ClassificationError, not
    # silently guess or fall through.
    try:
        classify(ClassificationAnswers())  # nothing answered
        raise AssertionError("Expected ClassificationError for empty answers")
    except ClassificationError:
        print("Missing-answer guard: PASS (ClassificationError raised as expected)")


if __name__ == "__main__":
    run_checkpoint()
