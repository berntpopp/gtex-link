"""Reference data API routes (genes, transcripts, exons)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    DatasetId,
    ErrorResponse,
    GeneRequest,
    PaginatedGeneResponse,
    PaginatedTranscriptResponse,
    TranscriptRequest,
)

from gtex_link.services.gtex_service import GTExService
from structlog.typing import FilteringBoundLogger

from .dependencies import LoggerDep, GTExServiceDep

router = APIRouter(prefix="/api/reference", tags=["Reference Data"])


@router.get(
    "/genes/search",
    response_model=PaginatedGeneResponse,
    summary="Search genes",
    description="Search for genes by symbol or other identifiers.",
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
    request: GeneRequest = Depends(),
) -> PaginatedGeneResponse:
    """Get gene information."""
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
    "/transcripts",
    response_model=PaginatedTranscriptResponse,
    summary="Get transcripts",
    description="Get transcript information with filtering options.",
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
    request: TranscriptRequest = Depends(),
) -> PaginatedTranscriptResponse:
    """Get transcript information."""
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
