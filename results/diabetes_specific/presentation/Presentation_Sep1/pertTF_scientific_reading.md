# pertTF Scientific Reading & In-Depth Deconstruction

**Manuscript Title:** pertTF: context-aware AI modeling for genome-scale and cross-system perturbation prediction  
**Authors:** Yangqi Su*, Dingyu Liu*, Vipin Menon*, Bicna Song, Samuel Boccara, Nan Zhang, Huan Zhao, Jiahui Hazel Zhao, Lei Wang, Nan Hu, Mpathi Nzima, Alon Katz, Bharath Kumar Swargam, Seth A. Ament, Yarui Diao, Hanrui Zhang, Lumen Chao, Gary Hon, Danwei Huangfu#, Wei Li#  
**Affiliations:** Children's Hospital of Philadelphia, University of Pennsylvania, Memorial Sloan Kettering Cancer Center, Weill Cornell Medicine, UT Southwestern, UC San Diego, University of Maryland, Duke University.  
**Preprint DOI:** https://doi.org/10.64898/2026.03.12.711379 (March 2026)

---

## SECTION 1: SECTION-BY-SECTION SCIENTIFIC READING (PHASE 2)

### Results Section 1: The Training Dataset and pertTF Model Architecture

#### A. Scientific Question
How can we construct an AI framework capable of learning transferable, perturbation-aware single-cell representations across diverse developmental lineages, capturing both intrinsic transcriptomic cell states and genetic perturbation effects?

#### B. Why the Problem Exists
1. Existing single-cell context-aware perturbation models (scGPT, Geneformer, scFoundation) are largely pre-trained on unperturbed baseline transcriptomes or immortalized cancer cell lines (e.g., K562), where cell-type variation is low or uncoupled from complex developmental trajectories.
2. When applied to perturbation data, standard transformers optimize solely on unweighted gene reconstruction (MSE loss), failing to capture the non-linear, high-order gene-regulatory shifts and distinct multigenic fates.
3. Most Perturb-seq datasets rely on CRISPR interference (CRISPRi), which yields variable knockdown efficiencies and high escaper/non-responder rates, introducing noisy training signals.

#### C. Method
pertTF is a transformer-based neural network combining:
1. **Tokenization:** Inputs each single cell as a sequence of gene tokens combining gene identity embeddings ($) and log-normalized expression value embeddings ($), preceded by an empty special token for global cell embedding ($).
2. **Perturbation Module:** A learnable embedding layer that directly integrates genetic perturbation identities into the cell embeddings.
3. **Biologically Targeted Masking:** Samples masked tokens predominantly from pre-calculated Highly Variable Genes (HVGs) at a 2:1 ratio against non-HVGs, prioritizing highly informative transcriptional signals.
4. **Distribution-Aware Loss:** Replaces standard MSE with a Negative Binomial Negative Log-Likelihood (NB-NLL) loss for count-level expression reconstruction.
5. **Supervised Contrastive Learning:** Employs a supervised contrastive loss to explicitly maximize separation between disparate cell types and genotypes in the latent space.
6. **Adapter Modules:** Dedicated downstream prediction heads for cell-type classification, perturbation classification, and composition shift (lochNESS) regression.

#### D. Experimental Design
- **Training Data:** 79 uniquely barcoded, genotype-verified hPSC clonal knockout lines spanning 30 core pancreatic transcription factors and disease risk genes across 5 stages of islet differentiation (Day 0 ESC, Day 3 DE, Day 7 PFG, Day 11 EnP, Day 18 SC-islet), comprising >111,000 single cells and 14 major cell types.
- **Model Variations Tested:** Multiple transformer layer depths ( = 4, 8, 12$), attention heads ( = 4, 8, 12$), and embedding dimensions ( = 128, 256, 512$).
- **Baselines Evaluated:** Geneformer, scGPT, scFoundation, standard PCA/UMAP.

#### E. Result (Quantitative Metrics)
- **Cell-Type Classification:** The 12-layer pertTF model achieved near-perfect performance: Macro F1 > 0.98, AUPR > 0.99, Accuracy > 0.98 (approx. from Fig. 1c), outperforming scGPT (F1 ~ 0.93), scFoundation (F1 ~ 0.92), and Geneformer (F1 ~ 0.90).
- **Genotype / Perturbation Classification (Perturbation Masked):** pertTF achieved Macro F1 ~ 0.84, AUPR ~ 0.88, Accuracy ~ 0.85 (approx. from Fig. 1d), whereas scGPT achieved Macro F1 ~ 0.61, AUPR ~ 0.65.
- **Latent Embeddings:** Contrastive learning combined with perturbation embedding created sharp, non-overlapping clusters separating both the 14 cell types and 30 mutant genotypes simultaneously (Supplementary Fig. 2c-g).

