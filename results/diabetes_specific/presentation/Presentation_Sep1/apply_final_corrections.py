# -*- coding: utf-8 -*-
import os

# 1. Update WIP_scientific_reading.md
with open('WIP_scientific_reading.md', 'r') as f:
    wip_text = f.read()

# Replace PS definition block
old_ps_block = """#### 3. Method & Input Representation
- **Method:** Adapted from the Mixscape Gaussian Mixture / local perturbation framework. PS is a continuous, cell-level score measuring the probability that an individual single cell has genuinely departed from the local unperturbed (WT) control distribution in high-dimensional gene expression space.
- **Input:** Normalized single-cell gene expression matrix and target gene identity.
- **Score Scale:** Native continuous probability range $[0.0, 1.0]$, where values near 1.0 indicate strong single-cell perturbation response, and values near 0.0 indicate non-responders or unperturbed 'escapers'.
- **Level of Analysis:** Inherently a cell-level continuous metric, which is summarized at the perturbation level using the median PS and an explicit responder fraction (percentage of cells with $\\text{PS} > 0.5$).
- **Missing Data Clarification:** Skipped/unavailable PS (for 10 compound/heterozygous lines) is an analytical lookup constraint (target name not matching a single gene symbol in the RNA matrix), NOT a zero response."""

new_ps_block = """#### 3. Method & Input Representation
- **Method:** Calculated using `pertps` / `PS_python` (the Wei Li lab\'s Python implementation of the scMAGeCK-style perturbation score). For each single cell, PS learns a target-specific transcriptional perturbation signature relative to unperturbed wild-type (WT) control cells and projects the cell onto this signature to quantify single-cell perturbation response.
- **Input:** Normalized single-cell gene expression matrix and target gene identity.
- **Score Scale:** Native continuous score range $[0.0, 1.0]$, where values approaching 1.0 reflect strong single-cell transcriptional response/penetrance, while values near 0.0 reflect unperturbed cells, low signal, or non-responders.
- **Level of Analysis:** Inherently a continuous cell-level metric. For perturbation-level summarization in this WIP, two distinct summary statistics are reported: (1) the **median PS**, and (2) an **explicit responder fraction** calculated using an operational downstream threshold (percentage of cells with $\\text{PS} > 0.5$). The responder fraction is a summary metric and should not be conflated with the continuous PS score itself.
- **Distinction from Mixscape:** Mixscape is a separate Gaussian mixture modeling method used for discrete KO vs non-perturbed classification (particularly in the independent CRISPRi validation context), whereas PS provides a continuous projection score.
- **Missing Data Clarification:** Skipped/unavailable PS (for 10 compound, heterozygous, or enhancer lines) is strictly an analytical lookup constraint (target label not matching an individual gene symbol in the count matrix), NOT a zero biological response."""

wip_text = wip_text.replace(old_ps_block, new_ps_block)

# Fix DistanceSpace and Stage 7 separation
old_ds_block = """### Higher-Order Manifold Structure: DistanceSpace, Modules, and Gene Programs
- **DistanceSpace:** Constructs a $36 \\times 36$ pairwise phenotypic distance matrix (630 pairwise comparisons) partitioning genotypes into **9 Phenotype Groups (PG1–PG9)**.
- **Co-Functional Modules:** Unsupervised Louvain clustering partitions perturbations into **6 Regulatory Modules (M1–M6)**:
  - **Module M1 (General Endoderm & Core Drivers):** *GATA6*, *FOXA2*, *HHEX*, *GLIS3*, *RFX6*, *MNX1*, *NKX2-2*, *HNF4A*, *TET1*.
  - **Module M2 (Chromatin Repressors):** *TLE3*.
  - **Module M3 (Polycomb / Corepressors):** *NEUROD1*, *BCOR*.
  - **Module M4 (Beta Master Selector):** *PDX1*.
  - **Module M5 (Histone Acetyltransferase Complexes):** *TADA2B*.
  - **Module M6 (Endocrine Lineage Directors):** *PAX6*, *PBX1*.
- **Gene Programs:** 4 core cNMF programs governing functional activity:
  - **Program P1:** Endocrine secretion machinery (*PEG10*, *CACNA2D3*, *FGF12*, *AKAP12*, *GAL*).
  - **Program P2:** Hypoxia, metabolic remodeling, and cellular survival (*BNIP3*, *PDE4D*, *WSB1*, *NREP*).
  - **Program P3 & P4:** Progenitor proliferation and extracellular matrix reorganization."""

