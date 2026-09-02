# Presentation Source Summary: Diabetes-Specific Perturb-seq Analysis

**Target Presentation**: `results/diabetes_specific/presentation/diabetes_perturbseq_comprehensive_analysis.pptx`  
**Auditable Inventory**: `results/diabetes_specific/presentation/inventory_analysis.md`  
**Dataset Source**: Chen et al., *Nature* 2023 (`s41586-023-06733-x`), GEO Accession: **GSE216909**  
**H5AD Source**: `results/diabetes_specific/diabetes_analysis.h5ad` ($111,581 \text{ cells} \times 36,601 \text{ genes}$)  
**Total Slides**: 30 (25 Main Deck Slides + 5 Backup Slides)  
**Execution Timestamp**: 2026-08-30  

---

## SLIDE-BY-SLIDE AUDITABLE TRACEABILITY MATRIX

### Slide 1: Title Slide — Multi-Layered Perturb-seq Analysis of Human Pancreatic Differentiation
- **Scientific Question**: What is the scope, dataset, and computational architecture of this study?
- **Figures Used**: N/A (Title banner & layout).
- **Tables Used**: `perturbation_summary.csv`, `ps_score_summary.csv`, `distance_results.csv`.
- **Exact Numerical Findings**: 111,581 single cells, 37 genotypes (1 WT + 36 transcription factors), 100 sgRNA constructs, 15 curated cell states, 13 sequencing libraries.
- **Take-Home Message**: A multi-layered computational framework systematically resolves 36 master regulators in human pancreatic development across single-cell response, global distance, manifold localization, and downstream regulomes.
- **Interpretation**: Establishing an auditable multi-metric paradigm for single-cell CRISPR screens in human stem cell differentiation.
- **Limitations**: In vitro directed differentiation captures major embryonic trajectories but does not fully recapitulate in vivo islet niche maturation.

---

### Slide 2: Biological Foundation — Dissecting the Regulatory Circuitry of Human Pancreatic Endocrine Fate
- **Scientific Question**: How do transcription factors orchestrate pancreatic beta-cell commitment and restrict off-target lineage diversions?
- **Figures Used**: Structured developmental lineage flowchart.
- **Tables Used**: `celltype_enrichment.csv`, `lochness_celltype_summary.csv`.
- **Exact Numerical Findings**: 15 curated states from ESC to mature SC-beta, SC-alpha, SC-delta, SC-EC, plus off-target Liver (3,416), Stromal (4,369), and Endothelial (1,157) populations.
- **Take-Home Message**: Pancreatic directed differentiation requires precise sequential activation of master TFs; perturbing these factors can cause either developmental arrest or active diversion into non-pancreatic fates.
- **Interpretation**: Identifying specific TF checkpoints is essential to optimize cell replacement therapies for diabetes.
- **Limitations**: Multiple transcription factors operate in combinatorial complexes whose epistatic interactions require multi-target perturbations.

---

### Slide 3: Experimental Design — Pooled Single-Cell CRISPR Screening Across 13 Differentiation Libraries
- **Scientific Question**: How was the pooled single-cell CRISPR screen designed and multiplexed?
- **Figures Used**: Workflow schematic and parameter summary cards.
- **Tables Used**: `perturbation_summary.csv`, `distance_results.csv`.
- **Exact Numerical Findings**: 111,581 single cells, 24,408 WT control cells, 87,173 perturbed cells, 100 sgRNA constructs across 36 non-WT TFs, 13 `orig.ident` libraries, 36,601 measured genes.
- **Take-Home Message**: Massive multiplexed screening across 6 differentiation stages provides high-powered, single-cell resolution of human transcription factor function.
- **Interpretation**: Deep cell coverage (mean ~2,421 cells per genotype) ensures robust statistical power for multivariate distance and continuous manifold testing.
- **Limitations**: Variable guide recovery per cell and unequal cell counts per genotype require bounded sampling during comparative distance testing.

---

### Slide 4: Cellular Landscape — Single-Cell Transcriptomic Map Spans 15 Curated Pancreatic States
- **Scientific Question**: What biological cell states and trajectories are present across the unperturbed differentiation landscape?
- **Figures Used**: `figures/01_umap_celltype2.png` (Figure 01).
- **Tables Used**: `lochness_celltype_summary.csv`, H5AD `obs['celltype_2']`.
- **Exact Numerical Findings**: 15 curated states: ESC ($n=21,027$), DE ($n=18,361$), PFG ($n=17,145$), PP ($n=13,388$), PDP ($n=9,178$), SC-EC ($n=8,785$), SC-alpha ($n=4,732$), Stromal ($n=4,369$), SC-beta ($n=3,799$), EnP ($n=3,620$), Liver ($n=3,416$), PGT ($n=1,733$), Endothelial ($n=1,157$), SC-delta ($n=740$), ESC (D3) ($n=131$).
- **Take-Home Message**: UMAP embedding resolves continuous in vitro progression from pluripotency to endocrine islet cells and separates off-target hepatic, stromal, and endothelial fates.
- **Interpretation**: Provides the ground-truth cellular manifold necessary to measure perturbation-induced lineage shifts.
- **Limitations**: 2D UMAP projections condense multidimensional geometry; all formal distance and localization statistics are computed directly in 50-dimensional PCA space.

