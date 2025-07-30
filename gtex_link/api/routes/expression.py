"""Gene expression API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    DatasetId,
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    PaginatedGeneExpressionResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedTopExpressedGenesResponse,
    TissueSiteDetailId,
    TopExpressedGenesRequest,
)
from .dependencies import LoggerDep, ServiceDep

router = APIRouter(prefix="/api/expression", tags=["Expression"])


@router.get(
    "/median-gene-expression",
    response_model=PaginatedMedianGeneExpressionResponse,
    summary="Get median gene expression",
    description="Get median gene expression data across tissues.",
    operation_id="get_median_gene_expression",
)
async def get_median_gene_expression(
    service: ServiceDep,
    logger: LoggerDep,
    gencode_id: list[str] = Query(
        ...,
        alias="gencodeId",
        description="List of versioned GENCODE IDs (required)",
        min_length=1,
        examples=["ENSG00000012048.20", "ENSG00000141510.17"],
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs (optional filter)",
        examples=["Brain_Cortex", "Muscle_Skeletal"],
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
) -> PaginatedMedianGeneExpressionResponse:
    """Get median gene expression data."""
    try:
        request = MedianGeneExpressionRequest(
            gencodeId=gencode_id,
            tissueSiteDetailId=tissue_site_detail_id,
            datasetId=dataset_id,
            page=page,
            itemsPerPage=page_size,
        )

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
    summary="Get gene expression",
    description="Get individual sample gene expression data.",
    operation_id="get_gene_expression",
)
async def get_gene_expression(
    service: ServiceDep,
    logger: LoggerDep,
    gencode_id: list[str] = Query(
        ...,
        alias="gencodeId",
        description="List of versioned GENCODE IDs (required)",
        min_length=1,
        examples=["ENSG00000012048.20", "ENSG00000141510.17"],
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs (optional filter)",
        examples=["Brain_Cortex", "Muscle_Skeletal"],
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
) -> PaginatedGeneExpressionResponse:
    """Get gene expression data."""
    try:
        request = GeneExpressionRequest(
            gencodeId=gencode_id,
            tissueSiteDetailId=tissue_site_detail_id,
            datasetId=dataset_id,
            page=page,
            itemsPerPage=page_size,
        )

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
    summary="Get top expressed genes",
    description="Get top expressed genes for a specific tissue.",
    operation_id="get_top_expressed_genes",
)
async def get_top_expressed_genes(
    service: ServiceDep,
    logger: LoggerDep,
    tissue_site_detail_id: TissueSiteDetailId = Query(
        ...,
        alias="tissueSiteDetailId",
        description="Tissue site detail ID (required)",
        example="Brain_Cortex",
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
) -> PaginatedTopExpressedGenesResponse:
    """Get top expressed genes."""
    try:
        request = TopExpressedGenesRequest(
            tissueSiteDetailId=tissue_site_detail_id,
            datasetId=dataset_id,
            page=page,
            itemsPerPage=page_size,
        )

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
