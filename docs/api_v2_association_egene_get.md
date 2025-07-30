# Get Eqtl Genes

## Overview
- **Path:** `/api/v2/association/egene`
- **Method:** `GET`
- **Tags:** `Static Association Endpoints`
- **Operation ID:** `get_eqtl_genes_api_v2_association_egene_get`

## Description
Retrieve eGenes (eQTL Genes).

- This service returns eGenes (eQTL Genes) from the specified dataset.
- eGenes are genes that have at least one significant cis-eQTL acting upon them.
- Results may be filtered by tissue. By default, the service queries the latest GTEx release.

For each eGene, the results include the allelic fold change (log2AllelicFoldChange), p-value (pValue),
p-value threshold (pValueThreshold), empirical p-value (empiricalPValue), and q-value (qValue).

- The log2AllelicFoldChange is the allelic fold change (in log2 scale) of the most significant eQTL.
- The pValue is the nominal p-value of the most significant eQTL.
- The pValueThreshold is the p-value threshold used to determine whether a cis-eQTL for this gene is  significant.
For more details see https://gtexportal.org/home/documentationPage#staticTextAnalysisMethods.
- The empiricalPValue is the beta distribution-adjusted empirical p-value from FastQTL.
- The qValues were calculated based on the empirical p-values. A false discovery rate (FDR) threshold of <= 0.05
was applied to identify genes with a significant eQTL.

## Parameters

### Query Parameters

- **`tissueSiteDetailId`**
  - **Required:** No
  - **Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** array
**Description:** A list of Tissue IDs of the tissue(s) of interest. Can be a GTEx specific ID or an Ontology ID
**Items:** **Type:** object

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_EqtlGene_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data