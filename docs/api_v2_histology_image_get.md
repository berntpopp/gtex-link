# Get Image

## Overview
- **Path:** `/api/v2/histology/image`
- **Method:** `GET`
- **Tags:** `Histology Endpoints`
- **Operation ID:** `get_image_api_v2_histology_image_get`

## Description


## Parameters

### Query Parameters

- **`tissueSampleId`**
  - **Required:** No
  - **Description:** A list of Tissue Sample ID(s)
  - **Schema:** **Type:** array
**Description:** A list of Tissue Sample ID(s)
**Items:** **Type:** string

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_HistologySample_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data