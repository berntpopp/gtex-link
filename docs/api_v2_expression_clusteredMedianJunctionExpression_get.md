# Get Clustered Median Junction Expression

## Overview
- **Path:** `/api/v2/expression/clusteredMedianJunctionExpression`
- **Method:** `GET`
- **Tags:** `Expression Data Endpoints`
- **Operation ID:** `get_clustered_median_junction_expression_api_v2_expression_clusteredMedianJunctionExpression_get`

## Description
Find median junction expression data along with hierarchical clusters .

-  Returns median junction read counts in tissues of a given gene from all known transcripts along with
the hierarchical clustering results of tissues and genes, based on junction expression, in Newick format.
- Results may be filtered by dataset, gene or tissue, but at least one gene must be provided.
- The hierarchical clustering is performed by calculating Euclidean distances and using the average linkage method.
- **This endpoint is not paginated.**

By default, this service queries the latest GTEx release.

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
  - **Schema:** **Type:** array
**Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
**Items:** **Type:** string

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** array
**Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
**Items:** **Type:** object

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** Reference: `#/components/schemas/ClusteredMedianJunctionExpression`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data