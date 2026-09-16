#!/usr/bin/env python
"""Iteration 2, step 5b (SLURM only): validation checklist (task section 15) for results/Hanrui_Fang_pair_guide_full_2."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import yaml

from perturbseq_pipeline import dual_guides as dg

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
OUT = REPO / "results" / "Hanrui_Fang_pair_guide_full_2"
PREV = REPO / "results" / "Hanrui_Fang_pair_guide_full"
DATA = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X")
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
RUNS = {"combined": OUT / "combined", **{w: OUT / "samples" / w for w in WELLS}}
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:500]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {str(detail)[:300]}", flush=True)


def read_elem(f, key):
    return ad.io.read_elem(f[key]) if hasattr(ad, "io") else ad.experimental.read_elem(f[key])


def main():
    # ---- 1. new experimental files used ---------------------------------------------------------
    ref = pd.read_csv(OUT / "audit" / "pair_guide_reference.csv", dtype=str, keep_default_na=False)
    check("1 pair reference derives from the NEW documents (oligo-pool workbook + scaffold docx recorded as sources)",
          ref["source_file"].str.contains("20250822_OligoPool_TwistAddG.xlsx").any() and (OUT / "audit" / "scaffold_audit.csv").is_file() and "Scaffold_seq.docx" in (OUT / "audit" / "scaffold_audit.csv").read_text(),
          f"{int(ref['source_file'].str.contains('OligoPool').sum())} features cite the oligo workbook")
    ev = pd.read_csv(OUT / "audit" / "evidence_matrix.csv", dtype=str, keep_default_na=False)
    check("1b evidence matrix cites both new documents", ev["source_file"].str.contains("OligoPool").any() and ev["source_file"].str.contains("Scaffold_seq.docx").any(), f"{len(ev)} facts")
    cmap = pd.read_csv(OUT / "audit" / "pair_mapping_audit.csv", dtype=str, keep_default_na=False)
    check("1c construct map has 236 constructs of three designed types", len(cmap) == 236 and set(cmap["construct_type"]) == {"dual_targeting_same_target", "ntc_pair", "targeting_plus_ntc"}, cmap["construct_type"].value_counts().to_dict())
    designed = ref[ref["designed_slot"].str.lower() == "true"]
    check("1d explicit pair ids for every designed slot; multi-construct membership encoded", (designed["pair_id"] != "").all() and (designed["pair_id"].str.contains(";")).sum() >= 42, f"{len(designed)} designed slots, {int(designed['pair_id'].str.contains(';').sum())} with >1 construct")
    # ---- 2. old result untouched -------------------------------------------------------------------
    prev_manifest = json.load(open(PREV / "run_manifest.json")) if (PREV / "run_manifest.json").is_file() else {}
    prev_mtimes = sorted(p.stat().st_mtime for p in [PREV / "report.html", PREV / "run_manifest.json", PREV / "combined" / "report.html"] if p.is_file())
    import datetime as _dt
    check("2 previous result directory not overwritten (its key files predate this iteration)", bool(prev_mtimes) and _dt.datetime.fromtimestamp(max(prev_mtimes)) < _dt.datetime(2026, 9, 15, 12, 0), f"latest previous mtime {_dt.datetime.fromtimestamp(max(prev_mtimes)) if prev_mtimes else 'n/a'}; generated {prev_manifest.get('generated')}")
    check("3 new output inside results/Hanrui_Fang_pair_guide_full_2", OUT.name == "Hanrui_Fang_pair_guide_full_2" and OUT.is_dir())
    # ---- 4/5. SLURM + conda ------------------------------------------------------------------------
    outs = sorted(OUT.glob("slurm/*.out"))
    hosts = [re.search(r"HOST: (\S+)", p.read_text(errors="ignore")) for p in outs]
    envs = [("ENV: perturbseq-pipeline" in p.read_text(errors="ignore")) or ("conda activate perturbseq-pipeline" in p.read_text(errors="ignore")) for p in outs]
    check("4 every step ran under SLURM (job logs with HOST lines)", len(outs) >= 5 and all(h is not None for h in hosts), [h.group(1).split(".")[0] if h else None for h in hosts])
    check("5 conda env perturbseq-pipeline activated in every SLURM step", all(envs), f"{sum(envs)}/{len(envs)}")
    prod = [p for p in outs if p.name.startswith("slurm_")]
    check("4b production runs used the requested h200 allocation", any("ihc-h200" in (p.read_text(errors="ignore")) for p in prod), [p.name for p in prod])
    # ---- per-run checks ----------------------------------------------------------------------------
    cfgs, obs_all, counts, pa_tabs = {}, {}, {}, {}
    for k, d in RUNS.items():
        rc = d / "logs" / "resolved_config.yaml"
        cfg = yaml.safe_load(open(rc)) if rc.is_file() else None
        cfgs[k] = cfg
        ok = cfg is not None and (d / "report.html").is_file() and (d / "report.md").is_file() and (d / cfg["output"]["h5ad_name"]).is_file()
        check(f"6/7 {k}: complete HTML + Markdown report, processed h5ad, resolved config", ok, str(d))
        if not ok:
            continue
        with h5py.File(d / cfg["output"]["h5ad_name"], "r") as f:
            o = read_elem(f, "obs"); obsm = list(f["obsm"].keys()); uns_ga = read_elem(f, "uns/guide_assignment") if "guide_assignment" in f["uns"] else {}
        obs_all[k] = o
        st = o[dg.OBS_PAIR_STATUS].astype(str)
        kl = o["perturbation_class"].astype(str)
        check(f"14 {k}: ambiguous / unresolved cells are labelled and NOT in the targeting or NTC classes",
              (kl[st.isin([dg.STATUS_UNRESOLVED, dg.STATUS_DUAL_TARGET, dg.STATUS_INCOMPLETE, "ambiguous_scaffold_A", "ambiguous_scaffold_C", "ambiguous_scaffold_A_and_C", dg.STATUS_UNKNOWN_GUIDE, dg.STATUS_BELOW_MIN_UMI])] == "ambiguous").all()
              and (kl[st == dg.STATUS_NO_GUIDE] == "unassigned").all() and dg.OBS_PAIR_DETAIL in o.columns and (o[dg.OBS_PAIR_DETAIL].astype(str) != "").all(), st.value_counts().to_dict())
        check(f"15 {k}: primary labels = experimentally supported constructs (explicit ids; targeting = designed dual or _S1; NTC = designed NTC pairs)",
              bool(uns_ga.get("pair_reference_explicit_ids", False)) and ((kl == "targeting") == st.isin([dg.STATUS_PAIR_TARGETING, dg.STATUS_PAIR_TARGET_NTC])).all() and ((kl == "non-targeting") == (st == dg.STATUS_PAIR_NTC)).all()
              and (o.loc[kl.isin(["targeting", "non-targeting"]), dg.OBS_PAIR_ID].astype(str).str.contains(r"^(?!.*\|).+$")).all(), f"construct types: {o[dg.OBS_CONSTRUCT_TYPE].astype(str).value_counts().to_dict() if dg.OBS_CONSTRUCT_TYPE in o.columns else 'n/a'}")
        check(f"16 {k}: single-guide rule present as diagnostic only", dg.OBS_SG_CLASS in o.columns and (o[dg.OBS_MODE].astype(str) == "pair").all() and (o[dg.OBS_PAIR_PROVISIONAL].astype(bool) == False).all())
        check(f"20 {k}: sample-prefixed unique cell ids", o.index.is_unique and all(str(i).startswith(tuple(f"{w}_" for w in WELLS)) for i in o.index[:5000]), str(o.index[0]))
        check(f"17 {k}: Harmony disabled (batch_key null, no X_pca_harmony)", cfg["cluster"]["batch_key"] is None and "X_pca_harmony" not in obsm and "harmony" not in (d / "logs" / "run.log").read_text(errors="ignore").lower(), obsm)
        check(f"18 {k}: PS-score / lochNESS / co-function / energy-distance disabled and absent", all(cfg[m]["enabled"] is False for m in ("ps_score", "lochness", "modules", "distance", "distance_space")) and not any((d / "tables" / t).exists() for t in ("ps_score.csv", "lochness.csv", "cofunctional_modules.csv", "perturbation_distance.csv")))
        req = ["qc/cell_counts_before_after_per_lane.png", "qc/ecdf_total_counts_before_after.png", "qc/ecdf_n_genes_by_counts_before_after.png", "qc/ecdf_pct_counts_mt_before_after.png", "qc/genes_vs_umis_before_after.png", "qc/pct_mt_vs_genes_and_umis.png",
               "qc/qc_violin_before_filtering.png", "qc/qc_violin_after_filtering.png", "guides/pair_guide_umis_detection_by_scaffold.png", "guides/pair_assignment_status_counts_and_fractions.png", "guides/target_pair_cells_per_lane.png", "guides/single_guide_diagnostic_vs_pair_status.png",
               "guides/strong_guides_per_scaffold.png", "guides/guide_umi_fraction_by_feature_role.png", "guides/guide_feature_representation.png",
               "clustering/pca_variance.png", "clustering/pca_by_sample_condition_pair_status.png", "clustering/umap_clusters.png", "clustering/umap_by_sample_condition_pair_status.png", "clustering/umap_assignment_class.png", "clustering/cluster_sizes.png", "clustering/cluster_composition_sample_pairstatus_class.png",
               "perturbation/pair_volcano_target_level.png", "perturbation/pair_volcano_pair_level.png", "perturbation/pair_waterfall_target_log2fc.png", "perturbation/pair_heatmap_log2fc_by_lane.png", "perturbation/pair_heatmap_neg_log10_fdr_by_lane.png", "perturbation/pair_hit_counts_per_lane.png", "perturbation/pair_ecdf_overview_top_targets.png", "perturbation/pair_level_expression_distributions.png"]
        missing = [f for f in req if not ((d / "figures" / f).is_file() and (d / "figures" / f).stat().st_size > 1000)]
        check(f"8-12 {k}: QC before/after, pair-guide QC, PCA/UMAP/Leiden, ECDF, volcano and heatmap figures exist and are non-empty", not missing, missing or f"{len(req)} figures")
        bt = pd.read_csv(d / "tables" / "pair_perturbation_by_target.csv")
        prim = bt[(bt.control == "ntc") & (bt.assignment_stratum == "primary_pair_targeting")]
        pooled_key = "ALL" if k == "combined" else k
        pooled = prim[prim.lane_id == pooled_key].dropna(subset=["log2fc"])
        slug = lambda t: re.sub(r"[^A-Za-z0-9._-]+", "_", f"ecdf_{t}").strip("_")
        ecdf_missing = [t for t in pooled.target_gene if not (d / "figures" / "perturbation" / "ecdf" / f"{slug(t)}.png").is_file()]
        check(f"11 {k}: ECDF figure for every tested target ({len(pooled)})", not ecdf_missing, ecdf_missing[:5])
        check(f"13 {k}: raw FDR and neg_log10_fdr present and consistent", {"fdr_ks", "neg_log10_fdr"} <= set(bt.columns) and np.allclose(bt["neg_log10_fdr"].dropna(), -np.log10(np.maximum(bt.loc[bt["neg_log10_fdr"].notna(), "fdr_ks"], 1e-300))))
        check(f"15b {k}: dual-only and single-guide strata reported alongside the primary stratum", {"dual_guide_constructs_only", "single_guide_plus_ntc_constructs_only", "sensitivity_incl_same_target_not_designed"} <= set(bt.assignment_stratum), sorted(set(bt.assignment_stratum)))
        check(f"14b {k}: primary NTC control = designed NTC pairs only", prim["n_ntc_pair_cells"].max() == int((st == dg.STATUS_PAIR_NTC).sum()))
        cc = pd.read_csv(d / "tables" / "cell_counts_before_after.csv").set_index("lane_id")
        counts[k] = cc
        pa_tabs[k] = pd.read_csv(d / "tables" / "pair_assignment_per_lane.csv").set_index("lane_id")
        check(f"19 {k}: QC accounting consistent with the object", int(cc.loc[pooled_key, "final_cells_retained"]) == len(o))
        for t in ("pair_resolution_detail_per_lane", "construct_type_per_lane", "guide_feature_representation", "off_design_umi_fraction_per_lane", "strong_guides_per_scaffold_per_lane", "construct_cells_per_lane", "target_support_matrix", "pair_perturbation_by_pair"):
            check(f"9 {k}: table {t}", (d / "tables" / f"{t}.csv").is_file())
        md = (d / "report.md").read_text()
        check(f"22 {k}: Markdown report has QC, pair-guide, ambiguity, clustering, ECDF, perturbation sections", all(s in md for s in ("Expression QC before filtering", "Pair-guide QC", "Pair ambiguity and unresolved", "PCA, UMAP and Leiden", "ECDF analysis", "Perturbation-expression analysis")))
    # ---- cross-run consistency -----------------------------------------------------------------
    if all(k in counts for k in RUNS):
        comb = counts["combined"]
        check("19/21 combined input cells == sum of the four per-sample inputs", int(comb.loc["ALL", "input_cells"]) == sum(int(counts[w].loc[w, "input_cells"]) for w in WELLS), int(comb.loc["ALL", "input_cells"]))
        check("21 combined per-well retained cells == per-sample runs", all(int(comb.loc[w, "final_cells_retained"]) == int(counts[w].loc[w, "final_cells_retained"]) for w in WELLS))
        check("19 four wells present in the combined object", set(obs_all["combined"]["lane_id"].astype(str)) == set(WELLS))
        pa_c = pa_tabs["combined"]
        same = all(int(pa_c.loc[w, s]) == int((obs_all[w][dg.OBS_PAIR_STATUS].astype(str) == s).sum()) for w in WELLS for s in (dg.STATUS_PAIR_TARGETING, dg.STATUS_PAIR_TARGET_NTC, dg.STATUS_PAIR_NTC, dg.STATUS_UNRESOLVED) if s in pa_c.columns)
        check("21 pair statuses per well identical between per-sample and combined runs", same)
        check("20 combined barcodes unique and equal to the union of per-sample cells", obs_all["combined"].index.is_unique and set(obs_all["combined"].index) == set().union(*[set(obs_all[w].index) for w in WELLS]))
        check("24 combined object retains sample / condition / replicate / pair metadata", all(c in obs_all["combined"].columns for c in ("lane_id", "sample", "condition", "replicate", "condition_status", dg.OBS_PAIR_STATUS, dg.OBS_PAIR_ID, dg.OBS_CONSTRUCT_TYPE)), [c for c in ("sample", "condition", "replicate", "condition_status") if c not in obs_all["combined"].columns])
    # ---- root outputs ---------------------------------------------------------------------------
    for f in ("report.html", "report.md", "README.md", "config_used.yaml", "run_manifest.json", "execution_commands.md", "audit/data_inventory.csv", "audit/experimental_design_audit.md", "audit/experimental_design_audit.html",
              "audit/evidence_matrix.csv", "audit/guide_reference_audit.csv", "audit/pair_mapping_audit.csv", "audit/scaffold_audit.csv", "audit/sample_metadata_audit.csv", "audit/previous_vs_new_analysis.md", "audit/pair_guide_reference.csv",
              "tables/target_support_matrix_across_runs.csv", "tables/previous_vs_new_summary.csv"):
        check(f"12 root output {f} exists", (OUT / f).is_file() and (OUT / f).stat().st_size > 0)
    html = (OUT / "report.html").read_text() if (OUT / "report.html").is_file() else ""
    secs = ["Executive summary", "Experimental information used", "Data and file inventory", "Sample structure", "Guide-design and pairing model", "Scaffold evidence", "Expression QC before filtering", "Expression QC after filtering",
            "Pair-guide QC", "Pair ambiguity and unresolved assignments", "PCA and clustering", "UMAP and Leiden results", "ECDF analysis", "Perturbation-expression analysis", "FDR and log2FC results", "Per-sample results", "Combined results",
            "Target-support and reproducibility", "Previous-versus-new run comparison", "Scientific limitations", "Reproducibility and execution information"]
    check("22 root report is a full 21-section analysis report (not comparison-only) and links every per-run report", all(s in html for s in secs) and all(f"{p}/report.html" in html for p in ["combined"] + [f"samples/{w}" for w in WELLS]), [s for s in secs if s not in html])
    check("13/24 root report tags evidence types and states that replicate identity is undocumented", all(s in html for s in ("experimental_document", "fastq_derived", "cellranger", "well-level support")) and "biological" in html.lower())
    n_fig = html.count("data:image/png;base64,")
    check("23 root HTML embeds figures and reports none missing", n_fig > 40 and "missing figure" not in html, f"{n_fig} figures embedded")
    md_root = (OUT / "report.md").read_text() if (OUT / "report.md").is_file() else ""
    fig_refs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md_root)
    missing_refs = [r for r in fig_refs if not (OUT / r).is_file() or (OUT / r).stat().st_size == 0]
    check("23 every figure referenced by the root Markdown exists and is non-empty", not missing_refs and len(fig_refs) > 40, missing_refs[:5] or f"{len(fig_refs)} references")
    man = json.load(open(OUT / "run_manifest.json")) if (OUT / "run_manifest.json").is_file() else {}
    check("21b run_manifest has branch/commit/jobs/versions/inputs/outputs", all(k in man for k in ("git_branch", "git_commit", "slurm_job_ids", "versions", "inputs", "outputs", "run_times")) and man.get("harmony") is False)
    ex = (OUT / "execution_commands.md").read_text() if (OUT / "execution_commands.md").is_file() else ""
    check("14 execution_commands has SBATCH scripts, commands, job ledger, versions, code changes", all(s in ex for s in ("#SBATCH", "perturbseq-pipeline run", "job_ids.txt", "## Environment", "Code changes")))
    check("25 remaining uncertainties documented (open questions in the design record and limitations section)", "Open questions" in (OUT / "audit" / "experimental_design_audit.md").read_text() and "Scientific limitations" in html)
    # ---- SLURM logs ----------------------------------------------------------------------------------
    ledger = (OUT / "slurm" / "job_ids.txt").read_text() if (OUT / "slurm" / "job_ids.txt").is_file() else ""
    superseded = set(re.findall(r"\((\d{7,9}) failed", ledger))
    errs = []
    for p in sorted((OUT / "slurm").glob("*.err")) + sorted((OUT / "slurm").glob("*.out")):
        t = p.read_text(errors="ignore")
        if ("Traceback" in t or "FAILED" in t) and not any(j in p.name for j in superseded) and not p.name.startswith("hpf2_05"):
            errs.append(p.name)
    check(f"4c no SLURM log with unhandled errors (superseded attempts {sorted(superseded)} excluded; documented in slurm/job_ids.txt)", not errs, errs)
    df = pd.DataFrame(checks)
    (OUT / "tables").mkdir(exist_ok=True)
    df.to_csv(OUT / "tables" / "final_validation.csv", index=False)
    (OUT / "final_validation.txt").write_text("\n".join(f"[{r.status}] {r.check}: {r.detail}" for r in df.itertuples()) + f"\n\n{int((df.status == 'PASS').sum())}/{len(df)} checks passed\n")
    print(f"\n{int((df.status == 'PASS').sum())}/{len(df)} checks passed")
    return 0 if (df.status == "PASS").all() else 1


if __name__ == "__main__":
    sys.exit(main())
