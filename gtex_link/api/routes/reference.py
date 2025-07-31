"""Reference data API routes (genes, transcripts, exons)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    ErrorResponse,
    GencodeVersion,
    GeneRequest,
    GenomeBuild,
    PaginatedGeneResponse,
    PaginatedTranscriptResponse,
    TranscriptRequest,
)

from gtex_link.services.gtex_service import GTExService
from structlog.typing import FilteringBoundLogger

from .dependencies import LoggerDep, GTExServiceDep

router = APIRouter(prefix="/api/reference", tags=["Reference Data"])


@router.get(
    "/geneSearch",
    response_model=PaginatedGeneResponse,
    summary="Search for genes by partial or complete match",
    description="""Find genes that are partial or complete match of a gene ID.
    
    **Gene ID Types:**
    - Gene symbol (e.g., BRCA1, TP53)
    - GENCODE ID (e.g., ENSG00000012048.20)
    - Ensembl ID (e.g., ENSG00000012048)
    
    **Optional Parameters:**
    - GENCODE version and genome build can be specified for specific releases
    - By default uses the genome build and GENCODE version from the latest GTEx release
    
    **Examples:**
    - Search for BRCA1: `geneId=BRCA1`
    - Search with specific version: `geneId=BRCA1&gencodeVersion=v26&genomeBuild=GRCh38`
    """,
    operation_id="search_genes",
    responses={
        200: {
            "description": "Genes found successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "chromosome": "17",
                                "dataSource": "GENCODE",
                                "description": "BRCA1 DNA repair associated",
                                "end": 43097243,
                                "entrezGeneId": 672,
                                "gencodeId": "ENSG00000012048.20",
                                "gencodeVersion": "v26",
                                "geneStatus": "KNOWN",
                                "geneSymbol": "BRCA1",
                                "geneSymbolUpper": "BRCA1",
                                "geneType": "protein_coding",
                                "genomeBuild": "GRCh38",
                                "start": 43044295,
                                "strand": "-",
                                "tss": 43097243,
                            }
                        ],
                        "paging_info": {
                            "numberOfPages": 1,
                            "page": 0,
                            "maxItemsPerPage": 250,
                            "totalNumberOfItems": 1,
                        },
                    }
                }
            },
        },
        400: {
            "description": "Invalid search query or parameters",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Search query must be between 1 and 50 characters",
                        "status_code": 400,
                        "details": {"field": "query", "value": ""},
                    }
                }
            },
        },
        422: {
            "description": "Request validation error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "ValidationError",
                        "message": "Invalid dataset identifier",
                        "status_code": 422,
                        "details": {"field": "datasetId", "value": "invalid_dataset"},
                    }
                }
            },
        },
        502: {
            "description": "GTEx Portal API communication error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "GTExAPIError",
                        "message": "GTEx Portal API error: Failed to search genes",
                        "status_code": 502,
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "InternalServerError",
                        "message": "Internal server error",
                        "status_code": 500,
                    }
                }
            },
        },
    },
)
async def search_genes(
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    gene_id: str = Query(
        alias="geneId",
        min_length=1,
        description="A gene symbol, versioned gencodeId, or unversioned gencodeId",
        examples=["BRCA1", "ENSG00000012048.20", "TP53"],
    ),
    gencode_version: GencodeVersion | None = Query(
        None,
        alias="gencodeVersion",
        description="GENCODE annotation release",
    ),
    genome_build: GenomeBuild | None = Query(
        None,
        alias="genomeBuild",
        description="Genome build version",
    ),
    page: int = Query(0, ge=0, le=1000000, description="Page number (0-based)"),
    items_per_page: int = Query(
        250,
        ge=1,
        le=100000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedGeneResponse:
    """Search for genes."""
    try:
        logger.info(
            "Gene search request",
            gene_id=gene_id,
            gencode_version=gencode_version,
            genome_build=genome_build,
        )

        result = await service.search_genes(
            query=gene_id,
            gencode_version=gencode_version.value if gencode_version else None,
            genome_build=genome_build.value if genome_build else None,
            page=page,
            page_size=items_per_page,
        )

        logger.info(
            "Gene search completed",
            gene_id=gene_id,
            result_count=len(result.data) if result.data else 0,
        )

    except ValidationError as e:
        logger.warning("Gene search validation error", error=str(e), gene_id=gene_id)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during gene search", gene_id=gene_id)
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during gene search", gene_id=gene_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/gene",
    response_model=PaginatedGeneResponse,
    summary="Get reference gene information",
    description="""Get detailed information about reference genes.
    
    **Required Parameters:**
    - Gene IDs: List of gene symbols, versioned or unversioned GENCODE IDs
    
    **Gene ID Types:**
    - Gene symbols (e.g., BRCA1, TP53)
    - Versioned GENCODE IDs (e.g., ENSG00000012048.20) - **recommended for unique matching**
    - Unversioned GENCODE IDs (e.g., ENSG00000012048)
    
    **Optional Parameters:**
    - GENCODE version and genome build for specific genome releases
    - By default uses the latest GTEx release genome build and GENCODE version
    
    **Examples:**
    - Get BRCA1 and TP53: `geneId=BRCA1&geneId=TP53`
    - Get by GENCODE ID: `geneId=ENSG00000012048.20&geneId=ENSG00000141510.11`
    """,
    operation_id="get_genes",
    responses={
        200: {
            "description": "Gene information retrieved successfully",
        },
        400: {
            "description": "Invalid request parameters",
            "model": ErrorResponse,
        },
        422: {
            "description": "Request validation error",
            "model": ErrorResponse,
        },
        502: {
            "description": "GTEx Portal API communication error",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_genes(
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    gene_id: list[str] = Query(
        alias="geneId",
        min_length=1,
        max_length=50,
        description="List of gene symbols, versioned or unversioned GENCODE IDs",
        examples=["BRCA1", "TP53"],
    ),
    gencode_version: GencodeVersion | None = Query(
        None,
        alias="gencodeVersion",
        description="GENCODE annotation release",
    ),
    genome_build: GenomeBuild | None = Query(
        None,
        alias="genomeBuild",
        description="Genome build version",
    ),
    page: int = Query(0, ge=0, le=1000000, description="Page number (0-based)"),
    items_per_page: int = Query(
        250,
        ge=1,
        le=100000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedGeneResponse:
    """Get gene information."""
    # Create request object from query parameters
    request = GeneRequest(
        geneId=gene_id,
        gencodeVersion=gencode_version,
        genomeBuild=genome_build,
        page=page,
        itemsPerPage=items_per_page,
    )

    try:
        logger.info("Get genes request", **request.model_dump(exclude_none=True))

        result = await service.get_genes(request)

        logger.info("Get genes completed", result_count=len(result.data) if result.data else 0)

    except ValidationError as e:
        logger.warning("Get genes validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during get genes")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during get genes")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/transcript",
    response_model=PaginatedTranscriptResponse,
    summary="Get gene transcripts",
    description="""Find all transcripts of a reference gene.
    
    **Required Parameters:**
    - GENCODE ID: A versioned GENCODE ID of a gene (e.g., ENSG00000065613.9)
    
    **Key Notes:**
    - Returns information about all transcripts for the specified gene
    - Requires a versioned GENCODE ID for accurate matching
    - A genome build and GENCODE version must be provided (or defaults are used)
    - By default queries the genome build and GENCODE version from the latest GTEx release
    
    **Examples:**
    - Get BRCA1 transcripts: `gencodeId=ENSG00000012048.20`
    - With specific version: `gencodeId=ENSG00000012048.20&gencodeVersion=v26&genomeBuild=GRCh38`
    """,
    operation_id="get_transcripts",
    responses={
        200: {
            "description": "Transcript information retrieved successfully",
        },
        400: {
            "description": "Invalid request parameters",
            "model": ErrorResponse,
        },
        422: {
            "description": "Request validation error",
            "model": ErrorResponse,
        },
        502: {
            "description": "GTEx Portal API communication error",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        },
    },
)
async def get_transcripts(
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    gencode_id: str = Query(
        alias="gencodeId",
        description="A versioned GENCODE ID of a gene, e.g. ENSG00000065613.9",
        examples=["ENSG00000012048.20", "ENSG00000141510.11"],
    ),
    gencode_version: GencodeVersion | None = Query(
        None,
        alias="gencodeVersion",
        description="GENCODE annotation release",
    ),
    genome_build: GenomeBuild | None = Query(
        None,
        alias="genomeBuild",
        description="Genome build version",
    ),
    page: int = Query(0, ge=0, le=1000000, description="Page number (0-based)"),
    items_per_page: int = Query(
        250,
        ge=1,
        le=100000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedTranscriptResponse:
    """Get transcript information."""
    # Create request object from query parameters
    request = TranscriptRequest(
        gencodeId=gencode_id,
        gencodeVersion=gencode_version,
        genomeBuild=genome_build,
        page=page,
        itemsPerPage=items_per_page,
    )

    try:
        logger.info("Get transcripts request", **request.model_dump(exclude_none=True))

        result = await service.get_transcripts(request)

        logger.info(
            "Get transcripts completed", result_count=len(result.data) if result.data else 0
        )

    except ValidationError as e:
        logger.warning("Get transcripts validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during get transcripts")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during get transcripts")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result
