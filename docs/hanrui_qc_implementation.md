# Hanrui Fang basic QC — implementation report

Branch `feature/basic-qc-hanrui` (off `dev`). Environment: conda
`perturbseq-pipeline` (Python 3.11.15, scanpy 1.11.5, anndata 0.12.19).
All real-data work ran through SLURM; the login node was used only for git,
config inspection and the synthetic unit tests.

## Scope

A reusable **basic QC stage** for `perturbseq-pipeline` (`run.stop_after: qc`)
that loads per-GEM-well 10x matrices, quantifies guides from FASTQ (or takes a
precomputed matrix, or no guide data), computes per-well expression QC, flags
doublets and guide-derived multiplets **without removing them**, concatenates
the wells and writes raw-count QC objects, tables, figures and a report. All
Hanrui-specific information lives in `config/hanrui_fang.yaml`; the Python code
contains no sample-specific logic.

## Files

### Modified

| File | Change |
|---|---|
| `src/perturbseq_pipeline/config.py` | `RunConfig.stop_after`; top-level `samples` + `SampleConfig` + `Config.resolved_samples()`; `QCConfig.thresholds` (`QCThresholdConfig`) and `QCConfig.doublets` (`DoubletConfig`); `GuideConfig.source/design/fastq/multiplet` (`GuideDesignConfig`, `GuideFastqConfig`, `GuideMultipletConfig`); `^no[-_. ]?target` in default `ntc_patterns`; `_validate_basic_qc()`; `resolved_mode() == "samples"`; input validation accepts `samples` without `input.mtx_dirs/h5ad`. |
| `src/perturbseq_pipeline/cli.py` | `run_pipeline(..., config_path=)` runs the basic QC stage and returns before Stage 1 when `stop_after == "qc"`; `PipelineResult.basic_qc` + QC summary line; `main()` passes the config path. |
| `src/perturbseq_pipeline/io.py` | `read_10x_h5`, `read_10x_mtx_sample`, `read_10x_guide_features`, `strip_barcode_suffix`, `BARCODE_KEY`; keeps the pre-existing uncommitted `allow_write_nullable_strings` hunk in `write_h5ad`. |
| `src/perturbseq_pipeline/qc.py` | `annotate_gene_classes_case_insensitive`, `compute_basic_qc_metrics`, `resolve_sample_thresholds`, `flag_expression_qc`, `expression_qc_step_table`, `QC_FLAG_COLUMNS`, `GEX_QC_PASS`. |
| `src/perturbseq_pipeline/report.py` | `build_qc_report()` (QC-only HTML; no `PerturbationResults` needed). |
| `pyproject.toml` | dependencies `h5py`, `openpyxl`, `scikit-image` (already installed in the env). |
| `config/default.yaml` | regenerated snapshot of `Config()`. |
| `README.md`, `docs/PIPELINE_DEVELOPMENT.md` | Basic QC stage section; changelog entry. |

### Added

| File | Purpose |
|---|---|
| `src/perturbseq_pipeline/basic_qc.py` | Stage driver (`run_basic_qc`), legacy-input adapter, concatenation, tables, provenance, report. |
| `src/perturbseq_pipeline/doublets.py` | Scrublet wrapper (`run_scrublet`): `doublet_score`, `predicted_doublet`, `uns["scrublet"]`; never subsets. |
| `src/perturbseq_pipeline/guide_design.py` | Design workbook parser (`load_guide_design`), control recognition, synthetic ids, optional scaffold table. |
| `src/perturbseq_pipeline/guide_counting.py` | Streaming scaffold-aware guide counter (`count_guides`, `count_fastq_file`), MTX writer/reader, precomputed-matrix adapter. |
| `src/perturbseq_pipeline/guide_qc.py` | `attach_guide_counts`, `infer_scaffold_classes`, `guide_multiplet_flag`/`guide_structure_pass`, summaries, Scrublet-vs-guide cross-tab. |
| `src/perturbseq_pipeline/qc_plots.py` | QC/doublet/guide figures (flagged cells overlaid, never dropped). |
| `src/perturbseq_pipeline/provenance.py` | git/SLURM/package/input provenance; `uns`-safe coercion. |
| `src/perturbseq_pipeline/templates/qc_report.html` | QC report template. |
| `tests/make_synthetic_basic_qc.py`, `tests/test_basic_qc.py` | Two-well synthetic dataset (h5 + guide FASTQ + design xlsx) and 22 tests. |
| `config/hanrui_fang.yaml`, `config/hanrui_fang_subset.yaml` | Production and subset-validation configs. |
| `jobs/run_hanrui_qc.sbatch`, `jobs/run_hanrui_subset.sbatch`, `jobs/run_tests.sbatch`, `jobs/stage_hanrui_cellranger.sh`, `jobs/_slurm_env.sh` | SLURM entry points and Cell Ranger tar staging. |

