# Get Significant Single Tissue Sqtls

## Overview
- **Path:** `/api/v2/association/singleTissueSqtl`
- **Method:** `GET`
- **Tags:** `Static Association Endpoints`
- **Operation ID:** `get_significant_single_tissue_sqtls_api_v2_association_singleTissueSqtl_get`

## Description
Retrieve Single Tissue sQTL Data.

- This service returns single tissue sQTL data for the given genes, from a specified dataset.
- Results may be filtered by tissue
- By default, the service queries the latest GTEx release.

The retrieved data is split into pages with `items_per_page` entries per page

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** No
  - **Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
  - **Schema:** **Type:** array
**Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
**Items:** **Type:** string

- **`variantId`**
  - **Required:** No
  - **Description:** A list of GTEx variant IDs
  - **Schema:** **Type:** array
**Description:** A list of GTEx variant IDs
**Items:** **Type:** string

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** array
**Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
**Items:** **Type:** object

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_SingleTissueSqtl_`

### Error Responses

**Status Code:** `400`
**Description:** Unable Process Request

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data