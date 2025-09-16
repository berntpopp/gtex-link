#!/usr/bin/env python3
"""GTEx API Endpoint Documentation Generator.

This script parses the GTEx OpenAPI specification and generates individual markdown
files for each endpoint, designed to be easily understood by agentic LLMs and
automated systems.

Usage:
    python generate_endpoint_docs.py [input_file] [output_dir]

Arguments:
    input_file: Path to the GTEx OpenAPI JSON file (default: gtex-openapi-spec-formatted.json)
    output_dir: Directory to output markdown files (default: current directory)

Example:
    python generate_endpoint_docs.py gtex-openapi-spec-formatted.json ./
"""

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict


def sanitize_filename(path: str, method: str) -> str:
    """Convert API path and method to a safe filename."""
    # Remove leading slash and replace remaining slashes with underscores
    clean_path = path.lstrip("/").replace("/", "_").replace("{", "").replace("}", "")
    # Remove special characters
    clean_path = "".join(c for c in clean_path if c.isalnum() or c in ("_", "-"))
    return f"{clean_path}_{method.lower()}.md"


def format_parameter(param: dict[str, Any]) -> str:
    """Format a parameter for markdown documentation."""
    name = param.get("name", "unknown")
    param_in = param.get("in", "unknown")
    required = param.get("required", False)
    schema = param.get("schema", {})
    description = param.get("description", "No description provided")

    # Extract type information
    param_type = schema.get("type", "unknown")
    default = schema.get("default")
    minimum = schema.get("minimum")
    maximum = schema.get("maximum")
    enum_values = schema.get("enum")

    # Build parameter documentation
    param_doc = f"- **`{name}`** ({'required' if required else 'optional'})\n"
    param_doc += f"  - **Type:** {param_type}\n"
    param_doc += f"  - **Location:** {param_in}\n"
    param_doc += f"  - **Description:** {description}\n"

    if default is not None:
        param_doc += f"  - **Default:** `{default}`\n"
    if minimum is not None:
        param_doc += f"  - **Minimum:** {minimum}\n"
    if maximum is not None:
        param_doc += f"  - **Maximum:** {maximum}\n"
    if enum_values:
        param_doc += f"  - **Allowed values:** {', '.join(f'`{v}`' for v in enum_values)}\n"

    return param_doc


def format_response(response_code: str, response_data: dict[str, Any]) -> str:
    """Format a response for markdown documentation."""
    description = response_data.get("description", "No description provided")
    content = response_data.get("content", {})

    response_doc = f"### {response_code} Response\n"
    response_doc += f"**Description:** {description}\n\n"

    if content:
        for media_type, media_data in content.items():
            response_doc += f"**Content Type:** `{media_type}`\n\n"
            schema = media_data.get("schema", {})
            if schema:
                schema_ref = schema.get("$ref")
                if schema_ref:
                    response_doc += f"**Schema:** `{schema_ref}`\n\n"
                else:
                    schema_type = schema.get("type", "object")
                    response_doc += f"**Schema Type:** `{schema_type}`\n\n"

    return response_doc


