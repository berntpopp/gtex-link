# Get Single Nucleus Gex Summary

## Overview
- **Path:** `/api/v2/expression/singleNucleusGeneExpressionSummary`
- **Method:** `GET`
- **Tags:** `Expression Data Endpoints`
- **Operation ID:** `get_single_nucleus_gex_summary_api_v2_expression_singleNucleusGeneExpressionSummary_get`

## Description
Retrieve Summarized Single Nucleus Gene Expression Data.

## Parameters

### Query Parameters

- **`datasetId`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** array
**Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
**Items:** **Type:** object

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_SingleNucleusGeneExpressionSummary_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data