new_ds_block = """### Distinct Higher-Order Analyses: DistanceSpace Phenotype Groups vs Stage 7 Regulatory Modules

These two analytical dimensions operate on different mathematical representations and must be interpreted separately rather than as a single hierarchy:

1. **DistanceSpace Analysis (Pairwise Phenotype Geometry):**
   - Computes a full $36 \\times 36$ pairwise Energy Distance matrix (630 unique pairwise comparisons) between all non-WT perturbation distributions.
   - PCoA and nearest-neighbor network analysis partition the 36 perturbations into **9 Phenotype Groups (PG1–PG9)** based on pairwise phenotypic similarity.

2. **Stage 7 Regulatory-Effect Analysis (Downstream Transcriptional Programs):**
   - Analyzes the perturbation $\\times$ downstream-gene effect matrix independently of DistanceSpace.
   - Louvain clustering identifies **6 Co-Functional Perturbation Modules (M1–M6)** based on shared downstream target regulation:
     - **Module M1 (General Endoderm & Core Lineage Drivers):** *GATA6*, *FOXA2*, *HHEX*, *GLIS3*, *RFX6*, *MNX1*, *NKX2-2*, *HNF4A*, *TET1*, etc.
     - **Module M2 (Chromatin Repressors):** *TLE3*.
     - **Module M3 (Polycomb / Corepressors):** *NEUROD1*, *BCOR*.
     - **Module M4 (Beta Master Selector):** *PDX1*.
     - **Module M5 (Histone Acetyltransferase Complexes):** *TADA2B*.
     - **Module M6 (Endocrine Lineage Directors):** *PAX6*, *PBX1*.
   - Consensus NMF factor decomposition identifies **4 Core Downstream Gene Programs (P1–P4)**:
     - **Program P1:** Endocrine secretion machinery (*PEG10*, *CACNA2D3*, *FGF12*, *AKAP12*, *GAL*).
     - **Program P2:** Hypoxia, metabolic remodeling, and cellular survival (*BNIP3*, *PDE4D*, *WSB1*, *NREP*).
     - **Program P3 & P4:** Progenitor proliferation and extracellular matrix reorganization."""

wip_text = wip_text.replace(old_ds_block, new_ds_block)

# Fix significance overstatement
old_sig = """- **Statistical Significance (DistanceTest):** 1,000 permutations with Benjamini-Hochberg FDR correction.
- **Level of Analysis:** Population-level / Perturbation-level metric.

#### 4. Quantitative Results & Metrics
- **Coverage:** All 36 non-control genotypes successfully evaluated.
- **Statistical Significance:** All 36 genotypes achieved $\\text{FDR} = 0.000999$ ($p < 0.001$, 100% significant)."""

new_sig = """- **Statistical Significance (DistanceTest):** Evaluated via 1,000 permutations against WT controls with Benjamini-Hochberg FDR correction.
- **Level of Analysis:** Population-level / Perturbation-level metric.

#### 4. Quantitative Results & Metrics
- **Coverage:** All 36 non-control genotypes were successfully evaluated.
- **Distributional Divergence:** All 36 tested non-WT perturbations showed statistically significant transcriptomic distributional divergence from WT under DistanceTest.
- **Permutation Resolution Floor:** With 1,000 permutations, the empirical resolution floor is approximately $1 / (N_{\\text{perm}} + 1) = 0.000999$. Consequently, identical permutation-bounded values (FDR = 0.000999) reflect this statistical floor and should not be interpreted as evidence that all perturbations have identical effect strength. Biological effect magnitude must be evaluated directly from the **Energy Distance**, which ranges widely from 1.64 to 13.63."""

wip_text = wip_text.replace(old_sig, new_sig)

# Fix GLIS3 dominant state label
wip_text = wip_text.replace("dominant cell type: ESC/PDP", "dominant cell type: ESC")
wip_text = wip_text.replace("dominant cell type: ESC, fraction = 64.5%", "dominant cell type: ESC (fraction = 64.49%, dominant celltype lochNESS = +13.6254, single-cell Peak lochNESS = +25.5636)")

