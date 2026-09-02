# Diabetes Progenitor Study

**Quantitative decomposition of genetic perturbation phenotypes across human pancreatic differentiation**

| | |
|---|---|
| Dataset | `data/diabetes.h5ad` — 111,581 cells × 36,601 features |
| Analysis workflow | `workflows/diabetes_analysis.py` (4,456 lines), driven by `workflows/run_diabetes_analysis.slurm` |
| Supporting pipeline run | `config/diabetes.yaml` → `results/diabetes/` (generic 14-stage pipeline) |
| Result directory for this report | `results/diabetes_specific/` |
| Last successful workflow run | SLURM job 19816263, 2026-08-30, 13:22:20 → 13:43:59 (21 min, 48 CPUs) |
| Analysis code test status | `tests/test_diabetes_analysis.py` — 39/39 passing (re-verified while writing this report) |
| Report status | Reflects the current contents of `results/diabetes_specific/tables/` and `figures/` |

---

## Executive Summary

This study takes a 37-genotype human pluripotent stem cell (hPSC) pancreatic differentiation Perturb-seq experiment and asks a question that a purely predictive model does not answer directly: **what is the biological phenotype of each perturbation, quantitatively decomposed?**

Five orthogonal measurements were computed per perturbation and, where possible, per cell state:

1. **Per-cell perturbation response (PS score)** — how strongly each individual cell shows the perturbation-associated transcriptional signature.
2. **Global state displacement (energy distance vs WT + permutation DistanceTest)** — how far the perturbed population's distribution has moved in PCA space.
3. **Continuous state-space localization (lochNESS)** — where in the transcriptional manifold each perturbation's cells accumulate.
4. **Discrete cell-state composition shift (stratified Cochran–Mantel–Haenszel enrichment)** — which annotated developmental states gain or lose cells.
5. **Regulatory structure (co-functional perturbation modules M1–M6 × gene programs P1–P4, with Hallmark/Reactome/GO ORA)** — which downstream transcriptional programs explain the phenotype.

**Headline findings (all traceable to files listed in the Appendix):**

- **All 36 non-WT genotypes produce a statistically detectable global transcriptional phenotype** (energy distance vs WT, FDR = 9.99 × 10⁻⁴ for every genotype — the permutation floor at 1,000 permutations). Effect *size*, not p-value, is therefore the discriminating quantity; energy distance spans a 12.7-fold range (PDX1het 13.63 → MNX1 1.08).
- **Perturbation effects are strongly cell-state-specific.** Mean PS ranges from 0.13 in PP (pancreatic progenitor) cells to 0.57 in ESC across the whole screen, and individual genotypes concentrate their response in single states (e.g. NEUROD1 mean PS = 0.89 in SC-beta vs 0.34 screen-wide).
- **Compositional results reproduce known developmental biology.** FOXA2 loss diverts cells to Liver (34.0% of FOXA2 cells vs 1.8% of reference, log₂OR = 4.28); GATA6 loss diverts to Endothelial (25.7% vs 0.95%, log₂OR = 6.31); NEUROG3 loss abolishes SC-beta (0.00% vs 2.92%, log₂OR = −6.54) while accumulating PDP/PP progenitors; PDX1 and PAX6 loss both redirect endocrine output toward SC-EC with SC-beta depletion.
- **The metrics are complementary, not redundant.** Energy distance vs PS median: Spearman ρ = 0.641 (n = 26); energy distance vs mean positive lochNESS: ρ = 0.410 (n = 36); PS median vs mean positive lochNESS: ρ = 0.061 (n = 26, not significant). No single number captures the phenotype.
- **Two hard analytical constraints must be stated up front.** (i) PS could only be computed for 26/36 genotypes — 10 genotypes whose labels are not literal gene symbols in the expression matrix (`PDX1het`, `GATA6het`, `HHEXe`, `ONECUT1e`, `QSER1TET1`, `TET1/2/3`, …) were skipped. (ii) The lochNESS implementation used here scores **only each cell's own genotype** (`lochness_self`), so it can measure enrichment but is structurally near-blind to depletion — depletion must be read from the compositional enrichment analysis instead.

Nothing in this report establishes mechanism. Observations, interpretations, and hypotheses are labelled separately throughout.

---

## 1. Biological Motivation

Directed differentiation of hPSCs into pancreatic islet-like cells passes through a stereotyped sequence of states: pluripotent (ESC) → definitive endoderm (DE) → posterior foregut (PFG) → pancreatic progenitor (PP) → pancreatic/endocrine progenitor (PDP, EnP) → hormone-expressing SC-beta, SC-alpha, SC-delta and SC-EC (enterochromaffin-like) cells. Off-target fates — Liver, Stromal, Endothelial — mark failures of lineage restriction.

Monogenic diabetes genes act at defined points in this sequence, and the same gene can be dispensable at one stage and essential at another. A perturbation screen across this axis therefore has a property most Perturb-seq screens lack: **the read-out is developmental fate, not just a shifted expression vector.** The scientifically useful questions are consequently positional and quantitative:

- Does perturbing gene *X* produce a response at all, and in what fraction of cells?
- At which developmental stage / cell state does the response appear?
- Does the perturbation move cells *out* of the intended lineage and, if so, *into what*?
- Do different genes converge on the same alternate fate, implying shared regulatory logic?

The analyses in `results/diabetes_specific/` were built to answer exactly these.

---

## 2. Relationship to pertTF

pertTF (Su, Liu, Menon et al.) demonstrates that perturbation responses in this system can be *learned and predicted* — including generalization to withheld genotypes and cell contexts, and transfer to primary islet data. That is a modelling result about predictability.

This work is the biological complement, not a competitor:

| Question | Answered by |
|---|---|
| "What is likely to happen after perturbing gene *X*?" | pertTF (predictive model) |
| "How strong is the response, in how many cells?" | PS score (this work) |
| "Where in the differentiation manifold does it occur?" | lochNESS + CMH cell-state enrichment (this work) |
| "How far has the population moved from WT?" | Energy distance / DistanceTest (this work) |
| "Do different perturbations move cells in the same direction?" | DistanceSpace / PCoA / phenotype groups (this work) |
| "Which molecular programs underlie the phenotype?" | Co-functional modules × gene programs + pathway ORA (this work) |

The workflow deliberately reuses pertTF's own lochNESS definition — the pipeline module `src/perturbseq_pipeline/lochness.py` states in its docstring that the score is *"ported from pertTF (`perttf.model.composition_change_analysis`)"* — so the two analyses are measuring the same quantity on the same manifold.

**What prediction-only framing leaves open (as observed in this project, not as a general claim):** a predicted expression vector for a genotype does not by itself report the *fraction of cells that responded* (here 1.5%–66.6% "responder fraction" across genotypes), the *state in which the response is concentrated*, or the *magnitude of the population displacement*. Those quantities are what the analyses below supply.

---

## 3. Dataset and Developmental Context

**Source object:** `../data/diabetes.h5ad` (Seurat-derived; `layers['GPTin']`, `obsm['X_umap']` present, **no** `X_pca` — PCA is recomputed by the workflow).

| Property | Value | Source |
|---|---|---|
| Cells | 111,581 | workflow validation log |
| Features | 36,601 | workflow validation log |
| Genotypes | 37 (WT + 36 perturbations) | `adata.obs['genotype']` |
| WT control cells | 32,693 | workflow validation log |
| Non-WT cells | 78,888 | `perturbation_summary.csv` |
| sgRNA constructs | 100 | `adata.obs['sgrna']` |
| Curated cell states (`celltype_2`) | 15 | workflow validation log |
| Samples (`orig.ident`) | 13 | `adata.obs['orig.ident']` |

**Cell states and their sizes** (whole dataset, `celltype_2`):

| State | Cells | | State | Cells |
|---|---|---|---|---|
| ESC | 21,027 | | SC-alpha | 4,732 |
| DE | 18,361 | | Stromal | 4,369 |
| PFG | 17,145 | | SC-beta | 3,799 |
| PP | 13,388 | | EnP | 3,620 |
| PDP | 9,178 | | Liver | 3,416 |
| SC-EC | 8,785 | | PGT | 1,733 |
| | | | Endothelial | 1,157 |
| | | | SC-delta | 740 |
| | | | ESC (D3) | 131 |

**Sample → developmental stage mapping** (hard-coded in `diabetes_analysis.py::STAGE_MAPPING`):

`Sample_A..F_WT → WT`; `Sample_G_1/G_2_ESC → ESC`; `Sample_H_DE → DE`; `Sample_I_PFG → PFG`; `Sample_J_PP → PP`; `Sample_L_1/L_2_3DEC → 3DEC`.

**A design fact that constrains every downstream comparison.** Perturbed cells exist *only* in the seven staged samples (G, H, I, J, L₁, L₂ — 78,888 cells). The six WT-only samples (A–F) contribute 24,408 of the 32,693 WT cells; the remaining 8,285 WT cells are co-embedded within the staged perturbation samples. Any WT-referenced comparison therefore mixes a within-sample and a between-sample contrast. This is why the workflow stratifies the compositional test by `orig.ident` (see §5 and §7).

**Genotype label heterogeneity.** The 36 perturbations are a mixture of homozygous nulls (`PDX1`, `FOXA2`, `RFX6`, …), heterozygous alleles (`PDX1het`, `GATA6het`, `GATA4het`, `HNF4Ahet`, `HHEXhet`, `NANOGe-het`), enhancer alleles (`HHEXe`, `ONECUT1e`), and compound genotypes (`QSER1TET1`, `TET1/2/3`). This is biologically valuable — `PDX1` vs `PDX1het` is a built-in dosage series — but it breaks any analysis that must map a genotype label to a gene in the expression matrix (§5, §6).

![Cell-state atlas](./figures/01_umap_celltype2.png)

**Figure 1. Differentiation atlas coloured by curated cell state.**
UMAP of all 111,581 cells (embedding carried over from the source object), each point coloured by `celltype_2`, ordered along the pancreatic differentiation progression (ESC → DE → PFG → PP → PDP/EnP → SC-EC/alpha/beta/delta) with off-target Liver, Stromal and Endothelial states shown separately. Source: `_fig01_umap_celltype2`.

**Biological interpretation.** The manifold recapitulates the intended stepwise differentiation with clearly separated terminal endocrine subtypes and distinct off-lineage compartments. This separation is what makes cell-state-resolved perturbation scoring meaningful: "which state" is a well-posed question on this embedding.

![Stage composition](./figures/03_stage_celltype_composition.png)

**Figure 2. Cell-state composition across developmental stages.**
Stacked bars give the proportion of each `celltype_2` state within each derived `development_stage` (normalized per stage; `pd.crosstab(..., normalize='index')`). Source: `_fig03_stage_celltype_composition`.

**Biological interpretation.** Stage and state are strongly but not perfectly coupled — each staged sample is dominated by its nominal state but contains cells that have run ahead or lagged behind. **Interpretation:** stage-level and state-level analyses therefore carry partially independent information, which is why the workflow reports both (`ps_by_development_stage.csv` and `ps_by_celltype2.csv`).

---

## 4. Analysis Workflow

`workflows/diabetes_analysis.py` is a standalone orchestration script. It does **not** reimplement statistics; it imports the validated algorithm modules from `src/perturbseq_pipeline/` (`ps_score`, `lochness`, `distance`, `enrichment`, `modules`, `gene_sets`) and configures them for this dataset. Execution order (`run_diabetes_workflow`):

1. Load h5ad, validate required obs columns (`genotype`, `sgrna`, `celltype_2`, `orig.ident`).
2. `prepare_diabetes_anndata`: derive `development_stage`; map `genotype == "WT"` → internal control class, all others → targeting class; set `target_gene = genotype`; **compute PCA (3,000 HVGs, 50 PCs, no batch correction)** because the source object lacks `X_pca`.
3. PS scoring (`pertps` 0.1.0) → 5 tables.
4. lochNESS in `X_pca` → 6 tables.
5. Energy distance + permutation DistanceTest vs WT → 2 tables.
6. DistanceSpace (pairwise, PCoA, phenotype groups) → 4 tables.
7. Cell-state enrichment, CMH-stratified by `orig.ident` → 1 table.
8. Co-functional modules and gene programs + pathway ORA → 6 tables.
9. Master merge → `perturbation_summary.csv`.
10. Lean h5ad export (`diabetes_analysis.h5ad`, 949 MB: X + 9 obs columns + `X_pca`/`X_umap`).
11. 28 primary figures + 102 per-genotype UMAP panels.

