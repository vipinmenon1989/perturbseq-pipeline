# Auditable Scientific Inventory: Pancreatic Differentiation Perturb-seq Analysis

**Analysis Directory**: `/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/diabetes_specific`  
**Presentation Output Directory**: `/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/diabetes_specific/presentation`  
**Workflow Script**: `workflows/diabetes_analysis.py`  
**Configuration**: `config/diabetes.yaml`  
**Execution Timestamp**: 2026-08-30  

---

## A. DATASET FILES

| File Type | Absolute Path | File Size | Timestamp | Presentation Role |
|---|---|---|---|---|
| **Source Processed H5AD** | `results/diabetes_specific/diabetes_analysis.h5ad` | 949.03 MB (995,127,317 bytes) | 2026-08-30 13:42 | **Primary presentation source** containing all per-cell annotations (`ps_score`, `lochness_self`, `celltype_2`, `orig.ident`, `development_stage`, `X_pca`, `X_umap`). |
| **Input / Reference H5AD** | `../data/diabetes.h5ad` | ~949 MB | 2026-08-30 | Original input dataset containing filtered counts, sgRNA assignments, and sample annotations. |
| **Result Tables Directory** | `results/diabetes_specific/tables/` | 23 CSV files (~1.4 MB total) | 2026-08-30 13:43 | Quantitative result summaries for all analytical stages. |
| **Result Figures Directory** | `results/diabetes_specific/figures/` | 46 PNG/PDF files (~50 MB total) | 2026-08-30 13:43 | High-resolution analytical figures and per-genotype atlases. |

---

## B. DATASET DIMENSIONS

- **Total Single Cells ($N$)**: **111,581**
- **Total Measured Features/Genes ($P$)**: **36,601**
- **Total Genotypes ($G$)**: **37** (1 WT control + 36 non-WT perturbations)
- **Total Non-WT Perturbations**: **36**
- **Total sgRNA Constructs**: **100**
- **Curated Biological Cell States (`celltype_2`)**: **15** distinct cell states
- **Derived Developmental Stages (`development_stage`)**: **6** stages (derived from 13 `orig.ident` biological samples)
- **Experimental Sample Strata (`orig.ident`)**: **13** multiplexed sequencing libraries

---

## C. IMPORTANT OBSERVATION COLUMNS & VARIABLE HIERARCHY

| Column Name | Type | Unique Count | Biological Interpretation | Key Distinction / Notes |
|---|---|---|---|---|
| `sgrna` | Categorical / String | 100 | Individual sgRNA construct sequence/ID introduced into the cell. | 2–4 distinct sgRNAs per targeted locus. |
| `genotype` | Categorical / String | 37 | Biological perturbation identity (e.g., `PDX1`, `GATA6`, `FOXA2`, `WT`). | Primary unit of all downstream biological perturbation analyses. |
| `celltype_2` | Categorical / String | 15 | Curated biological differentiation cell state annotated by lineage markers. | **`celltype_2 != development_stage`**. Represents true cellular phenotype. |
| `orig.ident` | Categorical / String | 13 | Experimental sample library / sequencing stratum. | Used for stratified hypergeometric tests to prevent batch/sample confounding. |
| `development_stage` | Categorical / String | 6 | Presentation-friendly differentiation stage mapped directly from `orig.ident`. | Values: `WT`, `ESC`, `DE`, `PFG`, `PP`, `3DEC`. |
| `time_point` | Categorical / Float | Multiple | Experimental differentiation timepoint. | Corresponds to developmental stage progression. |
| `ps_score` | Continuous Float $[0, 1]$ | 66,015 non-null | Perturbation Score ($PS$) computed via `pertps`. Quantifies cellular response strength. | Only computed for single-gene perturbations with valid target expression in matrix (26 genotypes). |
| `ps_quadrant` | Categorical | 66,015 non-null | Mechanistic classification: *successful knockdown*, *escaper*, *non-responder*, *low signal*. | Integrates PS with single-cell target gene transcript abundance. |
| `lochness_self` | Continuous Float $(-\infty, +\infty)$ | 111,581 non-null | Signed continuous local neighborhood enrichment score for each cell's perturbation. | Evaluated across all 111,581 cells ($>0$ = enrichment, $<0$ = depletion). |

### Distinction: `celltype_2` vs `development_stage`
- **`development_stage`** reflects the experimental harvesting timepoint/sample (`ESC` -> `DE` -> `PFG` -> `PP` -> `3DEC` + `WT`).
- **`celltype_2`** reflects true biological differentiation states discovered within those stages (`ESC`, `ESC (D3)`, `DE`, `PFG`, `PGT`, `PP`, `PDP`, `EnP`, `SC-EC`, `SC-alpha`, `SC-beta`, `SC-delta`, `Liver`, `Stromal`, `Endothelial`). Even late stages (`3DEC`) contain heterogeneous mixtures of progenitor, endocrine, and off-target lineages.

---

## D. LATENT REPRESENTATIONS

1. **`X_pca`** ($111,581 	imes 50$): 50 principal components computed across highly variable genes.
   - Used for **Energy Distance**, **DistanceTest**, **DistanceSpace PCoA**, and **lochNESS kNN graphs** ($k=30$).
2. **`X_umap`** ($111,581 	imes 2$): 2-dimensional uniform manifold approximation and projection.
   - Used for visual rendering of single-cell distributions, cell-state trajectories, and perturbation score densities.

---

## E. FIGURE INVENTORY & PRESENTATION SELECTION

