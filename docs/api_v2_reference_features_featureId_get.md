# Get Genomic Features

## Overview
- **Path:** `/api/v2/reference/features/{featureId}`
- **Method:** `GET`
- **Tags:** `Reference Genome Endpoints`
- **Operation ID:** `get_genomic_features_api_v2_reference_features__featureId__get`

## Description


## Parameters

### Path Parameters

- **`featureId`**
  - **Required:** Yes
  - **Schema:** **Type:** string

### Query Parameters

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
  - **Schema:** Reference: `#/components/schemas/Feature`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `featureId`
- Always handle error responses appropriately
- Check response status codes before processing response data