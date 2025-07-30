# Get Gwas Catalog By Location

## Overview
- **Path:** `/api/v2/reference/gwasCatalogByLocation`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_gwas_catalog_by_location_api_v2_reference_gwasCatalogByLocation_get`

## Description
Find the GWAS Catalog on a certain chromosome between start and end locations.

## Parameters

### Query Parameters

- **`start`**
  - **Required:** Yes
  - **Schema:** **Type:** integer
**Minimum:** 0
**Maximum:** 250000000

- **`end`**
  - **Required:** Yes
  - **Schema:** **Type:** integer
**Minimum:** 0
**Maximum:** 250000000

- **`chromosome`**
  - **Required:** Yes
  - **Schema:** Reference: `#/components/schemas/Chromosome`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_GWAS_`

### Error Responses

**Status Code:** `400`
**Description:** Illegal query input

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `start`, `end`, `chromosome`
- Always handle error responses appropriately
- Check response status codes before processing response data