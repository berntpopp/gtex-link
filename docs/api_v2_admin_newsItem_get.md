# Get News Item

## Overview
- **Path:** `/api/v2/admin/newsItem`
- **Method:** `GET`
- **Tags:** `Admin Endpoints`
- **Operation ID:** `get_news_item_api_v2_admin_newsItem_get`

## Description
Getting all the news items from the database that are current

## Parameters

### Query Parameters

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
  - **Schema:** Reference: `#/components/schemas/PaginatedResponse_NewsItem_`

### Error Responses

**Status Code:** `422`
**Description:** Validation Error

## Notes for LLM Agents

When using this endpoint:
- This is an admin endpoint - requires special privileges
- Always handle error responses appropriately
- Check response status codes before processing response data