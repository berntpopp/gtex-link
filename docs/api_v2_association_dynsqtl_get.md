# Calculate Splicing Quantitative Trait Loci

## Overview
- **Path:** `/api/v2/association/dynsqtl`
- **Method:** `GET`
- **Tags:** `Dynamic Association Endpoints`
- **Operation ID:** `calculate_splicing_quantitative_trait_loci_api_v2_association_dynsqtl_get`

## Description


## Parameters

### Query Parameters

- **`tissueSiteDetailId`**
  - **Required:** Yes
  - **Description:** The ID of the tissue of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** Reference: `#/components/schemas/TissueSiteDetailId`

- **`phenotypeId`**
  - **Required:** Yes
  - **Schema:** **Type:** string

- **`variantId`**
  - **Required:** Yes
  - **Description:** A gtex variant ID
  - **Schema:** **Type:** string
**Description:** A gtex variant ID

- **`datasetId`**
  - **Required:** No
  - **Description:** Unique identifier of a dataset. Usually includes a data source and data release.
  - **Schema:** Reference: `#/components/schemas/DatasetId`

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** Reference: `#/components/schemas/Sqtl`

### Error Responses

**Status Code:** `400`
**Description:** Unable to calculate sQTL

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `tissueSiteDetailId`, `phenotypeId`, `variantId`
- Always handle error responses appropriately
- Check response status codes before processing response data