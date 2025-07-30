# Get Linkage Disequilibrium By Variant Data

## Overview
- **Path:** `/api/v2/dataset/ldByVariant`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_linkage_disequilibrium_by_variant_data_api_v2_dataset_ldByVariant_get`

## Description
Find linkage disequilibrium (LD) data for a given variant

## Parameters

### Query Parameters

- **`variantId`**
  - **Required:** No
  - **Description:** A gtex variant ID
  - **Schema:** **Type:** string
**Description:** A gtex variant ID

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_List_Union_str__float___`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data