# Get Multi Tissue Eqtls

## Overview
- **Path:** `/api/v2/association/metasoft`
- **Method:** `GET`
- **Tags:** `Static Association Endpoints`
- **Operation ID:** `get_multi_tissue_eqtls_api_v2_association_metasoft_get`

## Description
Find multi-tissue eQTL `Metasoft` results.

- This service returns multi-tissue eQTL Metasoft results for a given gene and variant in a specified dataset.
- A Versioned GENCODE ID must be provided.
- For each tissue, the results include: m-value (mValue), normalized effect size (nes), p-value (pValue),
and standard error (se).
- The m-value is the posterior probability that an eQTL effect exists in each tissue tested in the cross-tissue
meta-analysis (Han and Eskin, PLoS Genetics 8(3): e1002555, 2012).
- The normalized effect size is the slope of the linear regression of normalized expression data versus the three
genotype categories using single-tissue eQTL analysis, representing eQTL effect size.
- The p-value is from a t-test that compares observed NES from single-tissue eQTL analysis to a null NES of 0.

By default, the service queries the latest GTEx release. The retrieved data is split into pages
with `items_per_page` entries per page

## Parameters

### Query Parameters

- **`gencodeId`**
  - **Required:** Yes
  - **Description:** A Versioned GENCODE ID of a gene, e.g. ENSG00000065613.9
  - **Schema:** **Type:** string
**Description:** A Versioned GENCODE ID of a gene, e.g. ENSG00000065613.9

- **`variantId`**
  - **Required:** No
  - **Description:** A gtex variant ID
  - **Schema:** **Type:** string
**Description:** A gtex variant ID

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_MetaSoft_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `gencodeId`
- Always handle error responses appropriately
- Check response status codes before processing response data