Every table is written immediately after its stage, and a `--recover` / `--plot-only` mode can rebuild all figures from the checkpointed tables without re-running the analysis (`recover_and_finish_diabetes_run`).

**Key parameters actually used** (from `run_diabetes_analysis.slurm` and the argparse defaults):

| Parameter | Value |
|---|---|
| `--seed` | 123 |
| `--min-cells` (per perturbation, all stages) | 10 |
| `--max-cells-per-target` (Distance / DistanceSpace) | 2,000 |
| `--max-control-cells` (DistanceTest) | 5,000 |
| `--n-permutations` | 1,000 |
| `--n-modules` / `--n-programs` | 6 / 4 |
| HVGs / PCs | 3,000 / 50 |
| Distance representation | `X_pca`, metric `edistance` |
| lochNESS neighbours / representation | `n_neighbors = 300`, `X_pca` (50 PCs) |
| Batch correction | **None** (`cluster.batch_key = None`, deliberate: samples are genuine differentiation stages) |
| FDR threshold | 0.05 (Benjamini–Hochberg) throughout |

A parallel run of the *generic* 14-stage pipeline (`config/diabetes.yaml` → `results/diabetes/`) supplies the guide-level knockdown QC used in §5. In that configuration lochNESS is explicitly disabled, with the reason documented in the config: the genotype label `TET1/2/3` produced an HDF5-unsafe obs column name (`lochness_TET1/2/3`) that crashed the writer. The dedicated workflow solves this (`sanitize_identifier`, and a lean h5ad that retains only `lochness_self`), so **lochNESS results in this report come from `results/diabetes_specific/`, not from `results/diabetes/`.**

---

## 5. Data Quality and Perturbation QC

QC matters here for a specific reason: an apparent genotype-specific difference can be manufactured by sequencing depth, RNA complexity, small cell numbers, sample-of-origin composition, or simply by the perturbation not having worked. Each is checked below.

### 5.1 Cell-level QC (upstream, inherited)

The source object has already been filtered upstream; `config/diabetes.yaml` therefore sets every QC threshold to `null` and imposes no further filtering.

| Metric | Mean | Median | Min | Max |
|---|---|---|---|---|
| `nCount_RNA` (UMIs) | 8,644 | 7,729 | 255 | 31,966 |
| `nFeature_RNA` (genes) | 3,569 | 3,449 | 202 | 7,498 |
| `percent.mt` | 3.17% | 2.77% | 0.00% | 10.00% |
| `nCount_sgRNA` | 111.9 | 82 | 10 | 2,197 |
| `nFeature_sgRNA` | **1.0 for every cell** | 1 | 1 | 1 |

**Observation.** The hard ceiling at `percent.mt` = 10.00% and floor at `nCount_sgRNA` = 10 are signatures of upstream filtering. Every cell carries exactly one sgRNA, so guide multiplets have already been removed and no multiplet gate is needed here.

**Per-sample depth** (median UMIs / median genes / median %mt):

| Sample | UMIs | Genes | %mt | Cells |
|---|---|---|---|---|
| Sample_A_WT | 9,923 | 4,154 | 2.0 | 2,463 |
| Sample_B_WT | 7,334 | 3,530 | 3.6 | 9,869 |
| Sample_C_WT | 9,027 | 3,879 | 2.0 | 2,492 |
| Sample_D_WT | 6,864 | 3,318 | 2.3 | 3,155 |
| Sample_E_WT | 9,985 | 4,201 | 2.0 | 2,767 |
| Sample_F_WT | 6,735 | 3,265 | 2.2 | 3,662 |
| Sample_G_1_ESC | 10,241 | 3,889 | 4.4 | 6,528 |
| Sample_G_2_ESC | 7,382 | 3,190 | 4.3 | 9,332 |
| Sample_H_DE | 7,393 | 3,420 | 2.0 | 18,120 |
| Sample_I_PFG | 6,408 | 2,900 | 1.7 | 17,664 |
| Sample_J_PP | 7,284 | 3,396 | 1.7 | 10,386 |
| Sample_L_1_3DEC | 9,053 | 3,791 | 4.3 | 12,343 |
| Sample_L_2_3DEC | 7,666 | 3,378 | 4.4 | 12,800 |

**Observation.** Median depth varies ~1.6-fold across samples (6,408–10,241 UMIs) and %mt varies ~2.6-fold (1.7–4.4%). Because genotypes are distributed across the staged samples, depth is partially confounded with stage. No batch correction was applied (a deliberate choice — samples *are* stages), so **stage-level PS or lochNESS differences must not be read as purely biological without this caveat.**

### 5.2 Perturbation representation

Non-WT genotype cell counts span 182 (KDM2B) to 6,451 (MNX1) — a 35-fold range. All 36 genotypes clear the `min_cells = 10` threshold used by every stage, so **no genotype was excluded for low cell count.**

**This range is not neutral.** Across the 36 genotypes, cell number is *negatively* rank-correlated with all three effect metrics:

| Correlation with `n_cells` | Spearman ρ | p | n |
|---|---|---|---|
| Energy distance | −0.448 | 6.2 × 10⁻³ | 36 |
| Mean absolute lochNESS | −0.383 | 2.1 × 10⁻² | 36 |
| PS mean | −0.460 | 1.8 × 10⁻² | 26 |

**Interpretation (important, and it cuts both ways).** Two non-exclusive explanations exist. (i) *Statistical:* the energy-distance estimator is upward-biased at small sample size, and lochNESS is a ratio to a genotype's global frequency (`local_fraction / overall_fraction − 1`), whose attainable maximum grows as the genotype becomes rarer — so rare genotypes are mechanically advantaged on both scales. (ii) *Biological:* severe perturbations kill or arrest cells and are therefore under-represented at harvest, so small *n* is itself a phenotype. **Both are probably operating here.** The three top-distance genotypes (PDX1het n = 469, HHEXhet n = 328, KDM2B n = 182) are exactly the ones where this ambiguity is sharpest, and their rankings should be treated as provisional pending a cell-number-matched re-analysis (§16).

### 5.3 Perturbation efficiency (does the genotype actually reduce its own transcript?)

From the generic pipeline run (`results/diabetes/tables/perturbation.csv`; target log₂FC vs WT with KS test, "Effective" requires log₂FC < 0 and KS FDR < 0.05):

**Only 13 of 26 testable targets show significant down-regulation of their own transcript.**

| Effective (log₂FC < 0, FDR < 0.05) | log₂FC | % knockdown |
|---|---|---|
| GLIS3 | −1.95 | 74.1 |
| NEUROG3 | −1.80 | 71.2 |
| ARX | −1.16 | 55.3 |
| GATA6 | −1.11 | 53.7 |
| PROSER1 | −0.84 | 44.3 |
| NKX2-2 | −0.74 | 40.1 |
| HNF4A | −0.72 | 39.5 |
| PDX1 | −0.69 | 37.9 |
| HHEX | −0.63 | 35.2 |
| OTUD5 | −0.52 | 30.3 |
| RFX6 | −0.45 | 26.8 |
| GATA4 | −0.40 | 24.4 |
| PBX1 | −0.37 | 22.3 |

| Not "effective" | log₂FC | Note |
|---|---|---|
| TADA2B, PAX6 | −0.36, −0.27 | Down but KS FDR ≥ 0.05 |
| TET1, QSER1, BMPR1A, FOXA1, TLE3, NEUROD1, KDM2B | +0.11 … +0.29 | Target transcript *up* |
| FOXA2 | +0.49 | Target transcript up, highly significant |
| MNX1 | +0.59 | " |
| BCOR | +0.75 | " |
| GSC | +1.79 | Largest increase in the screen |

**Observation.** For 13/26 genotypes the target transcript is not reduced, and for 10 it is significantly *increased*.

**Interpretation.** These are **engineered mutant lines, not CRISPRi knockdowns.** A frameshift or a heterozygous/enhancer allele need not reduce steady-state mRNA at all; loss of a transcription factor that autorepresses, or that is normally restricted to a lineage the mutant cells now over-occupy, can raise the measured transcript. FOXA2 is the clearest example: FOXA2-mutant cells are 34% Liver (§7), a compartment with high *FOXA2* expression, so the population-level increase is at least partly a composition effect, not evidence that the allele is inert.

**Consequence for reading this report.** "% knockdown" is **not** a validity filter for these genotypes. It is reported for transparency; downstream interpretation rests on the phenotype metrics (distance, lochNESS, composition), all of which are agnostic to target-transcript direction.

### 5.4 Genotype × cell-state sparsity and masking

- Observed genotype × cell-state combinations with ≥1 cell: **505 of a possible 540** (36 × 15).
- Combinations with **≥10 cells** (the masking threshold): **362 / 540** for lochNESS.
- For PS, only the 26 scored genotypes contribute: 370 observed combinations, of which **271 have ≥10 PS-valid cells.**

The threshold is applied in `compute_ps_by_genotype_celltype(min_cells=10)` and `compute_lochness_by_celltype(min_cells=10)`; masked cells are rendered grey (`cmap.set_bad("#edf2f7")`) in Figures 6 and 7 below, and are **NaN, not zero**, in the corresponding CSVs.

**Why this matters biologically.** A perturbation that eliminates a state produces *few or no cells* in that state. Masking correctly prevents an unstable mean from being drawn, but it also means **the strongest fate phenotypes are invisible on the PS and lochNESS heatmaps** — they appear as grey cells. NEUROG3 has zero SC-beta cells; that is the phenotype, and it is only recoverable from the compositional analysis (§7).

### 5.5 PS coverage gap

`ps_score_skipped.csv` — 10 genotypes, all with reason **"target gene not in the expression matrix"**:

`GATA4het` (1,957), `GATA6het` (2,266), `HHEXe` (1,487), `HHEXhet` (328), `HNF4Ahet` (829), `NANOGe-het` (996), `ONECUT1e` (2,436), `PDX1het` (469), `QSER1TET1` (1,157), `TET1/2/3` (948) — **12,873 cells, 16.3% of all perturbed cells.**

**Observation.** PS requires the *target gene symbol* to resolve to a row of the expression matrix in order to classify cells into the successful-knockdown / escaper / non-responder / low-signal quadrants. Non-canonical labels do not resolve.

**Consequence.** All PS-based statements in this report cover **26 genotypes / 66,015 perturbed cells**, whereas distance, lochNESS and compositional statements cover **all 36 genotypes / 78,888 cells**. Any genotype ranking that mixes the two must state which. In particular, `PDX1het` — the largest energy distance in the screen — has **no PS value at all**.

---

## 6. Quantifying Cellular Perturbation Response

### 6.1 Did the perturbation produce a measurable cellular response?

**Method (as implemented).** `compute_perturbation_distance` (`src/perturbseq_pipeline/distance.py`) takes each genotype's cells and the WT population in `X_pca` (50 dims), samples up to 2,000 target cells and 5,000 WT cells with a fixed seed, computes the **energy distance**

> E = 2·mean‖x−y‖ − mean‖x−x′‖ − mean‖y−y′‖

and tests it by permuting the target/control labels 1,000 times, giving the exact finite-permutation p-value `p = (1 + #{perm ≥ obs}) / (1 + n_perm)`, followed by Benjamini–Hochberg FDR. MMD is computed as a secondary statistic.

**Biological question answered.** Has the whole distribution of perturbed cells moved away from the unperturbed distribution — regardless of which genes changed?

**Result — `tables/distance_results.csv`, 36/36 genotypes.**