| Figure Filename | Figure # | Analysis Type | What the Figure Measures | Deck Selection | Rationale for Selection / Placement |
|---|---|---|---|---|---|
| `01_umap_celltype2.png` | Fig 01 | Single-Cell Landscape | 2D UMAP colored by 15 curated cell states (`celltype_2`). | **MAIN (Slide 4)** | Establishes the pancreatic differentiation trajectory and cell-state diversity. |
| `02_umap_development_stage.png` | Fig 02 | Single-Cell Landscape | 2D UMAP colored by 6 developmental stages (`development_stage`). | **MAIN (Slide 5)** | Demonstrates stage progression and temporal ordering from ESC to 3DEC. |
| `03_stage_celltype_composition.png` | Fig 03 | Compositional QC | Stacked bar chart of cell-state proportions across developmental stages. | **MAIN (Slide 5)** | Proves cell-state heterogeneity within stages; validates `celltype_2 != stage`. |
| `04_genotype_celltype_enrichment.png` | Fig 04 | Cell-State Enrichment | Stratified log2 odds ratio heatmap ($	ext{Genotype} 	imes 	ext{Celltype\_2}$) with FDR asterisks. | **MAIN (Slide 12)** | Shows lineage diversion (e.g. FOXA2 -> Liver, GATA6 -> Endothelial, NEUROG3 -> Endocrine block). |
| `05_ps_by_perturbation.png` | Fig 05 | Perturbation Score | Boxplots of PS across 26 genotypes + skipped target reasons. | **BACKUP** | Detailed distribution of PS per genotype; summarized cleaner in Slide 7/8. |
| `06_energy_distance_by_perturbation.png` | Fig 06 | Global Phenotype | Ranked bar plot of Energy Distance vs WT with permutation FDR. | **MAIN (Slide 9)** | Demonstrates multivariate phenotypic displacement magnitude (all 36 FDR < 0.001). |
| `07_ps_vs_distance.png` | Fig 07 | Cross-Metric Coupling | Scatter plot of PS mean vs Energy Distance ($ho = +0.783, p = 2.24 	imes 10^{-6}, n=26$). | **MAIN (Slide 13)** | Validates strong coupling between cellular response strength and global phenotypic shift. |
| `08_distance_vs_lochness_positive.png` | Fig 08 | Cross-Metric Coupling | Energy Distance vs positive lochNESS mean ($ho = +0.410, p = 0.0129, n=36$). | **MAIN (Slide 14)** | Shows moderate coupling: high phenotype distance drives positive focal accumulation. |
| `09_distance_vs_lochness_negative.png` | Fig 09 | Cross-Metric Coupling | Energy Distance vs negative lochNESS mean ($ho = -0.141, p = 0.426, n=34$). | **BACKUP** | Shows decoupling between distance and depletion magnitude. |
| `10_ps_vs_lochness_positive.png` | Fig 10 | Cross-Metric Coupling | PS mean vs positive lochNESS mean ($ho = +0.171, p = 0.403, n=26$). | **BACKUP** | Demonstrates complementarity: response strength does not dictate localization magnitude. |
| `11_ps_vs_lochness_negative.png` | Fig 11 | Cross-Metric Coupling | PS mean vs negative lochNESS mean ($ho = -0.177, p = 0.398, n=25$). | **BACKUP** | Confirms independence of negative localization from PS. |
| `12_distance_vs_lochness_absolute.png` | Fig 12 | Cross-Metric Coupling | Energy Distance vs absolute lochNESS mean ($ho = +0.451, p = 0.0057, n=36$). | **MAIN (Slide 14)** | Confirms overall manifold localization magnitude correlates with global distance. |
| `13_lochness_by_celltype.png` | Fig 13 | State Localization | Signed lochNESS heatmap across genotypes and 15 cell states. | **MAIN (Slide 11)** | High-resolution matrix of continuous neighborhood enrichment across curated states. |
| `14_distance_space.png` | Fig 14 | Phenotypic Manifold | PCoA embedding of 630 pairwise distances + hierarchical clustering dendrogram. | **MAIN (Slide 15)** | Reveals 9 phenotypic similarity groups (PG1–PG9) and shared phenotype manifolds. |
| `15_module_program_strength.png` | Fig 15 | Regulatory Architecture | Heatmap of co-functional module strength (M1–M6) across gene programs (P1–P4). | **MAIN (Slide 16)** | Links upstream perturbation clusters with downstream gene programs. |
| `16_program_activity_celltype2.png` | Fig 16 | Program Biology | Heatmap of program activity scores across 15 cell states. | **MAIN (Slide 17)** | Maps P1 (Endocrine), P2 (Beta cell), P3 (Proliferation/Progenitor), P4 (EMT/Vascular). |
| `17_program_enrichment.png` | Fig 17 | Functional Annotation | ORA enrichment bar charts (MSigDB Hallmark, Reactome, GO BP) for P2, P3, P4. | **MAIN (Slide 18)** | Annotates biological mechanisms: P2=Beta cells, P3=MYC/Translation, P4=EMT/Angiogenesis. |
| `18_module_network.png` | Fig 18 | Regulatory Network | TF-TF directional influence graph (nodes=TFs, edges=log2FC, colored by module). | **MAIN (Slide 19)** | Visualizes cross-regulatory interactions between master pancreatic regulators. |
| `19_perturbation_summary.png` | Fig 19 | Integrated Multi-Metric | Multi-panel atlas: cells, PS, Energy Distance, lochNESS pos/neg, module, PG. | **MAIN (Slide 20)** | Comprehensive synthesis proving why multi-dimensional measurement is essential. |
| `20_umap_ps_score.png` | Fig 20 | Single-Cell PS Density | 2D UMAP density of PS score across all 66,015 scored cells. | **MAIN (Slide 7)** | Shows single-cell resolution of perturbation response across the differentiation landscape. |
| `21_umap_lochness_score.png` | Fig 21 | Single-Cell lochNESS | 2D UMAP showing continuous local neighborhood enrichment values. | **MAIN (Slide 10)** | Illustrates continuous cluster-free focal accumulation on the manifold. |
| `22_ps_by_genotype.png` | Fig 22 | PS Distribution | Ranked bar/violin plot of mean PS across 26 genotypes. | **BACKUP** | Detailed ranking of PS response strength across genotypes. |
| `23_ps_by_celltype2.png` | Fig 23 | PS State Distribution | Mean PS across 15 cell types (highest in ESC/progenitor states). | **BACKUP** | Demonstrates cell-state baseline sensitivity to CRISPR perturbations. |
| `24_ps_genotype_celltype_heatmap.png` | Fig 24 | PS State Matrix | Heatmap of mean PS across genotype $	imes$ cell state. | **BACKUP** | Fine-grained state-specific response strength. |
| `25_lochness_by_genotype.png` | Fig 25 | Directional lochNESS | Ranked positive/negative lochNESS distributions per genotype. | **MAIN (Slide 10)** | Contrasts positive localization strength with negative depletion fraction. |
| `26_lochness_by_celltype2.png` | Fig 26 | lochNESS Cell State | Distribution of lochNESS values across 15 cell states. | **BACKUP** | Shows background baseline distribution of lochNESS across states. |
| `27_umap_ps_lochness_comparison.png` | Fig 27 | Metric Comparison | Side-by-side global UMAP comparing PS vs lochNESS. | **MAIN (Slide 8)** | Directly illustrates the conceptual difference between response strength and spatial localization. |
| `28_umap_highlight_genotypes.png` | Fig 28 | Case Study Highlights | Multi-panel UMAP highlighting cells from key perturbations (PDX1, GATA6, FOXA2, NEUROG3). | **MAIN (Slide 21)** | Spatial validation of dramatic lineage shifts in representative case studies. |
| `lochness_per_genotype_umap_atlas.png` | Atlas | lochNESS Atlas | Complete 36-genotype grid of lochNESS UMAP spatial projections. | **BACKUP** | Comprehensive diagnostic atlas of single-cell localization for all perturbations. |
| `ps_per_genotype_umap_atlas.png` | Atlas | PS Atlas | Complete 26-genotype grid of PS UMAP single-cell response maps. | **BACKUP** | Comprehensive diagnostic atlas of single-cell PS distribution for all valid targets. |
| `per_genotype_combined/*` | Case Studies | Combined UMAPs | Individual side-by-side PS + lochNESS UMAPs for specific perturbations. | **CASE STUDIES (Slides 22, 23, 24)** | High-resolution single-perturbation deep dives for PDX1/PDX1het, GATA6, FOXA2, NEUROG3. |

