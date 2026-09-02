# -*- coding: utf-8 -*-
import os

content = """# WIP Scientific Reading: Multi-Dimensional Phenotypic Decomposition

**Workspace Context:** `/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/diabetes_specific`  
**Dataset Analyzed:** `diabetes_analysis.h5ad` (111,581 cells × 36,601 genes, 37 genotypes across 14 cell types and 5 differentiation stages).

---

## SECTION 1: CRITICAL DISTINCTION — MANUSCRIPT vs CURRENT WIP EXTENSION

> [!IMPORTANT]
> **Clear Conceptual Boundary:**
> 1. **pertTF Manuscript / Preprint Work:** Introduced the core transformer model, multi-task learning, lochNESS score prediction, generalization benchmarks (unseen contexts / unseen genes), CRISPRi validation using Mixscape/PS filtering, and primary islet transfer learning.
> 2. **Current WIP Extension (diabetes_specific):** Energy Distance, DistanceTest, DistanceSpace, and Co-Functional Module clustering were **NOT** part of the original pertTF manuscript. In the WIP, they are introduced to build a **multi-dimensional phenotypic decomposition framework** that systematically evaluates whether single-cell penetrance (PS), multivariate transcriptomic magnitude (Energy Distance), and state localization (lochNESS) represent orthogonal or coupled biological dimensions.

---

## SECTION 2: SYSTEMATIC DECONSTRUCTION OF WIP ANALYTICAL PILLARS (PHASE 8A)

### Pillar 1: Perturbation Score (PS) — Single-Cell Response Penetrance

#### 1. Scientific Question
What fraction of cells carrying a genetic knockout exhibit a true transcriptomic departure from the unperturbed baseline, and what is the distribution of single-cell response strength?

#### 2. Why This Analysis is Needed
Even in clonal knockout lines or high-efficiency CRISPR experiments, transcriptional responses exhibit cell-to-cell heterogeneity due to cell cycle, stochastic expression bursts, or compensation. PS quantifies single-cell response penetrance.

#### 3. Method & Input Representation
- **Method:** Adapted from the Mixscape framework. For each perturbed cell $i$, PS calculates the probability that the cell has departed from the local control distribution in high-dimensional gene expression space.
- **Input:** Normalized count expression matrix of single cells and target gene expression.
- **Score Range:** Bounded native probability range $[0.0, 1.0]$.
- **Level of Analysis:** Cell-level score, aggregated to perturbation-level (mean PS, median PS, responder fraction where $\text{PS} > 0.5$).

#### 4. Quantitative Results & Metrics
- **Evaluated Genotypes:** 26 single-gene knockout genotypes.
- **Strongest Responders:**
  1. *GLIS3*: Median PS = 0.750, Responder Fraction = 66.6% ($n=935$ cells)
  2. *KDM2B*: Median PS = 0.681, Responder Fraction = 47.8% ($n=182$ cells)
  3. *HHEX*: Median PS = 0.659, Responder Fraction = 59.8% ($n=1,214$ cells)
  4. *GATA6*: Median PS = 0.648, Responder Fraction = 61.6% ($n=1,500$ cells)
  5. *GATA4*: Median PS = 0.622, Responder Fraction = 48.7% ($n=1,612$ cells)
  6. *GSC*: Median PS = 0.607, Responder Fraction = 54.8% ($n=1,652$ cells)
- **Moderate Responders:** *HNF4A* (Median PS = 0.458, 42.0%), *MNX1* (Median PS = 0.467, 41.1%), *ARX* (Median PS = 0.440, 38.3%), *OTUD5* (Median PS = 0.446, 38.2%).

#### 5. Audit of Skipped Genotypes
- Exactly 10 genotypes were skipped in the PS pipeline (`ps_score_skipped.csv`):
  `GATA4het`, `GATA6het`, `HHEXe` (enhancer KO), `HHEXhet`, `HNF4Ahet`, `NANOGe-het`, `ONECUT1e`, `PDX1het`, `QSER1TET1` (double KO), `TET1/2/3` (triple KO).
- **Reason:** The target genotype identifier does not match an individual gene symbol in the RNA expression matrix.
- **Critical Caveat:** Missing PS is an analytical artifact of gene-name lookup, **NOT zero biological response**. (For instance, *PDX1het* has the single highest Energy Distance in the entire dataset!).

---

### Pillar 2: Energy Distance & DistanceTest — Multivariate Phenotypic Magnitude

#### 1. Scientific Question
What is the global statistical magnitude of multivariate transcriptomic divergence between each mutant population and wild-type control cells across the full single-cell manifold?

#### 2. Why This Analysis is Needed
Differential gene expression sums marginal univariate changes, ignoring high-order covariance and manifold geometry. Energy Distance provides a non-parametric, metric-space measure of statistical distance between two multivariate distributions.

#### 3. Method & Input Representation
- **Method:** Calculated in the 50-dimensional PCA space (`X_pca`). Energy Distance between perturbed distribution $P$ and control distribution $Q$ is:
  $$\mathcal{E}(P, Q) = 2 \mathbb{E}[\|X - Y\|] - \mathbb{E}[\|X - X'\|] - \mathbb{E}[\|Y - Y'\|]$$
  where $X, X' \sim P$ and $Y, Y' \sim Q$.
- **Control Baseline:** Bounded subsampling of $N = 5,000$ wild-type cells.
- **Statistical Significance (DistanceTest):** 1,000 permutations with Benjamini-Hochberg FDR correction.
- **Level of Analysis:** Population-level / Perturbation-level metric.

#### 4. Quantitative Results & Metrics
- **Coverage:** All 36 non-control genotypes successfully evaluated.
- **Statistical Significance:** All 36 genotypes achieved $\text{FDR} = 0.000999$ ($p < 0.001$, 100% significant).
- **Strongest Global Phenotype Shifts (Energy Distance):**
  1. *PDX1het*: Energy Distance = 0.3129 ($n=469$ cells)
  2. *HHEXhet*: Energy Distance = 0.2307 ($n=328$ cells)
  3. *KDM2B*: Energy Distance = 0.2087 ($n=182$ cells)
  4. *HHEX*: Energy Distance = 0.2034 ($n=1,214$ cells)
  5. *GLIS3*: Energy Distance = 0.1854 ($n=935$ cells)
  6. *GATA6*: Energy Distance = 0.1590 ($n=1,500$ cells)
  7. *GSC*: Energy Distance = 0.1255 ($n=1,652$ cells)
  8. *QSER1TET1*: Energy Distance = 0.1262 ($n=1,157$ cells)
  9. *HHEXe*: Energy Distance = 0.1227 ($n=1,487$ cells)
  10. *FOXA2*: Energy Distance = 0.1063 ($n=4,896$ cells)
- **Weakest Global Phenotype Shifts:** *PAX6* (0.0381), *PBX1* (0.0386), *TADA2B* (0.0402), *MNX1* (0.0416).

---

### Pillar 3: lochNESS — Directional State Localization and Lineage Trapping

#### 1. Scientific Question
Where on the single-cell developmental manifold do mutant cells specifically accumulate (positive enrichment / trapping) or drop out (negative depletion / lineage failure)?

#### 2. Why This Analysis is Needed
Global distance metrics (like Energy Distance) are scalar magnitudes with no directional or lineage sign. An overall population median of lochNESS is often near zero because a severe mutation causes simultaneous positive trapping in one branch and negative collapse in another. lochNESS resolves signed, state-by-state localization.

#### 3. Method & Input Representation
- **Method:** $k$-nearest-neighbor ($k=30$) local density log2 odds ratio versus WT.
- **Metrics Decomposed:**
  - Positive lochNESS mean / median / Q90 (magnitude of state trapping).
  - Negative lochNESS mean / median / Q10 (magnitude of lineage depletion).
  - lochNESS peak (maximum focal accumulation score in any single cell).
  - Dominant cell-type lochNESS & cell fraction.
- **Level of Analysis:** Cell-level score and cell-state-level distribution.

#### 4. Quantitative Results & Metrics
- **Extreme Focal Trapping (Peak lochNESS):**
  1. *FOXA2*: Peak lochNESS = +13.740 (dominant cell type: Liver, fraction = 34.0%)
  2. *GLIS3*: Peak lochNESS = +13.625 (dominant cell type: PDP, fraction = 64.5%)
  3. *GATA6*: Peak lochNESS = +4.530 (dominant cell type: Endothelial, fraction = 34.5%)
  4. *BMPR1A*: Peak lochNESS = +4.129 (dominant cell type: Stromal, fraction = 34.2%)
  5. *BCOR*: Peak lochNESS = +3.304 (dominant cell type: ESC, fraction = 16.3%)
  6. *ARX*: Peak lochNESS = +3.084 (dominant cell type: SC-alpha, fraction = 23.2%)
- **Profound Negative Depletion:** *PDX1* in SC-beta (lochNESS < -3.8), *RFX6* in SC-beta (lochNESS < -3.5), *PAX6* in SC-beta (lochNESS < -3.2).

---

## SECTION 3: CROSS-METRIC COUPLING & DECOUPLING ANALYSIS (PHASE 8A & PHASE 9)

### Quantitative Correlation Matrix Across Analytical Dimensions

We performed rigorous Spearman rank ($\rho$) and Pearson ($r$) correlation analyses across all evaluated genotypes:

| Pairwise Comparison | $n$ | Spearman $\rho$ | $p$-value (Spearman) | Pearson $r$ | $p$-value (Pearson) | Biological Relationship |
|---|---|---|---|---|---|---|
| **PS vs Energy Distance** | 26 | **+0.6410** | **$4.18 \times 10^{-4}$** | **+0.7628** | **$5.87 \times 10^{-6}$** | **Strongly Coupled** |
| **Energy Dist vs Positive lochNESS Mean** | 36 | **+0.4103** | **$1.29 \times 10^{-2}$** | **+0.5967** | **$1.22 \times 10^{-4}$** | **Moderately Coupled** |
| **Energy Dist vs Negative lochNESS Mean** | 34 | -0.1410 | 0.4263 | +0.0814 | 0.6472 | **Completely Decoupled** |
| **Energy Dist vs Absolute lochNESS Mean** | 36 | **+0.4512** | **$5.74 \times 10^{-3}$** | **+0.6261** | **$4.42 \times 10^{-5}$** | **Moderately Coupled** |
| **PS vs Positive lochNESS Mean** | 26 | +0.0612 | 0.7665 | +0.2562 | 0.2065 | **Completely Decoupled** |
| **PS vs Negative lochNESS Mean** | 25 | -0.1715 | 0.4123 | -0.1973 | 0.3444 | **Completely Decoupled** |
| **PS vs Absolute lochNESS Mean** | 26 | +0.1214 | 0.5548 | +0.2876 | 0.1543 | **Completely Decoupled** |
| **Energy Dist vs Peak lochNESS** | 36 | +0.2178 | 0.2020 | +0.3782 | 0.0229 | **Weakly Coupled** |
| **PS vs Peak lochNESS** | 26 | -0.0400 | 0.8462 | +0.0782 | 0.7041 | **Completely Decoupled** |

```
                       PHENOTYPIC DIMENSION COUPLING MATRIX

             [ PS (Single-Cell Penetrance) ]
                           │
                           │  Spearman ρ = +0.641 (p = 4.2e-4)
                           │  [STRONG COUPLING]
                           ▼
          [ Energy Distance (Global Magnitude) ]
                           │
                           ├─ Spearman ρ = +0.451 (p = 0.0057) ──► [ Absolute lochNESS ]
                           │
                           └─ Spearman ρ = -0.141 (p = 0.426)  ──► [ Negative lochNESS ]
                                                                   (DECOUPLED)

   ─────────────────────────────────────────────────────────────────────────────
   [ PS (Penetrance) ] ── Spearman ρ = +0.061 (p = 0.766) ──► [ lochNESS (Localization) ]
                               (COMPLETE DECOUPLING)
```

---

## SECTION 4: THE CONCEPTUAL BRIDGE — FROM pertTF TO WIP (PHASE 9)

### What pertTF Achieved vs What Remained Compressed
- **pertTF Prediction Capability:** pertTF demonstrated that a transformer can accurately predict gene expression profiles, cell embeddings, cell-type classification, and lochNESS scores across unseen contexts.
- **The Unresolved Compression:** While pertTF *predicts* these outcomes, an end-to-end neural network compresses multiple biological phenomena into a single latent vector. It does not explicitly tell the biologist:
  - Is a large transcriptomic shift driven by high penetrance (many cells responding mildly) or extreme focal trapping (a subset converting to a radically foreign fate)?
  - Why do some master regulators (like *PAX6*) have modest global Energy Distance (0.038) yet produce complete lineage collapse of SC-beta and dramatic SC-EC diversion?

### The Multi-Dimensional Decomposition Solution
The WIP demonstrates that perturbation phenotypes must be decomposed into **three orthogonal, complementary coordinates**:
1. **Response Penetrance (PS):** The single-cell probability of leaving the ground state.
2. **Multivariate Phenotypic Magnitude (Energy Distance):** The global statistical displacement of the population distribution in transcriptomic space.
3. **Directional State Localization (Signed lochNESS):** The localized topological enrichment ($>0$, trapping) or depletion ($<0$, lineage dropout) on the developmental manifold.

### Higher-Order Manifold Structure: DistanceSpace, Modules, and Gene Programs
- **DistanceSpace:** Constructs a $36 \times 36$ pairwise phenotypic distance matrix (630 pairwise comparisons) partitioning genotypes into **9 Phenotype Groups (PG1–PG9)**.
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
  - **Program P3 & P4:** Progenitor proliferation and extracellular matrix reorganization.

### Future Impact on Perturbation Modeling
Integrating these decomposed coordinates (PS, Energy Distance, signed lochNESS) into the next generation of pertTF loss functions will enable **phenotype-aware foundation models** that predict not just static expression vectors, but complete multi-dimensional phenotypic manifolds.
"""

with open('WIP_scientific_reading.md', 'w') as f:
    f.write(content)
print('Successfully wrote WIP_scientific_reading.md, length:', len(content))
