# Get Neighbor Gene

## Overview
- **Path:** `/api/v2/reference/neighborGene`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_neighbor_gene_api_v2_reference_neighborGene_get`

## Description
Find all neighboring genes on a certain chromosome around a position with a certain window size.

## Parameters

### Query Parameters

- **`pos`**
  - **Required:** Yes
  - **Schema:** **Type:** integer
**Minimum:** 0
**Maximum:** 248945542

- **`chromosome`**
  - **Required:** Yes
  - **Schema:** Reference: `#/components/schemas/Chromosome`

- **`bp_window`**
  - **Required:** Yes
  - **Schema:** **Type:** integer
**Minimum:** 0
**Maximum:** 248936581

- **`page`**
  - **Required:** No
  - **Description:** The 0-based numeric ID of the page to retrieve
  - **Schema:** **Type:** integer
**Description:** The 0-based numeric ID of the page to retrieve
**Default:** `0`
**Minimum:** 0
**Maximum:** 1000000

- **`gencodeVersion`**
  - **Required:** No
  - **Description:** GENCODE annotation release.
  - **Schema:** Reference: `#/components/schemas/GencodeVersion`

- **`genomeBuild`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/GenomeBuild`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_Gene_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `pos`, `chromosome`, `bp_window`
- Always handle error responses appropriately
- Check response status codes before processing response data