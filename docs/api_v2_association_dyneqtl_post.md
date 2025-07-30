# Bulk Calculate Expression Quantitative Trait Loci

## Overview
- **Path:** `/api/v2/association/dyneqtl`
- **Method:** `POST`
- **Tags:** `Dynamic Association Endpoints`
- **Operation ID:** `bulk_calculate_expression_quantitative_trait_loci_api_v2_association_dyneqtl_post`

## Description
Calculate your own eQTLs

- This service calculates the gene-variant association for any given pair of gene and variant,
which may or may not be significant.
- This requires as input a GENCODE ID, GTEx variant ID, and tissue site detail ID.

By default, the calculation is based on the latest GTEx release.

## Parameters

### Query Parameters

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

## Request Body

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** Reference: `#/components/schemas/PostDynamicEqtlResult`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- This endpoint modifies data - ensure you have proper authorization
- Validate request body schema before sending
- Always handle error responses appropriately
- Check response status codes before processing response data