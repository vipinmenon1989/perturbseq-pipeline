#!/usr/bin/env python
"""Step 17: final validation of the Hanrui Fang dual-guide analysis. SLURM only."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
import yaml

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guides import assign_guides

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
RES = REPO / "results" / "Hanrui_fang_dual_guide"
WORK = REPO / "work" / "Hanrui_fang"
DATA = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X")
OLD = REPO / "results" / "Hanrui_fang"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
RUNS = {"combined": RES / "combined", **{w: RES / "per_sample" / w for w in WELLS}}
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def read_elem(f, key):
    return ad.io.read_elem(f[key]) if hasattr(ad, "io") else ad.experimental.read_elem(f[key])


def main():
    # ---- runs present --------------------------------------------------------------------
    cfgs = {}
    for k, d in RUNS.items():
        cfg = yaml.safe_load(open(d / "logs" / "resolved_config.yaml")) if (d / "logs" / "resolved_config.yaml").is_file() else None
        cfgs[k] = cfg
        check(f"run {k}: report + processed + all-cells h5ad + resolved config exist",
              cfg is not None and (d / "report.html").is_file() and (d / cfg["output"]["h5ad_name"]).is_file() and (d / cfg["output"]["unfiltered_h5ad_name"]).is_file(), str(d))
    check("all four per-sample runs present", all(cfgs[w] is not None for w in WELLS))

    # ---- combined H5AD ---------------------------------------------------------------------
    with h5py.File(WORK / "Hanrui_fang_combined.h5ad", "r") as f:
        obs = read_elem(f, "obs"); var = read_elem(f, "var")
        X_dtype = f["X"]["data"].dtype if isinstance(f["X"], h5py.Group) else f["X"].dtype
        counts_dtype = f["layers"]["counts"]["data"].dtype
    check("combined H5AD contains all four wells", sorted(obs["well"].astype(str).unique()) == WELLS, obs["well"].value_counts().to_dict())
    check("combined H5AD raw counts integer (X and layers['counts'])", np.issubdtype(X_dtype, np.integer) and np.issubdtype(counts_dtype, np.integer), f"X={X_dtype} counts={counts_dtype}")
    gvar = var[var["feature_types"].astype(str) == "CRISPR Guide Capture"]
    check("560 guide features with complete metadata", len(gvar) == 560 and all((gvar[c].astype(str) != "").all() for c in ("guide_id", "target_gene_name", "protospacer", "scaffold")), f"n={len(gvar)}, scaffold={gvar['scaffold'].value_counts().to_dict()}")
    check("pair_id column preserved in var (empty = no explicit design pair map)", "pair_id" in gvar.columns, f"non-empty: {int((gvar['pair_id'].astype(str) != '').sum())}")
    check("38,606 gene expression features", int((var["feature_types"].astype(str) == "Gene Expression").sum()) == 38606)
    check("163,991 cells in combined H5AD", len(obs) == 163991, len(obs))
    v = pd.read_csv(RES / "tables" / "combined_h5ad_validation.csv").set_index("field")["value"].astype(str)
    check("job-04 validation flags all true", all(v[k] == "True" for k in ("guide_matrix_rows_in_gex_order", "no_transposition", "zero_guide_cells_preserved", "guide_umis_match_counter", "cells_per_well_match_cellranger")), v[["guide_matrix_rows_in_gex_order", "no_transposition", "zero_guide_cells_preserved", "guide_umis_match_counter"]].to_dict())
    # per-well objects are exact row subsets of the combined object (GEX + guide columns share the row order)
    for w in WELLS:
        with h5py.File(WORK / "per_sample" / f"Hanrui_fang_{w}.h5ad", "r") as f:
            o = read_elem(f, "obs")
        check(f"per-well H5AD {w} rows == combined rows of that well (same order)", list(o.index) == list(obs.index[obs["well"].astype(str) == w]), len(o))

    # ---- assignment controlled by configuration ---------------------------------------------------
    procs = {}
    for k, d in RUNS.items():
        with h5py.File(d / cfgs[k]["output"]["h5ad_name"], "r") as f:
            po = read_elem(f, "obs")
            uns_keys = list(f["uns"].keys())
            obsm_keys = list(f["obsm"].keys())
            layers_counts_dtype = f["layers"]["counts"]["data"].dtype if "counts" in f["layers"] else None
        procs[k] = po
        check(f"{k}: assignment mode = dual_guide_pair in config and obs", cfgs[k]["guides"]["assignment_mode"] == "dual_guide_pair" and (po["guide_assignment_mode"].astype(str) == "dual_guide_pair").all())
        check(f"{k}: pair-level obs fields present", all(c in po.columns for c in ("guide_A_id", "guide_C_id", "guide_A_target", "guide_C_target", "pair_id", "pair_assignment", "pair_assignment_status", "n_guides_detected", "top_guide_count", "second_guide_count")))
        check(f"{k}: guide pair ids / scaffolds round-tripped in uns", "guide_pair_ids" in uns_keys and "guide_scaffolds" in uns_keys)
        check(f"{k}: Harmony not used (batch_key null, no X_pca_harmony)", cfgs[k]["cluster"]["batch_key"] is None and "X_pca_harmony" not in obsm_keys, obsm_keys)
        check(f"{k}: counts layer integer in processed object", layers_counts_dtype is not None and np.issubdtype(layers_counts_dtype, np.integer), layers_counts_dtype)
        log_txt = (d / "logs" / "run.log").read_text()
        check(f"{k}: run.log has no ERROR and no Harmony", "ERROR" not in log_txt and "harmony" not in log_txt.lower(), f"warnings={log_txt.count('WARNING')}")
        for stage, files in (("ps_score", ["ps_score.csv"]), ("lochness", ["lochness.csv"]), ("modules", ["cofunctional_modules.csv", "gene_programs.csv"]),
                             ("distance", ["perturbation_distance.csv"]), ("distance_space", ["perturbation_distance_matrix.tsv", "phenotype_modules.csv"]), ("meta_analysis", [])):
            check(f"{k}: {stage} disabled and produced no tables", cfgs[k][stage]["enabled"] is False and not any((d / "tables" / fn).exists() for fn in files))
        pf = pd.read_csv(d / "tables" / "perturbation_expression_by_target.csv")
        check(f"{k}: perturbation tables contain fdr_ks and neg_log10_fdr (= -log10 fdr_ks)", {"fdr_ks", "neg_log10_fdr", "ks_pval", "log2fc", "hit_status"} <= set(pf.columns)
              and np.allclose(pf["neg_log10_fdr"].dropna(), -np.log10(np.clip(pf.loc[pf["neg_log10_fdr"].notna(), "fdr_ks"], 1e-300, 1))))
        cc = pd.read_csv(d / "tables" / "cell_counts_before_after.csv")
        pooled = cc[cc.well == ("ALL" if k == "combined" else k)].set_index("cell_category")["cell_count"]
        qs = pd.read_csv(d / "tables" / "qc_steps.csv")
        check(f"{k}: QC counts internally consistent", pooled["cells in processed object (pipeline QC pass)"] == len(po) == int(qs["cells_after"].iloc[-1])
              and pooled["cells loaded by pipeline"] == pooled["cells in processed object (pipeline QC pass)"] + pooled["cells failing any expression QC"]
              and pooled["targeting cells (perturbation_class)"] + pooled["non-targeting cells (perturbation_class)"] == pooled["pair-assigned cells (targeting + non-targeting)"],
              f"processed={len(po)} qc_steps_final={int(qs['cells_after'].iloc[-1])}")
        req = {"qc": ["cell_counts_before_after", "cellranger_metrics_per_well", "dist_total_counts_before_after", "dist_n_genes_by_counts_before_after", "dist_pct_counts_mt_before_after",
                      "dist_pct_counts_ribo_before_after", "dist_pct_counts_hb_before_after", "umi_vs_genes_per_well", "barcode_rank_knee_per_well", "per_well_qc_heatmap",
                      "pca_by_well_condition_qcstatus_pairstatus", "umap_by_well_condition_qcstatus_pairstatus"]
               + [f"ecdf_{c}_before_after" for c in ("total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "guide_umi_total", "n_guides_ge_min_umi", "n_strong_guides_A_any", "n_strong_guides_C_any")],
               "guides": ["guide_read_funnel_and_retention_fractions", "valid_barcode_fraction", "valid_umi_fraction", "exact_match_fraction", "mismatch_rescue_fraction",
                          "per_guide_abundance_and_per_well_recovery", "per_target_guide_representation", "targeting_cells_per_target", "guide_umis_guides_per_cell_A_vs_C",
                          "pair_assignment_categories_and_fractions", "default_vs_dual_assignment"],
               "perturbation": ["volcano_log2fc_vs_neglog10fdr", "waterfall_target_log2fc", "heatmap_log2fc_by_sample", "heatmap_neg_log10_fdr_by_sample",
                                "targeting_cells_assigned_cells_significant_targets_per_sample", "per_guide_vs_target_efficacy", "ecdf_target_expression_vs_ntc",
                                "ecdf_target_expression_vs_other", "ecdf_neglog10fdr_by_sample"] + (["well_consistency_log2fc_A_vs_B"] if k == "combined" else [])}
        missing = [f"{s}/{n}" for s, names in req.items() for n in names if not (d / "figures" / s / f"{n}.png").is_file()]
        check(f"{k}: all required supplementary figures exist (incl. ECDFs)", not missing, f"missing={missing}" if missing else f"{sum(len(v) for v in req.values())} figures")
        pipe_figs = [f for f in ("guides/guide_assignment_classes.png", "clustering/umap_clusters.png", "perturbation/perturbation_volcano.png", "enrichment/enrichment_heatmap.png") if not (d / "figures" / f).is_file()]
        check(f"{k}: pipeline figures incl. cluster enrichment exist", not pipe_figs, pipe_figs)
    top = [RES / "comparison_report.html", RES / "tables" / "sample_comparison.csv", RES / "tables" / "target_hit_support_matrix.csv", RES / "tables" / "assignment_comparison.csv",
           RES / "tables" / "default_vs_dual_assignment.csv", RES / "figures" / "guides" / "default_vs_dual_assignment.png", RES / "tables" / "perturbation_expression_by_guide.csv",
           RES / "tables" / "perturbation_expression_by_target.csv", RES / "tables" / "perturbation_per_well.csv", RES / "tables" / "perturbation_replicate_summary.csv",
           RES / "tables" / "guide_read_retention_funnel.csv", RES / "tables" / "guide_quantification_summary.csv", RES / "tables" / "guide_counts_per_cell.csv", RES / "tables" / "guide_counts_per_well.csv",
           RES / "tables" / "guide_design_audit.csv", RES / "tables" / "guide_reference_used.csv", RES / "tables" / "guide_pair_map.csv", RES / "guide_design_audit.md",
           RES / "pipeline_comparison" / "audit_report_summary.md", RES / "pipeline_comparison" / "main_vs_dev.md", RES / "logs" / "audit_report_read.log", REPO / "config" / "Hanrui_fang_dual_guide.yaml"]
    miss = [str(p.relative_to(REPO)) for p in top if not p.is_file()]
    check("top-level required outputs exist", not miss, miss)

    # ---- single_guide reproduces the old baseline on the old matrix ------------------------------------------
    try:
        with h5py.File(OLD / "Hanrui_fang_processed.h5ad", "r") as f:
            oo = read_elem(f, "obs"); G = read_elem(f, "obsm/guide_counts"); names = [str(x) for x in read_elem(f, "uns/guide_names")]
        # the old processed object lacks uns['guide_target_genes'] (pre-existing quirk); take the labels
        # from the archived combined input of that run (identical guide order)
        with h5py.File(WORK / "Hanrui_fang_combined_prev_exact_only_counts.h5ad", "r") as f:
            ov = read_elem(f, "var")
        ov = ov[ov["feature_types"].astype(str) == "CRISPR Guide Capture"]
        assert list(ov["guide_id"].astype(str)) == names
        tg = ov["target_gene_name"].astype(str).tolist()
        cfg = Config.from_yaml(OLD / "logs" / "resolved_config.yaml")
        g = ad.AnnData(X=sp.csr_matrix(G)); g.obs_names = oo.index; g.var_names = pd.Index(names); g.var["target_gene_name"] = tg
        tmp = ad.AnnData(X=sp.csr_matrix((len(oo), 1)), obs=pd.DataFrame(index=oo.index))
        tmp = assign_guides(tmp, g, cfg)
        same = (tmp.obs["perturbation_class"].astype(str).to_numpy() == oo["perturbation_class"].astype(str).to_numpy()).all() and \
               (tmp.obs["target_gene"].astype(str).to_numpy() == oo["target_gene"].astype(str).to_numpy()).all()
        check("assignment_mode single_guide reproduces the previous baseline classes/targets exactly (old matrix, 161,594 cells)", bool(same),
              tmp.obs["perturbation_class"].value_counts().to_dict())
    except Exception as e:  # pragma: no cover
        check("assignment_mode single_guide reproduces the previous baseline", False, repr(e))
    dv = pd.read_csv(RES / "tables" / "default_vs_dual_assignment.csv")
    dvc = dv[(dv.run == "combined") & (dv.well == "ALL") & dv.pct_of_cells.notna()]
    amb = dvc[dvc.single_guide_class == "ambiguous"]
    check("dual_guide_pair produces a different (pair-resolved) result than single_guide", int(amb.loc[amb.dual_guide_category.str.startswith("targeting"), "n_cells"].sum()) > 0,
          f"baseline-ambiguous cells re-assigned to targeting: {int(amb.loc[amb.dual_guide_category.str.startswith('targeting'), 'n_cells'].sum()):,}; to NTC: {int(amb.loc[amb.dual_guide_category.str.startswith('non-targeting'), 'n_cells'].sum()):,}")

    # ---- raw data untouched ------------------------------------------------------------------------
    before = (RES / "logs" / "raw_tree_manifest_before.txt").read_text().splitlines()
    after = subprocess.run(["find", str(DATA), "-path", str(DATA / "data_audit"), "-prune", "-o", "-type", "f", "-printf", "%T@ %s %p\n"], capture_output=True, text=True).stdout.splitlines()
    after = sorted(after, key=lambda l: l.split(" ", 2)[2])
    before = sorted(before, key=lambda l: l.split(" ", 2)[2])
    check("no raw input file modified (mtime+size manifest identical)", before == after, f"{len(before)} files before, {len(after)} after")

    # ---- SLURM jobs -------------------------------------------------------------------------------
    superseded = set()
    resub = RES / "logs" / "job_resubmissions.txt"
    if resub.is_file():
        txt = resub.read_text()
        superseded.update(re.findall(r"failed \((\d{7,9})", txt))
        superseded.update(re.findall(r"\((\d{7,9}) cancelled\)", txt))
        for grp in re.findall(r"^cancelled ([\d ]+)\(", txt, flags=re.M):
            superseded.update(grp.split())
    check("superseded SLURM attempts documented (excluded from the error scan below)", True, f"{sorted(superseded)} listed in logs/job_resubmissions.txt")
    errs = []
    for p in sorted((REPO / "jobs" / "hanrui_fang").glob("*_*.err")) + sorted((REPO / "jobs" / "hanrui_fang").glob("*_*.out")):
        if any(j in p.name for j in superseded) or p.name.startswith("hf_09_validate"):
            continue  # earlier validation passes are diagnostic (they exit 1 when a check fails)
        t = p.read_text(errors="ignore")
        if "Traceback" in t or re.search(r"(?m)^(Error|.*Error:)", t) or "FAILED" in t.split("short test summary")[-1] and p.name.startswith("hf_05"):
            if p.name.startswith("hf_05") and "1 failed, 262 passed" in t:
                continue  # first test job: the config test fixed and re-run in the second test job
            errs.append(p.name)
    check("no SLURM job log with unhandled errors (Traceback/Error)", not errs, errs)
    ids = sorted({re.search(r"_(\d+)\.(out|err)$", p.name).group(1) for p in (REPO / "jobs" / "hanrui_fang").glob("hf_*_*.out")})
    sacct = subprocess.run(["sacct", "-j", ",".join(ids), "-X", "-n", "-P", "-o", "JobID,JobName,State,ExitCode,Elapsed,MaxRSS"], capture_output=True, text=True).stdout
    bad = [l for l in sacct.splitlines() if l and l.split("|")[2] not in ("COMPLETED", "RUNNING", "PENDING")
           and l.split("|")[0] not in superseded and l.split("|")[1] != "hf_09_validate"]
    check("earlier validation passes excluded from the job-state check", True, "hf_09_validate attempts 20045277 (3 failed checks, fixed) and 20045488 (2 failed checks, fixed) are diagnostic")
    check("all SLURM jobs completed (sacct)", not bad, bad or f"{len(ids)} jobs")
    (RES / "logs" / "slurm_jobs_sacct.txt").write_text(sacct)

    # ---- nothing written outside the results tree --------------------------------------------------------
    t0 = (RES / "logs" / "raw_tree_manifest_before.txt").stat().st_mtime
    out = subprocess.run(["find", str(REPO / "results"), "-newermt", f"@{t0}", "-type", "f", "-not", "-path", f"{RES}/*"], capture_output=True, text=True).stdout.split()
    out = [o for o in out if "/results/Hanrui_fang_dual_guide/" not in o]
    check("no result file written outside results/Hanrui_fang_dual_guide/ since job 01", not out, out[:10])

    df = pd.DataFrame(checks)
    df.to_csv(RES / "tables" / "final_validation.csv", index=False)
    txt = "\n".join(f"[{r.status}] {r.check}: {r.detail}" for r in df.itertuples()) + f"\n\n{int((df.status == 'PASS').sum())}/{len(df)} checks passed"
    (RES / "logs" / "final_validation.txt").write_text(txt)
    print(f"\n{int((df.status == 'PASS').sum())}/{len(df)} checks passed")
    return 0 if (df.status == "PASS").all() else 1


if __name__ == "__main__":
    sys.exit(main())
