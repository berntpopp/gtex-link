"""Real GTEx API response fixtures for testing."""

from typing import Any

# Real GTEx gene search response example
GENE_SEARCH_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated",
            "end": 43125364,
            "entrezGeneId": 672,
            "gencodeId": "ENSG00000012048.22",
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": "BRCA1",
            "geneSymbolUpper": "BRCA1",
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 43044295,
            "strand": "-",
            "tss": 43125364,
        },
        {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated, pseudogene 1",
            "end": 43125509,
            "entrezGeneId": None,
            "gencodeId": "ENSG00000283441.1",
            "gencodeVersion": "v26",
            "geneStatus": "KNOWN",
            "geneSymbol": "BRCA1P1",
            "geneSymbolUpper": "BRCA1P1",
            "geneType": "processed_pseudogene",
            "genomeBuild": "GRCh38",
            "start": 43125280,
            "strand": "-",
            "tss": 43125509,
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 2},
}

# Real GTEx median gene expression response
MEDIAN_GENE_EXPRESSION_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:0001911",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "median": 12.5436,
            "numSamples": 183,
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
            "unit": "TPM",
        },
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:0001134",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "median": 8.2147,
            "numSamples": 432,
            "tissueSiteDetailId": "Muscle_Skeletal",
            "unit": "TPM",
        },
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:0002046",
            "gencodeId": "ENSG00000012048.22",
            "geneSymbol": "BRCA1",
            "median": 15.7893,
            "numSamples": 208,
            "tissueSiteDetailId": "Thyroid",
            "unit": "TPM",
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 3},
}


# Real GTEx tissue site details response
TISSUE_SITE_DETAILS_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "colorHex": "#FF6600",
            "tissueSiteDetail": "Adipose - Subcutaneous",
            "tissueSiteDetailAbbr": "ADPSBQ",
            "tissueSiteDetailId": "Adipose_Subcutaneous",
            "tissueSiteOntologyId": "UBERON:0002190",
        },
        {
            "colorHex": "#FFAA00",
            "tissueSiteDetail": "Adipose - Visceral (Omentum)",
            "tissueSiteDetailAbbr": "ADPVSC",
            "tissueSiteDetailId": "Adipose_Visceral_Omentum",
            "tissueSiteOntologyId": "UBERON:0003688",
        },
        {
            "colorHex": "#33AADD",
            "tissueSiteDetail": "Adrenal Gland",
            "tissueSiteDetailAbbr": "ADRNLG",
            "tissueSiteDetailId": "Adrenal_Gland",
            "tissueSiteOntologyId": "UBERON:0002369",
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 3},
}

# Real GTEx top expressed genes response
TOP_EXPRESSED_GENES_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "gencodeId": "ENSG00000210082.2",
            "geneSymbol": "MT-RNR2",
            "medianTpm": 89543.2,
            "tissueSiteDetailId": "Whole_Blood",
        },
        {
            "gencodeId": "ENSG00000211459.2",
            "geneSymbol": "MT-RNR1",
            "medianTpm": 67832.1,
            "tissueSiteDetailId": "Whole_Blood",
        },
        {
            "gencodeId": "ENSG00000198888.2",
            "geneSymbol": "MT-ND1",
            "medianTpm": 45621.7,
            "tissueSiteDetailId": "Whole_Blood",
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 3},
}

# Real GTEx variant response
VARIANT_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "alleleFrequency": 0.295918,
            "alt": "C",
            "chromosome": "chr17",
            "numAltPerSite": 1,
            "position": 43051071,
            "ref": "T",
            "rsId": "rs8176318",
            "variantId": "chr17_43051071_T_C_b38",
        },
        {
            "alleleFrequency": 0.142857,
            "alt": "A",
            "chromosome": "chr17",
            "numAltPerSite": 1,
            "position": 43063873,
            "ref": "G",
            "rsId": "rs3092856",
            "variantId": "chr17_43063873_G_A_b38",
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 2},
}

