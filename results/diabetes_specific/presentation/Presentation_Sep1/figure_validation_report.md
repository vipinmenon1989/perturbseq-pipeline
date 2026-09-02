# Figure Validation & Visual QA Audit Report

This report documents the figure-level visual and quantitative quality assurance (QA) performed for every slide in `presentation/PertTF_Master_Scientific_Story.pptx`.

---

## 1. QA Criteria & Standards
1. **Aspect Ratio Preservation:** All figures must use exact contain-fitting geometry with zero stretching.
2. **Axis & Legend Integrity:** All coordinate axes, tick marks, gene names, statistics, and colorbars must be preserved without cropping.
3. **Clean Source Priority:** Use standalone vector PNG/PDF renders from `Figure_Source_Map.md` rather than rasterized page screenshots.
4. **Typography & Readability:** Slide headers, body bullet text, and takeaway callouts must have distinct visual hierarchy and zero overlapping frames.

---

## 2. SLIDE-BY-SLIDE FIGURE VALIDATION TABLE

| Slide # | Slide Title | Figure Source File | Source Dimensions (px) | Slide Dimensions (in) | Aspect Ratio Preserved? | Cropped? | Legend & Axes Intact? | Readability Status | QA Action Taken |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Title Slide | N/A (Text / Theme Card) | N/A | Full Slide | N/A | No | N/A | Excellent | Verified navy brand styling |
| 2 | Scientific Framing | N/A (3 Strategy Cards) | N/A | Full Slide | N/A | No | N/A | Excellent | Verified typography & spacing |
| 3 | Human Pancreatic Diff. | `clean_sources/precursor_figures_png/Fig.1-1.png` | 2550 x 3301 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Centered in white card |
| 4 | Knockout Village Design | `clean_sources/precursor_figures_png/Fig.1-1.png` | 2550 x 3301 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Centered in white card |
| 5 | Beta-Cell Formation Loss | `clean_sources/precursor_figures_png/Fig.2-1.png` | 2550 x 3301 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Volcano plot clearly legible |
| 6 | Alternative Lineages | `clean_sources/precursor_figures_png/Fig.3-1.png` | 2550 x 3301 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Dotplot & UMAPs intact |
| 7 | SC-Beta vs SC-EC Trade-Off | `clean_sources/precursor_figures_png/Fig.4-1.png` | 2550 x 3301 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Composition bars legible |
| 8 | ISL1 Predictive Modeling | `clean_sources/precursor_pdf_pages/page-44.png` | 2125 x 2750 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | High-DPI page render |
| 9 | Combinatorial Barrier | N/A (2 Strategy Cards) | N/A | Full Slide | N/A | No | N/A | Excellent | Clean 2-column layout |
| 10 | pertTF Architecture | `clean_sources/pertTF_pdf_pages/page-04.png` | 2125 x 2750 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Architecture diagram clean |
| 11 | Representation Benchmark | `clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img3.png` | 1184 x 1042 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | F1 bar chart intact |
| 12 | lochNESS Formulation | `clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img0.png` | 643 x 523 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | UMAP clustering sharp |
| 13 | Unseen Context Pred. | `clean_sources/pertTF_pdf_pages/page-20.png` | 2125 x 2750 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | PDX1 held-out panel |
| 14 | LOGO Unseen Genes | `clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img4.png` | 538 x 431 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Genotype benchmark bar |
| 15 | Joint Generalization | `clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide4_img24.png` | 899 x 1282 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Joint benchmark chart |
| 16 | CRISPRi Validation | `clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide5_img26.png` | 2100 x 1800 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | CTNNB1 shift & PS score |
| 17 | Primary Islet Transfer | `clean_sources/pertTF_extracted_pptx_images/Fig._5_v4_slide1_img0.png` | 1234 x 760 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Primary cell fine-tuning |
| 18 | Latent T2D Disruption | `clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide6_img29.png` | 2100 x 2100 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | T2D donor boxplots intact |
| 19 | Primary siRNA Validation | `clean_sources/pertTF_extracted_pptx_images/Supplementary_Fig_v8_slide6_img31.png` | 1682 x 1241 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | RFX6 siRNA bar chart |
| 20 | Virtual Genetic Screen | `clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img4.png` | 5366 x 3056 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | PDX1-GFP ROC & waterfall |
| 21 | Essential Gene Calib. | `clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img3.png` | 5366 x 3056 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Essential lochNESS dist |
| 22 | pertTF Synthesis | N/A (2 Strategy Cards) | N/A | Full Slide | N/A | No | N/A | Excellent | Verified summary layout |
| 23 | Next Question (WIP) | N/A (Full Card Layout) | N/A | Full Slide | N/A | No | N/A | Excellent | 3-question conceptual card |
| 24 | Three Phenotypic Pillars | `figures/19_perturbation_summary.png` | 6552 x 3240 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | 37-genotype matrix |
| 25 | PS vs Energy Distance | `figures/07_ps_vs_distance.png` | 2123 x 1909 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Scatter plot & fit line |
| 26 | PS vs lochNESS Decoupling| `figures/10_ps_vs_lochness_positive.png` | 2098 x 1909 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Decoupling scatter |
| 27 | Case Study Synthesis | `figures/28_umap_highlight_genotypes.png` | 5352 x 1291 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Multi-panel UMAP atlas |
| 28 | DistanceSpace & Modules | `figures/14_distance_space.png` | 4660 x 2148 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | PCoA & network diagram |
| 29 | Master Summary | N/A (3 Strategy Cards) | N/A | Full Slide | N/A | No | N/A | Excellent | Verified 3-pillar summary |
| 30 | Future Modeling Roadmap | N/A (Full Card Layout) | N/A | Full Slide | N/A | No | N/A | Excellent | 4-point roadmap card |
| 31 | Backup: DistanceTest | `figures/06_energy_distance_by_perturbation.png` | 2199 x 2602 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | Energy Distance rank bar |
| 32 | Backup: Manifold Atlases | `figures/27_umap_ps_lochness_comparison.png` | 5276 x 2430 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | PS vs lochNESS UMAP |
| 33 | Backup: Response Matrix | `figures/13_lochness_by_celltype.png` | 3441 x 3070 | 7.5 x 5.0 | Yes (Contain) | No | Yes | High Resolution | 14-celltype heatmap |
| 34 | Backup: Method QC Audit | N/A (Full Card Layout) | N/A | Full Slide | N/A | No | N/A | Excellent | Quality control table |
