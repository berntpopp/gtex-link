# Get Genes

## Overview
- **Path:** `/api/v2/reference/gene`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_genes_api_v2_reference_gene_get`

## Description
This service returns information about reference genes. A genome build and GENCODE version must be provided.
 - Genes are searchable by gene symbol, GENCODE ID and versioned GENCODE ID.
 - Versioned GENCODE ID is recommended to ensure unique ID matching.
 - By default, this service queries the genome build and GENCODE version used by the latest GTEx release.

## Parameters

### Query Parameters

- **`geneId`**
  - **Required:** Yes
  - **Description:** A gene symbol, versioned gencodeId, or unversioned gencodeId.
  - **Schema:** **Type:** array
**Description:** A gene symbol, versioned gencodeId, or unversioned gencodeId.
**Items:** **Type:** string

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

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `geneId`
- Always handle error responses appropriately
- Check response status codes before processing response data