# Real GTEx eGenes response
EGENES_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "geneSymbol": "BRCA1",
            "gencodeId": "ENSG00000012048.22",
            "numSignificantVariants": 234,
            "pValueThreshold": 1.2e-5,
            "qValue": 0.023,
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
        },
        {
            "geneSymbol": "TP53",
            "gencodeId": "ENSG00000141510.17",
            "numSignificantVariants": 156,
            "pValueThreshold": 1.8e-5,
            "qValue": 0.034,
            "tissueSiteDetailId": "Breast_Mammary_Tissue",
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 2},
}

# Real GTEx subject response
SUBJECT_RESPONSE: dict[str, Any] = {
    "data": [
        {
            "ageBracket": "60-69",
            "bmi": 28.4,
            "deathClassification": 0,
            "hardyScale": "0",
            "sex": "M",
            "subjectId": "GTEX-1117F",
        },
        {
            "ageBracket": "50-59",
            "bmi": 32.1,
            "deathClassification": 1,
            "hardyScale": "2",
            "sex": "F",
            "subjectId": "GTEX-111CU",
        },
    ],
    "pagingInfo": {"numberOfPages": 1, "page": 0, "maxItemsPerPage": 250, "totalNumberOfItems": 2},
}

# Real GTEx service info response
SERVICE_INFO_RESPONSE: dict[str, Any] = {
    "id": "gtex-portal-api",
    "name": "GTEx Portal API", 
    "version": "2.0.0",
    "organization": {
        "name": "Broad Institute",
        "url": "https://www.broadinstitute.org"
    },
    "title": "GTEx Portal API"
}

# Error response examples
ERROR_RESPONSES: dict[str, dict[str, Any]] = {
    "validation_error": {
        "detail": [
            {
                "loc": ["query_params", "itemsPerPage"],
                "msg": "ensure this value is less than or equal to 1000",
                "type": "value_error.number.not_le",
                "ctx": {"limit_value": 1000},
            }
        ]
    },
    "not_found": {"detail": "Gene not found"},
    "server_error": {"detail": "Internal server error"},
}

# Test data for different scenarios
TEST_GENE_SYMBOLS: list[str] = ["BRCA1", "BRCA2", "TP53", "EGFR", "MYC", "PIK3CA", "KRAS", "PTEN"]

TEST_GENCODE_IDS: list[str] = [
    "ENSG00000012048.22",  # BRCA1
    "ENSG00000139618.14",  # BRCA2
    "ENSG00000141510.17",  # TP53
    "ENSG00000146648.24",  # EGFR
]

TEST_VARIANT_IDS: list[str] = [
    "chr17_43051071_T_C_b38",
    "chr17_43063873_G_A_b38",
    "chr13_32315474_G_T_b38",
    "chr13_32316461_A_G_b38",
]

TEST_TISSUE_IDS: list[str] = [
    "Whole_Blood",
    "Breast_Mammary_Tissue",
    "Muscle_Skeletal",
    "Brain_Cortex",
    "Liver",
    "Lung",
]

# Large dataset for performance testing
LARGE_GENE_LIST: list[str] = [f"ENSG{i:011d}" for i in range(1000)]

# Edge case test data
EDGE_CASE_DATA: dict[str, Any] = {
    "empty_response": {
        "data": [],
        "pagingInfo": {
            "numberOfPages": 0,
            "page": 0,
            "maxItemsPerPage": 250,
            "totalNumberOfItems": 0,
        },
    },
    "single_item_response": {
        "data": [
            {
                "chromosome": "chrX",
                "dataSource": "GENCODE",
                "description": None,  # Test null description
                "end": 154531,
                "entrezGeneId": None,  # Test null entrez ID
                "gencodeId": "ENSG00000000003.15",
                "gencodeVersion": "v26",
                "geneStatus": "KNOWN",
                "geneSymbol": "TSPAN6",
                "geneSymbolUpper": "TSPAN6",
                "geneType": "protein_coding",
                "genomeBuild": "GRCh38",
                "start": 100627,
                "strand": "-",
                "tss": 154531,
            }
        ],
        "pagingInfo": {
            "numberOfPages": 1,
            "page": 0,
            "maxItemsPerPage": 250,
            "totalNumberOfItems": 1,
        },
    },
    "max_pagination": {
        "data": [],
        "pagingInfo": {
            "numberOfPages": 999,
            "page": 998,
            "maxItemsPerPage": 1000,
            "totalNumberOfItems": 999000,
        },
    },
}
