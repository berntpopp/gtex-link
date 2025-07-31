"""Gene expression API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    DatasetId,
    ErrorResponse,
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    PaginatedGeneExpressionResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedTopExpressedGenesResponse,
    TissueSiteDetailId,
    TopExpressedGenesRequest,
)

from gtex_link.services.gtex_service import GTExService
from structlog.typing import FilteringBoundLogger

from .dependencies import LoggerDep, GTExServiceDep

router = APIRouter(prefix="/api/expression", tags=["Expression"])


@router.get(
    "/median-gene-expression",
    response_model=PaginatedMedianGeneExpressionResponse,
    summary="Get median gene expression data",
    description="""Get median gene expression data across tissues.
    
    **Required:** Versioned GENCODE IDs (e.g., ENSG00000012048.20)
    **Optional:** Filter by specific tissues
    **Returns:** Median expression values in TPM units
    
    **Example:** Get BRCA1 expression in blood and brain tissues
    """,
    operation_id="get_median_gene_expression",
    responses={
        200: {
            "description": "Median gene expression data retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "gencodeId": "ENSG00000012048.20",
                                "geneSymbol": "BRCA1",
                                "tissueSiteDetailId": "Whole_Blood",
                                "median": 15.2,
                                "unit": "TPM",
                            }
                        ],
                        "page": 0,
                        "itemsPerPage": 250,
                        "totalItems": 1,
                    }
                }
            },
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
async def get_median_gene_expression(
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    gencode_id: list[str] = Query(
        alias="gencodeId",
        description="List of versioned GENCODE IDs (e.g. ENSG00000012048.20)",
        examples=["ENSG00000012048.20", "ENSG00000141510.11"],
        min_length=1,
        max_length=50,
    ),
    tissue_site_detail_id: TissueSiteDetailId = Query(
        default=TissueSiteDetailId.ALL,
        alias="tissueSiteDetailId",
        description="Tissue filter. Use 'ALL' (empty) for all tissues, or specific tissue name for single tissue.",
    ),
    dataset_id: DatasetId = Query(
        default=DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset ID - gtex_v8 is recommended",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    items_per_page: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page (1-1000)",
    ),
) -> PaginatedMedianGeneExpressionResponse:
    """Get median gene expression data."""

    # Create request object from query parameters
    request = MedianGeneExpressionRequest(
        gencodeId=gencode_id,
        tissueSiteDetailId=tissue_site_detail_id,
        datasetId=dataset_id,
        page=page,
        itemsPerPage=items_per_page,
    )

    try:
        logger.info("Get median gene expression request", **request.model_dump(exclude_none=True))

        result = await service.get_median_gene_expression(request)

        logger.info(
            "Get median gene expression completed",
            result_count=len(result.data) if result.data else 0,
        )

    except ValidationError as e:
        logger.warning("Median gene expression validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during median gene expression")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during median gene expression")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/gene-expression",
    response_model=PaginatedGeneExpressionResponse,
    summary="Get individual sample gene expression data",
    description="""Get normalized gene expression data at the sample level.
    
    **Required:** Versioned GENCODE IDs
    **Optional:** Filter by tissues, donor attributes
    **Returns:** Individual sample expression values in TPM units
    
    **Example:** Get BRCA1 expression in all blood samples
    """,
    operation_id="get_gene_expression",
    responses={
        200: {
            "description": "Gene expression data retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "gencodeId": "ENSG00000012048.20",
                                "geneSymbol": "BRCA1",
                                "sampleId": "GTEX-111FC-0226-SM-5GIEN",
                                "tissueSiteDetailId": "Whole_Blood",
                                "expression": 15.2,
                                "unit": "TPM",
                            }
                        ],
                        "page": 0,
                        "itemsPerPage": 250,
                        "totalItems": 670,
                    }
                }
            },
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
async def get_gene_expression(
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    gencode_id: list[str] = Query(
        alias="gencodeId",
        description="List of versioned GENCODE IDs (e.g. ENSG00000012048.20)",
        min_length=1,
        max_length=50,
        examples=["ENSG00000012048.20"],
    ),
    tissue_site_detail_id: TissueSiteDetailId = Query(
        default=TissueSiteDetailId.ALL,
        alias="tissueSiteDetailId",
        description="Tissue filter. Use 'ALL' (empty) for all tissues, or specific tissue name for single tissue.",
    ),
    attribute_subset: str | None = Query(
        None,
        alias="attributeSubset",
        description="Donor attribute to subset data by",
        examples=["sex", "age"],
    ),
    dataset_id: DatasetId = Query(
        default=DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset ID - gtex_v8 is recommended",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    items_per_page: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page (1-1000)",
    ),
) -> PaginatedGeneExpressionResponse:
    """Get gene expression data."""

    # Create request object from query parameters
    request = GeneExpressionRequest(
        gencodeId=gencode_id,
        tissueSiteDetailId=tissue_site_detail_id,
        attributeSubset=attribute_subset,
        datasetId=dataset_id,
        page=page,
        itemsPerPage=items_per_page,
    )

    try:
        logger.info("Get gene expression request", **request.model_dump(exclude_none=True))

        result = await service.get_gene_expression(request)

        logger.info(
            "Get gene expression completed", result_count=len(result.data) if result.data else 0
        )

    except ValidationError as e:
        logger.warning("Gene expression validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during gene expression")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during gene expression")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/top-expressed-genes",
    response_model=PaginatedTopExpressedGenesResponse,
    summary="Get top expressed genes by tissue",
    description="""Get top expressed genes for a specific tissue, sorted by median expression.
    
    **Required:** Single tissue site detail ID
    **Optional:** Filter mitochondrial genes, change dataset
    **Returns:** Top expressed genes ranked by median TPM
    
    **Example:** Get top 10 genes expressed in whole blood
    """,
    operation_id="get_top_expressed_genes",
    responses={
        200: {
            "description": "Top expressed genes retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "gencodeId": "ENSG00000244734.3",
                                "geneSymbol": "HBB",
                                "tissueSiteDetailId": "Whole_Blood",
                                "median": 267405.0,
                                "unit": "TPM",
                            }
                        ],
                        "page": 0,
                        "itemsPerPage": 250,
                        "totalItems": 56200,
                    }
                }
            },
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
async def get_top_expressed_genes(
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    tissue_site_detail_id: TissueSiteDetailId = Query(
        alias="tissueSiteDetailId", description="Tissue site detail ID for top gene analysis"
    ),
    filter_mt_gene: bool = Query(
        default=True, alias="filterMtGene", description="Exclude mitochondrial genes from results"
    ),
    dataset_id: DatasetId = Query(
        default=DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset ID - gtex_v8 is recommended",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    items_per_page: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page (1-1000)",
    ),
) -> PaginatedTopExpressedGenesResponse:
    """Get top expressed genes."""

    # Create request object from query parameters
    request = TopExpressedGenesRequest(
        tissueSiteDetailId=tissue_site_detail_id,
        filterMtGene=filter_mt_gene,
        datasetId=dataset_id,
        page=page,
        itemsPerPage=items_per_page,
    )

    try:
        logger.info("Get top expressed genes request", **request.model_dump(exclude_none=True))

        result = await service.get_top_expressed_genes(request)

        logger.info(
            "Get top expressed genes completed", result_count=len(result.data) if result.data else 0
        )

    except ValidationError as e:
        logger.warning("Top expressed genes validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during top expressed genes")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during top expressed genes")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result
