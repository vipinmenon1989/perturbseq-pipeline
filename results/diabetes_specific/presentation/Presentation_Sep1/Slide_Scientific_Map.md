# Master Slide Scientific Map & Narrative Blueprint

**Presentation File:** `presentation/PertTF_Master_Scientific_Story.pptx`  
**Total Slides:** 34  
**Balance:** Precursor Biology: 7 slides (20.6%) | pertTF AI Model: 13 slides (38.2%) | WIP Multi-Dimensional Decomposition: 6 slides (17.6%) | Framing & Conclusion: 4 slides (11.8%) | Technical Backup: 4 slides (11.8%)

---

## SECTION-BY-SECTION SLIDE BLUEPRINT

### PART 1: TITLE & EXECUTIVE FRAMING
- **Slide 1: Title Slide**
  - **Scientific Focus:** Context-Aware AI Modeling for Genome-Scale Perturbation Prediction Across Pancreatic Lineages and Disease States.
  - **Main Conclusion:** Bridges single-cell developmental genetics (knockout villages) to deep learning (pertTF) and multi-dimensional phenotypic decomposition.
  - **Why Next Slide Follows:** Establishes the three integrated pillars of the scientific presentation.

- **Slide 2: Scientific Framing & Executive Overview**
  - **Scientific Focus:** Three-pillar roadmap connecting causal biology, perturbation prediction, and multi-scale phenotyping.
  - **Main Conclusion:** Causal biology motivates AI modeling; AI prediction requires multi-scale decomposition.
  - **Why Next Slide Follows:** Begins Section 1 by examining the biological developmental system.

---

### PART 2: SECTION 1 — BIOLOGICAL FOUNDATION & PRECURSOR DISCOVERY
- **Slide 3: Human Pancreatic Differentiation Models Causal Disease Checkpoints**
  - **Scientific Question:** Why is human pancreatic differentiation an ideal system for studying genetic perturbations?
  - **Source Figure:** Precursor Figure 1a (`clean_sources/precursor_figures_png/Fig.1-1.png`).
  - **Main Conclusion:** Directed in vitro hPSC differentiation mirrors human embryonic islet development across 5 stages, providing an isogenic human platform to study monogenic diabetes mutations.
  - **Why Next Slide Follows:** Introduces the experimental platform used to profile multiple mutations simultaneously.

- **Slide 4: A Single-Cell Knockout Village Profiles 30 Regulators Across 5 Stages**
  - **Scientific Question:** How can we profile dozens of genetic knockouts across differentiation without batch effects?
  - **Source Figure:** Precursor Figure 1 (`clean_sources/precursor_figures_png/Fig.1-1.png`).
  - **Main Conclusion:** 79 uniquely barcoded clonal lines targeting 30 disease genes were pooled with 70% unlabeled WT cells, generating 111,581 single cells across 14 cell types.
  - **Why Next Slide Follows:** Investigates the primary biological outcome: beta-cell differentiation.

- **Slide 5: Loss of Lineage Regulators Impairs Beta-Cell Formation and Maturation**
  - **Scientific Question:** Which genetic mutations eliminate beta cells vs disrupt functional maturation?
  - **Source Figure:** Precursor Figure 2 (`clean_sources/precursor_figures_png/Fig.2-1.png`).
  - **Main Conclusion:** PDX1, RFX6, PAX6, and NEUROD1 eliminate SC-beta cells (<1% yield), while HNF4A beta cells survive but lose mature insulin secretion machinery.
  - **Why Next Slide Follows:** Asks where mutant cells divert when beta-cell fate fails.

- **Slide 6: Perturbations Divert Progenitors into Alternative Non-Pancreatic Lineages**
  - **Scientific Question:** Do arrested cells die or divert into non-pancreatic lineages?
  - **Source Figure:** Precursor Figure 3 (`clean_sources/precursor_figures_png/Fig.3-1.png`).
  - **Main Conclusion:** GATA6-/- diverts endoderm into Endothelial cells; FOXA2-/- diverts foregut into Hepatic liver progenitors; HHEX-/- causes gut tube arrest.
  - **Why Next Slide Follows:** Investigates late endocrine mutants that maintain endocrine commitment (CHGA+).

- **Slide 7: RFX6, PDX1, and PAX6 Regulate a Reciprocal SC-Beta vs SC-EC Fate Choice**
  - **Scientific Question:** What alternative endocrine cell type expands when beta cells fail to form?
  - **Source Figure:** Precursor Figure 4 (`clean_sources/precursor_figures_png/Fig.4-1.png`).
  - **Main Conclusion:** Loss of RFX6, PDX1, or PAX6 triggers a stoichiometric collapse of SC-beta and an expansion of serotonergic enterochromaffin-like cells (SC-EC) to >70-80% of endocrine cells.
  - **Why Next Slide Follows:** Identifies the molecular regulon and upstream causal repressor of this SC-EC fate.

