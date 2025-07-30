# GTEx Portal API Documentation

## Overview

This directory contains the OpenAPI specification for the GTEx Portal API version 2.0.0, retrieved from the official GTEx Portal.

## Retrieval Information

- **Source URL**: https://gtexportal.org/api/v2/openapi.json
- **Retrieved Date**: July 30, 2025
- **API Version**: 2.0.0
- **OpenAPI Version**: 3.1.0

## Files

### Core Specification
- `gtex-openapi-spec-formatted.json` - GTEx OpenAPI specification with proper JSON formatting
- `generate_endpoint_docs.py` - Python script to generate individual endpoint markdown files from the OpenAPI specification

### Individual Endpoint Documentation
This directory contains detailed markdown documentation for all 55 GTEx API endpoints, designed to be easily understood by agentic LLMs and automated systems. Each file includes comprehensive information about parameters, request/response schemas, and usage examples.

#### Service Information
- `api_v2_get.md` - General GTEx service information

#### Admin Endpoints
- `api_v2_admin_maintenanceMessage_get.md` - Maintenance message management
- `api_v2_admin_newsItem_get.md` - News item management

#### Association Data Endpoints
- `api_v2_association_egene_get.md` - Expression quantitative trait loci (eQTL) gene associations
- `api_v2_association_sgene_get.md` - Splicing quantitative trait loci (sQTL) gene associations
- `api_v2_association_singleTissueEqtl_get.md` - Single tissue eQTL data
- `api_v2_association_singleTissueEqtlByLocation_get.md` - Location-based single tissue eQTL queries
- `api_v2_association_singleTissueSqtl_get.md` - Single tissue sQTL data
- `api_v2_association_singleTissueIEqtl_get.md` - Single tissue interaction eQTL data
- `api_v2_association_singleTissueISqtl_get.md` - Single tissue interaction sQTL data
- `api_v2_association_dyneqtl_get.md` - Dynamic eQTL analysis (GET)
- `api_v2_association_dyneqtl_post.md` - Dynamic eQTL analysis (POST/bulk)
- `api_v2_association_dynieqtl_get.md` - Dynamic interaction eQTL analysis
- `api_v2_association_dynsqtl_get.md` - Dynamic sQTL analysis
- `api_v2_association_dynisqtl_get.md` - Dynamic interaction sQTL analysis
- `api_v2_association_fineMapping_get.md` - Fine mapping results
- `api_v2_association_independentEqtl_get.md` - Independent eQTL analysis
- `api_v2_association_metasoft_get.md` - Meta-analysis results (METASOFT)

#### Biobank Data Endpoints
- `api_v2_biobank_sample_get.md` - Sample data and metadata
- `api_v2_biobank_download_get.md` - Sample download capabilities

#### Dataset Information Endpoints
- `api_v2_dataset_annotation_get.md` - Dataset annotations and metadata
- `api_v2_dataset_collapsedGeneModelExon_get.md` - Collapsed gene model exon data
- `api_v2_dataset_fullCollapsedGeneModelExon_get.md` - Full collapsed gene model exon data
- `api_v2_dataset_functionalAnnotation_get.md` - Functional annotation data
- `api_v2_dataset_sample_get.md` - Sample information and metadata
- `api_v2_dataset_subject_get.md` - Subject information and demographics
- `api_v2_dataset_tissueSiteDetail_get.md` - Tissue site details and classifications
- `api_v2_dataset_variant_get.md` - Variant information and annotations
- `api_v2_dataset_variantByLocation_get.md` - Location-based variant queries
- `api_v2_dataset_ld_get.md` - Linkage disequilibrium data
- `api_v2_dataset_ldByVariant_get.md` - Variant-specific linkage disequilibrium
- `api_v2_dataset_fileList_get.md` - Dataset file listings
- `api_v2_dataset_openAccessFilesMetadata_get.md` - Open access file metadata

