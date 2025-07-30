# Download

## Overview
- **Path:** `/api/v2/biobank/download`
- **Method:** `GET`
- **Tags:** `Biobank Data Endpoints`
- **Operation ID:** `download_api_v2_biobank_download_get`

## Description


## Parameters

### Query Parameters

- **`materialType`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/MaterialType`

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** Tissues of interest
  - **Schema:** **Type:** array
**Description:** Tissues of interest
**Items:** **Type:** object

- **`pathCategory`**
  - **Required:** No
  - **Description:** A list of Pathology Category(s)
  - **Schema:** **Type:** array
**Description:** A list of Pathology Category(s)
**Items:** Reference: `#/components/schemas/PathCategory`

- **`tissueSampleId`**
  - **Required:** No
  - **Description:** A list of Tissue Sample ID(s)
  - **Schema:** **Type:** array
**Description:** A list of Tissue Sample ID(s)
**Items:** **Type:** string

- **`sex`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/DonorSex`

- **`sortBy`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/SortBy`

- **`sortDirection`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/SortDirection`

- **`searchTerm`**
  - **Required:** No
  - **Schema:** **Type:** string

- **`sampleId`**
  - **Required:** No
  - **Description:** GTEx sample ID
  - **Schema:** **Type:** array
**Description:** GTEx sample ID
**Items:** **Type:** string

- **`subjectId`**
  - **Required:** No
  - **Description:** GTEx subject ID
  - **Schema:** **Type:** array
**Description:** GTEx subject ID
**Items:** **Type:** string

- **`ageBracket`**
  - **Required:** No
  - **Description:** The age bracket(s) of the donors of interest
  - **Schema:** **Type:** array
**Description:** The age bracket(s) of the donors of interest
**Items:** Reference: `#/components/schemas/DonorAgeBracket`

- **`hardyScale`**
  - **Required:** No
  - **Description:** A list of Hardy Scale(s) of interest
  - **Schema:** **Type:** array
**Description:** A list of Hardy Scale(s) of interest
**Items:** Reference: `#/components/schemas/HardyScale-Input`

- **`hasExpressionData`**
  - **Required:** No
  - **Schema:** **Type:** boolean

- **`hasGenotype`**
  - **Required:** No
  - **Schema:** **Type:** boolean

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/BiobankSample`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data