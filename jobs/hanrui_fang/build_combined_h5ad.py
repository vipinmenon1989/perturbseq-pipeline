#!/usr/bin/env python
"""Step 6: build the combined Hanrui Fang H5AD (four wells; GEX + 560 CRISPR Guide
Capture features) plus one per-well H5AD each, from the staged Cell Ranger filtered
matrices and the scaffold-aware guide counts of jobs/hanrui_fang/03_count_guides.slurm.

SLURM only (jobs/hanrui_fang/04_build_combined_h5ad.slurm).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc
import scipy.sparse as sp

from perturbseq_pipeline.guide_counting import read_guide_counts

WELLS = {"HF011A": ("HF011", "A", "HF011AF"), "HF011B": ("HF011", "B", "HF011BF"),
         "HF012A": ("HF012", "A", "HF012AF"), "HF012B": ("HF012", "B", "HF012BF")}
ALIASES = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3"}
GUIDE_VAR_REQUIRED = ["guide_id", "target_gene_name", "protospacer", "scaffold", "pair_id", "is_non_targeting"]


def log(*a):
    print(*a, flush=True)


def symbol_of(label: str) -> str:
    s = re.sub(r"\s*\(rs\d+\)\s*$", "", str(label)).strip()
    return ALIASES.get(s, s)


def to_int_csr(X, what):
    X = sp.csr_matrix(X)
    if not np.issubdtype(X.data.dtype, np.integer):
        assert np.all(np.mod(X.data, 1) == 0), f"{what}: non-integer values"
        X = sp.csr_matrix((X.data.astype(np.int32), X.indices, X.indptr), shape=X.shape)
    X = X.astype(np.int32)
    X.sort_indices()
    return X


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cellranger-root", required=True)
    ap.add_argument("--guide-counts-root", required=True)
    ap.add_argument("--reference", required=True, help="tables/guide_reference_used.csv")
    ap.add_argument("--quant-summary", required=True, help="tables/guide_quantification_summary.csv")
    ap.add_argument("--out", required=True, help="combined h5ad path")
    ap.add_argument("--per-sample-dir", required=True)
    ap.add_argument("--tables", required=True)
    ap.add_argument("--design", required=True)
    args = ap.parse_args()
    out = Path(args.out)
    per_dir = Path(args.per_sample_dir)
    tables = Path(args.tables)
    per_dir.mkdir(parents=True, exist_ok=True)
    out.parent.mkdir(parents=True, exist_ok=True)

    ref = pd.read_csv(args.reference, dtype={"pair_id": str}, keep_default_na=False).set_index("guide_id")
    assert len(ref) == 560
    quant = pd.read_csv(args.quant_summary).set_index("well")
    log("guide reference:", ref.shape, "scaffold classes:", ref["scaffold"].value_counts().to_dict())

    parts, overlap_rows, checks = [], [], []
    for well, (cond, rep, glib) in WELLS.items():
        g = sc.read_10x_h5(Path(args.cellranger_root) / well / "filtered_feature_bc_matrix.h5", gex_only=False)
        g.var_names_make_unique()
        g.X = to_int_csr(g.X, f"{well} GEX")
        assert set(g.var["feature_types"].astype(str)) == {"Gene Expression"}
        mat, bare, gids = read_guide_counts(Path(args.guide_counts_root) / well, well)
        assert gids == list(ref.index), f"{well}: guide order differs from reference"
        gex_bare = [re.sub(r"-\d+$", "", b) for b in g.obs_names]
        assert bare == gex_bare, f"{well}: guide matrix rows are not the GEX barcodes in GEX order"
        assert mat.shape == (g.n_obs, 560), f"{well}: guide matrix shape {mat.shape} (transposed?)"
        mat = to_int_csr(mat, f"{well} guides")
        overlap_rows.append({"well": well, "guide_library": glib, "gex_cells": g.n_obs, "guide_matrix_cells": mat.shape[0],
                             "shared_barcodes": g.n_obs, "frac_gex_with_guide_row": 1.0,
                             "guide_rows_in_gex_order": True, "example_barcode": g.obs_names[0]})
        gvar = pd.DataFrame(index=pd.Index(gids, name=None))
        gvar["gene_ids"] = gids
        gvar["feature_types"] = "CRISPR Guide Capture"
        gvar["genome"] = ""
        gvar["guide_id"] = gids
        gvar["target_gene_name"] = ref["target_gene_name"].astype(str).to_numpy()
        gvar["target_raw"] = ref["target_raw"].astype(str).to_numpy()
        gvar["target_gene_symbol"] = [symbol_of(t) if not c else "ntc" for t, c in zip(ref["target_raw"], ref["is_non_targeting"].astype(str).str.lower() == "true")]
        gvar["protospacer"] = ref["protospacer"].astype(str).to_numpy()
        gvar["scaffold"] = ref["scaffold"].astype(str).to_numpy()
        gvar["pair_id"] = ref["pair_id"].astype(str).to_numpy()
        gvar["is_non_targeting"] = (ref["is_non_targeting"].astype(str).str.lower() == "true").to_numpy()
        xvar = g.var.copy()
        for c in ("guide_id", "target_gene_name", "target_raw", "target_gene_symbol", "protospacer", "scaffold", "pair_id"):
            xvar[c] = ""
        xvar["is_non_targeting"] = False
        xvar = xvar[list(gvar.columns)]
        var = pd.concat([xvar, gvar])
        X = sp.hstack([g.X, mat], format="csr", dtype=np.int32)
        obs = pd.DataFrame(index=[f"{well}_{b}" for b in g.obs_names])
        obs["cell_barcode"] = g.obs_names.to_numpy()
        obs["well"] = well
        obs["lane_id"] = well
        obs["sample"] = well
        obs["sample_id"] = well
        obs["guide_library"] = glib
        obs["condition"] = cond
        obs["replicate"] = rep
        obs["replicate_type"] = "unknown"
        obs["condition_status"] = "inferred"
        obs["cell_line"] = "unknown"
        a = ad.AnnData(X=X, obs=obs, var=var)
        a.layers["counts"] = a.X.copy()
        zero_guide = int((np.asarray(mat.sum(axis=1)).ravel() == 0).sum())
        checks.append({"well": well, "cellranger_cells": g.n_obs, "h5ad_cells": a.n_obs, "gex_features": g.n_vars, "guide_features": mat.shape[1],
                       "zero_guide_cells": zero_guide, "zero_guide_cells_expected": int(quant.loc[well, "cells_with_zero_guide_umis"]),
                       "guide_umis": int(mat.sum()), "guide_umis_expected": int(quant.loc[well, "total_guide_umis"])})
        assert zero_guide == int(quant.loc[well, "cells_with_zero_guide_umis"])
        parts.append(a)
        log(f"[{well}] {a.shape}; GEX {g.n_vars}, guides {mat.shape[1]}; guide UMIs {int(mat.sum()):,}; zero-guide cells {zero_guide}")

    var0 = parts[0].var
    for a in parts[1:]:
        assert a.var_names.equals(var0.index)
    combined = ad.concat(parts, axis=0, join="inner", merge="same", index_unique=None)
    for c in var0.columns:
        if c not in combined.var.columns:
            combined.var[c] = var0[c].to_numpy()
    combined.var = combined.var[list(var0.columns)]
    combined.X = to_int_csr(combined.X, "combined")
    combined.layers["counts"] = combined.X.copy()
    cat_cols = ["well", "lane_id", "sample", "sample_id", "guide_library", "condition", "replicate", "replicate_type", "condition_status", "cell_line"]
    for c in cat_cols:
        combined.obs[c] = pd.Categorical(combined.obs[c].astype(str))
    prov = {
        "built": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "slurm_job": os.environ.get("SLURM_JOB_ID", "n/a"),
        "gex_source": "Cell Ranger 9.0.1 filtered_feature_bc_matrix.h5 per well (extracted from <well>_cellranger_count_outs.tar; staged copy)",
        "guide_source": f"perturbseq_pipeline.guide_counting scaffold-aware UMI counts, exact + unambiguous 1-mismatch + +/-1 nt shift ({args.guide_counts_root})",
        "guide_design": args.design,
        "pair_map": "no explicit A-C pair map in the design workbook; var['pair_id'] is empty; pairing is provisional (same-target rule)",
        "labels": "condition/replicate inferred from well ids; replicate_type unknown; cell_line unknown; not confirmed by experimenters",
        "alias_mapping_target_gene_symbol": json.dumps(ALIASES) + "; '<GENE> (rsID)' -> '<GENE>' (informational only; target_gene_name is authoritative)",
    }
    combined.uns["provenance"] = prov
    assert combined.obs_names.is_unique and combined.var_names.is_unique

    if out.exists():
        backup = out.with_name(out.stem + "_prev_exact_only_counts" + out.suffix)
        if not backup.exists():
            log(f"existing {out.name} renamed to {backup.name} (previous iteration, exact-only guide counts)")
            out.rename(backup)
        else:
            out.unlink()
    combined.write_h5ad(out, compression="gzip")
    for a, well in zip(parts, WELLS):
        for c in cat_cols:
            a.obs[c] = pd.Categorical(a.obs[c].astype(str))
        a.uns["provenance"] = dict(prov, subset=f"well {well} only; identical construction to the combined object")
        a.write_h5ad(per_dir / f"Hanrui_fang_{well}.h5ad", compression="gzip")

    # ---- validation ---------------------------------------------------------------
    gmask = (combined.var["feature_types"] == "CRISPR Guide Capture").to_numpy()
    gvar = combined.var.loc[gmask]
    G = combined.X[:, gmask]
    ck = pd.DataFrame(checks)
    val = [
        ("path", str(out), ""),
        ("n_cells", combined.n_obs, "expected 163,991 (sum of Cell Ranger filtered cells)"),
        ("n_cells_matches_cellranger_sum", combined.n_obs == int(ck.cellranger_cells.sum()), ""),
        ("n_gene_expression_features", int((~gmask).sum()), "expected 38,606"),
        ("n_crispr_guide_capture_features", int(gmask.sum()), "expected 560"),
        ("X_dtype_integer", np.issubdtype(combined.X.dtype, np.integer), str(combined.X.dtype)),
        ("counts_layer_present_and_integer", "counts" in combined.layers and np.issubdtype(combined.layers["counts"].dtype, np.integer), ""),
        ("X_equals_counts_layer", (combined.X != combined.layers["counts"]).nnz == 0, ""),
        ("X_is_csr_sparse", sp.isspmatrix_csr(combined.X), ""),
        ("cell_ids_unique", combined.obs_names.is_unique, ""),
        ("cell_id_format", bool(all(re.fullmatch(r"HF01[12][AB]_[ACGT]{16}-\d+", i) for i in combined.obs_names[:1000])), "<well>_<barcode>"),
        ("four_wells_present", sorted(combined.obs["well"].unique().tolist()) == sorted(WELLS), json.dumps({k: int(v) for k, v in combined.obs["well"].value_counts().sort_index().items()})),
        ("cells_per_well_match_cellranger", bool(all(int((combined.obs["well"] == w).sum()) == int(ck.set_index("well").loc[w, "cellranger_cells"]) for w in WELLS)), ""),
        ("guide_matrix_rows_in_gex_order", True, "asserted per well before concatenation (bare barcodes identical, same order)"),
        ("no_transposition", combined.shape == (int(ck.cellranger_cells.sum()), int((~gmask).sum()) + 560), str(combined.shape)),
        ("guide_metadata_complete", bool(all((gvar[c].astype(str) != "").all() for c in ("guide_id", "target_gene_name", "protospacer", "scaffold"))), "guide_id/target_gene_name/protospacer/scaffold non-empty"),
        ("guide_var_columns", ",".join(GUIDE_VAR_REQUIRED), "all present: " + str(all(c in gvar.columns for c in GUIDE_VAR_REQUIRED))),
        ("pair_id_present", "pair_id" in gvar.columns, f"non-empty pair ids: {int((gvar['pair_id'].astype(str) != '').sum())} (0 expected: no explicit pair map)"),
        ("guide_scaffold_classes", json.dumps({k: int(v) for k, v in gvar["scaffold"].value_counts().items()}), ""),
        ("n_non_targeting_guides", int(gvar["is_non_targeting"].sum()), "expected 127"),
        ("zero_guide_cells_total", int((np.asarray(G.sum(axis=1)).ravel() == 0).sum()), "expected " + str(int(ck.zero_guide_cells_expected.sum())) + " (from guide_quantification_summary.csv)"),
        ("zero_guide_cells_preserved", int((np.asarray(G.sum(axis=1)).ravel() == 0).sum()) == int(ck.zero_guide_cells_expected.sum()), ""),
        ("guide_umis_total", int(G.sum()), "expected " + str(int(ck.guide_umis_expected.sum()))),
        ("guide_umis_match_counter", int(G.sum()) == int(ck.guide_umis_expected.sum()), ""),
        ("obs_columns", ",".join(combined.obs.columns), ""),
        ("var_columns", ",".join(combined.var.columns), ""),
        ("per_sample_h5ads", ",".join(str(per_dir / f"Hanrui_fang_{w}.h5ad") for w in WELLS), ""),
        ("file_size_gb", round(out.stat().st_size / 1e9, 2), ""),
    ]
    vdf = pd.DataFrame(val, columns=["field", "value", "note"])
    vdf.to_csv(tables / "combined_h5ad_validation.csv", index=False)
    pd.DataFrame(overlap_rows).to_csv(tables / "guide_gex_overlap_per_well.csv", index=False)
    ck.to_csv(tables / "combined_h5ad_per_well_checks.csv", index=False)
    log(vdf.to_string())
    bad = [f for f, v, _ in val if isinstance(v, (bool, np.bool_)) and not v]
    if bad:
        raise SystemExit(f"validation failed: {bad}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
