# -*- coding: utf-8 -*-
import os

content = """# Comprehensive Case Study Map & Multi-Stage Evidence Matrix (Phase 10A)

This document tracks and ranks key candidate genes that serve as the scientific "glue" bridging:
1. **Precursor Biology:** Experimental knockout village phenotype, lineage rewiring, stage specificity.
2. **pertTF AI Framework:** Model representation, multi-task learning, lochNESS prediction, unseen context/gene generalization, primary islet inference, in silico screens.
3. **Current WIP Decomposition:** Single-cell penetrance (PS), multivariate magnitude (Energy Distance), state localization (lochNESS), DistanceSpace module assignment.

---

## MULTI-STAGE EVIDENCE MATRIX FOR TOP CASE STUDY CANDIDATES

| Rank | Gene | Precursor Biology Phenotype | pertTF Model Representation & Prediction | Primary Islets / Validation | WIP PS (Penetrance) | WIP Energy Distance (Magnitude) | WIP lochNESS (Localization) | WIP Module & Phenotype Group |
|---|---|---|---|---|---|---|---|---|
| **#1 (GOLD)** | **PDX1** | Eliminates SC-beta (<1% yield); triggers stoichiometric SC-EC expansion (Fig 2, 4) | High lochNESS fidelity ($r=0.88$); held-out SC-beta generalization (Cosine=0.912, PCC=0.724); in silico screen top hit (AUC=0.79) | Inferred loss enriched 3.8-fold in T2D donors ($p < 10^{-5}$) (Fig 5d) | N/A (Het=0.313 ED, Hom=0.065 ED) | **PDX1het = 0.3129** (#1 highest in dataset!); PDX1 = 0.0649 (all FDR < 0.001) | SC-beta depletion (lochNESS < -3.8); EnP/SC-EC enrichment (lochNESS > +2.8) | **Module M4 (Master Selector)**; PG7 (Hom) / PG2 (Het) |
| **#2 (GOLD)** | **GATA6** | Definitive endoderm failure; dramatic lineage conversion into Endothelial cells (Fig 3) | Captures early lineage branching; top-ranked PP regulator in in silico screen (Fig 6c) | Generalizes across early developmental transitions | **Median PS = 0.648** (61.6% responder fraction, #4 highest) | **Energy Distance = 0.1590** (#6 highest in dataset, FDR < 0.001) | Extreme focal trapping in Endothelial cells (**Peak lochNESS = +4.530**, 34.5% fraction) | **Module M1 (Core Endoderm Driver)**; PG9 |
| **#3 (GOLD)** | **FOXA2** | Posterior foregut failure; lineage diversion into Hepatic / Liver progenitors (Fig 3) | Predicts foregut-to-hepatic trajectory bifurcation | Recovers endodermal pioneer factor networks | N/A (Het/Hom multi-line) | **Energy Distance = 0.1063** (#10 highest in dataset, FDR < 0.001) | Single highest peak trapping in dataset: **Peak lochNESS = +13.740** in Liver (34.0% fraction) | **Module M1 (Core Endoderm Driver)**; PG8 |
| **#4 (SILVER)** | **RFX6** | Endocrine gatekeeper; blocks SC-beta and drives massive SC-EC expansion (Fig 4) | High lochNESS fidelity; leave-one-out embedding prediction | **Primary islet siRNA validation:** 78.4% classified as perturbed (Cosine=0.873) (Fig 5g-h) | Median PS = 0.435 ($n=3,331$ cells) | Energy Distance = 0.0543 (FDR < 0.001) | SC-beta depletion (lochNESS < -3.5); SC-EC trapping (lochNESS > +2.5) | **Module M1 (Core Endoderm Driver)**; PG3 |
| **#5 (SILVER)** | **GLIS3** | Severe SC-beta loss; neonatal diabetes driver; progenitor arrest | Embedding clustering in endocrine progenitor branch | Unseen genotype leave-one-out winner | **Median PS = 0.750** (#1 single highest PS in dataset, 66.6% responders) | **Energy Distance = 0.1854** (#5 highest in dataset, FDR < 0.001) | Massive progenitor trapping: **Peak lochNESS = +13.625** in PDP (64.5% fraction) | **Module M1 (Core Endoderm Driver)**; PG2 |
| **#6 (SILVER)** | **HHEX** | Anterior-posterior patterning; developmental arrest at Primitive Gut Tube (Fig 3) | Predicts early gut tube composition shifts | Recovers early foregut regulatory check | **Median PS = 0.659** (59.8% responder fraction, #3 highest) | **HHEXhet = 0.2307** (#2 highest); HHEX = 0.2034 (#4 highest); HHEXe = 0.1227 | Strong trapping in PGT / PFG; complete absence of downstream endocrine states | **Module M1 (Core Endoderm Driver)**; PG1 |
| **#7 (BRONZE)** | **NEUROD1** | Beta-cell yield reduction and complete loss of insulin secretion machinery (Fig 2) | Separates beta-1 vs beta-2 regulatory states | Latent loss state enriched in fragile $\beta-2$ primary cells ($p < 10^{-4}$) (Fig 5e) | Evaluated across endocrine subsets | Energy Distance = 0.0512 (FDR < 0.001) | Selective depletion in mature SC-beta; enrichment in immature EnP | **Module M3 (Corepressor / Maturation)**; PG5 |
| **#8 (BRONZE)** | **PAX6** | Gatekeeper repressing SC-EC fate; cooperates with ISL1/PDX1 (Fig 4, 6) | Leave-one-out generalization across endocrine states | Validated co-regulation of hormone programs | Evaluated across endocrine subsets | Energy Distance = 0.0381 (FDR < 0.001) | SC-beta depletion; SC-EC expansion | **Module M6 (Lineage Director)**; PG6 |

---

## DETAILED DEEP-DIVE FOR TOP 3 GOLD CASE STUDIES

### Case Study 1: PDX1 — The Master Pancreatic Beta-Cell Selector
1. **Biological Experiment:** *PDX1*(-/-) hPSCs differentiate normally to the pancreatic progenitor stage (Day 7) but fail completely at the endocrine bifurcation (Day 11-18), eliminating SC-beta cells (<1%) and diverting progenitors into serotonergic SC-EC cells.
2. **pertTF Model Representation:** pertTF embeds *PDX1* loss as a distinct trajectory shift; predicts lochNESS with Pearson $r = 0.88$; accurately predicts held-out SC-beta *PDX1* knockout with Cosine Sim = 0.912 and PCC-delta = 0.724.
3. **Primary Islet Translation:** Latent *PDX1* loss state is enriched 3.8-fold in clinical T2D patient islets ($p < 10^{-5}$), proving that developmental failure mirrors adult diabetic pathology.
4. **In Silico Genetic Screen:** In silico screening for PDX1-GFP regulators achieves ROC-AUC = 0.79, recovering known upstream directors (*GATA6*, *MAPK1*).
5. **WIP Multi-Dimensional Decomposition:**
   - *PDX1het* exhibits the **#1 highest Energy Distance in the entire dataset (0.3129)**, demonstrating extreme dosage sensitivity.
   - Decomposes into Module M4 (Master Selector) with massive signed lochNESS polarity (SC-beta depletion < -3.8 vs SC-EC/EnP trapping > +2.8).

---

### Case Study 2: GATA6 — The Definitive Endoderm Gatekeeper & Transdifferentiation Driver
1. **Biological Experiment:** *GATA6*(-/-) hPSCs fail at the earliest definitive endoderm checkpoint (Day 3), abandoning the endodermal lineage entirely and transdifferentiating into endothelial cells (*CD34*, *PECAM1*).
2. **pertTF Model Representation:** pertTF captures early lineage bifurcation; accurately places *GATA6* as the top-ranked hit in virtual progenitor screens (Fig. 6c).
3. **WIP Multi-Dimensional Decomposition:**
   - **High Response Penetrance:** Median PS = 0.648 (61.6% true responding cells, #4 highest).
   - **Extreme Multivariate Magnitude:** Energy Distance = 0.1590 (#6 highest, FDR < 0.001).
   - **Focal Topological Trapping:** Peak lochNESS = +4.530, with 34.5% of cells stably trapped in the Endothelial state.
   - **Module Assignment:** Module M1 (Core Endoderm Driver), Phenotype Group PG9.

---

### Case Study 3: FOXA2 — The Foregut Pioneer & Hepatic Lineage Checkpoint
1. **Biological Experiment:** *FOXA2*(-/-) cells proceed through definitive endoderm but fail during posterior foregut patterning (Day 7), diverting directly into liver / hepatic progenitor cells (*ALB*, *AFP*, *APOA1*).
2. **pertTF Model Representation:** Captures the pioneer factor regulatory network and predicts foregut diversion.
3. **WIP Multi-Dimensional Decomposition:**
   - **Extreme Global Magnitude:** Energy Distance = 0.1063 (#10 highest, FDR < 0.001, $n=4,896$ cells).
   - **Record-Breaking Focal Trapping:** Displays the **single highest peak lochNESS in the entire 111,581-cell dataset (Peak lochNESS = +13.740)**, with 34.0% of all cells converted into Liver fate.
   - **Module Assignment:** Module M1 (Core Endoderm Driver), Phenotype Group PG8.
"""

with open('Case_Study_Map.md', 'w') as f:
    f.write(content)
print('Successfully wrote Case_Study_Map.md, length:', len(content))
