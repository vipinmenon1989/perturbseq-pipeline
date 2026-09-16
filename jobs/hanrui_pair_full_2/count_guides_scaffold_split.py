#!/usr/bin/env python
"""Iteration 2, step 2 (SLURM only): scaffold-specific guide quantification of the four guide-capture
libraries. Features = designed protospacer x scaffold class (``<design_id>:<A|C>``), so the NO-TARGET_1
spacer (cloned behind both scaffolds) is counted per scaffold and wrong-scaffold (chimeric) reads become
explicit off-design features. Matching rule unchanged: exact 20-mer 5' of the scaffold anchor, unambiguous
1-mismatch rescue, +/-1 nt positional shift, UMI-deduplicated, cells = Cell Ranger filtered GEX barcodes.
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

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guide_counting import GuideCountJob, count_guides, find_guide_fastqs, write_guide_counts
from perturbseq_pipeline.guide_design import load_guide_design

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("count_guides_scaffold_split")
WELLS = {"HF011A": "HF011AF", "HF011B": "HF011BF", "HF012A": "HF012AF", "HF012B": "HF012BF"}
JOB = os.environ.get("SLURM_JOB_ID", "n/a")


def read_barcodes(path: Path) -> list[str]:
    with gzip.open(path, "rt") as fh:
        return [l.strip() for l in fh if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qc-config", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--cellranger-root", required=True)
    ap.add_argument("--out", required=True, help="results/Hanrui_Fang_pair_guide_full_2")
    ap.add_argument("--max-mismatches", type=int, default=1)
    ap.add_argument("--n-workers", type=int, default=8)
    a = ap.parse_args()
    out = Path(a.out)
    audit, gc_root = out / "audit", out / "inputs" / "guide_counts"
    gc_root.mkdir(parents=True, exist_ok=True)

    cfg = Config.from_yaml(a.qc_config)
    cfg.guides.fastq.max_mismatches = a.max_mismatches
    cfg.guides.fastq.n_workers = a.n_workers
    cfg.guides.fastq.scaffold_specific_features = True
    fq = cfg.guides.fastq
    design = load_guide_design(cfg)
    assert len(design) == 560, len(design)
    ref = pd.read_csv(audit / "pair_guide_reference.csv", dtype=str, keep_default_na=False).set_index("guide_id")
    log.info("design: %d guides -> %d scaffold-specific features; reference: %d features", len(design), 2 * len(design), len(ref))

    jobs, gex_barcodes = [], {}
    suffix_re = re.compile(fq.barcode_suffix_regex)
    for well, lib in WELLS.items():
        bcs = read_barcodes(Path(a.cellranger_root) / well / "filtered_feature_bc_matrix" / "barcodes.tsv.gz")
        gex_barcodes[well] = bcs
        fastqs = find_guide_fastqs(Path(a.data_root) / lib, fq.read_pattern)
        log.info("%s: %d GEX barcodes, FASTQs %s", well, len(bcs), [Path(f).name for f in fastqs])
        jobs.append(GuideCountJob(sample_id=well, fastq_files=fastqs, cell_barcodes=[suffix_re.sub("", b) for b in bcs]))
    t0 = datetime.now()
    results = count_guides(jobs, design, cfg, n_workers=a.n_workers)
    log.info("counting finished in %s", datetime.now() - t0)

    fd = next(iter(results.values())).feature_design.copy()
    assert list(fd["guide_id"]) == list(ref.index), "feature order differs from the audit reference"
    for c in ("designed_slot", "feature_role", "pair_id", "construct_types", "construct_position", "target_gene_name", "target_symbol", "is_non_targeting"):
        fd[c] = ref.loc[fd["guide_id"], c].to_numpy()
    fd["target_raw"] = ref.loc[fd["guide_id"], "target_gene"].to_numpy()
    fd["designed_slot"] = fd["designed_slot"].astype(str).str.lower() == "true"

    funnel_rows, summary_rows, per_well_rows, offdesign_rows = [], [], [], []
    min_umi = cfg.guides.detection_threshold
    role = fd["feature_role"].to_numpy()
    for well, res in results.items():
        write_guide_counts(res, fd, gc_root / well)
        M = res.counts.tocsr()
        umis = np.asarray(M.sum(axis=0)).ravel()
        cells1 = np.asarray((M >= 1).sum(axis=0)).ravel()
        cells3 = np.asarray((M >= min_umi).sum(axis=0)).ravel()
        s = res.stats
        matched = s["reads_spacer_matched"]
        exact = matched - s["reads_spacer_matched_via_shift"] - s["reads_spacer_matched_via_mismatch"]
        funnel_rows.append({"well": well, "guide_library": WELLS[well], "n_fastq_files": s["n_files"], "reads_total": s["reads_total"], "reads_with_tso": s["reads_with_tso"],
                            "reads_with_scaffold_anchor": s["reads_with_scaffold_anchor"], "reads_scaffold_A": s["reads_scaffold_A"], "reads_scaffold_C": s["reads_scaffold_C"],
                            "reads_spacer_matched_total": matched, "reads_spacer_matched_exact": exact, "reads_spacer_matched_via_shift": s["reads_spacer_matched_via_shift"],
                            "reads_spacer_matched_via_1mismatch": s["reads_spacer_matched_via_mismatch"], "reads_spacer_matched_via_1mismatch_pos1": s["reads_spacer_matched_via_mismatch_pos1"],
                            "reads_spacer_unmatched": s["reads_spacer_unmatched"], "reads_matched_barcode_in_gex": s["reads_matched_barcode_in_gex"], "reads_matched_barcode_not_in_gex": s["reads_matched_barcode_not_in_gex"],
                            "reads_invalid_umi": s["reads_invalid_umi"], "unique_cell_feature_umis": s["unique_cell_guide_umis"],
                            "frac_reads_with_scaffold_anchor": s["frac_reads_with_scaffold_anchor"], "frac_anchored_spacer_matched": matched / s["reads_with_scaffold_anchor"],
                            "frac_anchored_exact_match": exact / s["reads_with_scaffold_anchor"], "frac_anchored_rescued_1mismatch": s["reads_spacer_matched_via_mismatch"] / s["reads_with_scaffold_anchor"],
                            "frac_anchored_unmatched": s["reads_spacer_unmatched"] / s["reads_with_scaffold_anchor"], "frac_matched_valid_gex_barcode": s["reads_matched_barcode_in_gex"] / max(matched, 1),
                            "frac_anchored_scaffold_A": s["frac_anchored_reads_scaffold_A"], "frac_anchored_scaffold_C": s["frac_anchored_reads_scaffold_C"]})
        total_cell = np.asarray(M.sum(axis=1)).ravel()
        n_ge3 = np.asarray((M >= min_umi).sum(axis=1)).ravel()
        des = M[:, np.flatnonzero(role == "designed_slot")]
        n_ge3_designed = np.asarray((des >= min_umi).sum(axis=1)).ravel()
        summary_rows.append({"well": well, "guide_library": WELLS[well], "counting_job": JOB, "n_gex_cells": M.shape[0], "n_features": M.shape[1], "n_designed_slot_features": int((role == "designed_slot").sum()),
                             "cells_with_any_guide_umi": int((total_cell > 0).sum()), "frac_gex_cells_with_guide_umi": float((total_cell > 0).mean()),
                             f"cells_with_ge1_feature_at_{min_umi}umi": int((n_ge3 >= 1).sum()), "total_guide_umis": int(total_cell.sum()), "median_guide_umis_per_cell": float(np.median(total_cell)),
                             f"median_features_ge{min_umi}_per_cell": float(np.median(n_ge3)), f"median_designed_features_ge{min_umi}_per_cell": float(np.median(n_ge3_designed)),
                             "features_detected_any_umi": int((umis > 0).sum()), "designed_slots_detected_any_umi": int(((umis > 0) & (role == "designed_slot")).sum()),
                             "reads_total": s["reads_total"], "reads_spacer_matched": matched, "frac_reads_spacer_matched": s["frac_reads_spacer_matched"], "frac_matched_reads_in_gex_barcodes": s["frac_matched_reads_in_gex_barcodes"]})
        for r in ("designed_slot", "wrong_scaffold_chimera_diagnostic", "non_cloned_spacer"):
            m = role == r
            offdesign_rows.append({"well": well, "feature_role": r, "n_features": int(m.sum()), "umis_in_cells": int(umis[m].sum()), "frac_of_cell_umis": float(umis[m].sum() / max(umis.sum(), 1)),
                                   "reads_matched_all_barcodes": int(res.guide_reads[m].sum()), "frac_of_matched_reads": float(res.guide_reads[m].sum() / max(res.guide_reads.sum(), 1)),
                                   f"cells_with_ge1_feature_at_{min_umi}umi": int((np.asarray((M[:, np.flatnonzero(m)] >= min_umi).sum(axis=1)).ravel() >= 1).sum()) if m.any() else 0,
                                   f"features_with_ge1_cell_at_{min_umi}umi": int((cells3[m] >= 1).sum())})
        per_well_rows.append(pd.DataFrame({"well": well, "guide_id": fd["guide_id"], "design_guide_id": fd["design_guide_id"], "scaffold": fd["scaffold"], "feature_role": role, "pair_id": fd["pair_id"],
                                           "target_gene_name": fd["target_gene_name"], "is_non_targeting": fd["is_non_targeting"], "umis_in_cells": umis, "cells_positive_ge1": cells1, f"cells_positive_ge{min_umi}": cells3,
                                           "reads_matched_all_barcodes": res.guide_reads}))
    funnel = pd.DataFrame(funnel_rows)
    funnel.to_csv(audit / "guide_read_retention_funnel.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(audit / "guide_quantification_summary.csv", index=False)
    pd.DataFrame(offdesign_rows).to_csv(audit / "off_design_feature_summary.csv", index=False)
    per_well = pd.concat(per_well_rows, ignore_index=True)
    allw = per_well.groupby(["guide_id", "design_guide_id", "scaffold", "feature_role", "pair_id", "target_gene_name", "is_non_targeting"], as_index=False, sort=False).sum(numeric_only=True)
    allw.insert(0, "well", "ALL")
    per_well = pd.concat([per_well, allw[per_well.columns]], ignore_index=True)
    per_well.to_csv(audit / "guide_counts_per_well.csv", index=False)

    # empirical columns into the reference
    aw = allw.set_index("guide_id")
    ref["reads_matched_all_wells"] = aw.loc[ref.index, "reads_matched_all_barcodes"].astype(int).to_numpy()
    ref["umis_in_cells_all_wells"] = aw.loc[ref.index, "umis_in_cells"].astype(int).to_numpy()
    ref[f"cells_ge{min_umi}umi_all_wells"] = aw.loc[ref.index, f"cells_positive_ge{min_umi}"].astype(int).to_numpy()
    ref["observed_in_reads"] = ref["reads_matched_all_wells"] > 0
    ref["observed_sequence"] = np.where(ref["observed_in_reads"], ref["guide_sequence"], "")
    ref["sequence_match_status"] = ref["sequence_match_status"] + np.where(ref["observed_in_reads"], "; observed in reads (exact 20-mer / unambiguous 1-mismatch)", "; not observed in any well")
    ref["counting_job"] = JOB
    ref.reset_index().to_csv(audit / "pair_guide_reference.csv", index=False)

    F = funnel.set_index("well")
    od = pd.DataFrame(offdesign_rows)
    md = ["# Guide quantification (iteration 2): scaffold-specific features", "",
          f"- Counter: `perturbseq_pipeline.guide_counting.count_guides` with `guides.fastq.scaffold_specific_features: true` (SLURM job {JOB}, {datetime.now():%Y-%m-%d %H:%M}).",
          f"- Read structure: R1 = [{fq.barcode_length} nt cell barcode][{fq.umi_length} nt UMI][TSO {fq.tso}][variable non-templated bases][{fq.protospacer_length} nt protospacer][scaffold]; the protospacer is the 20 nt immediately 5' of the scaffold anchor.",
          f"- Scaffold anchors: A = `{fq.scaffolds['A']}` (document Scaffold 2, construct position 2), C = `{fq.scaffolds['C']}` (document Scaffold 1, construct position 1).",
          f"- Matching: exact 20-mer against the 560 designed protospacers; unambiguous 1-mismatch rescue (max_mismatches = {fq.max_mismatches}); +/-{fq.position_shift} nt positional shift. Designed protospacers are >= 3 mismatches apart, so rescues are unambiguous.",
          "- Feature = (designed protospacer, scaffold class carried by the read): 1,120 features; 391 are designed construct slots, 389 are wrong-scaffold diagnostics (cloned spacer read with the other scaffold), 340 are never-cloned spacers.",
          "- UMI de-duplication per (cell barcode, feature, UMI); cell universe = Cell Ranger filtered GEX barcodes of the paired well (zero-guide cells kept as all-zero rows).", "",
          "## Read retention", "", "| well | reads | anchored | spacer matched | exact | 1-mismatch | unmatched | in GEX barcodes | unique cell-feature UMIs |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for w, r in F.iterrows():
        md.append(f"| {w} | {int(r.reads_total):,} | {int(r.reads_with_scaffold_anchor):,} | {int(r.reads_spacer_matched_total):,} | {int(r.reads_spacer_matched_exact):,} | {int(r.reads_spacer_matched_via_1mismatch):,} | {int(r.reads_spacer_unmatched):,} | {int(r.reads_matched_barcode_in_gex):,} | {int(r.unique_cell_feature_umis):,} |")
    md += ["", "## UMI mass by feature role", "", "| well | role | features | UMIs in cells | fraction of UMIs | fraction of matched reads |", "|---|---|---:|---:|---:|---:|"]
    for _, r in od.iterrows():
        md.append(f"| {r.well} | {r.feature_role} | {r.n_features} | {int(r.umis_in_cells):,} | {r.frac_of_cell_umis:.4f} | {r.frac_of_matched_reads:.4f} |")
    md += ["", "Outputs: `inputs/guide_counts/<well>/{matrix.mtx.gz,barcodes.tsv.gz,features.tsv.gz,*_guide_summary.tsv,*_guide_counting_stats.json,*_unmatched_protospacers.tsv}`, `audit/guide_read_retention_funnel.csv`, `audit/guide_quantification_summary.csv`, `audit/off_design_feature_summary.csv`, `audit/guide_counts_per_well.csv`, `audit/pair_guide_reference.csv` (empirical columns appended)."]
    (audit / "guide_quantification_methods.md").write_text("\n".join(md) + "\n")
    (gc_root / "PROVENANCE.md").write_text(f"Scaffold-specific guide count matrices written by SLURM job {JOB} on {datetime.now():%Y-%m-%d} (jobs/hanrui_pair_full_2/count_guides_scaffold_split.py). See audit/guide_quantification_methods.md.\n")
    log.info("done: %s", od.groupby("feature_role")["frac_of_cell_umis"].mean().to_dict())
    return 0


if __name__ == "__main__":
    sys.exit(main())
