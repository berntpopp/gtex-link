# Get Significant Single Tissue Eqtls By Location

## Overview
- **Path:** `/api/v2/association/singleTissueEqtlByLocation`
- **Method:** `GET`
- **Tags:** `Static Association Endpoints`
- **Operation ID:** `get_significant_single_tissue_eqtls_by_location_api_v2_association_singleTissueEqtlByLocation_get`

## Description
Find significant single tissue eQTLs using Chromosomal Locations.

- This service returns precomputed significant single tissue eQTLs.
- Results may be filtered by tissue, and/or dataset.

By default, the service queries the latest GTEx release. Since this endpoint is used to support a 
third party program on the portal, the return structure is different from other endpoints and is
not paginated.

## Parameters

### Query Parameters

- **`tissueSiteDetailId`**
  - **Required:** Yes
  - **Description:** The ID of the tissue of interest. Can be a GTEx specific ID or an Ontology ID
  - **Schema:** Reference: `#/components/schemas/TissueSiteDetailId`

- **`start`**
  - **Required:** Yes
  - **Schema:** **Type:** integer
**Minimum:** 0
**Maximum:** 250000000

- **`end`**
  - **Required:** Yes
  - **Schema:** **Type:** integer
**Minimum:** 0
**Maximum:** 250000000

- **`chromosome`**
  - **Required:** Yes
  - **Description:** Chromosome to Query
  - **Schema:** Reference: `#/components/schemas/Chromosome`

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
  - **Schema:** Reference: `#/components/schemas/IGVResponse`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `tissueSiteDetailId`, `start`, `end`, `chromosome`
- Always handle error responses appropriately
- Check response status codes before processing response data