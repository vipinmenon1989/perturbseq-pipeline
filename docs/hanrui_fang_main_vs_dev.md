# perturbseq-pipeline: `main` vs `dev` for the Hanrui Fang dataset

Read-only comparison of the two branches (local repository preferred over GitHub;
`main` inspected through a detached git worktree at `../perturbseq-pipeline-main`,
`dev` through the working checkout). Nothing was reset, rebased or overwritten.

| | `main` | `dev` (run as branch `feature/basic-qc-hanrui`) |
|---|---|---|
| Commit | `f5a8fa0651dac68b31a16680aeabe612087ce2ea` | `de12b52ce73afbd6ce89ec4b1c99d6d91be4fceb` (dev tip, 2026-09-01) + `37c536b74190badaaaee81937b69663b200306cc` (basic-QC stage, 2026-09-13) |
| Date | 2026-08-14 | 2026-09-01 / 2026-09-13 |
| Relation | `origin/main` | 10 commits ahead of `main` (+1 feature commit); `main` has nothing `dev` lacks |
| Source size | 13 modules, ~7.5 k lines | 24 modules, ~37 k lines |

The feature commit `37c536b` only adds an optional stage reachable through `run.stop_after: qc`;
the default 14-stage analysis path executed here is the `dev` code, with two default-value
changes noted below (`guides.ntc_patterns`, `io.write_h5ad` nullable-string opt-in).

## Feature-by-feature comparison