## Methods

### 10x loading
`sc.read_10x_h5(gex_only=False)` → keep `Gene Expression` features → cast to
integer CSR (values verified integral) → `layers["counts"] = X.copy()` →
`var_names_make_unique()` → `obs["cell_barcode"]` = original barcode,
`obs_names = <sample_id>_<barcode>`, `obs["sample_id"] = obs["lane_id"] = sample_id`.
`var` keeps `gene_ids`, `feature_types`, `genome`.

### Guide design
Workbook columns are auto-detected (`seq` → protospacer, `gene` → target; both
can be forced). Controls are recognised with `guides.design.control_patterns`
or, by default, `guides.ntc_patterns` (which now matches `NO-TARGET`). Guide
ids are `<sanitised target>_<n>` (e.g. `NO-TARGET_1`, `LIPA_rs1412444_1`). All
560 designed guides are retained; original columns are kept as
`on_target_efficacy_score`, `beginswithg`.

### Guide counting
Per FASTQ file (one worker process each, `pigz -dc` stream): barcode =
`seq[:16]`, UMI = `seq[16:28]`; scaffold anchor regex
`(GTTTAAGAGCTA)|(GTTTCAGAGCTA)` searched from position 40 (the matched
alternative names the scaffold class); protospacer = 20 nt immediately 5' of
the anchor; exact match against the design set, with a ±1 nt positional
fallback (`position_shift: 1`, still exact sequence) and no mismatches
(`max_mismatches: 0`). Reads whose barcode is in the paired GEX filtered set
are collapsed to unique (cell, guide, UMI) codes packed into int64 and
de-duplicated with `np.unique` in chunks; other barcodes are counted only.
Output per well: `cells × 560` UMI matrix (10x-style MTX), per-guide reads /
UMIs / positive cells / per-scaffold reads, counting statistics (TSO,
anchor, spacer match, shift matches, barcode-in-GEX, invalid UMI, throughput)
and the top unmatched protospacers. Scaffold classes are inferred from the
pooled per-guide scaffold reads (majority class, purity ≥ 0.9, ≥ 20 reads).

### Expression QC
`sc.pp.calculate_qc_metrics(qc_vars=[mt, ribo, hb], log1p=True, percent_top=[20])`
per well. Thresholds per well: `median ± 3·MAD` on the log1p scale for
`total_counts` and `n_genes_by_counts`, lower bounds floored at 1,000 counts /
500 genes; mitochondrial cap 10 % (condition code HF011) or 15 % (HF012);
no haemoglobin or ribosomal filter. Independent flags `qc_low_counts`,
`qc_high_counts`, `qc_low_genes`, `qc_high_genes`, `qc_high_mt`, `qc_high_hb`;
`gex_qc_pass = NOT(any flag)`. Resolved values are written to
`tables/qc_thresholds.tsv` and `uns["qc_thresholds"]`.

