# Get Service Info

## Overview
- **Path:** `/api/v2/`
- **Method:** `GET`
- **Tags:** `GTEx Portal API Info`
- **Operation ID:** `get_service_info_api_v2__get`

## Description
General information about the GTEx service.

## Response

### Success Response
**Status Code:** `200`

**Description:** Successful Response

**Content Types:**
- **application/json**
  - **Schema:** Reference: `#/components/schemas/ServiceInfo`

## Notes for LLM Agents

When using this endpoint:
- Always handle error responses appropriately
- Check response status codes before processing response data