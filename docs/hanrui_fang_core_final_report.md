# Hanrui Fang Perturb-seq — core workflow report (QC, guide assignment, clustering, perturbation expression)

Run `Hanrui_fang` · pipeline report `results/Hanrui_fang/report.html` (pipeline-generated) · this document records
decisions, provenance, counts, supplementary results and caveats. All matrix work ran through SLURM.

## Selected branch and inputs

| Item | Value |
|---|---|
| Branch / commit | **`dev`** — dev tip `de12b52ce73afbd6ce89ec4b1c99d6d91be4fceb`, run from `feature/basic-qc-hanrui` (`37c536b` basic-QC stage + this task's all-cells checkpoint fix in `cli.py` Stage 2). `main` = `f5a8fa0651dac68b31a16680aeabe612087ce2ea`. Decision and evidence: `pipeline_comparison/main_vs_dev.md` |
| Input H5AD | `/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/work/Hanrui_fang/Hanrui_fang_combined.h5ad` — 163,991 cells × 39,166 features (38,606 `Gene Expression` + 560 `CRISPR Guide Capture`), int32 counts in `X` and `layers["counts"]`, no normalised layer; built by `jobs/build_hanrui_combined_h5ad.py` (SLURM 20045174); validation `tables/combined_h5ad_validation.csv` |
| GEX source | Cell Ranger 9.0.1 `filtered_feature_bc_matrix.h5` per well (GRCh38-2024-A), extracted from the outs tars; raw tree untouched |
| Guide source | scaffold-aware exact-match UMI counter (`perturbseq_pipeline.guide_counting`, SLURM 20045135) on the four guide FASTQ libraries; guide/GEX barcode overlap 100 % in every well (`tables/guide_gex_overlap_per_well.csv`); read funnel `tables/guide_read_retention_funnel.csv`, `tables/guide_quantification_summary.csv` |
| Guide metadata (`var`) | `guide_id`, `target_gene_name` (design label, authoritative), `target_gene_symbol` (alias/rsID-stripped, supplementary only), `scaffold` (A 202 / C 199 / unknown 159 — 152 never sequenced), `is_non_targeting` (127 `NO-TARGET`), `protospacer`; reference `tables/guide_reference_used.csv` |
| Cell metadata (`obs`) | `well`, `lane_id`, `sample`, `sample_id`, `condition` (HF011/HF012, **inferred**), `replicate` (A/B), `replicate_type = unknown`, `condition_status = inferred`, `cell_line = unknown`, `cell_barcode`; ids `HF011A_AAAC…-1` |
| Configuration | `config/Hanrui_fang.yaml` (generated from the dev default `Config()`, K562 h5ad-mode structure; `config/default.yaml` untouched); resolved copy `logs/resolved_config.yaml` |
| Output directory | `/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_fang/` |
| SLURM jobs | build 20045174 · dev tests 20045157 (248 passed) · main tests 20045140 (88 passed) · `main_default` 20045175 · `dev_default` 20045176 · **final 20045177** (ihc-h200-1, 128 CPU, 15 min, 38.4 GB peak, CPU backend) · supplementary 20045178 · validation 20045192 |
| Environment | conda `perturbseq-pipeline`: Python 3.11.15, scanpy 1.11.5, anndata 0.12.19 |

Settings: defaults everywhere except input/output paths, `guides.target_feature_column: target_gene_name`,
`target_split_delims: []`, `ntc_label: ntc`, `enrichment.primary_control: ntc`, and the disabled modules.
Disabled (via their `enabled` keys, all present in the dev schema): `modules` (co-functional modules, gene programs,
networks), `ps_score`, `lochness`, `distance` (energy distance / MMD-style permutation test), `distance_space`
(perturbation space, phenotype modules), `meta_analysis` (integrated atlas table), and `visualization.*` atlas
figures. The run log confirms each skip ("… disabled"). The pipeline HTML report still renders an empty
"10. Master perturbation meta table" heading (template is unconditional) — cosmetic. Harmony off (`batch_key: null`).

## Cell counts (default QC: ≥ 200 genes prefilter → ≥ 1000 genes → mt < 20 %)

`tables/cell_counts_before_after.csv` (long format: well, condition, replicate, stage, category, count, % of input,
% of previous stage; per well and pooled) and `cell_counts_before_after_wide.csv`. Pooled:

| Stage | Cells | % input |
|---|---:|---:|
| Cell Ranger called / loaded | 163,991 | 100 |
| Pass ≥ 200 genes (permissive) / fail | 163,868 / 123 | 99.93 |
| Pass ≥ 1000 genes / fail | 161,649 / 2,219 | 98.57 |
| Pass mt < 20 % (final QC) / fail | 161,594 / 55 | 98.54 |
| Guide-zero (0 guide UMIs) / no guide detected (> 3 UMIs) | 3 / 3,848 | 0.002 / 2.35 |
| Targeting / non-targeting / ambiguous / unassigned | 50,268 / 27,071 / 84,252 / 3 | 30.7 / 16.5 / 51.4 / 0.002 |
| Cells in clustering | 161,594 | 98.54 |
| Cells in perturbation testing (targeting of tested targets + NTC) | 65,743 | 40.1 |
| Final cells | 161,594 | 98.54 |

Per well pass: HF011A 40,630 (98.8 %), HF011B 41,229 (98.7 %), HF012A 39,868 (98.4 %), HF012B 39,867 (98.3 %).
Genes 38,606 → 28,216 (≥ 3 cells) → 28,198. Per-well QC medians before/after: `tables/qc_metrics_per_well_before_after.csv`
(HF011 wells ~24 % ribosomal vs ~17 % for HF012; mt ≈ 3–4 %; haemoglobin ≈ 0; guide UMIs/cell ≈ 2,500–2,700).

## Guide QC and assignment (defaults: `min_umi 3`, `dominance_ratio 2`, `detection_threshold 3`)

`tables/guide_qc.csv`, `assignment_per_lane.csv`, `guide_assignment.csv`, `guide_representation.csv`,
`Hanrui_fang_guide_barcodes.txt`. Median 2,644 guide UMIs/cell, median 3 guides detected, MOI 4.31, median top:second 1.9.
Per well the assignment is stable (30.0–32.2 % targeting, 16.5–17.3 % NTC, 50.5–53.6 % ambiguous).

**Dual-guide compatibility.** Every vector carries one scaffold-A and one scaffold-C guide (both scaffolds recovered in
43/57 % of reads). Classifying QC-passing cells by their strongest A and C guides (≥ 3 UMIs,
`tables/dual_guide_diagnostics_per_well.csv`, `figures/guides/supp_dual_guide_*`): 39,861 two strong guides of the
**same target**, 52,786 **targeting + non-targeting**, 26,307 **two different targets**, 34,623 **both non-targeting**,
5,808 one strong guide, 2,209 no guide; 118,843 cells have > 1 guide ≥ 3 UMIs within a scaffold class. The pipeline's
single-guide dominance rule therefore: (i) calls 21,864 same-target cells `targeting` but leaves 17,997 of them
`ambiguous`; (ii) resolves targeting+NTC cells to `targeting` (14,470), `non-targeting` (9,573) or `ambiguous` (28,743)
purely by UMI ratio; (iii) makes 12,009 two-different-target cells `targeting` under one of the two targets. The rule is
**not designed for this library**; the baseline result is reported as-is and no cells were re-assigned. A pair-aware
assignment needs the intended A↔C vector design, which is not available.

## Clustering

Default normalisation → 3,000 HVGs → PCA 50 → 15-NN → UMAP → Leiden 1.0: **22 clusters** (`tables/clusters.csv`;
largest 24,026 cells, smallest 261; every large cluster is ~50 % A / 50 % B within its dominant condition, i.e. wells
mix within condition while HF011 and HF012 separate). Cluster enrichment vs NTC: 38 significant target × cluster pairs
(`tables/enrichment.csv`, `figures/enrichment/`).

## Perturbation-expression analysis

Pipeline test (`perturbation.py`): per target, `layers["lognorm"]` of the target gene in targeting cells vs non-targeting
(`ntc`, primary) and other-target (`other`, secondary) cells; two-sided KS + one-sided Mann–Whitney (perturbed < control);
`log2FC = log2((mean expm1 targeting + 0.01)/(mean expm1 control + 0.01))`; percent knockdown; BH FDR (pipeline
implementation); **default hit = KS-FDR < 0.05 and log2FC < 0** (verified in code; the MWU FDR is stored but unused).
The pipeline writes no `log10FDR` column; its figures use `-log10(clip(FDR, 1e-300, 1))`. Supplementary tables store the
raw FDR (`fdr_ks`) and **`neg_log10_fdr = -log10(FDR)`** (positive).

Pipeline result (`tables/perturbation_full.csv`): **34 targets tested, 28 default hits**; 10 skipped
(`tables/skipped.csv`: `BNC2`, `SMIM22` not expressed in controls; `CBWD1`, `RAPGEF5` absent after gene filtering; `CEBPb`,
`C6orf106`, `CCBL2` non-HGNC labels; three `(rsID)` labels). Strongest depletion: CD151 −4.19 (94.5 % knockdown), DDT −3.83,
ROGDI −3.40, LMAN1 −3.35, VCL −3.32, STAT2 −3.12, RPL30 −3.08. Not passing: C9orf72, TOM1L2, PGAP3, DGKQ, PLCB1 (negative
log2FC, KS-FDR ≥ 0.05) and RUNX1 (log2FC −0.03).

Supplementary (`tables/perturbation_expression_by_target.csv` 420 rows, `..._by_guide.csv` 1,238 rows,
`..._replicate_summary.csv`): per well / condition / pooled, both controls, per assigned guide; alias-mapped labels included
(`C6orf106`→ILRUN −1.76 hit; `FHL3 (rs114296424)` −2.58 hit; `LIPA (rs1412444)` −2.45 hit; `CCBL2`→KYAT3 −0.98; `CEBPb`→CEBPB −0.08 n.s.;
`ILRUN (rs16878812)` +0.05 n.s.). Response layers (`tables/perturbation_response_layers.csv`): 77,339 guide-assigned cells →
50,268 targeting cells → 36,410 targeting cells belonging to the 32 pooled-significant targets → 32 of 42 testable targets
with significant transcript depletion.

### Replicate / well-level support
A/B are captures of **unknown replicate type**; results are well-level comparisons. Of 42 testable labels: 23 significant
and down in all 4 wells, 5 in 1–3 wells, 14 in none (`reproducibility` column; per-well log2FC/FDR/cell counts included).
A-vs-B log2FC agreement: `figures/perturbation/supp_replicate_consistency_log2fc_A_vs_B.png`.

Interpretation boundary: the CRISPR modality/effector is undocumented, so these are target-transcript depletion associations,
not a confirmed mechanism; guide detection ≠ perturbation.

## Figures

Pipeline: `figures/{qc,guides,clustering,perturbation,enrichment}`. Supplementary (`supp_*`, 61): Cell Ranger metrics per well;
cells before/after QC; UMI / genes / mt / ribo / hb distributions before vs after QC (4 wells + pooled); UMI-vs-genes per
well; knee plots; per-well QC heatmap; A/B gene-mean concordance; ECDFs (UMIs, genes, mt, ribo, guide UMIs, guides per cell)
before/after by well + pooled; PCA/UMAP by well, condition, QC status and guide class (pipeline embedding) and of all
163,991 cells incl. QC-failed (supplementary embedding); UMAP faceted by well; guide read funnel + valid barcode / valid
UMI / exact-match / scaffold fractions; per-guide abundance, guide UMIs and guides per cell, top vs second guide;
assignment categories, NTC vs targeting, scaffold A/C per cell, representation by target, barcode matching per well;
dual-guide categories and their mapping to pipeline classes; volcano, waterfall, log2FC and −log10(FDR) heatmaps by well,
−log10(FDR) ECDF by well, target-expression ECDFs vs NTC and vs other-target controls (12 targets × 4 wells + pooled),
targeting cells per target, assigned cells per well, significant targets per well, A/B consistency, per-guide vs target efficacy.

## Verification, warnings, caveats

* `tables/final_validation.txt` (job 20045192) reopens both h5ad files and checks the contract; `logs/run.log` has 0 WARNING/ERROR
  lines; no tracebacks in any job.
* `Hanrui_fang_all_cells.h5ad` (163,991 cells, pre-QC, QC metrics + `obsm["guide_counts"]`, no normalised layer) is produced by
  the fix added in this task: `output.write_unfiltered_h5ad` previously only acted when `cluster.assigned_only: true`.
* Missing metadata: condition identity, replicate type, cell line, CRISPR modality, intended A↔C pairing.
* Six design labels are untestable by the pipeline as labelled (non-HGNC / rsID); alias-mapped only in supplementary tables.
* Doublets: no doublet filter is a pipeline default and none was applied; the ≈33 % multiplet estimate was not used. Dual-guide
  categories above are diagnostics, not filters.
* Guide matching is exact-sequence (+ ±1 nt positional shift); ~12 % of anchored reads (mostly 1-nt variants) are uncounted.
* `Hanrui_fang_results.tar.gz` (pipeline archive, excludes h5ad) was rebuilt after the supplementary step.
