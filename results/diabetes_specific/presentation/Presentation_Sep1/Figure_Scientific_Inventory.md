# Figure-by-Figure Scientific Inventory

This inventory provides a comprehensive, rigorous panel-level deconstruction for all main figures and key supplementary figures across both manuscripts:
1. **pertTF Manuscript:** Su, Liu, Menon et al., 2026 (*pertTF: context-aware AI modeling for genome-scale and cross-system perturbation prediction*)
2. **Precursor Manuscript:** Liu, Song, Li, Zhang et al., 2025 (*A stem cell knockout village reveals lineage rewiring and a non-canonical islet cell fate in monogenic diabetes*)

---

## PART 1: pertTF MANUSCRIPT FIGURES

### Figure 1: The pertTF Model and Training Framework

- **Panel 1a: Knockout Village Training Data & Multi-Stage Sampling**
  - **Source File:** `pertTF.pdf` (Page 4), `pertTF-figures/Fig. 2_v5.pptx` / `clean_sources/pertTF_extracted_pptx_images/`
  - **Main/Supplementary:** Main Figure 1a
  - **Scientific Question:** How was the perturbation-resolved single-cell dataset generated across differentiation stages to train pertTF?
  - **Experimental Comparison:** Longitudinal differentiation across 5 stages (Day 0 ESC, Day 3 DE, Day 7 PFG, Day 11 EnP, Day 18 SC-islet) spanning 79 clonal lines and 30 gene knockouts.
  - **Axes / Visual Encoding:** Schematic diagram of differentiation pipeline, barcoding, pooling into village, FACS isolation, and 10x single-cell RNA sequencing.
  - **Biological Conclusion:** The dataset uniquely captures both developmental state progression and complete loss-of-function genetic knockouts across 14 cell types.
  - **Next Question:** How can a transformer architecture effectively ingest this multi-stage, multi-task perturbation dataset?
  - **Clean Source Available:** Yes (`pertTF-figures/Fig. 2_v5.pptx` & `clean_sources/pertTF_pdf_pages/page-04.png`).

- **Panel 1b: pertTF Architecture & Multi-Task Loss Formulation**
  - **Source File:** `pertTF.pdf` (Page 4), editable in `Diabetes_perTF.pptx` (Slide 3)
  - **Main/Supplementary:** Main Figure 1b
  - **Scientific Question:** What is the mathematical and architectural structure of pertTF?
  - **Visual Encoding:** Transformer encoder backbone with input gene tokens ($E_g + E_x$), perturbation embedding adapter ($E_p$), empty cell token ($E_c$), Negative Binomial NLL reconstruction loss, supervised contrastive loss, and classification heads.
  - **Biological Conclusion:** Multi-task formulation forces the model to learn decoupled yet interactive representations of cell state and perturbation status.
  - **Next Question:** Does pertTF outperform standard foundation models on cell-type and perturbation classification?

- **Panel 1c: Cell-Type Classification Benchmark**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 2_v5.pptx`
  - **Main/Supplementary:** Main Figure 1c
  - **Comparison:** pertTF vs Geneformer vs scGPT vs scFoundation across layer depths ($L=4, 8, 12$), heads ($H=4, 8, 12$), dimensions ($D=128, 256, 512$).
  - **Axes:** X-axis: Model architectures; Y-axis: Macro F1 score, Accuracy, AUPR.
  - **Quantitative Result:** pertTF (12L-8H-512D) achieved F1 = 0.985, AUPR = 0.998, ACC = 0.987 (vs scGPT F1 = 0.932).
  - **Biological Conclusion:** pertTF accurately preserves subtle cell identity distinctions across 14 differentiating cell types.

- **Panel 1d: Genotype / Perturbation Classification Benchmark**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 2_v5.pptx`
  - **Main/Supplementary:** Main Figure 1d
  - **Comparison:** Predicting masked perturbation identities from transcriptomes alone.
  - **Quantitative Result:** pertTF achieved Macro F1 = 0.842, AUPR = 0.887, ACC = 0.856 (vs scGPT F1 = 0.612, AUPR = 0.654).
  - **Biological Conclusion:** Single-cell transcriptomes contain strong, learnable mutant-specific regulatory footprints.

