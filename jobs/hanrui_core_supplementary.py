"""Supplementary tables and figures for the Hanrui Fang core-workflow run (h5ad mode).

Derived only from the pipeline's own outputs in results/Hanrui_fang/ (processed h5ad, the pre-QC
all-cells h5ad written by output.write_unfiltered_h5ad, tables/*.csv, resolved_config.yaml), the
combined input H5AD's guide metadata (scaffold / target), the Cell Ranger outputs and the guide
counting statistics. Statistics reuse perturbation.compare_groups (two-sided KS, one-sided MWU,
log2FC on de-logged lognorm with pseudocount 0.01) and perturbation.benjamini_hochberg; hit rule =
pipeline default (ks_fdr < fdr_alpha and log2fc < max_log2fc_for_hit).

FDR convention: the pipeline writes no log10FDR column; plots use -log10(clip(FDR)). Tables here store
the raw FDR (fdr_ks) and the explicitly named positive neg_log10_fdr = -log10(FDR).

Alias mapping (supplementary only; not a pipeline default): CEBPb->CEBPB, C6orf106->ILRUN, CCBL2->KYAT3,
'<GENE> (rsID)'->'<GENE>' so the target transcript of those design labels can be tested by symbol.
"""

from __future__ import annotations

import json
import re
import sys
import warnings
from pathlib import Path

import anndata as ad
import h5py
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
REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
RES = REPO / "results" / "Hanrui_fang"
FIG, TAB = RES / "figures", RES / "tables"
COMBINED = REPO / "work" / "Hanrui_fang" / "Hanrui_fang_combined.h5ad"
INPUTS = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_inputs")
QC_OUT = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc")
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
COND = {"HF011A": "HF011", "HF011B": "HF011", "HF012A": "HF012", "HF012B": "HF012"}
REP = {"HF011A": "A", "HF011B": "B", "HF012A": "A", "HF012B": "B"}
COLORS = {"HF011A": "#2a78d6", "HF011B": "#8ab4e8", "HF012A": "#eb6834", "HF012B": "#f3a98a", "ALL": "#52514e"}
CLASS_COLORS = {"targeting": "#2a78d6", "non-targeting": "#1baf7a", "ambiguous": "#eda100", "unassigned": "#9a9a9a", "QC-failed": "#e34948"}
ALIASES = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3"}
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


def symbol_of(label):
    return ALIASES.get(re.sub(r"\s*\(rs\d+\)\s*$", "", str(label)).strip(), re.sub(r"\s*\(rs\d+\)\s*$", "", str(label)).strip())


# -------------------------------------------------------------------------------------------- load


def load():
    cfg = yaml.safe_load(open(RES / "logs" / "resolved_config.yaml"))
    proc = ad.read_h5ad(RES / cfg["output"]["h5ad_name"])
    allc = ad.read_h5ad(RES / cfg["output"]["unfiltered_h5ad_name"])
    log("processed", proc.shape, "| all cells", allc.shape)
    assert allc.obs_names.is_unique and proc.obs_names.is_unique
    in_proc = allc.obs_names.isin(proc.obs_names)
    assert in_proc.sum() == proc.n_obs
    allc.obs["pipeline_qc_pass"] = in_proc
    cls = pd.Series(proc.obs["perturbation_class"].astype(str).to_numpy(), index=proc.obs_names)
    allc.obs["perturbation_class"] = allc.obs_names.map(cls).fillna("QC-failed").to_numpy()
    tg = pd.Series(proc.obs["target_gene"].astype(str).to_numpy(), index=proc.obs_names)
    allc.obs["target_gene"] = allc.obs_names.map(tg).fillna("QC-failed").to_numpy()
    # guide metadata from the combined input (var only)
    with h5py.File(COMBINED, "r") as f:
        gvar = ad.io.read_elem(f["var"]) if hasattr(ad, "io") else ad.experimental.read_elem(f["var"])
    gvar = gvar[gvar["feature_types"].astype(str) == "CRISPR Guide Capture"].copy()
    gvar.index = gvar["guide_id"].astype(str)
    log("guide var:", gvar.shape, dict(gvar["scaffold"].value_counts()))
    for a in (proc, allc):
        G = sp.csr_matrix(a.obsm["guide_counts"])
        names = list(a.uns["guide_names"]) if "guide_names" in a.uns else list(gvar.index)
        assert len(names) == G.shape[1]
        a.obs["guide_umi_total"] = np.asarray(G.sum(axis=1)).ravel()
        a.obs["n_guides_ge3"] = np.asarray((G >= 3).sum(axis=1)).ravel()
    return cfg, proc, allc, gvar


# -------------------------------------------------------------------------------------------- tables


