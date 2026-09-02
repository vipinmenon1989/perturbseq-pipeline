# Master Scientific Story Deck Inventory
**Primary PPTX Output:** `Thomas_Sandmann_Master_Biology_Computation_pertTF.pptx` / `Master_Scientific_Story_pertTF_Phenotyping.pptx`  
**Core Scientific Story Spine:**
```
BIOLOGICAL QUESTION
        ↓
EXPERIMENTAL SYSTEM
        ↓
DATA QUALITY / PERTURBATION SIGNAL
        ↓
COMPUTATIONAL CHARACTERIZATION OF THE DATA
        ↓
pertTF
        ↓
GENERALIZATION TO EXPERIMENTALLY DIFFICULT / UNSEEN CONTEXTS
        ↓
LIMITATIONS OF ML-ONLY INTERPRETATION
        ↓
CURRENT COMPUTATIONAL-BIOLOGY EXTENSION
        ↓
DECOMPOSE THE PERTURBATION SIGNAL
        ↓
IDENTIFY COMPLEMENTARY BIOLOGICAL FEATURES
        ↓
IMPROVE FUTURE PERTURBATION MODELS
```

---

## Complete Slide-by-Slide Inventory (43 Slides)

| Slide # | Slide Title | Scientific Section | Source Panels / Figures | Key Biological & Computational Takeaways |
|:---|:---|:---|:---|:---|
| **1** | Decoding Human Pancreatic Differentiation & Monogenic Diabetes | Title & Scope | Custom Hero Layout | Unified continuous scientific story spanning human pancreatic development, knockout villages, context-aware transformers (pertTF), and statistical phenotype decomposition. |
| **2** | The Master Scientific Narrative Arc | Scientific Progression | 6-Pillar Overview Framework | Roadmap connecting biological question → knockout village → descriptive QC → pertTF transformer → generalization frontiers → phenotype decomposition → future closed-loop models. |
| **3** | Pancreatic Beta-Cell Development & Monogenic Diabetes Genetics | 1. Biological Question | `precursor_fig1a_genes.png`, `precursor_fig1b_workflow.png` | 30 high-confidence diabetes-associated TFs and chromatin regulators; 18-day directed differentiation through 5 stages (DE → PFG → PP → SC-islet). |
| **4** | Knockout Village Strategy & Single-Cell Differentiation Kinetics | 2. Experimental System | `precursor_fig1cd_kinetics.png`, `precursor_fig1e_pca.png` | Pooling 79 sequence-verified hPSC knockout clones in a shared culture eliminates batch effects; resolves stage-specific selection and pseudo-bulk PCA fidelity. |
| **5** | Single-Cell Differentiation Landscape & Cell-State Manifold | 3. Descriptive Data QC | `01_umap_celltype2.png`, `02_umap_development_stage.png` | 111,581 cells across 10 curated cell states and 5 synchronized stages; establishes high-resolution reference manifold prior to modeling. |
| **6** | Stage-Specific Cell Composition & Perturbation Distribution | 3. Descriptive Data QC | `03_stage_celltype_composition.png`, `28_umap_highlight_genotypes.png` | Synchronous state transitions; mutant genotypes separate systematically from WT controls, proving rich perturbation signal exists. |
| **7** | Loss of Lineage Regulators Impairs Beta-Cell Yield and State | 4. Biological Perturbation Signal | `precursor_fig2a_volcano.png`, `precursor_fig2b_state_scores.png` | Catastrophic loss of SC-β fraction in NEUROG3, BMPR1A, PDX1, RFX6, PAX6; surviving mutant cells show disrupted mature transcriptional states. |
| **8** | Lineage Rewiring: Master Binary Switches Divert Differentiation | 4. Biological Perturbation Signal | `precursor_fig3a_intended_dotplot.png`, `precursor_fig3bcd_alternative_fates.png` | TF knockouts cause active lineage diversion: GATA6 KO causes endothelial conversion (CD31+/CD34+); FOXA2 KO diverts to hepatic fate (AFP+/ALB+). |
| **9** | Endocrine Competition (SC-β vs SC-EC) & ISL1 Predictive Rescue | 4. Biological Perturbation Signal | `precursor_fig4ab_ec_quant.png`, `precursor_fig6cde_isl1_validation.png` | RFX6/PDX1/PAX6 loss shifts cells into serotonin-producing SC-EC fate; regression model prioritizes ISL1 as repressor (>70% wet-lab rescue). |
| **10** | The Combinatorial Bottleneck & Why Simple DE Fails: Introducing lochNESS | 5. Modeling Opportunity | `pertTF_fig2abcd_lochness_theory.png` (Fig 2a,b) | Intractable search space (>100,000 combinations); simple DE fails manifold shifts; lochNESS measures local k-NN density odds ratio. |
| **11** | pertTF Architecture: Dual-Input Transformer & Multi-Task Optimization | 6. pertTF Model | `pertTF_fig1ab_arch.png` | Dual-input expression + perturbation tokens; multi-task loss (cell identity + genotype classification + masked reconstruction) learns transferable operators. |
| **12** | Baseline Performance & Latent Embedding Geometry | 6. pertTF Model | `pertTF_fig1cdef_perf.png` | High classification accuracy (AUC > 0.94); latent embeddings organize cells along continuous perturbation displacement vectors without collapse. |
| **13** | Predicting Cell-State Composition Changes & lochNESS Scores | 6. pertTF Validation | `pertTF_fig2abcd_lochness_theory.png` (Fig 2c,d) | Accurately predicts PDX1 and TADA2B lochNESS shifts; significantly outperforms naive gene expression baselines (r = 0.82 vs 0.41, p < 1e-4). |
| **14** | Generalization to Unseen Cell Types and Developmental Contexts | 7. Generalization Frontiers | `pertTF_fig2efg_unseen_celltype.png` | Withholding PDX1-KO pancreatic-duodenal progenitors (PDP) from training; model predicts true knockout embedding shift (cosine similarity > 0.86). |
| **15** | Generalizing to Unseen Perturbations via Graph Neural Networks | 7. Generalization Frontiers | `pertTF_fig3ab_gnn_pdx1.png` | GNN trained on STRING PPI network embeds unmutated genes; leave-one-gene-out validation accurately predicts PDX1 loss phenotype. |
| **16** | Systematic Benchmarking Against Single-Cell Foundation Models | 7. Generalization Frontiers | `pertTF_fig3cd_benchmarks.png` | Head-to-head evaluation against scGPT, GEARS, and scFoundation; pertTF achieves superior cosine similarity (mean 0.84 vs 0.68 scGPT) and lower MSE. |
| **17** | Cross-Platform Validation on Independent CRISPRi Perturb-seq | 7. Generalization Frontiers | `pertTF_fig4_crispri.png` | Validates on external CRISPRi screen without retraining; accurately predicts embedding shifts for 10 strong Mixscape perturbations (e.g. CTNNB1). |
| **18** | Clinical Translation: Transfer Learning to Primary Human Islets & T2D | 7. Generalization Frontiers | `pertTF_fig5abc_primary_ft.png`, `pertTF_fig5defgh_t2d_loss.png` | Fine-tuning on primary donor islets; classifies T2D beta-cells as having cryptic NEUROD1, HNF4A, or PDX1 loss; validated via primary islet siRNA. |
| **19** | In Silico Genetic Screening & Regulatory Discovery | 7. Generalization Frontiers | `pertTF_fig6abcd_insilico_screen.png`, `pertTF_fig6hij_insilico_perturbseq.png` | Virtual screen for PDX1+ progenitor factors prioritizes GATA6, MAPK1; validated vs. pooled CRISPR screen (ROC AUC = 0.79 vs 0.66). |
| **20** | What pertTF Achieves & What It Still Does Not Fully Explain | 8. Critical Scientific Pivot | Two-Card Analytical Comparison | Predictive ML generalizes across contexts, but accuracy alone does not decompose penetrance, global magnitude, and manifold destination. |
| **21** | Three Orthogonal Axes of Perturbation Biology | 9. Phenotype Decomposition | 3-Column Framework Card | Axis 1: PS (cellular penetrance); Axis 2: Energy Distance (global magnitude); Axis 3: Directional lochNESS (manifold localization). |
| **22** | Axis 1: Single-Cell Perturbation Score (PS) & Response Heterogeneity | 9. Phenotype Decomposition | `05_ps_by_perturbation.png`, `20_umap_ps_score.png` | Ranks 37 genotypes by mean PS (GATA6: 0.978, FOXA2: 0.912); UMAP reveals cell-state-gated response competence windows. |
| **23** | Axis 2: Global Transcriptomic Phenotype Magnitude via Energy Distance | 9. Phenotype Decomposition | `06_energy_distance_by_perturbation.png` | Non-parametric V-statistic in 50 PCA dimensions (FDR < 0.001); ranks severity: GATA6 (E=4.71), FOXA2 (E=3.11), RFX6 (E=2.45), HNF4A (E=1.75). |
| **24** | Axis 3: Directional lochNESS Resolves Enrichment, Trapping, and Depletion | 9. Phenotype Decomposition | `21_umap_lochness_score.png`, `lochness_genotype_celltype_heatmap.png` | Signed analytical lochNESS separates positive focal trapping (+lochNESS) from negative lineage dropout (-lochNESS) across 10 cell types. |
| **25** | Response Strength Predicts Global Phenotype Magnitude | 10. Cross-Metric Analysis | `07_ps_vs_distance.png` | Strong linear coupling between Axis 1 (PS) and Axis 2 (Energy Distance): Spearman rho = 0.81 (p = 1.3e-6, n = 26 evaluated genotypes). |
| **26** | Global Magnitude Does Not Specify Cellular Destination | 10. Cross-Metric Analysis | `08_distance_vs_lochness_positive.png`, `12_distance_vs_lochness_absolute.png` | Moderate correlation (rho = 0.44 to 0.52); perturbations with identical Energy Distance diverge into completely different manifold fates. |
| **27** | Directionality Decouples Lineage Enrichment from Depletion | 10. Cross-Metric Analysis | `09_distance_vs_lochness_negative.png`, `10_ps_vs_lochness_positive.png` | Negative lochNESS correlates with Energy Distance (rho = -0.50), proving severe knockouts drive both deeper depletion and higher trapping. |
| **28** | Case Study 1: GATA6 — Endothelial Conversion & Focal Trapping | 11. Biological Case Studies | `GATA6_ps_lochness_umap.png` | Precursor biology + pertTF screening + WIP metrics: Rank 1 in penetrance (PS = 0.978), Rank 1 in magnitude (E = 4.71), focal +lochNESS (+0.83). |
| **29** | Case Study 2: FOXA2 — Pioneer Factor Loss & Hepatic Diversion | 11. Biological Case Studies | `FOXA2_ps_lochness_umap.png` | Precursor foregut biology + pertTF PFG recovery + WIP metrics: Rank 2 severity (E = 3.11, PS = 0.912), positive lochNESS in hepatic states (+0.54). |
| **30** | Case Study 3: NEUROG3 vs. PDX1 — Divergent Endocrine Checkpoints | 11. Biological Case Studies | `NEUROG3_ps_lochness_umap.png`, `PDX1_ps_lochness_umap.png` | NEUROG3 blocks endocrine entry (-lochNESS = -0.58); PDX1 permits endocrine entry but misroutes cells into SC-EC (+lochNESS = +0.48). |
| **31** | Case Study 4: HNF4A & GLIS3 — Dosage Concordance & High Responders | 11. Biological Case Studies | `HNF4A_ps_lochness_umap.png`, `GLIS3_ps_lochness_umap.png` | HNF4A KO and HNF4Ahet show near-identical displacement (d = 0.0905, Rank 1 neighbor), explaining MODY1 haploinsufficiency; GLIS3 PS = 0.895. |
| **32** | Case Study 5: RFX6 & HHEX — Endocrine Maturation & Enhancer Phenocopy | 11. Biological Case Studies | `RFX6_ps_lochness_umap.png`, `HHEX_ps_lochness_umap.png` | RFX6 validated in primary islets (E = 2.45, PS = 0.865); non-coding enhancer deletion HHEXe phenocopies coding KO (d = 0.1142, Rank 2 pair). |
| **33** | Higher-Order Organization: DistanceSpace & Regulatory Modules | 11. System Architecture | `14_distance_space.png`, `18_module_network.png` | 2D UMAP embedding of 630-pair Energy Distance matrix; reconstructs 6 TF regulatory modules (M1-M6) driving 8 downstream gene programs. |
| **34** | Integrated Multi-Metric Summary Across All 37 Genotypes | 12. Synthesis & Atlas | `19_perturbation_summary.png` | Definitive visual master atlas aligning cell counts, PS penetrance, Energy Distance, and directional lochNESS across all 37 genotypes. |
| **35** | Closing the Loop: Toward Phenotype-Aware Perturbation Modeling | 12. Synthesis & Future ML | 5-Step Continuous Flow Card | Connecting biology → descriptive QC → pertTF generalization → 3-axis phenotype decomposition → candidate multi-task loss objectives for future ML. |
| **36** | Core Scientific Takeaway: A Unified Framework for Perturbation Genomics | 12. Final Synthesis | Dark Hero Summary Card | Complete synthesis of the continuous scientific progression from experimental question to statistical phenotyping and ML modeling. |
| **37** | Technical Backup & Methodological Audits | Backup Section Divider | Dark Card Divider | Table of contents for supporting technical slides, mathematical derivations, skipped target audits, and full screen atlases. |
| **38** | Mathematical Formulations & Skipped Target Audit | Backup BKP 1 | V-statistic equation, formulas | Exact V-statistic estimator for Energy Distance, lochNESS, and transparent audit of 10 skipped PS targets (all retained for Distance & lochNESS). |
| **39** | Full 36-Genotype Single-Cell PS and lochNESS UMAP Atlases | Backup BKP 2 | `ps_per_genotype_umap_atlas.png`, `lochness_per_genotype_umap_atlas.png` | Full 36-panel atlases displaying single-cell PS score density and lochNESS spatial projection across every evaluated line. |
| **40** | High-Resolution Genotype × Cell-State Response Heatmaps | Backup BKP 3 | `ps_genotype_celltype_heatmap.png`, `lochness_genotype_celltype_heatmap.png` | Complete 37 × 10 response matrices resolving cell-type-specific vulnerability windows for PS penetrance and lochNESS shifts. |
| **41** | Full 630-Pair DistanceSpace Matrix & Top Phenotypic Neighbors | Backup BKP 4 | `14_distance_space.png`, neighbor table | Quantitative ranking of closest phenotypic pairs: HNF4A/HNF4Ahet (d=0.0905), HHEX/HHEXe (d=0.1142), FOXA1/FOXA2 (d=0.3471). |
| **42** | Extended pertTF Benchmarks & CRISPRi Mixscape Analysis | Backup BKP 5 | `pertTF_supp_fig3_4_benchmarks.png`, `pertTF_supp_fig5_6_crispri_primary.png` | Supplementary foundation model comparison tables (scFoundation, scGPT, GEARS) and Mixscape single-cell response distributions. |
| **43** | Precursor Study QC, Genotyping & ISL1 Rescue Validation | Backup BKP 6 | `precursor_supp_fig1_qc.png`, `precursor_supp_fig8_isl1_rescue.png` | Sanger sequencing verification across 79 clones and qPCR/flow cytometry validation of ISL1 lentiviral rescue of beta-cell identity. |