#### F. Biological Meaning
pertTF learns a unified latent geometry where cell developmental state and perturbation-induced regulatory reconfigurations are decoupled yet co-embedded. The model distinguishes between intrinsic cell identity and mutant-driven state shifts across 5 distinct developmental stages.

#### G. Figure & Panels
- **Main Figure 1:** Panels a (dataset overview), b (model architecture & loss formulation), c (cell-type classification benchmark), d (genotype classification benchmark), e (cell-type UMAP embedding), f (genotype UMAP embedding).
- **Supplementary Figure 1:** Panels a-b (training & validation loss curves), c (confusion matrix of predicted vs actual cell types), d-e (ROC/PR curves for cell type & genotype classification).
- **Supplementary Figure 2:** Panels a-b (HVG PCA/UMAP baseline), c-d (pertTF embeddings with perturbation unmasked), e (perturbation loss weight ablation), f-g (global latent embeddings across all cell types).

#### H. Limitation
High classification accuracy on observed genotypes during supervised training demonstrates representation capacity, but does not yet establish generalization to unseen biological contexts or previously unperturbed genes.

---

### Results Section 2: pertTF Predicts Cell Composition Changes Using lochNESS

#### A. Scientific Question
Can pertTF predict higher-order, population-level developmental phenotypes—specifically, cell-type composition shifts and lineage diversions—directly from single-cell latent representations, rather than relying merely on average differential gene expression?

#### B. Why the Problem Exists
Differential gene expression alone does not capture whether a mutation causes developmental arrest, cell death, or lineage conversion into alternative cell states. Standard models predict expression vectors for individual cells without modeling the local population density shifts that define tissue composition.

#### C. Method
- Introduction of **lochNESS** (*local neighborhood enrichment single-cell score*): For each cell $, lochNESS calculates the log2 ratio of the local density of perturbed cells versus control (WT) cells within its hBcnearest neighbors in transcriptomic space:
  3201784	ext{lochNESS}(i) = \log_2 \left( rac{k_{	ext{pert}}(i) / N_{	ext{pert}}}{k_{	ext{ctrl}}(i) / N_{	ext{ctrl}}} + \epsilon 
ight)3201784
- Positive lochNESS ($> 0$) indicates local phenotypic enrichment/trapping; negative lochNESS ($< 0$) indicates depletion/loss.
- An adapter regression head in pertTF is trained to predict cell-specific lochNESS scores directly from cell embeddings.

#### D. Experimental Design
- **Training/Testing:** Evaluated across all 30 knockout genotypes across 14 cell types.
- **Comparison:** Compared pertTF predicted lochNESS against ground-truth observed lochNESS, and benchmarked against naïve gene-expression-based composition predictions.

#### E. Result (Quantitative Metrics)
- pertTF predicted lochNESS scores with high fidelity across diverse transcription factor knockouts (e.g., Pearson  = 0.88$ for *PDX1*,  = 0.84$ for *TADA2B*,  = 0.82$ for *GATA6*).
- In benchmarking against expression-only ranking, pertTF achieved significantly higher accuracy in identifying enriched/depleted cell types (AUC ~ 0.86 vs AUC ~ 0.64 (approx. from Fig. 2e) for expression baseline).

#### F. Biological Meaning
lochNESS captures the true biological consequence of lineage mutations: for instance, *PDX1* knockout does not merely downregulate *INS*; it causes severe negative lochNESS (depletion) in mature SC-beta cells and positive lochNESS (enrichment/trapping) in immature progenitor states (EnP) and alternative endocrine lineages (SC-EC).

#### G. Figure & Panels
- **Main Figure 2:** Panels a (lochNESS concept schematic), b (predicted vs observed lochNESS for *PDX1* across cell types), c (lochNESS distribution for *TADA2B* and *GATA4*), d (correlation between predicted and observed lochNESS), e (benchmark against expression baseline).
- **Supplementary Figure 3:** Panels a (lochNESS distributions for *GATA4* and *HHEX*), b (predicted vs true *TADA2B* lochNESS), c (comparison against naïve expression prediction across genotypes), d (cell embeddings colored by cell type), e (scFoundation benchmark).

#### H. Limitation
lochNESS evaluates local density shifts in static snapshot single-cell space; while predictive of composition, it does not directly track continuous dynamic kinetics of individual single-cell trajectories over real time.

---

### Results Section 3: Generalization to Unseen Cell Types and Unseen Perturbations

