# -*- coding: utf-8 -*-
import os

content = """# Precursor Manuscript Scientific Reading & Biological Deconstruction

**Manuscript Title:** A stem cell knockout village reveals lineage rewiring and a non-canonical islet cell fate in monogenic diabetes  
**Authors:** Dingyu Liu, Bicna Song#, Zhaoheng Li#, Stephen Zhang#, Tabassum Fabiha, Jiahui Zhao, Ayaka Inoki, Julie Piccand, Chew-Li Soh, Gary Dixon, Aaron Zhong, Nan Hu, Renhe Luo, Batu Ozlusen, Vipin Menon, Ting Zhou, Xiaojie Qiu, Gerard Karsenty, Danwei Huangfu  
**Preprint DOI:** https://doi.org/10.64898/2025.12.23.696311 (December 2025)

---

## SECTION 1: FIGURE-BY-FIGURE SCIENTIFIC DECONSTRUCTION (PHASE 5)

### Figure 1: A Knockout Village of 79 hPSC Lines During Islet Differentiation

#### 1. Scientific Question
Can we systematically and causally map how loss of key lineage regulators and monogenic diabetes genes alters single-cell developmental trajectories across human pancreatic differentiation in a pooled, competitive format?

#### 2. Experimental Design & Comparison
- **Library Design:** 79 uniquely barcoded, genotype-verified clonal human pluripotent stem cell (hPSC) lines targeting 30 disease-relevant genes (15 monogenic diabetes genes, 11 chromatin/epigenetic regulators, and developmental TFs).
- **Pooling & Co-culture:** Clones were stably tagged with lentiviral lineage-tracing barcodes (LARRY GFP-barcode library) and pooled at equal ratios (the "knockout village").
- **Competition Assay:** Co-cultured with excess unlabeled wild-type (WT) cells (30% village : 70% WT) to buffer against non-cell-autonomous paracrine artifacts.
- **Longitudinal Sampling:** Isolated by FACS (GFP+) and profiled by scRNA-seq across 5 differentiation stages: Day 0 (ESC), Day 3 (Definitive Endoderm, DE), Day 7 (Posterior Foregut, PFG / Pancreatic Progenitor 1, PP1), Day 11 (Endocrine Progenitor, EnP / PP2), and Day 18 (Stem Cell-derived Islet, SC-islet).

#### 3. Result
- Generated 111,581 high-quality single-cell transcriptomes spanning 14 distinct cell types.
- Clonal lines from the same genotype exhibited highly consistent cell-type compositions across independent biological replicates (Supplementary Fig. 2).
- Identified distinct developmental branching: EnP bifurcates into canonical islet fates (SC-beta, SC-alpha, SC-delta) and an enterochromaffin-like endocrine lineage (SC-EC).

#### 4. Biological Conclusion
Human pancreatic differentiation proceeds through highly orchestrated checkpoints where specific mutant genotypes drop out, stall, or divert into unexpected developmental branches.

#### 5. Why the Next Figure Was Necessary
While Figure 1 establishes the global cellular atlas, it remains unclear which specific mutant genotypes directly impair beta-cell formation and whether residual beta cells maintain normal functional identity.

---

### Figure 2: Loss of Lineage Regulators Impairs Beta-Cell Formation and Beta-Cell State

#### 1. Scientific Question
Which genetic perturbations reduce the absolute or relative yield of SC-beta cells, and do surviving SC-beta cells in mutant lines suffer from impaired functional gene expression?

#### 2. Experimental Design & Comparison
- Evaluated SC-beta fraction across all 30 mutant genotypes on Day 18 relative to WT.
- Assessed correlation between Day 18 cell yield (fitness/survival) and SC-beta differentiation efficiency.
- Analyzed differential gene expression (DEG) in residual SC-beta cells for knockouts that retain beta cells.

#### 3. Result
- Severe loss of SC-beta cells (<1% of WT level) was observed in *PDX1*(-/-), *RFX6*(-/-), *PAX6*(-/-), *NEUROD1*(-/-), *GLIS3*(-/-), *MNX1*(-/-), and *NKX2-2*(-/-).
- In contrast, *HNF4A*(-/-) and *FOXA1*(-/-) retained substantial numbers of SC-beta cells.
- However, residual *HNF4A*(-/-) and *NEUROD1*(-/-) beta cells exhibited profound disruption of mature beta-cell transcriptional signatures (loss of *INS*, *MAFA*, *SLC30A8*, *G6PC2*, *PCSK1* and ectopic activation of progenitor/disallowed genes).

#### 4. Biological Conclusion
Mutations in monogenic diabetes genes cause beta-cell deficiency through two distinct mechanisms: (1) complete developmental blockage / fate failure, or (2) functional maturation failure in residual cells.

#### 5. Why the Next Figure Was Necessary
If mutations in *PDX1*, *RFX6*, and *PAX6* eliminate SC-beta cells, what happened to those mutant cells? Did they die, arrest at an immature progenitor stage, or adopt an alternative non-beta cell fate?

---

### Figure 3: Impaired Islet Differentiation is Accompanied by Increase of Alternative Lineages

#### 1. Scientific Question
When intended pancreatic lineages fail to differentiate due to transcription factor loss, do mutant cells arrest or divert into non-pancreatic or alternative endodermal lineages?

#### 2. Experimental Design & Comparison
- Quantified cell-type proportions across all 14 cell types on Day 18 for every mutant genotype.
- Mapped off-target and non-pancreatic lineages: Liver/Hepatic, Endothelial, Stromal, Intestinal/Primitive Gut Tube (PGT).

#### 3. Result
- Early endoderm regulators diverted cells into non-pancreatic lineages:
  - *GATA6*(-/-) cells completely failed to form pancreatic lineages and diverted into endothelial cells.
  - *FOXA2*(-/-) cells diverted from posterior foregut toward hepatic / liver progenitor fates (*ALB*, *AFP*, *APOA1*).
  - *HHEX*(-/-) and *HHEX* enhancer knockouts arrested at early primitive gut / foregut stages.
- Endocrine-stage mutants (*RFX6*, *PDX1*, *PAX6*) maintained total endocrine commitment (CHGA+) but failed to produce SC-beta cells.

#### 4. Biological Conclusion
Developmental failure in diabetes mutants involves lineage diversion into both non-pancreatic fates (early TFs like *GATA6*, *FOXA2*) and alternative endocrine fates (late TFs like *RFX6*, *PDX1*, *PAX6*).

#### 5. Why the Next Figure Was Necessary
Because *RFX6*(-/-), *PDX1*(-/-), and *PAX6*(-/-) maintain total endocrine commitment, we must precisely determine the identity of the endocrine cells they produce instead of SC-beta cells.

---

### Figure 4: Loss of RFX6, PDX1, or PAX6 Increases SC-EC Cells at the Expense of SC-Beta Cells

#### 1. Scientific Question
What is the exact identity, regulatory profile, and population balance of the alternative endocrine cells produced when *RFX6*, *PDX1*, or *PAX6* are knocked out?

#### 2. Experimental Design & Comparison
- Evaluated sub-lineage composition within the CHGA+ endocrine compartment on Day 18.
- Measured log2 fold changes of SC-beta, SC-alpha, SC-delta, and SC-EC fractions across mutant genotypes.
- Validated findings using flow cytometry and immunofluorescence co-staining for C-PEP (SC-beta) vs SLC18A1 / Serotonin (SC-EC).

#### 3. Result
- In WT differentiation, SC-beta represents ~45% of endocrine cells, while SC-EC represents ~15-20%.
- In *RFX6*(-/-), *PDX1*(-/-), and *PAX6*(-/-), SC-beta cells collapse to <2%, while SC-EC cells expand to >70-80% of the entire endocrine population.
- This creates an inverse, reciprocal trade-off: loss of SC-beta is directly mirrored by a stoichiometric expansion of SC-EC cells.

#### 4. Biological Conclusion
*RFX6*, *PDX1*, and *PAX6* act as developmental gatekeepers that safeguard SC-beta specification by actively repressing the alternative SC-EC (enterochromaffin) cell fate.

#### 5. Why the Next Figure Was Necessary
We must characterize the molecular identity, gene programs, and transcription factor regulons that govern this non-canonical SC-EC state compared to canonical islet cells.

---

### Figure 5: SC-EC Cells Show Reduced Hormone Regulation and Enhanced Neuronal Signatures

#### 1. Scientific Question
What transcriptomic programs and gene regulatory networks (GRNs) distinguish SC-EC cells from canonical islet cells (SC-beta, SC-alpha, SC-delta)?

#### 2. Experimental Design & Comparison
- Derived co-expression gene programs using consensus Non-Negative Matrix Factorization (cNMF) across all single cells.
- Mapped gene program activities across endocrine cell types.
- Inferred transcription factor regulons using SCENIC+ (motif analysis + gene co-expression).

#### 3. Result
- SC-EC cells express serotonin biosynthesis machinery (*TPH1*, *DDC*, *SLC18A1* / VMAT1).
- SC-EC cells display high activity of neuronal projection and axonogenesis gene programs (Program h3), while showing severe depletion of hormone regulation and secretion programs (Program i5).
- SCENIC+ regulon analysis identified distinct TF drivers:
  - SC-beta program (i5) is driven by *PDX1*, *PAX6*, *FOXO1*, *NR3C1*, and *ISL1*.
  - SC-EC program (h3) is driven by neuronal TFs including *MNX1*, *ZEB1*, and *LMX1A*.

#### 4. Biological Conclusion
SC-EC cells represent a stable, non-canonical neuroendocrine cell fate that hijacks neuronal transcriptional programs in the absence of beta-cell lineage directors.

#### 5. Why the Next Figure Was Necessary
Can we leverage our multi-genotype knockout village dataset to build a predictive model that identifies the upstream causal master repressor of this pathological SC-EC lineage diversion?

---

### Figure 6: Mutant-Based Predictive Analyses Identify ISL1 as a Key Repressor of SC-EC Cells

#### 1. Scientific Question
Can we predict and experimentally validate candidate transcription factors that enforce SC-beta commitment and repress SC-EC lineage diversion during endocrine progenitor specification?

#### 2. Experimental Design & Comparison
- Linear regression of all EnP-expressed transcription factors against the SC-EC / SC-beta ratio across all mutant genotypes.
- Prioritization of candidates from SCENIC+ regulons.
- Experimental generation of *ISL1*(-/-) hPSC lines and differentiation to Day 18.
- Lentiviral rescue: Overexpression (OE) of *ISL1* (ISL1-IRES2-BFP) in WT, *ISL1*(-/-), *PDX1*(-/-), and *PAX6*(-/-) cells at the PP stage (Day 11), followed by bulk RNA-seq and flow cytometry.

#### 3. Result
- *ISL1* expression in EnP showed the strongest negative correlation with the SC-EC / SC-beta ratio among all candidate TFs ($p < 10^{-4}$).
- Knockout validation: *ISL1*(-/-) cells exhibited complete loss of SC-beta cells and massive expansion of SC-EC cells (mirroring *RFX6* and *PDX1* loss).
- Hierarchical rescue:
  - *ISL1* overexpression in *ISL1*(-/-) and WT cells completely repressed the SC-EC (h3) program and restored SC-beta (i5) identity.
  - In *PDX1*(-/-) and *PAX6*(-/-) backgrounds, *ISL1* overexpression was **sufficient to repress SC-EC differentiation**, but **insufficient to fully restore SC-beta identity** without PDX1/PAX6 cooperation.

#### 4. Biological Conclusion
ISL1 is a master downstream repressor of the non-canonical SC-EC fate. Lineage specification requires a two-step regulatory logic: (1) ISL1 represses alternative neuronal/SC-EC fates, and (2) ISL1 acts cooperatively with PDX1, RFX6, and PAX6 to induce the mature SC-beta program.

#### 5. Why These Results Naturally Created the pertTF Question
The precursor study proved that combining multi-genotype knockout data across timepoints allows causal prediction of cell fate choices. However, testing genes one-by-one by linear regression and manual CRISPR knockout is fundamentally unscalable to genome scale. We need a generalizable, context-aware deep learning framework (pertTF) to predict these higher-order lineage conversions across thousands of unmeasured genes.

---

## SECTION 2: 23 CORE BIOLOGICAL & METHODOLOGICAL QUESTIONS (PHASE 5)

1. **Why these genes were selected:**  
   The 30 targeted genes represent high-confidence genetic drivers of human pancreatic diseases (monogenic neonatal diabetes, MODY, T2D risk loci) and key chromatin/epigenetic remodelers known to control cell fate transitions.

2. **How the genes relate to disease & regulation:**
   - **MODY (Maturity-Onset Diabetes of the Young):** *HNF4A* (MODY1), *GCK* (MODY2), *HNF1A* (MODY3), *PDX1* (MODY4), *HNF1B* (MODY5), *NEUROD1* (MODY6), *KLF11* (MODY7), *CEL* (MODY8), *PAX4* (MODY9), *INS* (MODY10), *BLK* (MODY11), *ABCC8* (MODY12), *KCNJ11* (MODY13).
   - **Neonatal Diabetes:** *GATA6*, *GATA4*, *PTF1A*, *RFX6*, *MNX1*, *NKX2-2*, *GLIS3*, *NEUROG3*, *PAX6*, *FOXA2*, *HHEX*, *ONECUT1*.
   - **T2D Risk / Islet Regulation:** *FOXA1*, *ARX*, *BMPR1A*, *GSC*, *PBX1*.
   - **Chromatin / Epigenetic Remodeling:** *TET1*, *TET2*, *TET3*, *QSER1*, *KDM2B*, *BCOR*, *TLE3*, *TADA2B*, *PROSER1*, *OTUD5*.

3. **Why pancreatic differentiation was used:**  
   Human pancreatic islet differentiation is an exquisitely choreographed, multi-step developmental process with well-defined stage-specific checkpoints, making it an ideal model to study how disease mutations alter lineage branching.

4. **Why hPSC-derived pancreatic differentiation is useful:**  
   Human pluripotent stem cells (hPSCs) provide an unlimited source of human developmental tissue, recapitulate in vivo embryonic development, and allow precise genetic engineering of homozygous null mutations in isogenic backgrounds.

5. **Why knockout villages were created:**  
   To eliminate batch effects, standardize culture conditions, and achieve high-throughput single-cell profiling of dozens of mutant lines within a single unified differentiation run.

6. **Why clones were pooled:**  
   Pooling multiple independent clones per genotype (79 total lines for 30 genes) provides biological replication and ensures observed phenotypes are robust to clonal variation.

7. **What developmental stages were sampled:**  
   Five longitudinal stages: Day 0 (ESC), Day 3 (DE), Day 7 (PFG/PP1), Day 11 (EnP/PP2), and Day 18 (SC-islet).

8. **What the cell-state landscape looks like:**  
   The landscape comprises 14 major cell types traversing pluripotent, endodermal, pancreatic progenitor, ductal, hepatic, endothelial, stromal, and mature endocrine lineages (SC-beta, SC-alpha, SC-delta, SC-EC).

9. **What happened to beta-cell differentiation:**  
   Beta-cell differentiation was severely compromised in the majority of diabetes-associated knockouts, with different mutants acting at distinct developmental stages.

10. **Which perturbations reduced SC-beta abundance:**  
    *PDX1*, *RFX6*, *PAX6*, *NEUROD1*, *GLIS3*, *MNX1*, *NKX2-2*, *GATA6*, and *FOXA2* reduced SC-beta abundance to <2-5% of normal levels.

11. **Which perturbations altered SC-beta state even when cells remained:**  
    *HNF4A*(-/-) and *NEUROD1*(-/-) maintained residual SC-beta cells but severely down-regulated insulin secretion machinery and upregulated progenitor/stress programs.

12. **What lineage rewiring means in this dataset:**  
    Lineage rewiring refers to mutant cells actively abandoning their intended developmental trajectory and adopting an entirely different, coherent cellular identity governed by alternative transcriptional networks.

13. **Which perturbations redirected lineage:**  
    - *GATA6*(-/-) redirected endoderm to Endothelial fate.
    - *FOXA2*(-/-) redirected foregut to Hepatic/Liver fate.
    - *RFX6*(-/-), *PDX1*(-/-), *PAX6*(-/-) redirected endocrine progenitors to SC-EC fate.

14. **What GATA6 showed:**  
    GATA6 is essential for definitive endoderm commitment; its loss triggers a dramatic fate switch into endothelial-like cells (*CD34*, *PECAM1*).

15. **What FOXA2 showed:**  
    FOXA2 specifies pancreatic vs hepatic foregut lineages; its loss diverts cells into liver progenitors (*ALB*, *AFP*).

16. **What HHEX showed:**  
    HHEX and its upstream enhancer are required for anterior-posterior patterning and gut tube specification; loss causes arrest at early primitive gut tube (PGT) stages.

17. **What RFX6 / PDX1 / PAX6 showed:**  
    These factors do not block endocrine commitment (cells remain CHGA+), but block beta-cell specification and divert cells into SC-EC enterochromaffin fate.

18. **What was learned about SC-beta vs SC-EC competition:**  
    SC-beta and SC-EC represent mutually exclusive, competing endocrine fates branching from common NEUROG3+ endocrine progenitors (EnP).

19. **What delayed vs alternative cell fates mean:**  
    - *Delayed fate:* Cells lag in pseudotime along the normal trajectory but eventually reach the target state.
    - *Alternative fate:* Cells depart the normal manifold entirely and activate stable, non-target gene regulatory networks.

20. **Whether perturbations caused arrest, diversion, or both:**  
    Both: Early chromatin/endoderm mutants often caused developmental arrest (e.g., *HHEX*, *KDM2B*), whereas lineage-determining TFs caused active diversion (*GATA6*, *FOXA2*, *RFX6*, *PDX1*).

21. **What predictive analysis was already attempted:**  
    Linear regression of EnP transcription factor expression against the SC-EC/SC-beta ratio across mutant lines.

22. **What ISL1 prediction/rescue showed:**  
    - Linear regression predicted ISL1 as the top candidate repressor of SC-EC fate.
    - *ISL1*(-/-) validated the prediction by expanding SC-EC cells.
    - ISL1 overexpression rescued SC-EC suppression across all mutant backgrounds.

23. **Why those results naturally created the pertTF question:**  
    While linear regression worked for this specific single-ratio question, it cannot model non-linear combinatorial interactions, whole-genome perturbations, or generalize to unseen cell types and clinical patient tissues—necessitating the development of pertTF.
"""

with open('precursor_scientific_reading.md', 'w') as f:
    f.write(content)
print('Successfully wrote precursor_scientific_reading.md, length:', len(content))