| Item | `main` | `dev` |
|---|---|---|
| Input formats (`input.mode`) | `auto / mtx / h5ad`; `mtx_dirs` (dict or list), `guide_mtx_dirs`, `h5ad`, `guide_h5ad`, `guide_table`, `guide_obs_column` | identical `InputConfig`; plus a `samples:` block (per-well `gex_h5`, `guide_fastq_dir`, `guide_matrix`) usable only with `stop_after: qc` |
| 10x HDF5 read directly | **no** (`sc.read_10x_h5` absent) | **not on the analysis path**; `io.read_10x_h5` exists but is only called by the basic-QC stage |
| Separate GEX + guide matrices | yes: `input.guide_mtx_dirs`, one dir per lane key; `_read_guide_mtx` matches barcode strings exactly (suffix `-1` included), zero-fills cells without guide rows, raises on zero overlap | identical code |
| Guide barcode table | yes (`input.guide_table*`), h5ad mode only | identical |
| Standard GEX QC metrics | scanpy `calculate_qc_metrics(qc_vars=mt,ribo,hb)`: `n_genes_by_counts`, `total_counts`, `pct_counts_mt/ribo/hb` (+log1p); mt=`MT-`, ribo=`RPS/RPL`, hb=`^HB[^(P)]` | identical (+ `pct_counts_in_top_20_genes` and flag columns in the QC stage only) |
| Guide QC metrics | `top_guide_count`, `second_guide_count`, `total_guide_counts`, `n_guides_detected` (> `detection_threshold`), `perturbation_class`; `guide_qc` summary table (MOI, multiplet-like cells, top:second ratio) | identical on the analysis path |
| Default QC thresholds | `min_genes_per_cell 200` (prefilter), `min_cells_per_gene 3`, `min_genes_final 1000`, `max_pct_mt 20`, `max_pct_hb null`, `min_counts_per_cell null`; global, applied to the pooled matrix; order: prefilter → metrics → filter | identical defaults and order |
| Guide-assignment defaults | `min_umi 3`, `dominance_ratio 2.0`, `max_second_umi -1`, `detection_threshold 3`; rule `top ≥ 3 & top > 2×second` → assigned, else `ambiguous` (if any counts) or `unassigned`; target from guide id via `target_split_delims ["_","-","."]` | same rule; adds `target_feature_column` / `ignored_target_values` (authoritative target from guide metadata) and `^no[-_. ]?target` in the default `ntc_patterns` |
| Before/after QC outputs | `plot_qc(before/after filtering)`, tables `qc_steps` (post-prefilter), `qc_summary` (post-filter, per lane) | identical |
| All-cells object | `output.write_unfiltered_h5ad: true` is **only honoured when `cluster.assigned_only: true`**; QC-failed cells are never written | identical defect on the analysis path; the basic-QC stage writes true all-cells objects |
| Cell-count tables | `qc_steps`, `qc_summary`, `guide_assignment`, `assignment_per_lane`, `guide_representation`, `clusters` | same + `perturbation_distance`, `perturbation_meta`, `compute_profile`, ... |
| Perturbation-expression test | per target vs `ntc` and `other` controls on `layers["lognorm"]`: two-sided KS + one-sided Mann-Whitney (`less`); `log2fc = log2((mean(expm1 p)+0.01)/(mean(expm1 c)+0.01))`; `pct_knockdown`; hand-written BH; hit = `ks_fdr < 0.05 & log2fc < 0` | identical statistics (+ LARGE-mode implementation above 1 M cells) |
| FDR | Benjamini–Hochberg (`perturbation.benjamini_hochberg`, NaN-tolerant) | identical |
| `log10FDR` convention | **no such column in any table**; plots use `-np.log10(clip(fdr, 1e-300, 1))`, labelled "-log10 FDR (KS test)" | identical; DEV-only figures also use `-log10(FDR)` |
| Biological replicate handling | metadata columns merged into `obs`; `cluster.batch_key` (Harmony) optional; `enrichment.stratify_by` (CMH) optional; the perturbation test pools all cells, never replicate-aware | identical + `distance.stratify_by` |
| Default normalisation / clustering | `normalize_total(target_sum=None)` → `log1p` → HVG 3000 → scale (max 10) → PCA 50 (arpack) → neighbours 15 → UMAP (min_dist 0.5) → Leiden 1.0 (igraph); `batch_key null`, `assigned_only false` | identical defaults |
| Figures | 11 `plot_*` families: qc, guides, clustering, perturbation(+per_gene), enrichment(+per_target), ps_score(+per_target, lda), lochness(+per_target), modules | same 11 + distance, distance_space, atlas, module concordance; QC-stage figures |
| Output directory | `<outdir>/{logs,figures/<section>,tables/*.csv,processed.h5ad,report.html,<name>_results.tar.gz,<name>_guide_barcodes.txt}` | identical layout |
| Tests (counted) | 88 tests in 2 files | 240 tests in 12 files |
| Tests (run on SLURM, this env) | see "Run outcomes" | 247 passed (job 20045137) |
| Required dependencies | scanpy, anndata, numpy, pandas, scipy, matplotlib, seaborn, leidenalg, igraph, statsmodels, jinja2, pyyaml | same + pertpy (never imported), joblib, threadpoolctl, psutil, h5py, openpyxl, scikit-image; `gpu` extra |
| SLURM / HPC support | none | `compute.py` (SLURM CPU detection, optional GPU, CPU fallback), `scaling`/`storage` config, sbatch templates |
| H5AD input support | yes (`input.mode: h5ad`); guides recovered from `var[feature_types]` (`split_features`), or `guide_h5ad`, `guide_table`, `guide_obs_column`; `counts_layer` / `normalized_layer` honoured (`apply_layer_choices`) | identical code (`io._load_h5ad`, `split_features`) |
| Feature-type splitting | `split_features`: GEX = `var[feature_type_column] == gex_feature_type`; guides = `isin(guide_feature_types)`; guides re-indexed by `var["gene_ids"]`, original name kept as `guide_symbol`; extra guide var columns preserved | identical |
| Guide-count handling (h5ad mode) | guide AnnData over the same cells; assignment via top-2 dominance on raw UMIs; merged back into `obsm["guide_counts"]` at output | identical; in addition `target_feature_column` reads the target from a guide `var` column (e.g. `target_gene_name`) |
| Cluster enrichment | `enrichment.enabled` (default true): per target × Leiden cluster odds ratios vs `ntc`/`other`, BH FDR, optional CMH `stratify_by`, guide concordance, permutation omnibus | identical module |
| Optional dependencies | `harmony`, `demo`, `networks`, `ps` (pertps), `dev` | same + `gpu`; hard deps add pertpy (unused), joblib, threadpoolctl, psutil, h5py, openpyxl, scikit-image |
| Disabling advanced modules | `modules.enabled`, `ps_score.enabled`, `lochness.enabled` exist; no distance / distance-space / meta stages | `modules`, `ps_score`, `lochness`, `distance`, `distance_space`, `meta_analysis` all have `enabled`; `visualization.*` toggles the atlas/space figures |
| Branch-specific issues | `write_h5ad` lacks the anndata ≥ 0.11 nullable-string opt-in → h5ad writing was expected to fail with anndata ≥ 0.11 — **not reproduced**: the comparison run wrote `processed.h5ad` fine; no `target_feature_column`, so the `NO-TARGET` label parses to `NO` under default delimiters and controls are lost unless `target_split_delims` **and** `ntc_patterns` are both overridden | `pertpy` is an unused hard dependency; stages 10–12 (distance, distance space, meta) default on; `guides.var["target_gene"]` written to a copy, so `uns["guide_target_genes"]` is empty (shared with `main`); `ps_score` skips cleanly when `pertps` is missing |

