# Get Subject

## Overview
- **Path:** `/api/v2/dataset/subject`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_subject_api_v2_dataset_subject_get`

## Description
This service returns information of subjects used in analyses from all datasets.
Results may be filtered by dataset ID, subject ID, sex, age bracket or Hardy Scale.
By default, this service queries the latest GTEx release.

## Parameters

### Query Parameters

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`sex`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/DonorSex`

- **`ageBracket`**
  - **Required:** No
  - **Description:** The age bracket(s) of the donors of interest
  - **Schema:** **Type:** array
**Description:** The age bracket(s) of the donors of interest
**Items:** Reference: `#/components/schemas/DonorAgeBracket`

- **`hardyScale`**
  - **Required:** No
  - **Description:** The hardy scale of interest
  - **Schema:** Reference: `#/components/schemas/HardyScale-Input`

- **`subjectId`**
  - **Required:** No
  - **Description:** GTEx subject ID
  - **Schema:** **Type:** array
**Description:** GTEx subject ID
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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_Subject_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data