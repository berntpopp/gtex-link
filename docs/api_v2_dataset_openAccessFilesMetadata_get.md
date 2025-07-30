# Get Downloads Page Data

## Overview
- **Path:** `/api/v2/dataset/openAccessFilesMetadata`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_downloads_page_data_api_v2_dataset_openAccessFilesMetadata_get`

## Description
Retrieves all the files belonging to the given `project_id` for display on the `Downloads Page`

## Parameters

### Query Parameters

- **`project_id`**
  - **Required:** Yes
  - **Schema:** Reference: `#/components/schemas/AvailableProjects`

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** Reference: `#/components/schemas/OpenAccessFilesMetadata`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- Ensure all required parameters are provided: `project_id`
- Always handle error responses appropriately
- Check response status codes before processing response data