Shared limitation relevant to this dataset: the assignment rule is **single-guide**. Every cell in
this library carries one scaffold-A and one scaffold-C guide, so cells with two comparable guides
are labelled `ambiguous` by design of the rule, on both branches.

## How guide labels are interpreted here

Guide features are written as `id = <TARGET>_<n>`, `name = <raw design label>` (e.g. `NO-TARGET_1` /
`NO-TARGET`, `LIPA_rs1412444_2` / `LIPA (rs1412444)`). With shipped defaults **both** branches parse
`NO-TARGET_1` to target `NO` (first delimiter is `-`) and classify the controls as `targeting`.

* `dev` config used here: `guides.target_feature_column: gene_symbols` (the 10x "name" column) and
  `ntc_patterns` extended with `^no[-_. ]?target`. Controls → `non-targeting`; targets keep the exact
  design label, so rsID-specific labels stay distinct (but are then not found as gene symbols).
* `main` config used here: `target_split_delims: ["_"]` + the same extra pattern. Controls →
  `non-targeting`; `LIPA_rs1412444_n` collapses onto `LIPA`.

These are guide-metadata interpretation settings, not QC or statistical tuning.

## Run outcomes (MTX-mode comparison, 2026-09-13 first pass)

All jobs ran on SLURM inside the `perturbseq-pipeline` conda env (Python 3.11.15, scanpy 1.11.5,
anndata 0.12.19, pertps 0.1.0 installed).

| Job | Branch | What | Result |
|---|---|---|---|
| 20045140 | `main` | full pytest suite (`PYTHONPATH=perturbseq-pipeline-main/src`) | **88 passed** (7.5 min) |
| 20045137 | `dev` | full pytest suite | **247 passed** (11 min) |
| 20045139 | – | input preparation (`jobs/prepare_hanrui_inputs.py`) | 4 wells extracted; guide/GEX barcode overlap 100 % in every well |
| 20045141 | `main` | default-parameter run, HF011A + HF011B (`config/Hanrui_fang_main_default.yaml`) | completed, 15 min, 21.8 GB peak; `processed.h5ad` (2.6 GB) and `report.html` written |
| 20045142 | `dev` | default-parameter run, HF011A + HF011B (`config/Hanrui_fang_dev_default.yaml`) | completed, 18 min, 21.4 GB peak; all 14 stages incl. distance / distance space / meta |

Both default runs are numerically identical wherever the code is shared:

| Quantity | `main_default` | `dev_default` |
|---|---:|---:|
| Cells loaded / after prefilter (≥ 200 genes) | 82,914 / 82,911 | 82,914 / 82,911 |
| Cells after `min_genes_final ≥ 1000` / `pct_mt < 20` | 81,877 / 81,859 | 81,877 / 81,859 |
| Genes after `min_cells_per_gene ≥ 3` | 26,440 | 26,440 |
| Guide classes (targeting / non-targeting / ambiguous / unassigned) | 24,750 / 13,481 / 43,628 / 0 | identical |
| Distinct targets assigned | 42 (rsID labels collapse onto `FHL3`, `LIPA`, `ILRUN`) | 44 (rsID labels kept distinct) |
| Targets tested / effective (KS-FDR < 0.05 & log2FC < 0 vs NTC) | 35 / 24 | 34 / 24 |
| Targets skipped | 7 | 10 (`BNC2`, `CBWD1`, `RAPGEF5` absent after gene filtering; `SMIM22` not expressed in controls; `CEBPb`, `C6orf106`, `CCBL2` non-HGNC labels; three `(rsID)` labels) |
| Per-target `log2fc_ntc` | identical for 32 common targets; differs only for `FHL3` (+581 rsID cells) and `LIPA` (+683 rsID cells, Δlog2FC = 1.34) | – |
| Warnings in `run.log` | 1 (unused manifest rows HF012A/B, expected for the 2-well subset) | 1 (same) |
| Figures written | 226 | 356 |

The anticipated `main` h5ad-writing failure (anndata nullable strings) did **not** occur in this
environment; `main` wrote `processed.h5ad` successfully. The earlier audit's concern is therefore not
a blocker for `main`.

## Decision

**Selected branch: `dev` (executed from `feature/basic-qc-hanrui`, i.e. dev `de12b52` plus the
basic-QC commit `37c536b`).**