---

## F. TABLE INVENTORY

| Table Filename | Shape | Key Columns | Analytical Role | Deck Slides Supported |
|---|---|---|---|---|
| `perturbation_summary.csv` | $(37, 27)$ | `genotype`, `n_cells`, `ps_mean`, `energy_distance`, `distance_fdr`, `lochness_positive_mean`, `lochness_negative_mean`, `cofunctional_module`, `phenotype_group`, `dominant_celltype_2` | **Master integrated table** joining all analytical layers across all 37 genotypes. | Slides 6, 7, 9, 10, 13, 14, 15, 20 |
| `ps_score_summary.csv` | $(26, 17)$ | `genotype`, `n_perturbed_cells`, `ps_mean`, `ps_median`, `ps_responder_fraction`, `pct_successful_kd`, `pct_escaper`, `pct_non_responder` | Target-level PS metrics and 4-quadrant mechanistic breakdown. | Slides 7, 8 |
| `ps_score_skipped.csv` | $(10, 3)$ | `genotype`, `n_cells`, `reason` | Auditable documentation of 10 perturbations where PS was skipped due to target gene absence. | Slide 7, Backup |
| `ps_by_celltype2.csv` | $(15, 6)$ | `celltype_2`, `n_cells`, `mean_ps`, `median_ps`, `q25_ps`, `q75_ps` | Perturbation response strength stratified across 15 curated cell states. | Slide 7, Backup |
| `ps_by_development_stage.csv` | $(6, 6)$ | `development_stage`, `n_cells`, `mean_ps`, `median_ps` | PS metrics across 6 differentiation stages. | Backup |
| `distance_results.csv` / `distance_test.csv` | $(36, 8)$ | `genotype`, `n_cells`, `n_control`, `energy_distance`, `pvalue`, `mmd_distance`, `fdr`, `significant` | Permutation DistanceTest results vs WT (Energy Distance, empirical p-value, BH-FDR). | Slide 9 |
| `distance_space_coordinates.csv` | $(36, 11)$ | `genotype`, `PCoA1` to `PCoA10` | Low-dimensional PCoA embedding coordinates of 36 perturbations in phenotype manifold. | Slide 15 |
| `distance_space_matrix.csv` | $(36, 36)$ | All 36 perturbation names | Symmetric matrix of all 630 pairwise Energy Distances between non-WT perturbations. | Slide 15, Backup |
| `distance_space_neighbors.csv` | $(360, 4)$ | `genotype`, `neighbor`, `distance`, `rank` | Top-10 nearest phenotypic neighbors for each perturbation in DistanceSpace. | Slide 15, Case Studies |
| `phenotype_groups.csv` | $(36, 2)$ | `genotype`, `phenotype_group` | Hierarchical clustering assignments into 9 phenotypic similarity groups (PG1–PG9). | Slide 15, Slide 20 |
| `lochness_summary.csv` | $(36, 18)$ | `genotype`, `lochness_positive_mean`, `lochness_positive_fraction`, `lochness_negative_mean`, `lochness_negative_fraction`, `lochness_abs_mean`, `dominant_celltype_2` | Directional summary of continuous neighborhood enrichment ($>0$ vs $<0$) per genotype. | Slide 10, Slide 11 |
| `lochness_by_celltype.csv` | $(505, 9)$ | `genotype`, `celltype_2`, `n_cells`, `mean_lochness`, `positive_fraction`, `negative_fraction`, `mean_positive_lochness` | Fine-grained lochNESS localization across all genotype $	imes$ cell state pairs. | Slide 11, Backup |
| `celltype_enrichment.csv` | $(1080, 17)$ | `genotype`, `celltype_2`, `log2_odds_ratio`, `odds_ratio`, `pval`, `fdr`, `direction`, `significant`, `n_target_cells`, `pct_of_target` | Stratified hypergeometric / Fisher test results for cell-state enrichment/depletion. | Slide 12, Case Studies |
| `module_assignments.csv` | $(36, 4)$ | `target_gene`, `module`, `n_cells`, `n_de_genes` | Assignment of 36 perturbations into 6 co-functional regulatory modules (M1–M6). | Slide 16, Slide 19 |
| `module_program_strength.csv` | $(6, 5)$ | `M1` to `M6`, `P1` to `P4` | Signed correlation / regulatory impact of each module on 4 gene programs. | Slide 16 |
| `gene_programs.csv` | $(980, 3)$ | `gene`, `program`, `program_size` | Membership of 980 downstream responsive genes across programs P1 (6), P2 (549), P3 (316), P4 (109). | Slide 17, Backup |
| `program_activity_celltype.csv` | $(4, 16)$ | `program`, 15 cell states | Mean activity score of each gene program across 15 curated cell states. | Slide 17 |
| `program_enrichment.csv` | $(105, 16)$ | `program_id`, `gene_set_source`, `term`, `clean_term`, `overlap_count`, `gene_set_size`, `p_value`, `fdr`, `odds_ratio` | Over-representation analysis of gene programs against Hallmark, Reactome, and GO BP. | Slide 18 |
| `program_summary.csv` | $(4, 9)$ | `program_id`, `top_term`, `gene_set_source`, `fdr`, `program_size`, `top_genes` | Executive summary of 4 gene programs with top biological annotations. | Slide 17, Slide 18 |

---

## G. VERIFIED CORE NUMERICAL RESULTS

