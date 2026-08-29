# perturbseq-pipeline

A simple, reproducible Perturb-seq pipeline: from counts to a QC + clustering +
perturbation-strength report, in one command.

```bash
perturbseq-pipeline run --config config/demo.local.yaml
```

Every run produces three deliverables:

1. a processed **`.h5ad`**,
2. a self-contained **HTML report**, and
3. **all diagnostic figures** on disk — including the per-target figures that
   were too numerous to embed in the report.

---

## Biological Framework & What It Does

Perturb-seq screens measure complex cellular consequences across multiple complementary dimensions. Rather than collapsing these distinct biological phenomena into an arbitrary composite score, the pipeline evaluates each orthogonal layer along the perturbation cascade:

$$\text{Perturbation} \longrightarrow \text{Efficacy} \longrightarrow \text{Penetrance} \longrightarrow \text{Phenotype Magnitude} \longrightarrow \text{Topology} \longrightarrow \text{Phenotype Similarity} \longrightarrow \text{Mechanistic Organization}$$

| Biological Dimension | Pipeline Stage | Primary Question | Key Metrics / Methods |
|---|---|---|---|
| **Efficacy** (Target Knockdown) | Stage 5 | Did the perturbation deplete the targeted transcript? | $\log_2\text{FC}$, KS/Wilcoxon FDR, `% knockdown` |
| **Penetrance** (Per-Cell Response) | Stage 8 | What fraction of perturbed cells shifted into a distinct state? | Perturbation Score (PS), responder vs escaper fraction |
| **Phenotype Magnitude** (Global Displacement) | Stage 10 | How far is the high-dimensional cell distribution displaced from control? | **Energy Distance** ($E$-distance), MMD |
| **Statistical Evidence** (Significance) | Stage 10 | Is the global phenotype shift statistically significant? | Permutation **DistanceTest** empirical p-value & BH-FDR |
| **Manifold Topology** (State Localization) | Stage 9 | Where does the perturbation concentrate in continuous cell-state space? | **lochNESS** neighborhood density enrichment ($k=300$) |
| **Discrete State Enrichment** | Stage 6 | Does the perturbation over-represent specific discrete clusters? | Fisher's exact test / stratified CMH test, guide concordance |
| **Phenotype Similarity** (Distance Space) | Stage 11 | Which perturbations produce similar whole-cell phenotype distributions? | Pairwise Energy Distance matrix, PCoA coordinates, **Phenotype Modules** |
| **Mechanistic Organization** (Regulome) | Stage 7 | Which perturbations regulate similar downstream genes and programs? | **Co-functional Modules** (shared DE targets) & **Gene Programs** |

---

### The 14 Pipeline Stages

