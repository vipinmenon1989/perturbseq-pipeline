# Hanrui Fang Perturb-seq — baseline preprocessing, default QC, branch comparison and perturbation QC

Run name `Hanrui_fang` · output root `results/Hanrui_fang/` · pipeline HTML report `report.html`
(pipeline-generated, 14 stages) · this document adds the decisions, provenance, supplementary
tables/figures and caveats required by the task. Nothing here was run on the login node.

## 1. Decision: `main` vs `dev`

**Selected: `dev`** — commit `de12b52ce73afbd6ce89ec4b1c99d6d91be4fceb` (dev tip) executed from branch
`feature/basic-qc-hanrui` at `37c536b74190badaaaee81937b69663b200306cc` (adds only the optional
basic-QC stage and the `^no[-_. ]?target` control pattern). `main` = `f5a8fa0651dac68b31a16680aeabe612087ce2ea`.
Full comparison, both branches' test results and the two default-parameter comparison runs:
`pipeline_comparison/main_vs_dev.md`, `pipeline_comparison/main_default/`, `pipeline_comparison/dev_default/`.
Both branches load the data and give identical QC and guide counts; `dev` was chosen because it
alone can use the raw design label as the authoritative target (`guides.target_feature_column`),
keeping `NO-TARGET` controls and the rsID-specific guide sets correct, and because it carries the
HPC plumbing and the guide-FASTQ counter used to produce the guide matrices.

## 2. Inputs and provenance

| Item | Value |
|---|---|
| Raw dataset (read-only) | `/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X/` |
| GEX input | Cell Ranger 9.0.1 `filtered_feature_bc_matrix/` MTX directories extracted from `<well>/analysis/*/<well>_cellranger_count_outs.tar` into `outputs/hanrui_fang_inputs/cellranger/<well>/` (GRCh38-2024-A, 38,606 features, integer counts, gene ids + symbols preserved) |
| Guide input | scaffold-aware guide UMI matrices (560 designed guides × cells) from `perturbseq_pipeline.guide_counting` (SLURM 20045135), re-emitted with `-1` barcodes to `outputs/hanrui_fang_inputs/guides/<well>/`; 100 % barcode overlap with GEX in every well (`tables/guide_gex_alignment_check.csv`) |
| Guide reference | `web_summaries/design_out_v2.xlsx` (560 protospacers, 45 targets + 127 `NO-TARGET`); `tables/guide_reference_used.csv` |
| Guide quantification | `tables/guide_quantification_summary.csv` — per well 225–259 M reads, 98.0–98.2 % with scaffold anchor, 87.4–88.9 % exact spacer match, 92.9–93.7 % of matched reads in GEX barcodes, 402–405 guides observed, 140–153 M unique cell-guide UMIs |
| Sample manifest | `config/Hanrui_fang_sample_manifest.csv` → `tables/sample_manifest.csv` (`condition_status = inferred`, `replicate_type = unknown`, `cell_line = unknown`) |
| Configuration | `config/Hanrui_fang.yaml`; resolved copy `logs/resolved_config.yaml` |
| Environment | conda `perturbseq-pipeline`: Python 3.11.15, scanpy 1.11.5, anndata 0.12.19, pertps 0.1.0, harmonypy 2.0.0 |
| SLURM jobs | prep 20045139 · main tests 20045140 · main_default 20045141 · dev_default 20045142 · **final run 20045143** (ihc-h200-1, 128 CPU, 31.5 min, 41.2 GB peak, GPU unused) · supplementary 20045144 · dev tests 20045137 · guide counting 20045135 |

Config overrides relative to defaults: input/metadata/output paths and run name; `input.cache_mtx: false`;
`guides.target_feature_column: gene_symbols` + `ntc_patterns` incl. `^no[-_. ]?target` (guide-metadata
interpretation); `output.write_unfiltered_h5ad: true`, `output.archive: true`. **All QC, clustering and
perturbation parameters are pipeline defaults.**

## 3. Cell counts (default pipeline QC: ≥ 200 genes prefilter, ≥ 1000 genes, mt < 20 %)

`tables/cell_counts_before_after.csv` (counts and percentages; per well, per inferred condition,
per replicate label, pooled). Criterion columns are overlapping flags on the all-cell object; the
pipeline's sequential removals are in `tables/qc_steps.csv`.