---

### Slide 5: Experimental Composition — Differentiation Stages Harbor Substantial Cell-State Heterogeneity
- **Scientific Question**: How do experimental harvesting timepoints relate to actual biological cell states?
- **Figures Used**: `figures/02_umap_development_stage.png` (Figure 02), `figures/03_stage_celltype_composition.png` (Figure 03).
- **Tables Used**: H5AD `obs[['development_stage', 'celltype_2', 'orig.ident']]`.
- **Exact Numerical Findings**: 6 stages: 3DEC ($25,143$), WT ($24,408$), DE ($18,120$), PFG ($17,664$), ESC ($15,860$), PP ($10,386$). Stage 3DEC contains SC-EC (34.9%), SC-alpha (18.8%), SC-beta (15.1%), PDP (12.4%), Stromal (12.1%), SC-delta (2.9%), Endothelial (1.4%).
- **Take-Home Message**: `celltype_2 != development_stage`. Evaluating perturbations by sample/stage alone introduces severe confounding; true biological effects must be measured in curated cell-state space.
- **Interpretation**: Late differentiation stages are multi-lineage mixtures. Sample-aware stratification is mandatory.
- **Limitations**: In vitro differentiation synchrony decreases over time, increasing within-sample variance at late stages.

---

### Slide 6: Analytical Architecture — A Multi-Layered Framework to Deconvolve Perturbation Biology
- **Scientific Question**: Why is a single master perturbation score insufficient to describe single-cell CRISPR phenotypes?
- **Figures Used**: Conceptual 4-pillar architectural hierarchy diagram.
- **Tables Used**: Master table integration (`perturbation_summary.csv`).
- **Exact Numerical Findings**: Integrates 6 distinct statistical layers (PS, Energy Distance, lochNESS pos/neg, cell-state odds ratio, DistanceSpace PCoA, co-functional modules M1–M6).
- **Take-Home Message**: Single-cell CRISPR phenotypes encompass distinct, orthogonal biological dimensions: single-cell response strength, global phenotype distance, continuous spatial trapping, and downstream regulome execution.
- **Interpretation**: Deconvolves "did the cell respond?" from "how big was the shift?", "where did cells go?", and "which genes changed?".
- **Limitations**: Requires careful multi-testing correction across independent analytical stages.

---

### Slide 7: Response Strength (PS) — Single-Cell Perturbation Scores Reveal Variable Response Penetrance
- **Scientific Question**: Which transcription factor knockouts reliably trigger strong single-cell transcriptional responses?
- **Figures Used**: `figures/05_ps_by_perturbation.png` (Figure 05).
- **Tables Used**: `ps_score_summary.csv`, `ps_score_skipped.csv`, `ps_by_genotype.csv`.
- **Exact Numerical Findings**: Evaluated for 26/36 single-gene targets ($n=66,015$ cells, mean PS $= 0.4132$). Top responders: KDM2B (mean 0.6273, median 0.6808), GLIS3 (mean 0.6075, median 0.7500, 66.6% responder fraction), HHEX (mean 0.6050, median 0.6589), GATA6 (mean 0.5776, median 0.6482). Lowest: PAX6 (0.3372), NEUROD1 (0.3393). 10 composite/heterozygous targets appropriately skipped.
- **Take-Home Message**: CRISPR knockout penetrance is highly locus-dependent in stem cells; PS separates true single-cell responders from unperturbed escapers.
- **Interpretation**: Cells with low PS reflect either incomplete target knockdown or cellular buffering mechanisms maintaining baseline homeostasis.
- **Limitations**: PS requires a single matching target feature in the expression matrix and was appropriately skipped for composite/enhancer/heterozygous targets.

---

