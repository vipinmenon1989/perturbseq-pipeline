"""Prepare Hanrui Fang inputs in the format the pipeline's default path supports.

* Extracts the Cell Ranger ``filtered_feature_bc_matrix/`` MTX directory,
  ``raw_feature_bc_matrix.h5`` and ``metrics_summary.csv`` from each outs tar
  (never modifies the raw tree; extraction target is the inputs directory).
* Re-emits the scaffold-aware guide UMI counts (produced by the basic QC
  stage, outputs/hanrui_fang_qc/guide_counts/<S>/) as 10x MTX directories
  whose barcodes carry the same ``-1`` suffix as the GEX matrices, so
  ``input.guide_mtx_dirs`` aligns 1:1 with ``input.mtx_dirs``.
* Verifies overlap / dimensions and writes the guide quantification tables.

Run on a compute node (SLURM).
"""

from __future__ import annotations

import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.io
import scipy.sparse as sp

DATA = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X")
QC_OUT = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc")
INPUTS = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_inputs")
REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
TABLES = REPO / "results" / "Hanrui_fang" / "tables"
WELLS = {"HF011A": "HF011AF", "HF011B": "HF011BF", "HF012A": "HF012AF", "HF012B": "HF012BF"}


def log(*a):
    print(*a, flush=True)


def extract(well: str) -> Path:
    dest = INPUTS / "cellranger" / well
    dest.mkdir(parents=True, exist_ok=True)
    mtx = dest / "filtered_feature_bc_matrix"
    if (mtx / "matrix.mtx.gz").exists() and (dest / "raw_feature_bc_matrix.h5").exists():
        log(f"[{well}] already extracted")
        return dest
    tar = next((DATA / well / "analysis").glob(f"*/{well}_cellranger_count_outs.tar"))
    log(f"[{well}] extracting from {tar}")
    subprocess.run([
        "tar", "-xf", str(tar), "-C", str(dest), "--strip-components=1", "--wildcards",
        f"{well}_cellranger_count_outs/filtered_feature_bc_matrix/*",
        f"{well}_cellranger_count_outs/filtered_feature_bc_matrix.h5",
        f"{well}_cellranger_count_outs/raw_feature_bc_matrix.h5",
        f"{well}_cellranger_count_outs/metrics_summary.csv",
    ], check=True)
    return dest


def read_barcodes(path: Path) -> list:
    with gzip.open(path, "rt") as fh:
        return [l.strip() for l in fh if l.strip()]


def guide_mtx(well: str, gex_barcodes: list) -> dict:
    src = QC_OUT / "guide_counts" / well
    dest = INPUTS / "guides" / well
    dest.mkdir(parents=True, exist_ok=True)
    with gzip.open(src / "matrix.mtx.gz", "rb") as fh:
        m = scipy.io.mmread(fh).tocsc()  # guides x cells (10x orientation)
    bare = read_barcodes(src / "barcodes.tsv.gz")
    feats = pd.read_csv(src / "features.tsv.gz", sep="\t", header=None, names=["id", "name", "type"])
    assert m.shape == (len(feats), len(bare)), (m.shape, len(feats), len(bare))
    gex_bare = [b.rsplit("-", 1)[0] for b in gex_barcodes]
    suffix = {b.rsplit("-", 1)[0]: b for b in gex_barcodes}
    assert len(suffix) == len(gex_barcodes), "GEX barcodes not unique after suffix strip"
    pos = {b: i for i, b in enumerate(bare)}
    idx = np.array([pos.get(b, -1) for b in gex_bare])
    n_missing = int((idx < 0).sum())
    assert n_missing == 0, f"{well}: {n_missing} GEX barcodes have no guide row"
    m_cells = m[:, idx]
    with gzip.open(dest / "matrix.mtx.gz", "wb") as fh:
        scipy.io.mmwrite(fh, m_cells.tocoo(), field="integer")
    with gzip.open(dest / "barcodes.tsv.gz", "wt") as fh:
        fh.write("\n".join(gex_barcodes) + "\n")
    shutil.copy(src / "features.tsv.gz", dest / "features.tsv.gz")
    # verification read-back with scanpy the way io._read_guide_mtx does
    import scanpy as sc

    g = sc.read_10x_mtx(dest, var_names="gene_ids", cache=False, gex_only=False)
    e_bc = pd.Index(gex_barcodes)
    overlap = len(e_bc.intersection(g.obs_names))
    stats = {
        "well": well,
        "guide_library": WELLS[well],
        "guide_mtx_dir": str(dest),
        "n_guides": int(g.n_vars),
        "n_cells": int(g.n_obs),
        "gex_cells": len(gex_barcodes),
        "barcode_overlap": overlap,
        "frac_overlap": overlap / len(gex_barcodes),
        "guide_var_columns": ",".join(g.var.columns),
        "feature_types": ",".join(sorted(set(g.var["feature_types"].astype(str)))),
        "total_guide_umis": int(g.X.sum()),
        "cells_with_zero_guide_umis": int((np.asarray(g.X.sum(axis=1)).ravel() == 0).sum()),
        "guides_with_zero_umis": int((np.asarray(g.X.sum(axis=0)).ravel() == 0).sum()),
        "example_gex_barcode": gex_barcodes[0],
        "example_guide_barcode": str(g.obs_names[0]),
    }
    assert overlap == len(gex_barcodes)
    assert "gene_symbols" in g.var.columns, g.var.columns
    log(f"[{well}] guide MTX {g.shape} written; overlap {overlap}/{len(gex_barcodes)}; var cols {list(g.var.columns)}")
    return stats


