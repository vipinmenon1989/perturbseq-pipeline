#!/usr/bin/env python
"""Step 5: quantify the four Hanrui Fang guide FASTQ libraries separately with the
pipeline's scaffold-aware counter, then write the retention funnel, quantification
summary, per-cell and per-well guide tables and update the guide reference /
pair map with this run's empirical scaffold classes.

SLURM only (jobs/hanrui_fang/03_count_guides.slurm).
"""
from __future__ import annotations

import argparse
import gzip
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guide_counting import GuideCountJob, count_guides, find_guide_fastqs, write_guide_counts
from perturbseq_pipeline.guide_design import load_guide_design
from perturbseq_pipeline.guide_qc import infer_scaffold_classes

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("count_guides_hanrui")

WELLS = {"HF011A": "HF011AF", "HF011B": "HF011BF", "HF012A": "HF012AF", "HF012B": "HF012BF"}


def read_barcodes(path: Path) -> list[str]:
    with gzip.open(path, "rt") as fh:
        return [l.strip() for l in fh if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-config", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--cellranger-root", required=True, help="staged cellranger/<well>/filtered_feature_bc_matrix dirs")
    ap.add_argument("--out-root", required=True, help="results/Hanrui_fang_dual_guide")
    ap.add_argument("--max-mismatches", type=int, default=1)
    ap.add_argument("--n-workers", type=int, default=8)
    ap.add_argument("--prior-stats-root", default=None, help="previous exact-only guide_counts/<well>/ for rescue comparison")
    args = ap.parse_args()

    out_root = Path(args.out_root)
    tables = out_root / "tables"
    gc_root = out_root / "guide_counts"
    tables.mkdir(parents=True, exist_ok=True)
    gc_root.mkdir(parents=True, exist_ok=True)

    cfg = Config.from_yaml(args.qc_config)
    cfg.guides.fastq.max_mismatches = args.max_mismatches
    cfg.guides.fastq.n_workers = args.n_workers
    fq = cfg.guides.fastq
    design = load_guide_design(cfg)
    assert len(design) == 560, len(design)
    log.info("design: %d guides; matching rule: exact spacer, +/-%d nt positional shift, max_mismatches=%d (unambiguous 1-mismatch index)",
             len(design), fq.position_shift, fq.max_mismatches)

    # ---- jobs --------------------------------------------------------------------
    jobs = []
    suffix_re = re.compile(fq.barcode_suffix_regex)
    gex_barcodes: dict[str, list[str]] = {}
    for well, lib in WELLS.items():
        bc_path = Path(args.cellranger_root) / well / "filtered_feature_bc_matrix" / "barcodes.tsv.gz"
        bcs = read_barcodes(bc_path)
        gex_barcodes[well] = bcs
        bare = [suffix_re.sub("", b) for b in bcs]
        fastqs = find_guide_fastqs(Path(args.data_root) / lib, fq.read_pattern)
        log.info("%s: %d GEX barcodes (%s), %d FASTQ files: %s", well, len(bcs), bc_path, len(fastqs), [Path(f).name for f in fastqs])
        jobs.append(GuideCountJob(sample_id=well, fastq_files=fastqs, cell_barcodes=bare))

    t0 = datetime.now()
    results = count_guides(jobs, design, cfg, n_workers=args.n_workers)
    log.info("counting finished in %s", datetime.now() - t0)
    design = infer_scaffold_classes(design, results, cfg)

    # ---- per-well outputs -----------------------------------------------------------
    for well, res in results.items():
        paths = write_guide_counts(res, design, gc_root / well)
        log.info("%s: wrote %s", well, sorted(str(p.name) for p in paths.values()))

    # ---- funnel -----------------------------------------------------------------------
    prior = {}
    if args.prior_stats_root:
        for well in WELLS:
            p = Path(args.prior_stats_root) / well / f"{well}_guide_counting_stats.json"
            if p.is_file():
                prior[well] = json.load(open(p))["sample"]
    funnel_rows = []
    for well, res in results.items():
        s = res.stats
        matched = s["reads_spacer_matched"]
        exact = matched - s["reads_spacer_matched_via_shift"] - s["reads_spacer_matched_via_mismatch"]
        in_gex = s["reads_matched_barcode_in_gex"]
        valid_umi = in_gex - s["reads_invalid_umi"]
        row = {
            "well": well, "guide_library": WELLS[well], "n_fastq_files": s["n_files"],
            "reads_total": s["reads_total"],
            "reads_with_tso": s["reads_with_tso"],
            "reads_with_scaffold_anchor": s["reads_with_scaffold_anchor"],
            "reads_scaffold_A": s["reads_scaffold_A"], "reads_scaffold_C": s["reads_scaffold_C"],
            "reads_spacer_matched_total": matched,
            "reads_spacer_matched_exact": exact,
            "reads_spacer_matched_via_shift": s["reads_spacer_matched_via_shift"],
            "reads_spacer_matched_via_1mismatch": s["reads_spacer_matched_via_mismatch"],
            "reads_spacer_matched_via_1mismatch_pos1": s["reads_spacer_matched_via_mismatch_pos1"],
            "reads_spacer_unmatched": s["reads_spacer_unmatched"],
            "reads_matched_barcode_in_gex": in_gex,
            "reads_matched_barcode_not_in_gex": s["reads_matched_barcode_not_in_gex"],
            "reads_invalid_umi": s["reads_invalid_umi"],
            "reads_valid_barcode_and_umi": valid_umi,
            "unique_cell_guide_umis": s["unique_cell_guide_umis"],
            "frac_reads_with_tso": s["reads_with_tso"] / s["reads_total"],
            "frac_reads_with_scaffold_anchor": s["reads_with_scaffold_anchor"] / s["reads_total"],
            "frac_anchored_spacer_matched": matched / s["reads_with_scaffold_anchor"],
            "frac_anchored_exact_match": exact / s["reads_with_scaffold_anchor"],
            "frac_anchored_rescued_1mismatch": s["reads_spacer_matched_via_mismatch"] / s["reads_with_scaffold_anchor"],
            "frac_anchored_unmatched": s["reads_spacer_unmatched"] / s["reads_with_scaffold_anchor"],
            "frac_matched_valid_gex_barcode": in_gex / max(matched, 1),
            "frac_barcode_matched_valid_umi": valid_umi / max(in_gex, 1),
            "frac_anchored_scaffold_A": s["reads_scaffold_A"] / s["reads_with_scaffold_anchor"],
            "frac_anchored_scaffold_C": s["reads_scaffold_C"] / s["reads_with_scaffold_anchor"],
        }
        if well in prior:
            row["prior_exact_only_reads_spacer_matched"] = prior[well]["reads_spacer_matched"]
            row["reads_rescued_vs_prior_exact_only"] = matched - prior[well]["reads_spacer_matched"]
            row["prior_exact_only_unique_cell_guide_umis"] = prior[well]["unique_cell_guide_umis"]
        funnel_rows.append(row)
    funnel = pd.DataFrame(funnel_rows)
    tot = funnel.select_dtypes("number").sum(numeric_only=True)
    all_row = {c: tot[c] for c in funnel.columns if c in tot.index and not c.startswith("frac_")}
    all_row.update({"well": "ALL", "guide_library": "all", "n_fastq_files": int(tot["n_fastq_files"])})
    A = all_row
    all_row["frac_reads_with_tso"] = A["reads_with_tso"] / A["reads_total"]
    all_row["frac_reads_with_scaffold_anchor"] = A["reads_with_scaffold_anchor"] / A["reads_total"]
    all_row["frac_anchored_spacer_matched"] = A["reads_spacer_matched_total"] / A["reads_with_scaffold_anchor"]
    all_row["frac_anchored_exact_match"] = A["reads_spacer_matched_exact"] / A["reads_with_scaffold_anchor"]
    all_row["frac_anchored_rescued_1mismatch"] = A["reads_spacer_matched_via_1mismatch"] / A["reads_with_scaffold_anchor"]
    all_row["frac_anchored_unmatched"] = A["reads_spacer_unmatched"] / A["reads_with_scaffold_anchor"]
    all_row["frac_matched_valid_gex_barcode"] = A["reads_matched_barcode_in_gex"] / A["reads_spacer_matched_total"]
    all_row["frac_barcode_matched_valid_umi"] = A["reads_valid_barcode_and_umi"] / A["reads_matched_barcode_in_gex"]
    all_row["frac_anchored_scaffold_A"] = A["reads_scaffold_A"] / A["reads_with_scaffold_anchor"]
    all_row["frac_anchored_scaffold_C"] = A["reads_scaffold_C"] / A["reads_with_scaffold_anchor"]
    funnel = pd.concat([funnel, pd.DataFrame([all_row])], ignore_index=True)
    funnel.to_csv(tables / "guide_read_retention_funnel.csv", index=False)

    # ---- per-cell table + quantification summary ---------------------------------------------
    scaf = design["scaffold"].astype(str).to_numpy()
    gids = design["guide_id"].astype(str).to_numpy()
    A_cols, C_cols = np.flatnonzero(scaf == "A"), np.flatnonzero(scaf == "C")
    min_umi = cfg.guides.detection_threshold
    per_cell_frames, summary_rows, per_well_rows = [], [], []
    for well, res in results.items():
        M = res.counts.tocsr()
        n_cells = M.shape[0]
        total = np.asarray(M.sum(axis=1)).ravel()
        n_ge1 = np.asarray((M >= 1).sum(axis=1)).ravel()
        n_ge3 = np.asarray((M >= min_umi).sum(axis=1)).ravel()
        dense_top = M.toarray() if n_cells * M.shape[1] < 8e7 else None
        if dense_top is None:
            raise RuntimeError("unexpectedly large matrix")
        order = np.argsort(-dense_top, axis=1)
        top_idx, second_idx = order[:, 0], order[:, 1]
        top_val = dense_top[np.arange(n_cells), top_idx]
        second_val = dense_top[np.arange(n_cells), second_idx]
        def cls(cols):
            sub = dense_top[:, cols]
            i = sub.argmax(axis=1)
            return cols[i], sub.max(axis=1), (sub >= min_umi).sum(axis=1), sub.sum(axis=1)
        a_idx, a_val, a_n, a_sum = cls(A_cols)
        c_idx, c_val, c_n, c_sum = cls(C_cols)
        gex_bc = gex_barcodes[well]
        df = pd.DataFrame({
            "cell_id": [f"{well}_{b}" for b in gex_bc], "well": well, "cell_barcode": gex_bc,
            "total_guide_umis": total, "n_guides_ge1_umi": n_ge1, f"n_guides_ge{min_umi}_umi": n_ge3,
            "top_guide": np.where(top_val > 0, gids[top_idx], ""), "top_guide_umi": top_val, "second_guide_umi": second_val,
            "umis_scaffold_A": a_sum, "umis_scaffold_C": c_sum,
            f"n_guides_A_ge{min_umi}": a_n, f"n_guides_C_ge{min_umi}": c_n,
            "top_guide_A": np.where(a_val > 0, gids[a_idx], ""), "top_guide_A_umi": a_val,
            "top_guide_C": np.where(c_val > 0, gids[c_idx], ""), "top_guide_C_umi": c_val,
        })
        per_cell_frames.append(df)
        s = res.stats
        summary_rows.append({
            "well": well, "guide_library": WELLS[well], "counting_job": os.environ.get("SLURM_JOB_ID", "n/a"),
            "counter": "perturbseq_pipeline.guide_counting (scaffold-aware; exact spacer match, +/-1 nt positional shift, unambiguous 1-mismatch rescue; UMI-deduplicated)",
            "n_gex_cells": n_cells, "cells_with_any_guide_umi": int((total > 0).sum()),
            "cells_with_zero_guide_umis": int((total == 0).sum()),
            f"cells_with_ge1_guide_at_{min_umi}umi": int((n_ge3 >= 1).sum()),
            "frac_gex_cells_with_guide_umi": float((total > 0).mean()),
            "guides_designed": M.shape[1], "guides_detected_any_umi": int((np.asarray(M.sum(axis=0)).ravel() > 0).sum()),
            f"guides_with_ge1_cell_at_{min_umi}umi": int(((M >= min_umi).sum(axis=0) > 0).sum()),
            "total_guide_umis": int(total.sum()), "median_guide_umis_per_cell": float(np.median(total)),
            "median_guides_ge1_per_cell": float(np.median(n_ge1)), f"median_guides_ge{min_umi}_per_cell": float(np.median(n_ge3)),
            "median_top_guide_umi": float(np.median(top_val)),
            f"cells_exactly_1A_1C_at_{min_umi}umi": int(((a_n == 1) & (c_n == 1)).sum()),
            f"cells_ge1A_ge1C_at_{min_umi}umi": int(((a_n >= 1) & (c_n >= 1)).sum()),
            "reads_total": s["reads_total"], "reads_spacer_matched": s["reads_spacer_matched"],
            "reads_spacer_matched_via_1mismatch": s["reads_spacer_matched_via_mismatch"],
            "frac_reads_spacer_matched": s["frac_reads_spacer_matched"],
            "frac_matched_reads_in_gex_barcodes": s["frac_matched_reads_in_gex_barcodes"],
            "reads_matched_barcode_not_in_gex": s["reads_matched_barcode_not_in_gex"],
            "barcode_overlap_guide_vs_gex": "guide matrix rows = GEX filtered barcodes (restricted at counting); matched reads outside GEX barcodes counted above",
            "frac_anchored_scaffold_A": s["frac_anchored_reads_scaffold_A"], "frac_anchored_scaffold_C": s["frac_anchored_reads_scaffold_C"],
        })
        umis = np.asarray(M.sum(axis=0)).ravel()
        pw = pd.DataFrame({"well": well, "guide_id": gids, "target_gene_name": np.where(design["is_control"], "ntc", design["target_raw"]),
                           "is_non_targeting": design["is_control"].astype(bool).to_numpy(), "scaffold": scaf,
                           "umis_in_cells": umis, "cells_positive_ge1": np.asarray((M >= 1).sum(axis=0)).ravel(),
                           f"cells_positive_ge{min_umi}": np.asarray((M >= min_umi).sum(axis=0)).ravel(),
                           "reads_matched_all_barcodes": res.guide_reads,
                           "reads_scaffold_A": res.guide_scaffold_reads[:, 0], "reads_scaffold_C": res.guide_scaffold_reads[:, 1]})
        per_well_rows.append(pw)
    per_cell = pd.concat(per_cell_frames, ignore_index=True)
    per_cell.to_csv(tables / "guide_counts_per_cell.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(tables / "guide_quantification_summary.csv", index=False)
    per_well = pd.concat(per_well_rows, ignore_index=True)
    allw = per_well.groupby(["guide_id", "target_gene_name", "is_non_targeting", "scaffold"], as_index=False, sort=False).sum(numeric_only=True)
    allw.insert(0, "well", "ALL")
    per_well = pd.concat([per_well, allw[per_well.columns]], ignore_index=True)
    per_well.to_csv(tables / "guide_counts_per_well.csv", index=False)

    # ---- guide reference / pair map update with this run's scaffold classes ------------------------
    ref_path = tables / "guide_reference_used.csv"
    ref = pd.read_csv(ref_path, dtype={"pair_id": str}, keep_default_na=False)
    d = design.set_index("guide_id")
    assert set(ref.guide_id) == set(d.index)
    ref["scaffold_empirical"] = ref.guide_id.map(d["scaffold"]).astype(str)
    ref["scaffold_empirical_purity"] = ref.guide_id.map(d["scaffold_purity"])
    ref["scaffold_empirical_reads"] = ref.guide_id.map(d["scaffold_reads_total"])
    ref["scaffold_empirical_reads_A"] = ref.guide_id.map(d["scaffold_reads_A"])
    ref["scaffold_empirical_reads_C"] = ref.guide_id.map(d["scaffold_reads_C"])
    design_has_scaffold = (ref["scaffold_design"].astype(str) != "unknown").any()
    if not design_has_scaffold:
        ref["scaffold"] = ref["scaffold_empirical"]
        ref["scaffold_source"] = np.where(ref["scaffold"] != "unknown", f"empirical_from_reads_job_{os.environ.get('SLURM_JOB_ID', 'n/a')}", "unspecified_no_reads")
    ref["observed_in_any_well"] = ref.guide_id.map(allw.set_index("guide_id")["umis_in_cells"] > 0)
    ref.to_csv(ref_path, index=False)
    pm_path = tables / "guide_pair_map.csv"
    pm = pd.read_csv(pm_path, dtype=str, keep_default_na=False)
    pm["scaffold"] = pm.guide_id.map(ref.set_index("guide_id")["scaffold"])
    pm["scaffold_source"] = pm.guide_id.map(ref.set_index("guide_id")["scaffold_source"])
    pm.to_csv(pm_path, index=False)
    log.info("scaffold classes this run: %s", ref["scaffold"].value_counts().to_dict())

    # ---- matching-rule documentation ----------------------------------------------------------------
    F = funnel.set_index("well")
    md = [
        "# Guide quantification: matching rule and safeguards", "",
        f"- Counter: `perturbseq_pipeline.guide_counting.count_guides` (SLURM job {os.environ.get('SLURM_JOB_ID', 'n/a')}, {datetime.now():%Y-%m-%d %H:%M})",
        f"- Read structure: R1 = [{fq.barcode_length} nt cell barcode][{fq.umi_length} nt UMI][TSO {fq.tso}][variable non-templated G run][{fq.protospacer_length} nt protospacer][scaffold]; "
        "the protospacer is taken as the 20 nt immediately 5' of the scaffold anchor, so the G run length does not matter.",
        f"- Scaffold anchors: A = `{fq.scaffolds['A']}`, C = `{fq.scaffolds['C']}` (searched from position {fq.anchor_search_start}).",
        f"- Matching rule: (1) exact 20-mer lookup against the 560 designed protospacers; (2) unambiguous 1-mismatch lookup "
        f"(max_mismatches = {fq.max_mismatches}); (3) exact/1-mismatch lookup after a +/-{fq.position_shift} nt positional shift.",
        "- Ambiguity safeguards: the 1-mismatch index drops any variant that equals a designed protospacer or that could derive from two different "
        "designed guides (`build_protospacer_index`). The design audit found **no two designed protospacers within Hamming distance 2** "
        "(`tables/guide_design_near_identical_protospacers.csv`), so every 1-mismatch rescue is unambiguous by construction.",
        "- Unmatched anchored reads are counted (`reads_spacer_unmatched`), and a 1-in-50 sample of their protospacers is written per well to "
        "`guide_counts/<well>/<well>_unmatched_protospacers.tsv` (top 50 with estimated read counts). Matched reads whose barcode is not a GEX cell are counted "
        "(`reads_matched_barcode_not_in_gex`) but not stored per UMI.",
        "- Cell universe: Cell Ranger filtered GEX barcodes of the paired well (guide/GEX overlap enforced at counting; zero-guide cells are retained as all-zero rows).",
        "", "## Rescue accounting", "",
        "| well | anchored reads | exact | +/-1 shift | 1-mismatch (all) | 1-mismatch at position 1 | unmatched | exact frac | rescued frac | unmatched frac |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for w, r in F.iterrows():
        md.append(f"| {w} | {int(r.reads_with_scaffold_anchor):,} | {int(r.reads_spacer_matched_exact):,} | {int(r.reads_spacer_matched_via_shift):,} | "
                  f"{int(r.reads_spacer_matched_via_1mismatch):,} | {int(r.reads_spacer_matched_via_1mismatch_pos1):,} | {int(r.reads_spacer_unmatched):,} | "
                  f"{r.frac_anchored_exact_match:.4f} | {r.frac_anchored_rescued_1mismatch:.4f} | {r.frac_anchored_unmatched:.4f} |")
    if prior:
        md += ["", "Reads rescued relative to the previous exact-only run (job 20045135): " +
               ", ".join(f"{w}: {int(F.loc[w, 'reads_rescued_vs_prior_exact_only']):,}" for w in WELLS if w in prior)]
    md += ["", f"Scaffold classes after this run: {ref['scaffold'].value_counts().to_dict()}; guides observed in any well: {int(ref.observed_in_any_well.sum())}/560.",
           "", "Outputs: `tables/guide_read_retention_funnel.csv`, `tables/guide_quantification_summary.csv`, `tables/guide_counts_per_cell.csv`, "
           "`tables/guide_counts_per_well.csv`, `guide_counts/<well>/{matrix.mtx.gz,barcodes.tsv.gz,features.tsv.gz,*_guide_summary.tsv,*_guide_counting_stats.json,*_unmatched_protospacers.tsv}`."]
    (out_root / "guide_quantification_methods.md").write_text("\n".join(md) + "\n")
    log.info("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
