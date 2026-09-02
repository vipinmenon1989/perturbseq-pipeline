# Case Study Evidence Audit & Traceability Matrix (Phase 6 Audit)

This document establishes the exact traceability of every biological and computational claim for the top 5 case study genes across **Precursor Biology**, **pertTF AI Framework**, and **Current WIP Multi-Dimensional Decomposition**.

---

## 1. PDX1 (GOLD CASE STUDY #1)

### A. Precursor Evidence
- **Exact Citation:** Liu et al., Figures 2a, 2b, 4a, 4b, 4e, 6b, 6f; Supp. Fig. 3a, 4a, 5a; Manuscript pages 6, 8, 9, 11.
- **Traceable Statements:**
  - *Homozygous knockout (PDX1-/-):* Eliminates SC-beta cells on Day 18 to $<1\%$ of WT level (Fig. 2a-b).
  - *Lineage Diversion:* Total endocrine fraction (CHGA+) remains intact, but cells divert stoichiometrically into serotonergic SC-EC cells ($>70\%$ of endocrine population) expressing *SLC18A1* and *TPH1* (Fig. 4a-b).
  - *Residual Beta State:* Shows collapse of mature beta markers (*INS*, *MAFA*, *SLC30A8*, *G6PC2*) and failure of glucose-sensing machinery (Supp. Fig. 3a).
  - *Hierarchy:* ISL1+ cells are significantly reduced in *PDX1*(-/-) (Fig. 6f).

### B. pertTF Evidence
- **Exact Citation:** Su, Liu, Menon et al., Figures 2b, 3b, 5d, 6b, 6c, 6d; Supp. Fig. 4a, 6a, 7a; Manuscript pages 5, 6, 8, 9, 10.
- **Traceable Statements:**
  - *lochNESS Score Prediction:* Accurately recapitulates negative lochNESS in SC-beta (depletion) and positive lochNESS in EnP/SC-EC (enrichment) ($r pprox 0.88$, Fig. 2b, 2d).
  - *Unseen Context Generalization:* When perturbed SC-beta cells are withheld during training, pertTF accurately predicts *PDX1* knockout phenotype from WT SC-beta input (Cosine Sim $pprox 0.91$, PCC-delta $pprox 0.72$, DE-direction $pprox 85\%$, Fig. 3b).
  - *Clinical Primary Islets:* Cells in a latent "*PDX1* loss state" increase dynamically across clinical progression, showing $\sim 3.8$-fold enrichment in T2D patient donors vs non-diabetic controls ($p < 0.0001$, Fig. 5d).
  - *In Silico Pooled Screen:* Virtual screen for PDX1-GFP regulators achieves ROC-AUC = 0.79 (vs Expression AUC = 0.66, Fig. 6d).

### C. WIP Decomposition Evidence
- **Exact Citation:** `distance_results.csv` (Row 0, 26), `lochness_summary.csv` (Row 26), `module_assignments.csv` (Row 32), `phenotype_groups.csv` (Row 26, 27).
- **Traceable Statements:**
  - *Extreme Dosage Sensitivity:* **PDX1het exhibits the #1 highest Energy Distance in the entire dataset (Energy Distance = 13.633665, MMD = 0.312907, FDR = 0.000999, $n=469$ cells)**.
  - *Homozygous Distance:* PDX1 homozygous KO shows Energy Distance = 2.457885 (MMD = 0.064893, FDR = 0.000999, $n=6,207$ cells), whereas PDX1het exhibits Energy Distance = 13.633665 (MMD = 0.312907), demonstrating pronounced dosage-dependent phenotypic divergence.
  - *Focal Lineage Trapping:* Dominant cell type is SC-EC (fraction = 25.4%, dominant lochNESS = 9.789030, Peak lochNESS = 15.543285).
  - *Module Assignment:* Partitions as the dedicated anchor of **Module M4 (Beta Master Selector)**; Phenotype Group PG7 (Homozygous) and PG2 (Heterozygous).

---

## 2. GATA6 (GOLD CASE STUDY #2)

### A. Precursor Evidence
- **Exact Citation:** Liu et al., Figures 3a, 3c; Supp. Fig. 1b, 4a; Manuscript pages 7, 8.
- **Traceable Statements:**
  - *Early Fate Checkpoint:* *GATA6*(-/-) hPSCs fail at the definitive endoderm checkpoint (Day 3).
  - *Transdifferentiation:* Completely eliminates all pancreatic lineages and diverts cells into Endothelial cells expressing *CD34* and *PECAM1* (Fig. 3a, 3c).

### B. pertTF Evidence
- **Exact Citation:** Su, Liu, Menon et al., Figure 6c; Manuscript page 10.
- **Traceable Statements:**
  - *In Silico Progenitor Screen:* Ranked as a top-priority hit in the virtual PP screen for pancreatic progenitor regulators without explicit supervision (Fig. 6c).

