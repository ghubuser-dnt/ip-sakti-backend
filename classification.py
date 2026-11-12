"""
classification.py — IP-SAKTI Sahayak (SIH26045)
rule-based formulation classification.

Scope : the Q1-Q5 decision tree as a pure-Python
classify() function (NO LLM call), plus a static lookup table mapping
each of the 6 resulting categories to a pre-written IP/ABS posture
summary. Retrieval, ChromaDB, and FastAPI wiring are out of scope here
and live in later phases.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class FormulationCategory(str, Enum):
    CLASSICAL = "classical_medicine"
    NEW_DRUG = "new_drug"
    PROPRIETARY = "proprietary_medicine"
    PHYTOPHARMACEUTICAL = "phytopharmaceutical"
    AYURVEDA_AAHAR = "ayurveda_aahar"
    COSMETIC = "cosmetic"


# ---------------------------------------------------------------------------
# Input schema for the tree
# ---------------------------------------------------------------------------

@dataclass
class ClassificationAnswers:
    """
    Yes/No answers to Q1-Q5, in the order the tree asks them.

    Each field is Optional[bool] so a caller (e.g. the future /classify
    endpoint) can stop asking questions the moment classify() would
    short-circuit — you don't need Q4/Q5 answered if Q1 was "Yes".
    """
    q1_from_first_schedule_text: Optional[bool] = None
    q2_requires_new_clinical_evidence: Optional[bool] = None
    q3_proprietary_blend_marketed_as_medicine: Optional[bool] = None
    q4_extraction_standardized_phytomedicine: Optional[bool] = None
    q5_consumed_as_food_or_supplement: Optional[bool] = None


class ClassificationError(ValueError):
    """Raised when classify() needs an answer that wasn't supplied."""


# ---------------------------------------------------------------------------
# The decision tree itself
# ---------------------------------------------------------------------------

def classify(answers: ClassificationAnswers) -> FormulationCategory:
    """
    Deterministic Q1-Q5 decision tree (see roadmap Phase 0.3). Pure
    Python, no ML/LLM involved — accuracy/auditability over flexibility.

    Question order (each only reached if the previous was answered No):
      Q1: formulation + method drawn directly from a First-Schedule
          classical Ayurvedic text?          -> Yes: Classical Medicine
      Q2: requires new safety/efficacy clinical evidence to market?
                                              -> Yes: New Drug
      Q3: proprietary blend, unique formulation, marketed as medicine?
                                              -> Yes: Proprietary Medicine
      Q4: specific extraction/standardization process, positioned as
          evidence-based phyto-medicine?     -> Yes: Phytopharmaceutical
      Q5: consumed as food / dietary supplement rather than medicine?
                                              -> Yes: Ayurveda-Aahar
      (fallback)                             -> Cosmetic

    Raises ClassificationError if a question needed to reach a verdict
    was left unanswered (None).
    """
    if answers.q1_from_first_schedule_text is None:
        raise ClassificationError("Q1 (first-schedule text) not answered.")
    if answers.q1_from_first_schedule_text:
        return FormulationCategory.CLASSICAL

    if answers.q2_requires_new_clinical_evidence is None:
        raise ClassificationError("Q2 (new clinical evidence) not answered.")
    if answers.q2_requires_new_clinical_evidence:
        return FormulationCategory.NEW_DRUG

    if answers.q3_proprietary_blend_marketed_as_medicine is None:
        raise ClassificationError("Q3 (proprietary blend) not answered.")
    if answers.q3_proprietary_blend_marketed_as_medicine:
        return FormulationCategory.PROPRIETARY

    if answers.q4_extraction_standardized_phytomedicine is None:
        raise ClassificationError("Q4 (standardized extraction) not answered.")
    if answers.q4_extraction_standardized_phytomedicine:
        return FormulationCategory.PHYTOPHARMACEUTICAL

    if answers.q5_consumed_as_food_or_supplement is None:
        raise ClassificationError("Q5 (food/supplement) not answered.")
    if answers.q5_consumed_as_food_or_supplement:
        return FormulationCategory.AYURVEDA_AAHAR

    return FormulationCategory.COSMETIC  # default fallback, no Q6 needed


# ---------------------------------------------------------------------------
# Static lookup table: category -> pre-written IP/ABS posture summary
# ---------------------------------------------------------------------------
# NOTE: these are short, deliberately generic summaries meant to seed the
# generation step (Phase C) — not full legal text. Refine wording against
# the actual India corpus once the data team hands it off.