def cell_counts_long(cfg, proc, allc, tested_targets):
    q = cfg["qc"]
    cr = pd.read_csv(TAB / "cellranger_metrics_per_well.csv") if (TAB / "cellranger_metrics_per_well.csv").exists() else None
    cr_cells = {r["well"]: int(str(r["Estimated Number of Cells"]).replace(",", "")) for _, r in cr.iterrows()} if cr is not None else {}
    a, p = allc.obs, proc.obs
    rows = []
    groups = {w: (a["well"].astype(str) == w, p["well"].astype(str) == w) for w in WELLS}
    groups["ALL"] = (pd.Series(True, index=a.index), pd.Series(True, index=p.index))
    for g, (ma, mp) in groups.items():
        sa, spp = a[ma], p[mp]
        cond = COND.get(g, "pooled"); rep = REP.get(g, "pooled")
        n_cr = sum(cr_cells.get(w, 0) for w in (WELLS if g == "ALL" else [g])) or len(sa)
        stages = []  # (stage, category, count)
        stages.append(("00_cellranger_called", "input cells (Cell Ranger)", n_cr))
        stages.append(("01_loaded", "cells loaded by pipeline", len(sa)))
        pre = sa["n_genes_by_counts"] >= q["min_genes_per_cell"]
        stages.append(("02_prefilter_min_genes_200", f"pass >= {q['min_genes_per_cell']} genes (permissive pass)", int(pre.sum())))
        stages.append(("02_prefilter_min_genes_200", f"fail < {q['min_genes_per_cell']} genes", int((~pre).sum())))
        fin = pre & (sa["n_genes_by_counts"] >= q["min_genes_final"])
        stages.append(("03_min_genes_final_1000", f"pass >= {q['min_genes_final']} genes", int(fin.sum())))
        stages.append(("03_min_genes_final_1000", f"fail < {q['min_genes_final']} genes (of permissive pass)", int((pre & ~fin).sum())))
        mt = fin & (sa["pct_counts_mt"] < q["max_pct_mt"])
        stages.append(("04_max_pct_mt_20", f"pass mt < {q['max_pct_mt']}% (final QC pass, derived)", int(mt.sum())))
        stages.append(("04_max_pct_mt_20", f"fail mt >= {q['max_pct_mt']}% (of gene-pass)", int((fin & ~mt).sum())))
        stages.append(("04_final_qc_pass_pipeline", "cells in processed object (pipeline QC pass)", int(sa["pipeline_qc_pass"].sum())))
        stages.append(("04_final_qc_pass_pipeline", "cells failing any expression QC", int((~sa["pipeline_qc_pass"]).sum())))
        stages.append(("05_guides", "guide-zero cells (0 guide UMIs, QC pass)", int((spp["guide_umi_total"] == 0).sum())))
        stages.append(("05_guides", "no guide detected (n_guides_detected == 0, QC pass)", int((spp["n_guides_detected"] == 0).sum())))
        for k in ("targeting", "non-targeting", "ambiguous", "unassigned"):
            stages.append(("05_guides", f"{k} cells", int((spp["perturbation_class"].astype(str) == k).sum())))
        stages.append(("06_clustering", "cells included in clustering", len(spp)))
        tested = (((spp["perturbation_class"].astype(str) == "targeting") & spp["target_gene"].astype(str).isin(tested_targets)) | (spp["perturbation_class"].astype(str) == "non-targeting"))
        stages.append(("07_perturbation_testing", "cells included in perturbation testing (targeting of tested targets + NTC)", int(tested.sum())))
        stages.append(("08_final", "final cells (processed object)", len(spp)))
        prev = {"00_cellranger_called": None, "01_loaded": n_cr, "02_prefilter_min_genes_200": len(sa), "03_min_genes_final_1000": int(pre.sum()),
                "04_max_pct_mt_20": int(fin.sum()), "04_final_qc_pass_pipeline": len(sa), "05_guides": len(spp), "06_clustering": len(spp),
                "07_perturbation_testing": len(spp), "08_final": len(spp)}
        for stage, cat, n in stages:
            pv = prev[stage]
            rows.append({"well": g, "condition": cond, "replicate": rep, "replicate_type": "unknown", "condition_status": "inferred",
                         "pipeline_stage": stage, "cell_category": cat, "cell_count": int(n),
                         "pct_of_input": round(100 * n / max(n_cr, 1), 3),
                         "pct_of_previous_stage": round(100 * n / pv, 3) if pv else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "cell_counts_before_after.csv", index=False)
    wide = df.pivot_table(index=["well", "condition", "replicate"], columns="cell_category", values="cell_count", aggfunc="first")
    wide.to_csv(TAB / "cell_counts_before_after_wide.csv")
    log("cell_counts_before_after:", df.shape)
    return df


def qc_per_well(allc):
    a = allc.obs
    rows = []
    for w in WELLS + ["ALL"]:
        m = pd.Series(True, index=a.index) if w == "ALL" else a["well"].astype(str) == w
        for stage, mm in (("before_qc", m), ("after_qc", m & a["pipeline_qc_pass"])):
            s = a[mm]
            rows.append({"well": w, "stage": stage, "n_cells": len(s),
                         **{f"median_{c}": float(s[c].median()) for c in ("total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "pct_counts_hb", "guide_umi_total", "n_guides_ge3")},
                         "median_genes_per_umi": float((s["n_genes_by_counts"] / s["total_counts"]).median())})
    df = pd.DataFrame(rows)
    df.to_csv(TAB / "qc_metrics_per_well_before_after.csv", index=False)
    return df


def dual_guide_diagnostics(proc, gvar, cfg):
    """Classify QC-passing cells by their strongest scaffold-A and scaffold-C guides (>= min_umi)."""
    min_umi = cfg["guides"]["min_umi"]
    G = sp.csr_matrix(proc.obsm["guide_counts"])
    names = np.array(list(proc.uns["guide_names"]), dtype=object)
    scaf = gvar.loc[names, "scaffold"].astype(str).to_numpy()
    tgt = gvar.loc[names, "target_gene_name"].astype(str).to_numpy()
    ntc = gvar.loc[names, "is_non_targeting"].astype(bool).to_numpy()

    def top(cols):
        sub = G[:, cols]
        idx = np.asarray(sub.argmax(axis=1)).ravel()
        val = np.asarray(sub.max(axis=1).todense()).ravel()
        return cols[idx], val

    A_cols, C_cols = np.where(scaf == "A")[0], np.where(scaf == "C")[0]
    a_idx, a_val = top(A_cols)
    c_idx, c_val = top(C_cols)
    has_a, has_c = a_val >= min_umi, c_val >= min_umi
    nA = np.asarray((G[:, A_cols] >= min_umi).sum(axis=1)).ravel()
    nC = np.asarray((G[:, C_cols] >= min_umi).sum(axis=1)).ravel()
    cat = np.full(G.shape[0], "no guide", dtype=object)
    both = has_a & has_c
    same_t = tgt[a_idx] == tgt[c_idx]
    a_ntc, c_ntc = ntc[a_idx], ntc[c_idx]
    cat[has_a & ~has_c] = "one strong guide (A only)"
    cat[~has_a & has_c] = "one strong guide (C only)"
    cat[both & same_t & ~a_ntc] = "two strong guides, same target"
    cat[both & same_t & a_ntc] = "two strong guides, both non-targeting"
    cat[both & ~same_t & (a_ntc ^ c_ntc)] = "two strong guides, targeting + non-targeting"
    cat[both & ~same_t & ~a_ntc & ~c_ntc] = "two strong guides, two different targets"
    multi = (nA > 1) | (nC > 1)
    obs = proc.obs
    df = pd.DataFrame({"well": obs["well"].astype(str).to_numpy(), "dual_guide_category": cat, "extra_guides_in_a_scaffold_class": multi,
                       "pipeline_class": obs["perturbation_class"].astype(str).to_numpy()})
    tab = df.groupby(["well", "dual_guide_category"]).size().unstack(fill_value=0).reindex(WELLS)
    tab.loc["ALL"] = tab.sum()
    tab.to_csv(TAB / "dual_guide_diagnostics_per_well.csv")
    cross = pd.crosstab(df["dual_guide_category"], df["pipeline_class"])
    cross.to_csv(TAB / "dual_guide_category_vs_pipeline_class.csv")
    extra = df.groupby("well")["extra_guides_in_a_scaffold_class"].sum().reindex(WELLS)
    log("dual-guide categories:\n" + tab.to_string()); log("cells with >1 strong guide within a scaffold class:", extra.to_dict())
    fig, ax = plt.subplots(figsize=(9, 4))
    bottom = np.zeros(len(WELLS))
    pal = ["#2a78d6", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#8ab4e8", "#f3a98a", "#9a9a9a"]
    for i, c in enumerate(tab.columns):
        ax.bar(WELLS, tab.loc[WELLS, c], bottom=bottom, color=pal[i % len(pal)], label=c)
        bottom += tab.loc[WELLS, c].to_numpy()
    ax.set_ylabel("QC-passing cells")
    ax.set_title(f"Dual-guide structure per well (strongest A and C guide, >= {min_umi} UMIs) — diagnostic only", fontsize=9)
    ax.legend(fontsize=6, frameon=False, loc="upper left", bbox_to_anchor=(1, 1))
    style(ax)
    fig.tight_layout()
    save(fig, "guides", "supp_dual_guide_categories_per_well")
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(cross.to_numpy(), cmap="Blues", aspect="auto")
    ax.set_xticks(range(cross.shape[1])); ax.set_xticklabels(cross.columns, fontsize=8)
    ax.set_yticks(range(cross.shape[0])); ax.set_yticklabels(cross.index, fontsize=7)
    for i in range(cross.shape[0]):
        for j in range(cross.shape[1]):
            ax.text(j, i, f"{cross.iloc[i, j]:,}", ha="center", va="center", fontsize=7, color="white" if cross.iloc[i, j] > cross.values.max() / 2 else "black")
    ax.set_title("Dual-guide category vs pipeline single-guide assignment class", fontsize=9)
    fig.tight_layout()
    save(fig, "guides", "supp_dual_guide_category_vs_pipeline_class")
    return tab


def _vec(proc, gene):
    X = proc.layers["lognorm"] if "lognorm" in proc.layers else proc.X
    col = X[:, proc.var_names.get_loc(gene)]
    return np.asarray(col.todense()).ravel() if sp.issparse(col) else np.asarray(col).ravel()


def perturbation_tables(cfg, proc):
    pc = cfg["perturbation"]
    alpha, max_lfc, min_cells, min_ctrl = pc["fdr_alpha"], pc["max_log2fc_for_hit"], pc["min_cells_per_target"], pc["min_control_cells"]
    obs = proc.obs
    klass = obs["perturbation_class"].astype(str).to_numpy(); tgt = obs["target_gene"].astype(str).to_numpy()
    gid = obs["guide_id"].astype(str).to_numpy(); well = obs["well"].astype(str).to_numpy()
    targets = sorted(set(tgt[klass == "targeting"]))
    present = {t: symbol_of(t) for t in targets if symbol_of(t) in proc.var_names}
    absent = sorted(set(targets) - set(present))
    log(f"{len(targets)} assigned targets; {len(present)} testable by symbol; absent from matrix: {absent}")
    cache = {}
    vec = lambda g: cache.setdefault(g, _vec(proc, g))
    n_assigned = {w: int(np.isin(klass[well == w], ["targeting", "non-targeting"]).sum()) for w in WELLS}
    n_assigned["ALL"] = int(np.isin(klass, ["targeting", "non-targeting"]).sum())

    def one(mp, mc, gene):
        if mp.sum() < min_cells or mc.sum() < min_ctrl:
            return None
        v = vec(gene)
        return compare_groups(v[mp], v[mc])

    bt, bg = [], []
    for t, gene in present.items():
        for w in WELLS + ["ALL"]:
            wm = np.ones(len(obs), bool) if w == "ALL" else well == w
            mp = (klass == "targeting") & (tgt == t) & wm
            m_ntc = (klass == "non-targeting") & wm
            m_oth = (klass == "targeting") & (tgt != t) & wm
            for ctrl, mc in (("ntc", m_ntc), ("other", m_oth)):
                r = one(mp, mc, gene)
                row = {"target_gene_name": t, "target_gene": gene, "alias_mapped": gene != t, "well": w, "condition": COND.get(w, "pooled"),
                       "replicate": REP.get(w, "pooled"), "control": ctrl, "n_guide_assigned_cells": n_assigned[w],
                       "n_targeting_cells": int(mp.sum()), "n_non_targeting_cells": int(m_ntc.sum()), "n_other_control_cells": int(m_oth.sum()),
                       "median_lognorm_targeting": float(np.median(vec(gene)[mp])) if mp.any() else np.nan,
                       "median_lognorm_control": float(np.median(vec(gene)[mc])) if mc.any() else np.nan}
                row.update(r if r is not None else {"skipped_reason": f"< {min_cells} targeting or < {min_ctrl} control cells"})
                bt.append(row)
            for g in sorted(set(gid[mp])):
                mg = mp & (gid == g)
                r = one(mg, m_ntc, gene)
                row = {"guide_id": g, "target_gene_name": t, "target_gene": gene, "well": w, "condition": COND.get(w, "pooled"), "replicate": REP.get(w, "pooled"),
                       "control": "ntc", "n_guide_assigned_cells": n_assigned[w], "n_targeting_cells": int(mg.sum()), "n_non_targeting_cells": int(m_ntc.sum()),
                       "n_other_control_cells": int(m_oth.sum())}
                row.update(r if r is not None else {"skipped_reason": f"< {min_cells} cells with this guide or < {min_ctrl} controls"})
                bg.append(row)

    def finish(rows, keys):
        df = pd.DataFrame(rows)
        df["fdr_ks"] = np.nan; df["fdr_mwu"] = np.nan
        for _, idx in df.groupby(keys, dropna=False).groups.items():
            df.loc[idx, "fdr_ks"] = benjamini_hochberg(df.loc[idx, "ks_pval"].to_numpy(float)) if "ks_pval" in df else np.nan
            df.loc[idx, "fdr_mwu"] = benjamini_hochberg(df.loc[idx, "mwu_pval_less"].to_numpy(float)) if "mwu_pval_less" in df else np.nan
        df["raw_pvalue_ks"] = df.get("ks_pval"); df["raw_pvalue_mwu_less"] = df.get("mwu_pval_less")
        df["neg_log10_fdr"] = -np.log10(np.clip(df["fdr_ks"].astype(float), 1e-300, 1))
        df["direction"] = np.select([df["log2fc"] < 0, df["log2fc"] > 0], ["down", "up"], "none")
        df.loc[df["log2fc"].isna(), "direction"] = "not_tested"
        df["default_hit"] = (df["fdr_ks"] < alpha) & (df["log2fc"] < max_lfc)
        df["hit_rule"] = f"fdr_ks < {alpha} and log2fc < {max_lfc} (pipeline default; BH within well x control)"
        df["fdr_convention"] = "fdr_ks = BH FDR of two-sided KS p (raw); neg_log10_fdr = -log10(fdr_ks), positive"
        return df

    bt = finish(bt, ["well", "control"]); bg = finish(bg, ["well"])
    bt.to_csv(TAB / "perturbation_expression_by_target.csv", index=False)
    bg.to_csv(TAB / "perturbation_expression_by_guide.csv", index=False)
    rows = []
    for t, gene in present.items():
        sub = bt[(bt.target_gene_name == t) & (bt.control == "ntc") & (bt.well != "ALL")]
        tested = sub[sub["log2fc"].notna()]
        pooled = bt[(bt.target_gene_name == t) & (bt.control == "ntc") & (bt.well == "ALL")].iloc[0]
        row = {"target_gene_name": t, "target_gene": gene, "n_wells_with_targeting_cells": int((sub["n_targeting_cells"] > 0).sum()),
               "n_wells_tested": int(len(tested)), "n_wells_consistent_direction_with_pooled": int((np.sign(tested["log2fc"]) == np.sign(pooled["log2fc"])).sum()) if np.isfinite(pooled["log2fc"]) else np.nan,
               "n_wells_passing_fdr_0.05_and_down": int(tested["default_hit"].sum()), "pooled_log2fc": pooled["log2fc"], "pooled_fdr_ks": pooled["fdr_ks"],
               "replicate_type": "unknown (well-level / capture-level comparison, not confirmed biological replicates)"}
        for w in WELLS:
            r = sub[sub.well == w]
            row[f"log2fc_{w}"] = float(r["log2fc"].iloc[0]) if len(r) else np.nan
            row[f"fdr_ks_{w}"] = float(r["fdr_ks"].iloc[0]) if len(r) else np.nan
            row[f"n_targeting_{w}"] = int(r["n_targeting_cells"].iloc[0]) if len(r) else 0
        n = row["n_wells_tested"]; k = row["n_wells_passing_fdr_0.05_and_down"]
        row["reproducibility"] = ("reproducible across wells (exploratory; replicate type unconfirmed)" if n >= 2 and k == n
                                  else "partially reproducible (exploratory)" if k > 0 else "not significant in any well" if n >= 2 else "insufficient wells")
        rows.append(row)
    rep = pd.DataFrame(rows)
    rep.to_csv(TAB / "perturbation_replicate_summary.csv", index=False)
    # response layers table
    pooled_ntc = bt[(bt.well == "ALL") & (bt.control == "ntc")]
    layers = {"guide_assigned_cells": n_assigned["ALL"], "targeting_cells": int((klass == "targeting").sum()),
              "targeting_cells_of_targets_with_measurable_depletion (pooled default hit)": int(pooled_ntc.loc[pooled_ntc.default_hit, "n_targeting_cells"].sum()),
              "targets_assigned": len(targets), "targets_testable_by_symbol": len(present), "targets_with_significant_depletion_pooled": int(pooled_ntc.default_hit.sum())}
    pd.DataFrame([layers]).T.reset_index().rename(columns={"index": "layer", 0: "count"}).to_csv(TAB / "perturbation_response_layers.csv", index=False)
    log("perturbation tables", bt.shape, bg.shape, rep.shape, layers)
    return bt, bg, rep, present


# -------------------------------------------------------------------------------------------- QC figures


def fig_cellranger():
    m = pd.read_csv(TAB / "cellranger_metrics_per_well.csv")
    cols = ["Estimated Number of Cells", "Mean Reads per Cell", "Median Genes per Cell", "Median UMI Counts per Cell",
            "Sequencing Saturation", "Fraction Reads in Cells", "Reads Mapped Confidently to Transcriptome", "Valid Barcodes"]
    fig, axes = plt.subplots(2, 4, figsize=(15, 6))
    for ax, c in zip(axes.ravel(), cols):
        vals = [float(str(v).replace(",", "").replace("%", "")) for v in m[c]]
        ax.bar(m["well"], vals, color=[COLORS[w] for w in m["well"]]); ax.set_title(c, fontsize=9); ax.tick_params(axis="x", labelsize=8); style(ax)
    fig.suptitle("Cell Ranger metrics per well", fontsize=11); fig.tight_layout(); save(fig, "qc", "supp_cellranger_metrics_per_well")


def fig_counts(cc):
    w = cc[(cc.well != "ALL")]
    inp = w[w.cell_category == "input cells (Cell Ranger)"].set_index("well")["cell_count"].reindex(WELLS)
    loaded = w[w.cell_category == "cells loaded by pipeline"].set_index("well")["cell_count"].reindex(WELLS)
    passed = w[w.cell_category == "cells in processed object (pipeline QC pass)"].set_index("well")["cell_count"].reindex(WELLS)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4)); x = np.arange(4)
    axes[0].bar(x - 0.2, inp, 0.4, color="#9a9a9a", label="Cell Ranger called"); axes[0].bar(x + 0.2, loaded, 0.4, color=[COLORS[k] for k in WELLS], label="loaded")
    axes[0].set_xticks(x); axes[0].set_xticklabels(WELLS); axes[0].set_ylabel("cells"); axes[0].set_title("Input cells per well"); axes[0].legend(fontsize=8, frameon=False); style(axes[0])
    axes[1].bar(x - 0.2, loaded, 0.4, color="#c8c7c1", label="before QC"); axes[1].bar(x + 0.2, passed, 0.4, color=[COLORS[k] for k in WELLS], label="after default QC")
    for xi, k in zip(x, WELLS):
        axes[1].text(xi + 0.2, passed[k], f"{100 * passed[k] / loaded[k]:.1f}%", ha="center", va="bottom", fontsize=8)
    axes[1].set_xticks(x); axes[1].set_xticklabels(WELLS); axes[1].set_ylabel("cells"); axes[1].set_title("Cells before vs after pipeline default QC (pooled: %s -> %s)" % (f"{int(loaded.sum()):,}", f"{int(passed.sum()):,}"), fontsize=9)
    axes[1].legend(fontsize=8, frameon=False); style(axes[1]); fig.tight_layout(); save(fig, "qc", "supp_cell_counts_before_after_qc")


def fig_dists_and_ecdfs(allc, proc):
    a = allc.obs
    specs = [("total_counts", "Total UMIs", True), ("n_genes_by_counts", "Detected genes", True), ("pct_counts_mt", "Mitochondrial %", False),
             ("pct_counts_ribo", "Ribosomal %", False), ("pct_counts_hb", "Haemoglobin %", False)]
    for col, label, logx in specs:
        fig, axes = plt.subplots(1, 5, figsize=(20, 3.6))
        for ax, w in zip(axes, WELLS + ["ALL"]):
            s = a if w == "ALL" else a[a.well.astype(str) == w]
            v = s[col].to_numpy(float)
            if logx:
                pos = v[v > 0]; bins = np.logspace(np.log10(max(pos.min(), 1)), np.log10(pos.max() + 1), 60); ax.set_xscale("log")
            else:
                bins = np.linspace(0, max(np.nanpercentile(v, 99.5) * 1.1, 1e-3), 60)
            ax.hist(v, bins=bins, color="#c8c7c1", label="before QC", histtype="stepfilled")
            ax.hist(v[s.pipeline_qc_pass.to_numpy()], bins=bins, color=COLORS[w], alpha=0.85, label="after QC", histtype="stepfilled")
            ax.set_title(w if w == "ALL" else f"{w} ({COND[w]}, capture {REP[w]})", fontsize=9); ax.set_xlabel(label); ax.set_ylabel("cells"); ax.legend(fontsize=7, frameon=False); style(ax)
        fig.suptitle(f"{label}: before vs after pipeline default QC (per well + pooled)", fontsize=10); fig.tight_layout(); save(fig, "qc", f"supp_dist_{col}_before_after")
    for col, label, logx in specs[:4] + [("guide_umi_total", "Guide UMIs per cell", True), ("n_guides_ge3", "Guides detected per cell (>= 3 UMIs)", False)]:
        fig, axes = plt.subplots(1, 5, figsize=(20, 3.6), sharey=True)
        for ax, w in zip(axes, WELLS + ["ALL"]):
            s = a if w == "ALL" else a[a.well.astype(str) == w]
            ecdf(ax, s[col], "before QC", "#7a7975", logx, "--"); ecdf(ax, s.loc[s.pipeline_qc_pass, col], "after QC", COLORS[w], logx)
            ax.set_title(w, fontsize=9); ax.set_xlabel(label + (" + 1" if logx else "")); ax.legend(fontsize=7, frameon=False, loc="lower right"); style(ax)
        axes[0].set_ylabel("ECDF"); fig.suptitle(f"ECDF of {label}: before vs after QC", fontsize=10); fig.tight_layout(); save(fig, "qc", f"supp_ecdf_{col}_before_after")
    fig, axes = plt.subplots(1, 4, figsize=(16, 4)); rng = np.random.default_rng(0)
    for ax, w in zip(axes, WELLS):
        s = a[a.well.astype(str) == w]; s = s.iloc[rng.choice(len(s), min(len(s), 25000), replace=False)]; ok = s.pipeline_qc_pass.to_numpy()
        ax.scatter(s.total_counts[ok], s.n_genes_by_counts[ok], s=2, alpha=0.3, color=COLORS[w], linewidths=0, label="pass", rasterized=True)
        ax.scatter(s.total_counts[~ok], s.n_genes_by_counts[~ok], s=4, alpha=0.7, color="#e34948", linewidths=0, label="fail", rasterized=True)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("Total UMIs"); ax.set_ylabel("Detected genes"); ax.set_title(w, fontsize=9); ax.legend(fontsize=7, frameon=False, markerscale=4); style(ax)
    fig.suptitle("UMIs vs detected genes (25k cells/well shown; red = failed default QC)", fontsize=10); fig.tight_layout(); save(fig, "qc", "supp_umi_vs_genes_per_well")


def fig_knee():
    fig, axes = plt.subplots(1, 4, figsize=(16, 3.8), sharey=True)
    for ax, w in zip(axes, WELLS):
        raw = sc.read_10x_h5(INPUTS / "cellranger" / w / "raw_feature_bc_matrix.h5"); tot = np.asarray(raw.X.sum(axis=1)).ravel(); tot = np.sort(tot[tot > 0])[::-1]
        n_called = len(pd.read_csv(INPUTS / "cellranger" / w / "filtered_feature_bc_matrix" / "barcodes.tsv.gz", header=None))
        ax.plot(np.arange(1, tot.size + 1), tot, color=COLORS[w], linewidth=1.4); ax.axvline(n_called, color="#e34948", linestyle="--", linewidth=1, label=f"Cell Ranger cells = {n_called:,}")
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("barcode rank"); ax.set_title(w, fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax); del raw
    axes[0].set_ylabel("total UMIs"); fig.suptitle("Barcode-rank (knee) plots from raw_feature_bc_matrix.h5", fontsize=10); fig.tight_layout(); save(fig, "qc", "supp_barcode_rank_knee_per_well")


def fig_heatmap(qcw):
    after = qcw[(qcw.stage == "after_qc") & (qcw.well != "ALL")].set_index("well"); cols = [c for c in after.columns if c.startswith("median_")]
    mat = after[cols].astype(float); z = (mat - mat.mean()) / mat.std(ddof=0).replace(0, 1)
    fig, ax = plt.subplots(figsize=(10, 3.2)); im = ax.imshow(z.to_numpy(), cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(cols))); ax.set_xticklabels([c.replace("median_", "") for c in cols], rotation=35, ha="right", fontsize=8); ax.set_yticks(range(len(after))); ax.set_yticklabels(after.index)
    for i in range(len(after)):
        for j in range(len(cols)):
            ax.text(j, i, f"{mat.iloc[i, j]:.3g}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="z across wells"); ax.set_title("Per-well QC medians after default QC", fontsize=9); fig.tight_layout(); save(fig, "qc", "supp_per_well_qc_heatmap")


def fig_ab_concordance(proc):
    X = proc.layers["lognorm"] if "lognorm" in proc.layers else proc.X; well = proc.obs.well.astype(str).to_numpy()
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, c in zip(axes, ("HF011", "HF012")):
        ma = np.asarray(X[well == f"{c}A"].mean(axis=0)).ravel(); mb = np.asarray(X[well == f"{c}B"].mean(axis=0)).ravel(); keep = (ma > 0) | (mb > 0)
        r = np.corrcoef(ma[keep], mb[keep])[0, 1]; ax.scatter(ma[keep], mb[keep], s=3, alpha=0.4, color=COLORS[f"{c}A"], linewidths=0, rasterized=True)
        lim = max(ma.max(), mb.max()); ax.plot([0, lim], [0, lim], color="#e34948", linewidth=1); ax.set_xlabel(f"{c}A mean lognorm"); ax.set_ylabel(f"{c}B mean lognorm")
        ax.set_title(f"{c}: well A vs B gene means, r = {r:.4f}", fontsize=9); style(ax)
    fig.suptitle("A/B well-level concordance (replicate type unconfirmed)", fontsize=10); fig.tight_layout(); save(fig, "qc", "supp_ab_well_concordance_gene_means")


def _scatter_cat(ax, xy, labels, palette, title, order=None, max_pts=80000):
    rng = np.random.default_rng(0); idx = rng.choice(xy.shape[0], min(xy.shape[0], max_pts), replace=False); xy = xy[idx]; labels = np.asarray(labels)[idx]
    for k in (order or list(pd.unique(labels))):
        m = labels == k
        if m.any():
            ax.scatter(xy[m, 0], xy[m, 1], s=2, alpha=0.5, color=palette.get(k, "#9a9a9a"), linewidths=0, label=f"{k} ({m.sum():,})", rasterized=True)
    ax.set_title(title, fontsize=9); ax.set_xticks([]); ax.set_yticks([]); ax.legend(fontsize=6, frameon=False, markerscale=5)


def fig_embeddings(proc, allc, cfg):
    cond_pal = {"HF011": "#2a78d6", "HF012": "#eb6834"}
    for key, name in (("X_pca", "pca"), ("X_umap", "umap")):
        xy = np.asarray(proc.obsm[key])[:, :2]
        fig, axes = plt.subplots(1, 4, figsize=(20, 4.6))
        _scatter_cat(axes[0], xy, proc.obs.well.astype(str), COLORS, f"{name.upper()} by well", WELLS)
        _scatter_cat(axes[1], xy, proc.obs.condition.astype(str), cond_pal, f"{name.upper()} by inferred condition")
        _scatter_cat(axes[2], xy, np.full(proc.n_obs, "QC pass"), {"QC pass": "#2a78d6"}, f"{name.upper()} by QC status (pipeline embedding: all cells pass)")
        _scatter_cat(axes[3], xy, proc.obs.perturbation_class.astype(str), CLASS_COLORS, f"{name.upper()} by guide assignment class", ["ambiguous", "unassigned", "targeting", "non-targeting"])
        fig.tight_layout(); save(fig, "clustering", f"supp_{name}_by_well_condition_qcstatus_class")
        if name == "umap":
            fig, ax = plt.subplots(figsize=(5.5, 5)); _scatter_cat(ax, xy, proc.obs.perturbation_class.astype(str), CLASS_COLORS, "UMAP: guide assignment category", ["ambiguous", "unassigned", "targeting", "non-targeting"]); fig.tight_layout(); save(fig, "guides", "supp_umap_guide_assignment_category")
            fig, axes = plt.subplots(1, 4, figsize=(18, 4.4))
            for ax, w in zip(axes, WELLS):
                m = (proc.obs.well.astype(str) == w).to_numpy(); ax.scatter(xy[~m, 0], xy[~m, 1], s=1, color="#e0dfda", linewidths=0, rasterized=True); ax.scatter(xy[m, 0], xy[m, 1], s=1.5, color=COLORS[w], linewidths=0, rasterized=True)
                ax.set_title(f"{w} ({m.sum():,} cells)", fontsize=9); ax.set_xticks([]); ax.set_yticks([])
            fig.suptitle("UMAP per well (grey = other wells)", fontsize=10); fig.tight_layout(); save(fig, "clustering", "supp_umap_facet_by_well")
    # all-cells supplementary embedding (pass + fail) with pipeline-like defaults
    cc = cfg["cluster"]; a = allc.copy(); a.X = a.layers["counts"].copy() if "counts" in a.layers else a.X
    sc.pp.filter_genes(a, min_cells=3); sc.pp.normalize_total(a, target_sum=cc.get("target_sum")); sc.pp.log1p(a)
    sc.pp.highly_variable_genes(a, n_top_genes=min(cc["n_top_genes"], a.n_vars)); a = a[:, a.var.highly_variable].copy(); sc.pp.scale(a, max_value=cc["scale_max_value"])
    sc.tl.pca(a, n_comps=cc["n_pcs"], svd_solver="arpack", random_state=0); sc.pp.neighbors(a, n_neighbors=cc["n_neighbors"], n_pcs=cc["n_pcs"], random_state=0); sc.tl.umap(a, min_dist=cc["umap_min_dist"], random_state=0)
    qc_status = np.where(a.obs.pipeline_qc_pass, "QC pass", "QC fail")
    for key, name in (("X_pca", "pca"), ("X_umap", "umap")):
        xy = np.asarray(a.obsm[key])[:, :2]; fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
        _scatter_cat(axes[0], xy, a.obs.well.astype(str), COLORS, f"{name.upper()} (all cells) by well", WELLS); _scatter_cat(axes[1], xy, a.obs.condition.astype(str), cond_pal, f"{name.upper()} by inferred condition")
        _scatter_cat(axes[2], xy, qc_status, {"QC pass": "#2a78d6", "QC fail": "#e34948"}, f"{name.upper()} by pipeline QC status", ["QC pass", "QC fail"])
        fig.suptitle(f"Supplementary {name.upper()} of all {a.n_obs:,} loaded cells (pipeline-like defaults; not the pipeline embedding)", fontsize=10); fig.tight_layout(); save(fig, "clustering", f"supp_{name}_all_cells_by_well_condition_qcstatus")


# -------------------------------------------------------------------------------------------- guide figures


def fig_guides(proc, gvar, cfg):
    obs = proc.obs; det_thr = cfg["guides"]["detection_threshold"]
    # funnel + retention fractions from the counting statistics
    rows = []
    for w in WELLS:
        st = json.load(open(QC_OUT / "guide_counts" / w / f"{w}_guide_counting_stats.json"))["sample"]
        rows.append({"well": w, "reads_total": st["reads_total"], "reads_with_tso": st["reads_with_tso"], "reads_with_scaffold_anchor": st["reads_with_scaffold_anchor"],
                     "reads_spacer_matched_exact": st["reads_spacer_matched"] - st["reads_spacer_matched_via_shift"], "reads_spacer_matched_total": st["reads_spacer_matched"],
                     "reads_valid_gex_barcode": st["reads_matched_barcode_in_gex"], "reads_valid_umi": st["reads_matched_barcode_in_gex"] - st["reads_invalid_umi"],
                     "unique_cell_guide_umis": st["unique_cell_guide_umis"], "reads_unmatched_spacer": st["reads_spacer_unmatched"], "reads_barcode_not_in_gex": st["reads_matched_barcode_not_in_gex"],
                     "frac_valid_barcode_of_matched": st["frac_matched_reads_in_gex_barcodes"], "frac_valid_umi_of_barcode_matched": 1 - st["reads_invalid_umi"] / max(st["reads_matched_barcode_in_gex"], 1),
                     "frac_exact_spacer_match_of_total": (st["reads_spacer_matched"] - st["reads_spacer_matched_via_shift"]) / st["reads_total"], "frac_scaffold_A_of_anchored": st["frac_anchored_reads_scaffold_A"], "frac_scaffold_C_of_anchored": st["frac_anchored_reads_scaffold_C"]})
    fun = pd.DataFrame(rows); fun.to_csv(TAB / "guide_read_retention_funnel.csv", index=False)
    steps = ["reads_total", "reads_with_scaffold_anchor", "reads_spacer_matched_total", "reads_valid_gex_barcode", "reads_valid_umi", "unique_cell_guide_umis"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    for w in WELLS:
        r = fun[fun.well == w].iloc[0]; axes[0].plot(range(len(steps)), [r[s] / r["reads_total"] for s in steps], marker="o", color=COLORS[w], label=w)
    axes[0].set_xticks(range(len(steps))); axes[0].set_xticklabels([s.replace("reads_", "").replace("_", " ") for s in steps], rotation=30, ha="right", fontsize=8); axes[0].set_ylabel("fraction of total reads"); axes[0].set_title("Guide read retention funnel", fontsize=9); axes[0].legend(fontsize=7, frameon=False); style(axes[0])
    fr = fun.set_index("well")[["frac_valid_barcode_of_matched", "frac_valid_umi_of_barcode_matched", "frac_exact_spacer_match_of_total", "frac_scaffold_A_of_anchored", "frac_scaffold_C_of_anchored"]]
    fr.plot.bar(ax=axes[1], color=["#2a78d6", "#1baf7a", "#eda100", "#4a3aa7", "#e87ba4"], width=0.8); axes[1].set_ylim(0, 1.05); axes[1].set_ylabel("fraction"); axes[1].set_title("Valid barcode / valid UMI / exact match / scaffold fractions", fontsize=9); axes[1].legend(fontsize=6, frameon=False); axes[1].tick_params(axis="x", rotation=0); style(axes[1])
    fig.tight_layout(); save(fig, "guides", "supp_guide_read_funnel_and_retention_fractions")
    # per-guide abundance, guide UMIs/cell, guides detected, top/second
    G = sp.csr_matrix(proc.obsm["guide_counts"]); names = np.array(list(proc.uns["guide_names"]), dtype=object); scaf = gvar.loc[names, "scaffold"].astype(str).to_numpy()
    fig, axes = plt.subplots(1, 4, figsize=(20, 4))
    umis = np.asarray(G.sum(axis=0)).ravel(); order = np.argsort(-umis)
    axes[0].bar(range(len(umis)), umis[order] + 1, color=[{"A": "#2a78d6", "C": "#eb6834"}.get(s, "#9a9a9a") for s in scaf[order]], width=1.0); axes[0].set_yscale("log"); axes[0].set_xlabel("designed guides ranked"); axes[0].set_ylabel("UMIs in QC-passing cells + 1"); axes[0].set_title(f"Per-guide abundance (blue A, orange C, grey unknown); {int((umis > 0).sum())}/{len(umis)} observed", fontsize=8); style(axes[0])
    for w in WELLS:
        m = obs.well.astype(str) == w; ecdf(axes[1], obs.loc[m, "guide_umi_total"], w, COLORS[w], True); axes[2].hist(obs.loc[m, "n_guides_detected"].clip(upper=10), bins=np.arange(-0.5, 11.5), histtype="step", linewidth=1.5, color=COLORS[w], label=f"{w} (mean {obs.loc[m, 'n_guides_detected'].mean():.2f})")
    axes[1].set_xlabel("guide UMIs per cell + 1"); axes[1].set_ylabel("ECDF"); axes[1].set_title("Guide UMIs per cell", fontsize=9); axes[1].legend(fontsize=7, frameon=False); style(axes[1])
    axes[2].set_xlabel(f"guides detected per cell (> {det_thr} UMIs, capped at 10)"); axes[2].set_ylabel("cells"); axes[2].set_title("Guides detected per cell / MOI", fontsize=9); axes[2].legend(fontsize=7, frameon=False); style(axes[2])
    rng = np.random.default_rng(0); idx = rng.choice(proc.n_obs, min(proc.n_obs, 60000), replace=False); k = obs.perturbation_class.astype(str).to_numpy()[idx]
    for cl in ("ambiguous", "targeting", "non-targeting", "unassigned"):
        m = k == cl
        if m.any():
            axes[3].scatter(obs.top_guide_count.to_numpy()[idx][m] + 1, obs.second_guide_count.to_numpy()[idx][m] + 1, s=2, alpha=0.4, color=CLASS_COLORS[cl], linewidths=0, label=f"{cl} ({m.sum():,} shown)", rasterized=True)
    lim = [1, obs.top_guide_count.max() + 1]; axes[3].plot(lim, lim, color="#7a7975", linewidth=0.8); axes[3].plot(lim, [l / 2 for l in lim], color="#e34948", linestyle="--", linewidth=0.8, label="top = 2 x second")
    axes[3].set_xscale("log"); axes[3].set_yscale("log"); axes[3].set_xlabel("top guide UMIs + 1"); axes[3].set_ylabel("second guide UMIs + 1"); axes[3].set_title("Top vs second guide (dominance rule)", fontsize=9); axes[3].legend(fontsize=6, frameon=False, markerscale=4); style(axes[3])
    fig.tight_layout(); save(fig, "guides", "supp_guide_abundance_umis_moi_top_vs_second")
    # categories per well, ntc vs targeting, scaffold A/C per cell, representation by target, barcode matching
    fig, axes = plt.subplots(1, 4, figsize=(20, 4.2))
    ct = pd.crosstab(obs.well.astype(str), obs.perturbation_class.astype(str)).reindex(WELLS); bottom = np.zeros(4)
    for cl in ("targeting", "non-targeting", "ambiguous", "unassigned"):
        if cl in ct:
            axes[0].bar(WELLS, ct[cl], bottom=bottom, color=CLASS_COLORS[cl], label=cl); bottom += ct[cl].to_numpy()
    axes[0].set_ylabel("QC-passing cells"); axes[0].set_title("Guide assignment categories per well", fontsize=9); axes[0].legend(fontsize=7, frameon=False); style(axes[0])
    x = np.arange(4); axes[1].bar(x - 0.2, ct.get("targeting", 0), 0.4, color=CLASS_COLORS["targeting"], label="targeting"); axes[1].bar(x + 0.2, ct.get("non-targeting", 0), 0.4, color=CLASS_COLORS["non-targeting"], label="non-targeting")
    axes[1].set_xticks(x); axes[1].set_xticklabels(WELLS); axes[1].set_ylabel("cells"); axes[1].set_title("Non-targeting vs targeting cells", fontsize=9); axes[1].legend(fontsize=7, frameon=False); style(axes[1])
    umA = np.asarray(G[:, scaf == "A"].sum(axis=1)).ravel(); umC = np.asarray(G[:, scaf == "C"].sum(axis=1)).ravel(); frac = umA / np.maximum(umA + umC, 1)
    for w in WELLS:
        m = (obs.well.astype(str) == w).to_numpy(); axes[2].hist(frac[m & ((umA + umC) > 0)], bins=40, histtype="step", linewidth=1.5, color=COLORS[w], label=w)
    axes[2].set_xlabel("fraction of guide UMIs from scaffold-A guides"); axes[2].set_ylabel("cells"); axes[2].set_title("Scaffold A/C UMI distribution per cell", fontsize=9); axes[2].legend(fontsize=7, frameon=False); style(axes[2])
    tt = pd.crosstab(obs.loc[obs.perturbation_class.isin(["targeting", "non-targeting"]), "target_gene"].astype(str), obs.well.astype(str)).reindex(columns=WELLS).fillna(0); tt = tt.loc[tt.sum(axis=1).sort_values(ascending=False).index]; bottom = np.zeros(len(tt))
    for w in WELLS:
        axes[3].bar(range(len(tt)), tt[w], bottom=bottom, color=COLORS[w], label=w); bottom += tt[w].to_numpy()
    axes[3].set_xticks(range(len(tt))); axes[3].set_xticklabels(tt.index, rotation=90, fontsize=5); axes[3].set_ylabel("assigned cells"); axes[3].set_title("Guide representation by target (assigned cells)", fontsize=9); axes[3].legend(fontsize=7, frameon=False); style(axes[3])
    fig.tight_layout(); save(fig, "guides", "supp_assignment_categories_ntc_scaffold_target_representation")
    ov = pd.read_csv(TAB / "guide_gex_overlap_per_well.csv")
    fig, ax = plt.subplots(figsize=(6, 3.6)); x = np.arange(4)
    ax.bar(x - 0.2, ov.gex_cells, 0.4, color="#9a9a9a", label="GEX cells"); ax.bar(x + 0.2, ov.shared_barcodes, 0.4, color=[COLORS[w] for w in ov.well], label="shared with guide matrix")
    for xi, r in zip(x, ov.itertuples()):
        ax.text(xi + 0.2, r.shared_barcodes, f"{100 * r.frac_gex_with_guide_row:.1f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x); ax.set_xticklabels(ov.well); ax.set_ylabel("barcodes"); ax.set_title("Guide/GEX barcode matching per well", fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax); fig.tight_layout(); save(fig, "guides", "supp_guide_gex_barcode_matching_per_well")


# -------------------------------------------------------------------------------------------- perturbation figures


def fig_perturbation(bt, bg, rep, proc, present, cfg):
    alpha = cfg["perturbation"]["fdr_alpha"]
    pooled = bt[(bt.well == "ALL") & (bt.control == "ntc") & bt.log2fc.notna()].copy(); pooled_o = bt[(bt.well == "ALL") & (bt.control == "other") & bt.log2fc.notna()].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for ax, df, ttl in zip(axes, (pooled, pooled_o), ("vs non-targeting (primary)", "vs other-target cells (secondary)")):
        hit = df.default_hit.to_numpy(bool); ax.scatter(df.log2fc[~hit], df.neg_log10_fdr[~hit], s=18, color="#9a9a9a", label="not hit"); ax.scatter(df.log2fc[hit], df.neg_log10_fdr[hit], s=18, color="#2a78d6", label=f"hit (KS FDR < {alpha} & log2FC < 0)")
        for _, r in df.iterrows():
            ax.annotate(r.target_gene_name, (r.log2fc, r.neg_log10_fdr), fontsize=6, xytext=(2, 2), textcoords="offset points")
        ax.axhline(-np.log10(alpha), color="#e34948", linestyle="--", linewidth=1); ax.axvline(0, color="#7a7975", linewidth=0.8); ax.set_xlabel("log2FC (target transcript)"); ax.set_ylabel("-log10(BH FDR, two-sided KS)"); ax.set_title(f"Pooled wells, {ttl}", fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax)
    fig.suptitle("Volcano: target-transcript depletion (pooled; alias-mapped labels included)", fontsize=10); fig.tight_layout(); save(fig, "perturbation", "supp_volcano_log2fc_vs_neglog10fdr")
    df = pooled.sort_values("log2fc"); order = df.target_gene_name.tolist()
    fig, ax = plt.subplots(figsize=(11, 4)); ax.bar(range(len(df)), df.log2fc, color=np.where(df.default_hit, "#2a78d6", "#9a9a9a")); ax.set_xticks(range(len(df))); ax.set_xticklabels(df.target_gene_name, rotation=90, fontsize=7); ax.set_ylabel("log2FC vs NTC (pooled)"); ax.set_title("Target-expression waterfall (blue = default hit)", fontsize=9); style(ax); fig.tight_layout(); save(fig, "perturbation", "supp_waterfall_target_log2fc")
    perwell = bt[(bt.well != "ALL") & (bt.control == "ntc")]
    for col, name, cmap, vlim in (("log2fc", "log2FC", "RdBu_r", (-4, 4)), ("neg_log10_fdr", "-log10(FDR)", "Blues", (0, 20))):
        piv = perwell.pivot(index="target_gene_name", columns="well", values=col).reindex(index=order, columns=WELLS)
        fig, ax = plt.subplots(figsize=(6, 0.28 * len(piv) + 1.5)); im = ax.imshow(piv.to_numpy(float), cmap=cmap, vmin=vlim[0], vmax=vlim[1], aspect="auto"); ax.set_yticks(range(len(piv))); ax.set_yticklabels(piv.index, fontsize=7); ax.set_xticks(range(4)); ax.set_xticklabels(WELLS, fontsize=8)
        fig.colorbar(im, ax=ax, label=name); ax.set_title(f"{name} by well (targeting vs NTC within well)", fontsize=9); fig.tight_layout(); save(fig, "perturbation", f"supp_heatmap_{col}_by_well")
    fig, ax = plt.subplots(figsize=(5.5, 3.8))
    for w in WELLS:
        ecdf(ax, perwell.loc[perwell.well == w, "neg_log10_fdr"], f"{w} ({COND[w]})", COLORS[w])
    ecdf(ax, pooled.neg_log10_fdr, "pooled", "#52514e", ls="--"); ax.axvline(-np.log10(alpha), color="#e34948", linestyle="--", linewidth=1); ax.set_xlabel("-log10(BH FDR) across targets"); ax.set_ylabel("ECDF"); ax.legend(fontsize=7, frameon=False); style(ax); fig.tight_layout(); save(fig, "perturbation", "supp_ecdf_neglog10fdr_by_well")
    obs = proc.obs; klass = obs.perturbation_class.astype(str).to_numpy(); tgt = obs.target_gene.astype(str).to_numpy(); well = obs.well.astype(str).to_numpy()
    picks = order[:8] + order[-4:]
    for t in picks:
        gene = present[t]; v = _vec(proc, gene)
        for ctrl in ("ntc", "other"):
            fig, axes = plt.subplots(1, 5, figsize=(20, 3.4), sharey=True)
            for ax, w in zip(axes, WELLS + ["ALL"]):
                wm = np.ones(len(obs), bool) if w == "ALL" else well == w
                ecdf(ax, v[wm & (klass == "targeting") & (tgt == t)], "targeting", "#2a78d6")
                if ctrl == "ntc":
                    ecdf(ax, v[wm & (klass == "non-targeting")], "non-targeting", "#1baf7a")
                else:
                    ecdf(ax, v[wm & (klass == "targeting") & (tgt != t)], "other-target controls", "#eda100", ls=":")
                ax.set_title(w if w == "ALL" else f"{w} ({COND[w]}, capture {REP[w]})", fontsize=9); ax.set_xlabel(f"{gene} lognorm"); ax.legend(fontsize=6, frameon=False, loc="lower right"); style(ax)
            axes[0].set_ylabel("ECDF"); fig.suptitle(f"Target transcript {gene} (design label {t}): targeting vs {'non-targeting' if ctrl == 'ntc' else 'other-target'} controls", fontsize=10); fig.tight_layout()
            save(fig, "perturbation", f"supp_ecdf_target_expression_{ctrl}_{re.sub(r'[^A-Za-z0-9]+', '_', t)}")
    fig, axes = plt.subplots(1, 3, figsize=(18, 4))
    cnt = perwell.pivot(index="target_gene_name", columns="well", values="n_targeting_cells").reindex(index=order, columns=WELLS).fillna(0); bottom = np.zeros(len(cnt))
    for w in WELLS:
        axes[0].bar(range(len(cnt)), cnt[w], bottom=bottom, color=COLORS[w], label=w); bottom += cnt[w].to_numpy()
    axes[0].set_xticks(range(len(cnt))); axes[0].set_xticklabels(cnt.index, rotation=90, fontsize=7); axes[0].set_ylabel("targeting cells"); axes[0].set_title("Targeting-cell count per target (stacked by well)", fontsize=9); axes[0].legend(fontsize=7, frameon=False); style(axes[0])
    ga = bt[(bt.control == "ntc")].groupby("well")["n_guide_assigned_cells"].first().reindex(WELLS); axes[1].bar(WELLS, ga, color=[COLORS[w] for w in WELLS]); axes[1].set_ylabel("cells"); axes[1].set_title("Guide-assigned cells (targeting + NTC) per well", fontsize=9); style(axes[1])
    passing = perwell.groupby("well")["default_hit"].sum().reindex(WELLS); tested = perwell.groupby("well")["log2fc"].apply(lambda s: s.notna().sum()).reindex(WELLS)
    axes[2].bar(WELLS, tested, color="#c8c7c1", label="targets tested"); axes[2].bar(WELLS, passing, color=[COLORS[w] for w in WELLS], label=f"significant (KS FDR < {alpha} & log2FC < 0)"); axes[2].set_ylabel("targets"); axes[2].set_title("Significant targets per well / replicate", fontsize=9); axes[2].legend(fontsize=7, frameon=False); style(axes[2])
    fig.tight_layout(); save(fig, "perturbation", "supp_targeting_cells_assigned_cells_significant_targets_per_well")
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))
    for ax, c in zip(axes, ("HF011", "HF012")):
        x, y = rep[f"log2fc_{c}A"], rep[f"log2fc_{c}B"]; ok = x.notna() & y.notna(); r = np.corrcoef(x[ok], y[ok])[0, 1] if ok.sum() > 2 else np.nan
        ax.scatter(x[ok], y[ok], s=18, color=COLORS[f"{c}A"])
        for _, rr in rep[ok].iterrows():
            ax.annotate(rr.target_gene_name, (rr[f"log2fc_{c}A"], rr[f"log2fc_{c}B"]), fontsize=6, xytext=(2, 2), textcoords="offset points")
        lim = [min(x[ok].min(), y[ok].min()) - 0.2, max(x[ok].max(), y[ok].max()) + 0.2]; ax.plot(lim, lim, color="#e34948", linewidth=1); ax.set_xlabel(f"log2FC {c}A"); ax.set_ylabel(f"log2FC {c}B"); ax.set_title(f"{c}: well A vs B log2FC, r = {r:.3f} (well-level)", fontsize=9); style(ax)
    fig.tight_layout(); save(fig, "perturbation", "supp_replicate_consistency_log2fc_A_vs_B")
    g = bg[(bg.well == "ALL") & bg.log2fc.notna()].merge(pooled[["target_gene_name", "log2fc"]].rename(columns={"log2fc": "target_log2fc"}), on="target_gene_name")
    fig, ax = plt.subplots(figsize=(6, 5)); ax.scatter(g.target_log2fc, g.log2fc, s=10 + g.n_targeting_cells / 20, alpha=0.6, color=np.where(g.default_hit, "#2a78d6", "#9a9a9a"), linewidths=0)
    lim = [min(g.target_log2fc.min(), g.log2fc.min()) - 0.3, max(g.target_log2fc.max(), g.log2fc.max()) + 0.3]; ax.plot(lim, lim, color="#e34948", linewidth=1); ax.set_xlabel("target-level log2FC (pooled)"); ax.set_ylabel("per-guide log2FC (pooled)"); ax.set_title(f"Per-guide vs target-level efficacy ({len(g)} guides; blue = guide passes)", fontsize=9); style(ax); fig.tight_layout(); save(fig, "perturbation", "supp_per_guide_vs_target_efficacy")


def main() -> int:
    cfg, proc, allc, gvar = load()
    pipeline_pert = pd.read_csv(TAB / "perturbation_full.csv"); tested = set(pipeline_pert.target_gene.astype(str))
    cc = cell_counts_long(cfg, proc, allc, tested); qcw = qc_per_well(allc)
    dual = dual_guide_diagnostics(proc, gvar, cfg)
    bt, bg, rep, present = perturbation_tables(cfg, proc)
    log("== figures"); fig_cellranger(); fig_counts(cc); fig_dists_and_ecdfs(allc, proc); fig_knee(); fig_heatmap(qcw); fig_ab_concordance(proc)
    fig_embeddings(proc, allc, cfg); fig_guides(proc, gvar, cfg); fig_perturbation(bt, bg, rep, proc, present, cfg)
    summary = {"processed": list(proc.shape), "all_cells": list(allc.shape), "clusters": int(proc.obs["leiden"].nunique()) if "leiden" in proc.obs else None,
               "pipeline_targets_tested": int(len(pipeline_pert)), "pipeline_hits_ntc": int(pipeline_pert.is_hit_ntc.sum()),
               "supp_pooled_hits_ntc": int(bt[(bt.well == "ALL") & (bt.control == "ntc")].default_hit.sum()), "targets_testable_by_symbol": len(present)}
    json.dump(summary, open(TAB / "supplementary_summary.json", "w"), indent=2); log(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