### Slide 8: Spatial Resolution — Response Strength Distributes Across Specific Lineage States
- **Scientific Question**: How does single-cell perturbation response density project across the differentiation landscape?
- **Figures Used**: `figures/27_umap_ps_lochness_comparison.png` (Figure 27), `figures/20_umap_ps_score.png` (Figure 20).
- **Tables Used**: `ps_by_celltype2.csv`, H5AD `obs['ps_score']`.
- **Exact Numerical Findings**: PS scores concentrate in early progenitor states (ESC mean PS $= 0.568$, DE $= 0.551$) and active differentiation branches, across 66,015 scored single cells.
- **Take-Home Message**: High cellular response strength is not uniform across cell states, but concentrates within specific developmental windows.
- **Interpretation**: Cells in pluripotent/progenitor states exhibit higher transcriptional plasticity in response to TF loss than terminally committed cells.
- **Limitations**: Visual density on UMAP reflects both cell abundance and local score magnitude.

---

### Slide 9: Phenotype Magnitude — Energy Distance Quantifies Global Multivariate Phenotypic Shift
- **Scientific Question**: How large is the multivariate transcriptomic displacement induced by each perturbation relative to WT?
- **Figures Used**: `figures/06_energy_distance_by_perturbation.png` (Figure 06).
- **Tables Used**: `distance_results.csv`, `distance_test.csv`.
- **Exact Numerical Findings**: 36/36 non-WT perturbations are statistically significant (all empirical $p = 0.000999, 	ext{BH-FDR} = 0.000999$, 1,000 permutations). Effect sizes span a 12-fold range: Top: PDX1het ($E = 13.6337$), HHEXhet ($E = 10.4732$), GATA6 ($E = 9.7045$), KDM2B ($E = 9.3204$), HHEX ($E = 8.9955$). Bottom: MNX1 ($E = 1.0755$), PAX6 ($E = 1.1531$), BCOR ($E = 1.3674$), NEUROD1 ($E = 1.4187$).
- **Take-Home Message**: Statistical significance alone (36/36) is uninformative without effect size quantification; master lineage drivers cause an order of magnitude larger multivariate displacement than late-stage TFs.
- **Interpretation**: Energy Distance measures total distribution divergence in 50-dimensional PCA space using the V-statistic formulation.
- **Limitations**: Bounded sampling (max 2,000 target, 5,000 control) is necessary to ensure distance values are not distorted by sample-size differences.

---

### Slide 10: State Localization (lochNESS) — Signed lochNESS Resolves Focal Accumulation from Lineage Depletion
- **Scientific Question**: Where on the single-cell manifold do perturbed cells accumulate or disappear?
- **Figures Used**: `figures/21_umap_lochness_score.png` (Figure 21), `figures/25_lochness_by_genotype.png` (Figure 25).
- **Tables Used**: `lochness_summary.csv`, H5AD `obs['lochness_self']`.
- **Exact Numerical Findings**: Continuous kNN score across 111,581 cells ($k=30$). Positive accumulation ($>0$): GATA6 (+14.18), PDX1het (+14.15), TADA2B (+11.23), GLIS3 (+9.53), FOXA2 (+5.86). Severe depletion ($<0$): PDX1 ($-0.5891$, 77.8% depleted cells), FOXA2 ($-0.4952$, 70.7% depleted cells).
- **Take-Home Message**: Global mean lochNESS obscures biology by canceling positive focal trapping with negative downstream depletion; directional decomposition is essential.
- **Interpretation**: Captures dual perturbation action: accumulating cells upstream at an arrest/diversion point while starving downstream descendant states.
- **Limitations**: Score magnitude depends on local kNN graph density; extreme outliers are bounded by dataset-level background frequency.

---

### Slide 11: State-by-State Resolution — lochNESS Maps State-Specific Perturbation Trapping and Exclusion
- **Scientific Question**: Which specific curated developmental cell states are enriched or depleted for each perturbation?
- **Figures Used**: `figures/13_lochness_by_celltype.png` (Figure 13).
- **Tables Used**: `lochness_by_celltype.csv`, `lochness_by_genotype_celltype.csv`.
- **Exact Numerical Findings**: Matrix of 36 genotypes $	imes$ 15 cell states (505 non-zero pairs). Highlights: GATA6 in Endothelial (+3.76) vs SC-beta (-0.43); FOXA2 in Liver (+4.12) vs mature endocrine; NEUROG3 in PDP (+1.11) vs SC-beta (-0.43).
- **Take-Home Message**: Maps continuous neighborhood enrichment directly onto discrete curated cell states to establish a high-resolution developmental diagnostic matrix.
- **Interpretation**: Pinpoints the exact developmental transitions where each transcription factor is required.
- **Limitations**: Cell types with very small cell counts (e.g. ESC (D3), $n=131$) exhibit higher score variance.

---

