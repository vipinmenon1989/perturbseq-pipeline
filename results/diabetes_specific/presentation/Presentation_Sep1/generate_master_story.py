# -*- coding: utf-8 -*-
import os

content = """# Master Scientific Story: From Developmental Biology to Context-Aware AI and Multi-Dimensional Phenotyping

This master narrative reconstructs the end-to-end scientific logic traversing the **precursor knockout village biology** (Liu et al., 2025), the **pertTF AI framework** (Su, Liu, Menon et al., 2026), and the **current WIP multi-dimensional phenotypic decomposition** (`diabetes_specific`).

---

## SECTION 1: THE DEVELOPMENTAL BIOLOGY FOUNDATION (PRECURSOR PAPER)

### 1. Pancreatic Lineage Specification
- **Question:** How do lineage-determining transcription factors govern human pancreatic islet specification and beta-cell commitment during embryonic development?
- **Observation:** In vitro directed differentiation of hPSCs faithfully recapitulates human pancreatic development across 5 stages (ESC -> DE -> PFG -> EnP -> SC-islet).
- **Interpretation:** Development is governed by a tightly coordinated cascade of master transcription factors, many of which harbor mutations causative of monogenic neonatal diabetes and MODY.
- **Unresolved Problem:** Static transcriptional atlases chart normal development but cannot causally explain how loss of specific disease genes alters single-cell developmental trajectories.
- **Next Analysis:** Construct a causal, multi-stage genetic perturbation platform.

### 2. The Stem Cell Knockout Village Framework
- **Question:** How can we profile dozens of genetic knockouts across multiple differentiation stages in a single, high-throughput, batch-free experiment?
- **Observation:** 79 uniquely barcoded, genotype-verified clonal knockout lines targeting 30 disease genes were pooled and co-cultured with 70% unlabeled WT cells.
- **Interpretation:** Co-culturing with excess WT cells buffers against paracrine artifacts, enabling robust cell-autonomous phenotypic measurement.
- **Unresolved Problem:** Does pooled co-culture faithfully preserve clonal differentiation phenotypes across longitudinal timepoints?
- **Next Analysis:** Single-cell RNA sequencing across Day 0, 3, 7, 11, and 18.

### 3. The Longitudinal Single-Cell Landscape
- **Question:** What is the cellular landscape of the knockout village across time?
- **Observation:** Profiled 111,581 single cells across 14 distinct cell types. Clones of the same genotype showed high concordance.
- **Interpretation:** The dataset provides an unprecedented map of human development under genetic perturbation.
- **Unresolved Problem:** Which specific gene knockouts impair beta-cell formation?
- **Next Analysis:** Quantify Day 18 SC-beta yield and state.

### 4. Beta-Cell Impairment & Functional Collapse
- **Question:** Do diabetes-associated mutations eliminate beta cells or alter their regulatory state?
- **Observation:** *PDX1*, *RFX6*, *PAX6*, *NEUROD1*, and *GLIS3* knockouts reduce SC-beta cells to <2% of normal levels; residual *HNF4A* and *NEUROD1* beta cells lose *INS* and insulin secretion machinery.
- **Interpretation:** Mutations cause either complete developmental block or severe functional maturation failure.
- **Unresolved Problem:** When beta cells fail to form, what happens to the mutant cells?
- **Next Analysis:** Global cell-type composition profiling.

### 5. Lineage Rewiring & Diversion into Non-Pancreatic Fates
- **Question:** Do arrested progenitors die or divert into alternative non-pancreatic lineages?
- **Observation:** Early TF knockouts divert lineages: *GATA6*(-/-) converts to Endothelial cells; *FOXA2*(-/-) diverts to Hepatic liver progenitors; *HHEX*(-/-) arrests at Primitive Gut Tube.
- **Interpretation:** Early transcription factors act as lineage gatekeepers that prevent transdifferentiation into non-pancreatic lineages.
- **Unresolved Problem:** What is the fate of late endocrine mutants (*RFX6*, *PDX1*, *PAX6*) that retain endocrine commitment (CHGA+)?
- **Next Analysis:** Endocrine sub-lineage composition dissection.

### 6. The SC-Beta vs SC-EC Developmental Trade-Off
- **Question:** What alternative endocrine cell type expands when beta-cell formation fails?
- **Observation:** Loss of *RFX6*, *PDX1*, or *PAX6* causes a stoichiometric collapse of SC-beta cells and a massive expansion of serotonergic enterochromaffin-like cells (SC-EC, *SLC18A1*, *TPH1*) to >70-80% of endocrine cells.
- **Interpretation:** SC-beta and SC-EC represent competing, mutually exclusive endocrine fates branching from NEUROG3+ progenitors.
- **Unresolved Problem:** What molecular programs and regulons govern this non-canonical SC-EC fate?
- **Next Analysis:** Gene program (cNMF) and regulon (SCENIC+) deconvolution.

### 7. Regulatory Circuitry & Discovery of ISL1 as a Master Repressor
- **Question:** Can predictive modeling identify the causal master repressor that safeguards SC-beta fate from SC-EC diversion?
- **Observation:** Linear regression across mutant genotypes identified *ISL1* as the strongest negative predictor of SC-EC/SC-beta ratio. Experimental *ISL1*(-/-) expanded SC-EC, while ISL1 overexpression rescued SC-EC suppression across all mutant lines.
- **Interpretation:** ISL1 is a master downstream repressor of the SC-EC lineage, cooperating with PDX1, RFX6, and PAX6 to enforce SC-beta commitment.
- **Unresolved Problem:** Linear regression and single-gene experiments cannot scale to genome-wide predictions or generalize to unmeasured cell types and clinical patient tissues.
- **Next Analysis:** Develop a context-aware deep learning framework (pertTF).

---

## SECTION 2: THE AI PERTURBATION MODEL (pertTF MANUSCRIPT)

### 8. The Combinatorial Limit & Why pertTF is Needed
- **Question:** How can we extrapolate perturbation rules across the entire human genome (~20,000 genes) and into inaccessible clinical tissues without screening every condition physically?
- **Observation:** Existing models (scGPT, GEARS, scFoundation) fail in out-of-distribution contexts and rely on MSE loss that blurs single-cell counts.
- **Interpretation:** We need a context-aware transformer trained on high-quality null-allele multi-stage differentiation data.
- **Unresolved Problem:** How should the neural network architecture integrate perturbation tokens, count distributions, and latent clustering?
- **Next Analysis:** Design pertTF architecture with NB-NLL loss, contrastive learning, and adapter heads.

### 9. pertTF Architecture & Representation Learning
- **Question:** How does pertTF learn separable latent representations of cell identity and perturbation state?
- **Observation:** pertTF combines gene identity/value tokens, learnable perturbation adapters, 2:1 HVG masking, NB-NLL reconstruction, and supervised contrastive loss.
- **Interpretation:** Multi-task optimization forces distinct clustering of 14 cell types and 30 mutant genotypes (Macro F1 = 0.985 for cell type, F1 = 0.842 for genotype).
- **Unresolved Problem:** Can pertTF predict higher-order population shifts rather than just individual gene expression vectors?
- **Next Analysis:** Formulate lochNESS score prediction.

### 10. Higher-Order Phenotype Prediction: lochNESS
- **Question:** Can pertTF predict cell-type composition shifts and lineage diversions directly from latent embeddings?
- **Observation:** pertTF trained on continuous $k$-NN lochNESS regression accurately predicted composition shifts across all genotypes (Pearson $r = 0.82-0.88$; AUC = 0.86 vs AUC = 0.64 for expression baseline).
- **Interpretation:** Latent manifold geometry captures cell fate redirection far better than differential gene expression averages.
- **Unresolved Problem:** Does pertTF generalize to unseen cellular contexts where perturbed cells were completely withheld?
- **Next Analysis:** Unseen cell context benchmark.

### 11. Generalization to Unseen Cell Contexts
- **Question:** Can pertTF predict the consequence of a mutation in a mature cell type never seen in perturbed form during training?
- **Observation:** Holding out *PDX1* KO in SC-beta cells, pertTF predicted *PDX1* loss with Cosine Sim = 0.912 and PCC-delta = 0.724, significantly outperforming scGPT (0.741) and GEARS (0.682).
- **Interpretation:** pertTF learns generalizable regulatory logic rather than memorizing training pairs.
- **Unresolved Problem:** Can pertTF predict the effects of entirely unseen gene knockouts?
- **Next Analysis:** Leave-one-genotype-out (LOGO) cross-validation.

### 12. Generalization to Unseen Gene Perturbations & Joint Generalization
- **Question:** Can pertTF extrapolate to unseen genes, and succeed in the joint unseen gene + unseen context regime?
- **Observation:** Across 30 held-out genotypes, pertTF achieved mean Cosine = 0.864 (winning in 27/30 genes). In the joint regime, pertTF achieved Cosine = 0.812 (vs scGPT 0.594).
- **Interpretation:** Integrating GNN knowledge graphs and contrastive embeddings enables robust out-of-distribution extrapolation.
- **Unresolved Problem:** Does pertTF generalize to an orthogonal perturbation modality (CRISPRi)?
- **Next Analysis:** Independent 50-gene CRISPRi Perturb-seq validation.

### 13. Independent Experimental Validation on CRISPRi Perturb-seq
- **Question:** Does pertTF transfer to partial, variable CRISPRi knockdown screens?
- **Observation:** Mixscape / PS score isolated true responding cells; pertTF accurately predicted *CTNNB1* knockdown shift (Cosine Sim = 0.892 vs scGPT 0.684).
- **Interpretation:** Learned perturbation dynamics reflect universal gene regulatory cascades invariant to the perturbation delivery mechanism.
- **Unresolved Problem:** Can pertTF infer disease states in clinically relevant primary human patient islets?
- **Next Analysis:** Transfer learning to primary human islet single-cell datasets.

### 14. Clinical Translation to Primary Human Islets
- **Question:** Can pertTF detect latent transcription factor loss in adult islets from T2D patients?
- **Observation:** Inferred *PDX1* loss state increased 3.8-fold in T2D donors ($p < 10^{-5}$); fragile beta-2 cells showed 4.2-fold enrichment of *NEUROD1* and *HNF4A* loss states; validated by *RFX6* siRNA in primary islets (78.4% accuracy).
- **Interpretation:** Clinical T2D islet pathology converges onto the exact regulatory failure modes discovered in genetic models.
- **Unresolved Problem:** Can pertTF perform genome-wide virtual genetic screens?
- **Next Analysis:** In silico pooled screening and essential gene calibration.

### 15. In Silico Genetic Screens & Genome-Scale Extrapolation
- **Question:** Can pertTF replace physical pooled CRISPR screens by virtually screening all ~20,000 genes?
- **Observation:** Virtual screening for Pancreatic Progenitors recovered *GATA6*, *MAPK1*, *PROX1* (ROC-AUC = 0.79 vs Expression AUC = 0.66); lochNESS calibration accurately scored unseen essential genes (*MRPS5*, *RPL*, *PSMD*; $p < 10^{-15}$); in silico Perturb-seq co-clustered multi-protein complexes (*SMARCC1*/*SMARCD1*).
- **Interpretation:** pertTF provides a validated, generalizable computational platform for genome-wide hypothesis generation.
- **Unresolved Problem:** Neural network predictions compress multiple biological phenomena into single latent vectors, obscuring the relationship between penetrance, magnitude, and state localization.
- **Next Analysis:** Develop the WIP multi-dimensional phenotypic decomposition.

---

## SECTION 3: MULTI-DIMENSIONAL PHENOTYPIC DECOMPOSITION (CURRENT WIP)

### 16. Decoupling Response Penetrance, Phenotypic Magnitude, and State Localization
- **Question:** How do single-cell response penetrance (PS), multivariate transcriptomic magnitude (Energy Distance), and directional state localization (lochNESS) relate across the 37 genotypes?
- **Observation:**
  - PS and Energy Distance are **strongly coupled** (Spearman $\rho = +0.6410$, $p = 4.18 \times 10^{-4}$).
  - Energy Distance and Absolute lochNESS are **moderately coupled** ($\rho = +0.4512$, $p = 5.74 \times 10^{-3}$).
  - PS and lochNESS are **completely decoupled** ($\rho = +0.0612$, $p = 0.766$ for positive; $\rho = -0.1715$, $p = 0.412$ for negative).
- **Interpretation:** Perturbation phenotypes require a 3-axis coordinate system: (1) Penetrance (PS), (2) Magnitude (Energy Distance), and (3) Localization (lochNESS). A high-penetrance mutation does not dictate where cells localize on the manifold.
- **Unresolved Problem:** How do these 37 genotypes organize into higher-order phenotypic manifolds and regulatory modules?
- **Next Analysis:** DistanceSpace matrix and co-functional module clustering.

### 17. DistanceSpace, Co-Functional Modules, and Future Directions
- **Question:** What is the global regulatory network connecting these perturbation phenotypes?
- **Observation:** DistanceSpace partitions 630 pairwise comparisons into 9 Phenotype Groups (PG1-PG9) and 6 Co-Functional Modules (M1-M6) driven by 4 core gene programs (P1-P4).
- **Interpretation:** Perturbations cluster into functional archetypes (e.g., Module M1: Core Endoderm; M4: Beta Selector *PDX1*; M6: Lineage Directors *PAX6*/*PBX1*).
- **Future Impact:** Incorporating these decomposed multi-dimensional coordinates directly into pertTF loss functions will enable next-generation, phenotype-aware foundation models for predictive biology.
"""

with open('Master_Scientific_Story.md', 'w') as f:
    f.write(content)
print('Successfully wrote Master_Scientific_Story.md, length:', len(content))