- **Slide 8: Predictive Modeling Identifies ISL1 as a Key Repressor Safeguarding Beta Fate**
  - **Scientific Question:** Can predictive regression identify the causal master repressor of SC-EC diversion?
  - **Source Figure:** Precursor Figure 5/6 (`clean_sources/precursor_pdf_pages/page-44.png`).
  - **Main Conclusion:** Linear regression identified ISL1 as the top negative predictor of SC-EC fate; ISL1-/- expanded SC-EC, while ISL1 overexpression rescued SC-EC suppression across all mutant lines.
  - **Why Next Slide Follows:** Highlights the experimental bottleneck of testing genes one-by-one.

- **Slide 9: The Combinatorial Barrier: Why We Need Transferable Perturbation Models**
  - **Scientific Question:** Why can we not experimentally screen every gene across every cell context?
  - **Source Concept:** The ~20,000 gene x context explosion and foundation model generalizability limits.
  - **Main Conclusion:** Physical screening cannot scale across millions of conditions; motivates building the context-aware pertTF transformer framework.
  - **Why Next Slide Follows:** Introduces the core pertTF model architecture.

---

### PART 3: SECTION 2 — pertTF: CONTEXT-AWARE AI MODELING
- **Slide 10: pertTF: A Context-Aware Transformer for Genetic Perturbation Prediction**
  - **Scientific Question:** What is the architectural design of pertTF?
  - **Source Figure:** pertTF Figure 1b (`clean_sources/pertTF_pdf_pages/page-04.png`).
  - **Main Conclusion:** Transformer encoder with negative binomial NLL reconstruction loss, supervised contrastive latent learning, and gene graph priors.
  - **Why Next Slide Follows:** Evaluates baseline representation capacity.

- **Slide 11: Multi-Task Learning Yields High-Resolution Cellular and Genotype Embeddings**
  - **Scientific Question:** Does pertTF outperform standard foundation models on classification benchmarks?
  - **Source Figure:** pertTF Figure 1c-f (`clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img3.png`).
  - **Main Conclusion:** Achieved Macro F1 > 0.98 for cell types and F1 ~ 0.84 for masked genotype classification (outperforming scGPT F1 ~ 0.61).
  - **Why Next Slide Follows:** Advances from expression classification to higher-order phenotype prediction.

- **Slide 12: Beyond Expression: lochNESS Quantifies Higher-Order Cell Composition Shifts**
  - **Scientific Question:** Can pertTF predict population-level lineage shifts rather than point-wise gene averages?
  - **Source Figure:** pertTF Figure 2 (`clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img0.png`).
  - **Main Conclusion:** lochNESS regression captures local enrichment/depletion (Pearson r ~ 0.88 for PDX1), outperforming expression baselines (AUC ~ 0.86 vs 0.64).
  - **Why Next Slide Follows:** Tests out-of-distribution generalization in unseen cellular contexts.

- **Slide 13: Predicting Perturbation Outcomes in Held-Out, Unseen Cellular Contexts**
  - **Scientific Question:** Can pertTF predict mutations in cell types never seen in perturbed form during training?
  - **Source Figure:** pertTF Figure 3a-b (`clean_sources/pertTF_pdf_pages/page-20.png`).
  - **Main Conclusion:** Predicted held-out SC-beta PDX1 KO with Cosine Sim ~ 0.91, PCC-delta ~ 0.72, and DE-direction ~ 85% (beating scGPT Cosine ~ 0.74).
  - **Why Next Slide Follows:** Tests generalization to entirely unseen gene perturbations.

- **Slide 14: Leave-One-Genotype-Out Testing Demonstrates Generalization to Unseen Genes**
  - **Scientific Question:** Can pertTF predict the effects of novel knockouts absent from training data?
  - **Source Figure:** pertTF Figure 3c (`clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img4.png`).
  - **Main Conclusion:** Across 30 held-out genotypes, pertTF achieved mean Cosine Sim ~ 0.86 (winning in 27/30 genes vs scGPT ~ 0.70).
  - **Why Next Slide Follows:** Evaluates the compound joint generalization challenge.

