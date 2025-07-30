# Get Independent Eqtl

## Overview
- **Path:** `/api/v2/association/independentEqtl`
- **Method:** `GET`
- **Tags:** `Static Association Endpoints`
- **Operation ID:** `get_independent_eqtl_api_v2_association_independentEqtl_get`

## Description
Retrieve Independent eQTL Data

- Finds and returns `Independent eQTL Data` data for the provided list of genes
- By default, this endpoint fetches data from the latest `GTEx` version

The retrieved data is split into pages with `items_per_page` entries per page

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
  - **Schema:** **Type:** array
**Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_IndependentEqtl_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data