# Get File List

## Overview
- **Path:** `/api/v2/dataset/fileList`
- **Method:** `GET`
- **Tags:** `Datasets Endpoints`
- **Operation ID:** `get_file_list_api_v2_dataset_fileList_get`

## Description
Get all the files in GTEx dataset for Download page

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** **Type:** array
**Items:** Reference: `#/components/schemas/File`

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data