| Well | Cell Ranger / loaded | fail <200 genes | fail <1000 genes | fail mt ≥ 20 % | pass expression QC | zero guide UMIs | targeting | non-targeting | ambiguous | unassigned | in perturbation test |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HF011A | 41,132 | 2 | 490 | 62 | 40,630 (98.8 %) | 15 | 12,390 | 6,693 | 21,547 | 0 | 16,207 |
| HF011B | 41,782 | 1 | 547 | 41 | 41,229 (98.7 %) | 9 | 12,360 | 6,788 | 22,081 | 0 | 16,417 |
| HF012A | 40,531 | 63 | 644 | 291 | 39,868 (98.4 %) | 24 | 12,839 | 6,915 | 20,113 | 1 | 16,720 |
| HF012B | 40,546 | 57 | 661 | 284 | 39,867 (98.3 %) | 9 | 12,679 | 6,675 | 20,511 | 2 | 16,399 |
| **ALL** | **163,991** | 123 | 2,342 | 678 | **161,594 (98.5 %)** | 57 | 50,268 | 27,071 | 84,252 | 3 | 65,743 |

Pipeline sequence (`qc_steps.csv`): 163,991 → 163,868 (prefilter) → 161,649 (≥ 1000 genes) →
161,594 (mt < 20 %); genes 38,606 → 28,216 → 28,198. All 161,594 QC-passing cells enter clustering
(`cluster.assigned_only: false`) and are the final analysed cells. Per-well QC medians before/after:
`tables/qc_metrics_per_well_before_after.csv` (e.g. HF011A median 15,270 UMIs / 3,919 genes / 3.7 % mt;
HF012 wells have lower ribosomal fraction, 17 % vs 24 %; haemoglobin ≈ 0 everywhere).

## 4. Guide QC and assignment (pipeline defaults: `min_umi 3`, `dominance_ratio 2`, `detection_threshold 3`)

`tables/guide_qc.csv`, `tables/assignment_per_lane.csv`, `tables/guide_assignment.csv`,
`tables/guide_representation.csv`, `Hanrui_fang_guide_barcodes.txt`.
Median guide UMIs per cell 2,644; median 3 guides detected (> 3 UMIs); mean 4.31; median
top:second ratio 1.9; 152,490 cells (94 %) have > 1 detected guide. Assignment: **31.1 % targeting,
16.8 % non-targeting, 52.1 % ambiguous, 3 unassigned**, stable across wells (30.0–32.2 % targeting).

Interpretation: this is a **dual-guide library** (every vector carries one scaffold-A and one
scaffold-C guide; audit + `outputs/hanrui_fang_qc`). The pipeline's single-guide dominance rule
therefore calls a cell only when one of its two guides has > 2× the UMIs of the other; the 52 %
ambiguous fraction is a property of the rule, not of cell quality. "Multiplet-like" (> 1 guide) is a
diagnostic field here, not a filter. No doublet filter was applied (none is a pipeline default).

## 5. Perturbation-expression (target-transcript) analysis

