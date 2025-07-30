# Calculate Isqtls

## Overview
- **Path:** `/api/v2/association/dynisqtl`
- **Method:** `GET`
- **Tags:** `Dynamic Association Endpoints`
- **Operation ID:** `calculate_isqtls_api_v2_association_dynisqtl_get`

## Description
Calculate your own Cell Specific sQTLs.

- This service calculates the gene-variant association for any given pair of
gene and variant, which may or may not be significant.
- This requires as input a GENCODE ID, GTEx variant ID, and tissue site detail ID.

By default, the calculation is based on the latest GTEx release.

## Parameters

### Query Parameters

- **`cellType`**
  - **Required:** Yes
  - **Schema:** Reference: `#/components/schemas/CellType`

- **`tissueSiteDetailId`**
  - **Required:** Yes
  - **Description:** The ID of the tissue of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** **Type:** object
**Description:** The ID of the tissue of interest. Can be a GTEx specific ID or an Ontology ID

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
  - **Schema:** Reference: `#/components/schemas/ISqtl`

### Error Responses

**Status Code:** `400`
**Description:** Unable to calculate isQTL

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `cellType`, `tissueSiteDetailId`, `phenotypeId`, `variantId`
- Always handle error responses appropriately
- Check response status codes before processing response data