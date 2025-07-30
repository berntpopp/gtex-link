# Get Sample

## Overview
- **Path:** `/api/v2/dataset/sample`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_sample_api_v2_dataset_sample_get`

## Description
This service returns information of samples used in analyses from all datasets.
Results may be filtered by dataset ID, sample ID, subject ID, sample metadata, or other provided parameters.
By default, this service queries the latest GTEx release.

## Parameters

### Query Parameters

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`sampleId`**
  - **Required:** No
  - **Description:** GTEx sample ID
  - **Schema:** **Type:** array
**Description:** GTEx sample ID
**Items:** **Type:** string

- **`tissueSampleId`**
  - **Required:** No
  - **Description:** A list of Tissue Sample ID(s)
  - **Schema:** **Type:** array
**Description:** A list of Tissue Sample ID(s)
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

- **`sex`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/DonorSex`

- **`pathCategory`**
  - **Required:** No
  - **Description:** A list of Pathology Category(s)
  - **Schema:** **Type:** array
**Description:** A list of Pathology Category(s)
**Items:** Reference: `#/components/schemas/PathCategory`

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** Tissues of interest
  - **Schema:** **Type:** array
**Description:** Tissues of interest
**Items:** Reference: `#/components/schemas/TissueSiteDetailId`

- **`aliquotId`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** **Type:** string

- **`autolysisScore`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/AutolysisScore`

- **`hardyScale`**
  - **Required:** No
  - **Description:** A list of Hardy Scale(s) of interest
  - **Schema:** **Type:** array
**Description:** A list of Hardy Scale(s) of interest
**Items:** Reference: `#/components/schemas/HardyScale-Input`

- **`ischemicTime`**
  - **Required:** No
  - **Description:** Ischemic Time for the sample of interest
  - **Schema:** **Type:** array
**Description:** Ischemic Time for the sample of interest
**Items:** **Type:** integer
**Minimum:** -1300
**Maximum:** 2100

- **`ischemicTimeGroup`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/IschemicTimeGroup`

- **`rin`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** **Type:** number
**Minimum:** 1.0
**Maximum:** 10.0

- **`uberonId`**
  - **Required:** No
  - **Description:** A list of Uberon ID(s) of interest.
  - **Schema:** **Type:** array
**Description:** A list of Uberon ID(s) of interest.
**Items:** Reference: `#/components/schemas/TissueSiteOntologyId`

- **`dataType`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/DataType`

- **`sortBy`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/SampleSortBy`

- **`sortDirection`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/SortDirection`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_DatasetSample_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data