"""Build the combined Hanrui Fang H5AD (GEX + CRISPR Guide Capture features) for h5ad-mode runs.

* GEX: Cell Ranger ``filtered_feature_bc_matrix.h5`` per well (integer counts, gene ids + symbols).
* Guides: scaffold-aware UMI counts produced by ``perturbseq_pipeline.guide_counting`` from the four
  guide FASTQ libraries (SLURM job 20045135), aligned 1:1 to the GEX barcodes of the paired well
  (``outputs/hanrui_fang_inputs/guides/<well>/``). Guide metadata come from the design workbook
  (``design_out_v2.xlsx``) plus the empirically inferred scaffold class.
* Cells: ``<well>_<barcode>``; obs carries provisional labels (condition_status = inferred,
  replicate_type = unknown). ``layers["counts"]`` = raw counts; nothing normalised.

Run on a compute node.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc
import scipy.sparse as sp

INPUTS = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_inputs")
QC_OUT = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc")
REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
OUT = REPO / "work" / "Hanrui_fang" / "Hanrui_fang_combined.h5ad"
TABLES = REPO / "results" / "Hanrui_fang" / "tables"
DESIGN = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X/web_summaries/design_out_v2.xlsx")
WELLS = {"HF011A": ("HF011", "A", "HF011AF"), "HF011B": ("HF011", "B", "HF011BF"),
         "HF012A": ("HF012", "A", "HF012AF"), "HF012B": ("HF012", "B", "HF012BF")}
ALIASES = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3"}


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
    X.sort_indices()
    return X


def main() -> int:
    ref = pd.read_csv(TABLES / "guide_reference_used.csv")
    ref = ref.set_index("guide_id")
    log("guide reference:", ref.shape, "scaffold classes:", dict(ref["scaffold"].value_counts()))
    parts, overlap_rows = [], []
    for well, (cond, rep, glib) in WELLS.items():
        g = sc.read_10x_h5(INPUTS / "cellranger" / well / "filtered_feature_bc_matrix.h5", gex_only=False)
        g.var_names_make_unique()
        g.X = to_int_csr(g.X, f"{well} GEX")
        assert set(g.var["feature_types"].astype(str)) == {"Gene Expression"}
        gd = sc.read_10x_mtx(INPUTS / "guides" / well, var_names="gene_ids", cache=False, gex_only=False)
        gd.X = to_int_csr(gd.X, f"{well} guides")
        shared = g.obs_names.intersection(gd.obs_names)
        overlap_rows.append({"well": well, "guide_library": glib, "gex_cells": g.n_obs, "guide_matrix_cells": gd.n_obs,
                             "shared_barcodes": len(shared), "frac_gex_with_guide_row": len(shared) / g.n_obs,
                             "example_gex_barcode": g.obs_names[0], "example_guide_barcode": gd.obs_names[0]})
        assert len(shared) == g.n_obs == gd.n_obs, f"{well}: barcode overlap incomplete"
        gd = gd[g.obs_names].copy()  # identical order
        assert list(gd.var_names) == list(ref.index), f"{well}: guide order differs from reference"
        gvar = pd.DataFrame(index=gd.var_names)
        gvar["gene_ids"] = gd.var_names.to_numpy()
        gvar["feature_types"] = "CRISPR Guide Capture"
        gvar["genome"] = ""
        gvar["guide_id"] = gd.var_names.to_numpy()
        gvar["target_gene_name"] = ref["target_raw"].astype(str).to_numpy()
        gvar["target_gene_symbol"] = [symbol_of(t) for t in ref["target_raw"]]
        gvar["scaffold"] = ref["scaffold"].astype(str).to_numpy()
        gvar["is_non_targeting"] = ref["is_control"].astype(bool).to_numpy()
        gvar["protospacer"] = ref["protospacer"].astype(str).to_numpy()
        xvar = g.var.copy()
        for c in ("guide_id", "target_gene_name", "target_gene_symbol", "scaffold", "protospacer"):
            xvar[c] = ""
        xvar["is_non_targeting"] = False
        xvar = xvar[list(gvar.columns)]
        var = pd.concat([xvar, gvar])
        X = sp.hstack([g.X, gd.X], format="csr", dtype=np.int32)
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
        parts.append(a)
        log(f"[{well}] {a.shape}; GEX {g.n_vars}, guides {gd.n_vars}; guide UMIs {int(gd.X.sum()):,}; cells w/o guide UMIs {int((np.asarray(gd.X.sum(axis=1)).ravel()==0).sum())}")
    var0 = parts[0].var
    for a in parts[1:]:
        assert a.var_names.equals(var0.index)
    combined = ad.concat(parts, axis=0, join="inner", merge="same", index_unique=None)
    for c in var0.columns:
        if c not in combined.var.columns:
            combined.var[c] = var0[c].to_numpy()
    combined.var = combined.var[list(var0.columns)]
    combined.var_names_make_unique()
    combined.X = to_int_csr(combined.X, "combined")
    combined.layers["counts"] = combined.X.copy()
    for c in ("well", "lane_id", "sample", "sample_id", "guide_library", "condition", "replicate", "replicate_type", "condition_status", "cell_line"):
        combined.obs[c] = pd.Categorical(combined.obs[c].astype(str))
    combined.uns["provenance"] = {
        "built": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "gex_source": "Cell Ranger 9.0.1 filtered_feature_bc_matrix.h5 per well (extracted from <well>_cellranger_count_outs.tar)",
        "guide_source": "perturbseq_pipeline.guide_counting scaffold-aware exact-match UMI counts (SLURM 20045135), aligned to GEX barcodes",
        "guide_design": str(DESIGN),
        "labels": "condition/replicate inferred from well ids; replicate_type unknown; not confirmed by experimenters",
        "alias_mapping_target_gene_symbol": json.dumps(ALIASES) + "; '<GENE> (rsID)' -> '<GENE>'",
    }
    assert combined.obs_names.is_unique and combined.var_names.is_unique
    OUT.parent.mkdir(parents=True, exist_ok=True)
    combined.write_h5ad(OUT, compression="gzip")
    ft = combined.var["feature_types"].value_counts()
    val = {
        "path": str(OUT), "n_cells": int(combined.n_obs), "n_features": int(combined.n_vars),
        "n_gene_expression": int(ft.get("Gene Expression", 0)), "n_crispr_guide_capture": int(ft.get("CRISPR Guide Capture", 0)),
        "X_dtype": str(combined.X.dtype), "counts_layer": "counts" in combined.layers,
        "obs_columns": ",".join(combined.obs.columns), "var_columns": ",".join(combined.var.columns),
        "cells_per_well": json.dumps({k: int(v) for k, v in combined.obs["well"].value_counts().sort_index().items()}),
        "guide_scaffold_classes": json.dumps({k: int(v) for k, v in combined.var.loc[combined.var["feature_types"] == "CRISPR Guide Capture", "scaffold"].value_counts().items()}),
        "n_non_targeting_guides": int(combined.var["is_non_targeting"].sum()),
        "file_size_gb": round(OUT.stat().st_size / 1e9, 2),
    }
    pd.DataFrame([val]).T.reset_index().rename(columns={"index": "field", 0: "value"}).to_csv(TABLES / "combined_h5ad_validation.csv", index=False)
    pd.DataFrame(overlap_rows).to_csv(TABLES / "guide_gex_overlap_per_well.csv", index=False)
    log(json.dumps(val, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