Pipeline test (`perturbation.py`): per target, `layers["lognorm"]` of the target gene in targeting
cells vs (a) non-targeting cells (`ntc`, preferred) and (b) cells assigned to other targets
(`other`); two-sided KS and one-sided Mann–Whitney (perturbed < control); `log2FC =
log2((mean expm1 perturbed + 0.01)/(mean expm1 control + 0.01))`; percent knockdown; BH FDR
(pipeline's own implementation); **hit = KS-FDR < 0.05 and log2FC < 0**. The pipeline writes no
`log10FDR` column; its plots use `-log10(clip(FDR, 1e-300, 1))`. Supplementary tables use the same
functions and report **`neg_log10_fdr_ks = -log10(FDR)` (positive)**.

Pipeline result (`tables/perturbation_full.csv`, pooled wells, NTC control): **34 targets tested, 28
pass** (`tables/perturbation.csv`), 10 skipped (`tables/skipped.csv`: `BNC2`, `SMIM22` not
expressed in controls; `CBWD1`, `RAPGEF5` not in the filtered matrix; `CEBPb`, `C6orf106`, `CCBL2`
non-HGNC labels; three `(rsID)` labels). Strongest depletion: CD151 (log2FC −4.19, 94.5 % knockdown),
DDT (−3.83), ROGDI (−3.40), LMAN1 (−3.35), VCL (−3.32), STAT2 (−3.12). Not passing: C9orf72, TOM1L2,
PGAP3, DGKQ, PLCB1 (negative log2FC but KS-FDR ≥ 0.05; note their MWU-FDR < 0.05, unused by the
rule) and RUNX1 (log2FC −0.03). `other` control agrees with `ntc` for 27/28 hits (TFEB other-FDR 0.050).

Supplementary (`tables/perturbation_expression_by_target.csv`, `..._by_guide.csv`,
`..._replicate_summary.csv`): per well, per condition, pooled; both controls; per assigned guide
(237 guides testable pooled, 125 pass). Design labels that are not HGNC symbols were mapped for the
supplementary tables only (`CEBPb→CEBPB`, `C6orf106→ILRUN`, `CCBL2→KYAT3`, `GENE (rsID)→GENE`):
`C6orf106`→ILRUN −1.76 (pass), `FHL3 (rs114296424)` −2.58 (pass), `LIPA (rs1412444)` −2.45 (pass),
`CCBL2`→KYAT3 −0.98 (pass), `CEBPb`→CEBPB −0.08 (not significant), `ILRUN (rs16878812)` +0.05 (none).

### Replicate / well-level support
A/B are **captures of unknown replicate type**; results are reported as well-level (capture-level)
concordance, not biological-replicate validation. Of 42 labels with the gene present, 26 pass in all
4 wells with the same direction, 5 pass in 1–3 wells, 11 in none (`reproducibility_label` column);
A-vs-B log2FC correlation figures: `figures/perturbation/supp_replicate_consistency_log2fc_A_vs_B.png`,
gene-mean concordance `figures/qc/supp_replicate_concordance_gene_means.png`.

### Interpretation boundaries
CRISPR modality/effector is undocumented, so these are **target-transcript depletion associations**
(guide assignment → transcript depletion), not a confirmed KO/CRISPRi mechanism. Per-cell response
(PS scores, `tables/ps_score.csv`), cluster enrichment, lochNESS and energy distance (19/44 targets
significant, `tables/perturbation_distance.csv`) are separate, downstream evidence layers produced
by the pipeline's optional modules (all ran; `pertps 0.1.0` present; nothing skipped for dependencies).

## 6. Figures

Pipeline figures: `figures/{qc,guides,clustering,perturbation,enrichment,ps_score,lochness,modules,distance,distance_space}` (244).
Supplementary (`supp_*`, 46): Cell Ranger metrics per well; input cells and retention; UMI / genes /
mt / ribo / hb distributions before vs after QC faceted by well; UMI-vs-genes per well; barcode-rank
knee plots (raw h5); per-well QC heatmap; A/B gene-mean concordance; ECDFs (UMIs, genes, mt %, ribo %,
guide UMIs, guides per cell) before/after by well; PCA/UMAP of processed cells by well, condition and
guide class; PCA/UMAP of **all** 163,991 cells by well, condition, QC status and class (supplementary
embedding, not the pipeline's); UMAP of assignment classes; assignment/MOI/dominance per well; target
and guide representation; volcano, waterfall, log2FC and −log10(FDR) heatmaps by well, ECDF of
−log10(FDR) by well, target-expression ECDFs (targeting vs NTC vs other, faceted by well) for 12 targets,
targeting cells per target, passing targets per well, A-vs-B replicate consistency, per-guide vs
target-level efficacy.

## 7. Caveats, missing metadata, limitations

* HF011/HF012 condition identity, A/B replicate type and cell line are **unconfirmed** (`inferred` / `unknown`).
* Single-guide dominance rule vs dual-guide design → 52 % ambiguous; an intended A↔C vector pairing
  table is required for pair-aware assignment (not available).
* The pipeline never writes QC-failed cells; before/after comparisons use the basic-QC all-cells object
  (`outputs/hanrui_fang_qc/combined/perttf_qc_allcells.h5ad`, same Cell Ranger cells, same scanpy metrics).
* `output.write_unfiltered_h5ad: true` is a no-op with `cluster.assigned_only: false` (both branches).
* Six design labels are untestable by the pipeline as-is (non-HGNC or rsID labels); alias mapping is supplementary.
* Guide matching is exact-sequence; ~12 % of anchored reads (mostly 1-nt variants) are not counted.
* The audit's ≈33 % multiplet estimate was not used as a filter; doublet flags from the basic-QC stage
  (`outputs/hanrui_fang_qc`) are available but Scrublet's automatic threshold was unreliable in 3/4 wells.
* `Hanrui_fang_results.tar.gz` excludes `*.h5ad/*.h5` (pipeline default) and was rebuilt after the
  supplementary step so it contains all tables, figures and this report.

## 8. Warnings / errors
`logs/run.log`: no WARNING or ERROR lines; `Hanrui_fang_20045143.err`: no traceback. Comparison runs:
one expected warning each (manifest rows for unused wells). Supplementary job: none.
