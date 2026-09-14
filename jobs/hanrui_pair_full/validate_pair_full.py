#!/usr/bin/env python
"""Step 4b (SLURM only): validation of the pair-guide full analysis (section 9 of the task)."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import yaml

from perturbseq_pipeline import dual_guides as dg

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
OUT = REPO / "results" / "Hanrui_Fang_pair_guide_full"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
RUNS = {"combined": OUT / "combined", **{w: OUT / "samples" / w for w in WELLS}}
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:400]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)


def read_elem(f, key):
    return ad.io.read_elem(f[key]) if hasattr(ad, "io") else ad.experimental.read_elem(f[key])


def main():
    cfgs, obs_all, counts = {}, {}, {}
    for k, d in RUNS.items():
        rc = d / "logs" / "resolved_config.yaml"
        cfg = yaml.safe_load(open(rc)) if rc.is_file() else None
        cfgs[k] = cfg
        ok = cfg is not None and (d / "report.html").is_file() and (d / cfg["output"]["h5ad_name"]).is_file()
        check(f"{k}: complete report + processed h5ad + resolved config", ok, str(d))
        if not ok:
            continue
        with h5py.File(d / cfg["output"]["h5ad_name"], "r") as f:
            o = read_elem(f, "obs"); obsm = list(f["obsm"].keys()); uns = list(f["uns"].keys())
        obs_all[k] = o
        check(f"{k}: processed h5ad = {cfg['output']['h5ad_name']} under the required directory", (d / "Hanrui_Fang_pair_guide_processed.h5ad").is_file())
        check(f"{k}: pair assignment fields + both scaffold-level assignments in obs", all(c in o.columns for c in (dg.OBS_PAIR_STATUS, dg.OBS_PAIR, dg.OBS_PAIR_ID, dg.OBS_PAIR_PRIMARY, "guide_A_id", "guide_C_id", "guide_A_target", "guide_C_target", "guide_A_slot_status", "guide_C_slot_status")))
        st = o[dg.OBS_PAIR_STATUS].astype(str)
        check(f"{k}: primary labels derive from pair statuses", ((st == dg.STATUS_PAIR_TARGETING) == (o["perturbation_class"].astype(str) == "targeting")).all() and ((st == dg.STATUS_PAIR_NTC) == (o["perturbation_class"].astype(str) == "non-targeting")).all(),
              st.value_counts().to_dict())
        check(f"{k}: single-guide result present as diagnostic columns only", dg.OBS_SG_CLASS in o.columns and (o[dg.OBS_MODE].astype(str) == "pair").all())
        check(f"{k}: sample-prefixed unique cell ids", o.index.is_unique and all(str(i).startswith(tuple(f"{w}_" for w in WELLS)) for i in o.index[:2000]), str(o.index[0]))
        check(f"{k}: no Harmony (batch_key null, no X_pca_harmony)", cfg["cluster"]["batch_key"] is None and "X_pca_harmony" not in obsm and "harmony" not in (d / "logs" / "run.log").read_text().lower(), obsm)
        check(f"{k}: PS-score / lochNESS / co-function / energy-distance disabled and absent", all(cfgs[k][m]["enabled"] is False for m in ("ps_score", "lochness", "modules", "distance", "distance_space")) and not any((d / "tables" / t).exists() for t in ("ps_score.csv", "lochness.csv", "cofunctional_modules.csv", "perturbation_distance.csv")))
        req = ["qc/cell_counts_before_after_per_lane.png", "qc/ecdf_total_counts_before_after.png", "qc/ecdf_n_genes_by_counts_before_after.png", "qc/ecdf_pct_counts_mt_before_after.png", "qc/genes_vs_umis_before_after.png", "qc/pct_mt_vs_genes_and_umis.png",
               "qc/qc_violin_before_filtering.png", "qc/qc_violin_after_filtering.png", "guides/pair_guide_umis_detection_by_scaffold.png", "guides/pair_assignment_status_counts_and_fractions.png", "guides/target_pair_cells_per_lane.png", "guides/single_guide_diagnostic_vs_pair_status.png",
               "clustering/pca_variance.png", "clustering/pca_by_sample_condition_pair_status.png", "clustering/umap_clusters.png", "clustering/umap_by_sample_condition_pair_status.png", "clustering/cluster_sizes.png", "clustering/cluster_composition_sample_pairstatus_class.png",
               "perturbation/pair_volcano_target_level.png", "perturbation/pair_volcano_pair_level.png", "perturbation/pair_waterfall_target_log2fc.png", "perturbation/pair_heatmap_log2fc_by_lane.png", "perturbation/pair_heatmap_neg_log10_fdr_by_lane.png", "perturbation/pair_hit_counts_per_lane.png", "perturbation/pair_ecdf_overview_top_targets.png", "perturbation/pair_level_expression_distributions.png"]
        missing = [f for f in req if not ((d / "figures" / f).is_file() and (d / "figures" / f).stat().st_size > 1000)]
        check(f"{k}: QC, pair-guide, PCA/UMAP/Leiden, ECDF and perturbation figures exist and are non-empty", not missing, missing or f"{len(req)} figures")
        bt = pd.read_csv(d / "tables" / "pair_perturbation_by_target.csv")
        prim = bt[(bt.control == "ntc") & (bt.assignment_stratum == "primary_pair_targeting")]
        pooled = prim[prim.lane_id == ("ALL" if k == "combined" else k)].dropna(subset=["log2fc"])
        ecdf_missing = [t for t in pooled.target_gene if not (d / "figures" / "perturbation" / "ecdf" / f"ecdf_{t}.png").is_file()]
        check(f"{k}: ECDF figure for every tested target ({len(pooled)})", not ecdf_missing, ecdf_missing[:5])
        check(f"{k}: raw FDR and neg_log10_fdr present and consistent", {"fdr_ks", "neg_log10_fdr"} <= set(bt.columns) and np.allclose(bt["neg_log10_fdr"].dropna(), -np.log10(np.maximum(bt.loc[bt["neg_log10_fdr"].notna(), "fdr_ks"], 1e-300))))
        check(f"{k}: pair-guide assignment is the primary perturbation label set", set(prim["assignment_stratum"]) == {"primary_pair_targeting"} and prim["n_ntc_pair_cells"].max() == int((st == dg.STATUS_PAIR_NTC).sum()))
        cc = pd.read_csv(d / "tables" / "cell_counts_before_after.csv").set_index("lane_id")
        counts[k] = cc
        pooled_key = "ALL" if k == "combined" else k
        check(f"{k}: pair-assignment counts reported per lane", (d / "tables" / "pair_assignment_per_lane.csv").is_file() and (d / "tables" / "pair_guide_qc_per_lane.csv").is_file())
        check(f"{k}: QC accounting consistent with the object", int(cc.loc[pooled_key, "final_cells_retained"]) == len(o))
        html = (d / "report.html").read_text()
        check(f"{k}: report distinguishes QC-pass / pair-assigned / pair-ambiguous / incomplete / unassigned", all(s in html for s in ("pair_targeting", "incomplete_pair", "ambiguous_scaffold", "no_guide", "Expression QC accounting")))
    if all(k in counts for k in RUNS):
        comb = counts["combined"]
        check("combined input cells == sum of the four sample inputs", int(comb.loc["ALL", "input_cells"]) == sum(int(counts[w].loc[w, "input_cells"]) for w in WELLS), f"{int(comb.loc['ALL', 'input_cells'])}")
        check("combined per-well retained cells == per-sample runs", all(int(comb.loc[w, "final_cells_retained"]) == int(counts[w].loc[w, "final_cells_retained"]) for w in WELLS))
        check("combined cells = 163,991 input / four wells present", int(comb.loc["ALL", "input_cells"]) == 163991 and set(obs_all["combined"]["lane_id"].astype(str)) == set(WELLS))
        pa_c = pd.read_csv(RUNS["combined"] / "tables" / "pair_assignment_per_lane.csv").set_index("lane_id")
        same = all(int(pa_c.loc[w, dg.STATUS_PAIR_TARGETING]) == int((obs_all[w][dg.OBS_PAIR_STATUS].astype(str) == dg.STATUS_PAIR_TARGETING).sum()) for w in WELLS)
        check("pair assignment per well identical between per-sample runs and the combined run", same)
    for f in ("report.html", "config_used.yaml", "run_manifest.json", "README.md", "audit/pair_guide_reference.csv", "audit/initial_audit.md", "tables/target_support_matrix_across_runs.csv"):
        check(f"root output {f} exists", (OUT / f).is_file())
    if (OUT / "report.html").is_file():
        html = (OUT / "report.html").read_text()
        secs = ["Dataset and sample structure", "guide-design audit", "Expression QC before and after", "Pair-guide quantification", "Per-sample analysis", "Combined analysis", "PCA, UMAP and Leiden", "ECDF and perturbation", "FDR and effect-size", "target support", "Single-guide diagnostic", "limitations", "Reproducibility"]
        check("root report has all 13 sections and links the per-run reports", all(s in html for s in secs) and all(f"{p}/report.html" in html for p in ["combined"] + [f"samples/{w}" for w in WELLS]), [s for s in secs if s not in html])
    check("output directory is results/Hanrui_Fang_pair_guide_full", OUT.name == "Hanrui_Fang_pair_guide_full" and OUT.is_dir())
    ledger = (OUT / "slurm" / "job_ids.txt").read_text() if (OUT / "slurm" / "job_ids.txt").is_file() else ""
    superseded = set(re.findall(r"\((\d{7,9}) (?:failed|cancelled)", ledger))
    errs = []
    for p in sorted((OUT / "slurm").glob("*.err")) + sorted((OUT / "slurm").glob("*.out")):
        t = p.read_text(errors="ignore")
        if ("Traceback" in t or "FAILED" in t) and not any(j in p.name for j in superseded) and not p.name.startswith("hpf_04"):
            errs.append(p.name)
    check(f"no SLURM log with unhandled errors (superseded attempts {sorted(superseded)} excluded; documented in slurm/job_ids.txt)", not errs, errs)
    df = pd.DataFrame(checks)
    (OUT / "tables").mkdir(exist_ok=True)
    df.to_csv(OUT / "tables" / "final_validation.csv", index=False)
    (OUT / "final_validation.txt").write_text("\n".join(f"[{r.status}] {r.check}: {r.detail}" for r in df.itertuples()) + f"\n\n{int((df.status == 'PASS').sum())}/{len(df)} checks passed\n")
    print(f"\n{int((df.status == 'PASS').sum())}/{len(df)} checks passed")
    return 0 if (df.status == "PASS").all() else 1


if __name__ == "__main__":
    sys.exit(main())