with open('WIP_scientific_reading.md', 'w') as f:
    f.write(wip_text)
print('Updated WIP_scientific_reading.md')

# 2. Update Master_Scientific_Story.md
with open('Master_Scientific_Story.md', 'r') as f:
    story_text = f.read()

# Fix PS / Mixscape in Master Story
story_text = story_text.replace(
    "Mixscape / PS score isolated true responding cells",
    "Mixscape classification (and per-cell PS scoring) isolated true responding cells"
)
story_text = story_text.replace(
    "DistanceSpace partitions 630 pairwise comparisons into 9 Phenotype Groups (PG1-PG9) and 6 Co-Functional Modules (M1-M6) driven by 4 core gene programs (P1-P4).",
    "DistanceSpace partitions 630 pairwise comparisons into 9 Phenotype Groups (PG1-PG9). Separately, Stage 7 regulatory effect analysis partitions perturbations into 6 Co-Functional Modules (M1-M6) and 4 core downstream gene programs (P1-P4)."
)
story_text = story_text.replace(
    "All 36 evaluated non-control genotypes exhibit statistically significant multivariate divergence from WT (FDR < 0.001).",
    "All 36 tested non-WT perturbations showed significant transcriptomic distributional divergence from WT under DistanceTest (with 1,000 permutations establishing an empirical resolution floor of FDR = 0.000999; effect magnitude is measured by Energy Distance)."
)
story_text = story_text.replace(
    "PDX1het exhibits the #1 highest Energy Distance in the entire dataset (Energy Distance = 13.6337, MMD 0.3129)",
    "PDX1het exhibits the #1 highest Energy Distance in the entire dataset (Energy Distance = 13.6337, MMD = 0.3129), whereas homozygous PDX1 KO exhibits Energy Distance = 2.4579"
)

with open('Master_Scientific_Story.md', 'w') as f:
    f.write(story_text)
print('Updated Master_Scientific_Story.md')

# 3. Update Case_Study_Map.md & Case_Study_Evidence_Audit.md
for fname in ['Case_Study_Map.md', 'Case_Study_Evidence_Audit.md']:
    with open(fname, 'r') as f:
        txt = f.read()
    
    # Fix GLIS3 cell state
    txt = txt.replace("ESC/PDP", "ESC")
    txt = txt.replace("Dominant cell type is ESC/PDP", "Dominant cell type is ESC")
    
    # Fix genotype distinction
    txt = txt.replace(
        "PDX1het = 13.6337 (MMD = 0.3129) (#1 highest in dataset!); PDX1 = 0.0649",
        "PDX1het Energy Distance = 13.6337 (MMD = 0.3129, #1 highest in dataset); PDX1 homozygous Energy Distance = 2.4579 (MMD = 0.0649)"
    )
    txt = txt.replace(
        "PDX1 homozygous KO shows Energy Distance = 2.457885 (MMD = 0.064893, FDR = 0.000999, $n=6,207$ cells).",
        "PDX1 homozygous KO shows Energy Distance = 2.457885 (MMD = 0.064893, FDR = 0.000999, $n=6,207$ cells), whereas PDX1het exhibits Energy Distance = 13.633665 (MMD = 0.312907), demonstrating pronounced dosage-dependent phenotypic divergence."
    )
    
    with open(fname, 'w') as f:
        f.write(txt)
    print(f'Updated {fname}')

# 4. Update Quantitative_Claim_Audit.md
with open('Quantitative_Claim_Audit.md', 'r') as f:
    q_text = f.read()

# Update claim #39 note and PS definitions
q_text = q_text.replace(
    "All FDR = 0.000999",
    "All 36 tested non-WT perturbations significant under DistanceTest; 1,000 permutations impose an empirical resolution floor of FDR = 0.000999"
)
q_text = q_text.replace(
    "peak = 25.563601, dom_ct = ESC, dom_loch = 13.625399",
    "peak = 25.563601, dom_ct = ESC (not PDP), dom_loch = 13.625399"
)

with open('Quantitative_Claim_Audit.md', 'w') as f:
    f.write(q_text)
print('Updated Quantitative_Claim_Audit.md')