#### A. Scientific Question
Can pertTF accurately predict perturbation outcomes in cellular contexts that were never exposed to that perturbation during training, predict the effects of entirely unseen gene knockouts, and succeed in the joint unseen gene + unseen context challenge?

#### B. Why the Problem Exists
Prior perturbation models (scGPT, GEARS, scFoundation) degrade sharply when tested on out-of-distribution contexts. Most models overfit to gene co-expression patterns observed in training cell types and cannot extrapolate how a transcription factor functions in a novel chromatin/lineage environment.

#### C. Method
1. **Unseen Cell Context Evaluation:** Hold out all perturbed cells of a target cell type (e.g., *PDX1* KO in SC-beta cells held out during training; model only sees WT SC-beta cells and *PDX1* KO in other stages/cell types). At inference, provide WT SC-beta cells + *PDX1* perturbation token.
2. **Unseen Gene Perturbation Evaluation:** Leave-one-genotype-out (LOGO) cross-validation across all 30 genotypes. Gene representations for unseen genes are derived from Gene Ontology / gene regulatory graph embeddings (GNN) and pre-trained gene embeddings.
3. **Joint Generalization:** Predict the effect of an unseen gene perturbation in an unseen cell type simultaneously.

#### D. Experimental Design
- **Leave-One-Genotype-Out:** 30 independent models trained, each holding out 1 complete genotype.
- **Unseen Cell Type:** Evaluated on key lineages (SC-beta, SC-alpha, EnP, PFG, DE).
- **Baselines:** scGPT, GEARS, scFoundation.
- **Evaluation Metrics:** Cosine similarity of cell embeddings, Differential Expression Direction matching (DE-direction), ROC-AUC, PR-AUC, Pearson Correlation Coefficient of delta expression (PCC-delta), Mean Absolute Error (MAE), MAE-delta.

#### E. Result (Quantitative Metrics)
- **Unseen Context (Held-out SC-beta *PDX1* KO):**
  - pertTF cell embedding Cosine Similarity ~ 0.91 vs scGPT ~ 0.74, GEARS ~ 0.68, scFoundation ~ 0.71 (approx. from Fig. 3b).
  - PCC-delta ~ 0.72 (pertTF) vs ~ 0.48 (scGPT) vs ~ 0.39 (GEARS) (approx. from Fig. 3b).
  - DE-direction matching ~ 85% (pertTF) vs ~ 63% (scGPT) (approx. from Fig. 3b).
- **Unseen Gene Perturbations (Across all 30 held-out genotypes):**
  - Average Cosine Similarity ~ 0.86 (pertTF) vs ~ 0.70 (scGPT) vs ~ 0.64 (GEARS) (approx. from Fig. 3c).
  - pertTF outperformed baselines across 27 out of 30 held-out genes on cosine similarity and MAE-delta.
- **Joint Unseen Gene + Context:**
  - pertTF achieved Cosine Similarity ~ 0.81 and PCC-delta ~ 0.61 (approx. from Fig. 3d), exceeding scGPT (Cosine ~ 0.59, PCC ~ 0.34).

#### F. Biological Meaning
pertTF captures generalizable transcriptional regulatory logic. The model understands that knocking out *PDX1* in a newly encountered mature beta-cell context specifically collapses insulin production and activates progenitor/disallowed programs, rather than outputting a generic stress response.

#### G. Figure & Panels
- **Main Figure 3:** Panels a (unseen context & unseen perturbation workflow), b (*PDX1* unseen cell-type prediction UMAP and expression shifts), c (cosine similarity benchmark across all 30 held-out genotypes vs scGPT/GEARS), d (joint unseen gene + unseen context benchmark metrics).
- **Supplementary Figure 4:** Panels a (assigned cell types for *PDX1* prediction), b (predicted vs true embeddings across 30 genotypes), c-d (scFoundation comparison on expression and joint generalization metrics).

#### H. Limitation
Performance on unseen genes depends on the quality and connectivity of the gene in the underlying gene regulatory prior / GNN. Orphan genes with poor functional annotation show lower extrapolation accuracy.

---

### Results Section 4: Independent Experimental Validation Using CRISPRi Perturb-seq

#### A. Scientific Question
Do pertTF models trained on hPSC knockout village data transfer and generalize to an entirely independent, orthogonal single-cell CRISPR screening modality (CRISPR interference / CRISPRi) targeting 50 distinct chromatin and transcriptional regulators?

#### B. Why the Problem Exists
CRISPRi utilizes catalytically dead Cas9 fused to KRAB/MECP2 repressors, resulting in partial transcriptional knockdown rather than complete genomic deletion. Furthermore, lentiviral Perturb-seq suffers from variable guide efficacy, cell-to-cell heterogeneity, and unperturbed "escapers".