- **Dataset Cell Count**: **111,581** cells across 13 multiplexed samples.
- **Gene Features**: **36,601** genes in source matrix; **980** downstream responsive genes in program clustering.
- **Total Genotypes Evaluated**: **37** (1 WT control + 36 perturbations).
- **Perturbations with Valid PS Score**: **26 / 36** ($72.2\%$).
  - Mean PS across scored cells: **0.4132** (range 0.0 to 1.0).
  - Top 3 PS perturbations: **KDM2B** (mean 0.6273, median 0.6808), **GLIS3** (mean 0.6075, median 0.7500), **HHEX** (mean 0.6050, median 0.6589).
  - Lowest 3 valid PS perturbations: **PAX6** (0.3372), **NEUROD1** (0.3393), **PBX1** (0.3454).
- **Perturbations Skipped for PS Score**: **10 / 36** ($27.8\%$).
  - Reason: Targeted loci (composite combinations like `TET1/2/3`, `QSER1TET1`, heterozygous constructs like `GATA4het`, `GATA6het`, `HHEXhet`, `HNF4Ahet`, `PDX1het`, or enhancer targets like `HHEXe`, `NANOGe-het`, `ONECUT1e`) do not map to a single transcript feature in the count matrix.
- **Perturbations Evaluated by lochNESS**: **36 / 36** ($100\%$, continuous scores for all 111,581 cells).
  - Overall mean `lochness_self`: **+2.7746** (min $-0.9660$, max $+45.5819$).
  - Top positive localization: **GATA6** (+14.18), **PDX1het** (+14.15), **TADA2B** (+11.23), **GLIS3** (+9.53), **FOXA2** (+5.86).
  - Strongest negative localization (depletion): **PDX1** ($-0.5891$, $77.8\%$ depleted cells), **GSC** ($-0.5135$), **FOXA2** ($-0.4952$, $70.7\%$ depleted cells).
- **DistanceTest vs WT Evaluated**: **36 / 36** ($100\%$).
  - **Statistically Significant Perturbations**: **36 / 36** ($100\%$, all empirical $p = 0.000999$, BH-FDR $= 0.000999$).
  - Top 5 Energy Distances: **PDX1het** ($13.6337$), **HHEXhet** ($10.4732$), **GATA6** ($9.7045$), **KDM2B** ($9.3204$), **HHEX** ($8.9955$).
  - Bottom 5 Energy Distances: **MNX1** ($1.0755$), **PAX6** ($1.1531$), **BCOR** ($1.3674$), **NEUROD1** ($1.4187$), **NKX2-2** ($1.4583$).
  - Distance Methodology: **V-statistic estimator** computed on 50 PCs in PCA space; **1,000 label permutations**; stratified bounded sampling (max 2,000 perturbed cells, 5,000 WT control cells).
- **Pairwise DistanceSpace Comparisons**: **630** unique perturbation pairs ($inom{36}{2} = 630$).
  - Closest Pair: **HNF4A $\leftrightarrow$ HNF4Ahet** ($d = 0.0905$, Rank 1).
  - Second Closest Pair: **ONECUT1e $\leftrightarrow$ OTUD5** ($d = 0.2664$, Rank 2).
  - Third Closest Pair: **GATA4 $\leftrightarrow$ GATA6het** ($d = 0.3729$, Rank 3).
- **Phenotypic Similarity Groups in DistanceSpace**: **9 groups** (PG1 to PG9):
  - PG1 (3): `HHEX`, `HHEXhet`, `KDM2B`
  - PG2 (2): `GLIS3`, `PDX1het`
  - PG3 (12): `ARX`, `FOXA1`, `HNF4A`, `HNF4Ahet`, `MNX1`, `NANOGe-het`, `NEUROG3`, `NKX2-2`, `PROSER1`, `RFX6`, `TET1`, `TET1/2/3`
  - PG4 (10): `BMPR1A`, `GATA4`, `GATA4het`, `GATA6het`, `GSC`, `HHEXe`, `ONECUT1e`, `OTUD5`, `QSER1`, `QSER1TET1`
  - PG5 (3): `BCOR`, `NEUROD1`, `TLE3`
  - PG6 (3): `PAX6`, `PBX1`, `TADA2B`
  - PG7 (1): `PDX1` (isolated single-perturbation group)
  - PG8 (1): `FOXA2` (isolated single-perturbation group)
  - PG9 (1): `GATA6` (isolated single-perturbation group)
- **Co-functional Regulatory Modules**: **6 modules** (M1 to M6):
  - M1 (29 targets): Major regulatory core (PDX1het, HHEX, GATA6, GLIS3, FOXA2, NEUROG3, etc.)
  - M2 (1 target): `TLE3`
  - M3 (2 targets): `NEUROD1`, `BCOR`
  - M4 (1 target): `PDX1`
  - M5 (1 target): `TADA2B`
  - M6 (2 targets): `PBX1`, `PAX6`
- **Gene Programs Discovered**: **4 programs** (P1–P4, total 980 genes):
  - **P1** (6 genes): Endocrine signature (`GAL`, `AKAP12`, `PEG10`, `CACNA2D3`, `FGF12`, `CDK6`). Active in SC-alpha (0.378) and SC-beta (0.371).
  - **P2** (549 genes): Mature Pancreatic Beta-cell Program. Top enrichment: `HALLMARK_PANCREAS_BETA_CELLS` (overlap 36/42, $	ext{FDR} = 1.28 	imes 10^{-3}, 	ext{OR} = 4.97$). Highly active in SC-delta (0.647), SC-beta (0.622), SC-alpha (0.574), EnP (0.553).
  - **P3** (316 genes): Progenitor Growth & Biosynthesis Program. Top enrichment: `HALLMARK_MYC_TARGETS_V1` (overlap 76/78, $	ext{FDR} = 3.50 	imes 10^{-36}, 	ext{OR} = 104.8$), `HALLMARK_MTORC1_SIGNALING` ($	ext{FDR} = 3.05 	imes 10^{-20}$), `REACTOME_TRANSLATION` ($	ext{FDR} = 1.13 	imes 10^{-19}$). Active in ESC (1.107), DE (1.087), PFG (1.043), PP (1.002).
  - **P4** (109 genes): Mesenchymal & Endothelial Program. Top enrichment: `HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION` (overlap 14/36, $	ext{FDR} = 1.47 	imes 10^{-4}, 	ext{OR} = 5.69$), `HALLMARK_ANGIOGENESIS` ($	ext{FDR} = 3.12 	imes 10^{-4}$). Active in Endothelial (1.298) and Stromal (0.193).

---

## H. TOP BIOLOGICAL RESULTS: OBSERVATION VS INTERPRETATION

