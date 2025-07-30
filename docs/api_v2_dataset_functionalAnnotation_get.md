# Get Functional Annotation

## Overview
- **Path:** `/api/v2/dataset/functionalAnnotation`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_functional_annotation_api_v2_dataset_functionalAnnotation_get`

## Description
This endpoint retrieves the functional annotation of a certain chromosome location. Default to most recent dataset
release.

## Parameters

### Query Parameters

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`chromosome`**
  - **Required:** Yes
  - **Schema:** Reference: `#/components/schemas/Chromosome`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_FunctionalAnnotation_`

### Error Responses

**Status Code:** `400`
**Description:** Illegal query input

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `chromosome`, `start`, `end`
- Always handle error responses appropriately
- Check response status codes before processing response data