### Doublets (flag only)
`sc.pp.scrublet` per well on a lightweight copy of the raw counts (default
expected rate 0.05, automatic threshold, `random_state = run.seed`). Stores
`doublet_score`, `predicted_doublet`; threshold failures are recorded and
produce `predicted_doublet = False` with scores retained. No cell is removed;
the wrapper asserts `n_obs` is unchanged.

### Guide multiplets (flag only)
Detected guide = UMIs ≥ 3. Per cell: `n_guides`, `n_guides_A`, `n_guides_C`,
`guide_umi_total`, `guide_umi_A`, `guide_umi_C`, top/second guide per class.
`guide_multiplet_flag = (n_guides_A > 1) | (n_guides_C > 1)`;
`guide_structure_pass = (n_guides_A == 1) & (n_guides_C == 1)` and no
unknown-scaffold guide; `guide_detected = n_guides ≥ 1`;
`perturbation_assignable = False` (vector pairing not supplied). Without
scaffold classes the rule falls back to `expected_guides_per_cell`.

### Outputs
Per well `per_sample/<S>_qc_allcells.h5ad`; combined
`combined/perttf_qc_allcells.h5ad` (all cells) and `combined/perttf_qc.h5ad`
(`gex_qc_pass` only — predicted doublets and guide multiplets retained);
tables, figures, `reports/qc_report.html`, `reports/provenance.json`.
Concatenation is `anndata.concat(join="inner")` after per-well QC; no
integration.

## AnnData schema

* `X`, `layers["counts"]`: raw integer CSR counts.
* `obs`: `sample_id`, `condition_code`, `gem_well`, `guide_library`, `cell_barcode`, `lane_id`;
  `total_counts`, `n_genes_by_counts`, `pct_counts_mt`, `pct_counts_ribo`, `pct_counts_hb`,
  `pct_counts_in_top_20_genes`, log1p companions; `qc_*` flags, `gex_qc_pass`;
  `doublet_score`, `predicted_doublet`; `guide_umi_total`, `n_guides`, `n_guides_A/C`,
  `guide_umi_A/C`, `top_guide`, `top_guide_umi`, `second_guide_umi`, `top_guide_A/C(_umi)`,
  `second_guide_A/C_umi`, `guide_detected`, `guide_structure_pass`, `guide_multiplet_flag`,
  `perturbation_assignable`.
* `var`: `gene_ids`, `feature_types`, `genome`, `mt`, `ribo`, `hb`, `n_cells_by_counts`, `n_cells_<S>`.
* `obsm["guide_counts"]`: cells × 560 int32 CSR UMI counts.
* `uns`: `guide_features` (design table + empirical scaffold + read evidence), `guide_names`,
  `guide_target_genes`, `guide_qc`, `sample_manifest`, `qc_thresholds`, `scrublet`, `basic_qc`,
  `provenance` (git branch/commit, config path, timestamp, host, SLURM job, packages, inputs), `config`.

## Tests
`tests/test_basic_qc.py` — loader (integer counts, barcodes, unique names, gene ids),
config (multi-sample, guide pairing, unknown keys, `stop_after`), QC (metrics, deterministic
thresholds, flags, fixed/condition/override), Scrublet wrapper (score, flag,
`n_before == n_after`, counts untouched), design parser (all guides kept, NO-TARGET),
FASTQ parser (valid / unknown / duplicate UMI / different UMI / A / C / invalid barcode /
bad UMI / no anchor / shift / mismatch mode), counter vs synthetic truth + MTX round trip +
empirical scaffold inference, guide multiplet flags (`n_before == n_after`), two-well
integration (all cells retained, flags aligned, guide rows aligned, doublets and multiplets
present in both objects, tables consistent), GEX-only run, precomputed-matrix run.

## SLURM execution
`jobs/run_hanrui_subset.sbatch` (HF011A + first 10 M reads of HF011AF L004) and
`jobs/run_hanrui_qc.sbatch` (all four wells, user template: ihc-h200-1, 128 CPU, 350 GB,
`--gres=gpu:1` retained for the cluster configuration; `compute.backend: cpu`, no QC
algorithm uses the GPU). CPU-only test/subset jobs run on `ihc-grid-1-1-1` because the
H200 node rejects CPU-only requests. Logs: `logs/hanrui_qc_<jobid>.{log,err}`.