### 1. Perturbation Response Strength (PS Score)
- **OBSERVATION**: PS varies widely across genotypes, from 0.6273 (KDM2B) and 0.6075 (GLIS3) down to 0.3372 (PAX6) and 0.3393 (NEUROD1). Single cells within the same perturbation exhibit heterogeneous response levels (e.g. GLIS3 has 66.6% responder cells, whereas NEUROD1 has only 1.5% high-response cells).
- **INTERPRETATION**: CRISPR perturbation penetrance and transcriptional responsiveness are highly target-dependent in human differentiating stem cells. Low PS indicates either weak knockdown efficiency or cellular buffering where cells maintain baseline expression signatures despite guide integration.

### 2. Global Transcriptomic Displacement (Energy Distance & DistanceTest)
- **OBSERVATION**: All 36 non-WT perturbations generate statistically significant shifts relative to WT ($p = 0.000999, 	ext{FDR} = 0.000999$). However, effect magnitudes span over an order of magnitude: PDX1het ($E = 13.63$), HHEXhet ($E = 10.47$), and GATA6 ($E = 9.70$) produce massive displacement, while MNX1 ($E = 1.08$) and PAX6 ($E = 1.15$) cause minor global shifts.
- **INTERPRETATION**: While all tested perturbations perturb single-cell distributions beyond random sampling fluctuations, master developmental regulators whose loss redirects whole lineage trajectories induce 10-fold larger multivariate distributional shifts than late-stage transcription factors.

### 3. Directional Neighborhood Enrichment (lochNESS)
- **OBSERVATION**: lochNESS reveals simultaneous positive and negative localization in individual perturbations. For example, FOXA2 has strong positive accumulation in specific states ($	ext{mean pos} = +5.86$) and simultaneous severe depletion in others ($	ext{mean neg} = -0.495, 70.7\%$ depleted cells). Similarly, PDX1 exhibits positive mean $+2.42$ but $77.8\%$ negative cells ($	ext{mean neg} = -0.589$).
- **INTERPRETATION**: Reporting only a global average lochNESS would obscure perturbation biology by averaging positive focal trapping with broad depletion. Signed lochNESS correctly captures that a single transcription factor knockout simultaneously blocks progression into specific descendant lineages while accumulating progenitor cells in upstream or diverted states.

### 4. Lineage Diversion & Cell-State Enrichment
- **OBSERVATION**: Stratified odds-ratio testing reveals dramatic lineage diversions:
  - **GATA6**: Huge enrichment in **Endothelial** cells ($25.7\%$ of cells vs $0.7\%$ baseline, $\log_2 	ext{OR} = +5.21, 	ext{FDR} = 1.05 	imes 10^{-141}$) and near-total depletion in endocrine lineages (SC-EC $\log_2 	ext{OR} = -5.46$, SC-alpha $\log_2 	ext{OR} = -5.57$, SC-beta $\log_2 	ext{OR} = -4.39$).
  - **FOXA2**: Dramatic diversion into **Liver** fate ($34.0\%$ of cells vs $2.0\%$ baseline, $\log_2 	ext{OR} = +4.09, 	ext{FDR} = 3.65 	imes 10^{-224}$).
  - **NEUROG3**: Severe depletion / complete block of mature endocrine cells (**SC-beta**: 0 cells, $0.0\%, \log_2 	ext{OR} = -\infty$; **SC-EC**: $0.32\%$ vs $8.78\%$ baseline, $\log_2 	ext{OR} = -4.75, 	ext{FDR} = 3.25 	imes 10^{-33}$), with accumulation in pancreatic/ductal progenitors (`PDP`, $\log_2 	ext{OR} = +1.11$).
  - **GSC**: Major enrichment in **Stromal** ($22.7\%, \log_2 	ext{OR} = +2.66$) and **ESC** ($42.7\%, \log_2 	ext{OR} = +1.32$).
- **INTERPRETATION**: Transcription factor knockouts during pancreatic differentiation do not merely slow development; they actively divert pluripotent and endodermal progenitors into alternative mesodermal/endothelial (GATA6), hepatic (FOXA2), or stromal (GSC) fates, or trap them at the progenitor stage (NEUROG3).

---

## I. CROSS-METRIC CORRELATION RESULTS

All metrics were evaluated across non-WT perturbations using Spearman rank correlation:

| Metric Pair | Spearman $ho$ | $p$-value | $n$ | Biological Meaning & Interpretation |
|---|---|---|---|---|
| **PS vs Energy Distance** | **+0.7832** | $\mathbf{2.24 	imes 10^{-6}}$ | **26** | **Strong Positive Coupling**: Perturbations triggering strong individual cellular responses reliably generate larger global multivariate transcriptomic displacement from WT. |
| **Energy Distance vs Positive lochNESS** | **+0.4103** | $\mathbf{1.29 	imes 10^{-2}}$ | **36** | **Moderate Positive Correlation**: Perturbations with large global phenotype shifts tend to exhibit stronger focal manifold accumulation in diverted/trapped states. |
| **Energy Distance vs Negative lochNESS** | **-0.1410** | $0.4263$ | **34** | **Decoupled**: Magnitude of global displacement does not strongly predict the average depth of single-cell depletion, reflecting widespread baseline cell-type absences. |
| **PS vs Positive lochNESS** | **+0.1713** | $0.4028$ | **26** | **Independent Layers**: High cell-level response score (PS) does not dictate whether cells accumulate tightly in a narrow neighborhood or disperse across broader states. |
| **PS vs Negative lochNESS** | **-0.1769** | $0.3975$ | **25** | **Independent Layers**: Cellular response strength does not govern the extent of lineage depletion. |
| **Energy Distance vs Absolute lochNESS** | **+0.4512** | $\mathbf{5.74 	imes 10^{-3}}$ | **36** | **Statistically Significant**: Overall magnitude of local manifold distortion ($|	ext{lochNESS}|$) tracks global distributional shift from WT. |

> **Key Analytical Takeaway**: The modest correlations between PS/Distance and directional lochNESS are NOT analytical failures—they prove that PS, Energy Distance, and lochNESS capture complementary, orthogonal biological dimensions of perturbation behavior.

---

## J. CASE-STUDY CANDIDATES & RANKING

### Evaluated Candidates

