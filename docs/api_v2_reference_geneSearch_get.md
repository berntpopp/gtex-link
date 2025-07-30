# Get Gene Search

## Overview
- **Path:** `/api/v2/reference/geneSearch`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_gene_search_api_v2_reference_geneSearch_get`

## Description
Find genes that are partial or complete match of a gene_id
 - gene_id could be a gene symbol, a gencode ID, or an Ensemble ID
 - Gencode Version and Genome Build must be specified

## Parameters

### Query Parameters

- **`geneId`**
  - **Required:** Yes
  - **Schema:** **Type:** string

- **`gencodeVersion`**
  - **Required:** No
  - **Description:** GENCODE annotation release.
  - **Schema:** Reference: `#/components/schemas/GencodeVersion`

- **`genomeBuild`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/GenomeBuild`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_Gene_`

### Error Responses

**Status Code:** `400`
**Description:** Illegal query input

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `geneId`
- Always handle error responses appropriately
- Check response status codes before processing response data