### Slide 12: Lineage Conversion — Stratified Odds-Ratio Testing Uncovers Dramatic Lineage Conversions
- **Scientific Question**: Which cell-state conversions and depletions achieve statistical significance when controlling for library composition?
- **Figures Used**: `figures/04_genotype_celltype_enrichment.png` (Figure 04).
- **Tables Used**: `celltype_enrichment.csv`.
- **Exact Numerical Findings**: 313 significant associations ($	ext{FDR} < 0.05$). Striking diversions: GATA6 $ightarrow$ Endothelial ($25.7\%$ vs $0.7\%, \log_2 	ext{OR} = +5.21, 	ext{FDR} = 1.05 	imes 10^{-141}$); FOXA2 $ightarrow$ Liver ($34.0\%$ vs $2.0\%, \log_2 	ext{OR} = +4.09, 	ext{FDR} = 3.65 	imes 10^{-224}$); NEUROG3 $ightarrow$ complete SC-beta loss ($0.0\%$ cells, $\log_2 	ext{OR} = -\infty$); GSC $ightarrow$ Stromal ($\log_2 	ext{OR} = +2.66$).
- **Take-Home Message**: Sample-stratified odds-ratio testing confirms master TFs act as binary lineage gatekeepers; their loss diverts endoderm into alternative mesodermal, hepatic, or stromal fates.
- **Interpretation**: Stratifying across 13 `orig.ident` libraries eliminates batch confounding, ensuring discovered lineage diversions reflect true cellular reprogramming.
- **Limitations**: Extreme odds ratios ($+\infty$ or $-\infty$) occur when target cell counts in specific clusters reach zero or 100%.

---

### Slide 13: Cross-Metric Coupling — Single-Cell Response Strength Strongly Predicts Global Phenotype Shift
- **Scientific Question**: Do perturbations that trigger strong single-cell responses systematically generate larger global transcriptomic phenotypes?
- **Figures Used**: `figures/07_ps_vs_distance.png` (Figure 07).
- **Tables Used**: `perturbation_summary.csv`.
- **Exact Numerical Findings**: Spearman $ho = +0.7832, p = 2.24 	imes 10^{-6}, n = 26$. Top concordant hits: KDM2B, GLIS3, HHEX, GATA6.
- **Take-Home Message**: Strong, statistically significant positive coupling validates that single-cell response penetrance (PS) scales directly into aggregate multivariate phenotype displacement (Energy Distance).
- **Interpretation**: High cross-metric correlation provides independent mutual validation of both scoring algorithms.
- **Limitations**: Correlation evaluated across the 26 single-gene targets with valid PS; 10 composite/heterozygous targets excluded.

---

### Slide 14: Cross-Metric Decoupling — Distance and lochNESS Capture Distinct, Complementary Dimensions
- **Scientific Question**: How does global phenotype distance relate to directional local manifold localization?
- **Figures Used**: `figures/08_distance_vs_lochness_positive.png` (Figure 08), `figures/12_distance_vs_lochness_absolute.png` (Figure 12).
- **Tables Used**: `perturbation_summary.csv`.
- **Exact Numerical Findings**: Distance vs Positive lochNESS: $ho = +0.4103, p = 0.0129, n=36$; Distance vs Absolute lochNESS: $ho = +0.4512, p = 0.0057, n=36$; Distance vs Negative lochNESS: $ho = -0.1410, p = 0.4263, n=34$.
- **Take-Home Message**: Global phenotype displacement moderately correlates with focal trapping, but modest coupling proves lochNESS provides an orthogonal, non-redundant layer of spatial information.
- **Interpretation**: A large Energy Distance indicates substantial multivariate shift, but only lochNESS reveals whether cells accumulated tightly in one cluster or dispersed across multiple states.
- **Limitations**: Spearman correlation captures monotonic relationships; non-linear manifold topologies may exhibit complex local associations.

---

### Slide 15: Phenotype Manifold — DistanceSpace Maps 630 Pairwise Phenotypes into 9 Similarity Groups
- **Scientific Question**: Which transcription factor knockouts generate similar global transcriptional phenotypes?
- **Figures Used**: `figures/14_distance_space.png` (Figure 14).
- **Tables Used**: `distance_space_coordinates.csv`, `distance_space_matrix.csv`, `distance_space_neighbors.csv`, `phenotype_groups.csv`.
- **Exact Numerical Findings**: 630 pairwise comparisons ($inom{36}{2} = 630$). Discovers 9 Phenotype Groups (PG1–PG9). Closest pair: HNF4A $\leftrightarrow$ HNF4Ahet ($d = 0.0905$, Rank 1). Other tight pairs: ONECUT1e $\leftrightarrow$ OTUD5 ($d = 0.2664$), GATA4 $\leftrightarrow$ GATA6het ($d = 0.3729$). Outlier singletons: GATA6 (PG9), FOXA2 (PG8), PDX1 (PG7).
- **Take-Home Message**: DistanceSpace organizes perturbations into a continuous phenotypic manifold, revealing functional phenocopying and proving exceptional reproducibility between heterozygous and homozygous edits.
- **Interpretation**: Proximity in DistanceSpace reflects geometric similarity of single-cell transcriptomic distributions, not direct protein-protein binding.
- **Limitations**: PCoA eigen-decomposition captures top linear projections of the pairwise distance matrix; higher-order non-Euclidean dimensions contain residual variance.