#### Expression Data Endpoints
- `api_v2_expression_geneExpression_get.md` - Gene expression data
- `api_v2_expression_medianGeneExpression_get.md` - Median gene expression values
- `api_v2_expression_clusteredMedianGeneExpression_get.md` - Clustered median gene expression
- `api_v2_expression_medianExonExpression_get.md` - Median exon expression values
- `api_v2_expression_clusteredMedianExonExpression_get.md` - Clustered median exon expression
- `api_v2_expression_medianJunctionExpression_get.md` - Median junction expression values
- `api_v2_expression_clusteredMedianJunctionExpression_get.md` - Clustered median junction expression
- `api_v2_expression_medianTranscriptExpression_get.md` - Median transcript expression values
- `api_v2_expression_clusteredMedianTranscriptExpression_get.md` - Clustered median transcript expression
- `api_v2_expression_singleNucleusGeneExpression_get.md` - Single nucleus gene expression data
- `api_v2_expression_singleNucleusGeneExpressionSummary_get.md` - Single nucleus expression summaries
- `api_v2_expression_topExpressedGene_get.md` - Top expressed genes by tissue
- `api_v2_expression_expressionPca_get.md` - Expression principal component analysis

#### Reference Genome Endpoints
- `api_v2_reference_gene_get.md` - Gene information and details
- `api_v2_reference_transcript_get.md` - Transcript information and annotations
- `api_v2_reference_exon_get.md` - Exon boundaries and information
- `api_v2_reference_geneSearch_get.md` - Gene search functionality
- `api_v2_reference_features_featureId_get.md` - Feature-specific queries by ID
- `api_v2_reference_gwasCatalogByLocation_get.md` - GWAS catalog integration by genomic location
- `api_v2_reference_neighborGene_get.md` - Neighboring gene queries

#### Histology Endpoints
- `api_v2_histology_image_get.md` - Histological image access

#### Metadata Endpoints
- `api_v2_metadata_dataset_get.md` - Dataset and system metadata

## API Summary

The GTEx Portal API provides access to gene expression and regulation data from the Genotype-Tissue Expression (GTEx) project. The API contains **55 endpoints** organized into the following categories:

### Endpoint Categories

#### Association Data
- Dynamic eQTL/sQTL analysis
- Single tissue eQTL/sQTL data
- eGene and sGene associations
- Fine mapping results
- Independent eQTL analysis
- Meta-analysis results (METASOFT)

#### Expression Data
- Gene, exon, junction, and transcript expression
- Median and clustered expression data
- Single nucleus RNA-seq data
- Expression PCA analysis
- Top expressed genes by tissue

#### Dataset Information
- Sample and subject metadata
- Tissue site details
- File listings and metadata
- Functional annotations
- Linkage disequilibrium data
- Variant information

#### Reference Data
- Gene and transcript information
- Exon boundaries
- Gene search functionality
- GWAS catalog integration
- Neighboring gene queries

#### Biobank Data
- Sample download capabilities
- Sample metadata

#### Histology
- Tissue histology images

#### Administration
- Maintenance messages
- News items
- Service information

## API Base URL

The API is accessible at: `https://gtexportal.org/api/v2/`

## Usage

### Using the Documentation Generator Script

The `generate_endpoint_docs.py` script can be used to regenerate or update the endpoint documentation files:

```bash
# Basic usage (uses defaults)
python generate_endpoint_docs.py

# Specify input file and output directory
python generate_endpoint_docs.py gtex-openapi-spec-formatted.json ./

# Make the script executable and run it
chmod +x generate_endpoint_docs.py
./generate_endpoint_docs.py
```

**Script Features:**
- Parses the GTEx OpenAPI specification JSON file
- Generates individual markdown files for each of the 55 endpoints
- Creates LLM-friendly documentation with detailed parameter information
- Includes usage notes specifically designed for agentic systems
- Handles both GET and POST endpoints (including the duplicate `/api/v2/association/dyneqtl` endpoint)
- Sanitizes filenames and organizes output systematically

**Script Requirements:**
- Python 3.6 or higher
- No external dependencies (uses only standard library)

### Using the OpenAPI Specification

This specification can be used with OpenAPI-compatible tools to:
- Generate client libraries
- Create interactive documentation
- Test API endpoints
- Build applications that integrate with GTEx data

## About GTEx

The Genotype-Tissue Expression (GTEx) project is a comprehensive public resource to study tissue-specific gene expression and regulation. The project has collected and analyzed gene expression data from 54 non-diseased tissue sites across nearly 1000 individuals.