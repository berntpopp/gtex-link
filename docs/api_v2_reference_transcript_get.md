# Get Transcripts

## Overview
- **Path:** `/api/v2/reference/transcript`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_transcripts_api_v2_reference_transcript_get`

## Description
Find all transcripts of a reference gene.

- This service returns information about transcripts of the given versioned GENCODE ID.
- A genome build and GENCODE version must be provided.
- By default, this service queries the genome build and GENCODE version used by the latest GTEx release.

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A Versioned GENCODE ID of a gene, e.g. ENSG00000065613.9
  - **Schema:** **Type:** string
**Description:** A Versioned GENCODE ID of a gene, e.g. ENSG00000065613.9

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_Transcript_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data