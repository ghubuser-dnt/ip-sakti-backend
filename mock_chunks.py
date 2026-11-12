from schema import Chunk, ChunkMetadata

MOCK_CHUNKS = [
    Chunk(
        chunk_id="patents_act_sec_3p",
        text="Section 3(p) bars patenting of inventions that are traditional "
             "knowledge or an aggregation/duplication of known properties of "
             "traditionally known components.",
        metadata=ChunkMetadata(
            document="Patents Act, 1970 (as amended)",
            section="Section 3(p)",
            jurisdiction="india",
            ip_type="patent",
            page=12,
            source_url="https://www.indiacode.nic.in/patents-act-1970",
            formulation_relevance=["classical_medicine"],
        ),
    ),
    Chunk(
        chunk_id="bda_2023_abs_obligations",
        text="Any person seeking to access biological resources occurring in "
             "India for research or commercial use must obtain prior approval "
             "from the National Biodiversity Authority and enter into a "
             "benefit-sharing agreement.",
        metadata=ChunkMetadata(
            document="Biological Diversity (Amendment) Act, 2023",
            section="Section 3 - Access and Benefit Sharing",
            jurisdiction="india",
            ip_type="abs",
            page=4,
            source_url="https://egazette.gov.in/biodiversity-amendment-2023",
            formulation_relevance=["classical_medicine", "new_drug"],
        ),
    ),
    Chunk(
        chunk_id="gi_act_1999_registration",
        text="A geographical indication may be registered where the goods "
             "originate from a defined region and possess a quality, "
             "reputation, or characteristic essentially attributable to that "
             "geographical origin.",
        metadata=ChunkMetadata(
            document="Geographical Indications of Goods Act, 1999",
            section="Section 2(e)",
            jurisdiction="india",
            ip_type="gi",
            page=2,
            source_url="https://www.indiacode.nic.in/gi-act-1999",
            formulation_relevance=["classical_medicine"],
        ),
    ),
    Chunk(
        chunk_id="dc_act_new_drug_definition",
        text="A new drug includes a substance requiring evidence of safety "
             "and efficacy through clinical trials before it may be marketed, "
             "even where derived from a plant source.",
        metadata=ChunkMetadata(
            document="Drugs and Cosmetics Act, 1940 (and Rules)",
            section="Rule 122E",
            jurisdiction="india",
            ip_type="drug_regulatory",
            page=45,
            source_url="https://cdsco.gov.in/dc-act-1940",
            formulation_relevance=["new_drug", "phytopharmaceutical"],
        ),
    ),
    Chunk(
        chunk_id="fssai_ayurveda_aahara_2022",
        text="Ayurveda Aahara products are those formulated in accordance "
             "with authoritative texts listed in Schedule A and intended for "
             "consumption as food rather than as medicine.",
        metadata=ChunkMetadata(
            document="FSSAI Ayurveda Aahara Regulations, 2022",
            section="Schedule A",
            jurisdiction="india",
            ip_type="drug_regulatory",
            page=3,
            source_url="https://fssai.gov.in/ayurveda-aahara-2022",
            formulation_relevance=["ayurveda_aahar"],
        ),
    ),
    Chunk(
        chunk_id="trips_art27_patentability",
        text="Patents shall be available for any inventions, whether products "
             "or processes, in all fields of technology, provided they are "
             "new, involve an inventive step, and are capable of industrial "
             "application.",
        metadata=ChunkMetadata(
            document="TRIPS Agreement",
            section="Article 27",
            jurisdiction="international",
            ip_type="patent",
            page=8,
            source_url="https://www.wto.org/trips-agreement",
            formulation_relevance=["new_drug", "proprietary_medicine"],
        ),
    ),
    Chunk(
        chunk_id="nagoya_protocol_abs",
        text="Parties shall take measures to ensure that access to genetic "
             "resources is subject to prior informed consent and that "
             "benefits arising from their utilization are shared fairly.",
        metadata=ChunkMetadata(
            document="Nagoya Protocol",
            section="Article 6",
            jurisdiction="international",
            ip_type="abs",
            page=5,
            source_url="https://www.cbd.int/abs/nagoya-protocol",
            formulation_relevance=["classical_medicine", "new_drug"],
        ),
    ),
    Chunk(
        chunk_id="madrid_system_trademark_filing",
        text="The Madrid System allows a trademark owner to seek protection "
             "in multiple member countries by filing a single international "
             "application through their national or regional trademark "
             "office.",
        metadata=ChunkMetadata(
            document="Madrid System — procedural overview",
            section="Filing Procedure",
            jurisdiction="international",
            ip_type="trademark",
            page=1,
            source_url="https://www.wipo.int/madrid/en",
            formulation_relevance=["proprietary_medicine", "cosmetic"],
        ),
    ),
    # New 9th-slot example showing the "omit entirely" case —
    # a chunk with no formulation ties at all:
    Chunk(
        chunk_id="copyright_act_1957_originality",
        text="Copyright protects original literary works, including written "
             "documentation of a formulation, but does not extend to the "
             "underlying traditional knowledge or method itself.",
        metadata=ChunkMetadata(
            document="Copyright Act, 1957",
            section="Section 13",
            jurisdiction="india",
            ip_type="copyright",
            page=6,
            source_url="https://www.indiacode.nic.in/copyright-act-1957",
            # formulation_relevance omitted — not passed at all, not []
        ),
    ),
]