### C. WIP Decomposition Evidence
- **Exact Citation:** `ps_score_summary.csv` (Row 1), `distance_results.csv` (Row 2), `lochness_summary.csv` (Row 7), `module_assignments.csv` (Row 5), `phenotype_groups.csv` (Row 7).
- **Traceable Statements:**
  - *High Single-Cell Penetrance:* **Median PS = 0.648252, Responder Fraction = 61.60% ($n=1,500$ cells, #4 highest PS in dataset)**.
  - *Massive Multivariate Magnitude:* **Energy Distance = 9.704493 (MMD = 0.159007, FDR = 0.000999, #3 highest KO distance)**.
  - *Topological Trapping:* Peak lochNESS = 37.058636 (dominant celltype lochNESS = 4.529683, Endothelial fraction = 34.5%).
  - *Module Assignment:* Partitions into **Module M1 (Core Endoderm Drivers)**; Phenotype Group PG9.

---

## 3. FOXA2 (GOLD CASE STUDY #3)

### A. Precursor Evidence
- **Exact Citation:** Liu et al., Figures 3a, 3d; Supp. Fig. 1b, 4a; Manuscript pages 7, 8.
- **Traceable Statements:**
  - *Foregut Bifurcation Checkpoint:* *FOXA2*(-/-) hPSCs proceed through definitive endoderm but fail during posterior foregut patterning (Day 7).
  - *Hepatic Diversion:* Diverts cells into hepatic / liver progenitor fates expressing *ALB*, *AFP*, and *APOA1* (Fig. 3a, 3d).

### B. pertTF Evidence
- **Exact Citation:** Su, Liu, Menon et al., Figure 1f, 3c; Manuscript pages 5, 7.
- **Traceable Statements:**
  - *Representation:* Embeds pioneer factor network disruption; successfully evaluated in leave-one-genotype-out testing.

### C. WIP Decomposition Evidence
- **Exact Citation:** `distance_results.csv` (Row 9), `lochness_summary.csv` (Row 4), `module_assignments.csv` (Row 7), `phenotype_groups.csv` (Row 4).
- **Traceable Statements:**
  - *Multivariate Magnitude:* **Energy Distance = 5.446592 (MMD = 0.106312, FDR = 0.000999, $n=4,896$ cells)**.
  - *Extreme Topological Trapping:* **Dominant cell type is Liver (fraction = 34.05%, dominant celltype lochNESS = 13.740321, Peak lochNESS = 18.307343)**.
  - *Module Assignment:* Partitions into **Module M1 (Core Endoderm Drivers)**; Phenotype Group PG8.

---

## 4. RFX6 (SILVER CASE STUDY #4)

### A. Precursor Evidence
- **Exact Citation:** Liu et al., Figures 2a, 4a, 4c, 4e, 6b, 6f; Supp. Fig. 4a, 5a; Manuscript pages 6, 8, 9, 11.
- **Traceable Statements:**
  - *Endocrine Gatekeeper:* *RFX6*(-/-) maintains total endocrine commitment (CHGA+) but collapses SC-beta ($<1\%$) and triggers massive expansion of SC-EC cells ($>75\%$ of endocrine cells, Fig. 4a, 4c).
  - *Upstream Regulator:* Loss of RFX6 abolishes ISL1 expression on Day 18 (Fig. 6f).

### B. pertTF Evidence
- **Exact Citation:** Su, Liu, Menon et al., Figure 5g, 5h; Supp. Fig. 6c; Manuscript pages 9, 21.
- **Traceable Statements:**
  - *Primary Islet Experimental Validation:* When primary human islets received siRNA knockdown of *RFX6*, pertTF accurately classified **~78% of knockdown cells as RFX6-perturbed (vs $<5\%$ in non-targeting controls)**, with predicted cell embedding Cosine Similarity $pprox 0.87$ (Fig. 5g-h).

### C. WIP Decomposition Evidence
- **Exact Citation:** `ps_score_summary.csv` (Row 11), `distance_results.csv` (Row 17), `lochness_summary.csv` (Row 28), `module_assignments.csv` (Row 17), `phenotype_groups.csv` (Row 31).
- **Traceable Statements:**
  - *Single-Cell Score:* Median PS = 0.451290, Responder Fraction = 30.98% ($n=3,331$ cells).
  - *Multivariate Distance:* Energy Distance = 2.115886 (MMD = 0.054291, FDR = 0.000999).
  - *Topological Trapping:* SC-beta depletion (lochNESS $< -3.5$); SC-EC trapping (dominant celltype PFG/SC-EC, Peak lochNESS = 9.127226).
  - *Module Assignment:* Partitions into **Module M1 (Core Endoderm Drivers)**; Phenotype Group PG3.

---

## 5. GLIS3 (SILVER CASE STUDY #5)

### A. Precursor Evidence
- **Exact Citation:** Liu et al., Figures 2a, 3a; Supp. Fig. 1b, 4a; Manuscript pages 6, 7.
- **Traceable Statements:**
  - *Neonatal Diabetes Factor:* *GLIS3*(-/-) causes severe reduction of SC-beta formation and arrest at early pancreatic progenitor stages.

### B. pertTF Evidence
- **Exact Citation:** Su, Liu, Menon et al., Figure 1f, 3c; Manuscript pages 5, 7.
- **Traceable Statements:**
  - *Representation:* Accurately embedded in endocrine lineage branch; high leave-one-out cosine similarity.

### C. WIP Decomposition Evidence
- **Exact Citation:** `ps_score_summary.csv` (Row 0), `distance_results.csv` (Row 5), `lochness_summary.csv` (Row 9), `module_assignments.csv` (Row 3), `phenotype_groups.csv` (Row 9).
- **Traceable Statements:**
  - *Single-Cell Penetrance Record:* **GLIS3 exhibits the #1 highest Median PS in the entire dataset (Median PS = 0.750025, Responder Fraction = 66.63%, $n=935$ cells)**.
  - *Multivariate Magnitude:* **Energy Distance = 7.969341 (MMD = 0.185375, FDR = 0.000999, #5 highest distance)**.
  - *Focal Lineage Trapping:* **Dominant cell type is ESC (fraction = 64.49%, dominant celltype lochNESS = 13.625399, Peak lochNESS = 25.563601)**.
  - *Module Assignment:* Partitions into **Module M1 (Core Endoderm Drivers)**; Phenotype Group PG2.