## Results

Production run: SLURM job **20045135** on `ihc-h200-1` (128 CPUs, 350 GB requested), branch
`feature/basic-qc-hanrui`, conda env `perturbseq-pipeline`. Wall time **44 min 56 s**, peak RSS
**54.1 GB** (job cgroup; main process 35.3 GB), CPU use ~370 % overall (8 counting workers, then
single-process QC). GPU not used by any algorithm (`compute.backend: cpu`). Validation job
**20045136** reopened both combined objects: **all checks passed**
(`outputs/hanrui_fang_qc/reports/final_validation.txt`). Test suite (job 20045137): **247 passed**
(223 pre-existing + 24 new).

Subset validation (job 20045129, HF011A + first 10 M reads of HF011AF L004, 8 min, 23 GB):
TSO at expected position 96.8 %, scaffold anchor 97.6 %, spacer matched 87.2 % (3,418 via ±1 shift),
93.1 % of matched reads in the HF011A barcode set, scaffold A/C 43.4/56.6 %, 401/560 guides observed;
audit references were 97.0 / 98.0 / 88.1 / 93.2 / 43.4-56.6 % and 402. Throughput ≈ 320 k reads/s per
worker; the full libraries (225-259 M reads each) took 578-731 s per lane file with 8 files in parallel.

### Guide counting (full libraries)

| Library → well | Reads | Anchor | Spacer matched | Matched reads in GEX barcodes | Guides observed | Unique cell-guide UMIs |
|---|---:|---:|---:|---:|---:|---:|
| HF011AF → HF011A | 234,699,206 | 98.2 % | 88.9 % | 93.2 % | 404 / 560 | 142,950,696 |
| HF011BF → HF011B | 258,645,413 | 98.1 % | 88.4 % | 92.9 % | 405 / 560 | 152,935,757 |
| HF012AF → HF012A | 224,556,668 | 98.0 % | 87.4 % | 93.7 % | 404 / 560 | 140,614,801 |
| HF012BF → HF012B | 253,339,079 | 98.1 % | 87.9 % | 93.6 % | 402 / 560 | 151,449,744 |

407 of 560 designed guides have UMIs in at least one well; 153 designed guides were never seen.
Empirical scaffold classes: **202 A, 199 C, 159 unknown** (152 with no reads, 6 below 20 reads,
`TOM1L2_10` mixed). Top unmatched protospacer is a 1-nt variant of the most abundant NO-TARGET guide
(`AAAACGAGAAGTTTGTACTA` vs `GAAACGAGAAGTTTGTACTA`), i.e. the mismatch class that exact matching
deliberately excludes. Guide-count matrix: 163,991 × 560 (int32 CSR) in `obsm["guide_counts"]`.

### Per-well QC (flags only; nothing removed)

| Well | Input cells | median UMIs / genes / mt % | min counts | max counts | min genes | max genes | mt cap | gex_qc_pass | Scrublet flagged | guide detected | structure pass | guide multiplet flagged |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HF011A | 41,132 | 15,270 / 3,919 / 3.73 | 4,199 | 55,524 | 1,749 | 8,777 | 10 % | 40,061 (97.4 %) | 6,610 (16.1 %) | 40,494 | 10,123 | 29,103 |
| HF011B | 41,782 | 12,597 / 3,524 / 3.87 | 3,476 | 45,643 | 1,541 | 8,056 | 10 % | 40,748 (97.5 %) | 1 (threshold suspect) | 41,237 | 8,691 | 31,408 |
| HF012A | 40,531 | 14,663 / 3,792 / 3.07 | 2,477 | 86,783 | 1,333 | 10,781 | 15 % | 39,670 (97.9 %) | 0 (threshold suspect) | 39,902 | 9,377 | 29,425 |
| HF012B | 40,546 | 13,012 / 3,541 / 3.05 | 2,259 | 74,936 | 1,239 | 10,115 | 15 % | 39,721 (98.0 %) | 0 (threshold suspect) | 39,964 | 8,657 | 30,281 |