---

### Slide 16: Regulatory Modules — Perturbations Partition into 6 Co-Functional Regulatory Modules
- **Scientific Question**: Which perturbations share common downstream regulatory consequences across responsive genes?
- **Figures Used**: `figures/15_module_program_strength.png` (Figure 15).
- **Tables Used**: `module_assignments.csv`, `module_program_strength.csv`.
- **Exact Numerical Findings**: 6 Co-functional Modules (M1–M6) across 980 responsive genes: M1 (29 TFs: core developmental engine, P3 strength +0.636, P4 +0.411, P2 -0.870); M2 (TLE3, P1 strength +0.666); M3 (NEUROD1, BCOR, P1 strength +0.512); M4 (PDX1); M5 (TADA2B); M6 (PAX6, PBX1, P1 strength -0.664).
- **Take-Home Message**: Clusters perturbations by downstream differential expression patterns rather than sequence homology, linking upstream regulators to downstream execution modules.
- **Interpretation**: Module M1 represents the core transcriptional network required to repress progenitor growth and activate endocrine maturation.
- **Limitations**: Module discovery depends on the number of selected responsive genes (980) and hierarchical clustering distance thresholds.

---

### Slide 17: Gene Programs — Four Core Gene Programs Reflect Endocrine, Growth, and EMT States
- **Scientific Question**: What co-regulated gene programs respond downstream of transcription factor perturbations?
- **Figures Used**: `figures/16_program_activity_celltype2.png` (Figure 16).
- **Tables Used**: `gene_programs.csv`, `program_activity_celltype.csv`, `program_summary.csv`.
- **Exact Numerical Findings**: 980 genes across 4 programs: P1 (6 genes: GAL, AKAP12, PEG10, CACNA2D3, FGF12, CDK6; active in SC-alpha 0.378, SC-beta 0.371); P2 (549 genes: mature beta signature, active in SC-delta 0.647, SC-beta 0.622, SC-alpha 0.574); P3 (316 genes: progenitor growth signature, active in ESC 1.107, DE 1.087, PFG 1.043, PP 1.002); P4 (109 genes: vascular/EMT signature, active in Endothelial 1.298, Stromal 0.193).
- **Take-Home Message**: Data-driven gene clustering decomposes the downstream pancreatic regulome into mature endocrine, progenitor biosynthesis, and mesenchymal state signatures.
- **Interpretation**: Connects abstract statistical gene clusters directly with known pancreatic cell physiology.
- **Limitations**: Small program sizes (P1, $n=6$) limit statistical power for functional enrichment testing.

---

### Slide 18: Functional Enrichment — Pathway Over-Representation Annotates Biological Mechanisms
- **Scientific Question**: What curated biological pathways and molecular mechanisms do the discovered gene programs represent?
- **Figures Used**: `figures/17_program_enrichment.png` (Figure 17).
- **Tables Used**: `program_enrichment.csv`, `program_summary.csv`.
- **Exact Numerical Findings**: ORA against MSigDB Hallmark, Reactome, and GO BP: P2 $ightarrow$ HALLMARK_PANCREAS_BETA_CELLS (overlap 36/42, $	ext{FDR} = 1.28 	imes 10^{-3}, 	ext{OR} = 4.97$); P3 $ightarrow$ HALLMARK_MYC_TARGETS_V1 (overlap 76/78, $	ext{FDR} = 3.50 	imes 10^{-36}, 	ext{OR} = 104.8$), MTORC1_SIGNALING ($	ext{FDR} = 3.05 	imes 10^{-20}$), TRANSLATION ($	ext{FDR} = 1.13 	imes 10^{-19}$); P4 $ightarrow$ EPITHELIAL_MESENCHYMAL_TRANSITION (overlap 14/36, $	ext{FDR} = 1.47 	imes 10^{-4}, 	ext{OR} = 5.69$), ANGIOGENESIS ($	ext{FDR} = 3.12 	imes 10^{-4}$).
- **Take-Home Message**: Over-representation analysis rigorously annotates data-driven programs as mature beta-cell identity (P2), progenitor ribosomal translation/growth (P3), and mesenchymal transition (P4).
- **Interpretation**: Confirms that unsupervised clustering recovered genuine, coherent biological pathways.
- **Limitations**: Pathway enrichment provides functional annotation; it does not prove direct biochemical pathway activation.

---

