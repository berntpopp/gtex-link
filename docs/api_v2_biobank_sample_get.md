# Get Sample

## Overview
- **Path:** `/api/v2/biobank/sample`
- **Method:** `GET`
- **Tags:** `Biobank Data Endpoints`
- **Operation ID:** `get_sample_api_v2_biobank_sample_get`

## Description


## Parameters

### Query Parameters

- **`draw`**
  - **Required:** No
  - **Schema:** **Type:** integer

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
  - **Schema:** Reference: `#/components/schemas/BiobankResponse`

### Error Responses

**Status Code:** `400`
**Description:** Illegal query input

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data