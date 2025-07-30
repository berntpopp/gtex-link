# Get Dataset Info

## Overview
- **Path:** `/api/v2/metadata/dataset`
- **Method:** `GET`
- **Tags:** `Metadata Endpoints`
- **Operation ID:** `get_dataset_info_api_v2_metadata_dataset_get`

## Description


## Parameters

### Query Parameters

- **`datasetId`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/DatasetId`

- **`organizationName`**
  - **Required:** No
  - **Schema:** Reference: `#/components/schemas/OrganizationNames`

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/Dataset`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data