"""Association analysis API routes (eQTL, sQTL)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from gtex_link.exceptions import GTExAPIError, ValidationError
from gtex_link.models import (
    DatasetId,
    EqtlGeneRequest,
    PaginatedEqtlGeneResponse,
    PaginatedSGeneResponse,
    PaginatedSingleTissueEqtlResponse,
    PaginatedSingleTissueSqtlResponse,
    SGeneRequest,
    SingleTissueEqtlRequest,
    SingleTissueSqtlRequest,
    TissueSiteDetailId,
)
from .dependencies import LoggerDep, ServiceDep

router = APIRouter(prefix="/api/association", tags=["Association"])


@router.get(
    "/single-tissue-eqtl",
    response_model=PaginatedSingleTissueEqtlResponse,
    summary="Get single tissue eQTL",
    description="Get expression quantitative trait loci (eQTL) data for single tissues.",
    operation_id="get_single_tissue_eqtl",
)
async def get_single_tissue_eqtl(
    service: ServiceDep,
    logger: LoggerDep,
    gencode_id: list[str] | None = Query(
        None,
        alias="gencodeId",
        description="List of Gencode IDs",
    ),
    gene_symbol: list[str] | None = Query(
        None,
        alias="geneSymbol",
        description="List of gene symbols",
    ),
    variant_id: list[str] | None = Query(
        None,
        alias="variantId",
        description="List of variant IDs",
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs",
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset identifier",
    ),
    pvalue_threshold: float | None = Query(
        None,
        alias="pValueThreshold",
        gt=0,
        le=1,
        description="P-value threshold for filtering results",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    page_size: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedSingleTissueEqtlResponse:
    """Get single tissue eQTL data."""
    try:
        request = SingleTissueEqtlRequest(
            gencode_id=gencode_id,
            gene_symbol=gene_symbol,
            variant_id=variant_id,
            tissue_site_detail_id=tissue_site_detail_id,
            dataset_id=dataset_id,
            pvalue_threshold=pvalue_threshold,
            page=page,
            items_per_page=page_size,
        )

        logger.info("Get single tissue eQTL request", **request.model_dump(exclude_none=True))

        result = await service.get_single_tissue_eqtl(request)

        logger.info(
            "Get single tissue eQTL completed", result_count=len(result.data) if result.data else 0
        )

    except ValidationError as e:
        logger.warning("Single tissue eQTL validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during single tissue eQTL")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during single tissue eQTL")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/single-tissue-sqtl",
    response_model=PaginatedSingleTissueSqtlResponse,
    summary="Get single tissue sQTL",
    description="Get splicing quantitative trait loci (sQTL) data for single tissues.",
    operation_id="get_single_tissue_sqtl",
)
async def get_single_tissue_sqtl(
    service: ServiceDep,
    logger: LoggerDep,
    phenotype_id: list[str] | None = Query(
        None,
        alias="phenotypeId",
        description="List of phenotype IDs",
    ),
    variant_id: list[str] | None = Query(
        None,
        alias="variantId",
        description="List of variant IDs",
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs",
    ),
    dataset_id: DatasetId = Query(
        DatasetId.GTEX_V8,
        alias="datasetId",
        description="Dataset identifier",
    ),
    pvalue_threshold: float | None = Query(
        None,
        alias="pValueThreshold",
        gt=0,
        le=1,
        description="P-value threshold for filtering results",
    ),
    page: int = Query(0, ge=0, description="Page number (0-based)"),
    page_size: int = Query(
        250,
        ge=1,
        le=1000,
        alias="itemsPerPage",
        description="Number of items per page",
    ),
) -> PaginatedSingleTissueSqtlResponse:
    """Get single tissue sQTL data."""
    try:
        request = SingleTissueSqtlRequest(
            phenotype_id=phenotype_id,
            variant_id=variant_id,
            tissue_site_detail_id=tissue_site_detail_id,
            dataset_id=dataset_id,
            pvalue_threshold=pvalue_threshold,
            page=page,
            items_per_page=page_size,
        )

        logger.info("Get single tissue sQTL request", **request.model_dump(exclude_none=True))

        result = await service.get_single_tissue_sqtl(request)

        logger.info(
            "Get single tissue sQTL completed", result_count=len(result.data) if result.data else 0
        )

    except ValidationError as e:
        logger.warning("Single tissue sQTL validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during single tissue sQTL")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during single tissue sQTL")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/egenes",
    response_model=PaginatedEqtlGeneResponse,
    summary="Get eGenes",
    description="Get eGenes (genes with significant eQTLs) data.",
    operation_id="get_egenes",
)
async def get_egenes(
    service: ServiceDep,
    logger: LoggerDep,
    gencode_id: list[str] | None = Query(
        None,
        alias="gencodeId",
        description="List of Gencode IDs",
    ),
    gene_symbol: list[str] | None = Query(
        None,
        alias="geneSymbol",
        description="List of gene symbols",
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs",
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
) -> PaginatedEqtlGeneResponse:
    """Get eGenes data."""
    try:
        request = EqtlGeneRequest(
            gencode_id=gencode_id,
            gene_symbol=gene_symbol,
            tissue_site_detail_id=tissue_site_detail_id,
            dataset_id=dataset_id,
            page=page,
            items_per_page=page_size,
        )

        logger.info("Get eGenes request", **request.model_dump(exclude_none=True))

        result = await service.get_egenes(request)

        logger.info("Get eGenes completed", result_count=len(result.data) if result.data else 0)

    except ValidationError as e:
        logger.warning("eGenes validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during eGenes")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during eGenes")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result


@router.get(
    "/sgenes",
    response_model=PaginatedSGeneResponse,
    summary="Get sGenes",
    description="Get sGenes (genes with significant sQTLs) data.",
    operation_id="get_sgenes",
)
async def get_sgenes(
    service: ServiceDep,
    logger: LoggerDep,
    gencode_id: list[str] | None = Query(
        None,
        alias="gencodeId",
        description="List of Gencode IDs",
    ),
    gene_symbol: list[str] | None = Query(
        None,
        alias="geneSymbol",
        description="List of gene symbols",
    ),
    tissue_site_detail_id: list[TissueSiteDetailId] | None = Query(
        None,
        alias="tissueSiteDetailId",
        description="List of tissue site detail IDs",
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
) -> PaginatedSGeneResponse:
    """Get sGenes data."""
    try:
        request = SGeneRequest(
            gencode_id=gencode_id,
            gene_symbol=gene_symbol,
            tissue_site_detail_id=tissue_site_detail_id,
            dataset_id=dataset_id,
            page=page,
            items_per_page=page_size,
        )

        logger.info("Get sGenes request", **request.model_dump(exclude_none=True))

        result = await service.get_sgenes(request)

        logger.info("Get sGenes completed", result_count=len(result.data) if result.data else 0)

    except ValidationError as e:
        logger.warning("sGenes validation error", error=str(e))
        raise HTTPException(status_code=400, detail=str(e)) from e
    except GTExAPIError as e:
        logger.exception("GTEx API error during sGenes")
        raise HTTPException(status_code=502, detail=f"GTEx Portal API error: {e}") from e
    except Exception as e:
        logger.exception("Unexpected error during sGenes")
        raise HTTPException(status_code=500, detail="Internal server error") from e
    else:
        return result