- **Panels 1e-f: Latent Cell Embeddings Colored by Cell Type (1e) and Genotype (1f)**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 2_v5.pptx`
  - **Main/Supplementary:** Main Figure 1e-f
  - **Axes:** UMAP 1 vs UMAP 2 of pertTF latent embeddings ($E_c$).
  - **Visual Encoding:** Colors represent 14 annotated cell types (1e) and 30 mutant genotypes + WT (1f).
  - **Observation:** Contrastive loss separates developmental states into distinct branches while partitioning genotypes within each state.
  - **Next Question:** Can pertTF use these embeddings to predict higher-order population composition shifts?

---

### Figure 2: Predicting Cell Composition Changes and lochNESS

- **Panel 2a: Concept of lochNESS Score**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 2a
  - **Visual Encoding:** Schematic illustrating $k$-NN local density ratio of perturbed vs WT cells in single-cell manifold. Positive lochNESS = enrichment ($>0$); Negative lochNESS = depletion ($<0$).
  - **Biological Purpose:** Bridges single-cell embeddings to population-level lineage shifts without requiring ad-hoc discrete clustering.

- **Panels 2b-c: Observed vs Predicted lochNESS for PDX1, TADA2B, and GATA4**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 2b-c
  - **Axes:** X-axis: Cell types; Y-axis: lochNESS score (log2 fold enrichment).
  - **Quantitative Result:** *PDX1* KO shows massive depletion in SC-beta (lochNESS < -3.5) and enrichment in EnP/SC-EC (lochNESS > +2.5). pertTF predicted scores correlate with observed at Pearson $r = 0.88$.
  - **Biological Conclusion:** pertTF captures both the direction and magnitude of cell-fate shifts.

- **Panels 2d-e: Benchmarking lochNESS Prediction vs Differential Expression Baselines**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 2d-e
  - **Comparison:** pertTF lochNESS regression head vs expression-based composition prediction.
  - **Quantitative Result:** pertTF achieved ROC-AUC = 0.86 vs 0.64 for expression baseline.
  - **Biological Conclusion:** Latent manifold geometry captures cell fate redirection far better than point-wise gene expression averages.

---

### Figure 3: Generalization to Unseen Cell Contexts and Unseen Perturbations

- **Panel 3a: Workflow for Unseen Context & Leave-One-Genotype-Out Testing**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 3a
  - **Visual Encoding:** Schematic showing: (1) Unseen context: target cell type perturbed cells held out; (2) Unseen gene: full genotype held out; (3) Joint unseen gene + context.

- **Panel 3b: PDX1 Perturbation Prediction in Held-Out SC-Beta Context**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 3b
  - **Comparison:** Real *PDX1* KO SC-beta cells vs pertTF predicted *PDX1* KO from WT SC-beta input.
  - **Quantitative Result:** Cosine Similarity = 0.912, PCC-delta = 0.724, DE-direction = 84.6%.
  - **Biological Conclusion:** Model understands lineage-specific vulnerability of beta cells to PDX1 loss without seeing perturbed beta cells during training.

- **Panel 3c: Systematic 30-Genotype Leave-One-Out Benchmark**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 3c
  - **Axes:** X-axis: 30 held-out genotypes; Y-axis: Cosine similarity to true perturbed embeddings.
  - **Quantitative Result:** pertTF achieved mean Cosine = 0.864 vs scGPT = 0.698 vs GEARS = 0.642. pertTF won in 27/30 genotypes.

- **Panel 3d: Joint Unseen Perturbation + Unseen Context Benchmark**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 3_v4.pptx`
  - **Main/Supplementary:** Main Figure 3d
  - **Quantitative Result:** pertTF Cosine Sim = 0.812, PCC-delta = 0.615 vs scGPT Cosine = 0.594, PCC = 0.341.
  - **Biological Conclusion:** pertTF generalizes across both axes of biological variation simultaneously.

---

### Figure 4: Independent Experimental Validations Using CRISPRi Perturb-seq

