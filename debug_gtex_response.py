#!/usr/bin/env python3
"""Debug actual GTEx API response structure."""

import asyncio
import json
from gtex_link.api.client import GTExClient
from gtex_link.config import get_api_config
from gtex_link.logging_config import configure_logging

async def debug_median_expression():
    """Debug median gene expression response structure."""
    logger = configure_logging()
    config = get_api_config()
    client = GTExClient(config=config, logger=logger)
    
    try:
        # Test median gene expression
        params = {
            "gencodeId": ["ENSG00000012048.20"],  # BRCA1
            "page": 0,
            "itemsPerPage": 5  # Small sample
        }
        
        print("🔍 Testing median gene expression...")
        response = await client.get_median_gene_expression(params)
        print("Raw GTEx API Response:")
        print(json.dumps(response, indent=2))
        
        if response.get("data"):
            print(f"\n📊 Sample data item structure:")
            sample_item = response["data"][0]
            print(json.dumps(sample_item, indent=2))
            print(f"\n🔑 Available fields: {list(sample_item.keys())}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()

async def debug_top_genes():
    """Debug top expressed genes response structure.""" 
    logger = configure_logging()
    config = get_api_config()
    client = GTExClient(config=config, logger=logger)
    
    try:
        params = {
            "tissueSiteDetailId": "Whole_Blood",
            "page": 0,
            "itemsPerPage": 5
        }
        
        print("\n🔍 Testing top expressed genes...")
        response = await client.get_top_expressed_genes(params)
        print("Raw GTEx API Response:")
        print(json.dumps(response, indent=2))
        
        if response.get("data"):
            print(f"\n📊 Sample data item structure:")
            sample_item = response["data"][0]
            print(json.dumps(sample_item, indent=2))
            print(f"\n🔑 Available fields: {list(sample_item.keys())}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(debug_median_expression())
    asyncio.run(debug_top_genes())