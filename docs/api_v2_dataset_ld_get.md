# Get Linkage Disequilibrium Data

## Overview
- **Path:** `/api/v2/dataset/ld`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_linkage_disequilibrium_data_api_v2_dataset_ld_get`

## Description
Find linkage disequilibrium (LD) data for a given gene.

This endpoint returns linkage disequilibrium data for the cis-eQTLs found associated with the provided
gene in a specified dataset. Results are queried by gencode ID.
By default, the service queries the latest GTEx release.
Specify a dataset ID to fetch results from a different dataset.

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A Versioned GENCODE ID of a gene, e.g. ENSG00000065613.9
  - **Schema:** **Type:** string
**Description:** A Versioned GENCODE ID of a gene, e.g. ENSG00000065613.9

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_List_Union_str__float___`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data