| Rank | Genotype | n cells | Energy distance | MMD | FDR |
|---|---|---|---|---|---|
| 1 | PDX1het | 469 | 13.63 | 0.313 | 9.99e-4 |
| 2 | HHEXhet | 328 | 10.47 | 0.231 | 9.99e-4 |
| 3 | GATA6 | 1,500 | 9.70 | 0.159 | 9.99e-4 |
| 4 | KDM2B | 182 | 9.32 | 0.209 | 9.99e-4 |
| 5 | HHEX | 1,214 | 9.00 | 0.203 | 9.99e-4 |
| 6 | GLIS3 | 935 | 7.97 | 0.185 | 9.99e-4 |
| 7 | GSC | 1,652 | 5.88 | 0.126 | 9.99e-4 |
| 8 | QSER1TET1 | 1,157 | 5.64 | 0.126 | 9.99e-4 |
| 9 | HHEXe | 1,487 | 5.62 | 0.123 | 9.99e-4 |
| 10 | FOXA2 | 4,896 | 5.45 | 0.106 | 9.99e-4 |
| … | | | | | |
| 19 | RFX6 | 3,331 | 2.45 | 0.056 | 9.99e-4 |
| 20 | NEUROG3 | 1,543 | 2.40 | 0.050 | 9.99e-4 |
| 21 | PDX1 | 6,207 | 2.23 | 0.051 | 9.99e-4 |
| 33 | NEUROD1 | 2,728 | 1.42 | 0.032 | 9.99e-4 |
| 35 | PAX6 | 3,237 | 1.15 | 0.026 | 9.99e-4 |
| 36 | MNX1 | 6,451 | 1.08 | 0.023 | 9.99e-4 |

**Observation.** Every one of the 36 genotypes is significant, and every FDR equals 9.99 × 10⁻⁴ — the smallest value attainable with 1,000 permutations (1/1001). **The p-values are therefore saturated and carry no ranking information.** Only the effect size is informative.

**Interpretation.** In a screen this deeply sampled (median ≈ 1,500 cells/genotype), even modest phenotypes are trivially detectable. The scientifically meaningful statement is the 12.7-fold spread in effect magnitude, not the uniform significance. **Hypothesis:** raising `n_permutations` would not change the ranking; a bootstrap confidence interval on the energy distance would be more informative than a permutation p-value here (§16).

![Energy distance ranking](./figures/06_energy_distance_by_perturbation.png)

**Figure 3. Global transcriptomic displacement from WT.**
Horizontal bars, one per genotype, giving the energy distance between that genotype's cells and WT cells in 50-dimensional PCA space. Green = significant at FDR < 0.05 (all 36); grey = not significant (none). Source: `_fig06_energy_distance_by_perturbation`, from `distance_results.csv`.

**Biological interpretation.** The ranking is led by heterozygous and enhancer alleles of early-acting factors (PDX1het, HHEXhet, HHEX, HHEXe) and by early endoderm gatekeepers (GATA6, GLIS3, GSC, FOXA2), while late endocrine factors (NEUROD1, PAX6, MNX1) sit at the bottom. **Interpretation:** the axis being measured is at least partly *how early in differentiation the perturbation acts* — an early block propagates through every subsequent state and therefore displaces the entire population, whereas a late factor only reshapes the terminal compartment, which is a small fraction of cells. **Caveat:** this ordering is also correlated with cell number (§5.2) and must not be read as a pure severity ranking.

### 6.2 How strong was the response, and was it consistent across cells?