- **Panel 4a: 50-Gene CRISPRi Perturb-seq Experimental Architecture**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 4_v7.pptx`
  - **Main/Supplementary:** Main Figure 4a
  - **Visual Encoding:** Lentiviral CRISPRi library targeting 50 chromatin/TF genes in hPSCs, 10x scRNA-seq, Mixscape / PS score deconvolution.

- **Panel 4b: CTNNB1 Knockdown Shift & Expression Prediction**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 4_v7.pptx`
  - **Main/Supplementary:** Main Figure 4b
  - **Quantitative Result:** pertTF predicted *CTNNB1* embedding shift with Cosine Sim = 0.892 (vs scGPT 0.684, scFoundation 0.697).
  - **Biological Conclusion:** Knowledge learned from knockout villages transfers to orthogonal CRISPRi repression modalities.

- **Panels 4c-d: Genome-Wide CRISPRi Benchmark Summary**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 4_v7.pptx`
  - **Main/Supplementary:** Main Figure 4c-d
  - **Comparison:** pertTF vs scGPT vs scFoundation across all responsive CRISPRi targets.
  - **Quantitative Result:** Higher DEG correlation ($r = 0.781$) and lower MAE across top responsive targets.

---

### Figure 5: Application of pertTF to Primary Human Islet Datasets

- **Panel 5a: Transfer Learning Framework for Primary Human Islets**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 5_v4.pptx`
  - **Main/Supplementary:** Main Figure 5a
  - **Visual Encoding:** Adaptation of in vitro pertTF model to primary donor single-cell transcriptomes (Non-diabetic, Pre-T2D, T2D).

- **Panels 5b-c: Primary Islet Fine-Tuning Performance**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 5_v4.pptx`
  - **Main/Supplementary:** Main Figure 5b-c
  - **Result:** Rapid convergence to near-perfect F1 score (>0.96) within 5 epochs across mature islet endocrine cell types.

- **Panel 5d: PDX1 Loss State Enrichment in Clinical T2D Donors**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 5_v4.pptx`
  - **Main/Supplementary:** Main Figure 5d
  - **Quantitative Result:** Inferred *PDX1* loss state increased by 3.8-fold in T2D donors relative to non-diabetic controls ($p < 10^{-5}$).

- **Panel 5e: NEUROD1 & HNF4A Disruption in Beta-1 vs Beta-2 Subpopulations**
  - **Source File:** `pertTF.pdf` (Page 20), `pertTF-figures/Fig. 5_v4.pptx`
  - **Main/Supplementary:** Main Figure 5e
  - **Quantitative Result:** Fragile beta-2 cells show 4.2-fold depletion of WT regulatory state and marked accumulation of inferred *NEUROD1* and *HNF4A* loss states.

- **Panels 5g-h: Primary Islet siRNA Validation (RFX6 Knockdown)**
  - **Source File:** `pertTF.pdf` (Page 21), `pertTF-figures/Fig. 5_v4.pptx`
  - **Main/Supplementary:** Main Figure 5g-h
  - **Quantitative Result:** pertTF correctly classified 78.4% of primary islet cells with *RFX6* siRNA as perturbed (vs 4.1% in controls), Cosine Sim = 0.873.

---

### Figure 6: pertTF Enables In Silico Genetic Screens

- **Panel 6a: Dual In Silico Screening Pipelines (Method 1 vs Method 2)**
  - **Source File:** `pertTF.pdf` (Page 21), `pertTF-figures/Fig. 6_v7.pptx`
  - **Main/Supplementary:** Main Figure 6a
  - **Visual Encoding:** Method 1: Embedding cosine similarity; Method 2: Calibrated lochNESS regression.

- **Panels 6b-d: In Silico Pancreatic Progenitor (PP) Screen Validation**
  - **Source File:** `pertTF.pdf` (Page 21), `pertTF-figures/Fig. 6_v7.pptx`
  - **Main/Supplementary:** Main Figure 6b-d
  - **Validation Dataset:** Experimental pooled CRISPR screen sorting on PDX1-GFP (Wang et al.).
  - **Quantitative Result:** pertTF recovered known PP regulators (*GATA6*, *MAPK1*, *PROX1*); achieved **ROC-AUC = 0.79**, **AUPR = 0.74** vs Expression baseline **ROC-AUC = 0.66**, **AUPR = 0.52**.

- **Panels 6e-g: Essential Gene lochNESS Calibration**
  - **Source File:** `pertTF.pdf` (Page 21), `pertTF-figures/Fig. 6_v7.pptx`
  - **Main/Supplementary:** Main Figure 6e-g
  - **Result:** Unseen essential genes (*MRPS5*, *RPL*, *PSMD*) accurately predicted with strong negative lochNESS ($p < 10^{-15}$ vs non-essential).

