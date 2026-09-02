# -*- coding: utf-8 -*-
import os

content = """# Figure Source Map & Asset Inventory (Phase 7)

This document maps every required manuscript figure and panel to its highest-quality clean source file, establishing extraction feasibility without raster degradation.

---

## SOURCE PRIORITY HIERARCHY
1. **TIER 1 (BEST):** Editable PPTX shape / vector panel / standalone vector PDF (`pertTF-figures/*.pptx`, `pertTF-precussor-figures/Fig.*.pdf`).
2. **TIER 2 (EXCELLENT):** High-resolution extracted PNG from original vector PDFs / PPTX (`clean_sources/precursor_figures_png/*.png`, `clean_sources/pertTF_extracted_pptx_images/*.png`).
3. **TIER 3 (GOOD):** High-DPI full-page manuscript PDF render (`clean_sources/*_pdf_pages/page-*.png`).
4. **TIER 4 (LAST RESORT):** Cropped raster manuscript PDF (avoided).

---

## COMPLETE FIGURE SOURCE MAPPING TABLE

| Paper | Figure | Panel(s) | Scientific Purpose | Best Source File | Source Type | Editable? | Clean Extraction Possible? | Manual Extraction Required? | Alternate Source File |
|---|---|---|---|---|---|---|---|---|---|
| **pertTF** | Fig 1 | 1a | Knockout village & differentiation stages | `pertTF-figures/Fig. 2_v5.pptx` | Vector PPTX | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-04.png` |
| **pertTF** | Fig 1 | 1b | pertTF architecture & multi-task loss | `Diabetes_perTF.pptx` (Slide 3) | Vector PPTX Shapes | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-04.png` |
| **pertTF** | Fig 1 | 1c | Cell-type classification benchmark | `pertTF-figures/Fig. 2_v5.pptx` | Vector / High-res PNG | Yes | Yes | No | `clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img3.png` |
| **pertTF** | Fig 1 | 1d | Genotype classification benchmark | `pertTF-figures/Fig. 2_v5.pptx` | Vector / High-res PNG | Yes | Yes | No | `clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img4.png` |
| **pertTF** | Fig 1 | 1e-f | Latent cell-type & genotype embeddings | `pertTF-figures/Fig. 2_v5.pptx` | High-res PNG | Partial | Yes | No | `clean_sources/pertTF_extracted_pptx_images/Fig._2_v5_slide1_img0.png` |
| **pertTF** | Fig 2 | 2a | lochNESS local neighborhood schematic | `pertTF-figures/Fig. 3_v4.pptx` | Vector PPTX Shapes | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 2 | 2b-c | Observed vs predicted lochNESS (PDX1, TADA2B, GATA4) | `pertTF-figures/Fig. 3_v4.pptx` | Vector PPTX / Charts | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 2 | 2d-e | lochNESS benchmark vs expression baseline | `pertTF-figures/Fig. 3_v4.pptx` | Vector PPTX / Charts | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 3 | 3a | Generalization workflow schematic | `pertTF-figures/Fig. 3_v4.pptx` | Vector PPTX Shapes | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 3 | 3b | PDX1 prediction in held-out SC-beta context | `pertTF-figures/Fig. 3_v4.pptx` | High-res PNG / Vector | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 3 | 3c | 30-genotype leave-one-out benchmark | `pertTF-figures/Fig. 3_v4.pptx` | Vector Bar Chart | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 3 | 3d | Joint unseen gene + context benchmark | `pertTF-figures/Fig. 3_v4.pptx` | Vector Bar Chart | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 4 | 4a | CRISPRi 50-gene Perturb-seq design | `pertTF-figures/Fig. 4_v7.pptx` | Vector PPTX Shapes | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 4 | 4b | CTNNB1 knockdown shift & expression | `pertTF-figures/Fig. 4_v7.pptx` | Vector / High-res PNG | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 4 | 4c-d | Multi-gene CRISPRi benchmark vs scGPT | `pertTF-figures/Fig. 4_v7.pptx` | Vector Charts | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 5 | 5a | Primary human islet transfer workflow | `pertTF-figures/Fig. 5_v4.pptx` | Vector PPTX Shapes | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 5 | 5b-c | Primary islet fine-tuning performance | `pertTF-figures/Fig. 5_v4.pptx` | Vector Line Charts | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 5 | 5d-e | PDX1 / NEUROD1 / HNF4A disruption in T2D & beta-2 | `pertTF-figures/Fig. 5_v4.pptx` | Vector Boxplots | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-20.png` |
| **pertTF** | Fig 5 | 5g-h | RFX6 siRNA experimental validation | `pertTF-figures/Fig. 5_v4.pptx` | Vector Bar / UMAP | Yes | Yes | No | `clean_sources/pertTF_pdf_pages/page-21.png` |
| **pertTF** | Fig 6 | 6a | In silico screening methods (Method 1 vs 2) | `pertTF-figures/Fig. 6_v7.pptx` | Vector PPTX Shapes | Yes | Yes | No | `clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img1.png` |
| **pertTF** | Fig 6 | 6b-d | PP screen PDX1-GFP validation & ROC curve | `pertTF-figures/Fig. 6_v7.pptx` | Vector ROC / Waterfall | Yes | Yes | No | `clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img4.png` |
| **pertTF** | Fig 6 | 6e-g | Essential gene lochNESS calibration | `pertTF-figures/Fig. 6_v7.pptx` | Vector Cumulative Dist | Yes | Yes | No | `clean_sources/pertTF_extracted_pptx_images/Fig._6_v7_slide1_img3.png` |
| **pertTF** | Fig 6 | 6h-j | In silico Perturb-seq & multi-complex clustering | `pertTF-figures/Fig. 6_v7.pptx` | High-res Heatmap / UMAP | Partial | Yes | No | `clean_sources/pertTF_pdf_pages/page-21.png` |
| **pertTF** | Supp Fig 1-8 | S1-S8 | Training curves, HVG UMAPs, LOO details, DE screen | `pertTF-figures/Supplementary Fig_v8.pptx` | 8-Slide Master PPTX | Yes | Yes | No | `clean_sources/pertTF_extracted_pptx_images/` |
| **Precursor** | Fig 1 | 1a-c | Knockout village design, 30 genes, stage dynamics | `pertTF-precussor-figures/Fig.1.pdf` | Vector PDF | No (Vector) | Yes | No | `clean_sources/precursor_figures_png/Fig.1-1.png` |
| **Precursor** | Fig 2 | 2a-e | Beta-cell yield volcano & DEG collapse | `pertTF-precussor-figures/Fig.2.pdf` | Vector PDF | No (Vector) | Yes | No | `clean_sources/precursor_figures_png/Fig.2-1.png` |
| **Precursor** | Fig 3 | 3a-e | Cell-type composition dotplot & GATA6/FOXA2 diversions | `pertTF-precussor-figures/Fig.3.pdf` | Vector PDF | No (Vector) | Yes | No | `clean_sources/precursor_figures_png/Fig.3-1.png` |
| **Precursor** | Fig 4 | 4a-f | SC-beta vs SC-EC trade-off (RFX6, PDX1, PAX6) | `pertTF-precussor-figures/Fig.4.pdf` | Vector PDF | No (Vector) | Yes | No | `clean_sources/precursor_figures_png/Fig.4-1.png` |
| **Precursor** | Fig 5 | 5a-h | cNMF gene programs & SCENIC+ regulons | `pertTF-precussor-figures/Fig.5.pdf` | Vector PDF | No (Vector) | Yes | No | `clean_sources/precursor_figures_png/Fig.5-1.png` |
| **Precursor** | Fig 6 | 6a-m | ISL1 regression discovery, knockout & rescue | `clean_sources/precursor_pdf_pages/page-44.png` | High-DPI Page Render | No | Yes | Yes | `pertTF-precussor.pdf` (Page 44) |
"""

with open('Figure_Source_Map.md', 'w') as f:
    f.write(content)
print('Successfully wrote Figure_Source_Map.md, length:', len(content))
