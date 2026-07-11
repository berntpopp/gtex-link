"""Group flat median rows into the token-efficient gene-grouped result.

Also fences upstream free-text (the GENCODE `description` on `Gene`, v1.1
untrusted-content standard) at this MCP serialization boundary -- see
`fence_gene_response`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from gtex_link.mcp.untrusted_content import (
    UntrustedText,
    enforce_untrusted_text_limits,
    fence_untrusted_text,
)
from gtex_link.models.mcp_results import (
    GeneMedianGroup,
    MCPGene,
    MedianExpressionResult,
    TissueMedian,
)
from gtex_link.models.responses import PaginatedResponse, PaginationInfo

if TYPE_CHECKING:
    from gtex_link.models.responses import MedianGeneExpression, PaginatedGeneResponse

SortMode = Literal["desc", "asc", "none"]
ResponseMode = Literal["compact", "full"]

# `search_genes`' `limit` query param has no declared upper bound (plain `int`
# default=20, not a constrained Field), so its real result cap is effectively
# unbounded by GTEx's own upstream page-size ceiling. Use a generous ceiling
# per Global Constraints ("object-count = real cap, never the bare default
# 128") rather than the 128 default so a legitimately large search never
# raises. `get_gene_information`'s cap is `GeneRequest.gene_id` `max_length=50`
# (models/requests.py), comfortably inside the untrusted-text module default
# (128), so it is passed explicitly for clarity but needs no override.
SEARCH_GENES_MAX_OBJECTS = 10_000


def fence_gene_response(result: PaginatedGeneResponse, *, max_objects: int) -> dict[str, Any]:
    """Fence each gene's upstream GENCODE `description` as an untrusted_text object.

    Applied at the MCP serialization boundary only: the internal `Gene`/
    `PaginatedGeneResponse` models (also used by the REST API) are untouched --
    this builds the MCP-only `PaginatedResponse[MCPGene]` shape and dumps it.
    Shared by the `search_genes` and `get_gene_information` MCP tools, which
    both return a `PaginatedGeneResponse`.
    """
    fenced_objects: list[UntrustedText] = []
    mcp_genes: list[MCPGene] = []
    for gene in result.data:
        fenced_description: UntrustedText | None = None
        if gene.description is not None:
            fenced_description = fence_untrusted_text(
                gene.description, source="gtex", record_id=gene.gencode_id
            )
            fenced_objects.append(fenced_description)
        mcp_genes.append(
            MCPGene(**gene.model_dump(exclude={"description"}), description=fenced_description)
        )
    enforce_untrusted_text_limits(fenced_objects, max_objects=max_objects)
    return PaginatedResponse[MCPGene](data=mcp_genes, pagingInfo=result.paging_info).model_dump(
        by_alias=True
    )


def median_headline(genes: list[GeneMedianGroup]) -> str:
    """One-line plain-English answer placed first; null-safe, never raises."""
    if not genes:
        return "No median expression found for the requested gene(s)."
    first = genes[0]
    if not first.tissues:
        head = f"{first.gene_symbol}: no expression rows returned."
    else:
        top = first.tissues[0]
        n_txt = f", n={top.n}" if top.n is not None else ""
        head = (
            f"{first.gene_symbol}: highest median in {top.tissue} "
            f"({top.median:.2f} {first.unit}{n_txt})."
        )
    if len(genes) > 1:
        head += f" (+{len(genes) - 1} more gene(s))"
    return head


def group_median(
    rows: list[MedianGeneExpression],
    *,
    counts: dict[str, int],
    sort: SortMode,
    top_n: int | None,
    response_mode: ResponseMode,
    spread_by_key: dict[tuple[str, str], dict[str, Any] | None],
    page: int = 0,
    page_size: int = 50,
    tissues_filter: set[str] | None = None,
) -> MedianExpressionResult:
    """Group rows by gene, sort/top_n tissues, hoist invariants, paginate by gene.

    When *tissues_filter* is given, each gene's tissues are restricted to that
    set after sorting (client-side multi-tissue selection); `tissuesTotal` then
    reflects the filtered universe, not all 54 tissues.
    """
    # Preserve first-seen gene order.
    order: list[str] = []
    buckets: dict[str, list[MedianGeneExpression]] = {}
    for row in rows:
        if row.gencode_id not in buckets:
            buckets[row.gencode_id] = []
            order.append(row.gencode_id)
        buckets[row.gencode_id].append(row)

    groups: list[GeneMedianGroup] = []
    for gencode_id in order:
        gene_rows = buckets[gencode_id]
        # Invariant fields (symbol/unit/dataset) are gene-level; capture before
        # any tissue filtering empties the row list.
        first = gene_rows[0]
        if sort != "none":
            gene_rows = sorted(gene_rows, key=lambda r: r.median, reverse=(sort == "desc"))
        if tissues_filter is not None:
            gene_rows = [r for r in gene_rows if r.tissue_site_detail_id in tissues_filter]
        total = len(gene_rows)
        selected = gene_rows[:top_n] if top_n else gene_rows
        tissues = [
            TissueMedian(
                tissue=r.tissue_site_detail_id,
                median=round(r.median, 4),
                n=counts.get(r.tissue_site_detail_id),
                ontologyId=r.ontology_id if response_mode == "full" else None,
                spread=spread_by_key.get((r.gencode_id, r.tissue_site_detail_id)),
            )
            for r in selected
        ]
        groups.append(
            GeneMedianGroup(
                gencodeId=gencode_id,
                geneSymbol=first.gene_symbol,
                datasetId=first.dataset_id,
                unit=first.unit,
                tissues=tissues,
                tissuesReturned=len(tissues),
                tissuesTotal=total,
            )
        )

    # Paginate the GENE list -- never split a gene's tissues across a page.
    total_genes = len(groups)
    start = page * page_size
    page_groups = groups[start : start + page_size]
    number_of_pages = (total_genes + page_size - 1) // page_size if page_size else 1
    return MedianExpressionResult(
        headline=median_headline(page_groups),
        genes=page_groups,
        pagingInfo=PaginationInfo(
            numberOfPages=number_of_pages,
            page=page,
            maxItemsPerPage=page_size,
            totalNumberOfItems=total_genes,
        ),
    )
