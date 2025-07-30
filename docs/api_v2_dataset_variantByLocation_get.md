# Get Variant By Location

## Overview
- **Path:** `/api/v2/dataset/variantByLocation`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_variant_by_location_api_v2_dataset_variantByLocation_get`

## Description
This service allows the user to query information about variants on a certain chromosome at a certain location

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

- **`sortBy`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/VariantSortBy`

- **`sortDirection`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/SortDirection`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_Variant_`

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