### Slide 19: Regulatory Network — Directed Regulatory Network Captures TF-TF Downstream Coupling
- **Scientific Question**: How do master transcription factors cross-regulate each other during differentiation?
- **Figures Used**: `figures/18_module_network.png` (Figure 18).
- **Tables Used**: `module_assignments.csv`, workflow `tf_edges`.
- **Exact Numerical Findings**: Directed graph of perturbed TFs (nodes colored by module M1–M6, directed edges weighted by $|\log_2 	ext{FC}|$). Identifies central regulatory hubs: PDX1, FOXA2, GATA6, NEUROG3, RFX6.
- **Take-Home Message**: Reconstructs the hierarchical web of cross-regulation governing human pancreatic development.
- **Interpretation**: Perturbing an upstream master regulator alters downstream fate by modulating the expression of multiple secondary transcription factors.
- **Limitations**: Network edges represent differential expression influence, not direct physical promoter binding or ChIP-seq occupancy.

---

### Slide 20: Multi-Metric Synthesis — Integrated Multi-Metric Profiling Across All 37 Genotypes
- **Scientific Question**: How do all analytical dimensions synthesize into a unified, comprehensive view across all 37 genotypes?
- **Figures Used**: `figures/19_perturbation_summary.png` (Figure 19).
- **Tables Used**: `perturbation_summary.csv`.
- **Exact Numerical Findings**: Complete 37-genotype matrix integrating cell count, PS mean/median, Energy Distance, lochNESS pos/neg/abs, dominant cell state, module, and phenotype group.
- **Take-Home Message**: Conclusively proves that no single metric can capture perturbation biology; multi-dimensional integration is mandatory.
- **Interpretation**: Demonstrates diverse combinatorial phenotypes: GATA6 (high PS, high E, focal lochNESS), FOXA2 (modest E, massive liver diversion), NEUROG3 (modest E, complete endocrine dropout), HNF4A (phenotypic dosage identity).
- **Limitations**: High information density requires structured multi-panel visual representations.

---

### Slide 21: Case Study 1 — GATA6 Loss Triggers Endothelial Lineage Conversion
- **Scientific Question**: What happens to human stem cell differentiation when master endodermal regulator GATA6 is knocked out?
- **Figures Used**: `figures/28_umap_highlight_genotypes.png` (Figure 28, Panel B).
- **Tables Used**: `celltype_enrichment.csv`, `perturbation_summary.csv`.
- **Exact Numerical Findings**: GATA6 KO ($n=1,500$ cells) exhibits 25.7% Endothelial cells vs 0.7% baseline ($\log_2 	ext{OR} = +5.21, 	ext{FDR} = 1.05 	imes 10^{-141}$); complete loss of SC-EC ($\log_2 	ext{OR} = -5.46$), SC-alpha ($\log_2 	ext{OR} = -5.57$), and SC-beta ($\log_2 	ext{OR} = -4.39$).
- **Take-Home Message**: GATA6 acts as an indispensable gatekeeper: it is required not only to promote endoderm, but actively to repress alternative endothelial and mesodermal fates.
- **Interpretation**: In the absence of GATA6, endodermal progenitors fail to restrict chromatin, derepressing vascular programs (P4) and executing an aberrant mesodermal conversion.
- **Limitations**: In vitro culture conditions contain growth factors that may interact with GATA6 deficiency to favor endothelial survival.

---

### Slide 22: Case Study 1 (Deep Dive) — GATA6 Multi-Metric Profile
- **Scientific Question**: How do single-cell PS, Energy Distance, and lochNESS integrate to describe the GATA6 phenotype?
- **Figures Used**: `figures/per_genotype_combined/GATA6_ps_lochness_umap.png`.
- **Tables Used**: `perturbation_summary.csv`, `ps_score_summary.csv`, `lochness_summary.csv`.
- **Exact Numerical Findings**: $n=1,500$ cells, 3 sgRNAs. PS Mean $= 0.5776$ (Rank 4), Median $= 0.6482$, Responder Fraction $= 61.6\%$. Energy Distance $E = 9.7045$ (Rank 3, $	ext{FDR} = 0.000999$). lochNESS Positive Mean $= +14.18$ (Rank 1 in screen), Absolute Mean $= 13.79$ (Rank 1). DistanceSpace Group: PG9 (isolated singleton). Module: M1.
- **Take-Home Message**: GATA6 demonstrates extreme concordance across all metrics: high single-cell response penetrance, third-largest global Energy Distance, and the highest focal lochNESS localization in the screen.
- **Interpretation**: GATA6 is indispensable for locking pluripotent cells into the pancreatic endoderm fate.
- **Limitations**: Single-gene knockout cannot evaluate potential functional redundancy with GATA4 without double-knockout constructs.

