"""Figures for one run of the Hanrui Fang dual-guide analysis (QC, guides, perturbation)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.sparse as sp

from perturbseq_pipeline import dual_guides as dg
from supp_common import (ALL_TARGETING, CLASS_COLORS, COLORS, COND, QC_COLS, RES, STATUS_COLORS, STRICT, WELLS, Run, cellranger_metrics,
                         ecdf, log, save, style, symbol_of, _vec)

LABELS = {"total_counts": "total UMIs", "n_genes_by_counts": "detected genes", "pct_counts_mt": "% mitochondrial",
          "pct_counts_ribo": "% ribosomal", "pct_counts_hb": "% haemoglobin", "guide_umi_total": "guide UMIs",
          "n_guides_ge_min_umi": "guides per cell (>= min_umi)", "n_strong_guides_A_any": "strong scaffold-A guides",
          "n_strong_guides_C_any": "strong scaffold-C guides"}
LOGX = {"total_counts", "n_genes_by_counts", "guide_umi_total"}


def _col(g):
    return COLORS.get(g, "#52514e")


# ------------------------------------------------------------------------------------------ QC


def qc_figures(run: Run, counts_df: pd.DataFrame):
    a, p = run.allc.obs, run.proc.obs
    groups = run.groups
    # before vs after cell counts
    wide = counts_df[counts_df.cell_category.isin(["input cells (Cell Ranger filtered)", "cells loaded by pipeline",
                                                    "pass >= 1000 genes", "cells in processed object (pipeline QC pass)",
                                                    "pair-assigned cells (targeting + non-targeting)",
                                                    "cells used for perturbation testing (targeting of tested targets + NTC)"])]
    piv = wide.pivot_table(index="well", columns="cell_category", values="cell_count", aggfunc="first").reindex(groups)
    fig, ax = plt.subplots(figsize=(1.8 * len(groups) + 4, 4))
    x = np.arange(len(groups)); w = 0.8 / max(len(piv.columns), 1)
    for i, c in enumerate(piv.columns):
        ax.bar(x + i * w, piv[c], width=w, label=c[:48])
    ax.set_xticks(x + 0.4 - w / 2); ax.set_xticklabels(groups); ax.set_ylabel("cells")
    ax.set_title(f"{run.label}: cells before and after QC / guide assignment", fontsize=9); ax.legend(fontsize=6, frameon=False); style(ax)
    save(fig, run.fig, "qc", "cell_counts_before_after")

    cr = cellranger_metrics()
    if len(cr):
        cr = cr[cr.well.isin(run.wells)].set_index("well")
        mets = [c for c in ("Estimated Number of Cells", "Mean Reads per Cell", "Median Genes per Cell", "Median UMI Counts per Cell",
                            "Sequencing Saturation", "Valid Barcodes", "Fraction Reads in Cells", "Total Genes Detected") if c in cr.columns]
        fig, axes = plt.subplots(2, 4, figsize=(14, 6)); axes = axes.ravel()
        for ax, m in zip(axes, mets):
            ax.bar(cr.index, pd.to_numeric(cr[m], errors="coerce"), color=[_col(w) for w in cr.index]); ax.set_title(m, fontsize=8); style(ax)
            ax.tick_params(axis="x", labelsize=7)
        fig.suptitle("Cell Ranger metrics per well", fontsize=10); fig.tight_layout()
        save(fig, run.fig, "qc", "cellranger_metrics_per_well")

    # distributions before/after per well + pooled (violin)
    for c in QC_COLS:
        fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
        for ax, (stage, m) in zip(axes, (("before QC (all loaded cells)", pd.Series(True, index=a.index)), ("after QC (processed object)", a["pipeline_qc_pass"]))):
            data = [a.loc[m & run.mask(a, g), c].to_numpy() for g in groups]
            data = [np.log10(d + 1) if c in LOGX else d for d in data]
            parts = ax.violinplot([d for d in data if len(d)], showmedians=True)
            for pc_, g in zip(parts["bodies"], [g for g, d in zip(groups, data) if len(d)]):
                pc_.set_facecolor(_col(g)); pc_.set_alpha(0.7)
            ax.set_xticks(range(1, len(groups) + 1)); ax.set_xticklabels(groups); ax.set_title(stage, fontsize=9)
            ax.set_ylabel(("log10 " if c in LOGX else "") + LABELS[c]); style(ax)
        fig.suptitle(f"{run.label}: {LABELS[c]} per well (pooled = ALL)", fontsize=10); fig.tight_layout()
        save(fig, run.fig, "qc", f"dist_{c}_before_after")

    # ECDFs before/after per well + pooled
    for c in QC_COLS[:4] + ["guide_umi_total", "n_guides_ge_min_umi", "n_strong_guides_A_any", "n_strong_guides_C_any"]:
        fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
        for ax, (stage, m) in zip(axes, (("before QC", pd.Series(True, index=a.index)), ("after QC", a["pipeline_qc_pass"]))):
            for g in groups:
                ecdf(ax, a.loc[m & run.mask(a, g), c], g, _col(g), log_x=c in LOGX, ls="--" if g == "ALL" else "-")
            ax.set_xlabel(LABELS[c] + (" (+1, log)" if c in LOGX else "")); ax.set_ylabel("ECDF"); ax.set_title(stage, fontsize=9)
            ax.legend(fontsize=6, frameon=False); style(ax)
        fig.suptitle(f"{run.label}: ECDF of {LABELS[c]} per well and pooled", fontsize=10); fig.tight_layout()
        save(fig, run.fig, "qc", f"ecdf_{c}_before_after")

    # UMI vs genes scatter per well
    fig, axes = plt.subplots(1, len(run.wells), figsize=(4 * len(run.wells), 3.8), squeeze=False)
    for ax, wl in zip(axes.ravel(), run.wells):
        s = a[a["well"].astype(str) == wl]
        ax.scatter(s["total_counts"], s["n_genes_by_counts"], s=2, c=np.where(s["pipeline_qc_pass"], _col(wl), CLASS_COLORS["QC-failed"]), alpha=0.4, linewidths=0)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("total UMIs"); ax.set_ylabel("detected genes")
        ax.set_title(f"{wl} (red = QC-failed, n={int((~s['pipeline_qc_pass']).sum()):,})", fontsize=8); style(ax)
    fig.tight_layout(); save(fig, run.fig, "qc", "umi_vs_genes_per_well")

    # barcode-rank knee per well
    fig, ax = plt.subplots(figsize=(6, 4))
    for wl in run.wells:
        v = np.sort(a.loc[a["well"].astype(str) == wl, "total_counts"].to_numpy())[::-1]
        ax.plot(np.arange(1, v.size + 1), v, color=_col(wl), label=wl)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("barcode rank (Cell Ranger-called cells)"); ax.set_ylabel("total UMIs")
    ax.set_title("Barcode-rank (knee) plot per well", fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax)
    save(fig, run.fig, "qc", "barcode_rank_knee_per_well")

    # per-well QC heatmap (medians after QC, z-scored per metric)
    med = pd.DataFrame({g: a.loc[a["pipeline_qc_pass"] & run.mask(a, g), QC_COLS + ["guide_umi_total", "n_guides_ge_min_umi"]].median() for g in groups}).T
    z = (med - med.mean()) / med.std(ddof=0).replace(0, 1)
    fig, ax = plt.subplots(figsize=(7, 0.6 * len(groups) + 2))
    im = ax.imshow(z.to_numpy(dtype=float), cmap="RdBu_r", vmin=-2, vmax=2, aspect="auto")
    ax.set_xticks(range(len(med.columns))); ax.set_xticklabels([LABELS.get(c, c) for c in med.columns], rotation=30, ha="right", fontsize=7)
    ax.set_yticks(range(len(groups))); ax.set_yticklabels(groups)
    for i in range(len(groups)):
        for j in range(len(med.columns)):
            ax.text(j, i, f"{med.iloc[i, j]:.3g}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=ax, label="z-score across wells"); ax.set_title("Per-well QC medians after QC", fontsize=9); fig.tight_layout()
    save(fig, run.fig, "qc", "per_well_qc_heatmap")

    # PCA / UMAP colourings
    for rep, key in (("pca", "X_pca"), ("umap", "X_umap")):
        if key not in run.proc.obsm:
            continue
        E = run.proc.obsm[key][:, :2]
        order = np.random.default_rng(0).permutation(E.shape[0])
        panels = [("well", p["well"].astype(str), {w: _col(w) for w in WELLS}), ("condition", p["condition"].astype(str), {"HF011": "#2a78d6", "HF012": "#eb6834"})]
        if rep == "umap":
            qc_status = np.where(p["pct_counts_mt"] >= 10, "QC pass: mt >= 10%", np.where(p["n_genes_by_counts"] < 1500, "QC pass: 1000-1500 genes", "QC pass: typical"))
            panels.append(("QC status", pd.Series(qc_status, index=p.index), {"QC pass: typical": "#c9c9c9", "QC pass: 1000-1500 genes": "#eda100", "QC pass: mt >= 10%": "#e34948"}))
            panels.append(("pair-assignment status", p[dg.OBS_PAIR_STATUS].astype(str), STATUS_COLORS))
            panels.append(("perturbation class", p["perturbation_class"].astype(str), CLASS_COLORS))
        fig, axes = plt.subplots(1, len(panels), figsize=(4.6 * len(panels), 4.2), squeeze=False)
        for ax, (name, lab, pal) in zip(axes.ravel(), panels):
            lab = lab.to_numpy()
            cols = np.array([pal.get(v, "#999999") for v in lab])
            ax.scatter(E[order, 0], E[order, 1], s=1.5, c=cols[order], linewidths=0, alpha=0.6)
            for v in pd.unique(lab):
                ax.scatter([], [], c=pal.get(v, "#999999"), s=14, label=f"{v} ({int((lab == v).sum()):,})")
            ax.legend(fontsize=5, frameon=False, markerscale=1.2, loc="best"); ax.set_title(f"{rep.upper()} coloured by {name}", fontsize=9)
            ax.set_xticks([]); ax.set_yticks([]); ax.set_xlabel(f"{rep.upper()}1"); ax.set_ylabel(f"{rep.upper()}2")
        fig.tight_layout(); save(fig, run.fig, "qc", f"{rep}_by_well_condition_qcstatus_pairstatus")


# ------------------------------------------------------------------------------------------ guides


def guide_figures(run: Run, assign_summary: pd.DataFrame, dv: pd.DataFrame):
    p = run.proc.obs
    groups = run.groups
    funnel = pd.read_csv(RES / "tables" / "guide_read_retention_funnel.csv").set_index("well")
    funnel = funnel.loc[[w for w in run.wells if w in funnel.index]]
    steps = ["reads_total", "reads_with_scaffold_anchor", "reads_spacer_matched_total", "reads_matched_barcode_in_gex", "reads_valid_barcode_and_umi", "unique_cell_guide_umis"]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    for wl in funnel.index:
        axes[0].plot(range(len(steps)), funnel.loc[wl, steps] / funnel.loc[wl, "reads_total"], marker="o", color=_col(wl), label=wl)
    axes[0].set_xticks(range(len(steps))); axes[0].set_xticklabels([s.replace("reads_", "").replace("_", "\n") for s in steps], fontsize=7)
    axes[0].set_ylabel("fraction of total reads"); axes[0].set_title("Guide read-retention funnel", fontsize=9); axes[0].legend(fontsize=7, frameon=False); style(axes[0])
    fr = funnel[["frac_matched_valid_gex_barcode", "frac_barcode_matched_valid_umi", "frac_anchored_exact_match", "frac_anchored_rescued_1mismatch", "frac_anchored_unmatched"]]
    fr.columns = ["valid GEX barcode\n(of matched)", "valid UMI\n(of barcode-matched)", "exact spacer match\n(of anchored)", "1-mismatch rescue\n(of anchored)", "unmatched\n(of anchored)"]
    x = np.arange(fr.shape[1]); w = 0.8 / max(len(fr), 1)
    for i, wl in enumerate(fr.index):
        axes[1].bar(x + i * w, fr.loc[wl], width=w, color=_col(wl), label=wl)
    axes[1].set_xticks(x + 0.4 - w / 2); axes[1].set_xticklabels(fr.columns, fontsize=7); axes[1].set_ylabel("fraction"); axes[1].set_title("Retention fractions per well", fontsize=9); style(axes[1])
    fig.tight_layout(); save(fig, run.fig, "guides", "guide_read_funnel_and_retention_fractions")
    for col, name in (("frac_matched_valid_gex_barcode", "valid_barcode_fraction"), ("frac_barcode_matched_valid_umi", "valid_umi_fraction"),
                      ("frac_anchored_exact_match", "exact_match_fraction"), ("frac_anchored_rescued_1mismatch", "mismatch_rescue_fraction")):
        fig, ax = plt.subplots(figsize=(4.5, 3.5)); ax.bar(funnel.index, funnel[col], color=[_col(w) for w in funnel.index]); ax.set_ylabel(col); ax.set_title(name.replace("_", " "), fontsize=9); style(ax)
        for i, v in enumerate(funnel[col]):
            ax.text(i, v, f"{v:.4f}", ha="center", va="bottom", fontsize=7)
        save(fig, run.fig, "guides", name)

    # per-guide abundance / per-well recovery / per-target representation (from job-03 table)
    gpw = pd.read_csv(RES / "tables" / "guide_counts_per_well.csv")
    gpw = gpw[gpw.well.isin(run.wells + ["ALL"])] if len(run.wells) > 1 else gpw[gpw.well.isin(run.wells)]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4))
    for wl in run.wells:
        s = gpw[gpw.well == wl].sort_values("umis_in_cells", ascending=False)
        axes[0].plot(np.arange(1, len(s) + 1), s["umis_in_cells"] + 1, color=_col(wl), label=f"{wl}: {int((s.umis_in_cells > 0).sum())}/560 guides observed")
    axes[0].set_yscale("log"); axes[0].set_xlabel("guide rank"); axes[0].set_ylabel("UMIs in cells + 1"); axes[0].set_title("Per-guide abundance (all 560 designs)", fontsize=9); axes[0].legend(fontsize=7, frameon=False); style(axes[0])
    rec = gpw[gpw.well.isin(run.wells)].groupby("well").agg(observed=("umis_in_cells", lambda s: int((s > 0).sum())), at_threshold=(gpw.columns[gpw.columns.str.startswith("cells_positive_ge") & ~gpw.columns.str.endswith("ge1")][0], lambda s: int((s > 0).sum())))
    rec.plot.bar(ax=axes[1], color=["#2a78d6", "#8ab4e8"]); axes[1].set_ylabel("guides (of 560)"); axes[1].set_title("Per-well guide recovery", fontsize=9); style(axes[1])
    fig.tight_layout(); save(fig, run.fig, "guides", "per_guide_abundance_and_per_well_recovery")
    tr = gpw[gpw.well.isin(run.wells)].groupby(["target_gene_name", "well"])["umis_in_cells"].sum().unstack(fill_value=0)
    tr = tr.loc[tr.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(12, 4)); tr.plot.bar(ax=ax, stacked=True, color=[_col(w) for w in tr.columns], width=0.8)
    ax.set_yscale("log"); ax.set_ylabel("guide UMIs in cells"); ax.set_title("Per-target guide representation (UMIs, all guides of the target)", fontsize=9); ax.tick_params(axis="x", labelsize=6); style(ax)
    save(fig, run.fig, "guides", "per_target_guide_representation")
    # cells per target after pair assignment
    ct = pd.crosstab(p.loc[p.perturbation_class.astype(str) == "targeting", "target_gene"].astype(str), p.loc[p.perturbation_class.astype(str) == "targeting", "well"].astype(str))
    ct = ct.loc[ct.sum(axis=1).sort_values(ascending=False).index]
    fig, ax = plt.subplots(figsize=(12, 4)); ct.plot.bar(ax=ax, stacked=True, color=[_col(w) for w in ct.columns], width=0.8)
    ax.axhline(run.cfg["perturbation"]["min_cells_per_target"], color="#e34948", ls="--", lw=0.8); ax.set_ylabel("targeting cells"); ax.set_title("Targeting cells per target after dual-guide assignment", fontsize=9); ax.tick_params(axis="x", labelsize=6); style(ax)
    save(fig, run.fig, "guides", "targeting_cells_per_target")

    # guide UMIs per cell, guides per cell, A vs C
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for g in groups:
        s = p[run.mask(p, g)]
        ecdf(axes[0], s["guide_umi_total"], g, _col(g), log_x=True, ls="--" if g == "ALL" else "-")
        ecdf(axes[1], s["n_guides_ge_min_umi"], g, _col(g), ls="--" if g == "ALL" else "-")
    axes[0].set_xlabel("guide UMIs per cell (+1)"); axes[0].set_title("Guide UMIs per cell", fontsize=9); axes[0].legend(fontsize=6, frameon=False); style(axes[0])
    axes[1].set_xlabel(f"guides per cell at >= {run.cfg['guides']['min_umi']} UMIs"); axes[1].set_title("Number of guides per cell", fontsize=9); axes[1].set_xlim(0, 15); style(axes[1])
    sub = p.sample(min(len(p), 40000), random_state=0)
    axes[2].scatter(sub[dg.OBS_SLOT_COUNT.format(c="A")] + 1, sub[dg.OBS_SLOT_COUNT.format(c="C")] + 1, s=2, alpha=0.3, linewidths=0,
                    c=[STATUS_COLORS.get(v, "#999") for v in sub[dg.OBS_PAIR_STATUS].astype(str)])
    axes[2].set_xscale("log"); axes[2].set_yscale("log"); axes[2].set_xlabel("top scaffold-A guide UMIs + 1"); axes[2].set_ylabel("top scaffold-C guide UMIs + 1")
    axes[2].set_title("Scaffold-A vs scaffold-C top-guide counts (colour = pair status)", fontsize=8); style(axes[2])
    fig.tight_layout(); save(fig, run.fig, "guides", "guide_umis_guides_per_cell_A_vs_C")

    # pair-assignment categories per well (stacked) + fractions
    tab = pd.crosstab(p["well"].astype(str), p[dg.OBS_PAIR_STATUS].astype(str)).reindex(run.wells).fillna(0)
    if len(run.wells) > 1:
        tab.loc["ALL"] = tab.sum()
    order = [s for s in dg.PAIR_STATUS_ORDER if s in tab.columns]
    tab = tab[order]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    bottom = np.zeros(len(tab))
    for c in order:
        axes[0].bar(tab.index, tab[c], bottom=bottom, color=STATUS_COLORS.get(c, "#999"), label=c); bottom += tab[c].to_numpy()
    axes[0].set_ylabel("QC-passing cells"); axes[0].set_title("Pair-assignment categories per well", fontsize=9); axes[0].legend(fontsize=6, frameon=False, bbox_to_anchor=(1, 1), loc="upper left"); style(axes[0])
    frac = tab.div(tab.sum(axis=1), axis=0)
    keys = {"same_target_pair": "same-target pair", "target_ntc_provisional": "target+NTC (provisional)", "ntc_pair": "NTC pair", "dual_target": "dual-target",
            "invalid_pair": "invalid pair", "incomplete_A_only": "incomplete (A only)", "incomplete_C_only": "incomplete (C only)"}
    kk = [k for k in keys if k in frac.columns]
    x = np.arange(len(kk)); w = 0.8 / len(tab)
    for i, g in enumerate(tab.index):
        axes[1].bar(x + i * w, frac.loc[g, kk], width=w, color=_col(g), label=g)
    axes[1].set_xticks(x + 0.4 - w / 2); axes[1].set_xticklabels([keys[k] for k in kk], fontsize=7, rotation=20); axes[1].set_ylabel("fraction of QC-passing cells")
    axes[1].set_title("Pair-category fractions per well", fontsize=9); axes[1].legend(fontsize=6, frameon=False); style(axes[1])
    fig.tight_layout(); save(fig, run.fig, "guides", "pair_assignment_categories_and_fractions")
    tab.to_csv(run.tab / "pair_assignment_categories_per_well.csv")

    # default (single-guide) vs dual comparison
    sc_, dc_ = run.single_class, run.dual_cat
    cross = pd.crosstab(pd.Series(sc_, name="single-guide baseline class"), pd.Series(dc_, name="dual-guide category"))
    fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
    im = axes[0].imshow(cross.to_numpy(), cmap="Blues", aspect="auto")
    axes[0].set_xticks(range(cross.shape[1])); axes[0].set_xticklabels(cross.columns, fontsize=6, rotation=30, ha="right")
    axes[0].set_yticks(range(cross.shape[0])); axes[0].set_yticklabels(cross.index, fontsize=7)
    for i in range(cross.shape[0]):
        for j in range(cross.shape[1]):
            axes[0].text(j, i, f"{cross.iloc[i, j]:,}", ha="center", va="center", fontsize=6, color="white" if cross.iloc[i, j] > cross.values.max() / 2 else "black")
    axes[0].set_title("Single-guide baseline class vs dual-guide category (cells)", fontsize=9)
    amb = cross.loc["ambiguous"] if "ambiguous" in cross.index else pd.Series(dtype=float)
    axes[1].barh(amb.index, amb.values, color=[STATUS_COLORS["same_target_pair"] if "same-target" in k else STATUS_COLORS["target_ntc_provisional"] if "provisional" in k else STATUS_COLORS["ntc_pair"] if "NTC pair" in k else STATUS_COLORS["dual_target"] if "dual" in k else "#eda100" for k in amb.index])
    for i, v in enumerate(amb.values):
        axes[1].text(v, i, f" {int(v):,} ({100 * v / max(amb.sum(), 1):.1f}%)", va="center", fontsize=7)
    axes[1].set_title(f"Where the {int(amb.sum()):,} baseline-ambiguous cells go under dual-guide assignment", fontsize=9); axes[1].tick_params(axis="y", labelsize=7); style(axes[1])
    fig.tight_layout(); save(fig, run.fig, "guides", "default_vs_dual_assignment")


# ------------------------------------------------------------------------------------------ perturbation


def perturbation_figures(run: Run, bt: pd.DataFrame, bg: pd.DataFrame, bi: pd.DataFrame, rep: pd.DataFrame, present: dict):
    alpha = run.cfg["perturbation"]["fdr_alpha"]
    pooled_key = "ALL" if "ALL" in run.groups else run.wells[0]
    main = bt[(bt.control == "ntc") & (bt.assignment_stratum == ALL_TARGETING)]
    pooled = main[main.well == pooled_key].dropna(subset=["log2fc"]).copy()
    strict = bt[(bt.control == "ntc") & (bt.assignment_stratum == STRICT) & (bt.well == pooled_key)].dropna(subset=["log2fc"])
    other = bt[(bt.control == "other") & (bt.assignment_stratum == ALL_TARGETING) & (bt.well == pooled_key)].dropna(subset=["log2fc"])
    # volcano
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(pooled["log2fc"], pooled["neg_log10_fdr"], c=np.where(pooled["default_hit"], "#2a78d6", "#9a9a9a"), s=28)
    for _, r in pooled.iterrows():
        ax.annotate(r["target_gene_name"], (r["log2fc"], r["neg_log10_fdr"]), fontsize=6, xytext=(2, 2), textcoords="offset points")
    ax.axhline(-np.log10(alpha), color="#e34948", ls="--", lw=0.8); ax.axvline(0, color="#52514e", lw=0.6)
    ax.set_xlabel("log2FC target transcript (targeting vs NTC)"); ax.set_ylabel("-log10(KS FDR)"); ax.set_title(f"{run.label}: target-transcript depletion association (volcano)", fontsize=9); style(ax)
    save(fig, run.fig, "perturbation", "volcano_log2fc_vs_neglog10fdr")
    # waterfall
    wf = pooled.sort_values("log2fc")
    fig, ax = plt.subplots(figsize=(max(6, 0.28 * len(wf)), 4))
    ax.bar(wf["target_gene_name"], wf["log2fc"], color=np.where(wf["default_hit"], "#2a78d6", "#9a9a9a"))
    sm = strict.set_index("target_gene_name")["log2fc"].reindex(wf["target_gene_name"])
    ax.scatter(range(len(wf)), sm.values, color="#e34948", s=12, zorder=3, label="same-target pairs only")
    ax.tick_params(axis="x", rotation=90, labelsize=7); ax.set_ylabel("log2FC vs NTC"); ax.set_title("Waterfall of target-transcript log2FC (blue = KS FDR < 0.05 & down)", fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax)
    save(fig, run.fig, "perturbation", "waterfall_target_log2fc")
    # heatmaps by sample
    for col, name, cmap in (("log2fc", "log2fc", "RdBu_r"), ("neg_log10_fdr", "neg_log10_fdr", "Blues")):
        piv = main.pivot_table(index="target_gene_name", columns="well", values=col, aggfunc="first").reindex(columns=run.groups)
        piv = piv.loc[pooled.sort_values("log2fc")["target_gene_name"]] if len(pooled) else piv
        fig, ax = plt.subplots(figsize=(1.2 * len(run.groups) + 3, 0.22 * len(piv) + 1.5))
        v = np.nanmax(np.abs(piv.to_numpy(dtype=float))) if piv.size else 1
        im = ax.imshow(piv.to_numpy(dtype=float), cmap=cmap, aspect="auto", **({"vmin": -v, "vmax": v} if col == "log2fc" else {"vmin": 0}))
        ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, fontsize=8); ax.set_yticks(range(len(piv))); ax.set_yticklabels(piv.index, fontsize=6)
        fig.colorbar(im, ax=ax, label=name); ax.set_title(f"{name} by sample (targeting vs NTC)", fontsize=9); fig.tight_layout()
        save(fig, run.fig, "perturbation", f"heatmap_{name}_by_sample")
    # counts per target / per sample
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    tc = pooled.sort_values("n_targeting_cells", ascending=False)
    axes[0].bar(tc["target_gene_name"], tc["n_targeting_cells"], color="#2a78d6"); axes[0].tick_params(axis="x", rotation=90, labelsize=6); axes[0].set_ylabel("targeting cells"); axes[0].set_title("Targeting cells per target", fontsize=9); style(axes[0])
    ga = main.groupby("well")["n_guide_assigned_cells"].first().reindex(run.groups)
    axes[1].bar(ga.index, ga.values, color=[_col(g) for g in ga.index]); axes[1].set_ylabel("guide-assigned cells"); axes[1].set_title("Guide-assigned cells per sample", fontsize=9); style(axes[1])
    ns = main.dropna(subset=["log2fc"]).groupby("well")["default_hit"].sum().reindex(run.groups)
    nt = main.dropna(subset=["log2fc"]).groupby("well").size().reindex(run.groups)
    axes[2].bar(ns.index, nt.values, color="#d0d0d0", label="tested"); axes[2].bar(ns.index, ns.values, color=[_col(g) for g in ns.index], label="significant (KS FDR<0.05 & down)")
    axes[2].set_ylabel("targets"); axes[2].set_title("Significant targets per sample", fontsize=9); axes[2].legend(fontsize=7, frameon=False); style(axes[2])
    fig.tight_layout(); save(fig, run.fig, "perturbation", "targeting_cells_assigned_cells_significant_targets_per_sample")
    # per-guide vs target efficacy
    gpool = bg[bg.well == pooled_key].dropna(subset=["log2fc"])
    ipool = bi[bi.well == pooled_key].dropna(subset=["log2fc"])
    tl = pooled.set_index("target_gene_name")["log2fc"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    axes[0].scatter(gpool["target_gene_name"].map(tl), gpool["log2fc"], s=10, alpha=0.6, c="#2a78d6"); axes[0].plot([-5, 1], [-5, 1], color="#999", lw=0.6)
    axes[0].set_xlabel("target-level log2FC"); axes[0].set_ylabel("guide-pair-level log2FC"); axes[0].set_title(f"Per guide pair (n={len(gpool)}) vs target", fontsize=9); style(axes[0])
    for slot, col in (("A", "#2a78d6"), ("C", "#eb6834")):
        s = ipool[ipool.scaffold == slot]
        axes[1].scatter(s["target_gene_name"].map(tl), s["log2fc"], s=10, alpha=0.6, c=col, label=f"scaffold {slot} (n={len(s)})")
    axes[1].plot([-5, 1], [-5, 1], color="#999", lw=0.6); axes[1].set_xlabel("target-level log2FC"); axes[1].set_ylabel("individual-guide log2FC"); axes[1].set_title("Per individual guide vs target", fontsize=9); axes[1].legend(fontsize=7, frameon=False); style(axes[1])
    fig.tight_layout(); save(fig, run.fig, "perturbation", "per_guide_vs_target_efficacy")
    # ECDF target expression (top targets) vs NTC and vs other
    top = pooled.sort_values("fdr_ks").head(12)
    obs = run.proc.obs; klass = obs["perturbation_class"].astype(str).to_numpy(); tgt = obs["target_gene"].astype(str).to_numpy()
    for ctrl in ("ntc", "other"):
        fig, axes = plt.subplots(3, 4, figsize=(15, 9)); axes = axes.ravel()
        for ax, (_, r) in zip(axes, top.iterrows()):
            v = _vec(run.proc, r["target_gene"])
            mp = (klass == "targeting") & (tgt == r["target_gene_name"])
            mc = (klass == "non-targeting") if ctrl == "ntc" else ((klass == "targeting") & (tgt != r["target_gene_name"]))
            ecdf(ax, v[mp], "targeting", "#2a78d6"); ecdf(ax, v[mc], ctrl, "#9a9a9a")
            ax.set_title(f"{r['target_gene_name']}: log2FC {r['log2fc']:.2f}, FDR {r['fdr_ks']:.1e}", fontsize=8); ax.set_xlabel("lognorm expression"); ax.legend(fontsize=6, frameon=False); style(ax)
        for ax in axes[len(top):]:
            ax.axis("off")
        fig.suptitle(f"Target-transcript ECDF: targeting vs {ctrl} controls ({run.label})", fontsize=10); fig.tight_layout()
        save(fig, run.fig, "perturbation", f"ecdf_target_expression_vs_{ctrl}")
    # -log10 FDR ECDF by sample
    fig, ax = plt.subplots(figsize=(6, 4))
    for g in run.groups:
        ecdf(ax, main.loc[main.well == g, "neg_log10_fdr"], g, _col(g), ls="--" if g == "ALL" else "-")
    ax.axvline(-np.log10(alpha), color="#e34948", ls="--", lw=0.8); ax.set_xlabel("-log10(KS FDR) per target"); ax.set_ylabel("ECDF over targets"); ax.set_title("-log10(FDR) ECDF by sample", fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax)
    save(fig, run.fig, "perturbation", "ecdf_neglog10fdr_by_sample")
    # well consistency (A vs B within condition) when >1 well
    if len(run.wells) > 1:
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
        for ax, cond in zip(axes, ("HF011", "HF012")):
            a_, b_ = f"{cond}A", f"{cond}B"
            if a_ in run.wells and b_ in run.wells:
                x = rep[f"log2fc_{a_}"]; y = rep[f"log2fc_{b_}"]
                ax.scatter(x, y, s=18, c=np.where(rep["pooled_hit"], "#2a78d6", "#9a9a9a"))
                for _, r in rep.iterrows():
                    ax.annotate(r["target_gene_name"], (r[f"log2fc_{a_}"], r[f"log2fc_{b_}"]), fontsize=5, xytext=(2, 2), textcoords="offset points")
                ok = x.notna() & y.notna()
                rho = np.corrcoef(x[ok], y[ok])[0, 1] if ok.sum() > 2 else np.nan
                ax.plot([-5, 1], [-5, 1], color="#999", lw=0.6); ax.set_xlabel(f"log2FC {a_}"); ax.set_ylabel(f"log2FC {b_}")
                ax.set_title(f"{cond}: well A vs well B (r = {rho:.2f}; replicate type unknown)", fontsize=9); style(ax)
        fig.tight_layout(); save(fig, run.fig, "perturbation", "well_consistency_log2fc_A_vs_B")