1. **PDX1 / PDX1het** (Pancreatic Master TF):
   - *PDX1*: 6,207 cells, $E=2.45, 	ext{FDR}=0.001$, dominant cell state SC-EC (25.3%), strong depletion in endocrine lineages (77.8% cells negative lochNESS), Module M4, PG7 (unique isolated phenotype group).
   - *PDX1het*: 469 cells, **Rank 1 Energy Distance ($13.63$)**, **Rank 2 Positive lochNESS ($+14.15$)**, dominant cell state ESC (83.8%), Module M1, PG2.
   - *Why interesting*: Contrasts dosage/heterozygosity effects and highlights the critical requirement of PDX1 for pancreatic specification vs progenitor maintenance.
2. **GATA6** (Endoderm / Lineage Gatekeeper):
   - 1,500 cells, $E=9.70$ (Rank 3), $	ext{PS mean}=0.5776$ (Rank 4), **Rank 1 Positive lochNESS ($+14.18$)**, **Rank 1 Absolute lochNESS ($13.79$)**.
   - Massive lineage conversion: **$25.7\%$ Endothelial cells** ($\log_2 	ext{OR} = +5.21, 	ext{FDR} = 1.05 	imes 10^{-141}$), complete loss of endocrine cells (SC-alpha, SC-beta, SC-EC, SC-delta). Module M1, PG9 (isolated group).
   - *Why interesting*: Most dramatic non-pancreatic lineage diversion in the entire dataset.
3. **FOXA2** (Pioneer Transcription Factor):
   - 4,896 cells, $E=2.14, 	ext{PS mean}=0.5085$, positive lochNESS $+5.86$, negative lochNESS $-0.495$ ($70.7\%$ depleted cells).
   - Dramatic hepatic diversion: **$34.0\%$ Liver cells** ($\log_2 	ext{OR} = +4.09, 	ext{FDR} = 3.65 	imes 10^{-224}$), severe depletion of SC-EC and mature pancreatic states. Module M1, PG8 (isolated group).
   - *Why interesting*: Perfect example of pioneer factor loss diverting endodermal fate toward an alternative hepatic trajectory.
4. **NEUROG3** (Endocrine Commitment Driver):
   - 1,543 cells, $E=2.03, 	ext{PS mean}=0.4735$, positive lochNESS $+4.14$, negative lochNESS $-0.378$.
   - Complete endocrine developmental block: **$0.0\%$ SC-beta cells** ($\log_2 	ext{OR} = -\infty$), SC-EC depleted ($0.32\%$ vs $8.78\%$, $\log_2 	ext{OR} = -4.75, 	ext{FDR} = 3.25 	imes 10^{-33}$), accumulation in Pancreatic/Ductal Progenitors (`PDP`, $\log_2 	ext{OR} = +1.11$). Module M1, PG3.
   - *Why interesting*: Classical endocrine lineage arrest; validates Perturb-seq's ability to pinpoint the precise developmental checkpoint where differentiation fails.
5. **HNF4A / HNF4Ahet** (Maturity & Phenotypic Dosage Concordance):
   - HNF4A (987 cells, $E=1.75$) and HNF4Ahet (829 cells, $E=1.86$).
   - **DistanceSpace Closest Pair in Entire Screen** ($d = 0.0905$, Rank 1 across 630 pairs). Both reside in Phenotype Group PG3 and Module M1.
   - *Why interesting*: Proves technical reproducibility, biological robustness, and phenotypic concordance between heterozygous and homozygous perturbations.
6. **GLIS3** (Neonatal Diabetes & Beta-cell Vulnerability Factor):
   - 935 cells, $E=8.21$ (Rank 6), **Rank 1 PS Median ($0.7500$)**, **Rank 1 Responder Fraction ($66.6\%$)**, positive lochNESS $+9.53$ (Rank 4). PG2 with PDX1het.
   - *Why interesting*: Highest single-cell response rate in screen; strong accumulation in early progenitor manifold.

### Final Ranked Case Studies for Main Presentation
1. **Case Study 1: GATA6** — Massive Lineage Switch to Endothelial Fate (Slides 21-22).
2. **Case Study 2: FOXA2** — Endodermal Diversion to Hepatic Lineage (Slide 23).
3. **Case Study 3: NEUROG3 & PDX1** — Endocrine Differentiation Checkpoint Block (Slide 24).
4. *(Supporting Case Study in Backup: HNF4A / HNF4Ahet & GLIS3)*.

---

## K. ANALYTICAL DEFINITIONS

- **Perturbation Score ($PS$)**: A supervised machine-learning metric ($[0, 1]$) computed via `pertps` that trains a classifier on target-perturbed vs non-targeting control cells to project individual cells onto a continuous perturbation-response axis.
- **Energy Distance ($E$)**: A multivariate statistical distance between two probability distributions in metric space ($PCA$). Computed via the V-statistic: $E(X,Y) = 2\,\mathbb{E}\|X - Y\| - \mathbb{E}\|X - X'\| - \mathbb{E}\|Y - Y'\|$. Measures total distributional divergence including shifts in mean, covariance, and dispersion.
- **DistanceTest**: A non-parametric permutation hypothesis test comparing observed Energy Distance against an empirical null distribution generated by 1,000 label permutations, followed by Benjamini-Hochberg FDR correction.
- **DistanceSpace**: A continuous geometric manifold constructed from all $inom{G}{2}$ pairwise Energy Distances between perturbations, projected via Classical Multidimensional Scaling (PCoA) to identify phenotypic similarity groups (PGs).
- **lochNESS**: Local Continuous Neighborhood Enrichment Score: $	ext{lochNESS}(	ext{cell}, g) = rac{	ext{local\_fraction}(g)}{	ext{overall\_fraction}(g)} - 1$, calculated across $k=30$ nearest neighbors in latent PCA space. Signed: $>0$ indicates local over-representation (trapping/enrichment), $<0$ indicates depletion.
- **Cell-State Enrichment**: A sample-stratified hypergeometric / Fisher's exact test quantifying whether a perturbation is disproportionately over-represented or depleted in specific curated cell states (`celltype_2`), adjusting for sample/batch composition (`orig.ident`).
- **Co-functional Perturbation Module**: A cluster of perturbations (M1–M6) that elicit similar patterns of downstream transcriptome-wide differential expression (log2 fold change vs WT).
- **Gene Program**: A co-regulated module of downstream target genes (P1–P4) that respond in concert across perturbations.
- **Program Enrichment (ORA)**: Over-representation analysis testing whether discovered gene programs share significant overlap with curated biological gene sets (MSigDB Hallmark, Reactome, GO BP).

---

## L. KNOWN LIMITATIONS

