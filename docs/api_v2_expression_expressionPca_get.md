# Get Expression Pca

## Overview
- **Path:** `/api/v2/expression/expressionPca`
- **Method:** `GET`
- **Tags:** `Expression Data Endpoints`
- **Operation ID:** `get_expression_pca_api_v2_expression_expressionPca_get`

## Description
Find gene expression PCA data.

- Returns gene expression PCA (principal component analysis) in tissues.
- Results may be filtered by tissue, sample, or dataset.

By default, the service queries the latest GTEx release.

## Parameters

### Query Parameters

- **`tissueSiteDetailId`**
  - **Required:** Yes
  - **Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** array
**Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
**Items:** **Type:** object

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`sampleId`**
  - **Required:** No
  - **Schema:** **Type:** string

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_ExpressionPCA_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `tissueSiteDetailId`
- Always handle error responses appropriately
- Check response status codes before processing response data