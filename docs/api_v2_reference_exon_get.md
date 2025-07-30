# Get Exons

## Overview
- **Path:** `/api/v2/reference/exon`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_exons_api_v2_reference_exon_get`

## Description
This service returns exons from all known transcripts of the given gene.
 - A versioned GENCODE ID is required to ensure that all exons are from a single gene.
 - A dataset ID or both GENCODE version and genome build must be provided.
 - Although annotated exons are not dataset dependent,
specifying a dataset here is equivalent to specifying the GENCODE version and genome build used by that dataset.

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
  - **Schema:** **Type:** array
**Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
**Items:** **Type:** string

- **`gencodeVersion`**
  - **Required:** No
  - **Description:** GENCODE annotation release.
  - **Schema:** Reference: `#/components/schemas/GencodeVersion`

- **`genomeBuild`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/GenomeBuild`

- **`datasetId`**
  - **Required:** No
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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_Exon_`

### Error Responses

**Status Code:** `400`
**Description:** Illegal query input

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data