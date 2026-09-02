# Quantitative Claim Audit & Source Verification Table (Phase 1 Audit)

This audit cross-examines every quantitative claim against primary manuscript text, vector PPTX figures, high-DPI page renders, and exact WIP CSV tables.

---

## VERIFICATION CATEGORY DEFINITIONS
- **TEXT-VERIFIED:** Stated verbatim in manuscript text, figure legends, or methods. (Allowed on slides)
- **TABLE-VERIFIED:** Extracted directly from primary CSV tables in `results/diabetes_specific/tables/`. (Allowed on slides)
- **FIGURE-VERIFIED:** Read from labeled numerical axes, data tables, or text callouts within vector PPTX figure panels. (Allowed on slides)
- **APPROXIMATE-FROM-FIGURE:** Visually estimated from unlabelled continuous bar/scatter/box plot axes. (Allowed ONLY with explicit approx marker, e.g., `~0.98`)
- **UNVERIFIED:** Cannot be confirmed in text, tables, or figure data. (PROHIBITED ON SLIDES)

---

## COMPLETE AUDIT OF QUANTITATIVE CLAIMS

| # | Claim Description | Value Reported | Source Document | Exact Figure / Panel / Table | Exact Manuscript Text OR CSV Row | Verification Status | Notes & Corrections |
|---|---|---|---|---|---|---|---|
| 1 | PP in silico screen pertTF AUC | 0.79 | `pertTF.pdf` | Fig. 6d, Page 10 | "pertTF achieved a higher area under the curve (AUC = 0.79) than expression-only ranking (AUC = 0.66; Fig. 6d)" | **TEXT-VERIFIED** | Gold standard benchmark hit |
| 2 | PP in silico screen Expression AUC | 0.66 | `pertTF.pdf` | Fig. 6d, Page 10 | "than expression-only ranking (AUC = 0.66; Fig. 6d)" | **TEXT-VERIFIED** | Baseline comparator |
| 3 | Knockout village clonal lines | 79 | `pertTF.pdf` / `precursor.pdf` | Main Text, Fig. 1a | "79 mutant hPSC clonal lines targeting 30 pancreas lineage regulators" | **TEXT-VERIFIED** | Library size |
| 4 | Targeted genes | 30 | `pertTF.pdf` / `precursor.pdf` | Main Text, Fig. 1a | "targeting 30 pancreas lineage regulators and diabetes risk genes" | **TEXT-VERIFIED** | Knockout village scope |
| 5 | Longitudinal differentiation stages | 5 | `pertTF.pdf` / `precursor.pdf` | Main Text, Fig. 1a | "profiled by scRNA-seq across five islet differentiation stages" | **TEXT-VERIFIED** | Day 0, 3, 7, 11, 18 |
| 6 | Major annotated cell types | 14 | `pertTF.pdf` | Main Text, Page 4 | "spanning 14 major cell types (see Methods)" | **TEXT-VERIFIED** | 14 curated cell lineages |
| 7 | Total single cells profiled | 111,581 | `precursor.pdf` / `diabetes_analysis.h5ad` | AnnData obs | `adata.shape = (111581, 36601)` | **TABLE-VERIFIED** | Exact dataset cell count |
| 8 | High-content sequencing cells | >87,000 | `Diabetes_perTF.pptx` | Slide 2 | "generate a high-content matrix of >87,000 cells" | **TEXT-VERIFIED** | Alternative filtering threshold |
| 9 | Masked training HVG ratio | 2:1 | `pertTF.pdf` | Methods, Page 13 | "predominantly from pre-calculated highly variable genes (HVGs) at a 2:1 ratio against non-HVGs" | **TEXT-VERIFIED** | Architectural training detail |
| 10 | Learning rate decay rate | 0.995 | `pertTF.pdf` | Methods, Page 16 | "step schedular with learning rate decay at 0.995" | **TEXT-VERIFIED** | Training hyperparameter |
| 11 | CRISPRi Perturb-seq library | 50 genes | `pertTF.pdf` | Main Text, Page 7 | "Perturb-seq (50-gene)... DNA oligonucleotide pools" | **TEXT-VERIFIED** | Cross-modality screen |
| 12 | Primary islet fine-tuning cells | <300 cells | `Diabetes_perTF.pptx` | Slide 8 | "fine-tune our model on primary human islet cells using fewer than 300 cells" | **TEXT-VERIFIED** | Transfer learning data size |
| 13 | Single-cell beta correlation ($P_{HNF4A}$) | $r = -0.78, p=0$ | `pertTF-figures/Fig. 5_v4.pptx` | Fig. 5f, Slide 1 | "PHNF4A vs PHNF4A at a single beta cell level, PCC=-0.78, p=0" | **FIGURE-VERIFIED** | Exact vector text callout |
| 14 | In silico screen PDX1 similarity | 0.995 | `pertTF-figures/Fig. 6_v7.pptx` | Fig. 6c Table, Slide 1 | `Table row: ['PDX1', '0.995', '1']` | **FIGURE-VERIFIED** | Top rank in silico screen |
| 15 | Cell-type classification F1 (pertTF 12L) | 0.985 | `pertTF.pdf` | Fig. 1c | Bar plot y-axis ~0.98 | **APPROXIMATE-FROM-FIGURE** | Precise exact decimal 0.985 is estimated; use `>0.98` |
| 16 | Cell-type classification F1 (scGPT) | 0.932 | `pertTF.pdf` | Fig. 1c | Bar plot y-axis ~0.93 | **APPROXIMATE-FROM-FIGURE** | Precise exact decimal 0.932 is estimated; use `~0.93` |
| 17 | Genotype classification F1 (pertTF) | 0.842 | `pertTF.pdf` | Fig. 1d | Bar plot y-axis ~0.84 | **APPROXIMATE-FROM-FIGURE** | Precise exact decimal 0.842 is estimated; use `~0.84` |
| 18 | Genotype classification F1 (scGPT) | 0.612 | `pertTF.pdf` | Fig. 1d | Bar plot y-axis ~0.61 | **APPROXIMATE-FROM-FIGURE** | Precise exact decimal 0.612 is estimated; use `~0.61` |
| 19 | PDX1 lochNESS prediction correlation | $r = 0.88$ | `pertTF.pdf` | Fig. 2d | Scatter plot fit ~0.88 | **APPROXIMATE-FROM-FIGURE** | Use `r ~ 0.88` |
| 20 | TADA2B lochNESS prediction correlation | $r = 0.84$ | `pertTF.pdf` | Fig. 2d | Scatter plot fit ~0.84 | **APPROXIMATE-FROM-FIGURE** | Use `r ~ 0.84` |
| 21 | lochNESS composition ROC-AUC | 0.86 | `pertTF.pdf` | Fig. 2e | ROC curve area ~0.86 | **APPROXIMATE-FROM-FIGURE** | Use `AUC ~ 0.86` |
| 22 | Unseen context PDX1 Cosine Sim | 0.912 | `pertTF.pdf` | Fig. 3b | Bar plot y-axis ~0.91 | **APPROXIMATE-FROM-FIGURE** | Use `Cosine ~ 0.91` |
| 23 | Unseen context PDX1 PCC-delta | 0.724 | `pertTF.pdf` | Fig. 3b | Bar plot y-axis ~0.72 | **APPROXIMATE-FROM-FIGURE** | Use `PCC-delta ~ 0.72` |
| 24 | Unseen context DE-direction match | 84.6% | `pertTF.pdf` | Fig. 3b | Bar plot y-axis ~85% | **APPROXIMATE-FROM-FIGURE** | Use `~85%` |
| 25 | Leave-one-out 30-genotype mean Cosine | 0.864 | `pertTF.pdf` | Fig. 3c | Summary bar y-axis ~0.86 | **APPROXIMATE-FROM-FIGURE** | Use `mean Cosine ~ 0.86` |
| 26 | Leave-one-out scGPT mean Cosine | 0.698 | `pertTF.pdf` | Fig. 3c | Summary bar y-axis ~0.70 | **APPROXIMATE-FROM-FIGURE** | Use `mean Cosine ~ 0.70` |
| 27 | Joint unseen gene + context Cosine | 0.812 | `pertTF.pdf` | Fig. 3d | Bar plot y-axis ~0.81 | **APPROXIMATE-FROM-FIGURE** | Use `Cosine ~ 0.81` |
| 28 | CRISPRi CTNNB1 Cosine Sim | 0.892 | `pertTF.pdf` | Fig. 4b | Bar plot y-axis ~0.89 | **APPROXIMATE-FROM-FIGURE** | Use `Cosine ~ 0.89` |
| 29 | T2D PDX1-loss fold increase | 3.8-fold | `pertTF.pdf` | Fig. 5d | Bar ratio T2D (~0.30) vs ND (~0.08) | **APPROXIMATE-FROM-FIGURE** | Use `~3.8-fold (p < 0.0001)` |
| 30 | RFX6 siRNA classification accuracy | 78.4% | `pertTF.pdf` | Fig. 5g | Bar plot y-axis ~78% | **APPROXIMATE-FROM-FIGURE** | Use `~78% (vs <5% control)` |
| 31 | PS vs Energy Distance Spearman $
ho$ | +0.641026 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(ps_median, energy_distance)` | **TABLE-VERIFIED** | $p = 4.18 	imes 10^{-4}, n=26$ |
| 32 | PS vs Energy Distance Pearson $r$ | +0.762837 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.pearsonr(ps_median, energy_distance)` | **TABLE-VERIFIED** | $p = 5.87 	imes 10^{-6}, n=26$ |
| 33 | Energy Dist vs Positive lochNESS $
ho$ | +0.410296 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(energy_distance, lochness_pos)` | **TABLE-VERIFIED** | $p = 0.0129, n=36$ |
| 34 | Energy Dist vs Negative lochNESS $
ho$ | -0.141024 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(energy_distance, lochness_neg)` | **TABLE-VERIFIED** | $p = 0.4263, n=34$ (Decoupled) |
| 35 | Energy Dist vs Absolute lochNESS $
ho$ | +0.451223 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(energy_distance, lochness_abs)` | **TABLE-VERIFIED** | $p = 0.0057, n=36$ |
| 36 | PS vs Positive lochNESS $
ho$ | +0.061197 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(ps_median, lochness_pos)` | **TABLE-VERIFIED** | $p = 0.7665, n=26$ (Decoupled) |
| 37 | PS vs Negative lochNESS $
ho$ | -0.171538 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(ps_median, lochness_neg)` | **TABLE-VERIFIED** | $p = 0.4123, n=25$ (Decoupled) |
| 38 | PS vs Absolute lochNESS $
ho$ | +0.121368 | WIP `perturbation_summary.csv` | Cross-metric calculation | `stats.spearmanr(ps_median, lochness_abs)` | **TABLE-VERIFIED** | $p = 0.5548, n=26$ (Decoupled) |
| 39 | DistanceTest significant genotypes | 36 / 36 (100%) | WIP `distance_results.csv` | Column `significant` | `sum(df['significant']) == 36` | **TABLE-VERIFIED** | All 36 tested non-WT perturbations significant under DistanceTest; 1,000 permutations impose an empirical resolution floor of FDR = 0.000999 |
| 40 | PDX1het Energy Distance | 13.633665 | WIP `distance_results.csv` | Row 0 | `energy_distance = 13.633665, mmd = 0.312907` | **TABLE-VERIFIED** | **CORRECTION:** 13.63 is Energy Dist; 0.3129 is MMD |
| 41 | HHEXhet Energy Distance | 10.473210 | WIP `distance_results.csv` | Row 1 | `energy_distance = 10.473210, mmd = 0.230716` | **TABLE-VERIFIED** | **CORRECTION:** 10.47 is Energy Dist; 0.2307 is MMD |
| 42 | GATA6 Energy Distance | 9.704493 | WIP `distance_results.csv` | Row 2 | `energy_distance = 9.704493, mmd = 0.159007` | **TABLE-VERIFIED** | **CORRECTION:** 9.70 is Energy Dist; 0.1590 is MMD |
| 43 | KDM2B Energy Distance | 9.320417 | WIP `distance_results.csv` | Row 3 | `energy_distance = 9.320417, mmd = 0.208670` | **TABLE-VERIFIED** | **CORRECTION:** 9.32 is Energy Dist; 0.2087 is MMD |
| 44 | HHEX Energy Distance | 8.995473 | WIP `distance_results.csv` | Row 4 | `energy_distance = 8.995473, mmd = 0.203398` | **TABLE-VERIFIED** | **CORRECTION:** 9.00 is Energy Dist; 0.2034 is MMD |
| 45 | GLIS3 Energy Distance | 7.969341 | WIP `distance_results.csv` | Row 5 | `energy_distance = 7.969341, mmd = 0.185375` | **TABLE-VERIFIED** | **CORRECTION:** 7.97 is Energy Dist; 0.1854 is MMD |
| 46 | FOXA2 Energy Distance | 5.446592 | WIP `distance_results.csv` | Row 9 | `energy_distance = 5.446592, mmd = 0.106312` | **TABLE-VERIFIED** | **CORRECTION:** 5.45 is Energy Dist; 0.1063 is MMD |
| 47 | GLIS3 Median PS & Responder Frac | 0.750025, 66.6% | WIP `ps_score_summary.csv` | Row 0 | `ps_median = 0.750025, resp = 0.666310, n=935` | **TABLE-VERIFIED** | #1 highest PS in dataset |
| 48 | GATA6 Median PS & Responder Frac | 0.648252, 61.6% | WIP `ps_score_summary.csv` | Row 1 | `ps_median = 0.648252, resp = 0.616000, n=1500` | **TABLE-VERIFIED** | High penetrance |
| 49 | HHEX Median PS & Responder Frac | 0.658885, 59.8% | WIP `ps_score_summary.csv` | Row 2 | `ps_median = 0.658885, resp = 0.598023, n=1214` | **TABLE-VERIFIED** | High penetrance |
| 50 | FOXA2 Peak lochNESS & Liver Frac | 18.307343, 34.0% | WIP `lochness_summary.csv` | Row 4 | `peak = 18.307343, dom_ct = Liver, dom_loch = 13.740321` | **TABLE-VERIFIED** | **CORRECTION:** 18.31 is cell peak; 13.74 is celltype mean |
| 51 | GLIS3 Peak lochNESS & Frac | 25.563601, 64.5% | WIP `lochness_summary.csv` | Row 9 | `peak = 25.563601, dom_ct = ESC (not PDP), dom_loch = 13.625399` | **TABLE-VERIFIED** | **CORRECTION:** 25.56 is cell peak; 13.63 is celltype mean |
| 52 | DistanceSpace Coordinates Count | 36 genotypes | WIP `distance_space_coordinates.csv` | Total rows | `len(df) == 36` | **TABLE-VERIFIED** | 630 pairwise combinations |
| 53 | Phenotype Groups Count | 9 groups (PG1–PG9) | WIP `phenotype_groups.csv` | Column `phenotype_group` | `df['phenotype_group'].nunique() == 9` | **TABLE-VERIFIED** | DistanceSpace clusters |
| 54 | Co-functional Modules Count | 6 modules (M1–M6) | WIP `module_assignments.csv` | Column `module` | `df['module'].nunique() == 6` | **TABLE-VERIFIED** | Louvain regulatory modules |
| 55 | Core Gene Programs Count | 4 programs (P1–P4) | WIP `gene_programs.csv` | Column `program` | `df['program'].nunique() == 4` | **TABLE-VERIFIED** | cNMF functional programs |
| 56 | PS Skipped Genotypes Count | 10 genotypes | WIP `ps_score_skipped.csv` | Total rows | `len(df) == 10` | **TABLE-VERIFIED** | Het/enhancers/double KOs |
