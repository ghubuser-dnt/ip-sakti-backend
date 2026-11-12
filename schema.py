from pydantic import BaseModel
from typing import Literal, Optional

class ChunkMetadata(BaseModel):
    document: str
    section: str
    jurisdiction: Literal["india", "international"]
    ip_type: Literal[
        "patent", "trademark", "gi", "copyright",
        "design", "plant_variety", "abs", "drug_regulatory"
    ]
    page: int
    source_url: str

    # Native array field (Chroma 1.5.0+). Omit entirely if a chunk has
    # no formulation ties — empty lists are NOT allowed by Chroma.
    # Values match classification.py's FormulationCategory enum exactly
    # (.value strings), so a classify() result can be passed straight
    # into a retrieval filter with no translation layer.
    formulation_relevance: Optional[list[Literal[
        "classical_medicine", "new_drug", "proprietary_medicine",
        "phytopharmaceutical", "ayurveda_aahar", "cosmetic"
    ]]] = None


class Chunk(BaseModel):
    chunk_id: str
    text: str
    metadata: ChunkMetadata