def main() -> int:
    INPUTS.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    align_rows, metrics_rows = [], []
    for well in WELLS:
        dest = extract(well)
        gex_bc = read_barcodes(dest / "filtered_feature_bc_matrix" / "barcodes.tsv.gz")
        feats = pd.read_csv(dest / "filtered_feature_bc_matrix" / "features.tsv.gz", sep="\t", header=None)
        log(f"[{well}] GEX MTX: {len(gex_bc)} barcodes, {len(feats)} features, example {gex_bc[0]}")
        align_rows.append(guide_mtx(well, gex_bc))
        met = pd.read_csv(dest / "metrics_summary.csv")
        met.insert(0, "well", well)
        metrics_rows.append(met)

    align = pd.DataFrame(align_rows)
    align.to_csv(TABLES / "guide_gex_alignment_check.csv", index=False)
    metrics = pd.concat(metrics_rows, ignore_index=True)
    metrics.to_csv(TABLES / "cellranger_metrics_per_well.csv", index=False)

    # Guide quantification summary from the scaffold-aware counter run.
    gq = pd.read_csv(QC_OUT / "tables" / "guide_qc_summary.tsv", sep="\t")
    rows = []
    for well in WELLS:
        st = json.load(open(QC_OUT / "guide_counts" / well / f"{well}_guide_counting_stats.json"))["sample"]
        r = gq[gq["sample_id"] == well].iloc[0]
        a = align[align["well"] == well].iloc[0]
        rows.append({
            "well": well, "guide_library": WELLS[well], "counter": "perturbseq_pipeline.guide_counting (scaffold-aware, exact spacer match, +/-1 nt positional shift, UMI-deduplicated)",
            "counting_job": "SLURM 20045135", "n_fastq_files": st["n_files"],
            "reads_total": st["reads_total"],
            "reads_with_tso": st["reads_with_tso"], "frac_reads_with_tso": st["frac_reads_with_tso"],
            "reads_with_scaffold_anchor": st["reads_with_scaffold_anchor"], "frac_reads_with_scaffold_anchor": st["frac_reads_with_scaffold_anchor"],
            "reads_scaffold_A": st["reads_scaffold_A"], "reads_scaffold_C": st["reads_scaffold_C"],
            "reads_spacer_matched": st["reads_spacer_matched"], "frac_reads_spacer_matched": st["frac_reads_spacer_matched"],
            "reads_spacer_matched_via_shift": st["reads_spacer_matched_via_shift"],
            "reads_spacer_unmatched": st["reads_spacer_unmatched"],
            "reads_matched_barcode_in_gex": st["reads_matched_barcode_in_gex"], "frac_matched_reads_in_gex_barcodes": st["frac_matched_reads_in_gex_barcodes"],
            "reads_matched_barcode_not_in_gex": st["reads_matched_barcode_not_in_gex"],
            "reads_invalid_umi": st["reads_invalid_umi"],
            "unique_cell_guide_umis": st["unique_cell_guide_umis"],
            "guides_designed": st["guides_designed"], "guides_observed_any_umi": st["guides_detected_any_umi"],
            "gex_cells": st["cells_in_gex_universe"], "cells_with_any_guide_umi": st["cells_with_any_guide_umi"],
            "cells_with_zero_guide_umis": int(a["cells_with_zero_guide_umis"]),
            "median_guide_umis_per_cell": r["median_guide_umi_total"],
            "guide_mtx_dir": a["guide_mtx_dir"], "barcode_overlap_with_gex": int(a["barcode_overlap"]),
        })
    pd.DataFrame(rows).to_csv(TABLES / "guide_quantification_summary.csv", index=False)

    ref = pd.read_csv(QC_OUT / "tables" / "guide_feature_table.tsv", sep="\t")
    keep = [c for c in ("guide_id", "protospacer", "target_raw", "target", "is_control", "scaffold", "scaffold_source",
                        "scaffold_purity", "scaffold_reads_total", "on_target_efficacy_score", "beginswithg") if c in ref.columns]
    keep += [c for c in ref.columns if c.startswith("umis_") or c.startswith("cells_positive_")]
    ref = ref[keep].copy()
    ref.insert(0, "design_source", str(DATA / "web_summaries" / "design_out_v2.xlsx"))
    ref.to_csv(TABLES / "guide_reference_used.csv", index=False)
    log(align.to_string())
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