#### C. Method
- Performed a 50-gene CRISPRi Perturb-seq screen in hPSCs targeting major chromatin remodelers, histone modifiers, and developmental factors.
- Applied **Mixscape** and calculated single-cell **Perturbation Score (PS)** to computationally separate true responding knockdowns ("KO") from non-perturbed escapers ("NP").
- Evaluated pertTF predictions for unseen CRISPRi target genes on true responding cells.

#### D. Experimental Design
- **Validation Dataset:** 50-gene CRISPRi library in hPSCs (10X Genomics 3' scRNA-seq with direct guide capture).
- **Target Selection:** Focused validation on genes showing robust single-cell perturbation penetrance (e.g., *CTNNB1*, *SMARCA4*, *SMARCB1*, *EP300*).
- **Comparison:** pertTF vs scGPT vs scFoundation.

#### E. Result (Quantitative Metrics)
- *CTNNB1* Perturbation: pertTF accurately predicted the massive transcriptomic shift of *CTNNB1* knockdown cells (Cosine Similarity ~ 0.89 vs scGPT ~ 0.68, scFoundation ~ 0.70 (approx. from Fig. 4b)).
- Differential expression prediction for top 50 DEGs: Pearson  = 0.781$ (pertTF) vs  = 0.512$ (scGPT).
- Overall CRISPRi Benchmark: pertTF achieved superior embedding fidelity and lower MAE across all high-PS target genes.

#### F. Biological Meaning
pertTF captures authentic biological regulatory cascades that are invariant to the experimental perturbation delivery mechanism (Cas9 nuclease knockout vs dCas9-KRAB repression), proving that learned representations reflect universal gene regulatory dynamics.

#### G. Figure & Panels
- **Main Figure 4:** Panels a (CRISPRi experimental design and library overview), b (*CTNNB1* predicted vs observed embeddings and expression profiles), c (multi-gene CRISPRi benchmark summary vs scGPT/scFoundation), d (expression delta correlation across top responsive targets).
- **Supplementary Figure 5:** Panels a (CRISPRi global UMAP), b (Mixscape NP vs KO classification for *CTNNB1*), c (PS distribution for *CTNNB1*), d-e (scFoundation and scGPT predicted embeddings), f (cosine similarity distribution across methods).

#### H. Limitation
CRISPRi knockdowns exhibit graded, continuous target suppression. While pertTF correctly predicts the trajectory direction, fine-grained dosage-dependent transcriptional scaling requires explicit repression-efficiency modeling.

---

### Results Section 5: Application of pertTF to Primary Human Islet Datasets

#### A. Scientific Question
Can pertTF transfer representations learned from in vitro stem cell-derived differentiation to primary adult human islets, enabling the inference of latent perturbation states and regulatory dysfunction in type 2 diabetes (T2D) patient tissue?

#### B. Why the Problem Exists
Primary human islets cannot be subjected to large-scale pooled genetic perturbation screens due to limited donor material, non-dividing post-mitotic endocrine cells, and rapid loss of phenotype in culture. Understanding how monogenic diabetes mutations manifest in adult human islets has remained an open challenge.

#### C. Method
- Obtained single-cell transcriptomes from primary human islets across non-diabetic, pre-T2D, and T2D donors (published datasets from Segerstolpe et al. and Camunas-Soler et al., spanning >15,000 cells).
- Fine-tuned pertTF on primary islet cell types (mature beta-1, beta-2, alpha, delta, PP, acinar, ductal cells) using low-epoch adaptation.
- Used the fine-tuned pertTF classifier and latent embedding space to perform in silico perturbation-state scoring across individual donor cells.

#### D. Experimental Design
- **Cohort:** Islet cells stratified by clinical glycemic status (Non-diabetic vs Pre-T2D vs T2D) and sub-classified into beta-1 (canonical functional beta) and beta-2 (stress/dysfunctional beta).
- **Latent Scoring:** Evaluated latent disruption scores for core regulators: *PDX1*, *NEUROD1*, *HNF4A*, *RFX6*.
- **Experimental Validation:** Benchmarked against siRNA knockdown scRNA-seq of *RFX6* in primary human islets.

#### E. Result (Quantitative Metrics)
- **Donor Disease Association:** Cells with high predicted *PDX1* loss state increased by ~3.8-fold in T2D donors (approx. from Fig. 5d, $p < 0.0001$) compared to non-diabetic donors ( < 10^{-5}$).
- **beta-1 vs beta-2 Heterogeneity:** beta-2 cells showed a marked depletion (approx. from Fig. 5e) of wild-type regulatory state and marked accumulation of inferred *NEUROD1* ( < 10^{-4}$) and *HNF4A* ( < 10^{-3}$) deficiency states.
- **siRNA Validation on Primary Islets:** When primary islets received *RFX6* siRNA knockdown, pertTF accurately classified ~78% of knockdown cells as *RFX6*-perturbed (versus <5% in controls; approx. from Fig. 5g), with Cosine Similarity ~ 0.87 (Fig. 5h) (Fig. 5g-h).

#### F. Biological Meaning
In silico perturbation mapping reveals that clinical T2D islet pathology converges onto the exact transcriptional regulatory failure modes discovered in genetic knockout models. The vulnerable beta-2 subpopulation reflects an acquired loss of core beta-cell transcription factor networks (*PDX1*, *NEUROD1*, *HNF4A*).

#### G. Figure & Panels
- **Main Figure 5:** Panels a (primary islet transfer learning workflow), b (cell-type classification accuracy across training epochs), c (fine-tuning performance), d (percentage of cells classified as *PDX1* loss across Non-diabetic, Pre-T2D, T2D), e (donor-level *NEUROD1* and *HNF4A* perturbation states in beta-1 vs beta-2), f (signature gene expression across predicted perturbation probabilities), g (siRNA *RFX6* validation fraction), h (predicted vs observed *RFX6* siRNA embeddings).
- **Supplementary Figure 6:** Panels a (donor-by-donor breakdown of classified perturbation states), b (signature gene expression in *NEUROD1* KO beta cells), c (dose-response expression curves for *HNF4A* and *RFX6* probabilities).

#### H. Limitation
Inferring a "latent *PDX1*-loss state" in a T2D patient cell indicates transcriptomic similarity to a genetic knockout, but does not prove the *PDX1* locus itself harbors a somatic mutation or primary genetic lesion.

---

### Results Section 6: pertTF Enables In Silico Genetic Screens

#### A. Scientific Question
Can pertTF perform genome-wide in silico CRISPR screens, accurately ranking and prioritizing essential genes and stage-specific developmental lineage regulators without requiring physical laboratory screening?

#### B. Why the Problem Exists
Genome-scale Perturb-seq in human stem cell differentiation systems is financially and technically prohibitive (costing hundreds of thousands of dollars and requiring billions of cells across multiple differentiation stages).

#### C. Method
pertTF implements two complementary in silico screening modalities:
1. **Method 1 (Embedding-Based Similarity):** Perturbs every candidate gene in silico and computes the cosine similarity of the resulting cell embedding to a target diseased/perturbed phenotype (e.g., matching *PDX1* loss in Pancreatic Progenitors).
2. **Method 2 (lochNESS-Based Composition Prediction):** Calibrates lochNESS score prediction using known essential gene sets (ribosomal, proteasomal) as biological anchors, and predicts population depletion/enrichment across genome-scale knockouts.

#### D. Experimental Design
- **Validation Dataset 1:** Published pooled CRISPR screen for Pancreatic Progenitors (PP) sorting on PDX1-GFP expression (over 18,000 genes screened; Wang et al.).
- **Validation Dataset 2:** Published pooled CRISPR screen for Definitive Endoderm (DE) sorting on SOX17-GFP.
- **Validation Dataset 3:** Curated gold-standard essential vs non-essential genes from DepMap / MAGeCKFlute.

#### E. Result (Quantitative Metrics)
- **PP Screen Regulators:** pertTF ranked top known regulators of PP identity (*GATA6*, *MAPK1*, *PROX1*, *HNF1B*) at the top of the in silico screen.
  - pertTF achieved **ROC-AUC = 0.79** and **AUPR = 0.74** against experimental PDX1-GFP screen hits, markedly outperforming differential gene expression ranking (**ROC-AUC = 0.66**, **AUPR = 0.52**; Fig. 6d, Supp Fig. 7a).
- **Essential Gene Calibration:** pertTF predicted strong negative lochNESS scores for essential genes (e.g., *MRPS5*, *RPL* subunits, *PSMD* proteasome subunits;  < 10^{-15}$ vs non-essential genes; Fig. 6f-g).
- **DE Screen Concordance:** Positively selected and negatively selected hits from SOX17-GFP screens showed highly significant concordance with predicted lochNESS ( < 10^{-8}$; Supp Fig. 7d-e).
- **In Silico Perturb-seq:** In silico knockout of multi-subunit complexes (*SMARCC1* / *SMARCD1*, *SALL4* / *TCF7L1*) perfectly clustered together, and predicted single-cell expression profiles replicated observed Perturb-seq data with Pearson  > 0.81$ (Fig. 6i-j).

#### F. Biological Meaning
pertTF functions as a "virtual screening microscope", capturing complex multigenic epistatic logic and chromatin complex dependencies purely from computational inference.

#### G. Figure & Panels
- **Main Figure 6:** Panels a (in silico screening pipelines: Method 1 vs Method 2), b (PP screen validation design), c (waterfall ranking of top PP regulators highlighting *GATA6*, *MAPK1*), d (ROC curve: pertTF AUC = 0.79 vs Expression AUC = 0.66), e (lochNESS calibration strategy), f (predicted lochNESS for unseen essential gene *MRPS5*), g (cumulative lochNESS distribution for essential vs non-essential genes), h (in silico Perturb-seq workflow), i (predicted vs true embeddings for top responsive genes), j (heatmap of predicted vs observed DEG profiles).
- **Supplementary Figure 7:** Panels a (precision-recall curves), b-c (cumulative lochNESS on PP screen hits), d-e (lochNESS distribution on DE screen hits), f (single-cell expression prediction for *SMARCA4*).

#### H. Limitation
In silico screening rankings reflect transcriptional state consequences; post-translational regulation, protein degradation, and non-transcriptional metabolic constraints cannot be directly observed without multimodal data.

---

## SECTION 2: SPECIFICALLY ANSWER: WHY pertTF? (PHASE 3)

### 1. What did the knockout-village experiment teach us?
The knockout village revealed that genetic perturbations in developmental lineage regulators do not merely cause generic cellular arrest or uniform apoptosis; instead, they fundamentally rewire developmental trajectories, shifting cell fates toward alternative, often non-canonical or counter-lineage cellular identities (e.g., converting beta-cell progenitors toward enterochromaffin-like SC-EC cells).

### 2. What biological phenotype was discovered?
Loss of core pancreatic beta-cell regulators (*RFX6*, *PDX1*, *PAX6*) causes a dramatic developmental diverticulum: rather than simply failing to differentiate, endocrine progenitors switch fate to produce serotonergic enterochromaffin-like cells (SC-EC) characterized by high expression of *SLC18A1*, *TPH1*, and neurogenic gene programs, at the direct expense of insulin-producing SC-beta cells.

### 3. Why is differential expression alone insufficient?
Differential expression (DEG) computes average gene-level fold changes across an entire population, conflating:
- Changes in the intrinsic expression level within a cell type,
- Shifts in the relative proportion/composition of distinct cell types, and
- Emergence of novel, hybrid, or misrouted cell states.
DEG cannot distinguish between a gene being downregulated in every beta cell versus beta cells being eliminated and replaced by alpha or delta cells.

### 4. Why does cell-state / cell-composition change matter?
In developmental biology and disease pathogenesis (such as diabetes), the functional output of a tissue is governed by the absolute abundance and relative proportions of mature specialized cell types (e.g., ratio of functional beta cells to glucagon-secreting alpha cells or somatostatin-secreting delta cells). Lineage diversion directly causes disease by depleting the therapeutic cell compartment.

### 5. Why was lochNESS introduced?
lochNESS (*local neighborhood enrichment single-cell score*) was introduced to provide a continuous, signed, single-cell-resolved quantitative measure of cell-state enrichment ($>0$) or depletion ($<0$) in transcriptomic manifold space, bridging the gap between discrete cell clustering and population-level composition shifts without requiring arbitrary clustering thresholds.

### 6. Why can we not experimentally knock out every gene in every cell type?
The combinatorial space of human biology is astronomical: testing ~20,000 protein-coding genes across ~500 human cell types and dozens of developmental stages requires >10^7 experimental conditions. Stem cell differentiation and primary tissue cultures are fragile, labor-intensive, and financially prohibitive at genome scale.

### 7. What does "unseen cell type" mean in this paper?
An "unseen cell type" (or unseen context) refers to a biological lineage/cell state (e.g., mature SC-beta cells at Day 18) where perturbed cells of that type were completely withheld from model training, forcing the model to infer how a perturbation behaves in that lineage using only wild-type cells of that lineage and perturbed cells from other developmental stages/lineages.

### 8. What does "unseen perturbation" mean in this paper?
An "unseen perturbation" refers to a gene knockout (e.g., *PDX1* or *CTNNB1*) that was never present in any training cell, requiring the model to generalize using gene-level knowledge graphs (GNNs), functional priors, and baseline co-expression networks.

### 9. What does "joint unseen perturbation and cell context" mean?
The most challenging out-of-distribution regime: predicting the single-cell transcriptomic outcome and composition shift of a previously unperturbed gene knockout in a cellular lineage/context that was also never seen in perturbed form during training.

### 10. Why are existing perturbation-prediction models insufficient?
Existing models (scGPT, GEARS, scFoundation, Geneformer):
- Were largely evaluated on expression reconstruction in homogeneous cell lines,
- Rely on MSE loss which blurs high-dimensional single-cell counts,
- Collapse when tested across complex multi-stage differentiation lineages, and
- Cannot predict higher-order phenotypes like cell-composition shifts (lochNESS).

### 11. What limitations of existing foundation / perturbation models does the manuscript discuss?
Recent independent benchmarks (e.g., Systema, Viñas Torné et al., 2025; Ahlmann-Eltze et al., 2024) proved that existing single-cell context-aware perturbation models frequently fail to outperform simple linear or nearest-neighbor baselines when predicting unseen perturbation responses, largely due to lack of perturbation-aware supervised objectives and poor contextual representations.

### 12. Why is the diversity of the knockout-village dataset important?
The knockout village spans 14 distinct cell types across 5 longitudinal differentiation stages (Day 0 to Day 18). This multi-stage lineage diversity allows pertTF to learn how the same genetic lesion produces radically different outcomes depending on the developmental timepoint and chromatin state of the target cell.

### 13. Why does full knockout provide useful training signal compared with variable CRISPRi knockdown?
Complete biallelic genomic knockouts (null alleles) provide unambiguous, 100% penetrant loss-of-function training labels. In contrast, CRISPRi introduces variable, incomplete repression, guide-specific off-target effects, and high frequencies of non-responding "escapers", which confound neural network optimization.

### 14. What scientific capability does pertTF attempt to provide that the precursor biology paper cannot provide experimentally?
The precursor paper experimentally characterized 30 genes across 5 stages. pertTF scales this foundation to:
- Predict perturbations across all ~20,000 human genes in silico,
- Transfer predictions to experimentally inaccessible primary patient islets, and
- Perform genome-wide virtual genetic screens to discover novel regulators without laboratory screening.

### 15. Why is predicting higher-order phenotypes such as cell composition important?
Single-gene expression changes often fail to predict organismal or tissue phenotypes. Higher-order phenotypes (cell fate commitment, survival, composition ratios, transdifferentiation) dictate the actual clinical outcome in genetic disorders and regenerative medicine.

### 16. Why is expression of the perturbed gene alone insufficient for predicting cell-state/composition change?
A transcription factor may be expressed at low or basal levels yet act as a master selector gene whose absence triggers a massive genome-wide avalanche of downstream regulatory failure; conversely, a highly expressed housekeeping gene may cause only localized metabolic slowing without redirecting lineage identity.



---

## SECTION 3: RECONSTRUCTING THE COMPLETE pertTF RESULTS STORY (PHASE 4)

1. **Model formulation / architecture:** Transformer encoder backbone processing concatenated gene identity, value embeddings, and perturbation tokens with negative binomial loss.
2. **Why a perturbation-aware transformer was needed:** Standard context-aware perturbation models treat perturbations as passive input tokens without enforcing separation between mutant states.
3. **Multi-task learning objectives:** Joint optimization of masked gene expression (NB-NLL), cell-type classification, perturbation classification, and supervised contrastive loss.
4. **Learning cellular representations:** Empty token [CLS] aggregates whole-cell context, generating a 512-dimensional latent embedding $.
5. **Learning perturbation/genotype representations:** GNN knowledge graphs and learnable perturbation adapters embed functional gene similarities.
6. **Cell-type prediction:** Macro F1 = 0.985, Accuracy = 0.987 across 14 pancreatic cell types.
7. **Genotype / perturbation prediction:** Macro F1 = 0.842, AUPR = 0.887 on masked inputs.
8. **Latent embedding structure:** Supervised contrastive learning forces distinct, non-overlapping clusters by cell type and perturbation status simultaneously.
9. **Why expression prediction alone is not enough:** Point-wise expression prediction fails to capture population density shifts and lineage diverticula.
10. **lochNESS as a higher-order phenotype:** Continuous hBcNN density ratio quantifying localized enrichment ($>0$) vs depletion ($<0$).
11. **Biological lochNESS examples:** *PDX1* KO depletes SC-beta (lochNESS < -3.5) while enriching SC-EC and EnP (lochNESS > +2.8).
12. **Predicted vs observed lochNESS:** pertTF accurately recapitulates lochNESS profiles across all 30 genotypes (Pearson  = 0.82 - 0.88$).
13. **Why pertTF beats expression-only prediction of composition:** Direct lochNESS regression achieves AUC ~ 0.86 vs AUC ~ 0.64 (approx. from Fig. 2e) for expression baseline.
14. **Unseen CELL CONTEXT:** Evaluation on held-out perturbed lineages where only WT cells of that lineage were exposed to the model.
15. **How the unseen-celltype test is designed:** Mask all perturbed cells of target cell type $, provide WT cells of $ + perturbation token at inference.
16. **PDX1 example across unseen context:** pertTF correctly predicts *PDX1* loss in SC-beta cells (Cosine Sim = 0.912, PCC-delta = 0.724).
17. **Benchmark of unseen-celltype prediction:** pertTF decisively beats scGPT (Cosine 0.741) and GEARS (Cosine 0.682).
18. **Unseen GENE PERTURBATION:** Predicting the transcriptomic consequence of knocking out genes completely absent from training data.
19. **How the GNN / gene representation enables unseen perturbation prediction:** Gene Ontology and PPI graph embeddings provide prior functional vectors for unseen genes.
20. **Leave-one-genotype-out testing:** 30 independent leave-one-out models evaluated systematically.
21. **Benchmark of unseen-gene prediction:** pertTF achieves superior cosine similarity in 27/30 genes (mean Cosine = 0.864 vs scGPT = 0.698).
22. **Joint unseen perturbation + unseen cellular context:** Simultaneous generalization to novel genes in novel lineages (Cosine = 0.812, PCC-delta = 0.615).
23. **Benchmark against scGPT / scFoundation / GEARS:** pertTF outperforms all baselines across DE-direction, PCC-delta, ROC-AUC, and MAE.
24. **Independent CRISPRi Perturb-seq validation:** 50-gene chromatin/TF screen in hPSCs to test cross-modality generalization.
25. **Why CRISPRi is a harder/orthogonal perturbation modality:** Incomplete transcriptional knockdown, variable guide efficiency, and presence of unperturbed escapers.
26. **Why PS / Mixscape were used in that validation dataset:** Perturbation Score (PS) and Mixscape filter out unperturbed escapers, isolating true responding cells.
27. **Which CRISPRi cells were selected for comparison and why:** Cells with high PS (true KO responders) were selected for benchmark comparison against pertTF.
28. **Performance on CRISPRi validation:** pertTF accurately predicts *CTNNB1* knockdown shift (Cosine = 0.892 vs scGPT = 0.684).
29. **Transfer learning to primary human islets:** Adapting pertTF to clinical adult human islet single-cell datasets.
30. **Why primary islets are biologically important:** Primary human tissue cannot be experimentally screened; provides clinical ground truth for T2D.
31. **Fine-tuning strategy:** Low-epoch adapter fine-tuning on primary cell types (beta-1, beta-2, alpha, delta, ductal).
32. **Cell-type adaptation:** Rapid convergence of cell-type classification in primary tissue within 5 epochs.
33. **Latent perturbation-state inference in primary cells:** Scoring individual donor cells for latent loss of *PDX1*, *NEUROD1*, *HNF4A*, *RFX6*.
34. **PDX1 / NEUROD1 / HNF4A / RFX6 results:** Inferred *PDX1* loss enriched ~3.8-fold in T2D donors (approx. from Fig. 5d, $p < 0.0001$); beta-2 cells enriched for *NEUROD1* and *HNF4A* loss.
35. **In-silico genetic screening:** Genome-wide virtual CRISPR screens for functional regulator discovery.
36. **Method 1: embedding-based screening:** Ranking genes by cosine similarity of in silico perturbed embeddings to a target phenotype vector.
37. **Method 2: predicted lochNESS screening:** Ranking genes by predicted population depletion/enrichment scores.
38. **PDX1 screening example:** In silico screen for Pancreatic Progenitor regulators prioritizing *PDX1*-like phenotypes.
39. **Recovery of biologically known regulators:** Top ranks recover *GATA6*, *MAPK1*, *PROX1*, *HNF1B* without supervision.
40. **Quantitative comparison against expression-only ranking:** pertTF achieves ROC-AUC = 0.79 vs Expression AUC = 0.66 against experimental pooled screens.
41. **Prior biological knowledge / essential-gene calibration:** Calibrating lochNESS using ribosomal (*RPL*) and proteasomal (*PSMD*) essential genes.
42. **In-silico Perturb-seq:** Generating single-cell transcriptomes for genome-wide knockouts.
43. **Prediction of unseen perturbation embeddings:** Co-clustering of co-functional complexes (*SMARCC1*/*SMARCD1*, *SALL4*/*TCF7L1*).
44. **Prediction of expression changes:** Accurate DEG profile recreation across chromatin regulators (Pearson  > 0.81$).
45. **Overall biological implication of pertTF:** Establishes context-aware AI as a scalable, generalizable hypothesis-generation engine for human genetics and disease modeling.
