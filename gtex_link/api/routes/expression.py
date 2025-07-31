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
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    gencode_id: list[str] | None = Query(
        None,
        alias="gencodeId",
        description="List of Gencode IDs",
        examples=["ENSG00000012048.20"],
    ),
    gene_symbol: list[str] | None = Query(
        None,
        description="List of gene symbols",
        examples=["BRCA1", "TP53"],
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs",
        examples=["Whole_Blood", "Breast_Mammary_Tissue"],
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset ID",
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
    # Validate that at least one gene identifier is provided
    if not gencode_id and not gene_symbol:
        raise HTTPException(
            status_code=422, detail="Either gencodeId or geneSymbol must be provided"
        )

    # Create request object from query parameters
    # If gene_symbol is provided but not gencode_id, we need to convert gene symbols to gencode IDs
    final_gencode_id = gencode_id

    if gene_symbol and not gencode_id:
        # Convert gene symbols to gencode IDs using gene search
        logger.info("Converting gene symbols to gencode IDs", gene_symbols=gene_symbol)
        try:
            gencode_ids = []
            for symbol in gene_symbol:
                # Search for the gene to get its gencode ID
                search_result = await service.search_genes(
                    query=symbol, dataset_id=dataset_id.value, page=0, page_size=1
                )
                if search_result.data:
                    gencode_ids.append(search_result.data[0].gencode_id)
                else:
                    logger.warning("Gene symbol not found", gene_symbol=symbol)
                    # Continue anyway - let the GTEx API handle the error
                    gencode_ids.append(symbol)

            final_gencode_id = gencode_ids
            logger.info(
                "Converted gene symbols to gencode IDs",
                gene_symbols=gene_symbol,
                gencode_ids=final_gencode_id,
            )

        except Exception as e:
            logger.error("Failed to convert gene symbols to gencode IDs", error=str(e))
            # Fall back to using gene symbols directly (will likely fail but shows better error)
            final_gencode_id = gene_symbol

    request = MedianGeneExpressionRequest(
        gencode_id=final_gencode_id,
        tissue_site_detail_id=tissue_site_detail_id,
        dataset_id=dataset_id,
        page=page,
        items_per_page=items_per_page,
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
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
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
    service: GTExService = GTExServiceDep,
    logger: FilteringBoundLogger = LoggerDep,
    tissue_site_detail_id: TissueSiteDetailId = Query(
        alias="tissueSiteDetailId",
        description="Tissue site detail ID",
        examples=["Whole_Blood", "Breast_Mammary_Tissue"],
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset ID",
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
        tissue_site_detail_id=tissue_site_detail_id,
        dataset_id=dataset_id,
        page=page,
        items_per_page=items_per_page,
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