- **Slide 15: Joint Generalization: Predicting Unseen Genes in Unseen Cell Contexts**
  - **Scientific Question:** Can pertTF predict novel knockouts in novel cell lineages simultaneously?
  - **Source Figure:** pertTF Figure 3d (`clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide4_img24.png`).
  - **Main Conclusion:** Maintained Cosine Sim ~ 0.81 and PCC-delta ~ 0.61 (vs scGPT Cosine ~ 0.59, PCC ~ 0.34).
  - **Why Next Slide Follows:** Validates predictions on an orthogonal perturbation modality (CRISPRi).

- **Slide 16: Orthogonal Validation: Generalizing to Partial CRISPRi Repression**
  - **Scientific Question:** Do learned representations transfer to partial CRISPRi knockdowns?
  - **Source Figure:** pertTF Figure 4 (`clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide5_img26.png`).
  - **Main Conclusion:** Mixscape and per-cell PS scoring isolated responders; pertTF accurately predicted CTNNB1 knockdown shift (Cosine ~ 0.89 vs scGPT ~ 0.68).
  - **Why Next Slide Follows:** Translates model to primary clinical patient tissues.

- **Slide 17: Clinical Transfer: Fine-Tuning pertTF on Primary Human Adult Islets**
  - **Scientific Question:** Can in vitro representations project onto primary adult human islets?
  - **Source Figure:** pertTF Figure 5a-c (`clean_sources/pertTF_extracted_pptx_images/Fig._5_v4_slide1_img0.png`).
  - **Main Conclusion:** Rapid fine-tuning with <300 primary cells achieved F1 > 0.96 across mature islet endocrine lineages.
  - **Why Next Slide Follows:** Analyzes latent perturbation states in T2D patient islets.

- **Slide 18: Latent PDX1, NEUROD1, and HNF4A Disruption Enriches in Clinical T2D Donors**
  - **Scientific Question:** Does clinical T2D islet pathology mirror developmental knockout failure modes?
  - **Source Figure:** pertTF Figure 5d-e (`clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide6_img29.png`).
  - **Main Conclusion:** Inferred PDX1 loss state increased ~3.8-fold in T2D donors (p < 0.0001); fragile beta-2 cells showed marked NEUROD1 and HNF4A disruption.
  - **Why Next Slide Follows:** Validates latent predictions experimentally in primary islets.

- **Slide 19: Primary Islet siRNA Validation Confirms In Silico Latent Predictions**
  - **Scientific Question:** Does experimental primary islet knockdown validate model predictions?
  - **Source Figure:** pertTF Figure 5g-h (`clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide6_img31.png`).
  - **Main Conclusion:** pertTF accurately classified ~78% of RFX6 siRNA knockdown cells as perturbed (vs <5% control, Cosine ~ 0.87).
  - **Why Next Slide Follows:** Deploys pertTF for genome-wide virtual genetic screening.

- **Slide 20: Virtual Genetic Screening: In Silico Prioritization of Progenitor Regulators**
  - **Scientific Question:** Can pertTF perform genome-wide in silico CRISPR screens?
  - **Source Figure:** pertTF Figure 6a-d (`clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img4.png`).
  - **Main Conclusion:** Benchmarked against experimental PDX1-GFP screen (>18,000 genes); pertTF achieved ROC-AUC = 0.79 (TEXT-VERIFIED) vs 0.66 for expression baseline.
  - **Why Next Slide Follows:** Calibrates essential genes and models multi-protein complexes.

- **Slide 21: Essential-Gene Calibration and Genome-Scale In Silico Perturb-seq**
  - **Scientific Question:** Can pertTF predict essential gene lethality and chromatin complex dynamics?
  - **Source Figure:** pertTF Figure 6e-j (`clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img3.png`).
  - **Main Conclusion:** Correctly predicted negative lochNESS for unseen essential genes (MRPS5, p < 10^-15); co-clustered SMARCC1/SMARCD1 and SALL4/TCF7L1 complexes.
  - **Why Next Slide Follows:** Synthesizes pertTF computational capabilities and boundaries.

- **Slide 22: pertTF Computational Synthesis: Context-Aware Modeling Across Scales**
  - **Scientific Focus:** Summary of verified computational breakthroughs and conceptual limitations.
  - **Main Conclusion:** pertTF provides scalable, context-aware predictions, but end-to-end latent vectors compress distinct biological phenomena.
  - **Why Next Slide Follows:** Motivates the WIP multi-dimensional phenotypic decomposition.

---

