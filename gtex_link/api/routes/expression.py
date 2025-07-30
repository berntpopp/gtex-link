"""Gene expression API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    ErrorResponse,
    GeneExpressionRequest,
    MedianGeneExpressionRequest,
    PaginatedGeneExpressionResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedTopExpressedGenesResponse,
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
    responses={
        200: {
            "description": "Median gene expression data retrieved successfully",
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
    service: ServiceDep,
    logger: LoggerDep,
    request: MedianGeneExpressionRequest = Depends(),
) -> PaginatedMedianGeneExpressionResponse:
    """Get median gene expression data."""
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
    summary="Get gene expression",
    description="Get individual sample gene expression data.",
    operation_id="get_gene_expression",
    responses={
        200: {
            "description": "Gene expression data retrieved successfully",
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
    service: ServiceDep,
    logger: LoggerDep,
    request: GeneExpressionRequest = Depends(),
) -> PaginatedGeneExpressionResponse:
    """Get gene expression data."""
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
    summary="Get top expressed genes",
    description="Get top expressed genes for a specific tissue.",
    operation_id="get_top_expressed_genes",
    responses={
        200: {
            "description": "Top expressed genes retrieved successfully",
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
    service: ServiceDep,
    logger: LoggerDep,
    request: TopExpressedGenesRequest = Depends(),
) -> PaginatedTopExpressedGenesResponse:
    """Get top expressed genes."""
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
