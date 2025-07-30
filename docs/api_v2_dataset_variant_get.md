# Get Variant

## Overview
- **Path:** `/api/v2/dataset/variant`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_variant_api_v2_dataset_variant_get`

## Description
This service returns information about a variant, including position, dbSNP RS ID, the reference allele,
the alternative allele, and whether the minor allele frequency is >= 1%.
For GTEx v6p, there is also information about whether the whole exome sequence and chip sequencing data are
available. Results may be queried by GTEx variant ID (variantId), dbSNP RS ID (snpId) or genomic location
(chromosome and pos). Variants are identified based on the genotype data of each dataset cohort, namely,
are dataset-dependent. Each variant is assigned a unique GTEx variant ID (i.e. the primary key).
Not all variants have a mappable dbSNP RS ID. By default, this service queries the latest GTEx release.

## Parameters

### Query Parameters

- **`snpId`**
  - **Required:** No
  - **Description:** A Snp ID
  - **Schema:** **Type:** string
**Description:** A Snp ID

- **`variantId`**
  - **Required:** No
  - **Description:** A gtex variant ID
  - **Schema:** **Type:** string
**Description:** A gtex variant ID

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`chromosome`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/Chromosome`

- **`pos`**
  - **Required:** No
  - **Schema:** **Type:** array
**Items:** **Type:** integer

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
- Always handle error responses appropriately
- Check response status codes before processing response data