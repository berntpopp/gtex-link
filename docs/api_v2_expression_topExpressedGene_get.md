# Get Top Expressed Genes

## Overview
- **Path:** `/api/v2/expression/topExpressedGene`
- **Method:** `GET`
- **Tags:** `Expression Data Endpoints`
- **Operation ID:** `get_top_expressed_genes_api_v2_expression_topExpressedGene_get`

## Description
Find top expressed genes for a specified tissue.

- Returns top expressed genes for a specified tissue in a dataset, sorted by median expression.
- When the optional parameter `filterMtGene` is set to true, mitochondrial genes will be excluded from the results.

By default, this service queries the latest GTEx release.

## Parameters

### Query Parameters

- **`tissueSiteDetailId`**
  - **Required:** Yes
  - **Description:** The ID of the tissue of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** object
**Description:** The ID of the tissue of interest. Can be a GTEx specific ID or an Ontology ID

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`filterMtGene`**
  - **Required:** No
  - **Description:** exclude mt genes
  - **Schema:** **Type:** boolean
**Description:** exclude mt genes
**Default:** `True`

- **`page`**
  - **Required:** No
  - **Description:** The 0-based numeric ID of the page to retrieve
  - **Schema:** **Type:** integer
**Description:** The 0-based numeric ID of the page to retrieve
**Default:** `0`
**Minimum:** 0
**Maximum:** 1000000

- **`itemsPerPage`**
  - **Required:** No
  - **Schema:** **Type:** integer
**Default:** `250`
**Minimum:** 1
**Maximum:** 100000

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_TopExpressedGenes_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `tissueSiteDetailId`
- Always handle error responses appropriately
- Check response status codes before processing response data