- **Panels 6h-j: In Silico Perturb-seq Across Multi-Subunit Complexes**
  - **Source File:** `pertTF.pdf` (Page 21), `pertTF-figures/Fig. 6_v7.pptx`
  - **Main/Supplementary:** Main Figure 6h-j
  - **Result:** Unseen multi-protein subunits (*SMARCC1*/*SMARCD1*, *SALL4*/*TCF7L1*) co-clustered in embedding space; predicted DEGs matched true Perturb-seq with Pearson $r > 0.81$.

---

## PART 2: PRECURSOR MANUSCRIPT FIGURES (Liu et al., 2025)

### Figure 1: A Knockout Village of 79 hPSC Lines During Islet Differentiation
- **Panels 1a-c:** Library composition (30 genes, 79 clonal lines, MODY/T2D/epigenetic classes), village co-culture schematic with 70% unlabeled WT cells, and stacked lineage dynamics across Day 0, 3, 7, 11, 18.
- **Source File:** `pertTF-precussor.pdf` (Page 34), `pertTF-precussor-figures/Fig.1.pdf` & `clean_sources/precursor_figures_png/Fig.1-1.png`.

### Figure 2: Loss of Lineage Regulators Impairs Beta-Cell Formation and Beta-Cell State
- **Panels 2a-e:** Volcano plot of Day 18 SC-beta fraction across mutants, SC-beta cell yield quantification, and DEG volcano plots showing collapse of mature beta markers (*INS*, *MAFA*, *SLC30A8*) in *NEUROD1* and *HNF4A* knockouts.
- **Source File:** `pertTF-precussor.pdf` (Page 36), `pertTF-precussor-figures/Fig.2.pdf` & `clean_sources/precursor_figures_png/Fig.2-1.png`.

### Figure 3: Impaired Islet Differentiation is Accompanied by Increase of Alternative Lineages
- **Panels 3a-e:** Dot plot of 14 cell-type fractions across 30 genotypes. Uncovers *GATA6*(-/-) -> Endothelial diversion, *FOXA2*(-/-) -> Hepatic diversion, and *HHEX*(-/-) -> PGT arrest.
- **Source File:** `pertTF-precussor.pdf` (Page 38), `pertTF-precussor-figures/Fig.3.pdf` & `clean_sources/precursor_figures_png/Fig.3-1.png`.

### Figure 4: Loss of RFX6, PDX1, or PAX6 Increases SC-EC Cells at the Expense of SC-Beta Cells
- **Panels 4a-f:** Endocrine sub-lineage composition shifts. Proves that *RFX6*, *PDX1*, and *PAX6* loss drives stoichiometric expansion of serotonergic SC-EC cells (*SLC18A1*, *TPH1*) to >70% of endocrine cells while eliminating SC-beta.
- **Source File:** `pertTF-precussor.pdf` (Page 40), `pertTF-precussor-figures/Fig.4.pdf` & `clean_sources/precursor_figures_png/Fig.4-1.png`.

### Figure 5: SC-EC Cells Show Reduced Hormone Regulation and Enhanced Neuronal Signatures
- **Panels 5a-h:** cNMF gene programs and SCENIC+ regulons. Program h3 (neuronal/axonogenesis) and TFs (*MNX1*, *ZEB1*, *LMX1A*) govern SC-EC, whereas Program i5 (hormone regulation) and TFs (*PDX1*, *PAX6*, *ISL1*) govern SC-beta.
- **Source File:** `pertTF-precussor.pdf` (Page 42), `pertTF-precussor-figures/Fig.5.pdf` & `clean_sources/precursor_figures_png/Fig.5-1.png`.

### Figure 6: Mutant-Based Predictive Analyses Identify ISL1 as a Key Repressor of SC-EC Cells
- **Panels 6a-m:** Linear regression model identifying ISL1 as the top negative predictor of SC-EC/SC-beta ratio; experimental *ISL1*(-/-) knockout validation showing SC-EC expansion; and lentiviral *ISL1* overexpression rescue proving ISL1 is sufficient to repress SC-EC fate across all mutant backgrounds (*PDX1*, *PAX6*, *ISL1* KOs).
- **Source File:** `pertTF-precussor.pdf` (Page 44).
