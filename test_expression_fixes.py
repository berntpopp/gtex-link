#!/usr/bin/env python3
"""Test expression endpoint fixes."""

import asyncio
from gtex_link.api.client import GTExClient
from gtex_link.config import get_api_config
from gtex_link.logging_config import configure_logging
from fastapi.testclient import TestClient
from gtex_link.app import app

async def test_gene_id_lookup():
    """Test looking up gencodeId for BRCA1 to use in expression tests."""
    logger = configure_logging()
    config = get_api_config()
    client = GTExClient(config=config, logger=logger)
    
    try:
        # Search for BRCA1 to get its gencodeId
        response = await client.search_genes("BRCA1")
        if response and response.get("data"):
            gene = response["data"][0]
            gencode_id = gene.get("gencodeId")
            print(f"BRCA1 Gencode ID: {gencode_id}")
            return gencode_id
        else:
            print("❌ Could not find BRCA1 gene")
            return None
    except Exception as e:
        print(f"❌ Error looking up BRCA1: {e}")
        return None
    finally:
        await client.close()

def test_expression_endpoints():
    """Test expression endpoints with proper parameters."""
    client = TestClient(app)
    
    # This is BRCA1's gencode ID
    brca1_gencode_id = "ENSG00000012048.20"
    
    print("Testing Expression Endpoints...")
    
    # Test median gene expression with gencodeId
    print("\n1. Testing median gene expression...")
    response = client.get(f"/api/expression/median-gene-expression?gencodeId={brca1_gencode_id}")
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}")
    else:
        data = response.json()
        print(f"   ✅ Success! Found {len(data.get('data', []))} results")
    
    # Test gene expression with gencodeId  
    print("\n2. Testing gene expression...")
    response = client.get(f"/api/expression/gene-expression?gencodeId={brca1_gencode_id}")
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}")
    else:
        data = response.json()
        print(f"   ✅ Success! Found {len(data.get('data', []))} results")
    
    # Test top expressed genes with tissue
    print("\n3. Testing top expressed genes...")
    response = client.get("/api/expression/top-expressed-genes?tissueSiteDetailId=Whole_Blood")
    print(f"   Status: {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}")
    else:
        data = response.json()
        print(f"   ✅ Success! Found {len(data.get('data', []))} results")

if __name__ == "__main__":
    print("🧪 Testing GTEx Expression Endpoint Fixes")
    
    # First get BRCA1's gencode ID
    brca1_gencode_id = asyncio.run(test_gene_id_lookup())
    
    if brca1_gencode_id:
        # Test endpoints
        test_expression_endpoints()
        print("\n🎉 Expression endpoint testing complete!")
    else:
        print("\n❌ Cannot test without valid gencode ID")