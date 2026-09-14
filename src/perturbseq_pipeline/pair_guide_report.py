"""Pair-guide QC, clustering annotation, ECDF and perturbation outputs.

Runs inside the pipeline when ``guides.assignment_mode: pair``. Everything is
written through the run's :class:`~perturbseq_pipeline.plots.FigureRegistry`
(so the figures land in the run report) and returned as tables for
``tables/*.csv``. Statistics reuse :func:`perturbation.compare_groups`
(two-sided KS, one-sided Mann-Whitney 'less', log2FC on de-logged lognorm with
pseudocount 0.01) and :func:`perturbation.benjamini_hochberg`; the hit rule is
the pipeline default (``ks_fdr < fdr_alpha`` and ``log2fc < max_log2fc_for_hit``).

Primary labels are the pair assignments: targeting cells = ``pair_targeting``
(plus ``pair_targeting_plus_ntc_provisional`` when that policy is on), controls =
``pair_non_targeting`` cells. A clearly labelled sensitivity stratum adds the
``pair_targeting_plus_ntc`` cells to the targeting group. FDR columns: ``fdr_ks``
(raw BH FDR) and ``neg_log10_fdr = -log10(max(fdr_ks, 1e-300))``.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse

from . import dual_guides as dg
from .config import Config
from .guides import CLASS_AMBIGUOUS, CLASS_NTC, CLASS_TARGETING, CLASS_UNASSIGNED, OBS_CLASS, OBS_GUIDE, OBS_TARGET
from .io import LANE_KEY
from .perturbation import benjamini_hochberg, compare_groups
from .plots import SECTION_CLUSTERING, SECTION_GUIDES, SECTION_PERTURBATION, SECTION_QC, FigureRegistry

logger = logging.getLogger(__name__)

SECTION_ECDF = "perturbation/ecdf"
QC_COLS = ["total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "pct_counts_hb"]
QC_LABEL = {"total_counts": "total UMIs", "n_genes_by_counts": "detected genes", "pct_counts_mt": "% mitochondrial",
            "pct_counts_ribo": "% ribosomal", "pct_counts_hb": "% haemoglobin"}
LOGX = {"total_counts", "n_genes_by_counts", "guide_umi_total"}
STRATUM_PRIMARY = "primary_pair_targeting"
STRATUM_SENSITIVITY = "sensitivity_incl_targeting_plus_ntc"
CLASS_COLORS = {CLASS_TARGETING: "#2a78d6", CLASS_NTC: "#1baf7a", CLASS_AMBIGUOUS: "#eda100", CLASS_UNASSIGNED: "#9a9a9a", "QC-failed": "#e34948"}
STATUS_COLORS = {
    dg.STATUS_PAIR_TARGETING: "#2a78d6", dg.STATUS_PAIR_NTC: "#1baf7a", dg.STATUS_PAIR_TARGET_NTC: "#8ab4e8",
    dg.STATUS_PAIR_TARGET_NTC_PROVISIONAL: "#5b9be0", dg.STATUS_DUAL_TARGET: "#4a3aa7", dg.STATUS_UNRESOLVED: "#e34948",
    dg.STATUS_INCOMPLETE: "#eda100", "ambiguous_scaffold_A": "#eb6834", "ambiguous_scaffold_C": "#f3a98a",
    "ambiguous_scaffold_A_and_C": "#b04a20", dg.STATUS_UNKNOWN_GUIDE: "#8d6e63", dg.STATUS_BELOW_MIN_UMI: "#c9c9c9", dg.STATUS_NO_GUIDE: "#7a7a7a",
}
_PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#4a3aa7", "#8ab4e8", "#f3a98a", "#52514e", "#e34948", "#b04a20", "#8d6e63", "#5b9be0"]


def _style(ax):
    ax.grid(True, color="#e0dfda", linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def _ecdf(ax, values, label, color, log_x=False, ls="-"):
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


def _lanes(obs) -> List[str]:
    return sorted(obs[LANE_KEY].astype(str).unique()) if LANE_KEY in obs.columns else []


def _groups(obs) -> List[str]:
    lanes = _lanes(obs)
    return lanes + (["ALL"] if len(lanes) > 1 else [])


def _mask(obs, g):
    return np.ones(len(obs), bool) if g == "ALL" else (obs[LANE_KEY].astype(str) == g).to_numpy()


def _color(i_or_key, keys=None):
    if keys is not None:
        return _PALETTE[list(keys).index(i_or_key) % len(_PALETTE)]
    return _PALETTE[i_or_key % len(_PALETTE)]


def _guide_matrix(expr: ad.AnnData, guides: Optional[ad.AnnData], cfg: Config) -> sparse.csr_matrix:
    if guides is not None:
        g = guides if guides.obs_names.equals(expr.obs_names) else guides[expr.obs_names]
        return sparse.csr_matrix(g.layers["counts"] if "counts" in g.layers else g.X)
    return sparse.csr_matrix(expr.obsm[cfg.output.guide_obsm_key])


# ---------------------------------------------------------------------------
# 1. Expression QC before / after, per lane
# ---------------------------------------------------------------------------


def qc_before_after(expr: ad.AnnData, qc_before: Optional[pd.DataFrame], cfg: Config, registry: FigureRegistry) -> Dict[str, pd.DataFrame]:
    """Per-lane cell accounting and before/after distributions.

    ``qc_before`` holds the QC metrics of every loaded cell (captured in the CLI
    before any filtering); ``expr`` is the filtered object.
    """
    tables: Dict[str, pd.DataFrame] = {}
    q = cfg.qc
    after = expr.obs
    if qc_before is None or LANE_KEY not in qc_before.columns:
        logger.warning("No pre-filter QC metrics available; before/after QC accounting skipped")
        return tables
    before = qc_before
    groups = _groups(before)
    rows = []
    for g in groups:
        b = before[_mask(before, g)]
        a = after[_mask(after, g)] if LANE_KEY in after.columns else after
        pre = b["n_genes_by_counts"] >= q.min_genes_per_cell
        fin = pre & (b["n_genes_by_counts"] >= q.min_genes_final)
        mt = fin & (b["pct_counts_mt"] < q.max_pct_mt)
        rows.append({"lane_id": g, "input_cells": len(b),
                     f"cells_after_permissive_gene_filter_ge{q.min_genes_per_cell}": int(pre.sum()),
                     f"cells_after_final_gene_filter_ge{q.min_genes_final}": int(fin.sum()),
                     f"cells_failing_mt_ge{q.max_pct_mt:g}pct": int((fin & ~mt).sum()),
                     "cells_failing_any_expression_qc": int(len(b) - len(a)),
                     "final_cells_retained": len(a), "frac_retained": len(a) / max(len(b), 1)})
    tables["cell_counts_before_after"] = pd.DataFrame(rows)
    rows = []
    cols = [c for c in QC_COLS if c in before.columns]
    for g in groups:
        for stage, df in (("before_qc", before[_mask(before, g)]), ("after_qc", after[_mask(after, g)])):
            rows.append({"lane_id": g, "stage": stage, "n_cells": len(df), **{f"median_{c}": float(df[c].median()) for c in cols},
                         **{f"mean_{c}": float(df[c].mean()) for c in cols}})
    tables["qc_metrics_per_lane_before_after"] = pd.DataFrame(rows)

    # figures
    cc = tables["cell_counts_before_after"].set_index("lane_id")
    fig, ax = plt.subplots(figsize=(1.6 * len(groups) + 4, 4))
    x = np.arange(len(groups)); cols_cc = [c for c in cc.columns if c not in ("frac_retained", "cells_failing_any_expression_qc")]
    w = 0.8 / len(cols_cc)
    for i, c in enumerate(cols_cc):
        ax.bar(x + i * w, cc[c], width=w, color=_color(i), label=c.replace("_", " "))
    ax.set_xticks(x + 0.4 - w / 2); ax.set_xticklabels(groups); ax.set_ylabel("cells"); ax.legend(fontsize=6, frameon=False); _style(ax)
    registry.save(fig, "cell_counts_before_after_per_lane", SECTION_QC, "Cells before and after expression QC, per lane",
                  "Input cells, cells passing the permissive and final gene filters, cells failing the mitochondrial filter and final retained cells.")
    for c in cols:
        fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
        for ax, (stage, df) in zip(axes, (("before QC (all loaded cells)", before), ("after QC (retained cells)", after))):
            for g in groups:
                _ecdf(ax, df.loc[_mask(df, g), c], g, _color(g, groups), log_x=c in LOGX, ls="--" if g == "ALL" else "-")
            ax.set_xlabel(QC_LABEL[c] + (" (+1, log)" if c in LOGX else "")); ax.set_ylabel("ECDF"); ax.set_title(stage, fontsize=9)
            ax.legend(fontsize=6, frameon=False); _style(ax)
        registry.save(fig, f"ecdf_{c}_before_after", SECTION_QC, f"ECDF of {QC_LABEL[c]} before and after QC, per lane")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, (df, ttl) in zip(axes, ((before, "before QC"), (after, "after QC"))):
        for g in _lanes(df):
            s = df[_mask(df, g)]
            ax.scatter(s["total_counts"], s["n_genes_by_counts"], s=1.5, alpha=0.35, linewidths=0, color=_color(g, groups), label=g)
        ax.set_xscale("log"); ax.set_yscale("log"); ax.set_xlabel("total UMIs"); ax.set_ylabel("detected genes"); ax.set_title(ttl, fontsize=9)
        ax.axhline(q.min_genes_final, color="#e34948", ls="--", lw=0.7); ax.legend(fontsize=6, frameon=False, markerscale=6); _style(ax)
    registry.save(fig, "genes_vs_umis_before_after", SECTION_QC, "Detected genes versus total UMIs per cell, before and after QC (red line = final gene threshold)")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, xcol in zip(axes, ("n_genes_by_counts", "total_counts")):
        for g in _lanes(before):
            s = before[_mask(before, g)]
            ax.scatter(s[xcol], s["pct_counts_mt"], s=1.5, alpha=0.35, linewidths=0, color=_color(g, groups), label=g)
        ax.set_xscale("log"); ax.set_xlabel(QC_LABEL[xcol]); ax.set_ylabel("% mitochondrial"); ax.axhline(q.max_pct_mt, color="#e34948", ls="--", lw=0.7)
        ax.legend(fontsize=6, frameon=False, markerscale=6); _style(ax)
    registry.save(fig, "pct_mt_vs_genes_and_umis", SECTION_QC, "Mitochondrial percentage versus detected genes and total UMIs (all loaded cells; red line = threshold)")
    return tables


# ---------------------------------------------------------------------------
# 2. Pair-guide QC
# ---------------------------------------------------------------------------


def pair_guide_qc(expr: ad.AnnData, guides: Optional[ad.AnnData], cfg: Config, registry: FigureRegistry) -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    obs = expr.obs
    if dg.OBS_PAIR_STATUS not in obs.columns:
        return tables
    groups = _groups(obs)
    G = _guide_matrix(expr, guides, cfg)
    min_umi = max(int(cfg.guides.min_umi), 1)
    scaf = np.asarray(guides.var["scaffold"].astype(str)) if guides is not None and "scaffold" in guides.var.columns else None
    umi_total = np.asarray(G.sum(axis=1)).ravel()
    n_det = np.asarray((G >= min_umi).sum(axis=1)).ravel()
    cA, cC = [str(c) for c in cfg.guides.scaffold_classes]
    umi_by = {}
    if scaf is not None:
        for c in (cA, cC, "unknown"):
            cols = np.flatnonzero(scaf == c)
            umi_by[c] = np.asarray(G[:, cols].sum(axis=1)).ravel() if len(cols) else np.zeros(G.shape[0])
    status = obs[dg.OBS_PAIR_STATUS].astype(str).to_numpy()
    klass = obs[OBS_CLASS].astype(str).to_numpy()

    # ---- tables ----------------------------------------------------------------------
    rows = []
    for g in groups:
        m = _mask(obs, g)
        st = pd.Series(status[m])
        d = {"lane_id": g, "n_cells": int(m.sum()), "cells_with_guide_umi": int((umi_total[m] > 0).sum()),
             "cells_no_guide_umi": int((umi_total[m] == 0).sum()), f"cells_ge1_guide_at_{min_umi}umi": int((n_det[m] >= 1).sum()),
             "median_guide_umis_per_cell": float(np.median(umi_total[m])) if m.any() else np.nan,
             f"median_guides_per_cell_at_{min_umi}umi": float(np.median(n_det[m])) if m.any() else np.nan}
        if umi_by:
            d[f"median_umis_scaffold_{cA}"] = float(np.median(umi_by[cA][m])); d[f"median_umis_scaffold_{cC}"] = float(np.median(umi_by[cC][m]))
            d[f"cells_detecting_{cA}_and_{cC}"] = int(((umi_by[cA][m] >= min_umi) & (umi_by[cC][m] >= min_umi)).sum())
            d[f"cells_detecting_{cA}_only"] = int(((umi_by[cA][m] >= min_umi) & (umi_by[cC][m] < min_umi)).sum())
            d[f"cells_detecting_{cC}_only"] = int(((umi_by[cC][m] >= min_umi) & (umi_by[cA][m] < min_umi)).sum())
        complete = st.isin([dg.STATUS_PAIR_TARGETING, dg.STATUS_PAIR_NTC, dg.STATUS_PAIR_TARGET_NTC, dg.STATUS_PAIR_TARGET_NTC_PROVISIONAL, dg.STATUS_DUAL_TARGET, dg.STATUS_UNRESOLVED])
        d["complete_pair_cells"] = int(complete.sum()); d["complete_pair_fraction"] = float(complete.mean()) if len(st) else np.nan
        d["incomplete_pair_cells"] = int((st == dg.STATUS_INCOMPLETE).sum()); d["incomplete_pair_fraction"] = float((st == dg.STATUS_INCOMPLETE).mean()) if len(st) else np.nan
        d["pair_ambiguity_cells"] = int(st.str.startswith("ambiguous_scaffold").sum())
        d["unknown_guide_cells"] = int((st == dg.STATUS_UNKNOWN_GUIDE).sum()); d["unresolved_pair_cells"] = int((st == dg.STATUS_UNRESOLVED).sum())
        d["below_min_umi_cells"] = int((st == dg.STATUS_BELOW_MIN_UMI).sum()); d["no_guide_cells"] = int((st == dg.STATUS_NO_GUIDE).sum())
        d["targeting_pair_cells"] = int((st == dg.STATUS_PAIR_TARGETING).sum()); d["ntc_pair_cells"] = int((st == dg.STATUS_PAIR_NTC).sum())
        d["targeting_plus_ntc_pair_cells"] = int(st.isin([dg.STATUS_PAIR_TARGET_NTC, dg.STATUS_PAIR_TARGET_NTC_PROVISIONAL]).sum())
        d["dual_target_ambiguous_cells"] = int((st == dg.STATUS_DUAL_TARGET).sum())
        d["primary_pair_assigned_cells"] = int(obs.loc[m, dg.OBS_PAIR_PRIMARY].astype(bool).sum())
        for k in (CLASS_TARGETING, CLASS_NTC, CLASS_AMBIGUOUS, CLASS_UNASSIGNED):
            d[f"class_{k}"] = int((klass[m] == k).sum())
        rows.append(d)
    tables["pair_guide_qc_per_lane"] = pd.DataFrame(rows)
    per_lane = dg.pair_assignment_per_lane(expr)
    if per_lane is not None:
        tables["pair_assignment_status_per_lane"] = per_lane
    # target / pair cell counts per lane
    tmask = klass == CLASS_TARGETING
    ct = pd.crosstab(obs.loc[tmask, OBS_TARGET].astype(str), obs.loc[tmask, LANE_KEY].astype(str)) if tmask.any() and LANE_KEY in obs.columns else pd.DataFrame()
    if len(ct):
        if ct.shape[1] > 1:
            ct["ALL"] = ct.sum(axis=1)
        ct.index.name = "target_gene"
        tables["target_cells_per_lane"] = ct.reset_index()
        pc = pd.crosstab(obs.loc[tmask, OBS_GUIDE].astype(str), obs.loc[tmask, LANE_KEY].astype(str))
        if pc.shape[1] > 1:
            pc["ALL"] = pc.sum(axis=1)
        pc.index.name = "guide_pair"
        pc.insert(0, "target_gene", pc.index.map(obs.loc[tmask].drop_duplicates(OBS_GUIDE).set_index(OBS_GUIDE)[OBS_TARGET].astype(str).to_dict()))
        tables["pair_cells_per_lane"] = pc.reset_index()
    # guide/GEX barcode overlap
    rows = []
    for g in _lanes(obs):
        m = _mask(obs, g)
        rows.append({"lane_id": g, "gex_cells": int(m.sum()), "cells_with_guide_row": int(m.sum()), "cells_with_any_guide_umi": int((umi_total[m] > 0).sum()),
                     "frac_cells_with_guide_umi": float((umi_total[m] > 0).mean()), "note": "guide matrix aligned to GEX barcodes at load; zero rows = no guide UMIs"})
    tables["guide_gex_barcode_overlap"] = pd.DataFrame(rows)

    # ---- figures ----------------------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    for g in groups:
        m = _mask(obs, g)
        _ecdf(axes[0], umi_total[m], g, _color(g, groups), log_x=True, ls="--" if g == "ALL" else "-")
        _ecdf(axes[1], n_det[m], g, _color(g, groups), ls="--" if g == "ALL" else "-")
    axes[0].set_xlabel("guide UMIs per cell (+1)"); axes[0].set_title("Guide UMI distribution per cell", fontsize=9); axes[0].legend(fontsize=6, frameon=False); _style(axes[0])
    axes[1].set_xlabel(f"detected guides per cell (>= {min_umi} UMIs)"); axes[1].set_xlim(0, 15); axes[1].set_title("Detected guides per cell", fontsize=9); _style(axes[1])
    if umi_by:
        sub = np.random.default_rng(0).choice(G.shape[0], size=min(G.shape[0], 40000), replace=False)
        axes[2].scatter(umi_by[cA][sub] + 1, umi_by[cC][sub] + 1, s=2, alpha=0.3, linewidths=0, c=[STATUS_COLORS.get(v, "#999") for v in status[sub]])
        axes[2].set_xscale("log"); axes[2].set_yscale("log"); axes[2].set_xlabel(f"scaffold-{cA} guide UMIs + 1"); axes[2].set_ylabel(f"scaffold-{cC} guide UMIs + 1")
        for k, col in STATUS_COLORS.items():
            if k in set(status):
                axes[2].scatter([], [], c=col, s=12, label=k)
        axes[2].legend(fontsize=5, frameon=False); axes[2].set_title("Guide UMIs by scaffold (colour = pair status)", fontsize=9); _style(axes[2])
    registry.save(fig, "pair_guide_umis_detection_by_scaffold", SECTION_GUIDES, "Guide UMIs per cell, detected guides per cell, and scaffold-A versus scaffold-C UMIs")
    tab = pd.crosstab(obs[LANE_KEY].astype(str), pd.Series(status, index=obs.index, name="status")) if LANE_KEY in obs.columns else pd.DataFrame()
    if len(tab):
        if len(tab) > 1:
            tab.loc["ALL"] = tab.sum()
        order = [s for s in dg.PAIR_STATUS_ORDER if s in tab.columns]
        fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
        bottom = np.zeros(len(tab))
        for c in order:
            axes[0].bar(tab.index, tab[c], bottom=bottom, color=STATUS_COLORS.get(c, "#999"), label=c); bottom += tab[c].to_numpy()
        axes[0].set_ylabel("expression-QC-pass cells"); axes[0].set_title("Pair-assignment status per lane", fontsize=9); axes[0].legend(fontsize=6, frameon=False, bbox_to_anchor=(1, 1), loc="upper left"); _style(axes[0])
        frac = tab.div(tab.sum(axis=1), axis=0)[order]
        x = np.arange(len(order)); w = 0.8 / len(tab)
        for i, g in enumerate(tab.index):
            axes[1].bar(x + i * w, frac.loc[g], width=w, color=_color(g, groups), label=g)
        axes[1].set_xticks(x + 0.4 - w / 2); axes[1].set_xticklabels(order, fontsize=6, rotation=35, ha="right"); axes[1].set_ylabel("fraction of cells"); axes[1].legend(fontsize=6, frameon=False); _style(axes[1])
        registry.save(fig, "pair_assignment_status_counts_and_fractions", SECTION_GUIDES, "Pair-assignment status counts and fractions per lane (primary labels: pair_targeting and pair_non_targeting)")
    if "target_cells_per_lane" in tables:
        t = tables["target_cells_per_lane"].set_index("target_gene")
        lanes_only = [c for c in t.columns if c != "ALL"]
        t = t.loc[t[lanes_only].sum(axis=1).sort_values(ascending=False).index]
        fig, ax = plt.subplots(figsize=(max(8, 0.3 * len(t)), 4))
        bottom = np.zeros(len(t))
        for g in lanes_only:
            ax.bar(t.index, t[g], bottom=bottom, color=_color(g, groups), label=g); bottom += t[g].to_numpy()
        ax.axhline(cfg.perturbation.min_cells_per_target, color="#e34948", ls="--", lw=0.8, label=f"min cells per target ({cfg.perturbation.min_cells_per_target})")
        ax.set_ylabel("pair_targeting cells"); ax.tick_params(axis="x", rotation=90, labelsize=6); ax.legend(fontsize=6, frameon=False); _style(ax)
        registry.save(fig, "target_pair_cells_per_lane", SECTION_GUIDES, "Cells with a primary targeting pair per target and lane")
    return tables


def single_guide_diagnostic(expr: ad.AnnData, registry: FigureRegistry) -> Dict[str, pd.DataFrame]:
    """Diagnostic-only comparison of the historical single-guide rule with the pair assignment."""
    tables: Dict[str, pd.DataFrame] = {}
    tab = dg.single_guide_diagnostic_table(expr)
    if tab is None:
        return tables
    tables["single_guide_diagnostic_vs_pair"] = tab
    ct = tab.set_index("single_guide_diagnostic_class").drop(columns="n_cells")
    fig, ax = plt.subplots(figsize=(12, 3.6))
    im = ax.imshow(ct.to_numpy(dtype=float), cmap="Blues", aspect="auto")
    ax.set_xticks(range(ct.shape[1])); ax.set_xticklabels(ct.columns, fontsize=6, rotation=35, ha="right")
    ax.set_yticks(range(ct.shape[0])); ax.set_yticklabels(ct.index, fontsize=7)
    for i in range(ct.shape[0]):
        for j in range(ct.shape[1]):
            v = ct.iloc[i, j]
            ax.text(j, i, f"{int(v):,}", ha="center", va="center", fontsize=6, color="white" if v > ct.values.max() / 2 else "black")
    ax.set_title("DIAGNOSTIC ONLY: single-guide top-vs-second class (rows) versus pair-assignment status (columns)", fontsize=9)
    registry.save(fig, "single_guide_diagnostic_vs_pair_status", SECTION_GUIDES,
                  "Diagnostic comparison of the historical single-guide rule with the primary pair assignment (not used for any result)")
    return tables


# ---------------------------------------------------------------------------
# 3. Clustering annotations
# ---------------------------------------------------------------------------


def clustering_pair_figures(expr: ad.AnnData, cfg: Config, registry: FigureRegistry) -> Dict[str, pd.DataFrame]:
    tables: Dict[str, pd.DataFrame] = {}
    obs = expr.obs
    ck = cfg.enrichment.cluster_key if cfg.enrichment.cluster_key in obs.columns else "leiden"
    if ck not in obs.columns or dg.OBS_PAIR_STATUS not in obs.columns:
        return tables
    status = obs[dg.OBS_PAIR_STATUS].astype(str)
    klass = obs[OBS_CLASS].astype(str)
    coarse = np.where(klass == CLASS_TARGETING, "targeting pair", np.where(klass == CLASS_NTC, "NTC pair",
                      np.where(status == dg.STATUS_INCOMPLETE, "incomplete pair", np.where(status.str.startswith("ambiguous_scaffold"), "pair-ambiguous",
                      np.where(status == dg.STATUS_DUAL_TARGET, "dual-target", "unassigned / other")))))
    coarse = pd.Series(coarse, index=obs.index, name="pair_status_coarse")
    rng = np.random.default_rng(cfg.run.seed)
    panels = []
    if LANE_KEY in obs.columns:
        panels.append(("sample / well", obs[LANE_KEY].astype(str)))
    if "condition" in obs.columns:
        panels.append(("inferred condition", obs["condition"].astype(str)))
    panels.append(("pair status", coarse))
    for rep, key in (("pca", "X_pca"), ("umap", "X_umap")):
        if key not in expr.obsm:
            continue
        E = np.asarray(expr.obsm[key])[:, :2]
        order = rng.permutation(E.shape[0])
        pl = panels + ([("Leiden cluster", obs[ck].astype(str))] if rep == "umap" else [])
        fig, axes = plt.subplots(1, len(pl), figsize=(4.6 * len(pl), 4.2), squeeze=False)
        for ax, (name, lab) in zip(axes.ravel(), pl):
            lab = lab.to_numpy(); keys = sorted(pd.unique(lab), key=str)
            cols = np.array([_color(v, keys) for v in lab])
            ax.scatter(E[order, 0], E[order, 1], s=1.2, c=cols[order], linewidths=0, alpha=0.6)
            if len(keys) <= 30:
                for v in keys:
                    ax.scatter([], [], c=_color(v, keys), s=14, label=f"{v} ({int((lab == v).sum()):,})")
                ax.legend(fontsize=5, frameon=False, markerscale=1.2, ncol=2 if len(keys) > 12 else 1)
            ax.set_title(f"{rep.upper()} coloured by {name}", fontsize=9); ax.set_xticks([]); ax.set_yticks([])
        registry.save(fig, f"{rep}_by_sample_condition_pair_status", SECTION_CLUSTERING, f"{rep.upper()} coloured by sample, condition and pair status")
    sizes = obs[ck].astype(str).value_counts()
    sizes = sizes.reindex(sorted(sizes.index, key=lambda s: int(s) if str(s).isdigit() else s))
    fig, ax = plt.subplots(figsize=(max(6, 0.35 * len(sizes)), 3.5))
    ax.bar(sizes.index, sizes.values, color="#2a78d6"); ax.set_ylabel("cells"); ax.set_xlabel("Leiden cluster"); _style(ax)
    registry.save(fig, "cluster_sizes", SECTION_CLUSTERING, "Cells per Leiden cluster")
    comps = {"sample": obs[LANE_KEY].astype(str) if LANE_KEY in obs.columns else None, "pair_status": status, "assignment_class": coarse}
    rows = []
    fig, axes = plt.subplots(1, 3, figsize=(16, 4))
    for ax, (name, lab) in zip(axes, comps.items()):
        if lab is None:
            ax.axis("off"); continue
        ct = pd.crosstab(obs[ck].astype(str), lab)
        ct = ct.reindex(sizes.index)
        frac = ct.div(ct.sum(axis=1), axis=0)
        keys = list(frac.columns)
        bottom = np.zeros(len(frac))
        for v in keys:
            ax.bar(frac.index, frac[v], bottom=bottom, color=STATUS_COLORS.get(v, _color(v, keys)), label=v); bottom += frac[v].to_numpy()
        ax.set_ylabel("fraction of cluster"); ax.set_xlabel("Leiden cluster"); ax.set_title(f"Cluster composition by {name}", fontsize=9)
        ax.legend(fontsize=5, frameon=False, bbox_to_anchor=(1, 1), loc="upper left"); _style(ax)
        for cl in ct.index:
            for v in keys:
                rows.append({"cluster": cl, "composition_by": name, "category": v, "n_cells": int(ct.loc[cl, v]), "frac_of_cluster": float(frac.loc[cl, v])})
    registry.save(fig, "cluster_composition_sample_pairstatus_class", SECTION_CLUSTERING, "Cluster composition by sample, pair status and targeting/NTC/unresolved class")
    tables["cluster_composition"] = pd.DataFrame(rows)
    tables["cluster_sizes"] = sizes.rename_axis("cluster").reset_index(name="n_cells")
    return tables


# ---------------------------------------------------------------------------
# 4. Pair-level perturbation-expression analysis
# ---------------------------------------------------------------------------


def _vec(expr, gene):
    X = expr.layers["lognorm"] if "lognorm" in expr.layers else expr.X
    col = X[:, expr.var_names.get_loc(gene)]
    return np.asarray(col.todense()).ravel() if sparse.issparse(col) else np.asarray(col).ravel()


def pair_perturbation(expr: ad.AnnData, cfg: Config, registry: FigureRegistry) -> Dict[str, pd.DataFrame]:
    """Target- and pair-level target-transcript tests with pair labels as primary."""
    tables: Dict[str, pd.DataFrame] = {}
    obs = expr.obs
    if dg.OBS_PAIR_STATUS not in obs.columns:
        return tables
    pc = cfg.perturbation
    alpha, max_lfc, min_cells, min_ctrl = pc.fdr_alpha, pc.max_log2fc_for_hit, pc.min_cells_per_target, pc.min_control_cells
    groups = _groups(obs)
    status = obs[dg.OBS_PAIR_STATUS].astype(str).to_numpy()
    klass = obs[OBS_CLASS].astype(str).to_numpy()
    tgt = obs[OBS_TARGET].astype(str).to_numpy()
    pair_call = obs[dg.OBS_PAIR].astype(str).to_numpy()
    gid = obs[OBS_GUIDE].astype(str).to_numpy()
    lane = obs[LANE_KEY].astype(str).to_numpy() if LANE_KEY in obs.columns else np.array(["run"] * len(obs))
    ntc_mask = klass == CLASS_NTC  # pair_non_targeting (or designed NTC pairs)
    primary_t = (klass == CLASS_TARGETING)  # pair_targeting (+ provisional target+NTC if that policy is on)
    sens_t = primary_t | (status == dg.STATUS_PAIR_TARGET_NTC)
    strata = {STRATUM_PRIMARY: (primary_t, tgt), STRATUM_SENSITIVITY: (sens_t, np.where(status == dg.STATUS_PAIR_TARGET_NTC, pair_call, tgt))}
    targets = sorted(set(tgt[primary_t]) | set(pair_call[status == dg.STATUS_PAIR_TARGET_NTC]))
    present = {t: t for t in targets if t in expr.var_names}
    absent = sorted(set(targets) - set(present))
    logger.info("Pair perturbation: %d targets with primary pairs, %d measurable by symbol; absent from matrix: %s", len(set(tgt[primary_t])), len([t for t in present if t in set(tgt[primary_t])]), absent)
    cache: Dict[str, np.ndarray] = {}
    vec = lambda g: cache.setdefault(g, _vec(expr, g))

    def test(mp, mc, gene):
        if mp.sum() < min_cells or mc.sum() < min_ctrl:
            return None
        v = vec(gene)
        return compare_groups(v[mp], v[mc])

    rows_t, rows_p = [], []
    for t, gene in present.items():
        for g in groups:
            wm = _mask(obs, g)
            m_ntc = ntc_mask & wm
            for stratum, (tm, tlab) in strata.items():
                mp = tm & (tlab == t) & wm
                m_oth = tm & (tlab != t) & wm
                base = {"target_gene": t, "lane_id": g, "assignment_stratum": stratum, "n_target_pair_cells": int(mp.sum()),
                        "n_ntc_pair_cells": int(m_ntc.sum()), "n_other_target_pair_cells": int(m_oth.sum())}
                for ctrl, mc in (("ntc", m_ntc), ("other", m_oth)):
                    r = test(mp, mc, gene)
                    row = dict(base, control=ctrl)
                    row.update(r if r is not None else {"skipped_reason": f"< {min_cells} target-pair cells or < {min_ctrl} control cells"})
                    rows_t.append(row)
                if stratum != STRATUM_PRIMARY:
                    continue
                for pr in sorted(set(gid[mp])):
                    mg = mp & (gid == pr)
                    r = test(mg, m_ntc, gene)
                    a_id, c_id = (pr.split(dg.PAIR_SEP) + [""])[:2]
                    row = dict(base, guide_pair=pr, guide_A_id=a_id, guide_C_id=c_id, control="ntc", n_target_pair_cells=int(mg.sum()))
                    row.update(r if r is not None else {"skipped_reason": f"< {min_cells} cells with this pair or < {min_ctrl} NTC-pair cells"})
                    rows_p.append(row)

    def finish(rows, keys):
        df = pd.DataFrame(rows)
        for c in ("ks_pval", "mwu_pval_less", "log2fc", "pct_knockdown"):
            if c not in df:
                df[c] = np.nan
        df["fdr_ks"] = np.nan; df["fdr_mwu"] = np.nan
        for _, idx in df.groupby(keys, dropna=False).groups.items():
            df.loc[idx, "fdr_ks"] = benjamini_hochberg(df.loc[idx, "ks_pval"].to_numpy(float))
            df.loc[idx, "fdr_mwu"] = benjamini_hochberg(df.loc[idx, "mwu_pval_less"].to_numpy(float))
        df["neg_log10_fdr"] = -np.log10(np.maximum(df["fdr_ks"].astype(float), 1e-300))
        df["neg_log10_fdr_mwu"] = -np.log10(np.maximum(df["fdr_mwu"].astype(float), 1e-300))
        df["direction"] = np.select([df["log2fc"] < 0, df["log2fc"] > 0], ["down", "up"], "none")
        df.loc[df["log2fc"].isna(), "direction"] = "not_tested"
        df["is_hit"] = (df["fdr_ks"] < alpha) & (df["log2fc"] < max_lfc)
        df["hit_status"] = np.where(df["log2fc"].isna(), "not_tested", np.where(df["is_hit"], "target_transcript_depletion_association", "not_significant"))
        df["hit_rule"] = f"fdr_ks < {alpha} and log2fc < {max_lfc}; BH within lane x control x stratum; response = target transcript (lognorm)"
        df["fdr_convention"] = "fdr_ks = raw BH FDR of two-sided KS p; neg_log10_fdr = -log10(max(fdr_ks, 1e-300))"
        return df

    bt = finish(rows_t, ["lane_id", "control", "assignment_stratum"]) if rows_t else pd.DataFrame()
    bp = finish(rows_p, ["lane_id"]) if rows_p else pd.DataFrame()
    tables["pair_perturbation_by_target"] = bt
    tables["pair_perturbation_by_pair"] = bp
    if not len(bt):
        return tables
    prim = bt[(bt.control == "ntc") & (bt.assignment_stratum == STRATUM_PRIMARY)]
    tables["pair_perturbation_primary"] = prim
    # hit counts per lane
    hc = prim.dropna(subset=["log2fc"]).groupby("lane_id").agg(targets_tested=("target_gene", "count"), targets_hit=("is_hit", "sum")).reset_index()
    sens = bt[(bt.control == "ntc") & (bt.assignment_stratum == STRATUM_SENSITIVITY)].dropna(subset=["log2fc"]).groupby("lane_id")["is_hit"].sum().rename("targets_hit_sensitivity_incl_targeting_plus_ntc")
    hc = hc.merge(sens.reset_index(), on="lane_id", how="left")
    tables["pair_perturbation_hit_counts_per_lane"] = hc
    # target support matrix (within run: per lane + pooled)
    pooled_key = "ALL" if "ALL" in groups else groups[0]
    rows = []
    for t in present:
        r = {"target_gene": t}
        sub = prim[prim.target_gene == t].set_index("lane_id")
        n_tested = n_hit = 0
        for g in [x for x in groups if x != "ALL"]:
            h = bool(sub.loc[g, "is_hit"]) if g in sub.index and pd.notna(sub.loc[g, "log2fc"]) else None
            r[f"hit_{g}"] = h; r[f"log2fc_{g}"] = float(sub.loc[g, "log2fc"]) if g in sub.index else np.nan; r[f"fdr_ks_{g}"] = float(sub.loc[g, "fdr_ks"]) if g in sub.index else np.nan
            n_tested += h is not None; n_hit += bool(h)
        r["n_lanes_tested"] = n_tested; r["n_lanes_hit"] = n_hit
        if pooled_key in sub.index:
            r["pooled_log2fc"] = sub.loc[pooled_key, "log2fc"]; r["pooled_fdr_ks"] = sub.loc[pooled_key, "fdr_ks"]; r["pooled_neg_log10_fdr"] = sub.loc[pooled_key, "neg_log10_fdr"]
            r["pooled_hit"] = bool(sub.loc[pooled_key, "is_hit"]) if pd.notna(sub.loc[pooled_key, "log2fc"]) else None
            r["pooled_n_target_pair_cells"] = int(sub.loc[pooled_key, "n_target_pair_cells"])
        s2 = bt[(bt.target_gene == t) & (bt.control == "ntc") & (bt.assignment_stratum == STRATUM_SENSITIVITY) & (bt.lane_id == pooled_key)]
        r["sensitivity_incl_targeting_plus_ntc_hit"] = bool(s2["is_hit"].iloc[0]) if len(s2) and pd.notna(s2["log2fc"].iloc[0]) else None
        o2 = bt[(bt.target_gene == t) & (bt.control == "other") & (bt.assignment_stratum == STRATUM_PRIMARY) & (bt.lane_id == pooled_key)]
        r["other_control_hit"] = bool(o2["is_hit"].iloc[0]) if len(o2) and pd.notna(o2["log2fc"].iloc[0]) else None
        r["well_level_agreement"] = (f"{n_hit}/{n_tested} lanes" if n_tested else "single lane")
        r["biological_replicate_evidence"] = "not available (replicate identity of wells unknown)"
        rows.append(r)
    tables["target_support_matrix"] = pd.DataFrame(rows)

    # ---- figures ---------------------------------------------------------------------------
    pooled = prim[prim.lane_id == pooled_key].dropna(subset=["log2fc"])
    sensp = bt[(bt.control == "ntc") & (bt.assignment_stratum == STRATUM_SENSITIVITY) & (bt.lane_id == pooled_key)].dropna(subset=["log2fc"]).set_index("target_gene")
    fig, ax = plt.subplots(figsize=(6.5, 5))
    ax.scatter(pooled["log2fc"], pooled["neg_log10_fdr"], c=np.where(pooled["is_hit"], "#2a78d6", "#9a9a9a"), s=28)
    for _, r in pooled.iterrows():
        ax.annotate(r["target_gene"], (r["log2fc"], r["neg_log10_fdr"]), fontsize=6, xytext=(2, 2), textcoords="offset points")
    ax.axhline(-np.log10(alpha), color="#e34948", ls="--", lw=0.8); ax.axvline(0, color="#52514e", lw=0.6)
    ax.set_xlabel("log2FC target transcript (targeting pairs vs NTC pairs)"); ax.set_ylabel("-log10(KS FDR)"); _style(ax)
    registry.save(fig, "pair_volcano_target_level", SECTION_PERTURBATION, "Target-level volcano (primary pair labels; blue = KS FDR < alpha and log2FC < 0)")
    bpp = bp[bp.lane_id == pooled_key].dropna(subset=["log2fc"]) if len(bp) else pd.DataFrame()
    if len(bpp):
        fig, ax = plt.subplots(figsize=(6.5, 5))
        ax.scatter(bpp["log2fc"], bpp["neg_log10_fdr"], c=np.where(bpp["is_hit"], "#2a78d6", "#9a9a9a"), s=14, alpha=0.8)
        ax.axhline(-np.log10(alpha), color="#e34948", ls="--", lw=0.8); ax.axvline(0, color="#52514e", lw=0.6)
        ax.set_xlabel("log2FC target transcript (guide pair vs NTC pairs)"); ax.set_ylabel("-log10(KS FDR)"); _style(ax)
        registry.save(fig, "pair_volcano_pair_level", SECTION_PERTURBATION, f"Guide-pair-level volcano ({len(bpp)} pairs with >= {min_cells} cells)")
    wf = pooled.sort_values("log2fc")
    if len(wf):
        fig, ax = plt.subplots(figsize=(max(6, 0.28 * len(wf)), 4))
        ax.bar(wf["target_gene"], wf["log2fc"], color=np.where(wf["is_hit"], "#2a78d6", "#9a9a9a"), label="primary (pair_targeting)")
        ax.scatter(range(len(wf)), sensp["log2fc"].reindex(wf["target_gene"]).values, color="#e34948", s=12, zorder=3, label="sensitivity: + targeting+NTC pairs")
        ax.tick_params(axis="x", rotation=90, labelsize=7); ax.set_ylabel("log2FC vs NTC pairs"); ax.legend(fontsize=7, frameon=False); _style(ax)
        registry.save(fig, "pair_waterfall_target_log2fc", SECTION_PERTURBATION, "Target-transcript log2FC per target (bars = primary pair labels; red dots = sensitivity stratum)")
    for col, cmap in (("log2fc", "RdBu_r"), ("neg_log10_fdr", "Blues")):
        piv = prim.pivot_table(index="target_gene", columns="lane_id", values=col, aggfunc="first").reindex(columns=groups)
        piv = piv.loc[wf["target_gene"]] if len(wf) else piv
        fig, ax = plt.subplots(figsize=(1.2 * len(groups) + 3, 0.22 * len(piv) + 1.5))
        v = np.nanmax(np.abs(piv.to_numpy(dtype=float))) if piv.size and np.isfinite(piv.to_numpy(dtype=float)).any() else 1
        im = ax.imshow(piv.to_numpy(dtype=float), cmap=cmap, aspect="auto", **({"vmin": -v, "vmax": v} if col == "log2fc" else {"vmin": 0}))
        ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, fontsize=8); ax.set_yticks(range(len(piv))); ax.set_yticklabels(piv.index, fontsize=6)
        fig.colorbar(im, ax=ax, label=col)
        registry.save(fig, f"pair_heatmap_{col}_by_lane", SECTION_PERTURBATION, f"{col} of the target transcript by lane (primary pair labels)")
    if len(hc):
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.arange(len(hc)); ax.bar(x - 0.2, hc["targets_tested"], 0.4, color="#d0d0d0", label="tested"); ax.bar(x + 0.2, hc["targets_hit"], 0.4, color="#2a78d6", label="depletion association")
        ax.set_xticks(x); ax.set_xticklabels(hc["lane_id"]); ax.set_ylabel("targets"); ax.legend(fontsize=7, frameon=False); _style(ax)
        registry.save(fig, "pair_hit_counts_per_lane", SECTION_PERTURBATION, "Targets tested and passing the hit criteria per lane (primary pair labels)")
    # ECDFs: one per tested target (targeting pairs vs NTC pairs, per lane + pooled), plus an overview
    tested = pooled.sort_values("fdr_ks")
    overview = tested.head(12)
    fig, axes = plt.subplots(3, 4, figsize=(15, 9)); axes = axes.ravel()
    for ax, (_, r) in zip(axes, overview.iterrows()):
        v = vec(r["target_gene"]); mp = primary_t & (tgt == r["target_gene"])
        _ecdf(ax, v[mp], "targeting pairs", "#2a78d6"); _ecdf(ax, v[ntc_mask], "NTC pairs", "#9a9a9a")
        ax.set_title(f"{r['target_gene']}: log2FC {r['log2fc']:.2f}, FDR {r['fdr_ks']:.1e}", fontsize=8); ax.set_xlabel("lognorm expression"); ax.legend(fontsize=6, frameon=False); _style(ax)
    for ax in axes[len(overview):]:
        ax.axis("off")
    registry.save(fig, "pair_ecdf_overview_top_targets", SECTION_PERTURBATION, "ECDF overview: target-transcript expression in targeting pairs versus NTC pairs (12 most significant targets)")
    for _, r in tested.iterrows():
        t = r["target_gene"]; v = vec(t)
        fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
        for g in groups:
            wm = _mask(obs, g)
            _ecdf(axes[0], v[primary_t & (tgt == t) & wm], f"{g} targeting pairs", _color(g, groups), ls="--" if g == "ALL" else "-")
            _ecdf(axes[1], v[ntc_mask & wm], f"{g} NTC pairs", _color(g, groups), ls="--" if g == "ALL" else "-")
        for ax, ttl in zip(axes, ("targeting pairs", "NTC pairs")):
            ax.set_xlabel(f"{t} lognorm expression"); ax.set_ylabel("ECDF"); ax.set_title(ttl, fontsize=9); ax.legend(fontsize=6, frameon=False); _style(ax)
        fig.suptitle(f"{t}: pooled log2FC {r['log2fc']:.2f}, KS FDR {r['fdr_ks']:.2e}, {int(r['n_target_pair_cells'])} targeting-pair cells", fontsize=9)
        registry.save(fig, f"ecdf_{t}", SECTION_ECDF, f"ECDF of {t} expression per lane: targeting pairs vs NTC pairs", in_report=False)
    # pair-level expression distributions for the top targets
    if len(bpp):
        top = tested.head(6)
        fig, axes = plt.subplots(2, 3, figsize=(15, 7)); axes = axes.ravel()
        for ax, (_, r) in zip(axes, top.iterrows()):
            t = r["target_gene"]; v = vec(t)
            pairs = bpp[bpp.target_gene == t].sort_values("log2fc")
            _ecdf(ax, v[ntc_mask], "NTC pairs", "#9a9a9a")
            for i, (_, pr) in enumerate(pairs.iterrows()):
                _ecdf(ax, v[primary_t & (gid == pr["guide_pair"])], f"{pr['guide_pair']} ({pr['log2fc']:.2f})", _color(i))
            ax.set_title(t, fontsize=9); ax.set_xlabel("lognorm expression"); ax.legend(fontsize=5, frameon=False); _style(ax)
        for ax in axes[len(top):]:
            ax.axis("off")
        registry.save(fig, "pair_level_expression_distributions", SECTION_PERTURBATION, "Guide-pair-level target-transcript ECDFs for the six most significant targets")
    return tables
