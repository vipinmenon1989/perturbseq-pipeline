"""Supplementary tables and figures for the Hanrui Fang baseline run.

Everything here is derived from the pipeline's own outputs (``results/Hanrui_fang/processed.h5ad``
and ``tables/*.csv``), the Cell Ranger outputs, and the basic-QC all-cells object
(``outputs/hanrui_fang_qc/combined/perttf_qc_allcells.h5ad``), which holds every Cell Ranger-
called cell with scanpy QC metrics — the pipeline itself never writes QC-failed cells.

Statistics reuse the pipeline's functions (``perturbation.compare_groups`` — two-sided KS,
one-sided MWU "less", log2FC on de-logged lognorm with pseudocount 0.01 — and
``perturbation.benjamini_hochberg``). Hit criterion mirrors the pipeline default:
``ks_fdr < fdr_alpha`` and ``log2fc < max_log2fc_for_hit``.

Convention: significance is plotted and tabulated as ``neg_log10_fdr = -log10(FDR)`` (positive).
The pipeline itself writes no ``log10FDR`` column; its plots use ``-log10(clip(FDR, 1e-300, 1))``.

Supplementary alias mapping (documented, not a pipeline default): design labels that are not
HGNC symbols are mapped to the symbol present in the GEX matrix so their target transcript can be
tested in the supplementary tables only: ``CEBPb -> CEBPB``, ``C6orf106 -> ILRUN``,
``CCBL2 -> KYAT3``, ``<GENE> (rsID) -> <GENE>``.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import anndata as ad
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import scipy.sparse as sp
import yaml

from perturbseq_pipeline.perturbation import benjamini_hochberg, compare_groups

warnings.filterwarnings("ignore")
sc.settings.verbosity = 1

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
RES = REPO / "results" / "Hanrui_fang"
QC_ALL = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc/combined/perttf_qc_allcells.h5ad")
INPUTS = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_inputs")
FIG = RES / "figures"
TAB = RES / "tables"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
WELL_COND = {"HF011A": "HF011", "HF011B": "HF011", "HF012A": "HF012", "HF012B": "HF012"}
WELL_REP = {"HF011A": "A", "HF011B": "B", "HF012A": "A", "HF012B": "B"}
ALIASES = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3"}
COLORS = {"HF011A": "#2a78d6", "HF011B": "#8ab4e8", "HF012A": "#eb6834", "HF012B": "#f3a98a"}
CLASS_COLORS = {"targeting": "#2a78d6", "non-targeting": "#1baf7a", "ambiguous": "#eda100", "unassigned": "#9a9a9a", "QC-failed": "#e34948"}
PSEUDO = 0.01
DPI = 130


def log(*a):
    print(*a, flush=True)


def save(fig, sub, name):
    p = FIG / sub / f"{name}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    log("  fig", p.relative_to(RES))


def style(ax):
    ax.grid(True, color="#e0dfda", linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def ecdf(ax, values, label, color, log_x=False, ls="-"):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return
    v = np.sort(v)
    y = np.arange(1, v.size + 1) / v.size
    if log_x:
        v = v + 1
        ax.set_xscale("log")
    ax.step(v, y, where="post", color=color, linewidth=1.4, linestyle=ls, label=f"{label} (n={v.size:,})")


def target_symbol(label: str) -> str:
    s = re.sub(r"\s*\(rs\d+\)\s*$", "", str(label)).strip()
    return ALIASES.get(s, s)


# --------------------------------------------------------------------------------------------
# Load
# --------------------------------------------------------------------------------------------


def load():
    cfg = yaml.safe_load(open(RES / "logs" / "resolved_config.yaml"))
    proc = ad.read_h5ad(RES / "processed.h5ad")
    log("processed:", proc.shape, "obs cols:", list(proc.obs.columns))
    allc = ad.read_h5ad(QC_ALL)
    log("all-cells:", allc.shape)
    # map processed cells back to Cell Ranger barcodes: pipeline obs_names are "<barcode>-<lane>"
    proc_bc = proc.obs_names.str.rsplit("-", n=1).str[0]
    proc.obs["cell_key"] = (proc.obs["lane_id"].astype(str) + "_" + proc_bc).to_numpy()
    allc.obs["cell_key"] = allc.obs_names.to_numpy()  # "<sample>_<barcode>"
    assert proc.obs["cell_key"].is_unique
    in_proc = allc.obs["cell_key"].isin(set(proc.obs["cell_key"]))
    allc.obs["pipeline_qc_pass"] = in_proc.to_numpy()
    assert int(in_proc.sum()) == proc.n_obs, (int(in_proc.sum()), proc.n_obs)
    # bring pipeline guide classes onto the all-cells object
    cls = pd.Series(proc.obs["perturbation_class"].astype(str).to_numpy(), index=proc.obs["cell_key"])
    allc.obs["perturbation_class"] = allc.obs["cell_key"].map(cls).fillna("QC-failed").to_numpy()
    tg = pd.Series(proc.obs["target_gene"].astype(str).to_numpy(), index=proc.obs["cell_key"])
    allc.obs["target_gene"] = allc.obs["cell_key"].map(tg).fillna("QC-failed").to_numpy()
    return cfg, proc, allc


# --------------------------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------------------------


def cell_counts_table(cfg, proc, allc, tested_targets):
    q = cfg["qc"]
    a = allc.obs
    rows = []
    groups = [(w, a["sample_id"].astype(str) == w) for w in WELLS]
    groups += [(c, a["condition_code"].astype(str) == c) for c in ("HF011", "HF012")]
    groups += [(f"replicate_{r}", a["gem_well"].astype(str) == r) for r in ("A", "B")]
    groups += [("ALL", pd.Series(True, index=a.index))]
    p = proc.obs
    p_groups = {w: p["lane_id"].astype(str) == w for w in WELLS}
    p_groups.update({c: p["condition"].astype(str) == c for c in ("HF011", "HF012")})
    p_groups.update({f"replicate_{r}": p["replicate"].astype(str) == r for r in ("A", "B")})
    p_groups["ALL"] = pd.Series(True, index=p.index)
    metrics = pd.read_csv(TAB / "cellranger_metrics_per_well.csv")
    cr_cells = {r["well"]: int(str(r["Estimated Number of Cells"]).replace(",", "")) for _, r in metrics.iterrows()}
    for name, m in groups:
        sub = a[m]
        n_in = int(len(sub))
        pm = p_groups[name]
        ps = p[pm]
        cr = sum(cr_cells[w] for w in WELLS if (w == name or WELL_COND[w] == name or f"replicate_{WELL_REP[w]}" == name or name == "ALL"))
        row = {
            "group": name,
            "group_type": "well" if name in WELLS else ("condition" if name in ("HF011", "HF012") else ("replicate_label" if name.startswith("replicate") else "all")),
            "condition_status": "inferred", "replicate_type": "unknown",
            "cellranger_called_cells": cr,
            "cells_loaded_by_pipeline": n_in,
            "fail_prefilter_min_genes_200": int((sub["n_genes_by_counts"] < q["min_genes_per_cell"]).sum()),
            "fail_min_genes_final_1000": int((sub["n_genes_by_counts"] < q["min_genes_final"]).sum()),
            "fail_max_pct_mt_20": int((sub["pct_counts_mt"] >= q["max_pct_mt"]).sum()),
            "fail_any_expression_qc": int((~sub["pipeline_qc_pass"]).sum()),
            "cells_passing_expression_qc": int(sub["pipeline_qc_pass"].sum()),
            "cells_zero_guide_umis": int((sub["guide_umi_total"] == 0).sum()),
            "qc_pass_cells_zero_guides_detected": int((ps["n_guides_detected"] == 0).sum()) if "n_guides_detected" in ps else np.nan,
            "guide_assigned_cells": int(ps["perturbation_class"].isin(["targeting", "non-targeting"]).sum()),
            "non_targeting_cells": int((ps["perturbation_class"] == "non-targeting").sum()),
            "targeting_cells": int((ps["perturbation_class"] == "targeting").sum()),
            "ambiguous_cells": int((ps["perturbation_class"] == "ambiguous").sum()),
            "unassigned_cells": int((ps["perturbation_class"] == "unassigned").sum()),
            "cells_in_clustering": int(len(ps)),
            "cells_in_perturbation_testing": int((((ps["perturbation_class"] == "targeting") & ps["target_gene"].astype(str).isin(tested_targets)) | (ps["perturbation_class"] == "non-targeting")).sum()),
            "final_analyzed_cells": int(len(ps)),
        }
        base = max(n_in, 1)
        for k in list(row):
            if k.startswith(("fail_", "cells_", "guide_", "non_", "targeting", "ambiguous", "unassigned", "final", "qc_pass")) and isinstance(row[k], (int, np.integer)):
                row[f"pct_{k}"] = round(100 * row[k] / base, 3)
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "cell_counts_before_after.csv", index=False)
    log("cell_counts_before_after written", df.shape)
    return df


def qc_per_well_table(allc):
    a = allc.obs
    rows = []
    for w in WELLS:
        for stage, m in (("before_qc", a["sample_id"].astype(str) == w), ("after_qc", (a["sample_id"].astype(str) == w) & a["pipeline_qc_pass"])):
            s = a[m]
            rows.append({
                "well": w, "condition": WELL_COND[w], "replicate": WELL_REP[w], "stage": stage, "n_cells": len(s),
                **{f"median_{c}": float(s[c].median()) for c in ("total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "pct_counts_hb", "guide_umi_total")},
                **{f"mean_{c}": float(s[c].mean()) for c in ("total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "pct_counts_hb")},
                "median_genes_per_umi": float((s["n_genes_by_counts"] / s["total_counts"]).median()),
            })
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "qc_metrics_per_well_before_after.csv", index=False)
    return df


def _expr_vector(proc, gene):
    X = proc.layers["lognorm"] if "lognorm" in proc.layers else proc.X
    j = proc.var_names.get_loc(gene)
    col = X[:, j]
    return np.asarray(col.todense()).ravel() if sp.issparse(col) else np.asarray(col).ravel()


def perturbation_tables(cfg, proc):
    pc = cfg["perturbation"]
    alpha, max_lfc = pc["fdr_alpha"], pc["max_log2fc_for_hit"]
    min_cells, min_ctrl = pc["min_cells_per_target"], pc["min_control_cells"]
    obs = proc.obs
    klass = obs["perturbation_class"].astype(str).to_numpy()
    tgt = obs["target_gene"].astype(str).to_numpy()
    gid = obs["guide_id"].astype(str).to_numpy()
    lane = obs["lane_id"].astype(str).to_numpy()
    targets = sorted(set(tgt[klass == "targeting"]))
    sym = {t: target_symbol(t) for t in targets}
    present = {t: s for t, s in sym.items() if s in proc.var_names}
    log(f"{len(targets)} assigned targets; {len(present)} with target gene present in the matrix; absent: {sorted(set(targets)-set(present))}")
    cache = {}

    def vec(gene):
        if gene not in cache:
            cache[gene] = _expr_vector(proc, gene)
        return cache[gene]

    def one(mask_p, mask_c, gene):
        if mask_p.sum() < min_cells or mask_c.sum() < min_ctrl:
            return None
        v = vec(gene)
        return compare_groups(v[mask_p], v[mask_c])

    by_target, by_guide = [], []
    wells_plus = WELLS + ["ALL"]
    for t, gene in present.items():
        for w in wells_plus:
            wm = np.ones(len(obs), bool) if w == "ALL" else lane == w
            mp = (klass == "targeting") & (tgt == t) & wm
            for ctrl in ("ntc", "other"):
                mc = ((klass == "non-targeting") if ctrl == "ntc" else ((klass == "targeting") & (tgt != t))) & wm
                r = one(mp, mc, gene)
                row = {"target_label": t, "target_gene": gene, "alias_mapped": gene != t, "well": w,
                       "condition": WELL_COND.get(w, "pooled"), "replicate": WELL_REP.get(w, "pooled"),
                       "control": ctrl, "n_targeting_cells": int(mp.sum()), "n_control_cells": int(mc.sum()),
                       "median_lognorm_targeting": float(np.median(vec(gene)[mp])) if mp.any() else np.nan,
                       "median_lognorm_control": float(np.median(vec(gene)[mc])) if mc.any() else np.nan}
                if r is not None:
                    row.update(r)
                else:
                    row["skipped_reason"] = f"fewer than {min_cells} targeting or {min_ctrl} control cells"
                by_target.append(row)
            # per guide (assigned guide id) vs ntc within the same well
            for g in sorted(set(gid[mp])):
                mg = mp & (gid == g)
                mc = (klass == "non-targeting") & wm
                r = one(mg, mc, gene)
                row = {"guide_id": g, "target_label": t, "target_gene": gene, "well": w, "condition": WELL_COND.get(w, "pooled"),
                       "replicate": WELL_REP.get(w, "pooled"), "control": "ntc", "n_targeting_cells": int(mg.sum()), "n_control_cells": int(mc.sum())}
                if r is not None:
                    row.update(r)
                else:
                    row["skipped_reason"] = f"fewer than {min_cells} cells with this guide or {min_ctrl} controls"
                by_guide.append(row)

    def finish(df, group_cols):
        df = pd.DataFrame(df)
        df["fdr_ks"] = np.nan
        df["fdr_mwu"] = np.nan
        for _, idx in df.groupby(group_cols, dropna=False).groups.items():
            sub = df.loc[idx]
            df.loc[idx, "fdr_ks"] = benjamini_hochberg(sub["ks_pval"].to_numpy(dtype=float)) if "ks_pval" in sub else np.nan
            df.loc[idx, "fdr_mwu"] = benjamini_hochberg(sub["mwu_pval_less"].to_numpy(dtype=float)) if "mwu_pval_less" in sub else np.nan
        df["neg_log10_fdr_ks"] = -np.log10(np.clip(df["fdr_ks"].astype(float), 1e-300, 1))
        df["direction"] = np.where(df["log2fc"] < 0, "down", np.where(df["log2fc"] > 0, "up", "none"))
        df.loc[df["log2fc"].isna(), "direction"] = "not_tested"
        df["passes_default_hit_criteria"] = (df["fdr_ks"] < alpha) & (df["log2fc"] < max_lfc)
        df["hit_rule"] = f"ks_fdr < {alpha} and log2fc < {max_lfc} (pipeline default; FDR = BH within well x control)"
        df["fdr_convention"] = "neg_log10_fdr_ks = -log10(BH FDR of two-sided KS p); positive values = more significant"
        return df

    bt = finish(by_target, ["well", "control"])
    bg = finish(by_guide, ["well"])
    bt.to_csv(TAB / "perturbation_expression_by_target.csv", index=False)
    bg.to_csv(TAB / "perturbation_expression_by_guide.csv", index=False)

    # replicate / well-level concordance summary (ntc control)
    rows = []
    for t, gene in present.items():
        sub = bt[(bt["target_label"] == t) & (bt["control"] == "ntc") & (bt["well"] != "ALL") & bt["log2fc"].notna()]
        pooled = bt[(bt["target_label"] == t) & (bt["control"] == "ntc") & (bt["well"] == "ALL")]
        row = {"target_label": t, "target_gene": gene, "n_wells_tested": int(len(sub)),
               "n_confirmed_biological_replicates": "unknown (A/B replicate type not confirmed by experimenters)",
               "n_wells_same_direction_as_pooled": int((np.sign(sub["log2fc"]) == np.sign(pooled["log2fc"].iloc[0])).sum()) if len(pooled) and pooled["log2fc"].notna().all() else np.nan,
               "n_wells_passing_fdr": int(sub["passes_default_hit_criteria"].sum()),
               "pooled_log2fc_ntc": float(pooled["log2fc"].iloc[0]) if len(pooled) else np.nan,
               "pooled_fdr_ks_ntc": float(pooled["fdr_ks"].iloc[0]) if len(pooled) else np.nan}
        for w in WELLS:
            r = sub[sub["well"] == w]
            row[f"log2fc_{w}"] = float(r["log2fc"].iloc[0]) if len(r) else np.nan
            row[f"fdr_ks_{w}"] = float(r["fdr_ks"].iloc[0]) if len(r) else np.nan
            row[f"n_targeting_{w}"] = int(r["n_targeting_cells"].iloc[0]) if len(r) else 0
        for c in ("HF011", "HF012"):
            a_, b_ = row.get(f"log2fc_{c}A"), row.get(f"log2fc_{c}B")
            row[f"{c}_AB_capture_concordant_direction"] = bool(np.sign(a_) == np.sign(b_)) if np.isfinite(a_) and np.isfinite(b_) else None
        n = row["n_wells_tested"]
        row["reproducibility_label"] = (
            "well-level concordant (exploratory; A/B not confirmed as biological replicates)"
            if n >= 2 and row["n_wells_passing_fdr"] == n else
            "partially concordant (exploratory)" if n >= 2 and row["n_wells_passing_fdr"] > 0 else
            "not significant in any well" if n >= 2 else "insufficient wells (exploratory)")
        rows.append(row)
    rep = pd.DataFrame(rows)
    rep.to_csv(TAB / "perturbation_replicate_summary.csv", index=False)
    log("perturbation tables written", bt.shape, bg.shape, rep.shape)
    return bt, bg, rep, present


# --------------------------------------------------------------------------------------------
# QC figures
# --------------------------------------------------------------------------------------------


def fig_cellranger_metrics():
    m = pd.read_csv(TAB / "cellranger_metrics_per_well.csv")
    cols = ["Estimated Number of Cells", "Mean Reads per Cell", "Median Genes per Cell", "Median UMI Counts per Cell",
            "Sequencing Saturation", "Fraction Reads in Cells", "Reads Mapped Confidently to Transcriptome", "Valid Barcodes"]
    fig, axes = plt.subplots(2, 4, figsize=(15, 6))
    for ax, c in zip(axes.ravel(), cols):
        vals = [float(str(v).replace(",", "").replace("%", "")) for v in m[c]]
        ax.bar(m["well"], vals, color=[COLORS[w] for w in m["well"]])
        ax.set_title(c + (" (%)" if "%" in str(m[c].iloc[0]) else ""), fontsize=9)
        ax.tick_params(axis="x", labelsize=8)
        style(ax)
    fig.suptitle("Cell Ranger metrics per well (metrics_summary.csv)", fontsize=11)
    fig.tight_layout()
    save(fig, "qc", "supp_cellranger_metrics_per_well")


def fig_counts_and_retention(cc):
    wells = cc[cc["group_type"] == "well"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    ax = axes[0]
    x = np.arange(len(wells))
    ax.bar(x - 0.2, wells["cellranger_called_cells"], width=0.4, color="#9a9a9a", label="Cell Ranger called")
    ax.bar(x + 0.2, wells["cells_loaded_by_pipeline"], width=0.4, color=[COLORS[w] for w in wells["group"]], label="loaded by pipeline")
    ax.set_xticks(x)
    ax.set_xticklabels(wells["group"])
    ax.set_ylabel("cells")
    ax.set_title("Input cells per well")
    ax.legend(fontsize=8, frameon=False)
    style(ax)
    ax = axes[1]
    ax.bar(x - 0.2, wells["cells_loaded_by_pipeline"], width=0.4, color="#c8c7c1", label="before QC")
    ax.bar(x + 0.2, wells["cells_passing_expression_qc"], width=0.4, color=[COLORS[w] for w in wells["group"]], label="after default QC")
    for xi, (_, r) in zip(x, wells.iterrows()):
        ax.text(xi + 0.2, r["cells_passing_expression_qc"], f"{100 * r['cells_passing_expression_qc'] / r['cells_loaded_by_pipeline']:.1f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(wells["group"])
    ax.set_ylabel("cells")
    ax.set_title("Cell retention: pipeline default QC (min genes 200/1000, mt < 20%)")
    ax.legend(fontsize=8, frameon=False)
    style(ax)
    fig.tight_layout()
    save(fig, "qc", "supp_input_cells_and_retention_per_well")


def fig_distributions(allc):
    a = allc.obs
    specs = [("total_counts", "Total UMIs", True), ("n_genes_by_counts", "Detected genes", True),
             ("pct_counts_mt", "Mitochondrial %", False), ("pct_counts_ribo", "Ribosomal %", False), ("pct_counts_hb", "Haemoglobin %", False)]
    for col, label, logx in specs:
        fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), sharey=False)
        for ax, w in zip(axes, WELLS):
            s = a[a["sample_id"].astype(str) == w]
            v = s[col].to_numpy(float)
            pos = v[v > 0] if logx else v
            if logx:
                bins = np.logspace(np.log10(max(pos.min(), 1)), np.log10(pos.max() + 1), 60)
                ax.set_xscale("log")
            else:
                hi = max(np.nanpercentile(v, 99.5) * 1.1, 1e-3)
                bins = np.linspace(0, hi, 60)
            ax.hist(v, bins=bins, color="#c8c7c1", label="before QC", histtype="stepfilled")
            ax.hist(v[s["pipeline_qc_pass"].to_numpy()], bins=bins, color=COLORS[w], alpha=0.85, label="after QC", histtype="stepfilled")
            ax.set_title(f"{w} ({WELL_COND[w]}, capture {WELL_REP[w]})", fontsize=9)
            ax.set_xlabel(label)
            ax.set_ylabel("cells")
            ax.legend(fontsize=7, frameon=False)
            style(ax)
        fig.suptitle(f"{label}: before vs after pipeline default QC, faceted by well", fontsize=10)
        fig.tight_layout()
        save(fig, "qc", f"supp_dist_{col}_before_after")
    # UMI vs genes scatter per well
    fig, axes = plt.subplots(1, 4, figsize=(16, 4))
    rng = np.random.default_rng(0)
    for ax, w in zip(axes, WELLS):
        s = a[a["sample_id"].astype(str) == w]
        idx = rng.choice(len(s), min(len(s), 25000), replace=False)
        s = s.iloc[idx]
        ok = s["pipeline_qc_pass"].to_numpy()
        ax.scatter(s["total_counts"][ok], s["n_genes_by_counts"][ok], s=2, alpha=0.3, color=COLORS[w], linewidths=0, label="pass", rasterized=True)
        ax.scatter(s["total_counts"][~ok], s["n_genes_by_counts"][~ok], s=4, alpha=0.7, color="#e34948", linewidths=0, label="fail", rasterized=True)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Total UMIs")
        ax.set_ylabel("Detected genes")
        ax.set_title(w, fontsize=9)
        ax.legend(fontsize=7, frameon=False, markerscale=4)
        style(ax)
    fig.suptitle("UMIs vs detected genes (25k cells shown per well; red = failed pipeline default QC)", fontsize=10)
    fig.tight_layout()
    save(fig, "qc", "supp_umi_vs_genes_per_well")


def fig_ecdfs(allc, proc):
    a = allc.obs
    specs = [("total_counts", "Total UMIs", True), ("n_genes_by_counts", "Detected genes", True), ("pct_counts_mt", "Mitochondrial %", False),
             ("pct_counts_ribo", "Ribosomal %", False), ("guide_umi_total", "Guide UMIs per cell", True), ("n_guides", "Guides detected per cell (>= 3 UMIs)", False)]
    for col, label, logx in specs:
        fig, axes = plt.subplots(1, 4, figsize=(16, 3.6), sharey=True)
        for ax, w in zip(axes, WELLS):
            s = a[a["sample_id"].astype(str) == w]
            ecdf(ax, s[col], "before QC", "#7a7975", logx, "--")
            ecdf(ax, s.loc[s["pipeline_qc_pass"], col], "after QC", COLORS[w], logx)
            ax.set_title(f"{w} ({WELL_COND[w]}, capture {WELL_REP[w]})", fontsize=9)
            ax.set_xlabel(label + (" + 1" if logx else ""))
            ax.legend(fontsize=7, frameon=False, loc="lower right")
            style(ax)
        axes[0].set_ylabel("ECDF")
        fig.suptitle(f"ECDF of {label}: before vs after pipeline default QC", fontsize=10)
        fig.tight_layout()
        save(fig, "qc", f"supp_ecdf_{col}_before_after")
    # pipeline's own n_guides_detected (> 3 UMIs) after QC by well
    if "n_guides_detected" in proc.obs:
        fig, ax = plt.subplots(figsize=(5.5, 3.8))
        for w in WELLS:
            ecdf(ax, proc.obs.loc[proc.obs["lane_id"].astype(str) == w, "n_guides_detected"], w, COLORS[w])
        ax.set_xlabel("pipeline n_guides_detected (> 3 UMIs), QC-passing cells")
        ax.set_ylabel("ECDF")
        ax.legend(fontsize=7, frameon=False)
        style(ax)
        fig.tight_layout()
        save(fig, "guides", "supp_ecdf_n_guides_detected_after_qc_by_well")


def fig_knee():
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.8), sharey=True)
    for ax, w in zip(axes, WELLS):
        raw = sc.read_10x_h5(INPUTS / "cellranger" / w / "raw_feature_bc_matrix.h5")
        tot = np.asarray(raw.X.sum(axis=1)).ravel()
        tot = np.sort(tot[tot > 0])[::-1]
        called = set(pd.read_csv(INPUTS / "cellranger" / w / "filtered_feature_bc_matrix" / "barcodes.tsv.gz", header=None)[0])
        n_called = len(called)
        ax.plot(np.arange(1, tot.size + 1), tot, color=COLORS[w], linewidth=1.4)
        ax.axvline(n_called, color="#e34948", linestyle="--", linewidth=1, label=f"Cell Ranger cells = {n_called:,}")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("barcode rank")
        ax.set_title(w, fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        style(ax)
        del raw
    axes[0].set_ylabel("total UMIs")
    fig.suptitle("Barcode-rank (knee) plots from raw_feature_bc_matrix.h5", fontsize=10)
    fig.tight_layout()
    save(fig, "qc", "supp_barcode_rank_knee_per_well")


def fig_qc_heatmap(qcw):
    after = qcw[qcw["stage"] == "after_qc"].set_index("well")
    cols = [c for c in after.columns if c.startswith("median_")]
    mat = after[cols].astype(float)
    z = (mat - mat.mean()) / mat.std(ddof=0).replace(0, 1)
    fig, ax = plt.subplots(figsize=(9, 3.2))
    im = ax.imshow(z.to_numpy(), cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([c.replace("median_", "") for c in cols], rotation=35, ha="right", fontsize=8)
    ax.set_yticks(range(len(after)))
    ax.set_yticklabels(after.index)
    for i in range(len(after)):
        for j, c in enumerate(cols):
            ax.text(j, i, f"{mat.iloc[i, j]:.3g}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="z-score across wells")
    ax.set_title("Per-well QC medians after default QC (cell values; colour = z-score)", fontsize=9)
    fig.tight_layout()
    save(fig, "qc", "supp_per_well_qc_heatmap")


def fig_replicate_concordance(proc):
    """A vs B capture concordance within each inferred condition: mean lognorm per gene."""
    X = proc.layers["lognorm"] if "lognorm" in proc.layers else proc.X
    lane = proc.obs["lane_id"].astype(str).to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, c in zip(axes, ("HF011", "HF012")):
        ma = np.asarray(X[lane == f"{c}A"].mean(axis=0)).ravel()
        mb = np.asarray(X[lane == f"{c}B"].mean(axis=0)).ravel()
        keep = (ma > 0) | (mb > 0)
        r = np.corrcoef(ma[keep], mb[keep])[0, 1]
        ax.scatter(ma[keep], mb[keep], s=3, alpha=0.4, color=COLORS[f"{c}A"], linewidths=0, rasterized=True)
        lim = max(ma.max(), mb.max())
        ax.plot([0, lim], [0, lim], color="#e34948", linewidth=1)
        ax.set_xlabel(f"{c}A mean lognorm")
        ax.set_ylabel(f"{c}B mean lognorm")
        ax.set_title(f"{c}: capture A vs B, Pearson r = {r:.4f} ({keep.sum():,} genes)", fontsize=9)
        style(ax)
    fig.suptitle("Capture-level (A/B) concordance of gene means — replicate type not confirmed", fontsize=10)
    fig.tight_layout()
    save(fig, "qc", "supp_replicate_concordance_gene_means")


# --------------------------------------------------------------------------------------------
# Clustering / embedding figures
# --------------------------------------------------------------------------------------------


def _scatter_cat(ax, xy, labels, palette, title, order=None, max_pts=80000, seed=0):
    rng = np.random.default_rng(seed)
    idx = rng.choice(xy.shape[0], min(xy.shape[0], max_pts), replace=False)
    xy = xy[idx]
    labels = np.asarray(labels)[idx]
    order = order or list(pd.unique(labels))
    for k in order:
        m = labels == k
        if m.any():
            ax.scatter(xy[m, 0], xy[m, 1], s=2, alpha=0.5, color=palette.get(k, "#9a9a9a"), linewidths=0, label=f"{k} ({m.sum():,})", rasterized=True)
    ax.set_title(title, fontsize=9)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(fontsize=6, frameon=False, markerscale=5, loc="best")


def fig_embeddings_processed(proc):
    cond_pal = {"HF011": "#2a78d6", "HF012": "#eb6834"}
    for key, name in (("X_pca", "pca"), ("X_umap", "umap")):
        if key not in proc.obsm:
            continue
        xy = np.asarray(proc.obsm[key])[:, :2]
        fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
        _scatter_cat(axes[0], xy, proc.obs["lane_id"].astype(str), COLORS, f"{name.upper()} by well (QC-passing cells)", WELLS)
        _scatter_cat(axes[1], xy, proc.obs["condition"].astype(str), cond_pal, f"{name.upper()} by inferred condition")
        _scatter_cat(axes[2], xy, proc.obs["perturbation_class"].astype(str), CLASS_COLORS, f"{name.upper()} by guide assignment class",
                     ["ambiguous", "unassigned", "targeting", "non-targeting"])
        fig.tight_layout()
        save(fig, "clustering" if name == "pca" else "guides" if False else "clustering", f"supp_{name}_processed_by_well_condition_class")
        if name == "umap":
            fig, ax = plt.subplots(figsize=(5.5, 5))
            _scatter_cat(ax, xy, proc.obs["perturbation_class"].astype(str), CLASS_COLORS, "UMAP: guide-assigned, ambiguous, unassigned, non-targeting",
                         ["ambiguous", "unassigned", "targeting", "non-targeting"])
            fig.tight_layout()
            save(fig, "guides", "supp_umap_guide_assignment_classes")


def fig_embedding_all_cells(allc, cfg):
    """Supplementary embedding of ALL Cell Ranger cells (pass + fail) with pipeline-like defaults."""
    cc = cfg["cluster"]
    a = allc.copy()
    a.X = a.layers["counts"].copy() if "counts" in a.layers else a.X
    sc.pp.filter_genes(a, min_cells=3)
    sc.pp.normalize_total(a, target_sum=cc.get("target_sum"))
    sc.pp.log1p(a)
    sc.pp.highly_variable_genes(a, n_top_genes=min(cc["n_top_genes"], a.n_vars))
    a = a[:, a.var["highly_variable"]].copy()
    sc.pp.scale(a, max_value=cc["scale_max_value"])
    sc.tl.pca(a, n_comps=cc["n_pcs"], svd_solver="arpack", random_state=0)
    sc.pp.neighbors(a, n_neighbors=cc["n_neighbors"], n_pcs=cc["n_pcs"], random_state=0)
    sc.tl.umap(a, min_dist=cc["umap_min_dist"], random_state=0)
    qc_status = np.where(a.obs["pipeline_qc_pass"], "QC pass", "QC fail")
    pal_qc = {"QC pass": "#2a78d6", "QC fail": "#e34948"}
    cond_pal = {"HF011": "#2a78d6", "HF012": "#eb6834"}
    for key, name in (("X_pca", "pca"), ("X_umap", "umap")):
        xy = np.asarray(a.obsm[key])[:, :2]
        fig, axes = plt.subplots(1, 4, figsize=(20, 4.6))
        _scatter_cat(axes[0], xy, a.obs["sample_id"].astype(str), COLORS, f"{name.upper()} (all cells) by well", WELLS)
        _scatter_cat(axes[1], xy, a.obs["condition_code"].astype(str), cond_pal, f"{name.upper()} by inferred condition")
        _scatter_cat(axes[2], xy, qc_status, pal_qc, f"{name.upper()} by pipeline QC status", ["QC pass", "QC fail"])
        _scatter_cat(axes[3], xy, a.obs["perturbation_class"].astype(str), CLASS_COLORS, f"{name.upper()} by guide class (QC-failed shown)",
                     ["QC-failed", "ambiguous", "unassigned", "targeting", "non-targeting"])
        fig.suptitle(f"Supplementary {name.upper()} of all {a.n_obs:,} Cell Ranger cells (pipeline-like defaults; not the pipeline embedding)", fontsize=10)
        fig.tight_layout()
        save(fig, "clustering", f"supp_{name}_all_cells_by_well_condition_qcstatus")
    pd.DataFrame(a.obsm["X_umap"], index=a.obs_names, columns=["umap1", "umap2"]).assign(qc_status=qc_status).to_csv(TAB / "supp_all_cells_umap.csv")


# --------------------------------------------------------------------------------------------
# Guide figures
# --------------------------------------------------------------------------------------------


def fig_guide_summaries(proc, cc):
    obs = proc.obs
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    ax = axes[0]
    ct = pd.crosstab(obs["lane_id"].astype(str), obs["perturbation_class"].astype(str)).reindex(WELLS)
    bottom = np.zeros(len(ct))
    for k in ["targeting", "non-targeting", "ambiguous", "unassigned"]:
        if k in ct:
            ax.bar(ct.index, ct[k], bottom=bottom, color=CLASS_COLORS[k], label=k)
            bottom += ct[k].to_numpy()
    ax.set_ylabel("QC-passing cells")
    ax.set_title("Guide assignment outcome per well (default dominance rule)", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    ax = axes[1]
    for w in WELLS:
        s = obs[obs["lane_id"].astype(str) == w]
        ax.hist(s["n_guides_detected"].clip(upper=10), bins=np.arange(-0.5, 11.5, 1), histtype="step", linewidth=1.5, color=COLORS[w], label=f"{w} (MOI {s['n_guides_detected'].mean():.2f})")
    ax.set_xlabel("guides detected per cell (> 3 UMIs, capped at 10)")
    ax.set_ylabel("cells")
    ax.set_title("Guides detected per cell / MOI", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    ax = axes[2]
    ratio = (obs["top_guide_count"].astype(float) / obs["second_guide_count"].astype(float).clip(lower=1)).replace(np.inf, np.nan)
    for w in WELLS:
        m = obs["lane_id"].astype(str) == w
        ecdf(ax, ratio[m], w, COLORS[w], log_x=True)
    ax.axvline(2 + 1, color="#e34948", linestyle="--", linewidth=1, label="dominance_ratio = 2")
    ax.set_xlabel("top / second guide UMI ratio (+1, log)")
    ax.set_ylabel("ECDF")
    ax.set_title("Top-vs-second guide dominance", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    fig.tight_layout()
    save(fig, "guides", "supp_guide_assignment_moi_dominance_per_well")

    # representation: targets and NTC per well; guide representation
    fig, axes = plt.subplots(1, 2, figsize=(15, 4.5))
    ax = axes[0]
    tt = pd.crosstab(obs.loc[obs["perturbation_class"].isin(["targeting", "non-targeting"]), "target_gene"].astype(str), obs["lane_id"].astype(str)).reindex(columns=WELLS).fillna(0)
    tt = tt.loc[tt.sum(axis=1).sort_values(ascending=False).index]
    bottom = np.zeros(len(tt))
    for w in WELLS:
        ax.bar(range(len(tt)), tt[w], bottom=bottom, color=COLORS[w], label=w)
        bottom += tt[w].to_numpy()
    ax.set_xticks(range(len(tt)))
    ax.set_xticklabels(tt.index, rotation=90, fontsize=6)
    ax.set_ylabel("assigned cells")
    ax.set_title("Target representation (assigned cells per target incl. non-targeting), stacked by well", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    ax = axes[1]
    G = sp.csr_matrix(proc.obsm["guide_counts"]) if "guide_counts" in proc.obsm else None
    if G is not None:
        for w in WELLS:
            m = (obs["lane_id"].astype(str) == w).to_numpy()
            umis = np.asarray(G[m].sum(axis=0)).ravel()
            ax.plot(np.arange(1, umis.size + 1), np.sort(umis)[::-1] + 1, color=COLORS[w], label=f"{w} ({int((umis > 0).sum())}/{umis.size} guides)")
        ax.set_yscale("log")
        ax.set_xlabel("designed guides ranked by UMIs")
        ax.set_ylabel("guide UMIs in QC-passing cells + 1")
        ax.set_title("Guide representation per well", fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        style(ax)
    fig.tight_layout()
    save(fig, "guides", "supp_target_and_guide_representation_per_well")

    fig, ax = plt.subplots(figsize=(6, 3.6))
    wells = cc[cc["group_type"] == "well"]
    x = np.arange(len(wells))
    ax.bar(x - 0.3, wells["guide_assigned_cells"], width=0.3, color="#2a78d6", label="guide-assigned (targeting + NTC)")
    ax.bar(x, wells["non_targeting_cells"], width=0.3, color="#1baf7a", label="non-targeting")
    ax.bar(x + 0.3, wells["cells_zero_guide_umis"], width=0.3, color="#9a9a9a", label="zero guide UMIs")
    ax.set_xticks(x)
    ax.set_xticklabels(wells["group"])
    ax.set_ylabel("cells")
    ax.set_title("Guide-assigned cells per well", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    fig.tight_layout()
    save(fig, "guides", "supp_guide_assigned_cells_per_well")


# --------------------------------------------------------------------------------------------
# Perturbation figures
# --------------------------------------------------------------------------------------------


def fig_perturbation(bt, bg, rep, proc, present, cfg):
    alpha = cfg["perturbation"]["fdr_alpha"]
    pooled = bt[(bt["well"] == "ALL") & (bt["control"] == "ntc") & bt["log2fc"].notna()].copy()
    pooled_other = bt[(bt["well"] == "ALL") & (bt["control"] == "other") & bt["log2fc"].notna()].copy()
    # volcano (pooled, ntc) + other
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, df, ttl in zip(axes, (pooled, pooled_other), ("vs non-targeting cells", "vs other-target cells (may themselves be perturbed)")):
        hit = df["passes_default_hit_criteria"].to_numpy(bool)
        ax.scatter(df["log2fc"][~hit], df["neg_log10_fdr_ks"][~hit], s=18, color="#9a9a9a", label="not hit")
        ax.scatter(df["log2fc"][hit], df["neg_log10_fdr_ks"][hit], s=18, color="#2a78d6", label=f"hit (KS FDR < {alpha}, log2FC < 0)")
        for _, r in df.iterrows():
            ax.annotate(r["target_label"], (r["log2fc"], r["neg_log10_fdr_ks"]), fontsize=6, xytext=(2, 2), textcoords="offset points")
        ax.axhline(-np.log10(alpha), color="#e34948", linestyle="--", linewidth=1)
        ax.axvline(0, color="#7a7975", linewidth=0.8)
        ax.set_xlabel("log2FC (target transcript, targeting vs control)")
        ax.set_ylabel("-log10(BH FDR, two-sided KS)")
        ax.set_title(f"Pooled wells, {ttl}", fontsize=9)
        ax.legend(fontsize=7, frameon=False)
        style(ax)
    fig.suptitle("Target-transcript depletion (pooled 4 wells; alias-mapped labels included)", fontsize=10)
    fig.tight_layout()
    save(fig, "perturbation", "supp_volcano_log2fc_vs_neglog10fdr")

    # waterfall
    df = pooled.sort_values("log2fc")
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.bar(range(len(df)), df["log2fc"], color=np.where(df["passes_default_hit_criteria"], "#2a78d6", "#9a9a9a"))
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(df["target_label"], rotation=90, fontsize=7)
    ax.set_ylabel("log2FC vs NTC (pooled)")
    ax.set_title("Waterfall of target-transcript log2FC (blue = passes default hit criteria)", fontsize=9)
    style(ax)
    fig.tight_layout()
    save(fig, "perturbation", "supp_waterfall_target_log2fc")

    # heatmaps by well
    perwell = bt[(bt["well"] != "ALL") & (bt["control"] == "ntc")]
    order = df["target_label"].tolist()
    for col, name, cmap, vlim in (("log2fc", "log2FC", "RdBu_r", (-4, 4)), ("neg_log10_fdr_ks", "-log10(FDR)", "Blues", (0, 20))):
        piv = perwell.pivot(index="target_label", columns="well", values=col).reindex(index=order, columns=WELLS)
        fig, ax = plt.subplots(figsize=(6, 0.28 * len(piv) + 1.5))
        im = ax.imshow(piv.to_numpy(dtype=float), cmap=cmap, vmin=vlim[0], vmax=vlim[1], aspect="auto")
        ax.set_yticks(range(len(piv)))
        ax.set_yticklabels(piv.index, fontsize=7)
        ax.set_xticks(range(len(WELLS)))
        ax.set_xticklabels(WELLS, fontsize=8)
        fig.colorbar(im, ax=ax, label=name)
        ax.set_title(f"{name} by well (targeting vs NTC within well)", fontsize=9)
        fig.tight_layout()
        save(fig, "perturbation", f"supp_heatmap_{col}_by_well")

    # ECDF of -log10 FDR across targets by well / condition
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    for w in WELLS:
        ecdf(ax, perwell.loc[perwell["well"] == w, "neg_log10_fdr_ks"], f"{w} ({WELL_COND[w]})", COLORS[w])
    ax.axvline(-np.log10(alpha), color="#e34948", linestyle="--", linewidth=1)
    ax.set_xlabel("-log10(BH FDR) across targets")
    ax.set_ylabel("ECDF")
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    fig.tight_layout()
    save(fig, "perturbation", "supp_ecdf_neglog10fdr_by_well")

    # ECDF of target expression: targeting vs NTC vs other, faceted by well, for the 8 strongest + 4 weakest targets
    picks = df["target_label"].tolist()[:8] + df["target_label"].tolist()[-4:]
    obs = proc.obs
    klass = obs["perturbation_class"].astype(str).to_numpy()
    tgt = obs["target_gene"].astype(str).to_numpy()
    lane = obs["lane_id"].astype(str).to_numpy()
    for t in picks:
        gene = present[t]
        v = _expr_vector(proc, gene)
        fig, axes = plt.subplots(1, 4, figsize=(16, 3.4), sharey=True)
        for ax, w in zip(axes, WELLS):
            wm = lane == w
            ecdf(ax, v[wm & (klass == "targeting") & (tgt == t)], "targeting", "#2a78d6")
            ecdf(ax, v[wm & (klass == "non-targeting")], "non-targeting", "#1baf7a")
            ecdf(ax, v[wm & (klass == "targeting") & (tgt != t)], "other-target", "#eda100", ls=":")
            ax.set_title(f"{w} ({WELL_COND[w]}, capture {WELL_REP[w]})", fontsize=9)
            ax.set_xlabel(f"{gene} lognorm expression")
            ax.legend(fontsize=6, frameon=False, loc="lower right")
            style(ax)
        axes[0].set_ylabel("ECDF")
        fig.suptitle(f"Target transcript {gene} (design label {t}): targeting vs controls", fontsize=10)
        fig.tight_layout()
        save(fig, "perturbation", f"supp_ecdf_target_expression_{re.sub(r'[^A-Za-z0-9]+', '_', t)}")

    # counts: targeting cells per target; targets passing per well
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    ax = axes[0]
    cnt = perwell.pivot(index="target_label", columns="well", values="n_targeting_cells").reindex(index=order, columns=WELLS).fillna(0)
    bottom = np.zeros(len(cnt))
    for w in WELLS:
        ax.bar(range(len(cnt)), cnt[w], bottom=bottom, color=COLORS[w], label=w)
        bottom += cnt[w].to_numpy()
    ax.set_xticks(range(len(cnt)))
    ax.set_xticklabels(cnt.index, rotation=90, fontsize=7)
    ax.set_ylabel("targeting cells (assigned)")
    ax.set_title("Targeting cells per target, stacked by well", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    ax = axes[1]
    passing = perwell.groupby("well")["passes_default_hit_criteria"].sum().reindex(WELLS)
    tested = perwell.groupby("well")["log2fc"].apply(lambda s: s.notna().sum()).reindex(WELLS)
    ax.bar(WELLS, tested, color="#c8c7c1", label="targets tested")
    ax.bar(WELLS, passing, color=[COLORS[w] for w in WELLS], label=f"pass (KS FDR < {alpha} & log2FC < 0)")
    ax.set_ylabel("targets")
    ax.set_title("Targets passing default criteria per well", fontsize=9)
    ax.legend(fontsize=7, frameon=False)
    style(ax)
    fig.tight_layout()
    save(fig, "perturbation", "supp_targeting_cells_and_passing_targets_per_well")

    # replicate consistency: A vs B log2FC per condition
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, c in zip(axes, ("HF011", "HF012")):
        x = rep[f"log2fc_{c}A"]
        y = rep[f"log2fc_{c}B"]
        ok = x.notna() & y.notna()
        r = np.corrcoef(x[ok], y[ok])[0, 1] if ok.sum() > 2 else np.nan
        ax.scatter(x[ok], y[ok], s=18, color=COLORS[f"{c}A"])
        for _, rr in rep[ok].iterrows():
            ax.annotate(rr["target_label"], (rr[f"log2fc_{c}A"], rr[f"log2fc_{c}B"]), fontsize=6, xytext=(2, 2), textcoords="offset points")
        lim = [min(x[ok].min(), y[ok].min()) - 0.2, max(x[ok].max(), y[ok].max()) + 0.2]
        ax.plot(lim, lim, color="#e34948", linewidth=1)
        ax.set_xlabel(f"log2FC {c}A")
        ax.set_ylabel(f"log2FC {c}B")
        ax.set_title(f"{c}: capture A vs B log2FC (r = {r:.3f}) — capture-level concordance", fontsize=9)
        style(ax)
    fig.tight_layout()
    save(fig, "perturbation", "supp_replicate_consistency_log2fc_A_vs_B")

    # per-guide vs target-level efficacy (pooled, ntc)
    g = bg[(bg["well"] == "ALL") & bg["log2fc"].notna()].merge(pooled[["target_label", "log2fc"]].rename(columns={"log2fc": "target_log2fc"}), on="target_label")
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(g["target_log2fc"], g["log2fc"], s=10 + g["n_targeting_cells"] / 20, alpha=0.6, color=np.where(g["passes_default_hit_criteria"], "#2a78d6", "#9a9a9a"), linewidths=0)
    lim = [min(g["target_log2fc"].min(), g["log2fc"].min()) - 0.3, max(g["target_log2fc"].max(), g["log2fc"].max()) + 0.3]
    ax.plot(lim, lim, color="#e34948", linewidth=1)
    ax.set_xlabel("target-level log2FC (pooled)")
    ax.set_ylabel("per-guide log2FC (pooled)")
    ax.set_title(f"Per-guide vs target-level efficacy ({len(g)} guides; size = cells; blue = guide passes)", fontsize=9)
    style(ax)
    fig.tight_layout()
    save(fig, "perturbation", "supp_per_guide_vs_target_efficacy")


# --------------------------------------------------------------------------------------------


def main() -> int:
    cfg, proc, allc = load()
    pipeline_pert = pd.read_csv(TAB / "perturbation_full.csv")
    tested_targets = set(pipeline_pert["target_gene"].astype(str))
    cc = cell_counts_table(cfg, proc, allc, tested_targets)
    qcw = qc_per_well_table(allc)
    bt, bg, rep, present = perturbation_tables(cfg, proc)
    log("== figures")
    fig_cellranger_metrics()
    fig_counts_and_retention(cc)
    fig_distributions(allc)
    fig_ecdfs(allc, proc)
    fig_knee()
    fig_qc_heatmap(qcw)
    fig_replicate_concordance(proc)
    fig_embeddings_processed(proc)
    fig_guide_summaries(proc, cc)
    fig_perturbation(bt, bg, rep, proc, present, cfg)
    fig_embedding_all_cells(allc, cfg)
    summary = {
        "processed_cells": int(proc.n_obs), "processed_genes": int(proc.n_vars), "all_cells": int(allc.n_obs),
        "targets_present_for_supplementary_test": {k: v for k, v in present.items()},
        "pipeline_hits_ntc": int(pipeline_pert["is_hit_ntc"].sum()), "pipeline_targets_tested": int(len(pipeline_pert)),
        "supp_pooled_hits_ntc": int(bt[(bt.well == "ALL") & (bt.control == "ntc")]["passes_default_hit_criteria"].sum()),
    }
    json.dump(summary, open(TAB / "supplementary_summary.json", "w"), indent=2)
    log(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