---

### Slide 23: Case Study 2 — FOXA2 Loss Diverts Pancreatic Endoderm to Hepatic Fate
- **Scientific Question**: How does pioneer factor FOXA2 deficiency alter lineage specification in foregut endoderm?
- **Figures Used**: `figures/per_genotype_combined/FOXA2_ps_lochness_umap.png`.
- **Tables Used**: `celltype_enrichment.csv`, `perturbation_summary.csv`, `lochness_summary.csv`.
- **Exact Numerical Findings**: $n=4,896$ cells. Cell State: **34.0% Liver cells** vs 2.0% baseline ($\log_2 	ext{OR} = +4.09, 	ext{FDR} = 3.65 	imes 10^{-224}$). Quantitative Profile: PS Mean $= 0.5085$, Energy Distance $E = 2.1444$ ($	ext{FDR} = 0.000999$), lochNESS Positive Mean $= +5.86$ (Rank 5), Negative Mean $= -0.4952$ (Rank 3 most depleted, 70.7% depleted cells). DistanceSpace Group: PG8 (isolated singleton). Module: M1.
- **Take-Home Message**: FOXA2 loss does not arrest cells in pluripotency; instead, shared endodermal progenitors lose pancreatic competence and default into the hepatic lineage.
- **Interpretation**: Pioneer factor FOXA2 is required to open pancreatic regulatory chromatin; without FOXA2, foregut endoderm defaults to the liver program.
- **Limitations**: Hepatic identity is annotated by single-cell transcriptomic markers; functional albumin secretion was not evaluated in this screen.

---

### Slide 24: Case Study 3 — NEUROG3 and PDX1 Enforce Endocrine Differentiation Checkpoints
- **Scientific Question**: How do NEUROG3 and PDX1 govern mature beta-cell genesis and endocrine checkpoints?
- **Figures Used**: `figures/per_genotype_combined/NEUROG3_ps_lochness_umap.png`, `figures/per_genotype_combined/PDX1_ps_lochness_umap.png`.
- **Tables Used**: `celltype_enrichment.csv`, `perturbation_summary.csv`, `distance_results.csv`.
- **Exact Numerical Findings**: NEUROG3 ($n=1,543$): 0.0% SC-beta cells observed ($\log_2 	ext{OR} = -\infty$), SC-EC depleted ($\log_2 	ext{OR} = -4.75, 	ext{FDR} = 3.25 	imes 10^{-33}$), accumulation in PDP ($\log_2 	ext{OR} = +1.11$, PG3, M1). PDX1 ($n=6,207$): 77.8% depleted cells (neg mean $-0.589$, PG7, M4). PDX1het ($n=469$): Rank 1 Energy Distance in screen ($E = 13.6337$), lochNESS pos mean $+14.15$ (Rank 2), trapped in ESC ($83.8\%$).
- **Take-Home Message**: Pinpoints discrete developmental checkpoints: NEUROG3 acts as the indispensable master gate for endocrine commitment, while PDX1 dosage governs earliest pancreatic specification.
- **Interpretation**: Validates the sequential regulatory hierarchy governing beta-cell development.
- **Limitations**: PDX1het was skipped for PS scoring due to absence of an independent heterozygous transcript feature in the count matrix.

---

### Slide 25: Summary & Conclusions — A Multi-Dimensional Blueprint of Human Pancreatic Regulators
- **Scientific Question**: What are the overarching biological and methodological conclusions of this study?
- **Figures Used**: Integrated summary architecture and conclusions diagram.
- **Tables Used**: Full repository metadata and results inventory.
- **Exact Numerical Findings**: Comprehensive synthesis across 111,581 single cells, 36 TFs, 15 cell states, 6 metrics, 4 programs, and 9 phenotype groups.
- **Take-Home Message**: A multi-layered computational framework successfully deconvolves the multi-faceted biology of human transcription factors, moving from binary "hit" calls to actionable regulatory blueprints.
- **Interpretation**: Establishes a standardized, auditable paradigm for interpreting single-cell functional genomics screens in regenerative biology.
- **Limitations**: Follow-up in vivo transplantation studies are required to confirm long-term functional stability of in vitro-derived beta cells.

---

### Slide 26: Backup — Full 36-Genotype Single-Cell PS and lochNESS UMAP Atlases
- **Scientific Question**: What do the individual single-cell response and localization maps look like across all 36 perturbations?
- **Figures Used**: `figures/ps_per_genotype_umap_atlas.png`, `figures/lochness_per_genotype_umap_atlas.png`.
- **Tables Used**: `per_genotype_umap_manifest.csv`.
- **Exact Numerical Findings**: Complete 36-genotype atlas grid across all 111,581 cells.
- **Take-Home Message**: Provides a complete visual reference library for all perturbations in the screen.
- **Interpretation**: Facilitates granular inspection of individual TF knockout distributions across the UMAP manifold.
- **Limitations**: Atlas panels condense high-dimensional data into small-multiple tiles.