Rationale, based on what actually ran on this dataset rather than on feature count:

1. Both branches load the converted data, pass their own test suites (88 / 247) and produce identical
   QC and guide-assignment counts, so compatibility is equal.
2. `dev` is the only branch with `guides.target_feature_column`, which lets the raw design labels be
   used verbatim: the `NO-TARGET` controls are recognised without rewriting guide ids, and the
   rsID-specific guide sets (`FHL3 (rs114296424)`, `ILRUN (rs16878812)`, `LIPA (rs1412444)`) stay
   separate from the gene-level guide sets instead of being silently merged (on `main` this changes
   the `LIPA` log2FC by 1.34).
3. `dev` provides the HPC plumbing (SLURM CPU detection, compute/scaling/storage policy, memory
   logging) and the basic-QC stage used to quantify the guide FASTQs, so the whole analysis is
   reproducible from one repository state.
4. Cost of `dev`: three extra default-on stages (distance, distance space, meta) and unused
   dependencies; on this dataset they added ~3 min and no failures.

Caveats that apply to **both** branches and are carried into the final analysis: the single-guide
dominance rule labels 53 % of cells ambiguous in this dual-guide (A + C) library; the pipeline never
writes QC-failed cells (the pre-QC object used for before/after figures comes from the basic-QC
stage); design labels that are not HGNC symbols are untestable without an alias table.


## h5ad-mode comparison (core workflow, this run)

Both branches were run on the **same combined H5AD** (`work/Hanrui_fang/Hanrui_fang_combined.h5ad`,
163,991 cells × 38,606 genes + 560 guide features) with default QC / clustering / perturbation
settings and the advanced modules disabled (`main`: modules, ps_score, lochness off; `dev`: those plus
distance, distance_space, meta_analysis off). Earlier MTX-mode outputs in the same directories were moved
to `stale_mtx_mode_run_20045141_2/` subfolders.

| Job | Branch | Result |
|---|---|---|
| 20045157 | `dev` | pytest **248 passed** (247 + new all-cells checkpoint test) |
| 20045175 | `main` | `config/Hanrui_fang_main_default.yaml`, 12 min, 37.8 GB peak, 0 warnings |
| 20045176 | `dev` | `config/Hanrui_fang_dev_default.yaml`, 16 min, 37.4 GB peak, 0 warnings |
| 20045177 | `dev` (final) | `config/Hanrui_fang.yaml` → `results/Hanrui_fang/`, 15 min, 38.4 GB, 0 warnings; numerically identical to 20045176 |

| Quantity | `main_default` | `dev_default` / final |
|---|---:|---:|
| Loaded → prefilter (≥ 200 genes) → ≥ 1000 genes → mt < 20 % | 163,991 → 163,868 → 161,649 → 161,594 | identical |
| Genes after `min_cells_per_gene` | 28,198 | 28,198 |
| Guide classes (targeting / NTC / ambiguous / unassigned) | 50,268 / 27,071 / 84,252 / 3 | identical |
| Distinct targets | 42 (rsID labels collapse; requires `target_split_delims: ["_"]` + hand-added `^no[-_.]?target` pattern) | 44 (`target_feature_column: target_gene_name`; labels verbatim) |
| Leiden clusters (res 1.0) | 22 | 22 |
| Targets tested / passing (KS-FDR < 0.05 & log2FC < 0 vs NTC) | 35 / 28 | 34 / 28 |
| Targets skipped | 7 | 10 (three rsID labels + `CEBPb`, `C6orf106`, `CCBL2` non-HGNC; `BNC2`, `SMIM22` not expressed; `CBWD1`, `RAPGEF5` absent after gene filter) |
| Cluster enrichment (vs NTC) | 39 significant target×cluster pairs | 39 / 38 |
| `Hanrui_fang_all_cells.h5ad` written | no (`write_unfiltered_h5ad` gated on `assigned_only`) | yes — pre-QC object with all 163,991 cells (fix in this branch, `cli.py` Stage 2) |
| Figures / tables | 238 / 28 | 244 / 36 |

Per-target statistics agree wherever the cell sets agree; `LIPA` (Δlog2FC 0.25) and `FHL3` (0.13) differ
only because `main` merges the rsID guide sets into the gene-level sets.

**Decision unchanged: `dev`** (`de12b52` + `37c536b` + this task's all-cells checkpoint fix), for the same
reasons as above; in h5ad mode the only functional differences are `target_feature_column` (correct control
recognition and rsID-distinct targets without rewriting guide ids) and the all-cells checkpoint.
