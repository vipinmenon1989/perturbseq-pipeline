"""Reopen the basic-QC h5ad outputs and verify the documented contract.

Usage: python jobs/validate_qc_outputs.py <outdir>
Writes <outdir>/reports/final_validation.txt and prints it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp


def check(adata: ad.AnnData, label: str, lines: list) -> None:
    lines.append(f"\n[{label}] {adata.n_obs:,} cells x {adata.n_vars:,} genes")
    ok = True

    def rec(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        lines.append(f"  {'PASS' if cond else 'FAIL'}  {name}{(': ' + detail) if detail else ''}")

    rec("unique obs names", adata.obs_names.is_unique)
    rec("unique var names", adata.var_names.is_unique)
    X = adata.X
    rec("X is sparse CSR", sp.isspmatrix_csr(X), str(type(X)))
    rec("X integer dtype", np.issubdtype(X.dtype, np.integer), str(X.dtype))
    sample = X[: min(2000, X.shape[0])]
    rec("X values integral (sample)", bool(np.all(np.mod(sample.data, 1) == 0)))
    rec("layers['counts'] present", "counts" in adata.layers)
    if "counts" in adata.layers:
        C = adata.layers["counts"]
        rec("counts integer dtype", np.issubdtype(C.dtype, np.integer), str(C.dtype))
        rec("X == counts (sample)", (sample != C[: sample.shape[0]]).nnz == 0)
    for col in ("sample_id", "condition_code", "gem_well", "guide_library", "cell_barcode"):
        rec(f"obs.{col}", col in adata.obs)
    rec("sample identities", True, str(dict(adata.obs["sample_id"].value_counts().sort_index())))
    for col in ("total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "qc_low_counts",
                "qc_high_counts", "qc_low_genes", "qc_high_genes", "qc_high_mt", "gex_qc_pass"):
        rec(f"QC column {col}", col in adata.obs)
    for col in ("doublet_score", "predicted_doublet"):
        rec(f"doublet column {col}", col in adata.obs)
    for col in ("n_guides", "n_guides_A", "n_guides_C", "guide_umi_total", "guide_umi_A", "guide_umi_C",
                "guide_detected", "guide_structure_pass", "guide_multiplet_flag", "perturbation_assignable"):
        rec(f"guide column {col}", col in adata.obs)
    rec("obsm['guide_counts']", "guide_counts" in adata.obsm)
    if "guide_counts" in adata.obsm:
        G = adata.obsm["guide_counts"]
        rec("guide matrix rows == cells", G.shape[0] == adata.n_obs, str(G.shape))
        feats = adata.uns.get("guide_features")
        rec("guide metadata rows == guide columns", feats is not None and len(feats) == G.shape[1],
            f"{len(feats) if feats is not None else 'NA'} guide features")
        rec("guide_umi_total == row sums", bool(np.all(np.asarray(G.sum(axis=1)).ravel() == adata.obs["guide_umi_total"].to_numpy())))
    n_dbl = int(adata.obs["predicted_doublet"].astype(bool).sum())
    n_gm = int(adata.obs["guide_multiplet_flag"].astype(bool).sum())
    lines.append(f"  Number of predicted doublets in {label}: {n_dbl:,}")
    lines.append(f"  Number of guide multiplets in {label}: {n_gm:,}")
    rec("predicted doublets retained (> 0)", n_dbl > 0)
    rec("guide multiplets retained (> 0)", n_gm > 0)
    rec("no embeddings", not any(k.startswith("X_") for k in adata.obsm))
    rec("no lognorm layer", "lognorm" not in adata.layers)
    for key in ("provenance", "qc_thresholds", "sample_manifest", "config", "basic_qc"):
        rec(f"uns['{key}']", key in adata.uns)
    lines.append(f"  => {'ALL CHECKS PASSED' if ok else 'SOME CHECKS FAILED'}")


def main(outdir: str) -> int:
    outdir = Path(outdir)
    lines = [f"Final validation of basic QC outputs in {outdir}"]
    allc = ad.read_h5ad(outdir / "combined" / "perttf_qc_allcells.h5ad")
    check(allc, "perttf_qc_allcells.h5ad", lines)
    per_sample_input = allc.obs["sample_id"].value_counts()
    passed = ad.read_h5ad(outdir / "combined" / "perttf_qc.h5ad")
    check(passed, "perttf_qc.h5ad", lines)
    lines.append("\n[consistency]")
    lines.append(f"  gex_qc_pass in all-cells: {int(allc.obs['gex_qc_pass'].sum()):,} == QC object cells: {passed.n_obs:,} -> "
                 f"{'PASS' if int(allc.obs['gex_qc_pass'].sum()) == passed.n_obs else 'FAIL'}")
    exp_dbl = int((allc.obs["predicted_doublet"].astype(bool) & allc.obs["gex_qc_pass"]).sum())
    lines.append(f"  doublets expected in QC object {exp_dbl:,} == found {int(passed.obs['predicted_doublet'].astype(bool).sum()):,}")
    exp_gm = int((allc.obs["guide_multiplet_flag"].astype(bool) & allc.obs["gex_qc_pass"]).sum())
    lines.append(f"  guide multiplets expected in QC object {exp_gm:,} == found {int(passed.obs['guide_multiplet_flag'].astype(bool).sum()):,}")
    lines.append(f"  predicted doublets that pass expression QC: {exp_dbl:,} of {int(allc.obs['predicted_doublet'].astype(bool).sum()):,}")
    lines.append(f"  guide_detected == False cells passing expression QC: {int((~passed.obs['guide_detected'].astype(bool)).sum()):,}")
    lines.append(f"  perturbation_assignable True: {int(allc.obs['perturbation_assignable'].astype(bool).sum())}")
    for sid, h5 in sorted((p.name.split("_qc_allcells")[0], p) for p in (outdir / "per_sample").glob("*_qc_allcells.h5ad")):
        a = ad.read_h5ad(h5, backed="r")
        lines.append(f"  per-sample {sid}: {a.n_obs:,} cells (== {int(per_sample_input.get(sid, 0)):,} in combined) -> "
                     f"{'PASS' if a.n_obs == int(per_sample_input.get(sid, 0)) else 'FAIL'}; obsm guide_counts "
                     f"{'present' if 'guide_counts' in a.obsm else 'absent'}")
        a.file.close()
    feats = allc.uns.get("guide_features")
    if feats is not None:
        umi_cols = [c for c in feats.columns if c.startswith("scaffold_reads_total")]
        lines.append(f"\n[guides] designed {len(feats)}; scaffold classes {dict(pd.Series(feats['scaffold']).value_counts())}")
        G = sp.csr_matrix(allc.obsm["guide_counts"])
        lines.append(f"  guides with any UMI in cells: {int((G.sum(axis=0) > 0).sum())}")
        lines.append(f"  guide-positive cells (>=1 detected guide): {int(allc.obs['guide_detected'].astype(bool).sum()):,}")
        lines.append(f"  guide-count matrix shape: {G.shape}")
    text = "\n".join(lines)
    (outdir / "reports" / "final_validation.txt").write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