**Method (as implemented).** `compute_ps_scores` delegates to `pertps` 0.1.0 (the lab's PS_python, a scMAGeCK-style perturbation score). For each target it compares target cells with control cells, learns a transcriptional perturbation signature from the top 100 biomarkers, and projects each cell onto it to yield **PS ∈ [0, 1]** — 0 = control-like, 1 = fully perturbed. Combining PS with the target gene's own expression (cut at the control mean) assigns each cell to one of four quadrants: *successful knockdown* (high PS, low target), *escaper* (high PS, high target), *non-responder* (low PS, high target), *low signal* (low PS, low target). `ps_threshold = 0.5`.

**Biological question answered.** What fraction of cells actually responded, and how uniformly? This is *penetrance*, which a population-average measurement cannot see.

**Result — `tables/ps_score_summary.csv`, 26 genotypes.** Per-cell quadrant assignments across all 66,015 scored cells: successful knockdown 20,949; low signal 27,644; non-responder 10,674; escaper 6,748.

| Genotype | n cells | Mean PS | Median PS | Responder fraction | % escaper |
|---|---|---|---|---|---|
| GLIS3 | 935 | 0.607 | 0.750 | 66.6% | 1.1% |
| GATA6 | 1,500 | 0.578 | 0.648 | 61.6% | 11.5% |
| HHEX | 1,214 | 0.605 | 0.659 | 59.8% | 8.5% |
| GSC | 1,652 | 0.539 | 0.607 | 54.8% | 6.0% |
| GATA4 | 1,612 | 0.534 | 0.622 | 48.7% | 13.4% |
| KDM2B | 182 | 0.627 | 0.681 | 47.8% | 25.8% |
| HNF4A | 987 | 0.421 | 0.458 | 42.0% | 2.8% |
| MNX1 | 6,451 | 0.403 | 0.467 | 41.1% | 5.4% |
| RFX6 | 3,331 | 0.405 | 0.451 | 31.0% | 8.8% |
| PDX1 | 6,207 | 0.378 | 0.378 | 29.1% | 12.2% |
| NEUROG3 | 1,543 | 0.399 | 0.440 | 35.7% | 0.6% |
| TLE3 | 3,259 | 0.387 | 0.164 | 26.4% | 12.3% |
| QSER1 | 1,232 | 0.474 | 0.535 | 22.8% | 30.0% |
| BMPR1A | 925 | 0.497 | 0.538 | 21.7% | 33.6% |
| PAX6 | 3,237 | 0.337 | 0.168 | 18.6% | 11.9% |
| TET1 | 1,370 | 0.390 | 0.394 | 19.8% | 23.0% |
| FOXA2 | 4,896 | 0.399 | 0.331 | **5.7%** | 28.1% |
| NEUROD1 | 2,728 | 0.339 | 0.268 | **1.5%** | 21.7% |

*(Full 26-row table in `ps_score_summary.csv`.)*

**Observation.** Responder fraction spans 1.5% (NEUROD1) to 66.6% (GLIS3) — a 44-fold range — and is **not** a monotone function of mean PS. FOXA2 has a respectable mean PS of 0.399 but a responder fraction of 5.7% and an escaper fraction of 28.1%.

**Critical caveat.** The "responder fraction" column is `pct_successful_kd`, which by construction requires **high PS *and* low target-gene expression**. For genotypes whose target transcript is not reduced (§5.3 — FOXA2, NEUROD1, MNX1, BCOR, GSC, …), cells with a genuine transcriptional response are classified as *escapers*, not responders. **The low responder fractions for FOXA2 and NEUROD1 are therefore an artefact of the quadrant definition applied to mutant (not knockdown) lines, not evidence of a weak phenotype.** Both genotypes have unambiguous compositional phenotypes (§7). Mean/median PS and the escaper+responder sum are the safer summaries for this dataset.

![PS by perturbation](./figures/05_ps_by_perturbation.png)

**Figure 4. Per-cell perturbation response strength and penetrance.**
Left: median PS per genotype (native 0–1 scale; dashed red line = active threshold 0.5). Right: responder fraction (% of cells classified *successful knockdown*). 26 genotypes; the 10 PS-skipped genotypes are absent. Source: `_fig05_ps_by_perturbation`.

**Biological interpretation.** No genotype reaches median PS ≥ 0.5 except GLIS3 (0.750), GATA6 (0.648), HHEX (0.659), KDM2B (0.681), GATA4 (0.622), GSC (0.607), BMPR1A (0.538) and QSER1 (0.535). **Observation:** the perturbation response is heterogeneous within essentially every genotype — most perturbed populations are a mixture of strongly responding and near-control cells. **Interpretation:** in a differentiation system this is expected, because a cell's capacity to respond depends on whether it has reached the stage at which the gene is required. §7 shows this directly.

---

## 7. Cell-State-Specific Perturbation Effects

### 7.1 In which developmental cell states is the response strongest?

**Result — `tables/ps_by_celltype2.csv`** (non-WT cells with a valid PS, pooled across the 26 scored genotypes):

| Cell state | n | Mean PS | Median PS | | Cell state | n | Mean PS | Median PS |
|---|---|---|---|---|---|---|---|---|
| ESC | 13,463 | 0.568 | 0.642 | | SC-EC | 5,377 | 0.460 | 0.487 |
| ESC (D3) | 110 | 0.569 | 0.653 | | SC-alpha | 2,879 | 0.371 | 0.226 |
| DE | 11,528 | 0.450 | 0.485 | | SC-beta | 1,928 | 0.402 | 0.107 |
| PFG | 10,907 | 0.349 | 0.366 | | SC-delta | 369 | 0.180 | 0.000 |
| PGT | 134 | 0.370 | 0.402 | | Liver | 2,726 | 0.549 | 0.607 |
| PP | **5,331** | **0.134** | **0.065** | | Stromal | 3,474 | 0.389 | 0.372 |
| PDP | 5,633 | 0.353 | 0.357 | | Endothelial | 1,040 | 0.311 | 0.302 |
| EnP | 1,116 | 0.228 | 0.022 | | | | | |

And by derived stage (`ps_by_development_stage.csv`): ESC 0.573 → DE 0.467 → PFG 0.419 → **PP 0.153** → 3DEC 0.387.

**Observation.** Response strength is highest in ESC and in the off-lineage Liver compartment, and reaches a pronounced minimum in **PP** (mean PS 0.134, median 0.065) and **EnP** (median 0.022) — the pancreatic-progenitor and endocrine-progenitor states sitting in the middle of the trajectory.

**Interpretation.** Two readings are consistent with the data and cannot be separated by this analysis alone. (i) *Biological:* the PP state is a transcriptionally canalized bottleneck — cells either reach it in a near-normal configuration or never arrive, so surviving PP cells look control-like. (ii) *Technical:* PS is defined relative to a WT reference pooled across all states; if the PP compartment is transcriptionally tight, the learned perturbation signature may simply project weakly there. **Hypothesis (testable):** re-deriving PS with a state-matched WT reference would distinguish these; if reading (i) is right, PP would remain low.

**Interpretation of the ESC maximum.** High PS in ESC is partly attributable to the two dedicated ESC-stage samples (G_1/G_2), which contribute 15,006 perturbed cells at a point where all genotypes are still present, and to baseline transcriptional differences between mutant hPSC lines. It should not be read as "these genes act mainly in the pluripotent state" without a line-effect control.

![PS by cell state](./figures/23_ps_by_celltype2.png)

**Figure 5. Perturbation response strength by cell state.**
Distribution of per-cell PS within each `celltype_2`, pooled over the 26 scored genotypes and ordered along the differentiation progression. Source: `_fig23_ps_by_celltype2`.

**Biological interpretation.** The response profile is non-monotone along the trajectory: high at the start (ESC/DE), collapsing at PP/EnP, then rising again in the terminal endocrine and off-lineage states. **Interpretation:** perturbation consequences are expressed at two distinct points — early lineage specification and terminal fate assignment — with a comparatively refractory progenitor window between them.

### 7.2 Which perturbation is strongest in which state?

**Result — `tables/ps_by_genotype_celltype.csv`** (masked at n < 10). Selected maxima:

| Genotype | Peak state | n | Mean PS in state | Screen-wide mean PS |
|---|---|---|---|---|
| NEUROD1 | **SC-beta** | 464 | **0.889** | 0.339 |
| PDX1 | **SC-EC** | 1,576 | **0.833** | 0.378 |
| GLIS3 | ESC | 603 | 0.792 | 0.607 |
| GATA6 | ESC (D3) / ESC | 14 / 517 | 0.756 / 0.698 | 0.578 |
| PDX1 | SC-beta | 65 | 0.722 | — |
| NEUROD1 | SC-alpha | 138 | 0.670 | — |
| FOXA2 | **Liver** | 1,667 | **0.661** | 0.399 |
| RFX6 | ESC | 776 | 0.572 | 0.405 |
| NEUROG3 | ESC | 303 | 0.544 | 0.399 |

**Observation.** For several genotypes the state-resolved PS is 2–3× the genotype-wide average, and the peak state is biologically specific: NEUROD1 → SC-beta, PDX1 → SC-EC, FOXA2 → Liver.

**Interpretation.** This is the clearest demonstration in the study that a single per-genotype number under-describes the phenotype. **A genotype-level mean PS of 0.339 for NEUROD1 conceals a mean PS of 0.889 in the 464 SC-beta cells where the factor actually acts.** Averaging over states dilutes the signal by the fraction of cells that are in the wrong state to respond.

![PS genotype × cell state](./figures/24_ps_genotype_celltype_heatmap.png)

**Figure 6. Genotype × cell-state perturbation response strength.**
Heatmap of mean PS (viridis, fixed 0–1 scale) for each genotype (rows, 36; the 10 PS-skipped genotypes appear as fully grey rows) × cell state (columns, ordered along differentiation). Grey = fewer than 10 PS-valid cells in that combination. Source: `_fig24_ps_genotype_celltype_heatmap`, from the masked pivot of `ps_by_genotype_celltype.csv`.

**Biological interpretation.** The heatmap is sparse by design and the sparsity is informative: extensive grey in the terminal endocrine columns for early-acting genotypes (GATA6, GLIS3, GSC) reflects those genotypes barely reaching the endocrine compartment at all. The bright, focal cells — NEUROD1 in SC-beta, PDX1 in SC-EC, FOXA2 in Liver — mark stage-restricted responses. **Caveat:** grey means "unmeasurable", not "no effect"; the two are distinguished only in §7.3.

### 7.3 Which developmental fates are actually gained or lost?

**Method (as implemented).** `test_cluster_enrichment` builds, for each (genotype, cell state) pair, a 2 × 2 contingency table of in-state vs elsewhere, target vs reference. Because `enrichment.stratify_by = "orig.ident"`, a **Cochran–Mantel–Haenszel test stratified by sample** replaces the pooled Fisher test, and the reported odds ratio is the CMH pooled OR (Haldane–Anscombe corrected). Benjamini–Hochberg FDR is applied within each reference. Two references are computed: `ntc` (= WT) and `other` (= all other perturbed cells).

**Two implementation facts that must be stated to read the results correctly:**

1. **The `significant` flag applies only to the `other` reference.** In `enrichment.py`, `significant = (fdr < alpha) & (control == primary_control)`, and this workflow uses the `Config()` default `primary_control = "other"` (it does *not* set `enrichment.controls`/`primary_control`, unlike `config/diabetes.yaml` which sets `ntc`). Consequently `celltype_enrichment.csv` contains **313 significant rows, all with `control == "other"`, and 0 with `control == "ntc"`** — the WT-referenced odds ratios are computed and stored but are never flagged. The comparison being made is therefore *"is this genotype over/under-represented in this state relative to the pooled other perturbations in the same samples"*, which is a well-controlled within-sample contrast, but it is **not** a comparison to WT.
2. **The `direction` column and the sign of `log2_odds_ratio` can disagree.** `direction` is derived from raw pooled percentages (`pct_of_target > pct_of_reference`), whereas `log2_odds_ratio` is the sample-*stratified* CMH estimate. Where they conflict (e.g. GATA6/DE: 21.8% vs 18.2% but log₂OR = −1.54), the stratified odds ratio is the one to trust; the disagreement is a Simpson's-paradox signature of stage composition differing between samples. **This is a labelling inconsistency in the current output and should be fixed (§15).**

**Result — `tables/celltype_enrichment.csv`, `control == "other"`, FDR < 0.05:**

| Genotype | State gained (log₂OR) | State lost (log₂OR) |
|---|---|---|
| **GATA6** | Endothelial +6.31 (25.7% vs 0.95%), ESC +1.31 | SC-EC −4.27, SC-alpha −4.14, EnP −3.34, PP −2.99, PFG −2.90, Liver −3.19 |
| **FOXA2** | Liver +4.28 (34.0% vs 1.8%), Endothelial +2.15, PGT +0.84 | PFG −3.27, PP −2.52, SC-EC −1.77, SC-beta −1.27, PDP −1.18 |
| **GSC** | Stromal +3.69 (22.7% vs 4.9%), ESC +2.50, ESC (D3) +2.23 | PP −2.55, DE −2.64, SC-EC −1.94, EnP −1.90 |
| **PAX6** | SC-EC +2.43 (25.6% vs 6.5%), PGT +1.77, EnP +1.05 | SC-beta −3.20, Endothelial −3.00, PDP −1.58, Liver −1.49 |
| **PDX1** | SC-EC +1.49 (25.4% vs 5.7%), PP +0.57, PDP +0.24 | SC-beta −2.93, Stromal −2.50, SC-delta −2.40, Endothelial −2.23, Liver −1.88, ESC −1.04 |
| **NEUROG3** | PDP +2.00 (21.6% vs 8.1%), PP +1.44, PFG +0.79 | **SC-beta −6.54 (0.00% vs 2.92%)**, SC-EC −5.14, SC-delta −3.30, SC-alpha −2.26 |
| **NEUROD1** | **SC-beta +2.83 (17.0% vs 2.36%)**, PP +0.52 | Endothelial −3.55, SC-EC −1.88, Liver −0.66 |
| **RFX6** | PFG +1.48 (27.9% vs 15.3%), DE +0.41 | SC-beta −3.01 (0.30% vs 2.98%), SC-delta −2.14, Endothelial −1.94, SC-alpha −1.18 |
| **TLE3** | SC-alpha +1.73 (17.9% vs 3.5%), SC-beta +0.57 | Liver −1.89, Endothelial −1.85 |
| **GATA4** | PDP +2.58 (14.4% vs 8.2%) | SC-EC −4.15, SC-delta −4.09, SC-beta −4.01, PP −1.58 |
| **HHEX** | Liver +1.62, Stromal +1.58 | PP −3.51, SC-EC −2.87, PFG −1.14 |
| **KDM2B** | SC-delta +3.91, Liver +2.24, DE +1.08 | SC-beta −2.56 |
| **GLIS3** | (ESC 64.5% of cells) | Liver −2.14, SC-alpha −3.14, Stromal −1.26 |
| **PDX1het** | — | SC-EC −3.19 (only significant row) |

![Cell-state enrichment heatmap](./figures/04_genotype_celltype_enrichment.png)

**Figure 7. Perturbation × cell-state compositional shift (stratified CMH).**
Heatmap of log₂ odds ratio (red = over-represented, blue = under-represented, diverging scale centred at 0) for each genotype × cell state, from the sample-stratified CMH test; `*` marks FDR < 0.05. Source: `_fig04_genotype_celltype_enrichment`, from `enrichment_matrix(enrich_res)`.
**Note on this figure:** the colourbar is labelled *"Enrichment vs WT (log2 OR)"*, but `enrichment_matrix()` returns the matrix for `results.primary_control`, which is `"other"` here. **The figure plots the other-perturbation reference, not WT.** This is a mislabelling in the current plotting code (§15) — the underlying numbers are correct for the `other` reference.

**Biological interpretation.**
- **Reproduces known biology.** GATA6 → Endothelial transdifferentiation and FOXA2 → hepatic diversion are exactly the phenotypes reported for these genotypes in the source differentiation system. NEUROG3 loss abolishing all hormone-positive endocrine cells while accumulating PP/PDP progenitors is the canonical endocrine-commitment block. PDX1 and RFX6 loss collapsing SC-beta while endocrine output redirects toward SC-EC matches the published beta-to-EC switch.
- **Convergence.** Multiple genetically distinct perturbations converge on the same alternate fate — PDX1 and PAX6 both to SC-EC (+1.49, +2.43), FOXA2 and HHEX both to Liver (+4.28, +1.62), GATA6 and FOXA2 both to Endothelial (+6.31, +2.15). **Interpretation:** these are shared downstream lineage attractors, not gene-specific idiosyncrasies.
- **New hypothesis.** **NEUROD1 mutants are *enriched* 6.6-fold in SC-beta** (17.0% vs 2.36%, log₂OR = +2.83, FDR = 0) — the opposite direction to the endocrine-loss genotypes — and this is the state where NEUROD1 cells have the highest PS in the entire screen (0.889). **Hypothesis:** NEUROD1 loss does not block beta-lineage entry but produces an abundant, transcriptionally aberrant SC-beta-annotated population — i.e. cells that are labelled beta by the classifier while being transcriptionally far from normal beta. This requires targeted validation (marker-level DE within SC-beta, protein-level INS/MAFA) before any mechanistic claim; the annotation itself could be mis-assigning these cells.

---

## 8. Localizing Perturbation Effects in Transcriptional State Space

**Method (as implemented).** `compute_lochness` (`src/perturbseq_pipeline/lochness.py`, ported from pertTF's `composition_change_analysis`) builds a k = 300 neighbour graph on `X_pca` and computes, for each cell *i* and perturbation *g*:

> lochNESS(i, g) = (fraction of *i*'s neighbours carrying *g*) / (global fraction of cells carrying *g*) − 1

0 = the perturbation appears in that neighbourhood exactly as often as chance predicts; > 0 = locally over-represented; < 0 = locally depleted. In this run the pipeline stores **`lochness_self`** — each cell's score for *the perturbation it itself carries* — rather than the full cell × perturbation matrix.

**Biological question answered.** Cluster-free, continuous mapping of *where on the manifold* a perturbation's cells pile up, including structure that falls within or straddles annotated states.

**A structural limitation that governs interpretation.** Because only `lochness_self` is retained, a cell is scored only for its own genotype. A genotype can therefore never receive a strongly negative score in a state it has *vacated* — there are no cells there to score. Empirically this is exactly what the data show: over all 111,581 cells `lochness_self` ranges from **−0.966 to +45.58**, the negative tail is bounded near −1 (the theoretical floor), and every genotype's `lochness_negative_mean` sits between −0.20 and −0.71. Figure 8 below contains essentially no blue.

**Conclusion: in this run lochNESS measures enrichment only. All depletion statements in this report come from §7.3, not from lochNESS.**

**Result — `tables/lochness_summary.csv`, 36 genotypes:**

| Genotype | n | Mean lochNESS | Positive fraction | Peak (95th pct) | Dominant state | Mean lochNESS in dominant state |
|---|---|---|---|---|---|---|
| GATA6 | 1,500 | 13.72 | 91.5% | 37.06 | ESC (34.5%) | 4.53 |
| PDX1het | 469 | 13.73 | 95.1% | 28.72 | ESC (87.8%) | 15.51 |
| TADA2B | 1,138 | 11.18 | 91.7% | 37.16 | ESC (24.0%) | 7.35 |
| GLIS3 | 935 | 9.34 | 90.2% | 25.56 | ESC (64.5%) | 13.63 |
| KDM2B | 182 | 6.91 | **100%** | 17.33 | ESC (52.2%) | 8.61 |
| FOXA2 | 4,896 | 6.07 | 83.1% | 18.31 | **Liver (34.0%)** | **13.74** |
| PDX1 | 6,207 | 5.91 | 82.7% | 15.54 | **SC-EC (25.4%)** | **9.79** |
| NEUROD1 | 2,728 | 4.12 | 87.1% | 27.67 | **SC-beta (17.0%)** | **19.56** |
| RFX6 | 3,331 | 2.30 | 88.5% | 9.13 | PFG (27.9%) | 3.91 |
| NEUROG3 | 1,543 | 1.70 | 89.2% | 5.97 | PDP (21.6%) | 3.23 |
| FOXA1 | 5,668 | 1.10 | 87.4% | 3.12 | PFG (21.4%) | 1.38 |

**Note:** `dominant_celltype_2` is the *most frequent* state among a genotype's cells, which is not necessarily the most enriched one. GATA6's dominant state is ESC (34.5%), but its highest lochNESS by far is in Endothelial (31.02, n = 386) — consistent with the +6.31 log₂OR in §7.3.

**Result — `tables/lochness_by_celltype.csv`, per-state maxima for the case-study genotypes:**

| Genotype | State | n cells | Mean lochNESS |
|---|---|---|---|
| GATA6 | Endothelial | 386 | **31.02** |
| GATA6 | DE | 327 | 18.01 |
| NEUROD1 | SC-beta | 464 | **19.56** |
| FOXA2 | Liver | 1,667 | **13.74** |
| PDX1 | PDP | 1,133 | 11.23 |
| PDX1 | SC-EC | 1,576 | 9.79 |
| FOXA2 | Endothelial | 397 | 7.27 |
| RFX6 | SC-EC | 160 | 7.15 |
| NEUROG3 | PDP | 333 | 3.23 |

**Result — `tables/lochness_by_celltype2.csv`, pooled by state:** Endothelial 13.25 > Liver 7.95 > SC-EC 6.85 > SC-beta 6.70 > SC-alpha 5.66 > PDP 4.23 > … > PFG 1.74, PP 1.79.

**Observation.** Pooled lochNESS is highest in exactly the off-lineage and terminal states (Endothelial, Liver, SC-EC, SC-beta) and lowest in the mid-trajectory progenitor states (PFG, PP).

**Interpretation.** Perturbation-driven neighbourhood structure is concentrated at the *ends* of the trajectory: cells that have exited the intended lineage form tight, genotype-pure neighbourhoods (Endothelial mean 13.25 means a perturbed cell's neighbourhood is ~14× enriched for its own genotype), whereas the progenitor compartment is well mixed across genotypes. **Interpretation:** progenitor states are a shared corridor all genotypes pass through; divergence — and therefore detectable local enrichment — happens on exit.

**Caveat.** lochNESS is a ratio to global frequency, so a rare genotype has a higher attainable ceiling than a common one (§5.2), and the pooled per-state values are dominated by whichever genotypes happen to occupy that state.

![lochNESS heatmap](./figures/13_lochness_by_celltype.png)

**Figure 8. Genotype × cell-state continuous lochNESS localization.**
Mean signed `lochness_self` per genotype × cell state on a diverging scale nominally centred at 0 (red > 0 enrichment, blue < 0 depletion); grey = fewer than 10 cells. All 36 genotypes appear. Source: `_fig13_lochness_by_celltype`.

**Biological interpretation.** The heatmap is essentially uniformly red-or-grey — the direct visual confirmation of the `lochness_self` limitation above. Read as an *enrichment map* it is highly informative: FOXA2 lights up Liver and Endothelial; GATA6 lights up DE, ESC (D3) and Endothelial; NEUROD1 lights up SC-beta; PDX1, PBX1, PAX6, TADA2B and TLE3 light up the SC-EC / SC-alpha / SC-beta block; GLIS3, PDX1het, KDM2B and NANOGe-het light up ESC only. **Interpretation:** the genotypes partition into an "arrested early" group whose enrichment is confined to ESC/DE, and a "redirected late" group whose enrichment appears in the terminal endocrine and off-lineage compartments.

---

## 9. Quantifying Perturbation-Induced State Displacement

### 9.1 Do different perturbations move cells in different directions?

**Method (as implemented).** `compute_distance_space` computes the full 36 × 36 pairwise energy-distance matrix between perturbation populations in `X_pca` (bounded sampling, ≤2,000 cells per genotype, seed 123), projects it with classical MDS/PCoA into 10 coordinates, extracts 10 nearest phenotypic neighbours per genotype, and clusters the matrix (average linkage) into **phenotype similarity groups**.

**Biological question answered.** Do perturbations displace cells along *different* axes, and which perturbations phenocopy one another?

**Result — 9 phenotype groups (`tables/phenotype_groups.csv`):**

| Group | Members |
|---|---|
| PG1 | HHEX, HHEXhet, KDM2B |
| PG2 | GLIS3, PDX1het |
| PG3 | ARX, FOXA1, HNF4A, HNF4Ahet, MNX1, NANOGe-het, NEUROG3, NKX2-2, PROSER1, RFX6, TET1, TET1/2/3 |
| PG4 | BMPR1A, GATA4, GATA4het, GATA6het, GSC, HHEXe, ONECUT1e, OTUD5, QSER1, QSER1TET1 |
| PG5 | BCOR, NEUROD1, TLE3 |
| PG6 | PAX6, PBX1, TADA2B |
| PG7 | PDX1 (singleton) |
| PG8 | FOXA2 (singleton) |
| PG9 | GATA6 (singleton) |

**Nearest phenotypic neighbours (`tables/distance_space_neighbors.csv`):**

| Genotype | 1st | 2nd | 3rd |
|---|---|---|---|
| PDX1 | PAX6 (1.51) | PBX1 (1.75) | BCOR (1.95) |
| RFX6 | TET1 (0.59) | NKX2-2 (0.63) | OTUD5 (0.70) |
| NEUROG3 | GATA4het (0.59) | PROSER1 (0.67) | NKX2-2 (0.75) |
| FOXA2 | HHEXe (3.38) | ARX (3.41) | RFX6 (3.43) |
| GATA6 | GATA6het (4.90) | GSC (4.92) | GATA4 (5.54) |

**Observation.** Three genotypes — PDX1, FOXA2, GATA6 — are phenotypic singletons; their nearest neighbours are 1.5–4.9 distance units away, versus 0.59–0.75 for members of the large PG3 group. GATA6's nearest neighbour is its own heterozygote, GATA6het.

**Interpretation.** The screen contains a small number of genuinely distinct phenotypic directions (early endoderm failure → GATA6; hepatic diversion → FOXA2; beta-to-EC redirection → PDX1) and a large cluster (PG3, 12 genotypes) whose members are phenotypically near-interchangeable at this resolution. **Interpretation:** PG3 likely represents perturbations with mild or late effects that do not substantially displace the population — RFX6, NEUROG3 and NKX2-2 all sit here despite having strong *compositional* phenotypes, which shows that global displacement and fate redirection are separable measurements.

**Hypothesis.** The `PDX1` / `PDX1het` split (PG7 vs PG2) and the `GATA6` / `GATA6het` pairing (PG9 vs PG4) suggest allele dosage produces qualitatively different phenotypic directions for PDX1 but a graded one for GATA6. **This is a hypothesis about dosage, and the small `PDX1het` cell count (n = 469) plus the small-sample bias in §5.2 mean it needs a matched-*n* re-analysis before it is asserted.**

![Distance space](./figures/14_distance_space.png)

**Figure 9. Perturbation distance space and phenotypic similarity groups.**
(A) PCoA of the 36 × 36 pairwise energy-distance matrix, first two coordinates, points coloured by phenotype similarity group and labelled by genotype. (B) The full pairwise energy-distance matrix (viridis_r; darker = more similar). Source: `_fig14_distance_space`, from `distance_space_coordinates.csv` / `distance_space_matrix.csv` / `phenotype_groups.csv`.

**Biological interpretation.** Most perturbations occupy a dense central cloud with a small number of extreme outliers pulled along PCoA1. **Interpretation:** the dominant axis of phenotypic variation in this screen separates "population stays on the intended trajectory" from "population is displaced wholesale", and only a handful of genotypes achieve the latter. **Caveat:** the PCoA eigenvalue spectrum / variance explained is not persisted to a table, so the fraction of structure captured by PCoA1–2 cannot be quoted here (§15).

### 9.2 Do the three metrics measure the same thing?

Spearman correlations across the master table `perturbation_summary.csv`:

| Pair | ρ | p | n |
|---|---|---|---|
| Energy distance ↔ PS median | **0.641** | 4.2 × 10⁻⁴ | 26 |
| Energy distance ↔ PS mean | 0.783 | 2.2 × 10⁻⁶ | 26 |
| Energy distance ↔ mean positive lochNESS | **0.410** | 1.3 × 10⁻² | 36 |
| Energy distance ↔ mean absolute lochNESS | 0.451 | 5.7 × 10⁻³ | 36 |
| PS median ↔ mean positive lochNESS | **0.061** | 0.77 (n.s.) | 26 |
| Energy distance ↔ mean negative lochNESS | −0.141 | 0.43 (n.s.) | 34 |

**Observation.** Distance and PS share roughly 41% of rank variance (ρ² = 0.41 for ps_median); distance and lochNESS share ~17%; **PS and lochNESS are effectively uncorrelated.**

**Interpretation.** These are three genuinely different measurements. PS reports *per-cell response penetrance*; lochNESS reports *manifold localization*; energy distance reports *population displacement*. A perturbation can be high on one and low on another: NEUROD1 has near-zero responder fraction (1.5%) and low energy distance (1.42, rank 33) yet the second-highest state-specific lochNESS in the screen (19.56 in SC-beta). **A single-number "perturbation strength" summary would misrank it badly.**

![PS vs distance](./figures/07_ps_vs_distance.png)

**Figure 10. Perturbation penetrance versus global phenotype magnitude.**
Scatter of energy distance vs WT (x) against median PS (y), one labelled point per genotype, with a dashed OLS trend line and the Spearman statistics inset (ρ = 0.641, p = 4.2 × 10⁻⁴, n = 26). Source: `_fig07_ps_vs_distance`.

**Biological interpretation.** The relationship is positive but loose, and the residuals are the interesting part. Genotypes above the line (high penetrance, modest displacement) respond strongly in the cells they occupy without leaving the trajectory; genotypes below the line (large displacement, low penetrance) move the population without a uniform per-cell signature — typically the mutant lines whose target transcript is not reduced, where the PS quadrant definition under-counts responders (§6.2).

---

## 10. Molecular Programs and Regulatory Interpretation

**Method (as implemented).** `compute_modules` (`src/perturbseq_pipeline/modules.py`, following Chen et al., *Nature* 2023) builds a perturbation × gene matrix of pseudobulk log₂FC vs control, using `celltype_2` cluster markers (Wilcoxon, top 100 per cluster) as the feature set. It then clusters the gene axis into **co-regulated programs** (Pearson) and the perturbation axis into **co-functional modules** (Spearman, average linkage), and computes a signed module × program strength matrix. Programs are annotated by over-representation analysis against Hallmark / Reactome / GO-BP.

**Result — 6 co-functional modules (`tables/module_assignments.csv`):**

| Module | Members |
|---|---|
| **M1** | ARX, BMPR1A, FOXA1, FOXA2, GATA4, GATA4het, GATA6, GATA6het, GLIS3, GSC, HHEX, HHEXe, HHEXhet, HNF4A, HNF4Ahet, KDM2B, MNX1, NANOGe-het, NEUROG3, NKX2-2, ONECUT1e, OTUD5, PDX1het, PROSER1, QSER1, QSER1TET1, RFX6, TET1, TET1/2/3 (29) |
| **M2** | TLE3 |
| **M3** | BCOR, NEUROD1 |
| **M4** | PDX1 |
| **M5** | TADA2B |
| **M6** | PAX6, PBX1 |

**Observation.** 29 of 36 perturbations fall into a single module (M1); the other five modules contain 1–2 members each.

**Interpretation, stated plainly:** **this is a weak clustering.** With `n_modules = 6` fixed by configuration, the algorithm was forced to return six groups; the resulting partition is one giant cluster plus five near-singletons. The number of DE genes per perturbation (`n_de_genes`, 638–777 for the top members) is similar across M1, so the module structure is not resolving distinct regulatory logic at this parameter setting. **The module assignment should be treated as preliminary and should not be used to claim shared mechanism.** The DistanceSpace phenotype groups (§9.1), which are derived from the actual cell distributions rather than pseudobulk log₂FC, give a more balanced and more interpretable partition.

**Result — 4 gene programs (`tables/gene_programs.csv`, `program_summary.csv`, `program_enrichment.csv`):**

| Program | Size | Top Hallmark term | ORA FDR | Representative overlap genes |
|---|---|---|---|---|
| **P1** | 6 | *unannotated* (too small for ORA) | — | GAL, AKAP12, PEG10, CACNA2D3, FGF12, CDK6 |
| **P2** | 549 | **HALLMARK_PANCREAS_BETA_CELLS** | 1.3 × 10⁻³ | INS, GCG, SST, CHGA, CHGB, NEUROD1, NEUROG3, NKX2-2, PAX4, PAX6, PCSK2, SLC30A8, ABCC8, MAFB, ISL1, GLIS3, TCF7L2 |
| **P3** | 316 | **HALLMARK_MYC_TARGETS_V1** | 3.5 × 10⁻³⁶ | RPL/RPS ribosomal proteins, NPM1, NCL, EIF4A1, HSP90AA1/AB1, PTTG1 (secondary: MTORC1_SIGNALING, FDR = 3.0 × 10⁻²⁰) |
| **P4** | 109 | **HALLMARK_EPITHELIAL_MESENCHYMAL_TRANSITION** | 1.5 × 10⁻⁴ | COL1A1, COL1A2, VIM, ZEB1, CTNNB1, ITGB1 (secondary: ANGIOGENESIS FDR = 3.1 × 10⁻⁴ — CD34, CDH5, FLT1, KDR, ERG, PECAM1) |

**Result — program activity by cell state (`tables/program_activity_celltype.csv`):**

| Program | Highest states | Lowest states |
|---|---|---|
| P1 | SC-alpha 0.378, SC-beta 0.371 | PP −0.432, PDP −0.328, Liver −0.320 |
| P2 (beta-cell) | SC-delta 0.647, SC-beta 0.622, SC-EC 0.572, SC-alpha 0.574 | ESC 0.071, DE 0.158 |
| P3 (MYC/ribosome) | ESC (D3) 1.142, ESC 1.107, DE 1.087 | SC-delta 0.330, SC-alpha 0.361, SC-EC 0.379 |
| P4 (EMT/angiogenesis) | **Endothelial 1.183** | ESC 0.054, SC-EC 0.029 |

**Result — module × program strength (`tables/module_program_strength.csv`):**

| | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| M1 (29 perturbations) | 0.109 | **−0.870** | 0.636 | 0.411 |
| M2 (TLE3) | **0.666** | 0.102 | 0.039 | 0.033 |
| M3 (BCOR, NEUROD1) | 0.512 | −0.077 | 0.213 | −0.006 |
| M4 (PDX1) | 0.126 | −0.110 | −0.016 | −0.029 |
| M5 (TADA2B) | −0.190 | −0.476 | 0.180 | −0.022 |
| M6 (PAX6, PBX1) | **−0.664** | −0.200 | 0.224 | 0.061 |

**Observation.** The strongest single entry in the matrix is **M1 → P2 = −0.870**: the 29-member module strongly *suppresses* the beta-cell program. M1 simultaneously *raises* P3 (MYC/ribosome, +0.636) and P4 (EMT/angiogenesis, +0.411).

**Interpretation.** The dominant molecular signature of perturbation in this screen is a coordinated **loss of the endocrine/beta program with a shift toward proliferative-progenitor (MYC target, ribosome biogenesis, mTORC1) and mesenchymal/endothelial character.** P4's strong Endothelial-specific activity (1.183, ~10× any other state) and its CD34/CDH5/PECAM1/FLT1/KDR content directly connect this program to the GATA6 → Endothelial transdifferentiation seen compositionally in §7.3.

**Hypothesis.** The M1 → P2⁻ / P3⁺ axis is a *failure-to-exit-progenitor* signature: cells that cannot complete endocrine specification remain in a proliferative, MYC-high, partially mesenchymal state. This is a coherent reading of the data but is **not** demonstrated — it would need pseudotime or lineage-tracing evidence, and the module partition itself is unreliable (above).

![Module × program strength](./figures/15_module_program_strength.png)

**Figure 11. Co-functional module × gene program signed strength.**
Heatmap of the signed module × program strength matrix (M1–M6 rows × P1–P4 columns), diverging scale centred at 0. Source: `_fig15_module_program_strength`, from `module_program_strength.csv`.

**Biological interpretation.** The matrix is dominated by the M1 row, which is a direct consequence of M1 containing 29 of 36 perturbations (see the clustering caveat above). The informative content is the *sign pattern* — P2 down, P3/P4 up — rather than the module partition.

![Program enrichment](./figures/17_program_enrichment.png)

**Figure 12. Pathway over-representation for the four gene programs.**
Top enriched gene-set terms per program (Hallmark / Reactome / GO-BP, ORA, FDR < 0.05), with programs on one axis and −log₁₀ FDR encoded by bar length / colour. Source: `_fig17_program_enrichment`, from `program_enrichment.csv`.

**Biological interpretation.** P2's overlap list is a textbook islet signature (INS, GCG, SST, CHGA, PCSK2, SLC30A8, ABCC8, NEUROD1, NEUROG3, PAX4, PAX6, NKX2-2, ISL1, MAFB, GLIS3, TCF7L2 — several of which are themselves perturbation targets in this screen), and P4 is a clean endothelial/EMT signature. **This is an internal validity check that passes:** unsupervised gene clustering on this dataset recovers the biology the screen was designed to perturb, without being told about it.

---

## 11. Integrated Perturbation Phenotype Framework

The conceptual chain that the current results *do* support:

```
Genetic perturbation  (36 genotypes; §3)
        ↓
Global state displacement    energy distance vs WT, 1.08 – 13.63, all FDR-significant  (§6.1)
        ↓
Per-cell response penetrance PS 0–1, responder fraction 1.5% – 66.6%, 26/36 genotypes  (§6.2)
        ↓
Cell-state specificity       PS by state: PP 0.13 → ESC 0.57; per-genotype peaks up to 0.89  (§7.1–7.2)
        ↓
State-space localization     lochNESS enrichment, up to 31.0 (GATA6/Endothelial)  (§8)
        ↓
Fate composition change      CMH log₂OR, −6.54 (NEUROG3/SC-beta) to +6.31 (GATA6/Endothelial)  (§7.3)
        ↓
Transcriptional programs     P2 beta-cell ↓, P3 MYC/ribosome ↑, P4 EMT/endothelial ↑  (§10)
        ↓
Developmental phenotype      arrest / lineage diversion / endocrine subtype redirection  (§12)
```

Two deviations from the idealized framework must be recorded:

1. **The chain is not a single ordered axis.** Because PS and lochNESS are uncorrelated (ρ = 0.061, §9.2), a perturbation's position in the chain cannot be predicted from one link to the next. The levels are complementary coordinates, not a severity ladder.
2. **The "cell-state specificity → displacement" step is measured by two instruments that disagree about direction.** lochNESS in this run reports enrichment only (§8); depletion is only visible compositionally (§7.3). Any integrated score built from these must not treat lochNESS as a signed quantity.

The single most compact integrated view currently produced is Figure 13.

![Multi-metric atlas](./figures/19_perturbation_summary.png)

**Figure 13. Multi-metric perturbation atlas.**
Five aligned horizontal-bar panels, genotypes sorted by cell number: (1) screen representation (n cells), (2) PS median with the 0.5 activity threshold marked, (3) energy distance vs WT, (4) mean positive lochNESS, (5) mean negative lochNESS. All panels on native scales — deliberately **not** z-scored, so magnitudes remain interpretable. Source: `_fig19_perturbation_summary`, from `perturbation_summary.csv`.

**Biological interpretation.** Reading across a row shows that no genotype is extreme on every axis. Panel 5 (negative lochNESS) is visually near-empty for every genotype, which is the graphical statement of the `lochness_self` limitation (§8) — this panel is currently uninformative and should either be removed or replaced by a compositional depletion statistic (§16).

---

## 12. Biological Case Studies

Five perturbations are examined where several independent metrics agree. Each is separated into **Observation** (directly measured), **Interpretation** (consistent explanation), and **Hypothesis** (requires validation).

![Highlighted genotypes on the manifold](./figures/28_umap_highlight_genotypes.png)

**Figure 14. Case-study genotypes on the differentiation manifold.**
UMAP panels highlighting the cells of `PDX1`, `FOXA2`, `RFX6` and `NEUROG3` (the workflow default `--highlight-genotypes`) against a 5%-subsampled grey background of all other cells. Source: `_fig28_umap_highlight_genotypes`.

**Biological interpretation.** Each highlighted genotype occupies a visibly distinct sector of the manifold — FOXA2 in the Liver/Endothelial lobe, PDX1 in the SC-EC/PDP region, RFX6 spread over PFG/DE, NEUROG3 concentrated in PDP/PP — which is the qualitative form of the quantitative statements below.

### 12.1 FOXA2 — hepatic diversion (strongest single-state relocation)

**Observation.**
- Energy distance 5.45 (rank 10/36), FDR = 9.99 × 10⁻⁴, n = 4,896.
- **Liver enrichment: 34.05% of FOXA2 cells vs 1.82% of reference, log₂OR = +4.28, FDR = 0.** Endothelial +2.15. Depleted in PFG (−3.27), PP (−2.52), SC-EC (−1.77), SC-beta (−1.27), PDP (−1.18).
- lochNESS: dominant state Liver (34.0% of cells), mean lochNESS **13.74** in Liver, 7.27 in Endothelial; genotype-wide mean 6.07.
- PS: mean 0.399 genotype-wide, but **0.661 in Liver** (n = 1,667). Responder fraction 5.7%, escaper fraction 28.1%.
- Target transcript log₂FC = **+0.49** (KS FDR 1.0 × 10⁻¹⁷¹), i.e. *FOXA2* mRNA is higher, not lower.
- Phenotype singleton PG8; nearest phenotypic neighbour HHEXe at distance 3.38.

**Interpretation.** FOXA2 loss permits progression through definitive endoderm but fails at posterior foregut patterning, and cells adopt a hepatic identity instead — the classic FOXA2 endoderm-bifurcation phenotype. Three independent measurements (composition, lochNESS localization, state-specific PS) converge on Liver. The apparent *increase* in *FOXA2* transcript is a composition artefact: FOXA2 is highly expressed in hepatic cells, and a third of this genotype's cells are now hepatic (§5.3). The 5.7% "responder fraction" is likewise an artefact of the PS quadrant rule, which requires low target expression.

**Hypothesis.** The additional Endothelial enrichment (+2.15, 8.1% of cells) is a secondary phenotype rather than part of the hepatic program. Testing this requires checking whether FOXA2 Endothelial cells cluster with GATA6 Endothelial cells (which they would if there is a shared endothelial attractor) — the pairwise distance data exist for this but the analysis has not been run.

### 12.2 GATA6 — earliest checkpoint failure and endothelial transdifferentiation

**Observation.**
- Energy distance 9.70 (rank 3/36), n = 1,500. Phenotype singleton **PG9**; nearest neighbour is its own heterozygote GATA6het at 4.90.
- **Endothelial enrichment: 25.73% of GATA6 cells vs 0.95% of reference, log₂OR = +6.31 — the largest odds ratio in the entire screen.** Also enriched ESC +1.31, ESC (D3) +1.96.
- Depleted across the whole pancreatic axis: SC-EC −4.27, SC-alpha −4.14, EnP −3.34, Liver −3.19, PP −2.99, PFG −2.90.
- lochNESS: **31.02 in Endothelial** (n = 386) and 18.01 in DE; genotype-wide mean 13.72, peak 37.06.
- PS: mean 0.578, median 0.648, responder fraction **61.6%** (2nd highest in the screen). Target *GATA6* log₂FC = −1.11 (53.7% knockdown, effective).
- Gene program P4 (EMT / angiogenesis; CD34, CDH5, PECAM1, FLT1, KDR) has by far its highest activity in Endothelial cells (1.183).

**Interpretation.** GATA6 loss blocks pancreatic specification at or before the definitive-endoderm-to-foregut transition and diverts cells wholesale into an endothelial-like fate. This is the most internally consistent phenotype in the study: it is simultaneously the largest compositional odds ratio, the largest state-specific lochNESS, a phenotypic singleton in distance space, the second-highest per-cell penetrance, *and* it has a matching unsupervised gene program (P4) with the correct marker content. Target knockdown is confirmed, so none of the QC caveats about mutant lines apply.

**Hypothesis.** The GATA6/GATA6het pairing (nearest neighbours at 4.90, but assigned to different phenotype groups PG9 vs PG4) suggests a dosage-graded rather than threshold phenotype. Confirming this requires a matched-*n* comparison; GATA6het has 2,266 cells against GATA6's 1,500, so the small-sample bias of §5.2 does not obviously explain the split.

### 12.3 PDX1 — beta-to-enterochromaffin redirection, with a dosage puzzle

**Observation (homozygous PDX1, n = 6,207).**
- Energy distance 2.23 (rank 21/36) — **modest**, despite a severe fate phenotype. Phenotype singleton **PG7**; nearest neighbour PAX6 at 1.51.
- **SC-EC enrichment +1.49 (25.39% vs 5.72%); SC-beta depletion −2.93 (1.05% vs 3.02%).** Also depleted Stromal −2.50, SC-delta −2.40, Endothelial −2.23, Liver −1.88, ESC −1.04; enriched PP +0.57, PDP +0.24.
- lochNESS: dominant state SC-EC (25.4%), mean lochNESS 9.79 in SC-EC and **11.23 in PDP** (n = 1,133).
- PS: genotype-wide mean 0.378, but **0.833 in SC-EC** (n = 1,576) and 0.722 in SC-beta (n = 65). Responder fraction 29.1%.
- Target *PDX1* log₂FC = −0.69 (37.9% knockdown, effective).
- Assigned to its own co-functional module **M4**.

**Observation (heterozygous PDX1het, n = 469).**
- **Energy distance 13.63 — the largest in the screen**, 6.1× the homozygote's.
- lochNESS mean 13.73, 95.1% of cells positive, and **87.8% of its cells are ESC** with mean lochNESS 15.51 in that state.
- Only one significant compositional result: SC-EC **depletion** −3.19.
- **No PS value** (target label not resolvable in the expression matrix).

**Interpretation (homozygote).** PDX1 loss does not block endocrine commitment but redirects endocrine output away from beta and toward the serotonergic SC-EC fate, with progenitor (PP/PDP) accumulation upstream — the published PDX1 phenotype in this differentiation system. Note that the *global* displacement is small (rank 21) while the *fate* consequence is severe: this is the clearest single demonstration in the study that energy distance and developmental phenotype are different quantities. The state-resolved PS of 0.833 in SC-EC versus 0.378 genotype-wide is the corresponding penetrance statement.

**Interpretation (heterozygote) — flagged as unresolved.** PDX1het's extreme energy distance is not corroborated by its compositional profile (a single significant depletion) and is heavily confounded: n = 469 (small-sample upward bias in the energy-distance estimator, §5.2), 87.8% of its cells sit in ESC (so it is largely being compared against a WT population that spans all stages), and lochNESS ceilings rise for rare genotypes. **The claim "PDX1het has the strongest phenotype in the screen" is not supported at the current level of analysis and should not be made.** What *is* supported is that PDX1het's cells are strongly localized (95.1% positive lochNESS, mean 13.7) within the ESC compartment.

**Hypothesis.** PDX1het cells may be predominantly arrested at or near the pluripotent state rather than differentiating with reduced fidelity. This is directly testable by re-running the distance test restricted to ESC cells only, with matched cell numbers.

### 12.4 NEUROG3 — canonical endocrine-commitment block

**Observation.**
- Energy distance 2.40 (rank 20/36), n = 1,543. Phenotype group PG3; nearest neighbours GATA4het (0.59), PROSER1 (0.67), NKX2-2 (0.75) — i.e. phenotypically unremarkable in *distance* terms.
- **SC-beta: 0.00% of NEUROG3 cells vs 2.92% of reference, log₂OR = −6.54, FDR = 6.7 × 10⁻¹⁴ — complete absence.** Also SC-EC −5.14, SC-delta −3.30, SC-alpha −2.26, EnP −1.66.
- **Upstream accumulation: PDP +2.00 (21.58% vs 8.09%), PP +1.44 (13.16% vs 7.58%), PFG +0.79.**
- lochNESS: genotype-wide mean only 1.70, dominant state PDP with mean lochNESS 3.23. No SC-beta row exists (zero cells).
- PS: mean 0.399, responder fraction 35.7%, escaper fraction 0.6%. Target *NEUROG3* log₂FC = **−1.80 (71.2% knockdown)** — the second-strongest knockdown in the screen.

**Interpretation.** NEUROG3 loss produces the textbook endocrine-commitment block: cells reach the pancreatic/endocrine progenitor stage and stop, so progenitors accumulate and *every* hormone-expressing subtype is lost. Target knockdown is confirmed and strong, so this phenotype is free of the mutant-line QC caveats.

**This case study is also the study's most instructive methodological lesson.** NEUROG3 ranks 20/36 on energy distance and has an unremarkable lochNESS profile, yet it has the most extreme compositional effect in the screen (log₂OR = −6.54). The reason is structural: an arrest phenotype leaves cells in a state the WT population also occupies, so the population is not *displaced* — it is *stalled*. **Displacement metrics are blind to arrest; only the compositional analysis detects it.**

### 12.5 NEUROD1 — an unexpected SC-beta enrichment

**Observation.**
- Energy distance 1.42 (rank 33/36) — near the bottom. n = 2,728. Phenotype group PG5 with BCOR and TLE3; co-functional module M3 with BCOR.
- **SC-beta enrichment +2.83 (17.01% of NEUROD1 cells vs 2.36% of reference, FDR = 0)** — a 7.2-fold over-representation, in the *opposite* direction to every other endocrine-factor genotype. Also PP +0.52; depleted Endothelial −3.55, SC-EC −1.88.
- lochNESS: **19.56 in SC-beta** (n = 464, 100% of those cells positive) — the second-highest state-specific lochNESS in the screen, against a genotype-wide mean of only 4.12.
- PS: **0.889 mean / 0.936 median in SC-beta** (n = 464) — the highest state-specific PS in the entire study — against a genotype-wide mean of 0.339. Responder fraction 1.5% (lowest in the screen), escaper fraction 21.7%.
- Target *NEUROD1* log₂FC = **+0.25** (transcript up, not "effective").

**Interpretation.** NEUROD1-mutant cells are not excluded from the beta-annotated compartment; they are strongly over-represented in it and, once there, are transcriptionally the *most* perturbed cells anywhere in the screen (PS 0.889, lochNESS 19.56, 100% positive). The 1.5% responder fraction is an artefact of requiring low target expression (§6.2) and should be disregarded for this genotype. The near-perfect lochNESS positivity in SC-beta means these cells form a tight, genotype-pure neighbourhood — they are clustered *apart from* wild-type SC-beta cells while still receiving the SC-beta label.

**Hypothesis (the study's clearest novel lead).** NEUROD1 loss produces an aberrant, immature or mis-specified beta-like population that the current `celltype_2` annotation assigns to SC-beta on the basis of partial marker expression. **Required validation:** differential expression restricted to SC-beta cells, NEUROD1-mutant vs WT (INS, MAFA, MAFB, G6PC2, SLC30A8, UCN3); re-annotation of these cells with a reference-based classifier; and protein-level confirmation. Until then, the "SC-beta" label for these cells should be treated as provisional and no mechanistic claim should be made.

---

## 13. What These Analyses Add Beyond Prediction Alone

Concrete instances from this dataset where a single predicted response vector would have been insufficient:

| Finding | Which metric revealed it | Why prediction alone would miss it |
|---|---|---|
| NEUROD1 mean PS = 0.339 genotype-wide but **0.889 in SC-beta** | State-resolved PS (§7.2) | A genotype-level prediction averages over 2,264 cells that are not in the responsive state |
| NEUROG3 log₂OR = **−6.54** for SC-beta but energy distance rank only 20/36 | CMH composition vs displacement (§12.4) | An arrest phenotype does not displace the population; a distance-based summary ranks it as mild |
| PDX1 energy distance rank 21/36 despite complete beta-to-EC redirection | Composition vs displacement (§12.3) | Magnitude of transcriptional change ≠ magnitude of developmental consequence |
| Responder fractions spanning **1.5% – 66.6%** | PS quadrants (§6.2) | Population-average predictions cannot express penetrance or cell-to-cell heterogeneity |
| PS ↔ lochNESS ρ = **0.061** | Cross-metric correlation (§9.2) | The two dimensions are independent; neither substitutes for the other |
| P2 (beta-cell program) suppressed with P3 (MYC/ribosome) and P4 (EMT) raised | Modules/programs + ORA (§10) | Names the transcriptional programs behind the phenotype rather than the phenotype itself |
| GATA6, FOXA2, PDX1 are phenotypic **singletons**; 12 genotypes are near-interchangeable in PG3 | DistanceSpace (§9.1) | Relational structure among perturbations is not derivable from per-genotype predictions |

**Stated fairly:** none of this contradicts pertTF. It supplies the phenotypic measurements a prediction can be *evaluated against* and *interpreted with*, on the same manifold and using the same lochNESS definition pertTF uses.

---

## 14. Current Limitations

Ordered by how much they constrain interpretation.

1. **PS covers only 26/36 genotypes (§5.5).** The 10 non-canonical genotype labels (12,873 cells, 16.3% of perturbed cells) have no per-cell response score. This includes `PDX1het`, the top-ranked genotype by energy distance.
2. **lochNESS as run measures enrichment only (§8).** `lochness_self` is bounded below at −1 and cannot score a cell in a state the genotype has vacated. Figure 8 and panel 5 of Figure 13 contain effectively no depletion signal. All depletion claims here derive from §7.3.
3. **Cell number confounds every effect metric (§5.2).** Energy distance (ρ = −0.448), lochNESS (−0.383) and PS (−0.460) all correlate negatively with genotype cell count. Statistical bias and biological severity are not separated.
4. **All permutation p-values are at the resolution floor (§6.1).** 36/36 genotypes have FDR = 9.99 × 10⁻⁴ = 1/1001. The test confirms detectability and contributes nothing to ranking.
5. **The "significant" compositional comparison is against other perturbations, not WT (§7.3).** WT-referenced odds ratios are computed but never flagged, because `primary_control` defaults to `"other"` in the workflow's `Config()`. The `other` reference is a defensible within-sample control, but it is not the comparison the figure label claims.
6. **Genotype is confounded with sample (§3).** Perturbed cells exist only in the seven staged samples; the WT population is dominated by six separate WT-only samples. CMH stratification mitigates this for the compositional test; PS, lochNESS and energy distance are **not** sample-stratified.
7. **No batch correction, by design.** `cluster.batch_key = None` because samples are genuine differentiation stages. The consequence is that per-sample depth variation (6,408–10,241 median UMIs) and %mt variation (1.7–4.4%) propagate into `X_pca` and therefore into every distance and neighbourhood computation.
8. **Perturbation efficiency is unverified or contradicted for 13/26 testable genotypes (§5.3).** These are mutant lines, so this is expected, but it means there is no independent molecular confirmation of allele function for those genotypes within this dataset.
9. **The co-functional module partition is degenerate (§10).** 29/36 perturbations in M1; `n_modules = 6` was imposed by configuration. Do not use module co-membership as evidence of shared mechanism.
10. **PS uses a globally pooled WT reference,** not a state-matched one. The very low PS in PP (0.134) could reflect either biology or reference mismatch (§7.1).
11. **Cell-state annotation is inherited, not re-derived.** `celltype_2` comes from the source object. Where a perturbation produces an aberrant state (NEUROD1/SC-beta, §12.5), the label may be misleading, and this analysis has no independent check on it.
12. **Traceability gaps in the outputs.** The TF-hub network and module-connectivity tables used by Figure 18 are computed in memory but never written to `tables/`; the PCoA eigenvalue spectrum (variance explained) is likewise not persisted, so Figure 9's axes cannot be quantified.

---

## 15. Work in Progress

Items that are actively in an incomplete state in the repository, distinguished from limitations of completed work:

- **lochNESS in the generic pipeline configuration is disabled.** `config/diabetes.yaml` sets `lochness.enabled: false`, with the reason recorded inline: the genotype `TET1/2/3` generates the HDF5-unsafe obs column `lochness_TET1/2/3`, which crashes the writer at stage 13. The dedicated workflow works around this (`sanitize_identifier`; lean h5ad retains only `lochness_self`), but **the underlying writer has not been fixed**, so `results/diabetes/` has no lochNESS output. Any stale `results/diabetes/tables/lochness*.csv` files predate this configuration and should not be used.
- **Figure 4 colourbar is mislabelled** ("Enrichment vs WT (log2 OR)" while plotting the `other` reference). Cosmetic, but it will mislead a reader. Not yet fixed.
- **`direction` and `sign(log2_odds_ratio)` can disagree** in `celltype_enrichment.csv` (§7.3), because one is unstratified and the other is CMH-stratified. Not yet reconciled.
- **Stage-7 network outputs are not persisted.** `mod_results.tf_edges` and `mod_results.module_connectivity` are produced and plotted (Figure 18) but not written to `tables/`.
- **Presentation build is in flux.** `results/diabetes_specific/presentation/` contains multiple deck generators (`build_deck.py`, `build_full_deck.py`, `Presentation_Sep1/build_master_deck.py`, `build_master_presentation.py`, `apply_final_corrections.py`) plus audit documents. Several numbers in `Presentation_Sep1/Case_Study_Evidence_Audit.md` are **stale relative to the current tables** — e.g. it lists RFX6 energy distance = 2.115886 and PDX1 = 2.457885, whereas the current `distance_results.csv` gives 2.446204 and 2.230481, and it describes GATA6's dominant cell type as Endothelial where `lochness_summary.csv` records ESC. Those documents should be regenerated against the current tables before reuse.
- **`PertTF_Diabetes_Quantitative_Perturbation_Biology_Report.docx`** (16.6 MB, last modified after the analysis run) is a parallel narrative document. It was used as supporting material for this report; every quantitative claim reproduced here was re-verified against the CSVs rather than transferred.

**Explicitly *not* work in progress — these are complete:** the PS, lochNESS, DistanceTest, DistanceSpace, cell-state enrichment and modules/programs stages all ran to completion in job 19816263 (21 minutes, 0 failed stages), all 28 primary figures were generated (`figure_manifest.json`: `total_attempted: 28, total_generated: 28, total_failed: 0`), plus 102 per-genotype UMAP panels, and the 39-test suite for the workflow passes.

---

## 16. Proposed Next Analyses

Ordered by how much they would strengthen the current claims.

1. **Cell-number-matched re-analysis of the distance ranking.** Subsample every genotype to a common *n* (e.g. 182, or bootstrap to a common *n* with confidence intervals) and recompute energy distance. This is the single most important control, because it directly tests whether the PDX1het / HHEXhet / KDM2B leadership of the ranking is biology or small-sample bias (§5.2, §12.3).
2. **Replace saturated permutation p-values with bootstrap confidence intervals** on the energy distance (§6.1). Ranking with uncertainty is what the data can actually support.
3. **Compute the full cell × perturbation lochNESS matrix**, not just `lochness_self`, so that depletion becomes measurable and Figure 8 / Figure 13 panel 5 become informative. The pipeline supports this for datasets of this size (36 perturbations × 111,581 cells is tractable).
4. **State-matched PS.** Recompute PS with a WT reference restricted to the same `celltype_2` (or same `orig.ident`) as the target cells, to test whether the PP minimum (0.134) is biological (§7.1).
5. **Report the WT-referenced compositional test as primary,** or report both explicitly, by setting `enrichment.primary_control = "ntc"` in the workflow (§7.3) — and fix the Figure 4 label either way.
6. **Within-state differential expression for NEUROD1 SC-beta cells** vs WT SC-beta cells (INS, MAFA, MAFB, G6PC2, SLC30A8, UCN3, NKX6-1), plus reference-based re-annotation, to test the §12.5 hypothesis.
7. **Dosage-series analysis.** A dedicated comparison of the five homozygote/heterozygote pairs present (PDX1/PDX1het, GATA6/GATA6het, GATA4/GATA4het, HNF4A/HNF4Ahet, HHEX/HHEXhet) at matched *n*, on all metrics.
8. **Re-run the module clustering with `cluster_distance_threshold` instead of a fixed `n_modules = 6`,** so the partition is data-determined; the current 29/36 single-module result is uninformative (§10).
9. **Direct comparison against pertTF predictions.** Correlate pertTF's predicted per-cell lochNESS / response with the measured `lochness_self` and PS on the same cells. All the required per-cell values are present in `diabetes_analysis.h5ad`; this analysis has not been run.
10. **Persist the missing outputs** (`tf_edges`, `module_connectivity`, PCoA eigenvalues) so Figures 9 and 18 become fully traceable (§14.12).

---

## 17. Conclusions

1. Every one of the 36 perturbations in this pancreatic differentiation screen produces a measurable transcriptional phenotype, but the **effect magnitude varies 12.7-fold** and the permutation p-values are uninformative for ranking.
2. **Perturbation effects are strongly cell-state-dependent.** Response strength varies more than 4-fold across developmental states (PP 0.13 → ESC 0.57), and individual genotypes concentrate their response in specific states, reaching mean PS 0.889 (NEUROD1 in SC-beta) and 0.833 (PDX1 in SC-EC) against genotype-wide means near 0.34–0.38. Genotype-level averages substantially under-report the phenotype.
3. **The compositional analysis is the instrument that detects developmental redirection.** It recovers FOXA2 → Liver, GATA6 → Endothelial, NEUROG3 → complete endocrine block, and PDX1/PAX6/RFX6 → beta-to-EC redirection, all at large effect sizes and with the correct known directions. Displacement metrics alone rank several of these as mild.
4. **The metrics are complementary.** PS and lochNESS are statistically unrelated across genotypes (ρ = 0.061). Energy distance explains only ~41% of the rank variance in PS and ~17% in lochNESS. An integrated phenotype requires all three plus the compositional test.
5. **Unsupervised gene-program discovery independently recovers the biology the screen targets** — a 549-gene beta-cell program (INS/GCG/SST/CHGA/PCSK2/SLC30A8) suppressed by perturbation, and a 109-gene EMT/angiogenesis program (CD34/CDH5/PECAM1/FLT1) whose activity is ~10× higher in Endothelial cells than anywhere else, matching the GATA6 transdifferentiation phenotype.
6. **Three results are honest caveats rather than findings:** PS is unavailable for 10 genotypes; lochNESS as run cannot see depletion; and effect size is confounded with genotype cell number. Each has a specific proposed remedy (§16).
7. **One clear new hypothesis emerges:** NEUROD1-mutant cells are 7.2-fold over-represented in the SC-beta compartment while being the most transcriptionally perturbed cells in the study, suggesting an aberrant beta-like state rather than a beta-lineage block. This is a lead for validation, not a conclusion.

---

## Appendix: Analysis-to-Code Mapping

All paths are relative to the repository root (`perturbseq-pipeline/`). Result files are local analysis outputs and are intentionally **not** tracked in Git (see the repository `.gitignore`).

| Analysis | Script / module | Key output files | Status |
|---|---|---|---|
| Workflow orchestration | `workflows/diabetes_analysis.py`, `workflows/run_diabetes_analysis.slurm` | `results/diabetes_specific/` | **Completed** (job 19816263) |
| Dataset validation & stage derivation | `diabetes_analysis.py::validate_dataset`, `derive_development_stage`, `prepare_diabetes_anndata` | workflow log | **Completed** |
| Dataset inventory / label audit | `diabetes_mapping.py`, `check_h5ad_diabetes.py` | stdout | **Completed** |
| PCA (3,000 HVGs, 50 PCs, no batch key) | `src/perturbseq_pipeline/cluster.py` (`_select_hvgs`, `_run_pca_on_hvgs`) | `diabetes_analysis.h5ad::obsm['X_pca']` | **Completed** |
| Per-cell PS score (`pertps` 0.1.0) | `src/perturbseq_pipeline/ps_score.py`; `diabetes_analysis.py::run_diabetes_ps_analysis` | `tables/ps_score_summary.csv`, `ps_score_skipped.csv` | **Completed** (26/36 genotypes) |
| PS by genotype / state / stage | `diabetes_analysis.py::compute_ps_by_genotype`, `compute_ps_by_celltype2`, `compute_ps_by_genotype_celltype`, `compute_ps_by_development_stage` | `tables/ps_by_genotype.csv`, `ps_by_celltype2.csv`, `ps_by_genotype_celltype.csv`, `ps_by_development_stage.csv` | **Completed** |
| lochNESS (k = 300, `X_pca`) | `src/perturbseq_pipeline/lochness.py`; `diabetes_analysis.py::run_diabetes_lochness_analysis`, `compute_lochness_directional_summary` | `tables/lochness_summary.csv`, `lochness_by_genotype.csv`, `lochness_by_celltype.csv`, `lochness_by_celltype2.csv`, `lochness_by_development_stage.csv` | **Completed — `lochness_self` only (enrichment-directional)** |
| Energy distance + permutation DistanceTest | `src/perturbseq_pipeline/distance.py::compute_perturbation_distance`, `distance_test_permutation` | `tables/distance_results.csv`, `distance_test.csv` | **Completed** (36/36, p-values at floor) |
| DistanceSpace / PCoA / phenotype groups | `src/perturbseq_pipeline/distance.py::compute_distance_space`, `compute_pcoa_coordinates` | `tables/distance_space_matrix.csv`, `distance_space_coordinates.csv`, `distance_space_neighbors.csv`, `phenotype_groups.csv` | **Completed** (eigenvalues not persisted) |
| Cell-state enrichment (CMH, stratified by `orig.ident`) | `src/perturbseq_pipeline/enrichment.py::test_cluster_enrichment`, `enrichment_matrix`, `significance_matrix` | `tables/celltype_enrichment.csv` | **Completed — significance flagged for `other` reference only** |
| Co-functional modules & gene programs | `src/perturbseq_pipeline/modules.py::compute_modules` | `tables/module_assignments.csv`, `gene_programs.csv`, `module_program_strength.csv`, `program_activity_celltype.csv` | **Preliminary** (29/36 in M1) |
| Program pathway ORA (Hallmark/Reactome/GO-BP) | `src/perturbseq_pipeline/gene_sets.py::run_program_enrichment` | `tables/program_enrichment.csv`, `program_summary.csv` | **Completed** |
| Master multi-metric merge | `diabetes_analysis.py::build_master_summary_table` | `tables/perturbation_summary.csv` | **Completed** |
| Lean h5ad export | `diabetes_analysis.py::export_lean_h5ad` | `results/diabetes_specific/diabetes_analysis.h5ad` (949 MB) | **Completed** |
| 28 primary figures | `diabetes_analysis.py::generate_diabetes_figures`, `_fig01`–`_fig28`, `safe_generate_figure` | `figures/01_*.png` … `figures/28_*.png`, `figures/figure_manifest.json` | **Completed** (28/28, 0 failed) |
| 102 per-genotype UMAP atlases | `diabetes_analysis.py::generate_per_genotype_umaps` | `figures/per_genotype_ps/` (28), `per_genotype_lochness/` (38), `per_genotype_combined/` (36), `tables/per_genotype_umap_manifest.csv` | **Completed** |
| Figure/table recovery from checkpoints | `diabetes_analysis.py::recover_and_finish_diabetes_run` (`--recover`) | regenerates `figures/`, `tables/` | **Completed** (available, not needed for the current run) |
| Generic 14-stage pipeline run (perturbation-efficiency QC source) | `config/diabetes.yaml`, `petrub-pipeline.slurm`, `src/perturbseq_pipeline/cli.py` | `results/diabetes/tables/perturbation.csv`, `qc_summary.csv`, `report.html` | **Completed — lochNESS stage disabled** |
| Workflow regression tests | `tests/test_diabetes_analysis.py` | — | **Completed** (39/39 passing) |
| Presentation / deck generation | `results/diabetes_specific/presentation/**` | `.pptx`, audit `.md` files | **Work in progress** (several numbers stale) |

**Figures referenced in this report** (all under `results/diabetes_specific/figures/`):

| Report figure | File | Generating function |
|---|---|---|
| 1 | `01_umap_celltype2.png` | `_fig01_umap_celltype2` |
| 2 | `03_stage_celltype_composition.png` | `_fig03_stage_celltype_composition` |
| 3 | `06_energy_distance_by_perturbation.png` | `_fig06_energy_distance_by_perturbation` |
| 4 | `05_ps_by_perturbation.png` | `_fig05_ps_by_perturbation` |
| 5 | `23_ps_by_celltype2.png` | `_fig23_ps_by_celltype2` |
| 6 | `24_ps_genotype_celltype_heatmap.png` | `_fig24_ps_genotype_celltype_heatmap` |
| 7 | `04_genotype_celltype_enrichment.png` | `_fig04_genotype_celltype_enrichment` |
| 8 | `13_lochness_by_celltype.png` | `_fig13_lochness_by_celltype` |
| 9 | `14_distance_space.png` | `_fig14_distance_space` |
| 10 | `07_ps_vs_distance.png` | `_fig07_ps_vs_distance` |
| 11 | `15_module_program_strength.png` | `_fig15_module_program_strength` |
| 12 | `17_program_enrichment.png` | `_fig17_program_enrichment` |
| 13 | `19_perturbation_summary.png` | `_fig19_perturbation_summary` |
| 14 | `28_umap_highlight_genotypes.png` | `_fig28_umap_highlight_genotypes` |

**Supplementary figures produced but not reproduced in this report:** `02` (UMAP by stage), `08`–`12` (distance/PS vs lochNESS scatters), `16` (program activity by state), `18` (module network — source tables not persisted), `20`–`22`, `25`–`27` (UMAP overlays and per-metric bar charts), and the 102 per-genotype UMAP panels. These are available in `figures/` and are useful for per-genotype inspection but do not add to the narrative above.

---

*Report generated from the analysis outputs in `results/diabetes_specific/` as of 2026-09-01. Every numerical claim above is traceable to a file listed in this appendix; where a claim rests on an assumption or is confounded, the caveat is stated inline.*