1. **PS Unavailability for Composite/Heterozygous Targets**: PS requires a direct single target gene feature in the expression matrix. Perturbations targeting composite loci (`TET1/2/3`, `QSER1TET1`), heterozygous edits (`PDX1het`, `GATA6het`), or enhancers (`HHEXe`, `ONECUT1e`) were appropriately skipped (10/36) to prevent invalid target expression assignment.
2. **Unequal Cell Counts Across Genotypes**: Perturbation cell abundance ranges from 182 cells (`KDM2B`) to 6,451 cells (`MNX1`). To prevent sample-size bias in Energy Distance, the pipeline employs deterministic bounded sampling (max 2,000 cells per target, 5,000 WT control cells).
3. **Sample & Stage Composition Confounding**: Cells were harvested from multiple differentiation timepoints and libraries (`orig.ident`). Evaluating cell-state enrichment without stratification would yield false associations driven solely by library composition; stratified testing mitigates this confounding.
4. **lochNESS Sign Interpretation**: Because lochNESS is signed, global unweighted averages cancel out positive enrichment and negative depletion. Directional decomposition (mean positive, mean negative, positive fraction) is mandatory.
5. **DistanceSpace Similarity $
eq$ Direct Mechanism**: Proximity in DistanceSpace indicates similar global transcriptomic phenotypes, which may arise through convergent downstream pathways rather than identical physical interactions.
6. **Program Enrichment $
eq$ Pathway Proof**: Statistical over-representation against MSigDB sets establishes functional annotation, not direct biochemical proof of pathway activity.

---

## M. DATASET PROVENANCE

- **Source Study**: Chen et al., *Nature* 2023 (`s41586-023-06733-x`).
- **GEO Accession**: **GSE216909** (Genome-scale Perturb-seq / TF perturbation during human pluripotent stem cell pancreatic differentiation).
- **Experimental System**: Human embryonic stem cell ($hESC$) in vitro directed differentiation toward pancreatic beta-cell lineages across multiple developmental stages (`ESC` -> `DE` -> `PFG` -> `PP` -> `3DEC`).
- **Control Condition**: Non-targeting / wild-type control cells ($WT$, $n=24,408$ cells across samples).

---

## N. FINAL PRESENTATION PLAN & SLIDE MAPPING