### PART 4: SECTION 3 — MULTI-DIMENSIONAL PHENOTYPIC DECOMPOSITION (WIP)
- **Slide 23: The Next Question: What Remains Compressed Inside a Perturbation Prediction?**
  - **Scientific Focus:** Decompressing end-to-end predictions into penetrance, magnitude, and localization.
  - **Main Conclusion:** Formulates the need for three explicit coordinates: PS, Energy Distance, and signed lochNESS.
  - **Why Next Slide Follows:** Defines the mathematical properties of each dimension.

- **Slide 24: Three Complementary Dimensions of Single-Cell Perturbation Phenotypes**
  - **Scientific Focus:** Formalizing PS penetrance, Energy Distance magnitude, and signed lochNESS localization.
  - **Source Figure:** WIP Figure 19 (`figures/19_perturbation_summary.png`).
  - **Main Conclusion:** PS measures continuous response probability [0, 1]; Energy Distance measures multivariate displacement; signed lochNESS measures directional state trapping/loss.
  - **Why Next Slide Follows:** Evaluates coupling between single-cell penetrance and global magnitude.

- **Slide 25: Response Penetrance Strongly Couples with Global Multivariate Magnitude**
  - **Scientific Question:** Does high single-cell response strength predict large population-level shifts?
  - **Source Figure:** WIP Figure 07 (`figures/07_ps_vs_distance.png`).
  - **Main Conclusion:** Median PS and Energy Distance are strongly correlated (Spearman rho = +0.6410, p = 4.18 x 10^-4, n = 26).
  - **Why Next Slide Follows:** Tests whether single-cell penetrance dictates directional state localization.

- **Slide 26: Single-Cell Penetrance Decouples from Directional State Localization**
  - **Scientific Question:** Does high penetrance dictate where cells localize on the manifold?
  - **Source Figure:** WIP Figure 10/11 (`figures/10_ps_vs_lochness_positive.png`).
  - **Main Conclusion:** PS is completely decoupled from positive lochNESS (rho = +0.0612, p = 0.7665) and negative lochNESS (rho = -0.1715, p = 0.4123).
  - **Why Next Slide Follows:** Synthesizes these dimensions into audited case study profiles.

- **Slide 27: Multi-Scale Case Studies: Tracking PDX1, GATA6, and FOXA2 Across Stages**
  - **Scientific Focus:** Comprehensive case study tracking across Precursor, pertTF, and WIP.
  - **Source Figure:** WIP Figure 28 (`figures/28_umap_highlight_genotypes.png`).
  - **Main Conclusion:** PDX1het shows #1 highest Energy Distance (13.6337, MMD 0.3129); GATA6 combines high PS (0.6482) and endothelial trapping (+4.530); FOXA2 exhibits peak Liver trapping (+13.740).
  - **Why Next Slide Follows:** Examines higher-order manifold geometry.

- **Slide 28: DistanceSpace and Downstream Modules Reveal Higher-Order Architecture**
  - **Scientific Question:** How do perturbations organize into geometric similarity vs regulatory modules?
  - **Source Figure:** WIP Figure 14 (`figures/14_distance_space.png`).
  - **Main Conclusion:** DistanceSpace partitions 630 pairwise comparisons into 9 Phenotype Groups; Stage 7 partitions perturbation-to-gene effects into 6 Co-Functional Modules.
  - **Why Next Slide Follows:** Summarizes the overall master story and future roadmap.

---

### PART 5: CONCLUSION & FUTURE OUTLOOK
- **Slide 29: A Complete Scientific Trajectory: From Developmental Genetics to AI**
  - **Scientific Focus:** Integrated summary across biological discovery, AI modeling, and multi-scale phenotyping.
  - **Main Conclusion:** Unifies the end-to-end scientific narrative.
  - **Why Next Slide Follows:** Projects the computational roadmap forward.

- **Slide 30: Toward Next-Generation Phenotype-Aware Perturbation Models**
  - **Scientific Focus:** Roadmap for multi-objective loss engineering, massive dataset scaling, and multimodal integration.
  - **Main Conclusion:** Future foundation models will embed multi-dimensional phenotypic loss functions directly during pre-training.

---

### PART 6: TECHNICAL BACKUP SLIDES
- **Slide 31: Backup | DistanceTest Methodology and Permutation Resolution Floor** (WIP Fig 06)
- **Slide 32: Backup | Single-Cell PS and lochNESS Manifold Atlases** (WIP Fig 27)
- **Slide 33: Backup | High-Resolution Genotype x Cell-State Response Matrices** (WIP Fig 13)
- **Slide 34: Backup | Quality Control, Bounded Sampling, and Skipped Targets Audit** (Audit table)