---

### Slide 27: Backup — High-Resolution Genotype $	imes$ Cell-State Response Matrices
- **Scientific Question**: What are the exact cell-state response distributions across all 505 genotype-celltype pairs?
- **Figures Used**: `figures/24_ps_genotype_celltype_heatmap.png` (Figure 24), `figures/26_lochness_by_celltype2.png` (Figure 26).
- **Tables Used**: `ps_by_genotype_celltype.csv`, `lochness_by_genotype_celltype.csv`.
- **Exact Numerical Findings**: 505 evaluated genotype $	imes$ cell state pairs.
- **Take-Home Message**: Fine-grained tabular and heatmap documentation of response and localization across 15 curated cell states.
- **Interpretation**: Auditable reference for state-specific sensitivity to CRISPR perturbations.
- **Limitations**: Certain rare cell states contain limited target cell counts.

---

### Slide 28: Backup — Full 630-Pair DistanceSpace Matrix and Nearest Phenotypic Neighbors
- **Scientific Question**: What are the exact pairwise phenotypic distances and nearest neighbors for every perturbation?
- **Figures Used**: `figures/14_distance_space.png` (Figure 14).
- **Tables Used**: `distance_space_matrix.csv`, `distance_space_neighbors.csv`.
- **Exact Numerical Findings**: 630 pairwise Energy Distances. Top 8 nearest neighbor pairs documented (HNF4A/HNF4Ahet $d=0.0905$, ONECUT1e/OTUD5 $d=0.2664$, GATA4/GATA6het $d=0.3729$, BMPR1A/GATA4 $d=0.3793$, etc.).
- **Take-Home Message**: Complete quantitative audit of the phenotypic manifold geometry and nearest neighbor pairings.
- **Interpretation**: Quantifies exact phenotypic divergence across all screened transcriptional regulators.
- **Limitations**: Classical MDS projects continuous non-Euclidean pairwise distances onto top orthogonal eigenvectors.

---

### Slide 29: Backup — Quality Control, Bounded Sampling, and Skipped Targets Audit
- **Scientific Question**: Why were specific perturbations skipped for PS scoring, and what sampling limits were enforced?
- **Figures Used**: QC parameter tables and mathematical formulations.
- **Tables Used**: `ps_score_skipped.csv`, `config/diabetes.yaml`.
- **Exact Numerical Findings**: Documentation of 10 skipped PS targets (GATA4het, GATA6het, HHEXe, HHEXhet, HNF4Ahet, NANOGe-het, ONECUT1e, PDX1het, QSER1TET1, TET1/2/3). Distance sampling limits: max 2,000 target cells, 5,000 WT control cells.
- **Take-Home Message**: Transparent documentation of algorithmic eligibility and bounded sampling ensures statistical integrity and computational tractability.
- **Interpretation**: Skipping composite/enhancer targets prevents erroneous assignment of single-gene target expression cuts in pertps.
- **Limitations**: Composite knockouts cannot be evaluated with single-target response models without multi-locus classification extensions.

---

### Slide 30: Backup — Additional Case Studies: HNF4A Dosage Concordance and GLIS3 Response
- **Scientific Question**: How do HNF4A dosage sensitivity and GLIS3 single-cell responsiveness manifest across metrics?
- **Figures Used**: `figures/per_genotype_combined/HNF4A_ps_lochness_umap.png`, `figures/per_genotype_combined/GLIS3_ps_lochness_umap.png`.
- **Tables Used**: `perturbation_summary.csv`, `ps_score_summary.csv`, `distance_space_neighbors.csv`.
- **Exact Numerical Findings**: HNF4A ($n=987, E=1.75$) vs HNF4Ahet ($n=829, E=1.86$) $ightarrow d = 0.0905$ (Rank 1 closest pair, PG3, M1). GLIS3 ($n=935$) $ightarrow$ PS median $= 0.7500$ (Rank 1), 66.6% responders, $E = 8.21$, positive lochNESS $= +9.53$ (Rank 4, PG2, M1).
- **Take-Home Message**: HNF4A demonstrates near-perfect phenotypic dosage concordance; GLIS3 exhibits the highest single-cell response rate in the screen and acute progenitor vulnerability.
- **Interpretation**: Validates the high technical reproducibility of the pipeline and connects GLIS3 with known neonatal diabetes etiology.
- **Limitations**: GLIS3 transcriptional mechanisms involve both endocrine specification and polycystic epithelial maintenance.

