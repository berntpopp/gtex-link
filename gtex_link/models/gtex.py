"""GTEx-specific Pydantic models and enums."""

from __future__ import annotations

from enum import Enum


class Chromosome(str, Enum):
    """Chromosome enumeration."""

    CHR1 = "chr1"
    CHR2 = "chr2"
    CHR3 = "chr3"
    CHR4 = "chr4"
    CHR5 = "chr5"
    CHR6 = "chr6"
    CHR7 = "chr7"
    CHR8 = "chr8"
    CHR9 = "chr9"
    CHR10 = "chr10"
    CHR11 = "chr11"
    CHR12 = "chr12"
    CHR13 = "chr13"
    CHR14 = "chr14"
    CHR15 = "chr15"
    CHR16 = "chr16"
    CHR17 = "chr17"
    CHR18 = "chr18"
    CHR19 = "chr19"
    CHR20 = "chr20"
    CHR21 = "chr21"
    CHR22 = "chr22"
    CHR_X = "chrX"
    CHR_Y = "chrY"
    CHR_M = "chrM"


class DatasetId(str, Enum):
    """Dataset ID enumeration."""

    GTEX_V8 = "gtex_v8"
    GTEX_SNRNASEQ_PILOT = "gtex_snrnaseq_pilot"
    GTEX_V10 = "gtex_v10"


class GencodeVersion(str, Enum):
    """Gencode version enumeration."""

    V19 = "v19"
    V26 = "v26"
    V32 = "v32"
    V43 = "v43"


class GenomeBuild(str, Enum):
    """Genome build enumeration."""

    GRCH37 = "GRCh37"
    GRCH38 = "GRCh38"
    GRCH38_HG38 = "GRCh38/hg38"  # GTEx API format


class Strand(str, Enum):
    """Strand enumeration."""

    POSITIVE = "+"
    NEGATIVE = "-"


class Sex(str, Enum):
    """Sex enumeration."""

    MALE = "Male"
    FEMALE = "Female"


class DonorSex(str, Enum):
    """Donor sex enumeration."""

    M = "M"
    F = "F"


class TissueSiteDetailId(str, Enum):
    """Tissue site detail ID enumeration.
    
    Organized with most commonly used tissues first for better UX.
    """
    
    # Most commonly used tissues (appear first in dropdowns)
    WHOLE_BLOOD = "Whole_Blood"
    BRAIN_CORTEX = "Brain_Cortex"
    MUSCLE_SKELETAL = "Muscle_Skeletal"
    LIVER = "Liver"
    LUNG = "Lung"
    BREAST_MAMMARY_TISSUE = "Breast_Mammary_Tissue"
    HEART_LEFT_VENTRICLE = "Heart_Left_Ventricle"
    THYROID = "Thyroid"
    ADIPOSE_SUBCUTANEOUS = "Adipose_Subcutaneous"
    SKIN_SUN_EXPOSED = "Skin_Sun_Exposed_Lower_leg"
    
    # All other tissues (alphabetically organized)
    ADIPOSE_VISCERAL = "Adipose_Visceral_Omentum"
    ADRENAL_GLAND = "Adrenal_Gland"
    ARTERY_AORTA = "Artery_Aorta"
    ARTERY_CORONARY = "Artery_Coronary"
    ARTERY_TIBIAL = "Artery_Tibial"
    BLADDER = "Bladder"
    BRAIN_AMYGDALA = "Brain_Amygdala"
    BRAIN_ANTERIOR_CINGULATE_CORTEX = "Brain_Anterior_cingulate_cortex_BA24"
    BRAIN_CAUDATE = "Brain_Caudate_basal_ganglia"
    BRAIN_CEREBELLAR_HEMISPHERE = "Brain_Cerebellar_Hemisphere"
    BRAIN_CEREBELLUM = "Brain_Cerebellum"
    BRAIN_FRONTAL_CORTEX = "Brain_Frontal_Cortex_BA9"
    BRAIN_HIPPOCAMPUS = "Brain_Hippocampus"
    BRAIN_HYPOTHALAMUS = "Brain_Hypothalamus"
    BRAIN_NUCLEUS_ACCUMBENS = "Brain_Nucleus_accumbens_basal_ganglia"
    BRAIN_PUTAMEN = "Brain_Putamen_basal_ganglia"
    BRAIN_SPINAL_CORD = "Brain_Spinal_cord_cervical_c-1"
    BRAIN_SUBSTANTIA_NIGRA = "Brain_Substantia_nigra"
    CELLS_CULTURED_FIBROBLASTS = "Cells_Cultured_fibroblasts"
    CELLS_EBV_LYMPHOCYTES = "Cells_EBV-transformed_lymphocytes"
    CERVIX_ECTOCERVIX = "Cervix_Ectocervix"
    CERVIX_ENDOCERVIX = "Cervix_Endocervix"
    COLON_SIGMOID = "Colon_Sigmoid"
    COLON_TRANSVERSE = "Colon_Transverse"
    ESOPHAGUS_GASTROESOPHAGEAL_JUNCTION = "Esophagus_Gastroesophageal_Junction"
    ESOPHAGUS_MUCOSA = "Esophagus_Mucosa"
    ESOPHAGUS_MUSCULARIS = "Esophagus_Muscularis"
    FALLOPIAN_TUBE = "Fallopian_Tube"
    HEART_ATRIAL_APPENDAGE = "Heart_Atrial_Appendage"
    KIDNEY_CORTEX = "Kidney_Cortex"
    KIDNEY_MEDULLA = "Kidney_Medulla"
    MINOR_SALIVARY_GLAND = "Minor_Salivary_Gland"
    NERVE_TIBIAL = "Nerve_Tibial"
    OVARY = "Ovary"
    PANCREAS = "Pancreas"
    PITUITARY = "Pituitary"
    PROSTATE = "Prostate"
    SKIN_NOT_SUN_EXPOSED = "Skin_Not_Sun_Exposed_Suprapubic"
    SMALL_INTESTINE = "Small_Intestine_Terminal_Ileum"
    SPLEEN = "Spleen"
    STOMACH = "Stomach"
    TESTIS = "Testis"
    UTERUS = "Uterus"
    VAGINA = "Vagina"


class SortDirection(str, Enum):
    """Sort direction enumeration."""

    ASC = "asc"
    DESC = "desc"


class SortBy(str, Enum):
    """General sort by enumeration."""

    GENE_SYMBOL = "geneSymbol"
    CHROMOSOME = "chromosome"
    START = "start"
    END = "end"


class VariantSortBy(str, Enum):
    """Variant sort by enumeration."""

    CHROMOSOME = "chromosome"
    POSITION = "position"
    VARIANT_ID = "variantId"
    REF = "ref"
    ALT = "alt"


class MaterialType(str, Enum):
    """Material type enumeration."""

    DNA = "DNA"
    RNA = "RNA"
    PROTEIN = "Protein"


class HardyScale(str, Enum):
    """Hardy scale enumeration."""

    ZERO = "0"
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"


class DataType(str, Enum):
    """Data type enumeration."""

    RNA_SEQ = "RNA-seq"
    GENOTYPE = "Genotype"
    WGS = "WGS"
    WES = "WES"