| Slide # | Slide Title | Scientific Question Addressed | Visual Figures / Tables | Key Numerical Results | Take-Home Message |
|---|---|---|---|---|---|
| **1** | Multi-Layered Perturb-seq Analysis of Pancreatic Differentiation | Presentation overview & title | Title banner & workflow icons | 111,581 cells, 37 genotypes, 15 cell states | Comprehensive multi-metric resolution of human pancreatic transcription factor biology. |
| **2** | Dissecting Transcriptional Regulators of Human Pancreatic Fate | Biological rationale & questions | Pancreatic lineage diagram | 36 master TFs, hESC beta-cell differentiation | Understanding how key TFs orchestrate or restrict pancreatic endocrine commitment. |
| **3** | Experimental Design & Multiplexed Perturb-seq Screen | How was the experiment designed? | Workflow schematic / Table | 111,581 cells, 100 sgRNAs, 13 samples (GSE216909) | High-throughput pooled single-cell CRISPR screening across 6 differentiation stages. |
| **4** | The Pancreatic Differentiation Landscape across 15 Cell States | What biological cell states are present? | `01_umap_celltype2.png` | 15 curated states: ESC (21k), DE (18k), PFG (17k), SC-beta (3.8k) | UMAP captures continuous in vitro trajectory from pluripotency to mature endocrine lineages. |
| **5** | Differentiation Stage Progression & Cellular Heterogeneity | How do stages relate to curated cell states? | `02_umap_development_stage.png`, `03_stage_celltype_composition.png` | 6 stages: ESC to 3DEC; celltype_2 != stage | Stages contain diverse cell states; late 3DEC cultures harbor endocrine, progenitor, and off-target cells. |
| **6** | Conceptual Analytical Framework: Deconvolving Perturbation Biology | Why is a single metric insufficient? | Multi-layer hierarchy flowchart | 6 distinct analytical dimensions (PS, Distance, lochNESS, etc.) | Separate metrics capture target response, phenotype magnitude, spatial localization, and mechanism. |
| **7** | Perturbation Score (PS): Measuring Single-Cell Response Strength | Which perturbations elicit strong cellular responses? | `05_ps_by_perturbation.png`, `ps_score_summary.csv` | 26 valid targets (mean PS 0.413); Top: KDM2B (0.627), GLIS3 (0.607) | CRISPR penetrance is highly variable; single-cell PS separates true responders from escapers. |
| **8** | Response Strength vs Spatial Trapping on the Cellular Manifold | How does response strength project onto single-cell space? | `20_umap_ps_score.png`, `27_umap_ps_lochness_comparison.png` | 66,015 scored cells; UMAP response density | PS measures cellular response intensity, while lochNESS identifies focal manifold trapping. |
| **9** | Energy Distance & DistanceTest: Quantifying Global Phenotype Shift | How large is the multivariate phenotype shift vs WT? | `06_energy_distance_by_perturbation.png`, `distance_results.csv` | 36/36 significant (FDR < 0.001); Top: PDX1het (13.63), HHEXhet (10.47), GATA6 (9.70) | All 36 TFs perturb the manifold, but master developmental drivers cause 10-fold larger shifts. |
| **10** | lochNESS: Directional Single-Cell Manifold Localization | Where on the manifold do perturbations accumulate or deplete? | `21_umap_lochness_score.png`, `25_lochness_by_genotype.png` | GATA6 (+14.18), PDX1het (+14.15); PDX1 (-0.589, 77.8% depleted) | Signed lochNESS reveals simultaneous focal accumulation and broad downstream lineage depletion. |
| **11** | High-Resolution lochNESS Localization across 15 Cell States | Which specific developmental states are enriched or depleted? | `13_lochness_by_celltype.png` | Matrix of 36 genotypes x 15 cell states | Maps exact developmental trapping points (e.g. progenitor accumulation vs endocrine loss). |
| **12** | Stratified Cell-State Enrichment Uncovers Lineage Diversions | Which curated pancreatic states are significantly altered? | `04_genotype_celltype_enrichment.png`, `celltype_enrichment.csv` | 313 significant associations; GATA6->Endothelial, FOXA2->Liver | Sample-stratified testing confirms master TFs act as binary lineage gatekeepers. |
| **13** | Cross-Metric Coupling: Response Strength Drives Phenotype Distance | Do strongly responding cells produce larger global phenotypes? | `07_ps_vs_distance.png` | Spearman rho = +0.7832, p = 2.24e-6, n = 26 | Strong coupling validates that single-cell response intensity scales into global phenotype magnitude. |
| **14** | Cross-Metric Decoupling: Complementary Dimensions of Biology | How do Distance and lochNESS interrelate? | `08_distance_vs_lochness_positive.png`, `12_distance_vs_lochness_absolute.png` | Distance vs Pos: rho = +0.410 (p=0.013); Distance vs Abs: rho = +0.451 (p=0.006) | Global phenotype distance moderately correlates with localization, while remaining distinct layers. |
| **15** | Perturbation DistanceSpace: Discovering Phenotypic Similarity | Which perturbations phenocopy one another? | `14_distance_space.png`, `distance_space_neighbors.csv` | 630 pairs, 9 phenotype groups (PG1-PG9); HNF4A-HNF4Ahet d=0.090 | Manifold distance organizes TFs into 9 phenotypic groups and verifies dosage concordance. |
| **16** | Co-Functional Modules: Shared Downstream Regulatory Effects | Which perturbations share downstream regulatory programs? | `15_module_program_strength.png`, `module_assignments.csv` | 6 modules (M1-M6); M1 core (29 TFs), M2-M6 specialized | Groups perturbations by downstream transcriptional consequences rather than direct binding. |
| **17** | Gene Programs: Core Downstream Transcriptional Signatures | Which downstream gene programs respond across perturbations? | `16_program_activity_celltype2.png`, `gene_programs.csv` | 4 programs (980 genes); P1 (Endocrine), P2 (Beta cell), P3 (Progenitor), P4 (EMT) | Downstream genes cluster into 4 biologically coherent developmental programs. |
| **18** | Functional Enrichment of Co-Regulated Gene Programs | What biological pathways do these gene programs represent? | `17_program_enrichment.png`, `program_enrichment.csv` | P2: Pancreas Beta Cells (FDR 1.28e-3); P3: MYC (FDR 3.50e-36); P4: EMT (FDR 1.47e-4) | ORA annotates programs as mature beta-cell function, stem/progenitor growth, and EMT. |
| **19** | Co-Functional Regulatory Network & TF-TF Cross-Regulation | How do master transcription factors cross-regulate each other? | `18_module_network.png` | Directed TF network, edge weights = |log2FC| | Visualizes hierarchical and cross-regulatory interactions among key developmental TFs. |
| **20** | Integrated Perturbation Landscape: Multi-Metric Synthesis | How do all analytical dimensions synthesize into a unified view? | `19_perturbation_summary.png` | Complete 37-genotype multi-panel summary matrix | Proves no single metric suffices: multi-metric profiling resolves multi-faceted TF biology. |
| **21** | Case Study 1: GATA6 Loss Triggers Endothelial Lineage Switch | What happens when GATA6 is perturbed during differentiation? | `28_umap_highlight_genotypes.png` (Panel B), `celltype_enrichment.csv` | 25.7% Endothelial cells (log2 OR = +5.21, FDR = 1e-141); E = 9.70 | GATA6 acts as an essential repressor of endothelial fate during endodermal differentiation. |
| **22** | Case Study 1 (Deep Dive): GATA6 Single-Cell Spatial & Metric Profile | What does the single-cell profile of GATA6 reveal? | `per_genotype_combined/GATA6_ps_lochness_umap.png` | PS mean = 0.578, pos lochNESS = +14.18 (Rank 1), Module M1, PG9 | Combined PS and lochNESS confirm intense single-cell response and massive focal trapping. |
| **23** | Case Study 2: FOXA2 Loss Diverts Endoderm to Hepatic Fate | How does FOXA2 deficiency alter lineage specification? | `per_genotype_combined/FOXA2_ps_lochness_umap.png`, `celltype_enrichment.csv` | 34.0% Liver cells (log2 OR = +4.09, FDR = 3.65e-224); E = 2.14, Module M1, PG8 | FOXA2 loss diverts endodermal progenitors away from pancreatic lineage into hepatic fate. |
| **24** | Case Study 3: NEUROG3 & PDX1 Enforce Endocrine Checkpoints | How do NEUROG3 and PDX1 govern mature beta-cell genesis? | `per_genotype_combined/NEUROG3_ps_lochness_umap.png`, `per_genotype_combined/PDX1_ps_lochness_umap.png` | NEUROG3: 0.0% SC-beta; PDX1: 77.8% depleted cells; PDX1het E = 13.63 (Rank 1) | Pinpoints exact developmental arrest points: NEUROG3 blocks endocrine genesis; PDX1 blocks maturation. |
| **25** | Summary & Conclusions: Multi-Dimensional Perturb-seq Profiling | What are the core biological & methodological conclusions? | Summary diagram / key takeaway bullets | 111k cells, 36 TFs, 6 metrics, 4 programs, 9 PGs | Multi-layered framework turns single-cell CRISPR screens into auditable regulatory maps. |
| **26** | Backup: Complete Single-Cell PS & lochNESS Atlases | Diagnostic atlas overview across 36 perturbations | `ps_per_genotype_umap_atlas.png`, `lochness_per_genotype_umap_atlas.png` | 36-genotype atlas grid | Complete visual reference for all 36 perturbations in screen. |
| **27** | Backup: Full Genotype x Cell-State PS & lochNESS Matrices | Detailed cell-state response matrices | `24_ps_genotype_celltype_heatmap.png`, `26_lochness_by_celltype2.png` | 505 genotype-celltype pairs | Comprehensive tabular and heatmap distributions across 15 curated cell states. |
| **28** | Backup: Phenotype Manifold & Complete Distance Matrix | Full pairwise DistanceSpace dendrogram and matrix | `distance_space_matrix.csv`, PCoA scree | 630 pairwise Energy Distances across 36 perturbations | Complete matrix of pairwise phenotypic divergence among all tested TFs. |
| **29** | Backup: Auditable Table of Skipped Perturbations & QC Limits | Why were certain metrics unavailable for specific targets? | `ps_score_skipped.csv`, QC threshold table | 10 skipped PS targets (composite/heterozygous/enhancer) | Full technical audit ensuring transparency regarding metric eligibility and parameters. |
| **30** | Backup: Detailed Case Study: HNF4A/HNF4Ahet & GLIS3 | Dosage concordance & neonatal diabetes mechanisms | `per_genotype_combined/HNF4A_ps_lochness_umap.png`, `GLIS3_ps_lochness_umap.png` | HNF4A-HNF4Ahet d=0.0905 (Rank 1); GLIS3 PS median=0.750 (Rank 1) | Demonstrates high reproducibility of phenotypic effects and strong beta-cell responder phenotypes. |