POSTURE_SUMMARY: dict[FormulationCategory, dict] = {
    FormulationCategory.CLASSICAL: {
        "label": "Classical / Generic Medicine",
        "ip_posture": (
            "Treated as traditional knowledge (TK) already in the public "
            "domain via the authoritative classical text. Barred from "
            "patenting under Patents Act 1970 Section 3(p) since it is not "
            "a new invention. Trademark protection is still available for "
            "the brand name/get-up, not the formulation itself."
        ),
        "abs_posture": (
            "If a biological resource sourced from India is used, ABS "
            "obligations under the Biological Diversity Act, 2002 (as "
            "amended 2023) and the 2024 BDA Rules still apply to "
            "commercial use, regardless of the formulation's TK status."
        ),
        "prior_art_note": (
            "TKDL is the primary defensive tool here — it documents this "
            "TK precisely to defeat any third-party patent claim over it."
        ),
    },
    FormulationCategory.NEW_DRUG: {
        "label": "New / Non-Classical Drug",
        "ip_posture": (
            "Genuine patent potential if the formulation, process, or "
            "indication is novel and non-obvious. Section 3(p) does not "
            "apply since this is not a mere TK restatement — but "
            "patentability still requires clearing novelty/prior-art "
            "checks, including against TKDL, and demonstrating an "
            "inventive step beyond known Ayurvedic practice."
        ),
        "abs_posture": (
            "ABS obligations under the BDA apply if any Indian biological "
            "resource was accessed during R&D, in addition to the "
            "regulatory (clinical evidence) burden under the Drugs and "
            "Cosmetics Act, 1940."
        ),
        "prior_art_note": (
            "A TKDL prior-art search is strongly advisable before filing, "
            "to confirm the 'new' element isn't already documented TK."
        ),
    },
    FormulationCategory.PROPRIETARY: {
        "label": "Patent / Proprietary Medicine",
        "ip_posture": (
            "May combine a trademark-protected brand with a proprietary "
            "formulation. Patent eligibility turns on whether the specific "
            "blend/ratio/process is novel and non-obvious versus classical "
            "TK — a case-by-case, evidence-heavy determination, not a "
            "given just because it's marketed as proprietary."
        ),
        "abs_posture": (
            "ABS obligations under the BDA apply if Indian biological "
            "resources are used in the formulation or its research."
        ),
        "prior_art_note": (
            "TKDL search recommended to test how much of the blend "
            "overlaps with documented classical TK before relying on "
            "'proprietary' as a patentability argument."
        ),
    },
    FormulationCategory.PHYTOPHARMACEUTICAL: {
        "label": "Phytopharmaceutical",
        "ip_posture": (
            "A distinct regulatory category under the Drugs and "
            "Cosmetics Rules for standardized plant-derived drugs backed "
            "by evidence. The standardization/extraction process itself "
            "is often the strongest patentable element, more so than the "
            "underlying plant source, which may already be TK."
        ),
        "abs_posture": (
            "ABS obligations under the BDA apply to sourcing the plant "
            "material; benefit-sharing terms should be settled before "
            "scale-up given the regulatory evidence-generation timeline."
        ),
        "prior_art_note": (
            "TKDL search useful to separate 'known plant use' (TK, "
            "unpatentable) from the 'novel standardized process' (potentially "
            "patentable) components."
        ),
    },
    FormulationCategory.AYURVEDA_AAHAR: {
        "label": "Ayurveda-Aahar / Nutraceutical",
        "ip_posture": (
            "Regulated primarily under FSSAI's Ayurveda Aahara "
            "Regulations rather than as a drug. IP protection typically "
            "routes through trademark (branding) and, where packaging or "
            "product form is distinctive, the Designs Act — not patents, "
            "since it is classified and marketed as food, not medicine."
        ),
        "abs_posture": (
            "ABS obligations under the BDA still apply if an Indian "
            "biological resource is used, independent of the food/drug "
            "classification."
        ),
        "prior_art_note": (
            "TKDL relevance is lower here unless a medicinal claim is also "
            "being made, which would risk reclassification as a drug."
        ),
    },
    FormulationCategory.COSMETIC: {
        "label": "Cosmetic",
        "ip_posture": (
            "Regulated under the Drugs and Cosmetics Act's cosmetics "
            "provisions. IP protection is mainly via trademark (brand) "
            "and Designs Act (packaging/container/product form); patent "
            "potential is limited unless a genuinely novel formulation or "
            "delivery process is involved."
        ),
        "abs_posture": (
            "ABS obligations under the BDA apply if Indian biological "
            "resources are used as active or functional ingredients."
        ),
        "prior_art_note": (
            "TKDL relevance is generally low for cosmetics unless "
            "medicinal/therapeutic claims are made alongside cosmetic use."
        ),
    },
}


def get_posture_summary(category: FormulationCategory) -> dict:
    """Convenience accessor — returns the static posture dict for a category."""
    return POSTURE_SUMMARY[category]