1. **Input Loading & Validation**: Multi-lane 10x MTX directories or AnnData H5AD, with automatic lane concatenation, guide/feature splitting, and sample metadata merging.
2. **Quality Control**: Standard single-cell QC (gene/UMI counts, mitochondrial, ribosomal, hemoglobin fractions) plus Perturb-seq guide QC (depth, MOI, dominance).
3. **Guide Assignment**: Dominance-ratio based single-guide calling per cell (`targeting`, `non-targeting`, `ambiguous`, `unassigned`).
4. **Clustering & Normalization**: Library-size normalization, log1p transformation, HVG selection, PCA, optional Harmony batch correction, UMAP embedding, and Leiden clustering.
5. **Perturbation Strength (Efficacy)**: Direct target knockdown assessment comparing target gene expression in perturbed vs control cells (two-sided and directional tests, log2FC, `% knockdown`, BH-FDR).
6. **Cluster Enrichment**: Tests whether perturbations favor discrete cell states via Fisher's exact test or stratified Cochran–Mantel–Haenszel (CMH) test controlling for batch.
7. **Co-functional Modules & Gene Programs (Regulome)**: Biclusters perturbation effect matrix into co-functional modules (Spearman correlation) and co-regulated gene programs (Pearson correlation), computing signed module-program strength and TF-hub connectivity.
8. **Per-cell Perturbation Response (PS Penetrance)**: Computes per-cell perturbation scores via [PS_python](https://github.com/weili-lab/PS_python) (`pertps`), separating confirmed responders from escapers.
9. **lochNESS Neighborhood Topology**: Continuous, cluster-free manifold neighborhood density enrichment ($k=300$) mapping where perturbations localize on the single-cell manifold.
10. **Perturbation Distance & Permutation DistanceTest**: High-dimensional multivariate distribution comparison against unperturbed control using Energy Distance (primary) and optional MMD (secondary), with finite-permutation `DistanceTest` empirical p-values and BH-FDR.
11. **Perturbation Distance Space & Phenotype Modules**: All-vs-all pairwise perturbation distance matrix (`tables/perturbation_distance_matrix.tsv`), Principal Coordinate Analysis (PCoA / classical MDS embedding in `tables/perturbation_space_coordinates.csv`), nearest phenotypic neighbors (`tables/perturbation_neighbors.csv`), and hierarchical clustering into Phenotype Modules (`tables/phenotype_modules.csv`).
12. **Master Perturbation Metadata & Integrated Visualizations**: Consolidates all target-level summaries into a unified reference table (`tables/perturbation_meta.csv`) and generates integrated cross-layer figures (Perturbation Atlas heatmap, PS $\times$ Distance map, Phenotype Space PCoA, Module concordance).
13. **Output Delivery & Lean H5AD**: Exports lean processed `.h5ad` storing cell-level annotations in `obs`/`obsm` while keeping large target tables and pairwise matrices in `tables/`.
14. **Interactive HTML Report & Manifest**: Compiles all diagnostic figures, summary cards, and table previews into a standalone shareable HTML report with figure manifest.

---

## Install

```bash
git clone https://github.com/weili-lab/perturbseq-pipeline.git
cd perturbseq-pipeline
pip install -e .

# optional extras
pip install -e ".[harmony]"   # Harmony batch correction across lanes
pip install -e ".[ps]"        # PS_python perturbation penetrance scoring
pip install -e ".[networks]"  # NetworkX layouts for TF hub graphs
pip install -e ".[demo]"      # gdown, for fetching demo datasets
pip install -e ".[gpu]"       # GPU acceleration extras (CuPy, cuML, rapids-singlecell)
pip install -e ".[dev]"       # pytest and developer tools
```

Requires Python >= 3.9. Runs on Linux/macOS/Windows, Colab, workstations, or HPC clusters. CPU execution is fully supported out of the box with zero GPU requirements.

---

## Quick start: the demo

One lane of a human ESC transcription-factor screen — 416 guides, 61 targets,
30 non-targeting controls.

```bash
python demo/fetch_demo_data.py --dest demo_data --write-config config/demo.local.yaml
perturbseq-pipeline run --config config/demo.local.yaml
```

Already have the data (e.g. on a mounted Drive)? Skip the download:

```bash
python demo/fetch_demo_data.py --source "/path/to/raw_counts" --dest demo_data
```

There is also a runnable notebook that walks through the whole thing:
**[`notebooks/demo_run_pipeline.ipynb`](notebooks/demo_run_pipeline.ipynb)**.

---

## Inputs

Start a config from the documented defaults:

```bash
perturbseq-pipeline init-config my_run.yaml
```

### Option 1 — 10x count matrices

Every directory needs `barcodes.tsv.gz`, `features.tsv.gz` and `matrix.mtx.gz`.
Which of the two layouts below you have depends on how the run was quantified.

#### 1.1 Guides and gene expression in one matrix

The CellRanger layout: one directory per lane, holding both `Gene Expression`
and guide (`Custom` / `CRISPR Guide Capture`) features, told apart by the third
column of `features.tsv.gz`. This is the ESC TF Perturb-seq screen.

```yaml
input:
  mode: mtx
  mtx_dirs:
    S1lane1: /path/to/filtered_feature_bc_matrix_S1lane1
    S1lane2: /path/to/filtered_feature_bc_matrix_S1lane2
metadata:
  file: my_samples.csv
cluster:
  batch_key: lane_id     # Harmony correction across lanes
```

The pipeline splits the two feature classes itself. If your file names the guide
class something else, set `input.guide_feature_types`.

#### 1.2 Gene expression and guides quantified separately

The STARsolo layout: each lane has two independent MTX directories, and
`features.tsv.gz` carries no usable class column — guides are often labelled
`Gene Expression` too, so there is nothing to split on. This is the THP-1 /
M0 / M1 screen:

```
count_matrices/{THP1,M0,M1}/{ch_1,ch_2}/
  GEX/filtered/    <- genes, called cells only
  sgRNA/raw/       <- guides, the entire barcode whitelist
```

Add `guide_mtx_dirs` alongside `mtx_dirs`, **using the same lane keys**:

```yaml
input:
  mode: mtx
  mtx_dirs:                                     # gene expression
    THP1_ch1: /path/THP1/ch_1/GEX/filtered
    M0_ch1:   /path/M0/ch_1/GEX/filtered
    M1_ch1:   /path/M1/ch_1/GEX/filtered
  guide_mtx_dirs:                               # guide counts, same keys
    THP1_ch1: /path/THP1/ch_1/sgRNA/raw
    M0_ch1:   /path/M0/ch_1/sgRNA/raw
    M1_ch1:   /path/M1/ch_1/sgRNA/raw
  var_names: gene_symbols

guides:
  # Strip only a trailing _<number>, so multi-token targets survive:
  #   ADGRV1_1 -> ADGRV1, gene_desert_1 -> gene_desert, non-targeting_20 -> non-targeting
  # The default first-delimiter split would give a target called "gene".
  target_regex: '^(.+)_\d+$'
  ntc_patterns: ["^non[-_.]?targeting$"]

metadata:
  file: my_samples.csv
cluster:
  batch_key: lane_id
```

Three things worth knowing about this layout:

**The keys must match exactly.** A lane in one mapping and not the other is
rejected at config load, rather than after a long read.

**The guide matrix is usually much larger than the cell set.** STARsolo emits
guide counts over the whole barcode whitelist — 737,280 barcodes against 36,364
called cells in the THP-1 run. The pipeline subsets it to the barcodes in the
expression matrix, filling any missing ones with zeros rather than dropping
those cells, and logs the match rate per lane (it was 100% for all three THP-1
channels). No overlap at all is an error, since that almost always means the two
matrices use different barcode formats.

**Point GEX at the called cells and guides at whatever exists.** In the THP-1
tree that is `GEX/filtered` and `sgRNA/raw` — `sgRNA` has no `filtered` output.

Check your guide naming before a long run:

```bash
python -c "
from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guides import parse_target_genes, is_non_targeting
cfg = Config.from_yaml('config/my_run.yaml')
names = ['ADGRV1_1', 'gene_desert_3', 'non-targeting_20']
t = parse_target_genes(names, cfg.guides)
print(dict(zip(names, t)), dict(zip(t, is_non_targeting(t, cfg.guides))))"
```

### Option 2 — an existing `.h5ad`

Guide information can arrive three ways; the pipeline detects them in order:

```yaml
input:
  mode: h5ad
  h5ad: /path/to/my_data.h5ad

  # (a) guide features already in var['feature_types'] — nothing else needed
  # (b) a companion guide count matrix:
  guide_h5ad: /path/to/my_guides.h5ad
  # (c) a pre-computed per-cell label, e.g. a Seurat 'genotype' column:
  guide_obs_column: genotype
  # (d) a barcode -> guide table (the PS_python demo layout):
  guide_table: BARCODE_10x_Merged.txt

  # Seurat exports often keep counts in X and log values in a layer:
  normalized_layer: logcounts
  # ...or use "X" when the object holds only normalized values and no counts:
  # normalized_layer: "X"
```

A barcode table lists one row per detected guide per cell, so a cell with two
guides appears twice. The pipeline resolves those with the **same dominance rule
as the count-matrix path** (top guide must clear `guides.min_umi` and beat the
runner-up by `guides.dominance_ratio`) rather than keeping whichever row came
last, which would pick a guide at random for every multiplet.

### Sample metadata

**Required for any run spanning more than one lane.** One row per lane, joined
on `lane_id`; every column is merged into `adata.obs` and travels with the
output `.h5ad`.

```csv
lane_id,sample,lane,cell_line,condition,replicate
S1lane1,S1,1,ESC,TF_screen,1
S1lane2,S1,2,ESC,TF_screen,1
```

---

## Outputs

```
results/<run>/
├── report.html                      # deliverable 2 — self-contained
├── processed.h5ad                   # deliverable 1 — includes the guide matrix
├── figures/                         # deliverable 3
│   ├── qc/                          # cell QC, before and after filtering
│   ├── guides/                      # Perturb-seq guide QC
│   ├── clustering/                  # PCA, UMAPs, cluster composition
│   └── perturbation/
│       ├── perturbation_volcano.png
│       ├── perturbation_waterfall.png
│       └── per_gene/                # EVERY target, not just those in the report
├── tables/                          # CSVs for all report tables
├── logs/  run.log + resolved_config.yaml
└── <run>_results.tar.gz             # shareable bundle, matrices excluded
```

### The guide barcode table

Every run also exports the guide count matrix as a long `barcode -> guide`
table (`<run>_guide_barcodes.txt`) — the format
[PS_python](https://github.com/weili-lab/PS_python) consumes. It was verified to
reproduce that project's `BARCODE_10x_Merged.txt` exactly: filtering the matrix
at >= 3 UMIs matches the original on per-cell totals and guides-per-cell for
100% of shared cells.

```yaml
output:
  write_guide_table: true
  guide_table_min_umi: 3
```

Two deliberate differences: the `gene` column uses the pipeline's target parser
(so `CD81.2` collapses to `CD81` instead of becoming its own target), and an
`assignment` column carries the pipeline's dominance-rule call so consumers get
the same per-cell answer. Rows are ordered with the dominant guide last, so even
a naive "last row wins" reader lands on the right guide. See
[`docs/ps_python_proposal.md`](docs/ps_python_proposal.md).

### The results archive

Every run bundles its outputs into one `.tar.gz` — the report, all figures,
tables and logs, with the `.h5ad` matrices left out so the archive stays small
enough to email or attach to a GitHub release. It unpacks into a single
directory named after the run.

```yaml
output:
  archive: true                 # set false to skip
  archive_name: null            # defaults to <run.name>_results.tar.gz
  archive_exclude: ["*.h5ad", "*.h5", "*.loom", "*.tar.gz"]
```

Patterns are matched against paths relative to the run directory (and against
bare filenames), so `"figures/perturbation/per_gene/*"` would drop just the
per-target figures.

Large outputs can be redirected off local disk (useful on Colab):

```yaml
output:
  large_file_dir: "/content/drive/MyDrive/.../pipeline"
  large_file_threshold_mb: 50
```

### The processed `.h5ad`

| Slot | Contents |
|---|---|
| `X`, `layers['lognorm']` | log1p of library-size-normalized counts |
| `layers['counts']` | raw integer counts |
| `obsm['guide_counts']` | the raw guide count matrix, sparse (cells x guides) |
| `uns['guide_names']`, `uns['guide_target_genes']` | guide IDs and their parsed targets |
| `obs['target_gene']` | assigned target, or `ambiguous` / `unassigned` / `non-targeting` |
| `obs['perturbation_class']` | `targeting` / `non-targeting` / `ambiguous` / `unassigned` |
| `obs['guide_id']`, `top_guide_count`, `second_guide_count` | guide-call diagnostics |
| `obs['total_guide_counts']`, `n_guides_detected` | guide depth and MOI |
| `obs['leiden']`, `obsm['X_umap']` | clustering and embedding |
| `obs[...]` | all sample metadata columns |

### One file, both matrices

The guide counts live **inside** the processed `.h5ad`, in
`obsm['guide_counts']`, so a run is a single file rather than a pair that can
drift apart. They sit in `obsm` rather than being concatenated onto `var`
because guide counts are not gene expression: putting them in `var` would feed
them to normalization, HVG selection and scaling along with the genes.

They stay sparse — on the THP-1 run that is 7.2M non-zeros in a 103,151 x 694
matrix, about 58 MB in memory against 286 MB dense. `obsm` also keeps the rows
tied to the cells through any subsetting, which two separate files do not.

```python
import scanpy as sc
adata = sc.read_h5ad("results/my_run/processed.h5ad")
guides = adata.obsm["guide_counts"]          # sparse, cells x guides
names  = adata.uns["guide_names"]            # column labels
```

A merged object can be fed straight back to the pipeline — the reader detects
`obsm['guide_counts']` and rebuilds the guide matrix, no companion file needed.

```yaml
output:
  merge_guides_into_h5ad: true   # guides inside the processed .h5ad
  guide_obsm_key: guide_counts
  write_guide_h5ad: false        # also write the old separate file
```

---

## Guide calling

For each cell the pipeline takes the highest and second-highest guide counts and
applies one rule:

```python
assigned = (
    top >= guides.min_umi
    and top > guides.dominance_ratio * second
    and (guides.max_second_umi < 0 or second <= guides.max_second_umi)
)
```

| Condition | Label in `obs['target_gene']` |
|---|---|
| top count is 0 | `unassigned` |
| top ≥ `min_umi`, top > `dominance_ratio` × second, and second within `max_second_umi` | the guide's target gene |
| anything else | **`ambiguous`** |

There is no separate "ambiguous threshold" — `ambiguous` is the fallback when a
cell *has* guide counts but fails the rule, either because its best guide is too
weak or because the runner-up is too close to it.

```yaml
guides:
  min_umi: 3            # the top guide must reach this many UMIs
  dominance_ratio: 2.0  # ...and exceed the runner-up by this factor
  max_second_umi: -1    # hard cap on the runner-up; -1 disables the gate
  detection_threshold: 3         # MOI statistics only — NOT used for assignment
  target_split_delims: ["_", "-", "."]   # AFF4_P1P2_1 -> AFF4
  target_regex: null             # override when targets contain a delimiter
  ambiguous_label: ambiguous     # the strings written into obs
  unassigned_label: unassigned
  ntc_label: non-targeting
```

### Tuning the ambiguous rate

**`dominance_ratio` is the knob that matters.** At 2.0 a cell with counts 40 and
25 is ambiguous (40 < 50); at 1.5 it would be assigned. That one value drives
most of the ambiguous rate — 24% of cells on the ESC screen. The prototype
notebooks used 1.2 in one and 2.0 in the other, which is why it is an explicit
key rather than a number buried in the code.

`min_umi` matters less on deeply sequenced guide libraries, where the top guide
is usually far above 3, but raising it is the right move when guide capture is
shallow and low-count calls are unreliable.

Watch out for **`detection_threshold`**, which looks similar but is only used for
the guides-per-cell and MOI statistics in the QC section. Changing it does not
move a single assignment.

### Removing droplet multiplets

A cell carrying genuine counts of a *second* guide is usually two cells in one
droplet. The dominance ratio alone does not catch those, because a ratio scales
with sequencing depth: at `dominance_ratio: 2.0` a cell with 1,000 and 100 UMIs
passes, even though 100 UMIs of a second guide is real signal rather than
ambient. `max_second_umi` puts an absolute cap on the runner-up, which does not
scale.

It is **off by default** (`-1`). To calibrate it, the THP-1 M0_ch1 channel was
compared against that study's own published cell set, which keeps only cells
strictly expressing one sgRNA (14,156 of 48,554 cells):

| Setting | Cells assigned | Recall | Precision | F1 |
|---|---|---|---|---|
| `-1` (off) | 30,208 | 0.970 | 0.455 | 0.619 |
| `max_second_umi: 5` | 12,345 | 0.832 | 0.954 | 0.889 |
| **`max_second_umi: 8`** | **14,580** | **0.920** | **0.893** | **0.906** |
| `max_second_umi: 10` | 15,563 | 0.942 | 0.857 | 0.897 |

Raising `dominance_ratio` instead does **not** work as well — its best setting
(20) reaches only F1 0.817, because it cannot distinguish a deep singlet from a
deep doublet. The two knobs address different things and are worth setting
independently.

Note this is a property of the *library and chemistry*, not a universal
constant: the runner-up count on Seurat-retained cells had a median of 3 and a
99th percentile of 16, whereas rejected cells sat at a median of 33. Re-derive
it for a new dataset rather than copying the number.

### What happens to ambiguous cells

They are **kept** in the object and counted in the report, but excluded from
perturbation testing and from *both* control groups. So loosening
`dominance_ratio` does not merely relabel cells — it moves them into the tested
populations. On the four-lane run that category holds 27,566 cells (25.4%),
so the setting has real leverage over every downstream result.

One place ambiguous cells still act is **clustering**, which by default runs on
all QC-passing cells. Multiplets pass gene-expression QC and fragment the
embedding into many small clusters (on M0_ch1, 123 instead of 37).

`cluster.assigned_only: true` splits the run into two objects rather than
discarding anything:

| | Cells | Written as | Used for |
|---|---|---|---|
| all cells | every QC-passing cell | `<name>_all_cells.h5ad` | the `all_cells_*` UMAPs, where ambiguous/unassigned cells are visible |
| analysed | guide-assigned singlets | `<name>.h5ad` | clustering, perturbation, enrichment, PS scores, lochNESS |

Each is embedded independently and is internally complete, so **cluster labels
do not carry across the two files**. Set `output.write_unfiltered_h5ad: false`
to keep the figures but skip the extra (large) matrix.

The same rule is applied when guides arrive as a barcode table
(`input.guide_table`), reading the same two keys, so a run from a count matrix
and a run from a barcode table produce identical per-cell calls.

Non-targeting guides are detected by pattern (`non`, `non_targeting`, `NTC`,
`scramble`, …) via `guides.ntc_patterns` and used as the preferred control group.

---

## Perturbation Distance & DistanceTest (Stage 10)

### Biological Purpose & Concept
While target log2FC measures **direct efficacy** (did the guide deplete its targeted transcript?), **Perturbation Distance** measures **global phenotypic magnitude**: how far did the perturbation displace the high-dimensional cell distribution away from the unperturbed control population?

These two metrics answer distinct biological questions:
* **Strong target knockdown + small Energy Distance**: Highly effective molecular targeting with relatively specialized or minimal global transcriptional consequence.
* **Modest target knockdown + large Energy Distance**: Downstream signal amplification, transcription factor cascade activation, or broad cellular state transitions.

### Primary Metric: Energy Distance
Evaluated in latent embedding space (e.g. PCA space `adata.obsm['X_pca']`):
$$D^2(P, Q) = 2\,\mathbb{E}_{X \sim P, Y \sim Q}[\|X - Y\|_2] - \mathbb{E}_{X, X' \sim P}[\|X - X'\|_2] - \mathbb{E}_{Y, Y' \sim Q}[\|Y - Y'\|_2]$$
Energy distance is zero if and only if $P = Q$. Unlike mean centroid Euclidean distance, Energy Distance captures higher-order distribution moments including variance shifts, shape changes, and multimodality. An optional secondary metric is **Maximum Mean Discrepancy (MMD)** with a Gaussian RBF kernel.

### Permutation DistanceTest
Statistical significance is assessed via label permutation testing:
$$p = \frac{1 + \sum_{b=1}^B \mathbf{1}(D_{\text{perm}, b} \ge D_{\text{observed}})}{1 + B}$$
followed by Benjamini–Hochberg False Discovery Rate (BH-FDR) multiple testing correction across all tested perturbations.
* **Energy Distance** = effect magnitude.
* **Distance FDR** = statistical confidence.

### Scalable Bounded Sampling
To prevent intractable pairwise matrix allocations on large datasets (such as Replogle or KOLF), cells are sampled deterministically:
```yaml
distance:
  enabled: true
  representation: X_pca
  primary_metric: edistance
  max_cells_per_target: 2000
  max_control_cells: 5000
  n_permutations: 1000
  random_seed: 123
  fdr_threshold: 0.05
```

---

## Perturbation Distance Space & Phenotype Modules (Stage 11)

Where Stage 10 asks *"How far does each perturbation move from control?"*, **DistanceSpace** asks:
> **Which perturbations generate similar whole-cell phenotypic states?**

### Outputs & Deliverables
* `tables/perturbation_distance_matrix.tsv`: All-vs-all symmetric target $\times$ target Energy Distance matrix (stored outside H5AD to prevent memory bloat).
* `tables/perturbation_space_coordinates.csv`: Low-dimensional Principal Coordinate Analysis (PCoA / classical MDS) embedding coordinates.
* `tables/perturbation_neighbors.csv`: Top-$k$ nearest phenotypic neighbors ranked for every perturbation.
* `tables/phenotype_modules.csv`: Hierarchical clustering partition into discrete **Phenotype Modules**.

### DistanceSpace Scaling: $O(P^2)$
Pairwise perturbation analysis scales quadratically as $\frac{P(P - 1)}{2}$. For ~1,800 perturbations in the Replogle dataset, this represents ~1.62 million pairwise distance evaluations. DistanceSpace is therefore substantially more intensive than Distance-vs-control. We recommend:
* Running Distance & DistanceTest for routine phenotype magnitude quantification.
* Enabling DistanceSpace when all-vs-all perturbation phenotypic relationships and manifolds are scientifically required.

### Phenotype Modules vs Co-functional Modules
The pipeline explicitly discovers and distinguishes two complementary modular structures:
* **Co-functional Modules** (Stage 7, `tables/cofunctional_modules.csv`): Discovered from shared downstream differential expression profiles ($\log_2\text{FC}$ vectors across genes). *Which perturbations regulate the same downstream genes?*
* **Phenotype Modules** (Stage 11, `tables/phenotype_modules.csv`): Discovered from pairwise Energy Distances in single-cell latent space. *Which perturbations produce similar geometric distributions across cellular states?*

---

## Master Perturbation Metadata & Integrated Visualizations (Stage 12)

The pipeline integrates all target-level statistics into a unified master reference table:
`tables/perturbation_meta.csv`.

| Column | Source Stage | Biological Concept |
|---|---|---|
| `target_gene` | Metadata | Target identifier |
| `n_cells` | QC / Guide calling | QC-passing cell count |
| `target_log2fc` | Stage 5 | Direct target transcript knockdown ($\log_2\text{FC}$) |
| `target_pct_kd` | Stage 5 | Percentage depletion of target transcript |
| `target_fdr` | Stage 5 | Statistical significance of target depletion |
| `is_effective_hit` | Stage 5 | Binary flag: statistically verified knockdown |
| `ps_mean`, `ps_median` | Stage 8 | Per-cell Perturbation Score (PS) central tendencies |
| `ps_responder_fraction` | Stage 8 | Cellular penetrance: fraction of confirmed responders |
| `ps_escaper_fraction` | Stage 8 | Fraction of cells escaping perturbation phenotype |
| `lochness_mean`, `lochness_peak` | Stage 9 | Continuous manifold neighborhood density enrichment |
| `energy_distance`, `mmd_distance` | Stage 10 | Global phenotype displacement magnitude vs control |
| `distance_pvalue`, `distance_fdr` | Stage 10 | Permutation DistanceTest statistical confidence |
| `distance_significant` | Stage 10 | Binary flag: statistically significant phenotype shift |
| `cofunctional_module` | Stage 7 | Co-functional module (shared DE target regulation) |
| `phenotype_module` | Stage 11 | Phenotype module (shared manifold state distribution) |

> **Architectural Principle**: This table is an integrated reference matrix, **never** an arbitrary composite scalar score. Target efficacy, cellular penetrance, manifold topology, and phenotypic distance represent distinct, non-fungible biological questions.

### Integrated Figures
* `figures/perturbation_atlas.png`: Heatmap overview of Z-scored efficacy, PS penetrance, lochNESS topology, and Energy Distance across top perturbations.
* `figures/ps_vs_distance_map.png`: Scatter plot mapping Cellular Penetrance (PS) on the Y-axis against Global Phenotypic Distance on the X-axis.
* `figures/perturbation_phenotype_space.png`: PCoA projection of Perturbation Distance Space colored by Phenotype Modules.
* `figures/module_concordance.png`: Cross-tabulation heatmap and mutual information metrics between Co-functional Modules and Phenotype Modules.

---

## Lean H5AD Storage Policy

To prevent single-cell objects from exhausting host memory, the pipeline enforces a strict storage separation:

| Granularity | Location | Deliverables |
|---|---|---|
| **Cell $\times$ 1 value** | `adata.obs` | `target_gene`, `leiden`, `ps_score`, `ps_quadrant`, `lochness_self` |
| **Cell $\times$ Feature** | `adata.obsm` / `layers` | `counts`, `lognorm`, `X_pca`, `X_umap`, `X_lda_umap`, `guide_counts` |
| **Target $\times$ 1 summary** | `tables/perturbation_meta.csv` | Target efficacy, PS penetrance, lochNESS, Energy Distance, module calls |
| **Target $\times$ Target** | `tables/` (TSV/CSV) | `perturbation_distance_matrix.tsv`, `perturbation_space_coordinates.csv` |
| **Target $\times$ Gene** | `tables/` (CSV) | `effect_matrix.csv`, `gene_programs.csv`, `module_program_strength.csv` |
| **Networks & Profiles** | `tables/` (CSV) | `tf_edges.csv`, `tf_hubs.csv`, `compute_profile.csv` |

Large matrices and target tables are never stuffed into `adata.uns`.

---

## Storage, Scaling, and Compute Architecture

The pipeline enforces a strict three-tier separation of concerns:

```
Storage / Data Access (in_memory / backed / auto)
        │
        ▼
Biological Analysis Modules (STANDARD / LARGE)
        │
        ▼
Compute Backend (CPU / GPU / AUTO)
```

### 1. Storage & Data Access (`storage.*`)
* **Modes**: `auto` (default), `in_memory`, or `backed` (read-only H5AD backing for expression matrices with cells $\ge$ `backed_threshold_cells`, default: 1,000,000).
* **Decoupled Data Access**: Analysis modules query only required representations via `perturbseq_pipeline.data_access` without materializing full dense matrices.
* **Shared Multiprocessing Arrays**: Low-dimensional representations (`X_pca`) are memory-mapped/shared across workers with zero AnnData serialization overhead.

### 2. Biological Scaling Modes (`scaling.*`)

| Dataset Class | Approximate Scale | Scaling Mode (`scaling.mode`) | Default Storage Mode | Default Backend (`compute.backend`) | Execution Strategy |
|---|---|---|---|---|---|
| **Small Screen** | $< 100\text{k}$ cells | `STANDARD` | `in_memory` | `auto` (CPU) | In-memory processing, CPU multiprocessing |
| **Standard Screen (Replogle)** | $\sim 300\text{k}$ cells | `STANDARD` | `in_memory` | `auto` (CPU / selective GPU) | CPU multiprocessing + optional GPU dense linear algebra |
| **Large Screen** | $\sim 1\text{M}$ cells | `LARGE` / `AUTO` | `auto` / `backed` | `auto` (CPU / selective GPU) | Streaming/chunked CPU statistics + optional GPU |
| **Million-Cell (KOLF)** | $\sim 2.66\text{M}$ cells | `LARGE` | `backed` | `auto` (CPU / selective GPU) | Memory-bounded sparse CPU + optional GPU acceleration |

### 3. Accelerated Distance & Permutation DistanceTest
* **Exact $O(n^2)$ Energy Distance Identity**:
  $$S_Y = S_{total} + S_X - 2 R_X, \quad E^2(X, Y) = \frac{2 (R_X - S_X)}{n \cdot m} - \frac{S_X}{n^2} - \frac{S_Y}{m^2}$$
  Permutation null sampling reduces from $O((n+m)^2)$ submatrix slicing down to $O(n^2)$ row-sum evaluation, speeding up DistanceTest by **45x–200x** with 100% mathematical and statistical exactness.
* **Zero AnnData Worker Serialization**: Workers receive only target slice indices and shared embedding buffers.

### 4. CPU Multiprocessing vs Selective GPU Acceleration
* **CPU Multiprocessing**: Embarrassingly parallel statistical routines (perturbation testing, cluster enrichment Fisher/CMH tests, DistanceTest permutations) execute across worker pools with `blas_threads_per_worker: 1` to prevent CPU oversubscription.
* **Selective GPU Acceleration**: GPU acceleration is optional and applied only to dense linear algebra (correlation matrices, RAPIDS single-cell neighbors/UMAP), with automatic VRAM safety checks (`gpu_memory_fraction: 0.80`) and CPU fallback.
* **SLURM Cluster Awareness**: Detects `SLURM_CPUS_PER_TASK`, `SLURM_CPUS_ON_NODE`, and CPU affinity automatically.

#### SLURM HPC Job Script Example
```bash
#!/bin/bash
#SBATCH --job-name=perturbseq_run
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=04:00:00

# Run with CPU multiprocessing using all 16 allocated SLURM cores:
perturbseq-pipeline run --config config/my_run.yaml
```


---

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

The suite includes comprehensive unit tests verifying hardware detection, SLURM parsing, deterministic backend resolution, seed reproducibility, and serial vs parallel execution equivalence.

---

## Repository layout

```
src/perturbseq_pipeline/   io · qc · guides · cluster · perturbation · distance · modules · ps_score · lochness · meta · plots · report · compute · cli
config/                    default.yaml · demo.yaml · reploge.yaml · kolf.yaml
demo/                      fetch_demo_data.py · sample_metadata.csv
notebooks/                 demo_run_pipeline.ipynb · prototype/ (original analyses)
tests/                     synthetic data generator + end-to-end tests + compute unit tests
```

`CLAUDE.md` records the project conventions, including where large files belong.

---

## Development notes

For implementation details, scaling behavior, and documentation of the extended Perturb-seq analyses, see [`docs/PIPELINE_DEVELOPMENT.md`](docs/PIPELINE_DEVELOPMENT.md) and [`docs/methods.md`](docs/methods.md).

