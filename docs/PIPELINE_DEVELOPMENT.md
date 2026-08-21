# Perturb-seq Pipeline: Extended Analyses and Scalable Execution

## Overview

This document describes the extended analytical stages, modular architecture, and centralized scalable execution framework of the `perturbseq-pipeline` package.

The pipeline provides an end-to-end workflow for CRISPR pooled single-cell screens (Perturb-seq), taking raw count matrices or processed AnnData objects and producing:
1. Standard single-cell and guide-specific quality control (QC)
2. Guide assignment and multiplet classification
3. Normalization, high-variable gene (HVG) selection, embedding, and Leiden clustering
4. Directional perturbation-strength testing against dual control groups
5. Cluster-level perturbation enrichment testing (Fisher's exact, Cochran–Mantel–Haenszel, guide concordance, omnibus permutation)
6. Co-functional perturbation modules and co-regulated gene programs (regulome discovery)
7. Per-cell perturbation response scores (via the `pertps` / `PS_python` framework)
8. Continuous neighbourhood perturbation enrichment via lochNESS
9. Centralized scalable execution supporting datasets ranging from standard screens (~300k cells) to multi-million-cell pan-genome libraries (>2.6M cells)
10. Complete deliverables: processed `.h5ad`, structured tabular CSV outputs, publication-ready vector/raster figures, and a self-contained interactive HTML report.

---

## Pipeline Workflow

The complete analysis pipeline executes 11 sequential stages managed centrally by `perturbseq_pipeline.cli.run_pipeline`:

```text
 [1. Input Loading]
         │
         ▼
 [2. QC Filtering] ─────────────► [Cell & Gene QC Statistics]
         │
         ▼
 [3. Guide Assignment] ─────────► [Dominance / Multiplet Gate]
         │
         ▼
 [4. Normalization & Cluster] ──► [HVG -> PCA -> UMAP -> Leiden]
         │
         ▼
 [5. Perturbation Strength] ────► [Directional Knockdown vs NTC/Other]
         │
         ▼
 [6. Cluster Enrichment] ───────► [Fisher / CMH / Guide Concordance]
         │
         ▼
 [7. Modules & Programs] ───────► [Log2FC Matrix -> Modules (Spearman) & Programs (Pearson)]
         │
         ▼
 [8. PS Scoring] ───────────────► [Single-cell PS Scores & Supervised LDA]
         │
         ▼
 [9. lochNESS] ─────────────────► [k-NN Neighbourhood Enrichment (k=300)]
         │
         ▼
 [10. Output Writing] ──────────► [Processed H5AD, Guide Table, CSVs, Figures, Tarball]
         │
         ▼
 [11. HTML Report] ─────────────► [Self-contained Interactive Report]
```

### Execution Stages in `cli.py`

1. **Stage 1/11: Input Loading & Validation**: Resolves 10x MTX directories, companion guide matrices, or `.h5ad` inputs; merges sample metadata; applies `Config.validate()`; determines scaling execution mode (`standard` vs `large`).
2. **Stage 2/11: Quality Control**: Annotates mitochondrial, ribosomal, and hemoglobin genes; filters low-quality cells and unexpressed genes; records step-by-step filtering tables.
3. **Stage 3/11: Guide Assignment**: Determines dominant and runner-up guide counts per cell; applies dominance ratio and optional second-guide UMI gates; parses target gene identities.
4. **Stage 4/11: Normalization, Embedding & Clustering**: Performs library-size normalization and log1p transformation; identifies HVGs; computes PCA, k-NN graph, UMAP projection, and Leiden clustering. If `cluster.assigned_only: true`, optionally re-embeds singlets while preserving the all-cell embedding.
5. **Stage 5/11: Perturbation Strength**: Measures target gene knockdown in perturbed cells versus Non-Targeting Controls (`ntc`) and Other-Targeting Controls (`other`); calculates log2 fold changes and Benjamini–Hochberg FDR values.
6. **Stage 6/11: Cluster Enrichment**: Evaluates whether perturbation targets alter cluster occupancy using Fisher's exact test, stratified CMH tests across lanes, guide concordance verification, and omnibus permutation testing.
7. **Stage 7/11: Co-functional Modules & Gene Programs**: Constructs a perturbation × gene effect matrix; clusters genes into co-regulated programs (Pearson correlation) and perturbations into co-functional modules (Spearman correlation); identifies TF hubs and connectivity networks.
8. **Stage 8/11: Per-cell Perturbation Scores (PS Score)**: Executes per-cell signature scoring via `pertps`; stratifies cells into responders and non-responders/escapers; optionally constructs supervised LDA projections.
9. **Stage 9/11: lochNESS Neighbourhood Enrichment**: Quantifies continuous manifold over-representation across $k=300$ nearest neighbours without relying on discrete cluster boundaries.
10. **Stage 10/11: Output Writing**: Saves the integrated `.h5ad` containing expression counts, layers, and embedded guide matrices (`obsm['guide_counts']`); writes structured tables (`tables/`), diagnostic figures (`figures/`), figure manifest, and results archive (`.tar.gz`).
11. **Stage 11/11: HTML Report Generation**: Renders a standalone, self-contained HTML report with interactive data tables and embedded figures.

---

## Input Compatibility

The pipeline supports diverse sequencing chemistries, alignment pipelines, and single-cell data formats through `perturbseq_pipeline.io`:

| Input Layout | Configuration Key | Description |
|---|---|---|
| **Combined 10x MTX** | `input.mode: mtx`<br>`input.mtx_dirs: {lane: path}` | Standard 10x Genomics CellRanger output where GEX and CRISPR guide capture features are stored in a single matrix and differentiated by `features.tsv.gz`. |
| **Separated GEX & Guide MTX** | `input.mode: mtx`<br>`input.mtx_dirs: {lane: path}`<br>`input.guide_mtx_dirs: {lane: path}` | STARsolo layout where gene expression and guide barcodes are quantified independently. The pipeline matches cell barcodes and fills missing guide entries with zero counts. |
| **Integrated H5AD** | `input.mode: h5ad`<br>`input.h5ad: path.h5ad` | AnnData object with guide features already in `var` (`feature_types`), in an existing layer/slot, or with precomputed guide calls. |
| **Companion Guide H5AD** | `input.mode: h5ad`<br>`input.h5ad: path.h5ad`<br>`input.guide_h5ad: guides.h5ad` | Separate expression and guide AnnData files aligned by cell barcode (`obs_names`). |
| **Precomputed Guide Labels** | `input.mode: h5ad`<br>`input.guide_obs_column: col_name` | Datasets (such as KOLF or Replogle) with precomputed guide assignments in `obs` (e.g. `gene_target` or `genotype`). The pipeline parses targets directly without reconstructing guide count matrices. |
| **Barcode Guide Table** | `input.mode: h5ad`<br>`input.guide_table: table.txt` | Long-format `barcode -> guide -> count` lookup table (e.g., PS_python input format). |

---

## Guide Assignment and Classification

### Decision Gate
For count-based guide assignment, the pipeline computes top and second-highest guide UMIs per cell and evaluates:

$$\text{Assigned} = (\text{top} \ge \text{min\_umi}) \land (\text{top} > \text{dominance\_ratio} \times \text{second}) \land (\text{max\_second\_umi} < 0 \lor \text{second} \le \text{max\_second\_umi})$$

Cells are assigned to one of four mutually exclusive perturbation classes:
* **`targeting`**: Cell passed the assignment gate and carries a guide targeting a known gene.
* **`non-targeting`**: Cell passed the assignment gate and carries a guide matching non-targeting patterns (`guides.ntc_patterns`).
* **`ambiguous`**: Cell has guide counts but failed the dominance ratio or maximum runner-up UMI threshold.
* **`unassigned`**: Cell has zero detected guide counts.

### Scalable Execution
* **Sparse CSR & Numba Search**: For large guide libraries, `_csr_top_two_numba` and `_csr_top_two_python` search non-zero entries in sparse CSR format without dense matrix allocations.
* **Categorical Unique Parsing**: When precomputed labels are provided in `obs` (e.g., KOLF), target regular expressions are evaluated once per unique category rather than millions of times across all rows.

---

## Perturbation-Strength Analysis

Perturbation-strength testing (`perturbseq_pipeline.perturbation`) verifies whether a guide knock-down successfully depletes the target gene's own mRNA transcript.

* **Target Expression**: Evaluated on log-normalized counts (`layers['lognorm']` or `X`).
* **Dual Control Groups**:
  * **`ntc` (Non-Targeting Controls)**: Cells carrying non-targeting guides (unperturbed baseline).
  * **`other` (Other-Targeting Controls)**: Cells carrying guides targeting other genes.
* **Statistical Tests**: Mann–Whitney U test and Kolmogorov–Smirnov test.
* **Directional Hit Calling**: A perturbation is called an effective hit (`is_hit_<control>`) if:
  1. $\text{BH-FDR} < \text{fdr\_alpha}$ (default: $0.05$)
  2. $\log_2\text{FC} < \text{max\_log2fc\_for\_hit}$ (default: $0.0$)
* **Threshold Guards**: Minimum cell count (`min_cells_per_target`, default: 10) and minimum percentage of control cells expressing the target (`min_pct_expressing_control`, default: 1.0%).

---

## Cluster-Level Perturbation Enrichment

Cluster enrichment (`perturbseq_pipeline.enrichment`) tests whether gene perturbations drive cells toward or away from specific transcriptional states.

* **Pairwise Association**: $2 \times 2$ contingency tables for each target-cluster pair evaluated with Fisher's exact test and Haldane–Anscombe corrected odds ratios.
* **Stratified CMH Test**: When `enrichment.stratify_by` (e.g., `lane_id` or `batch`) is configured, a Cochran–Mantel–Haenszel test controls for batch composition differences.
* **Guide Concordance**: Computes the percentage of independent guides for a target gene that agree in enrichment direction, filtering out single-guide artefacts.
* **Omnibus Permutation Test**: Global Monte Carlo permutation test evaluating overall perturbation-cluster dependency across the full screen.

---

## Co-functional Modules and Co-regulated Programs

The modules stage (`perturbseq_pipeline.modules`) discovers regulatory structure inspired by regulome mapping approaches (e.g., Chen et al., *Nature* 2023):

```text
                Perturbation × Gene Effect Matrix (Log2FC vs Control)
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
Gene–Gene Correlation (Pearson)               Perturbation–Perturbation Correlation (Spearman)
            │                                               │
            ▼                                               ▼
  Co-regulated Programs (P1, P2, ...)           Co-functional Modules (M1, M2, ...)
            │                                               │
            └───────────────────────┬───────────────────────┘
                                    ▼
                      Module × Program Strength Matrix
                      Transcription Factor (TF) Hubs
                      TF–TF Directed Regulatory Edges
                      Module–Module Connectivity Network
                      Per-Cell Program Activity Scores
```

### Methodological Details
* **Candidate Gene Selection**: Highly variable genes (HVGs), cluster marker genes, and perturbation marker genes.
* **Hierarchical Clustering**: Average linkage hierarchical clustering applied to Pearson distance for genes and Spearman distance for perturbations.
* **Cluster Nomenclature**: Program labels (`P1`, `P2`, ...) and module labels (`M1`, `M2`, ...) are numbered cluster identifiers. Member genes and TFs are output in tables for downstream biological annotation.
* **Underpowered Protection**: Automatically skips execution if the screen contains fewer than `min_perturbations` or `min_genes`.

---

## Per-Cell Perturbation Scores (PS Score)

The PS score stage (`perturbseq_pipeline.ps_score`) interfaces with the `pertps` / `PS_python` framework to quantify perturbation response at single-cell resolution:

* **Biomarker Construction**: Selects top up- and down-regulated biomarker genes for each target against control baselines.
* **Per-Cell Scoring**: Calculates continuous perturbation scores ($0$ to $1$) separating confirmed knockdowns from unperturbed cells or escapers.
* **Supervised LDA Projection**: Builds an LDA embedding trained on perturbation labels to maximize separation between perturbation states.
* **Computational Safeguards**:
  * Supervised LDA visualization can be disabled via `ps_score.compute_lda_umap: false` while retaining all PS scoring and statistics.
  * In large mode, LDA projection uses a bounded, stratified cell subset capped by `ps_score.lda_large_max_cells` (default: $150,000$).

---

## lochNESS: Neighbourhood Perturbation Enrichment

Ported from `pertTF`, lochNESS (`perturbseq_pipeline.lochness`) measures local neighbourhood enrichment on the phenotypic manifold:

$$\text{lochNESS}_{i, g} = \frac{\text{Local Fraction of Target } g \text{ in } k\text{-NN of Cell } i}{\text{Global Fraction of Target } g} - 1$$

* **Neighbourhood Size**: Evaluated across $k=300$ nearest neighbours in PCA space.
* **Interpretation**: A score of $0$ reflects background expectation; positive values indicate localized accumulation on the manifold.
* **Large-Screen Optimization**: In large mode (`self_only: true`), `lochness_self` (the score of each cell for its own assigned perturbation) is computed directly in sparse chunks, avoiding the memory cost of materializing full multi-gigabyte $N_{\text{cells}} \times N_{\text{targets}}$ matrices.

---

## Centralized Scaling Architecture

### Central Decision Contract in `config.py`

Scaling decisions across all stages are centralized in `Config` via `ScalingConfig`:

```yaml
scaling:
  mode: auto                      # "auto", "standard", or "large"
  large_n_cells: 1000000          # Cell count threshold for automatic large mode
  large_n_perturbations: 5000     # Perturbation count threshold for automatic large mode
  marker_max_cells: 200000        # Maximum cells sampled for HVG/marker discovery
  effect_gene_chunk: 256          # Gene chunk size for effect matrix accumulation
  guide_chunk_size: 20000         # Cell chunk size for dense guide assignment
  guide_max_dense_elements: 20000000 # Dense element ceiling before forcing sparse CSR
  collect_between_stages: true    # Run gc.collect() between major stages in large mode
  log_memory: true                # Log RSS memory usage across pipeline stages
  report_preview_rows: 500        # Maximum table rows embedded in the HTML report
```

### Execution Mode Logic

The decision to activate scalable execution is governed by `Config.use_large_mode(n_cells, n_perturbations=None)`:

```python
def use_large_mode(self, n_cells: int, n_perturbations: Optional[int] = None) -> bool:
    if self.scaling.mode == "large":
        return True
    if self.scaling.mode == "standard":
        return False
    # "auto" mode:
    if n_cells >= self.scaling.large_n_cells:
        return True
    if n_perturbations is not None and n_perturbations >= self.scaling.large_n_perturbations:
        return True
    return False
```

### Stage-Specific Scalability Behaviors

| Module | Standard Mode | Large Mode |
|---|---|---|
| **`qc.py`** | Sequential per-cell filtering and recalculation | Reuses precomputed QC columns when available; combined single-pass boolean masks. |
| **`cluster.py`** | Full-matrix HVG dispersion calculation | Estimates HVGs on a stratified subset of `scaling.marker_max_cells` (200k cells); avoids full-matrix copies. |
| **`guides.py`** | Vectorized dense chunked top-two search | Sparse CSR Numba/Python search; categorical unique-label parsing for precomputed labels. |
| **`modules.py`** | Dense cells × genes slice operations | Sparse sufficient-statistics accumulation in chunks of `scaling.effect_gene_chunk` (256 genes); stratified marker discovery. |
| **`lochness.py`** | Computes full cell × target score matrix | Computes `lochness_self` directly without allocating multi-target dense score matrices. |
| **`ps_score.py`** | Computes all targets and full LDA/UMAP | Subsamples control cells to 50k per target; bounds LDA visualization to `ps_score.lda_large_max_cells` (150k cells). |
| **`cli.py`** | Retains full tables in memory | Truncates in-memory report tables to `scaling.report_preview_rows` (500 rows); forces garbage collection between stages. |

---

## Configuration Examples

### 1. Default Automatic Execution
```yaml
run:
  name: standard_run
input:
  mode: auto
  h5ad: data/screen.h5ad
scaling:
  mode: auto
```

### 2. Large Screen Without Supervised LDA Visualization
```yaml
run:
  name: kolf_large_screen
input:
  mode: h5ad
  h5ad: data/kolf_2.6m_cells.h5ad
  guide_obs_column: gene_target
scaling:
  mode: auto
ps_score:
  enabled: true
  compute_lda_umap: false
```

### 3. Forced Large Mode on High-Core Node
```yaml
scaling:
  mode: large
  effect_gene_chunk: 512
  marker_max_cells: 300000
  log_memory: true
```

---

## Pipeline Outputs

```text
results/<run_name>/
├── processed.h5ad                   # Final AnnData (expression counts, lognorm, obsm['guide_counts'])
├── report.html                      # Self-contained HTML report with embedded figures
├── tables/                          # Tabular CSV outputs
│   ├── qc_summary.csv
│   ├── clusters.csv
│   ├── perturbation.csv             # Formatted hit calls
│   ├── perturbation_full.csv        # Complete statistics for all targets
│   ├── enrichment.csv               # Fisher/CMH cluster enrichment
│   ├── cofunctional_modules.csv     # Module assignments
│   ├── gene_programs.csv            # Program assignments
│   ├── effect_matrix.csv            # Perturbation x gene log2FC matrix
│   ├── ps_score.csv                 # PS response summaries
│   ├── lochness.csv                 # lochNESS summaries
│   └── figure_manifest.csv          # Catalog of all generated plots
├── figures/                         # Diagnostic figures (PNG / PDF)
│   ├── qc/
│   ├── guides/
│   ├── clustering/
│   ├── perturbation/
│   │   └── per_gene/                # Individual volcano and expression plots
│   ├── enrichment/
│   ├── modules/
│   ├── ps_score/
│   └── lochness/
│       └── per_target/              # Individual neighbourhood maps
├── logs/
│   ├── run.log
│   └── resolved_config.yaml         # Fully resolved configuration for reproducibility
└── <run_name>_results.tar.gz        # Portable results archive (matrices excluded)
```

---

## Test Suite and Verification

The test suite validates pipeline integrity, edge cases, and numerical accuracy against synthetic ground-truth screens and published references:

```bash
PYTHONPATH=src pytest -v
```

### Test Coverage
* **`tests/test_scaling_config.py`**: Validates `ScalingConfig` defaults, standard vs large scale detection (Replogle vs KOLF), manual overrides, threshold triggers, YAML serialization, and schema validation.
* **`tests/test_modules.py`**: Tests co-functional module discovery, gene program recovery, control group fallback, hub significance gating, and signed module-program strength.
* **`tests/test_pipeline.py`**: Comprehensive end-to-end tests covering 10x MTX input, multilane processing, separate GEX/guide directories, H5AD companion files, precomputed labels, guide dominance rules, perturbation testing, Fisher/CMH enrichment, PS scores, lochNESS pertTF reference matching, output writing, and HTML report compilation.

---

## Scientific Safeguards and Design Principles

1. **Explicit Ambiguity Representation**: Ambiguous and multiplet cells are explicitly labelled and tracked rather than silently discarded or forced into single-guide classes.
2. **Centralized Scaling Decisions**: Operational mode decisions reside in `Config`, preventing conflicting heuristics across modules.
3. **Preservation of Scientific Invariants**: Large-scale optimizations modify memory allocation, chunking, and computational representations while preserving statistical methods, test statistics, and significance thresholds.
4. **Reproducibility**: The exact parameters, thresholds, and runtime settings used for every run are dumped to `logs/resolved_config.yaml`.
