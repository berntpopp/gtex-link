# Get Single Nucleus Gex

## Overview
- **Path:** `/api/v2/expression/singleNucleusGeneExpression`
- **Method:** `GET`
- **Tags:** `Expression Data Endpoints`
- **Operation ID:** `get_single_nucleus_gex_api_v2_expression_singleNucleusGeneExpression_get`

## Description
Retrieve Single Nucleus Gene Expression Data for a given Gene.

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
  - **Schema:** **Type:** array
**Description:** A list of Versioned GENCODE IDs, e.g. ENSG00000065613.9,ENSG00000203782.5
**Items:** **Type:** string

- **`datasetId`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** array
**Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
**Items:** **Type:** object

- **`excludeDataArray`**
  - **Required:** No
  - **Description:** Include Expression Values in Result. Set to `false` to include the data array
  - **Schema:** **Type:** boolean
**Description:** Include Expression Values in Result. Set to `false` to include the data array
**Default:** `True`

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_SingleNucleusGeneExpressionResult_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data