def generate_endpoint_markdown(path: str, method: str, endpoint_data: dict[str, Any]) -> str:
    """Generate markdown content for a single endpoint."""
    summary = endpoint_data.get("summary", "No summary provided")
    description = endpoint_data.get("description", "No description provided")
    operation_id = endpoint_data.get("operationId", "unknown")
    tags = endpoint_data.get("tags", [])
    parameters = endpoint_data.get("parameters", [])
    request_body = endpoint_data.get("requestBody")
    responses = endpoint_data.get("responses", {})

    # Start building markdown content
    markdown = f"# {summary}\n\n"

    # Overview section
    markdown += "## Overview\n"
    markdown += f"- **Path:** `{path}`\n"
    markdown += f"- **Method:** `{method.upper()}`\n"
    markdown += f"- **Operation ID:** `{operation_id}`\n"
    if tags:
        markdown += f"- **Tags:** {', '.join(f'`{tag}`' for tag in tags)}\n"
    markdown += "\n"

    # Description section
    markdown += "## Description\n"
    markdown += f"{description}\n\n"

    # Parameters section
    if parameters:
        markdown += "## Parameters\n\n"

        # Group parameters by location
        path_params = [p for p in parameters if p.get("in") == "path"]
        query_params = [p for p in parameters if p.get("in") == "query"]
        header_params = [p for p in parameters if p.get("in") == "header"]

        if path_params:
            markdown += "### Path Parameters\n"
            for param in path_params:
                markdown += format_parameter(param) + "\n"

        if query_params:
            markdown += "### Query Parameters\n"
            for param in query_params:
                markdown += format_parameter(param) + "\n"

        if header_params:
            markdown += "### Header Parameters\n"
            for param in header_params:
                markdown += format_parameter(param) + "\n"

    # Request body section
    if request_body:
        markdown += "## Request Body\n\n"
        description = request_body.get("description", "No description provided")
        required = request_body.get("required", False)
        content = request_body.get("content", {})

        markdown += f"**Description:** {description}\n"
        markdown += f"**Required:** {'Yes' if required else 'No'}\n\n"

        for media_type, media_data in content.items():
            markdown += f"**Content Type:** `{media_type}`\n\n"
            schema = media_data.get("schema", {})
            if schema:
                schema_ref = schema.get("$ref")
                if schema_ref:
                    markdown += f"**Schema:** `{schema_ref}`\n\n"

    # Responses section
    if responses:
        markdown += "## Responses\n\n"
        for response_code, response_data in responses.items():
            markdown += format_response(response_code, response_data)

    # Notes for LLM agents
    markdown += "## Notes for LLM Agents\n\n"
    markdown += "When using this endpoint programmatically:\n\n"

    # Add specific notes based on parameters
    required_params = [p["name"] for p in parameters if p.get("required", False)]
    if required_params:
        markdown += f"- **Required parameters:** {', '.join(f'`{p}`' for p in required_params)}\n"

    # Common parameter notes
    if any(p.get("name") == "datasetId" for p in parameters):
        markdown += "- The `datasetId` parameter controls which GTEx release version to query (defaults to latest)\n"

    if any(p.get("name") == "gencodeId" for p in parameters):
        markdown += (
            "- Use versioned GENCODE IDs (e.g., 'ENSG00000065613.9') for consistent results\n"
        )

    if any(p.get("name") in ["page", "itemsPerPage"] for p in parameters):
        markdown += "- Implement pagination for large result sets using `page` and `itemsPerPage` parameters\n"

    if method.upper() == "POST":
        markdown += "- This endpoint supports bulk operations - use POST for multiple simultaneous queries\n"

    markdown += "- Always handle HTTP error responses (400, 422, etc.) appropriately\n"
    markdown += "- Check the response schema reference for detailed field information\n"

    return markdown


def main() -> None:
    """Generate endpoint documentation from OpenAPI specification."""
    # Check for help argument
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        print(__doc__)
        sys.exit(0)

    # Parse command line arguments
    input_file = sys.argv[1] if len(sys.argv) > 1 else "gtex-openapi-spec-formatted.json"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "."

    # Validate input file
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    try:
        # Load OpenAPI specification
        print(f"Loading OpenAPI specification from {input_file}...")
        with open(input_file, encoding="utf-8") as f:
            spec = json.load(f)

        paths = spec.get("paths", {})
        if not paths:
            print("Error: No paths found in OpenAPI specification.")
            sys.exit(1)

        print(f"Found {len(paths)} paths in specification.")

        # Generate markdown files for each endpoint
        total_endpoints = 0
        for path, path_data in paths.items():
            for method, endpoint_data in path_data.items():
                if method.lower() in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    total_endpoints += 1

                    # Generate filename
                    filename = sanitize_filename(path, method)
                    filepath = os.path.join(output_dir, filename)

                    # Generate markdown content
                    markdown_content = generate_endpoint_markdown(path, method, endpoint_data)

                    # Write to file
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(markdown_content)

                    print(f"Generated: {filename}")

        print(f"\nSuccessfully generated {total_endpoints} endpoint documentation files.")
        print(f"Files saved to: {os.path.abspath(output_dir)}")

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error generating documentation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
