"""Reference data API routes (genes, transcripts, exons)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    Chromosome,
    DatasetId,
    GeneRequest,
    PaginatedGeneResponse,
    PaginatedTranscriptResponse,
    SortBy,
    SortDirection,
    TranscriptRequest,
)
from .dependencies import LoggerDep, ServiceDep

router = APIRouter(prefix="/api/reference", tags=["Reference Data"])


@router.get(
    "/genes/search",
    response_model=PaginatedGeneResponse,
    summary="Search genes",
    description="Search for genes by symbol or other identifiers.",
    operation_id="search_genes",
)
async def search_genes(
    service: ServiceDep,
    logger: LoggerDep,
    query: str = Query(
        ...,
        min_length=1,
        max_length=50,
        description="Gene search query",
        examples=["BRCA1", "ENSG00000012048.20", "TP53"],
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset identifier",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    page_size: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedGeneResponse:
    """Search for genes."""
    try:
        logger.info("Gene search request", query=query, dataset_id=dataset_id)

        result = await service.search_genes(
            query=query,
            dataset_id=dataset_id.value,
            page=page,
            page_size=page_size,
        )

        logger.info(
            "Gene search completed",
            query=query,
            result_count=len(result.data) if result.data else 0,
        )

    except ValidationError as e:
        logger.warning("Gene search validation error", error=str(e), query=query)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during gene search", query=query)
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during gene search", query=query)
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/genes",
    response_model=PaginatedGeneResponse,
    summary="Get genes",
    description="Get gene information with filtering options.",
    operation_id="get_genes",
)
async def get_genes(
    service: ServiceDep,
    logger: LoggerDep,
    gene_id: list[str] | None = Query(
        None,
        alias="geneId",
        description="List of gene IDs (gene symbols, versioned or unversioned GENCODE IDs)",
        examples=["BRCA1", "ENSG00000012048.20", "ENSG00000012048"],
    ),
    gene_symbol: list[str] | None = Query(
        None,
        alias="geneSymbol",
        description="List of gene symbols",
        examples=["BRCA1", "TP53", "APOE"],
    ),
    chromosome: list[Chromosome] | None = Query(
        None,
        description="List of chromosomes",
        examples=["chr17", "chr1"],
    ),
    start: int | None = Query(
        None, 
        ge=0, 
        description="Start position (genomic coordinates)",
        example=43044295
    ),
    end: int | None = Query(
        None, 
        ge=0, 
        description="End position (genomic coordinates)",
        example=43170245
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset identifier",
    ),
    sort_by: SortBy = Query(
        SortBy.GENE_SYMBOL,
        alias="sortBy",
        description="Sort field",
    ),
    sort_direction: SortDirection = Query(
        SortDirection.ASC,
        alias="sortDirection",
        description="Sort direction",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    page_size: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedGeneResponse:
    """Get gene information."""
    try:
        request = GeneRequest(
            geneId=gene_id,
            geneSymbol=gene_symbol,
            chromosome=chromosome,
            start=start,
            end=end,
            datasetId=dataset_id,
            sortBy=sort_by,
            sortDirection=sort_direction,
            page=page,
            itemsPerPage=page_size,
        )

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
    "/transcripts",
    response_model=PaginatedTranscriptResponse,
    summary="Get transcripts",
    description="Get transcript information with filtering options.",
    operation_id="get_transcripts",
)
async def get_transcripts(
    service: ServiceDep,
    logger: LoggerDep,
    gencode_id: list[str] | None = Query(
        None,
        alias="gencodeId",
        description="List of versioned GENCODE IDs",
        examples=["ENSG00000012048.20", "ENSG00000141510.17"],
    ),
    transcript_id: list[str] | None = Query(
        None,
        alias="transcriptId",
        description="List of transcript IDs",
        examples=["ENST00000357654.9", "ENST00000380152.8"],
    ),
    chromosome: list[Chromosome] | None = Query(
        None,
        description="List of chromosomes",
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset identifier",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    page_size: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedTranscriptResponse:
    """Get transcript information."""
    try:
        request = TranscriptRequest(
            gencodeId=gencode_id,
            transcriptId=transcript_id,
            chromosome=chromosome,
            datasetId=dataset_id,
            page=page,
            itemsPerPage=page_size,
        )

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