The MAD-derived lower bounds reproduce the audit's expected values (e.g. HF011A 4,199 counts / 1,749 genes).

### Combined objects

| Object | Cells | Genes | Predicted doublets retained | Guide multiplets retained |
|---|---:|---:|---:|---:|
| `combined/perttf_qc_allcells.h5ad` (3.0 GB) | 163,991 | 38,606 | 6,611 | 120,217 |
| `combined/perttf_qc.h5ad` (`gex_qc_pass`, 3.0 GB) | 160,200 | 38,606 | 6,509 | 117,886 |

2,182 cells without a detected guide pass expression QC and are retained. `perturbation_assignable`
is False for every cell.

### Findings that need a decision (not acted on — flags only)

1. **Scrublet automatic thresholds are implausible in 3 of 4 wells.** HF011A: threshold 0.132 →
   6,610 calls (16.1 %). HF011B / HF012A / HF012B: thresholds 0.709 / 0.514 / 0.518, above the
   99.9th percentile of observed scores (0.44 / 0.36 / 0.35) → 1 / 0 / 0 calls, now reported as
   `threshold_suspect` in `tables/doublet_summary.tsv` and in the report warnings. The score
   distributions are nearly identical across wells (p50 ≈ 0.05-0.07, p90 ≈ 0.18, p99 ≈ 0.28-0.34),
   so the difference is the threshold search, not the data. Nothing was forced; scores are stored for
   all 163,991 cells and a manual `qc.doublets.threshold` can be applied later. In HF011A, 5,760 of
   6,610 Scrublet doublets also carry a guide multiplet flag.
2. **The absolute 3-UMI guide detection rule is too permissive at this depth.** Median guide UMIs
   per cell are ≈ 2,500-2,700 (vs ≈ 280 in the audit's 20 M-read subsample), so ambient guides
   exceed 3 UMIs: 73.3 % of cells are `guide_multiplet_flag` and only 22.5 % `guide_structure_pass`
   (1 A + 1 C). `tables/guide_detection_sensitivity.tsv` shows the structure-pass fraction rises to
   ≈ 0.47 and the multiplet fraction falls to ≈ 0.42-0.46 once a depth-aware rule is used (e.g.
   ≥ 10 UMIs, or ≥ 2 % of the cell's top guide), matching the audit's ≈ 48 % clean-pair estimate.
   The configurable rule `guides.multiplet.detection_min_fraction_of_top` (default off) and the
   absolute threshold are the knobs; re-running only re-derives flags from the stored guide matrix.

## Remaining limitations / blockers

* **Designed A↔C vector pairing** is not available, so no perturbation is assigned
  (`perturbation_assignable` is False everywhere). Guide identities per scaffold class are
  stored so pairing can be applied later without recounting.
* **CRISPR modality / effector** (KO, CRISPRi, CRISPRa) is undocumented; nothing in the QC
  stage depends on it.
* **HF011 vs HF012 and A vs B** remain neutral codes until experimenter metadata confirm them;
  the only place the condition code is used is the configurable mitochondrial cap.
* Scaffold class for guides with too few reads stays `unknown`; `TOM1L2_10` shows mixed
  scaffold reads and is left `unknown` (its detections count toward `n_guides` but not toward
  `guide_structure_pass`).
* Scrublet's automatic threshold is data-driven and may under-call homotypic doublets; the
  guide-derived flag is stored alongside so the removal rule can be chosen after inspection.
* `samples` mode currently requires `stop_after: qc`; hand-off into the downstream stages
  (guide assignment, clustering, perturbation tests) is a follow-up once pairing is defined.
* The counter uses exact matching (plus ±1 positional shift). `max_mismatches: 1` is
  implemented and tested but off by default.
