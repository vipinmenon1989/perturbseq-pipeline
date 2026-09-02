#!/usr/bin/env python3
"""Pancreatic Diabetes Perturb-seq Analysis Workflow.

A dedicated, biologically-grounded analysis workflow for the pancreatic differentiation
Perturb-seq dataset (111,581 cells x 36,601 genes, 37 genotypes including WT).

This workflow imports and orchestrates the validated mathematical algorithms from
``perturbseq_pipeline`` without modifying or redesigning the generic pipeline:
  - PS score (pertps)
  - lochNESS continuous neighborhood enrichment
  - Energy Distance / permutation DistanceTest vs WT
  - DistanceSpace (pairwise manifold, PCoA, phenotype similarity groups)
  - Cell-type enrichment across curated cell states (celltype_2) stratified by orig.ident
  - Stage 7 co-functional modules (M1-M6) and gene programs (P1-P4)
  - Program pathway enrichment (Hallmark, Reactome, GO BP)

Usage:
    python workflows/diabetes_analysis.py \\
        --input ../data/diabetes.h5ad \\
        --outdir results/diabetes_specific \\
        --n-jobs 32
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

import anndata as ad
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from scipy import sparse, stats
from scipy.cluster.hierarchy import dendrogram, fcluster, linkage
from scipy.spatial.distance import squareform
import seaborn as sns

# ===========================================================================
# Reused functions and classes from perturbseq_pipeline
# ===========================================================================
from perturbseq_pipeline.config import Config
from perturbseq_pipeline.cluster import (
    LOGNORM_LAYER,
    _run_pca_on_hvgs,
    _select_hvgs,
    normalize,
)
from perturbseq_pipeline.compute import (
    log_compute_decision,
    resolve_stage_backend,
    run_parallel,
)
from perturbseq_pipeline.distance import (
    DistanceResults,
    DistanceSpaceResults,
    compute_distance_space,
    compute_energy_distance,
    compute_pcoa_coordinates,
    compute_perturbation_distance,
    energy_distance_from_cdist,
)
from perturbseq_pipeline.enrichment import (
    EnrichmentResults,
    enrichment_matrix,
    significance_matrix,
    test_cluster_enrichment,
)
from perturbseq_pipeline.gene_sets import (
    clean_term_name,
    run_program_enrichment,
)
from perturbseq_pipeline.guides import (
    CLASS_NTC,
    CLASS_TARGETING,
    OBS_CLASS,
    OBS_TARGET,
)
from perturbseq_pipeline.lochness import (
    LOCHNESS_SELF,
    LochnessResults,
    attach_scores as attach_lochness_scores,
    compute_lochness,
)
from perturbseq_pipeline.modules import (
    ModulesResults,
    build_effect_matrix,
    cluster_axis,
    compute_modules,
    module_program_strength,
    select_genes,
    select_perturbations,
    tf_network,
)
from perturbseq_pipeline.perturbation import (
    CONTROL_NTC,
    benjamini_hochberg,
    control_masks,
)
from perturbseq_pipeline.ps_score import (
    PSResults,
    attach_scores as attach_ps_scores,
    compute_ps_scores,
    pertps_available,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("diabetes_analysis")

# ===========================================================================
# Domain-Specific Constants & Mappings
# ===========================================================================

REQUIRED_OBS_COLUMNS = ["genotype", "sgrna", "celltype_2", "orig.ident"]

STAGE_MAPPING = {
    "Sample_A_WT": "WT",
    "Sample_B_WT": "WT",
    "Sample_C_WT": "WT",
    "Sample_D_WT": "WT",
    "Sample_E_WT": "WT",
    "Sample_F_WT": "WT",
    "Sample_G_1_ESC": "ESC",
    "Sample_G_2_ESC": "ESC",
    "Sample_H_DE": "DE",
    "Sample_I_PFG": "PFG",
    "Sample_J_PP": "PP",
    "Sample_L_1_3DEC": "3DEC",
    "Sample_L_2_3DEC": "3DEC",
}

STAGE_ORDER = ["WT", "ESC", "DE", "PFG", "PP", "3DEC"]

# Cell type display ordering matching pancreatic differentiation progression
CELLTYPE_ORDER = [
    "ESC",
    "ESC (D3)",
    "DE",
    "PFG",
    "PGT",
    "PP",
    "PDP",
    "EnP",
    "SC-EC",
    "SC-alpha",
    "SC-beta",
    "SC-delta",
    "Liver",
    "Stromal",
    "Endothelial",
]

CELLTYPE_PALETTE = {
    "ESC": "#2b6cb0",
    "ESC (D3)": "#4299e1",
    "DE": "#319795",
    "PFG": "#38a169",
    "PGT": "#68d391",
    "PP": "#d69e2e",
    "PDP": "#dd6b20",
    "EnP": "#e53e3e",
    "SC-EC": "#805ad5",
    "SC-alpha": "#b83280",
    "SC-beta": "#3182ce",
    "SC-delta": "#4fd1c5",
    "Liver": "#805ad5",
    "Stromal": "#a0aec0",
    "Endothelial": "#718096",
}

STAGE_PALETTE = {
    "WT": "#4a5568",
    "ESC": "#3182ce",
    "DE": "#319795",
    "PFG": "#38a169",
    "PP": "#dd6b20",
    "3DEC": "#805ad5",
}


# ===========================================================================
# Helper Functions
# ===========================================================================


def sanitize_identifier(name: str) -> str:
    """Sanitize identifier for HDF5 obs column names and filenames.

    Replaces '/', '\\', ':', whitespace, and invalid characters with '__'.
    Biological values in 'genotype' and tables remain untouched (e.g. 'TET1/2/3').

    Example:
        sanitize_identifier("TET1/2/3") -> "TET1__2__3"
    """
    return re.sub(r"[/\\:\s]+", "__", str(name)).strip("_")


def derive_development_stage(orig_ident_series: pd.Series) -> pd.Series:
    """Derive presentation-friendly development_stage from orig.ident.

    Mapping:
        Sample_A_WT ... Sample_F_WT -> WT
        Sample_G_1_ESC, Sample_G_2_ESC -> ESC
        Sample_H_DE -> DE
        Sample_I_PFG -> PFG
        Sample_J_PP -> PP
        Sample_L_1_3DEC, Sample_L_2_3DEC -> 3DEC
    """
    mapped = orig_ident_series.map(STAGE_MAPPING)
    if mapped.isna().any():
        # Fallback regex parser for unmapped sample names
        unmapped = orig_ident_series[mapped.isna()].astype(str)
        extracted = unmapped.str.extract(
            r"(?:_)?(WT|ESC|DE|PFG|PP|3DEC|PGT|PDP|EnP)$", re.IGNORECASE
        )[0]
        mapped = mapped.fillna(extracted).fillna(orig_ident_series.astype(str))
    return mapped.astype(str)


def compute_metric_correlation(
    x: Sequence[float],
    y: Sequence[float],
) -> Tuple[float, float, int]:
    """Compute Spearman rank correlation between two metrics.

    Returns:
        Tuple of (Spearman rho, p-value, n_pairs).
        Filters out NaN/Inf pairs.
    """
    x_arr = np.asarray(x, dtype=np.float64)
    y_arr = np.asarray(y, dtype=np.float64)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    n = int(mask.sum())
    if n < 3:
        return float("nan"), float("nan"), n
    res = stats.spearmanr(x_arr[mask], y_arr[mask])
    return float(res.statistic), float(res.pvalue), n


def validate_dataset(adata: ad.AnnData) -> None:
    """Validate required obs columns and print dataset statistics at startup."""
    missing = [c for c in REQUIRED_OBS_COLUMNS if c not in adata.obs.columns]
    if missing:
        raise ValueError(
            f"Dataset is missing required obs columns: {missing}. "
            f"Available obs columns: {list(adata.obs.columns)}"
        )

    n_cells = adata.n_obs
    n_genes = adata.n_vars
    genotypes = adata.obs["genotype"].astype(str)
    n_genotypes = genotypes.nunique()
    n_wt = int((genotypes == "WT").sum())
    n_non_wt = n_genotypes - (1 if "WT" in genotypes.values else 0)
    n_sgrnas = adata.obs["sgrna"].nunique()
    celltype_counts = adata.obs["celltype_2"].value_counts()
    n_celltypes = len(celltype_counts)

    logger.info("=" * 70)
    logger.info("DIABETES PERTURB-SEQ DATASET VALIDATION")
    logger.info("=" * 70)
    logger.info("  Total cells:             %s", f"{n_cells:,}")
    logger.info("  Total genes/features:    %s", f"{n_genes:,}")
    logger.info("  Total genotypes:         %d", n_genotypes)
    logger.info("  WT control cells:        %s", f"{n_wt:,}")
    logger.info("  Non-WT perturbations:    %d", n_non_wt)
    logger.info("  Distinct sgRNAs:         %d", n_sgrnas)
    logger.info("  Curated cell states:     %d (celltype_2)", n_celltypes)
    logger.info("=" * 70)


def prepare_diabetes_anndata(adata: ad.AnnData, cfg: Config) -> ad.AnnData:
    """Prepare diabetes AnnData with developmental stage and internal pipeline columns."""
    # 1. Derive presentation-friendly development_stage
    adata.obs["development_stage"] = derive_development_stage(adata.obs["orig.ident"])

    # 2. Add internal compatibility columns for perturbseq_pipeline algorithms
    # WT is the biological control (mapped to CLASS_NTC internally for APIs that check CLASS_NTC)
    adata.obs[OBS_CLASS] = np.where(
        adata.obs["genotype"] == "WT", CLASS_NTC, CLASS_TARGETING
    )
    # Target gene is the biological perturbation identity (genotype)
    adata.obs[OBS_TARGET] = adata.obs["genotype"].astype(str)
    # Sample identifier for stratified analyses
    adata.obs["lane_id"] = adata.obs["orig.ident"].astype(str)

    # 3. Ensure PCA representation is computed if absent
    if "X_pca" not in adata.obsm:
        logger.info("X_pca is absent. Computing PCA on 3000 HVGs (50 PCs)...")
        _select_hvgs(adata, cfg)
        _run_pca_on_hvgs(adata, cfg)
    else:
        logger.info("Using existing X_pca representation: shape %s", adata.obsm["X_pca"].shape)

    # 4. Ensure UMAP representation is present if absent
    if "X_umap" not in adata.obsm and "X_pca" in adata.obsm:
        logger.info("X_umap is absent. Deriving 2D coordinates from X_pca...")
        adata.obsm["X_umap"] = np.asarray(adata.obsm["X_pca"][:, :2], dtype=np.float32)

    return adata


# ===========================================================================
# Analytical Step Functions
# ===========================================================================


def run_diabetes_ps_analysis(
    adata: ad.AnnData,
    cfg: Config,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate per-cell perturbation scores (PS) at genotype level vs WT."""
    logger.info("=== Running PS Score Analysis (pertps) ===")

    if not pertps_available():
        logger.warning("pertps is not installed; skipping per-cell PS scoring.")
        return pd.DataFrame(), pd.DataFrame()

    ps_results = compute_ps_scores(adata, cfg)
    if ps_results is None or ps_results.summary.empty:
        logger.warning("PS scoring returned empty results.")
        return pd.DataFrame(), pd.DataFrame()

    # Attach scores to adata.obs
    attach_ps_scores(adata, ps_results)

    summary_df = ps_results.summary.copy()
    if "target_gene" in summary_df.columns:
        summary_df = summary_df.rename(columns={"target_gene": "genotype"})

    # Populate canonical column aliases for downstream consumers
    if "mean_ps" in summary_df.columns and "ps_mean" not in summary_df.columns:
        summary_df["ps_mean"] = summary_df["mean_ps"]
    if "median_ps" in summary_df.columns and "ps_median" not in summary_df.columns:
        summary_df["ps_median"] = summary_df["median_ps"]
    if "pct_successful_kd" in summary_df.columns and "ps_responder_fraction" not in summary_df.columns:
        summary_df["ps_responder_fraction"] = summary_df["pct_successful_kd"] / 100.0

    skipped_df = ps_results.skipped.copy()
    if not skipped_df.empty and "target_gene" in skipped_df.columns:
        skipped_df = skipped_df.rename(columns={"target_gene": "genotype"})

    logger.info("PS scoring complete: %d targets evaluated.", len(summary_df))
    return summary_df, skipped_df


def compute_lochness_directional_summary(
    scores: Union[np.ndarray, Sequence[float]],
) -> Dict[str, float]:
    """Calculate positive, negative, absolute, and net lochNESS summaries for a 1D score vector.

    Parameters
    ----------
    scores : array-like
        Array of per-cell lochNESS scores (L_i).

    Returns
    -------
    dict
        Dictionary containing:
        - lochness_mean, lochness_median (net signed)
        - lochness_positive_mean, lochness_positive_median, lochness_positive_fraction, lochness_positive_q90
        - lochness_negative_mean, lochness_negative_median, lochness_negative_fraction, lochness_negative_q10 (signed negative)
        - lochness_abs_mean, lochness_abs_median
    """
    scores_arr = np.asarray(scores, dtype=np.float64)
    finite_scores = scores_arr[np.isfinite(scores_arr)]
    n_scored = len(finite_scores)

    if n_scored == 0:
        return {
            "lochness_mean": float("nan"),
            "lochness_median": float("nan"),
            "lochness_positive_mean": float("nan"),
            "lochness_positive_median": float("nan"),
            "lochness_positive_fraction": float("nan"),
            "lochness_positive_q90": float("nan"),
            "lochness_negative_mean": float("nan"),
            "lochness_negative_median": float("nan"),
            "lochness_negative_fraction": float("nan"),
            "lochness_negative_q10": float("nan"),
            "lochness_abs_mean": float("nan"),
            "lochness_abs_median": float("nan"),
        }

    # Net summaries
    net_mean = float(np.mean(finite_scores))
    net_median = float(np.median(finite_scores))

    # Positive side (L_i > 0)
    pos_mask = finite_scores > 0
    pos_scores = finite_scores[pos_mask]
    n_pos = len(pos_scores)
    pos_frac = float(n_pos / n_scored)
    pos_mean = float(np.mean(pos_scores)) if n_pos > 0 else float("nan")
    pos_median = float(np.median(pos_scores)) if n_pos > 0 else float("nan")
    pos_q90 = float(np.percentile(pos_scores, 90)) if n_pos > 0 else float("nan")

    # Negative side (L_i < 0) - remains signed negative
    neg_mask = finite_scores < 0
    neg_scores = finite_scores[neg_mask]
    n_neg = len(neg_scores)
    neg_frac = float(n_neg / n_scored)
    neg_mean = float(np.mean(neg_scores)) if n_neg > 0 else float("nan")
    neg_median = float(np.median(neg_scores)) if n_neg > 0 else float("nan")
    neg_q10 = float(np.percentile(neg_scores, 10)) if n_neg > 0 else float("nan")

    # Absolute magnitude
    abs_scores = np.abs(finite_scores)
    abs_mean = float(np.mean(abs_scores))
    abs_median = float(np.median(abs_scores))

    return {
        "lochness_mean": net_mean,
        "lochness_median": net_median,
        "lochness_positive_mean": pos_mean,
        "lochness_positive_median": pos_median,
        "lochness_positive_fraction": pos_frac,
        "lochness_positive_q90": pos_q90,
        "lochness_negative_mean": neg_mean,
        "lochness_negative_median": neg_median,
        "lochness_negative_fraction": neg_frac,
        "lochness_negative_q10": neg_q10,
        "lochness_abs_mean": abs_mean,
        "lochness_abs_median": abs_median,
    }


def compute_ps_by_genotype(adata: ad.AnnData) -> pd.DataFrame:
    """Calculate genotype-level PS summary using only valid per-cell PS values.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'genotype' and 'ps_score' in obs.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['genotype', 'n_cells', 'n_valid_ps', 'mean_ps', 'median_ps', 'q25_ps', 'q75_ps', 'pct_high_ps']
        sorted by median_ps descending.
    """
    if "ps_score" not in adata.obs:
        return pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    ps_scores = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)

    non_wt_mask = (genotypes != "WT")
    if not np.any(non_wt_mask):
        return pd.DataFrame()

    unique_targets = sorted(set(genotypes[non_wt_mask]))
    rows = []
    for target in unique_targets:
        t_mask = (genotypes == target)
        n_cells = int(np.sum(t_mask))
        scores = ps_scores[t_mask]
        valid_scores = scores[np.isfinite(scores)]
        n_valid = len(valid_scores)

        if n_valid > 0:
            mean_ps = float(np.mean(valid_scores))
            median_ps = float(np.median(valid_scores))
            q25_ps = float(np.percentile(valid_scores, 25))
            q75_ps = float(np.percentile(valid_scores, 75))
            pct_high_ps = float(100.0 * np.mean(valid_scores >= 0.5))
        else:
            mean_ps = float("nan")
            median_ps = float("nan")
            q25_ps = float("nan")
            q75_ps = float("nan")
            pct_high_ps = float("nan")

        rows.append({
            "genotype": target,
            "n_cells": n_cells,
            "n_valid_ps": n_valid,
            "mean_ps": mean_ps,
            "median_ps": median_ps,
            "q25_ps": q25_ps,
            "q75_ps": q75_ps,
            "pct_high_ps": pct_high_ps,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="median_ps", ascending=False, na_position="last").reset_index(drop=True)
    return df


def compute_ps_by_celltype2(adata: ad.AnnData) -> pd.DataFrame:
    """Calculate curated cell type (celltype_2) PS summary using only valid per-cell PS values.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'celltype_2' and 'ps_score' in obs.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['celltype_2', 'n_cells', 'mean_ps', 'median_ps', 'q25_ps', 'q75_ps']
    """
    if "ps_score" not in adata.obs or "celltype_2" not in adata.obs:
        return pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    celltypes = adata.obs["celltype_2"].astype(str).to_numpy()
    ps_scores = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)

    non_wt_mask = (genotypes != "WT")
    present_cts = set(celltypes[non_wt_mask]) if np.any(non_wt_mask) else set(celltypes)
    ordered_cts = [ct for ct in CELLTYPE_ORDER if ct in present_cts]
    for ct in sorted(present_cts):
        if ct not in ordered_cts:
            ordered_cts.append(ct)

    rows = []
    for ct in ordered_cts:
        ct_mask = (celltypes == ct) & non_wt_mask
        scores = ps_scores[ct_mask]
        valid_scores = scores[np.isfinite(scores)]
        n_valid = len(valid_scores)

        if n_valid > 0:
            mean_ps = float(np.mean(valid_scores))
            median_ps = float(np.median(valid_scores))
            q25_ps = float(np.percentile(valid_scores, 25))
            q75_ps = float(np.percentile(valid_scores, 75))
        else:
            mean_ps = float("nan")
            median_ps = float("nan")
            q25_ps = float("nan")
            q75_ps = float("nan")

        rows.append({
            "celltype_2": ct,
            "n_cells": n_valid,
            "mean_ps": mean_ps,
            "median_ps": median_ps,
            "q25_ps": q25_ps,
            "q75_ps": q75_ps,
        })

    return pd.DataFrame(rows)


def compute_ps_by_genotype_celltype(
    adata: ad.AnnData,
    min_cells: int = 10,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate genotype x celltype_2 PS summary table and masked mean PS matrix.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'genotype', 'celltype_2', and 'ps_score' in obs.
    min_cells : int, default=10
        Minimum valid cell count threshold for heatmap matrix. Below threshold is set to NaN.

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        - summary_table: tidy DataFrame with columns
          ['genotype', 'celltype_2', 'n_cells', 'n_valid_ps', 'mean_ps', 'median_ps']
        - pivot_matrix: matrix of mean_ps (genotype x celltype_2), masked as NaN if n_valid_ps < min_cells.
    """
    if "ps_score" not in adata.obs or "celltype_2" not in adata.obs:
        return pd.DataFrame(), pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    celltypes = adata.obs["celltype_2"].astype(str).to_numpy()
    ps_scores = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)

    non_wt_mask = (genotypes != "WT")
    if not np.any(non_wt_mask):
        return pd.DataFrame(), pd.DataFrame()

    unique_targets = sorted(set(genotypes[non_wt_mask]))
    present_cts = set(celltypes[non_wt_mask])
    ordered_cts = [ct for ct in CELLTYPE_ORDER if ct in present_cts]
    for ct in sorted(present_cts):
        if ct not in ordered_cts:
            ordered_cts.append(ct)

    rows = []
    for target in unique_targets:
        t_mask = (genotypes == target)
        for ct in ordered_cts:
            ct_mask = t_mask & (celltypes == ct)
            n_cells = int(np.sum(ct_mask))
            if n_cells == 0:
                continue

            scores = ps_scores[ct_mask]
            valid_scores = scores[np.isfinite(scores)]
            n_valid = len(valid_scores)

            if n_valid > 0:
                mean_ps = float(np.mean(valid_scores))
                median_ps = float(np.median(valid_scores))
            else:
                mean_ps = float("nan")
                median_ps = float("nan")

            rows.append({
                "genotype": target,
                "celltype_2": ct,
                "n_cells": n_cells,
                "n_valid_ps": n_valid,
                "mean_ps": mean_ps,
                "median_ps": median_ps,
            })

    by_ct_df = pd.DataFrame(rows)
    if by_ct_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    pivot_mat = by_ct_df.pivot(index="genotype", columns="celltype_2", values="mean_ps")
    pivot_n = by_ct_df.pivot(index="genotype", columns="celltype_2", values="n_valid_ps").fillna(0)

    # Mask groups with < min_cells valid PS as NaN (distinct from 0)
    pivot_mat[pivot_n < min_cells] = np.nan

    cols = [c for c in ordered_cts if c in pivot_mat.columns]
    pivot_mat = pivot_mat.reindex(index=unique_targets, columns=cols)

    return by_ct_df, pivot_mat


def compute_ps_by_development_stage(adata: ad.AnnData) -> pd.DataFrame:
    """Calculate developmental stage PS summary using only valid per-cell PS values.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'development_stage' and 'ps_score' in obs.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['development_stage', 'n_cells', 'mean_ps', 'median_ps', 'q25_ps', 'q75_ps']
    """
    if "ps_score" not in adata.obs or "development_stage" not in adata.obs:
        return pd.DataFrame()

    stages = adata.obs["development_stage"].astype(str).to_numpy()
    ps_scores = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)

    present_stages = set(stages)
    ordered_stages = [st for st in STAGE_ORDER if st in present_stages]
    for st in sorted(present_stages):
        if st not in ordered_stages:
            ordered_stages.append(st)

    rows = []
    for st in ordered_stages:
        st_mask = (stages == st)
        scores = ps_scores[st_mask]
        valid_scores = scores[np.isfinite(scores)]
        n_valid = len(valid_scores)

        if n_valid > 0:
            mean_ps = float(np.mean(valid_scores))
            median_ps = float(np.median(valid_scores))
            q25_ps = float(np.percentile(valid_scores, 25))
            q75_ps = float(np.percentile(valid_scores, 75))
        else:
            mean_ps = float("nan")
            median_ps = float("nan")
            q25_ps = float("nan")
            q75_ps = float("nan")

        rows.append({
            "development_stage": st,
            "n_cells": n_valid,
            "mean_ps": mean_ps,
            "median_ps": median_ps,
            "q25_ps": q25_ps,
            "q75_ps": q75_ps,
        })

    return pd.DataFrame(rows)


def compute_lochness_by_genotype(
    adata: ad.AnnData,
    lochness_self: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """Calculate genotype-level signed lochNESS distribution summary.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'genotype' and per-cell lochNESS.
    lochness_self : ndarray, optional
        Per-cell signed lochNESS array. If None, retrieved from adata.obs[LOCHNESS_SELF].

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['genotype', 'n_cells', 'mean_lochness', 'median_lochness', 'positive_fraction',
         'negative_fraction', 'mean_positive_lochness', 'mean_negative_lochness',
         'q10_lochness', 'q90_lochness', 'lochness_abs_mean']
    """
    if lochness_self is None:
        if LOCHNESS_SELF in adata.obs:
            lochness_self = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)
        else:
            return pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    non_wt_mask = (genotypes != "WT")
    if not np.any(non_wt_mask):
        return pd.DataFrame()

    unique_targets = sorted(set(genotypes[non_wt_mask]))
    rows = []
    for target in unique_targets:
        t_mask = (genotypes == target)
        n_cells = int(np.sum(t_mask))
        scores = lochness_self[t_mask]
        valid_scores = scores[np.isfinite(scores)]
        n_valid = len(valid_scores)

        if n_valid > 0:
            mean_loch = float(np.mean(valid_scores))
            median_loch = float(np.median(valid_scores))
            pos_scores = valid_scores[valid_scores > 0]
            neg_scores = valid_scores[valid_scores < 0]
            pos_frac = float(len(pos_scores) / n_valid)
            neg_frac = float(len(neg_scores) / n_valid)
            mean_pos = float(np.mean(pos_scores)) if len(pos_scores) > 0 else float("nan")
            mean_neg = float(np.mean(neg_scores)) if len(neg_scores) > 0 else float("nan")
            q10_loch = float(np.percentile(valid_scores, 10))
            q90_loch = float(np.percentile(valid_scores, 90))
            abs_mean = float(np.mean(np.abs(valid_scores)))
        else:
            mean_loch = float("nan")
            median_loch = float("nan")
            pos_frac = float("nan")
            neg_frac = float("nan")
            mean_pos = float("nan")
            mean_neg = float("nan")
            q10_loch = float("nan")
            q90_loch = float("nan")
            abs_mean = float("nan")

        rows.append({
            "genotype": target,
            "n_cells": n_cells,
            "mean_lochness": mean_loch,
            "median_lochness": median_loch,
            "positive_fraction": pos_frac,
            "negative_fraction": neg_frac,
            "mean_positive_lochness": mean_pos,
            "mean_negative_lochness": mean_neg,
            "q10_lochness": q10_loch,
            "q90_lochness": q90_loch,
            "lochness_abs_mean": abs_mean,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(by="mean_lochness", ascending=False, na_position="last").reset_index(drop=True)
    return df


def compute_lochness_by_celltype2(
    adata: ad.AnnData,
    lochness_self: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """Calculate curated cell type (celltype_2) signed lochNESS summary.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'celltype_2' and per-cell lochNESS.
    lochness_self : ndarray, optional
        Per-cell signed lochNESS array. If None, retrieved from adata.obs[LOCHNESS_SELF].

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['celltype_2', 'n_cells', 'mean_lochness', 'median_lochness', 'positive_fraction',
         'negative_fraction', 'mean_positive_lochness', 'mean_negative_lochness']
    """
    if lochness_self is None:
        if LOCHNESS_SELF in adata.obs:
            lochness_self = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)
        else:
            return pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    celltypes = adata.obs["celltype_2"].astype(str).to_numpy()

    non_wt_mask = (genotypes != "WT")
    present_cts = set(celltypes[non_wt_mask]) if np.any(non_wt_mask) else set(celltypes)
    ordered_cts = [ct for ct in CELLTYPE_ORDER if ct in present_cts]
    for ct in sorted(present_cts):
        if ct not in ordered_cts:
            ordered_cts.append(ct)

    rows = []
    for ct in ordered_cts:
        ct_mask = (celltypes == ct) & non_wt_mask
        scores = lochness_self[ct_mask]
        valid_scores = scores[np.isfinite(scores)]
        n_valid = len(valid_scores)

        if n_valid > 0:
            mean_loch = float(np.mean(valid_scores))
            median_loch = float(np.median(valid_scores))
            pos_scores = valid_scores[valid_scores > 0]
            neg_scores = valid_scores[valid_scores < 0]
            pos_frac = float(len(pos_scores) / n_valid)
            neg_frac = float(len(neg_scores) / n_valid)
            mean_pos = float(np.mean(pos_scores)) if len(pos_scores) > 0 else float("nan")
            mean_neg = float(np.mean(neg_scores)) if len(neg_scores) > 0 else float("nan")
        else:
            mean_loch = float("nan")
            median_loch = float("nan")
            pos_frac = float("nan")
            neg_frac = float("nan")
            mean_pos = float("nan")
            mean_neg = float("nan")

        rows.append({
            "celltype_2": ct,
            "n_cells": n_valid,
            "mean_lochness": mean_loch,
            "median_lochness": median_loch,
            "positive_fraction": pos_frac,
            "negative_fraction": neg_frac,
            "mean_positive_lochness": mean_pos,
            "mean_negative_lochness": mean_neg,
        })

    return pd.DataFrame(rows)


def compute_lochness_by_development_stage(
    adata: ad.AnnData,
    lochness_self: Optional[np.ndarray] = None,
) -> pd.DataFrame:
    """Calculate developmental stage signed lochNESS summary.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'development_stage' and per-cell lochNESS.
    lochness_self : ndarray, optional
        Per-cell signed lochNESS array. If None, retrieved from adata.obs[LOCHNESS_SELF].

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        ['development_stage', 'n_cells', 'mean_lochness', 'median_lochness', 'positive_fraction',
         'negative_fraction', 'mean_positive_lochness', 'mean_negative_lochness']
    """
    if lochness_self is None:
        if LOCHNESS_SELF in adata.obs:
            lochness_self = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)
        else:
            return pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    stages = adata.obs["development_stage"].astype(str).to_numpy()

    non_wt_mask = (genotypes != "WT")
    present_stages = set(stages[non_wt_mask]) if np.any(non_wt_mask) else set(stages)
    ordered_stages = [st for st in STAGE_ORDER if st in present_stages]
    for st in sorted(present_stages):
        if st not in ordered_stages:
            ordered_stages.append(st)

    rows = []
    for st in ordered_stages:
        st_mask = (stages == st) & non_wt_mask
        scores = lochness_self[st_mask]
        valid_scores = scores[np.isfinite(scores)]
        n_valid = len(valid_scores)

        if n_valid > 0:
            mean_loch = float(np.mean(valid_scores))
            median_loch = float(np.median(valid_scores))
            pos_scores = valid_scores[valid_scores > 0]
            neg_scores = valid_scores[valid_scores < 0]
            pos_frac = float(len(pos_scores) / n_valid)
            neg_frac = float(len(neg_scores) / n_valid)
            mean_pos = float(np.mean(pos_scores)) if len(pos_scores) > 0 else float("nan")
            mean_neg = float(np.mean(neg_scores)) if len(neg_scores) > 0 else float("nan")
        else:
            mean_loch = float("nan")
            median_loch = float("nan")
            pos_frac = float("nan")
            neg_frac = float("nan")
            mean_pos = float("nan")
            mean_neg = float("nan")

        rows.append({
            "development_stage": st,
            "n_cells": n_valid,
            "mean_lochness": mean_loch,
            "median_lochness": median_loch,
            "positive_fraction": pos_frac,
            "negative_fraction": neg_frac,
            "mean_positive_lochness": mean_pos,
            "mean_negative_lochness": mean_neg,
        })

    return pd.DataFrame(rows)


def compute_lochness_by_celltype(
    adata: ad.AnnData,
    lochness_self: Optional[np.ndarray] = None,
    min_cells: int = 10,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate genotype x celltype_2 signed lochNESS summary table and masked matrix.

    Parameters
    ----------
    adata : AnnData
        Annotated dataset containing 'genotype' and 'celltype_2' obs columns.
    lochness_self : ndarray, optional
        1D array of per-cell self lochNESS scores. If None, retrieved from adata.obs[LOCHNESS_SELF].
    min_cells : int, default=10
        Minimum cell threshold for genotype x celltype_2 combinations in the heatmap matrix.
        Groups with fewer cells are set to NaN (masked, distinct from zero).

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        - lochness_by_celltype: tidy DataFrame with columns:
          ['genotype', 'celltype_2', 'n_cells', 'mean_lochness', 'median_lochness',
           'positive_fraction', 'negative_fraction', 'mean_positive_lochness', 'mean_negative_lochness']
        - lochness_celltype_matrix: pivoted DataFrame of mean signed lochNESS (genotypes x celltype_2),
          with combinations having < min_cells masked as NaN.
    """
    if lochness_self is None:
        if LOCHNESS_SELF in adata.obs:
            lochness_self = np.asarray(adata.obs[LOCHNESS_SELF], dtype=np.float64)
        else:
            return pd.DataFrame(), pd.DataFrame()

    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    celltypes = adata.obs["celltype_2"].astype(str).to_numpy()

    # Filter for non-WT cells
    non_wt_mask = (genotypes != "WT")
    if not np.any(non_wt_mask):
        return pd.DataFrame(), pd.DataFrame()

    unique_targets = sorted(set(genotypes[non_wt_mask]))

    # Determine column order from CELLTYPE_ORDER present in adata
    present_cts = set(celltypes[non_wt_mask])
    ordered_cts = [ct for ct in CELLTYPE_ORDER if ct in present_cts]
    for ct in sorted(present_cts):
        if ct not in ordered_cts:
            ordered_cts.append(ct)

    rows = []
    for target in unique_targets:
        t_mask = (genotypes == target)
        for ct in ordered_cts:
            ct_mask = t_mask & (celltypes == ct)
            n_cells = int(np.sum(ct_mask))
            if n_cells == 0:
                continue

            scores = lochness_self[ct_mask]
            scores_finite = scores[np.isfinite(scores)]
            n_scored = len(scores_finite)

            if n_scored == 0:
                mean_val = float("nan")
                med_val = float("nan")
                pos_frac = float("nan")
                neg_frac = float("nan")
                mean_pos = float("nan")
                mean_neg = float("nan")
            else:
                mean_val = float(np.mean(scores_finite))
                med_val = float(np.median(scores_finite))
                pos_scores = scores_finite[scores_finite > 0]
                neg_scores = scores_finite[scores_finite < 0]
                pos_frac = float(len(pos_scores) / n_scored)
                neg_frac = float(len(neg_scores) / n_scored)
                mean_pos = float(np.mean(pos_scores)) if len(pos_scores) > 0 else float("nan")
                mean_neg = float(np.mean(neg_scores)) if len(neg_scores) > 0 else float("nan")

            rows.append({
                "genotype": target,
                "celltype_2": ct,
                "n_cells": n_cells,
                "mean_lochness": mean_val,
                "median_lochness": med_val,
                "positive_fraction": pos_frac,
                "negative_fraction": neg_frac,
                "mean_positive_lochness": mean_pos,
                "mean_negative_lochness": mean_neg,
            })

    by_ct_df = pd.DataFrame(rows)
    if by_ct_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Pivot into matrix for heatmap: rows=genotype, columns=celltype_2, values=mean_lochness
    pivot_mat = by_ct_df.pivot(index="genotype", columns="celltype_2", values="mean_lochness")
    pivot_n = by_ct_df.pivot(index="genotype", columns="celltype_2", values="n_cells").fillna(0)

    # Mask groups with < min_cells as NaN (distinct from 0)
    pivot_mat[pivot_n < min_cells] = np.nan

    # Reindex columns to match ordered_cts and rows to unique_targets
    cols = [c for c in ordered_cts if c in pivot_mat.columns]
    pivot_mat = pivot_mat.reindex(index=unique_targets, columns=cols)

    return by_ct_df, pivot_mat


def run_diabetes_lochness_analysis(
    adata: ad.AnnData,
    cfg: Config,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray]:
    """Calculate continuous lochNESS in X_pca space, directional summaries, and link to celltype_2."""
    logger.info("=== Running lochNESS State-Space Localization ===")

    loch_res = compute_lochness(adata, cfg)
    if loch_res is None or loch_res.self_score is None:
        logger.warning("lochNESS computation returned None.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), np.array([], dtype=np.float32)

    # Attach scores to adata.obs (adds LOCHNESS_SELF and per-target columns)
    attach_lochness_scores(adata, loch_res)

    lochness_self = loch_res.self_score
    labels = adata.obs["genotype"].astype(str).to_numpy()
    targeting_mask = (labels != "WT")

    # Summarize per target with celltype_2 linkage
    targets = sorted(set(labels[targeting_mask]))
    lochness_rows = []

    for target in targets:
        mask = (labels == target)
        n_cells = int(mask.sum())
        if n_cells < cfg.lochness.min_cells_per_target:
            continue

        target_scores = lochness_self[mask]
        target_scores_finite = target_scores[np.isfinite(target_scores)]
        if len(target_scores_finite) == 0:
            continue

        target_celltypes = adata.obs.loc[mask, "celltype_2"]

        # Dominant cell type determination (highest frequency among target cells)
        ct_counts = target_celltypes.value_counts()
        dominant_ct = ct_counts.index[0] if len(ct_counts) > 0 else "Unknown"
        dominant_frac = float(ct_counts.iloc[0] / n_cells) if len(ct_counts) > 0 else 0.0

        # Mean lochNESS score within that dominant cell type
        dom_mask = mask & (adata.obs["celltype_2"] == dominant_ct).to_numpy()
        dom_scores = lochness_self[dom_mask]
        dom_scores_finite = dom_scores[np.isfinite(dom_scores)]
        dom_lochness = float(np.mean(dom_scores_finite)) if len(dom_scores_finite) > 0 else np.nan

        # Directional and magnitude lochNESS statistics
        dir_stats = compute_lochness_directional_summary(target_scores_finite)

        lochness_rows.append(
            {
                "genotype": target,
                "n_cells": n_cells,
                **dir_stats,
                "lochness_peak": float(np.percentile(target_scores_finite, 95)),
                "dominant_celltype_2": dominant_ct,
                "dominant_celltype_fraction": dominant_frac,
                "dominant_celltype_lochness": dom_lochness,
            }
        )

    lochness_df = pd.DataFrame(lochness_rows)

    # Compute genotype x celltype_2 signed lochNESS table and matrix
    lochness_by_celltype, lochness_celltype_matrix = compute_lochness_by_celltype(
        adata, lochness_self=lochness_self, min_cells=10
    )

    logger.info("lochNESS localization complete: %d targets evaluated.", len(lochness_df))
    return lochness_df, lochness_by_celltype, lochness_celltype_matrix, lochness_self


def run_diabetes_distance_analysis(
    adata: ad.AnnData,
    cfg: Config,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate Perturbation Distance vs WT (Energy Distance / permutation DistanceTest)."""
    logger.info("=== Running Energy Distance / DistanceTest vs WT ===")

    dist_res = compute_perturbation_distance(adata, cfg)
    if dist_res is None or dist_res.table.empty:
        logger.warning("DistanceTest returned empty results.")
        return pd.DataFrame(), pd.DataFrame()

    table = dist_res.table.copy()
    if "target_gene" in table.columns:
        table = table.rename(columns={"target_gene": "genotype"})

    skipped = dist_res.skipped.copy()
    if not skipped.empty and "target_gene" in skipped.columns:
        skipped = skipped.rename(columns={"target_gene": "genotype"})

    logger.info("DistanceTest complete: %d perturbations tested vs WT.", len(table))
    return table, skipped


def run_diabetes_distance_space_analysis(
    adata: ad.AnnData,
    cfg: Config,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate pairwise DistanceSpace, PCoA coordinates, and Phenotype Similarity Groups."""
    logger.info("=== Running Perturbation Distance Space (Pairwise Manifold) ===")

    ds_res = compute_distance_space(adata, cfg)
    if ds_res is None or ds_res.distance_matrix.empty:
        logger.warning("DistanceSpace returned empty results.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    dist_mat = ds_res.distance_matrix.copy()
    coords = ds_res.coordinates.copy()
    if "target_gene" in coords.columns:
        coords = coords.rename(columns={"target_gene": "genotype"})

    neighbors = ds_res.neighbors.copy()
    if "target" in neighbors.columns:
        neighbors = neighbors.rename(columns={"target": "genotype"})
    if "target_gene" in neighbors.columns:
        neighbors = neighbors.rename(columns={"target_gene": "genotype"})

    pheno_groups = ds_res.phenotype_modules.copy()
    if "target_gene" in pheno_groups.columns:
        pheno_groups = pheno_groups.rename(columns={"target_gene": "genotype"})
    if "phenotype_module" in pheno_groups.columns:
        pheno_groups = pheno_groups.rename(columns={"phenotype_module": "phenotype_group"})
        # Map PM1 -> PG1 (Phenotypic similarity group)
        pheno_groups["phenotype_group"] = pheno_groups["phenotype_group"].str.replace(
            "PM", "PG", regex=False
        )

    logger.info(
        "DistanceSpace complete: %d x %d pairwise matrix, %d phenotype groups.",
        dist_mat.shape[0],
        dist_mat.shape[1],
        pheno_groups["phenotype_group"].nunique() if not pheno_groups.empty else 0,
    )
    return dist_mat, coords, neighbors, pheno_groups


def run_diabetes_enrichment_analysis(
    adata: ad.AnnData,
    cfg: Config,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate genotype x celltype_2 enrichment using WT reference stratified by orig.ident."""
    logger.info("=== Running Genotype x celltype_2 Enrichment Analysis ===")

    enrich_res = test_cluster_enrichment(adata, cfg)
    if enrich_res is None or enrich_res.table.empty:
        logger.warning("Cell-type enrichment returned empty results.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    table = enrich_res.table.copy()
    if "target_gene" in table.columns:
        table = table.rename(columns={"target_gene": "genotype"})
    if "cluster" in table.columns:
        table = table.rename(columns={"cluster": "celltype_2"})

    log_or_matrix = enrichment_matrix(enrich_res)
    sig_matrix = significance_matrix(enrich_res)

    logger.info(
        "Cell-type enrichment complete: %d targets x %d cell types.",
        log_or_matrix.shape[0] if not log_or_matrix.empty else 0,
        log_or_matrix.shape[1] if not log_or_matrix.empty else 0,
    )
    return table, log_or_matrix, sig_matrix


def run_diabetes_modules_analysis(
    adata: ad.AnnData,
    cfg: Config,
) -> Optional[ModulesResults]:
    """Calculate Stage 7 co-functional modules (M1-M6) and gene programs (P1-P4)."""
    logger.info("=== Running Stage 7 Co-functional Modules & Gene Programs ===")

    mod_res = compute_modules(adata, cfg)
    if mod_res is None:
        logger.warning("Stage 7 module computation returned None.")
        return None

    logger.info(
        "Stage 7 complete: %d co-functional modules (M1-M%d), %d gene programs (P1-P%d).",
        mod_res.n_modules,
        mod_res.n_modules,
        mod_res.n_programs,
        mod_res.n_programs,
    )
    return mod_res


def build_master_summary_table(
    adata: ad.AnnData,
    ps_summary: pd.DataFrame,
    dist_table: pd.DataFrame,
    lochness_df: pd.DataFrame,
    pheno_groups: pd.DataFrame,
    mod_results: Optional[Any],
) -> pd.DataFrame:
    """Merge available perturbation-level metrics by genotype on native scales."""
    logger.info("=== Assembling Master Perturbation Summary Table ===")

    # Get non-WT genotypes and cell counts
    genotypes = (
        adata.obs.loc[adata.obs["genotype"] != "WT", "genotype"]
        .value_counts()
        .reset_index()
    )
    genotypes.columns = ["genotype", "n_cells"]
    genotypes = genotypes.sort_values("genotype").reset_index(drop=True)

    # 1. Merge PS summary
    if not ps_summary.empty:
        ps_copy = ps_summary.copy()
        if "target_gene" in ps_copy.columns and "genotype" not in ps_copy.columns:
            ps_copy = ps_copy.rename(columns={"target_gene": "genotype"})
        if "mean_ps" in ps_copy.columns and "ps_mean" not in ps_copy.columns:
            ps_copy["ps_mean"] = ps_copy["mean_ps"]
        if "median_ps" in ps_copy.columns and "ps_median" not in ps_copy.columns:
            ps_copy["ps_median"] = ps_copy["median_ps"]
        if "pct_successful_kd" in ps_copy.columns and "ps_responder_fraction" not in ps_copy.columns:
            ps_copy["ps_responder_fraction"] = ps_copy["pct_successful_kd"] / 100.0

        ps_cols = ["genotype", "ps_mean", "ps_median", "ps_responder_fraction"]
        avail_ps_cols = [c for c in ps_cols if c in ps_copy.columns]
        genotypes = genotypes.merge(ps_copy[avail_ps_cols], on="genotype", how="left")

    # 2. Merge Distance results
    if not dist_table.empty:
        dist_cols = ["genotype", "energy_distance", "pvalue", "fdr", "significant"]
        avail_dist = [c for c in dist_cols if c in dist_table.columns]
        renamed_dist = dist_table[avail_dist].rename(
            columns={
                "pvalue": "distance_pvalue",
                "fdr": "distance_fdr",
                "significant": "distance_significant",
            }
        )
        genotypes = genotypes.merge(renamed_dist, on="genotype", how="left")

    # 3. Merge lochNESS summary
    if not lochness_df.empty:
        loch_cols = [
            "genotype",
            "lochness_mean",
            "lochness_median",
            "lochness_positive_mean",
            "lochness_positive_median",
            "lochness_positive_fraction",
            "lochness_positive_q90",
            "lochness_negative_mean",
            "lochness_negative_median",
            "lochness_negative_fraction",
            "lochness_negative_q10",
            "lochness_abs_mean",
            "lochness_abs_median",
            "lochness_peak",
            "dominant_celltype_2",
            "dominant_celltype_fraction",
            "dominant_celltype_lochness",
        ]
        avail_loch = [c for c in loch_cols if c in lochness_df.columns]
        genotypes = genotypes.merge(lochness_df[avail_loch], on="genotype", how="left")

    # 4. Merge Co-functional Modules (Stage 7)
    if mod_results is not None:
        modules_df = getattr(mod_results, "modules", pd.DataFrame())
        if not modules_df.empty:
            mod_df = modules_df.copy()
            if "target_gene" in mod_df.columns and "genotype" not in mod_df.columns:
                mod_df = mod_df.rename(columns={"target_gene": "genotype"})
            if "module" in mod_df.columns:
                mod_df = mod_df.rename(columns={"module": "cofunctional_module"})
            avail_mod = [c for c in ["genotype", "cofunctional_module"] if c in mod_df.columns]
            genotypes = genotypes.merge(mod_df[avail_mod], on="genotype", how="left")

    # 5. Merge Phenotype Similarity Groups
    if not pheno_groups.empty:
        genotypes = genotypes.merge(
            pheno_groups[["genotype", "phenotype_group"]], on="genotype", how="left"
        )

    # Order columns strictly matching Section 19 canonical order where available
    canonical_order = [
        "genotype",
        "n_cells",
        "ps_mean",
        "ps_median",
        "ps_responder_fraction",
        "energy_distance",
        "distance_pvalue",
        "distance_fdr",
        "lochness_mean",
        "lochness_median",
        "lochness_positive_mean",
        "lochness_positive_median",
        "lochness_positive_fraction",
        "lochness_positive_q90",
        "lochness_negative_mean",
        "lochness_negative_median",
        "lochness_negative_fraction",
        "lochness_negative_q10",
        "lochness_abs_mean",
        "lochness_abs_median",
        "cofunctional_module",
        "phenotype_group",
    ]
    present_canonical = [c for c in canonical_order if c in genotypes.columns]
    extra_cols = [c for c in genotypes.columns if c not in present_canonical]
    genotypes = genotypes[present_canonical + extra_cols]

    logger.info("Master summary table assembled: %d genotypes x %d features.", len(genotypes), len(genotypes.columns))
    return genotypes


# ===========================================================================
# Dedicated Publication-Quality Visualizations
# ===========================================================================


def safe_generate_figure(
    name: str,
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> bool:
    """Safely execute a figure generation function without interrupting workflow execution.

    Parameters
    ----------
    name : str
        Human-readable figure name / filename for logging.
    func : Callable
        Function that renders and saves the figure.
    *args, **kwargs
        Arguments passed to func.

    Returns
    -------
    bool
        True if figure was successfully generated, False otherwise.
    """
    logger.info("Generating %s...", name)
    try:
        func(*args, **kwargs)
        logger.info("Generated %s", name)
        return True
    except Exception as exc:
        logger.exception(
            "Failed to generate %s: %s. Continuing workflow.",
            name,
            exc,
        )
        return False


def _fig01_umap_celltype2(
    adata: Optional[ad.AnnData],
    sample_idx: np.ndarray,
    umap: np.ndarray,
    fig_dir: Path,
) -> None:
    """Figure 01: UMAP colored by curated cell states (celltype_2)."""
    if adata is None or len(sample_idx) == 0:
        logger.warning("Skipping Figure 01: AnnData or UMAP coordinates unavailable.")
        return
    fig, ax = plt.subplots(figsize=(9, 8), dpi=300)
    ct_sample = adata.obs["celltype_2"].iloc[sample_idx].astype(str)
    unique_cts = [ct for ct in CELLTYPE_ORDER if ct in ct_sample.unique()]
    for ct in unique_cts:
        mask = (ct_sample == ct)
        color = CELLTYPE_PALETTE.get(ct, "#718096")
        ax.scatter(
            umap[sample_idx][mask, 0],
            umap[sample_idx][mask, 1],
            s=4,
            c=color,
            label=ct,
            alpha=0.7,
            rasterized=True,
        )
    ax.set_title("Pancreatic Differentiation — Curated Cell States (celltype_2)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("UMAP 1", fontsize=11)
    ax.set_ylabel("UMAP 2", fontsize=11)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True, fontsize=9, markerscale=3, title="Cell State")
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "01_umap_celltype2.png", bbox_inches="tight")
    plt.close(fig)


def _fig02_umap_development_stage(
    adata: Optional[ad.AnnData],
    sample_idx: np.ndarray,
    umap: np.ndarray,
    fig_dir: Path,
) -> None:
    """Figure 02: UMAP colored by developmental stages."""
    if adata is None or len(sample_idx) == 0:
        logger.warning("Skipping Figure 02: AnnData or UMAP coordinates unavailable.")
        return
    fig, ax = plt.subplots(figsize=(9, 8), dpi=300)
    stage_sample = adata.obs["development_stage"].iloc[sample_idx].astype(str)
    unique_stages = [st for st in STAGE_ORDER if st in stage_sample.unique()]
    for st in unique_stages:
        mask = (stage_sample == st)
        color = STAGE_PALETTE.get(st, "#a0aec0")
        ax.scatter(
            umap[sample_idx][mask, 0],
            umap[sample_idx][mask, 1],
            s=4,
            c=color,
            label=st,
            alpha=0.7,
            rasterized=True,
        )
    ax.set_title("Pancreatic Differentiation — Developmental Stages", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("UMAP 1", fontsize=11)
    ax.set_ylabel("UMAP 2", fontsize=11)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True, fontsize=10, markerscale=3, title="Stage")
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "02_umap_development_stage.png", bbox_inches="tight")
    plt.close(fig)


def _fig03_stage_celltype_composition(adata: Optional[ad.AnnData], fig_dir: Path) -> None:
    """Figure 03: Stage Cell-type Composition Stacked Bar."""
    if adata is None:
        logger.warning("Skipping Figure 03: AnnData unavailable.")
        return
    ct_stage = pd.crosstab(
        adata.obs["development_stage"], adata.obs["celltype_2"], normalize="index"
    )
    ordered_stages = [s for s in STAGE_ORDER if s in ct_stage.index]
    ordered_cts = [c for c in CELLTYPE_ORDER if c in ct_stage.columns]
    ct_stage = ct_stage.reindex(index=ordered_stages, columns=ordered_cts).fillna(0)

    fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
    bottom = np.zeros(len(ordered_stages))
    for ct in ordered_cts:
        values = ct_stage[ct].values
        color = CELLTYPE_PALETTE.get(ct, "#718096")
        ax.bar(ordered_stages, values, bottom=bottom, label=ct, color=color, width=0.65, edgecolor="white", linewidth=0.5)
        bottom += values

    ax.set_title("Cell State Composition Across Developmental Stages", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Developmental Stage", fontsize=11, fontweight="bold")
    ax.set_ylabel("Proportion of Cells", fontsize=11, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", frameon=True, fontsize=9, title="Cell State")
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "03_stage_celltype_composition.png", bbox_inches="tight")
    plt.close(fig)


def _fig04_genotype_celltype_enrichment(
    log_or_matrix: pd.DataFrame,
    sig_matrix: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 04: Genotype x Cell-type Enrichment Heatmap (Stratified CMH Test)."""
    if log_or_matrix.empty:
        logger.warning("Skipping Figure 04: log_or_matrix is empty.")
        return
    fig, ax = plt.subplots(figsize=(12, 11), dpi=300)
    plot_mat = log_or_matrix.copy()
    cols = [c for c in CELLTYPE_ORDER if c in plot_mat.columns]
    if cols:
        plot_mat = plot_mat.reindex(columns=cols)

    vmax = max(2.5, min(5.0, float(np.percentile(np.abs(plot_mat.fillna(0)), 98))))
    sns.heatmap(
        plot_mat,
        cmap="vlag",
        center=0,
        vmax=vmax,
        vmin=-vmax,
        linewidths=0.5,
        linecolor="#f0f0f0",
        cbar_kws={"label": "Enrichment vs WT (log2 OR)", "shrink": 0.8},
        ax=ax,
    )
    if not sig_matrix.empty:
        for i, row in enumerate(plot_mat.index):
            for j, col in enumerate(plot_mat.columns):
                if col in sig_matrix.columns and row in sig_matrix.index:
                    val = sig_matrix.loc[row, col]
                    if pd.notna(val) and (
                        (isinstance(val, (bool, np.bool_)) and val)
                        or (isinstance(val, (int, float, np.number)) and val < 0.05)
                    ):
                        ax.text(j + 0.5, i + 0.65, "*", ha="center", va="center", color="black", fontsize=11, fontweight="bold")

    ax.set_title("Perturbation vs Control Cell-State Enrichment (Stratified CMH Test)", fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Curated Cell State (celltype_2)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Perturbation Genotype", fontsize=11, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    fig.savefig(fig_dir / "04_genotype_celltype_enrichment.png", bbox_inches="tight")
    plt.close(fig)


def _fig05_ps_by_perturbation(ps_summary: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 05: PS Score by Perturbation (Native Scale)."""
    if ps_summary.empty:
        logger.warning("Skipping Figure 05: ps_summary is empty.")
        return

    ps_col = "ps_median" if "ps_median" in ps_summary.columns else ("median_ps" if "median_ps" in ps_summary.columns else None)
    if not ps_col:
        logger.warning("Skipping Figure 05: neither ps_median nor median_ps found in ps_summary.")
        return

    ps_sorted = ps_summary.sort_values(ps_col, ascending=True).copy()
    geno_col = "genotype" if "genotype" in ps_sorted.columns else ("target_gene" if "target_gene" in ps_sorted.columns else ps_sorted.columns[0])

    resp_col = (
        "ps_responder_fraction"
        if "ps_responder_fraction" in ps_sorted.columns
        else ("pct_successful_kd" if "pct_successful_kd" in ps_sorted.columns else None)
    )

    if resp_col:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 10), dpi=300, sharey=True)
    else:
        fig, ax1 = plt.subplots(1, 1, figsize=(7, 10), dpi=300)
        ax2 = None

    y_pos = np.arange(len(ps_sorted))
    ax1.barh(y_pos, ps_sorted[ps_col], color="#2b6cb0", height=0.65, edgecolor="none", alpha=0.85)
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(ps_sorted[geno_col], fontsize=9)
    ax1.set_xlabel("PS Median (Native 0–1 scale)", fontsize=10, fontweight="bold")
    ax1.set_xlim(0, 1.0)
    ax1.axvline(0.5, color="#e53e3e", linestyle="--", linewidth=1, label="Active threshold (0.5)")
    ax1.set_title("Perturbation Response Strength", fontsize=11, fontweight="bold")
    ax1.legend(loc="lower right", fontsize=9)
    sns.despine(fig, ax1)

    if ax2 is not None and resp_col:
        vals = ps_sorted[resp_col].values
        if np.nanmax(vals) <= 1.0:
            vals = vals * 100.0
        ax2.barh(y_pos, vals, color="#319795", height=0.65, edgecolor="none", alpha=0.85)
        ax2.set_xlabel("Responder Fraction (% cells)", fontsize=10, fontweight="bold")
        ax2.set_xlim(0, 100)
        ax2.set_title("Knockdown Penetrance", fontsize=11, fontweight="bold")
        sns.despine(fig, ax2)

    fig.suptitle("Per-Cell Perturbation Scores (PS) Across Genotypes (Native Scale)", fontsize=13, fontweight="bold", y=0.98)
    fig.tight_layout()
    fig.savefig(fig_dir / "05_ps_by_perturbation.png", bbox_inches="tight")
    plt.close(fig)


def _fig06_energy_distance_by_perturbation(dist_table: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 06: Energy Distance by Perturbation (Native Scale)."""
    if dist_table.empty or "energy_distance" not in dist_table.columns:
        logger.warning("Skipping Figure 06: dist_table is empty or missing energy_distance.")
        return

    dist_sorted = dist_table.sort_values("energy_distance", ascending=True).copy()
    geno_col = "genotype" if "genotype" in dist_sorted.columns else ("target_gene" if "target_gene" in dist_sorted.columns else dist_sorted.columns[0])

    fig, ax = plt.subplots(figsize=(8, 10), dpi=300)
    y_pos = np.arange(len(dist_sorted))

    colors = ["#2f855a" if sig else "#a0aec0" for sig in dist_sorted.get("significant", [True] * len(dist_sorted))]
    ax.barh(y_pos, dist_sorted["energy_distance"], color=colors, height=0.65, edgecolor="none")

    ax.set_yticks(y_pos)
    ax.set_yticklabels(dist_sorted[geno_col], fontsize=9)
    ax.set_xlabel("Energy Distance vs WT (X_pca representation)", fontsize=10, fontweight="bold")
    ax.set_title("Transcriptomic Distance from WT (Permutation DistanceTest)", fontsize=12, fontweight="bold", pad=12)

    legend_elements = [
        Patch(facecolor="#2f855a", label="Significant (FDR < 0.05)"),
        Patch(facecolor="#a0aec0", label="Not Significant"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=9)
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "06_energy_distance_by_perturbation.png", bbox_inches="tight")
    plt.close(fig)


def _fig07_ps_vs_distance(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 07: PS vs Energy Distance Scatter & Correlation."""
    ps_col = "ps_median" if "ps_median" in summary_df.columns else ("median_ps" if "median_ps" in summary_df.columns else None)
    edist_col = "energy_distance" if "energy_distance" in summary_df.columns else None
    if not ps_col or not edist_col:
        logger.warning("Skipping Figure 07: missing required metric columns in summary_df.")
        return

    df_corr = summary_df.dropna(subset=[edist_col, ps_col])
    if df_corr.empty:
        logger.warning("Skipping Figure 07: no overlapping finite points.")
        return

    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    rho, pval, n_pts = compute_metric_correlation(df_corr[edist_col], df_corr[ps_col])

    ax.scatter(df_corr[edist_col], df_corr[ps_col], color="#2b6cb0", s=50, alpha=0.85, edgecolors="white", linewidth=0.5)

    geno_col = "genotype" if "genotype" in df_corr.columns else df_corr.columns[0]
    for _, r in df_corr.iterrows():
        ax.annotate(r[geno_col], (r[edist_col], r[ps_col]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    if n_pts >= 3:
        sns.regplot(
            data=df_corr,
            x=edist_col,
            y=ps_col,
            scatter=False,
            ax=ax,
            color="#4a5568",
            line_kws={"linewidth": 1.2, "linestyle": "--"},
        )

    ax.set_xlabel("Energy Distance vs WT (Global Phenotype Magnitude)", fontsize=10, fontweight="bold")
    ax.set_ylabel("PS Median (Cell-level Response Penetrance)", fontsize=10, fontweight="bold")
    ax.set_title("Perturbation Penetrance vs Global Phenotype Magnitude", fontsize=12, fontweight="bold", pad=12)

    p_str = f"{pval:.2e}" if pd.notna(pval) and pval < 0.001 else (f"{pval:.3f}" if pd.notna(pval) else "N/A")
    rho_str = f"{rho:.3f}" if pd.notna(rho) else "N/A"
    stats_text = f"Spearman ρ = {rho_str}\np-value = {p_str}\nn = {n_pts} perturbations"
    ax.text(
        0.05,
        0.92,
        stats_text,
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc", edgecolor="#cbd5e0", alpha=0.9),
    )
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "07_ps_vs_distance.png", bbox_inches="tight")
    plt.close(fig)


def _fig08_distance_vs_lochness_positive(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 08: Energy Distance vs Positive lochNESS Mean (State-Space Enrichment)."""
    edist_col = "energy_distance" if "energy_distance" in summary_df.columns else None
    loch_col = "lochness_positive_mean" if "lochness_positive_mean" in summary_df.columns else None
    if not edist_col or not loch_col:
        logger.warning("Skipping Figure 08: missing required metric columns in summary_df.")
        return

    df_corr = summary_df.dropna(subset=[edist_col, loch_col])
    if df_corr.empty:
        logger.warning("Skipping Figure 08: no overlapping finite points.")
        return

    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    rho, pval, n_pts = compute_metric_correlation(df_corr[edist_col], df_corr[loch_col])

    ax.scatter(df_corr[edist_col], df_corr[loch_col], color="#2b6cb0", s=50, alpha=0.85, edgecolors="white", linewidth=0.5)
    geno_col = "genotype" if "genotype" in df_corr.columns else df_corr.columns[0]
    for _, r in df_corr.iterrows():
        ax.annotate(r[geno_col], (r[edist_col], r[loch_col]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    if n_pts >= 3:
        sns.regplot(data=df_corr, x=edist_col, y=loch_col, scatter=False, ax=ax, color="#4a5568", line_kws={"linewidth": 1.2, "linestyle": "--"})

    ax.set_xlabel("Energy Distance from WT (Global Phenotype Magnitude)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean Positive lochNESS (State-Space Enrichment)", fontsize=10, fontweight="bold")
    ax.set_title("Global Phenotype Magnitude vs State-Space Enrichment", fontsize=12, fontweight="bold", pad=12)

    p_str = f"{pval:.2e}" if pd.notna(pval) and pval < 0.001 else (f"{pval:.3f}" if pd.notna(pval) else "N/A")
    rho_str = f"{rho:.3f}" if pd.notna(rho) else "N/A"
    stats_text = f"Spearman ρ = {rho_str}\np-value = {p_str}\nn = {n_pts} perturbations"
    ax.text(0.05, 0.92, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc", edgecolor="#cbd5e0", alpha=0.9))
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "08_distance_vs_lochness_positive.png", bbox_inches="tight")
    plt.close(fig)


def _fig09_distance_vs_lochness_negative(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 09: Energy Distance vs Negative lochNESS Mean (State-Space Depletion)."""
    edist_col = "energy_distance" if "energy_distance" in summary_df.columns else None
    loch_col = "lochness_negative_mean" if "lochness_negative_mean" in summary_df.columns else None
    if not edist_col or not loch_col:
        logger.warning("Skipping Figure 09: missing required metric columns in summary_df.")
        return

    df_corr = summary_df.dropna(subset=[edist_col, loch_col])
    if df_corr.empty:
        logger.warning("Skipping Figure 09: no overlapping finite points.")
        return

    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    rho, pval, n_pts = compute_metric_correlation(df_corr[edist_col], df_corr[loch_col])

    ax.scatter(df_corr[edist_col], df_corr[loch_col], color="#c53030", s=50, alpha=0.85, edgecolors="white", linewidth=0.5)
    geno_col = "genotype" if "genotype" in df_corr.columns else df_corr.columns[0]
    for _, r in df_corr.iterrows():
        ax.annotate(r[geno_col], (r[edist_col], r[loch_col]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    if n_pts >= 3:
        sns.regplot(data=df_corr, x=edist_col, y=loch_col, scatter=False, ax=ax, color="#4a5568", line_kws={"linewidth": 1.2, "linestyle": "--"})

    ax.set_xlabel("Energy Distance from WT (Global Phenotype Magnitude)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean Negative lochNESS (State-Space Depletion)", fontsize=10, fontweight="bold")
    ax.set_title("Global Phenotype Magnitude vs State-Space Depletion", fontsize=12, fontweight="bold", pad=12)

    p_str = f"{pval:.2e}" if pd.notna(pval) and pval < 0.001 else (f"{pval:.3f}" if pd.notna(pval) else "N/A")
    rho_str = f"{rho:.3f}" if pd.notna(rho) else "N/A"
    stats_text = f"Spearman ρ = {rho_str}\np-value = {p_str}\nn = {n_pts} perturbations"
    ax.text(0.05, 0.92, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc", edgecolor="#cbd5e0", alpha=0.9))
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "09_distance_vs_lochness_negative.png", bbox_inches="tight")
    plt.close(fig)


def _fig10_ps_vs_lochness_positive(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 10: PS Median vs Positive lochNESS Mean (State-Space Enrichment)."""
    ps_col = "ps_median" if "ps_median" in summary_df.columns else ("median_ps" if "median_ps" in summary_df.columns else None)
    loch_col = "lochness_positive_mean" if "lochness_positive_mean" in summary_df.columns else None
    if not ps_col or not loch_col:
        logger.warning("Skipping Figure 10: missing required metric columns in summary_df.")
        return

    df_corr = summary_df.dropna(subset=[ps_col, loch_col])
    if df_corr.empty:
        logger.warning("Skipping Figure 10: no overlapping finite points.")
        return

    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    rho, pval, n_pts = compute_metric_correlation(df_corr[ps_col], df_corr[loch_col])

    ax.scatter(df_corr[ps_col], df_corr[loch_col], color="#319795", s=50, alpha=0.85, edgecolors="white", linewidth=0.5)
    geno_col = "genotype" if "genotype" in df_corr.columns else df_corr.columns[0]
    for _, r in df_corr.iterrows():
        ax.annotate(r[geno_col], (r[ps_col], r[loch_col]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    if n_pts >= 3:
        sns.regplot(data=df_corr, x=ps_col, y=loch_col, scatter=False, ax=ax, color="#4a5568", line_kws={"linewidth": 1.2, "linestyle": "--"})

    ax.set_xlabel("PS Median (Native 0–1 Scale)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean Positive lochNESS (State-Space Enrichment)", fontsize=10, fontweight="bold")
    ax.set_title("Perturbation Response vs State-Space Enrichment", fontsize=12, fontweight="bold", pad=12)

    p_str = f"{pval:.2e}" if pd.notna(pval) and pval < 0.001 else (f"{pval:.3f}" if pd.notna(pval) else "N/A")
    rho_str = f"{rho:.3f}" if pd.notna(rho) else "N/A"
    stats_text = f"Spearman ρ = {rho_str}\np-value = {p_str}\nn = {n_pts} perturbations"
    ax.text(0.05, 0.92, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc", edgecolor="#cbd5e0", alpha=0.9))
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "10_ps_vs_lochness_positive.png", bbox_inches="tight")
    plt.close(fig)


def _fig11_ps_vs_lochness_negative(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 11: PS Median vs Negative lochNESS Mean (State-Space Depletion)."""
    ps_col = "ps_median" if "ps_median" in summary_df.columns else ("median_ps" if "median_ps" in summary_df.columns else None)
    loch_col = "lochness_negative_mean" if "lochness_negative_mean" in summary_df.columns else None
    if not ps_col or not loch_col:
        logger.warning("Skipping Figure 11: missing required metric columns in summary_df.")
        return

    df_corr = summary_df.dropna(subset=[ps_col, loch_col])
    if df_corr.empty:
        logger.warning("Skipping Figure 11: no overlapping finite points.")
        return

    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    rho, pval, n_pts = compute_metric_correlation(df_corr[ps_col], df_corr[loch_col])

    ax.scatter(df_corr[ps_col], df_corr[loch_col], color="#dd6b20", s=50, alpha=0.85, edgecolors="white", linewidth=0.5)
    geno_col = "genotype" if "genotype" in df_corr.columns else df_corr.columns[0]
    for _, r in df_corr.iterrows():
        ax.annotate(r[geno_col], (r[ps_col], r[loch_col]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    if n_pts >= 3:
        sns.regplot(data=df_corr, x=ps_col, y=loch_col, scatter=False, ax=ax, color="#4a5568", line_kws={"linewidth": 1.2, "linestyle": "--"})

    ax.set_xlabel("PS Median (Native 0–1 Scale)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean Negative lochNESS (State-Space Depletion)", fontsize=10, fontweight="bold")
    ax.set_title("Perturbation Response vs State-Space Depletion", fontsize=12, fontweight="bold", pad=12)

    p_str = f"{pval:.2e}" if pd.notna(pval) and pval < 0.001 else (f"{pval:.3f}" if pd.notna(pval) else "N/A")
    rho_str = f"{rho:.3f}" if pd.notna(rho) else "N/A"
    stats_text = f"Spearman ρ = {rho_str}\np-value = {p_str}\nn = {n_pts} perturbations"
    ax.text(0.05, 0.92, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc", edgecolor="#cbd5e0", alpha=0.9))
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "11_ps_vs_lochness_negative.png", bbox_inches="tight")
    plt.close(fig)


def _fig12_distance_vs_lochness_absolute(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 12: Energy Distance vs Absolute lochNESS Magnitude Scatter & Correlation."""
    edist_col = "energy_distance" if "energy_distance" in summary_df.columns else None
    loch_col = "lochness_abs_mean" if "lochness_abs_mean" in summary_df.columns else None
    if not edist_col or not loch_col:
        logger.warning("Skipping Figure 12: missing required metric columns in summary_df.")
        return

    df_corr = summary_df.dropna(subset=[edist_col, loch_col])
    if df_corr.empty:
        logger.warning("Skipping Figure 12: no overlapping finite points.")
        return

    fig, ax = plt.subplots(figsize=(8, 7), dpi=300)
    rho, pval, n_pts = compute_metric_correlation(df_corr[edist_col], df_corr[loch_col])

    ax.scatter(df_corr[edist_col], df_corr[loch_col], color="#805ad5", s=50, alpha=0.85, edgecolors="white", linewidth=0.5)
    geno_col = "genotype" if "genotype" in df_corr.columns else df_corr.columns[0]
    for _, r in df_corr.iterrows():
        ax.annotate(r[geno_col], (r[edist_col], r[loch_col]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    if n_pts >= 3:
        sns.regplot(data=df_corr, x=edist_col, y=loch_col, scatter=False, ax=ax, color="#4a5568", line_kws={"linewidth": 1.2, "linestyle": "--"})

    ax.set_xlabel("Energy Distance from WT (Global Phenotype Magnitude)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Mean Absolute lochNESS Magnitude", fontsize=10, fontweight="bold")
    ax.set_title("Global Phenotype Magnitude vs Absolute lochNESS Magnitude\n(Irrespective of enrichment vs depletion direction)", fontsize=11, fontweight="bold", pad=12)

    p_str = f"{pval:.2e}" if pd.notna(pval) and pval < 0.001 else (f"{pval:.3f}" if pd.notna(pval) else "N/A")
    rho_str = f"{rho:.3f}" if pd.notna(rho) else "N/A"
    stats_text = f"Spearman ρ = {rho_str}\np-value = {p_str}\nn = {n_pts} perturbations"
    ax.text(0.05, 0.92, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment="top", bbox=dict(boxstyle="round,pad=0.5", facecolor="#f7fafc", edgecolor="#cbd5e0", alpha=0.9))
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "12_distance_vs_lochness_absolute.png", bbox_inches="tight")
    plt.close(fig)


def _fig13_lochness_by_celltype(lochness_celltype_matrix: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 13: Genotype x celltype_2 Signed lochNESS Heatmap (Primary Biological Interpretation)."""
    if lochness_celltype_matrix is None or lochness_celltype_matrix.empty:
        logger.warning("Skipping Figure 13: lochness_celltype_matrix is empty.")
        return

    plot_mat = lochness_celltype_matrix.copy()
    cols = [c for c in CELLTYPE_ORDER if c in plot_mat.columns]
    if cols:
        plot_mat = plot_mat.reindex(columns=cols)

    # Determine dynamic color scale centered at 0
    finite_vals = plot_mat.to_numpy().flatten()
    finite_vals = finite_vals[np.isfinite(finite_vals)]
    if len(finite_vals) > 0:
        vmax = max(1.5, min(10.0, float(np.percentile(np.abs(finite_vals), 98))))
    else:
        vmax = 3.0

    fig, ax = plt.subplots(figsize=(13, 11), dpi=300)
    cmap = sns.color_palette("vlag", as_cmap=True).copy()
    try:
        cmap.set_bad(color="#edf2f7")  # Clean subtle light grey for NaN/masked low-cell groups
    except Exception:
        pass

    sns.heatmap(
        plot_mat,
        cmap=cmap,
        center=0,
        vmax=vmax,
        vmin=-vmax,
        linewidths=0.5,
        linecolor="#f0f0f0",
        cbar_kws={"label": "Mean Signed lochNESS\n(>0 enrichment, <0 depletion)", "shrink": 0.8},
        ax=ax,
    )

    ax.set_title("Genotype × Cell State Continuous lochNESS Localization (celltype_2)\n(Groups with <10 cells masked in grey)", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Curated Cell State (celltype_2)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Perturbation Genotype", fontsize=11, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    fig.savefig(fig_dir / "13_lochness_by_celltype.png", bbox_inches="tight")
    fig.savefig(fig_dir / "lochness_genotype_celltype_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def _fig14_distance_space(
    dist_mat: pd.DataFrame,
    coords: pd.DataFrame,
    pheno_groups: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 14: DistanceSpace & Phenotypic Similarity Groups."""
    if dist_mat.empty or coords.empty:
        logger.warning("Skipping Figure 14: dist_mat or coords is empty.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7), dpi=300)

    # Panel A: PCoA
    pcoa_df = coords.copy()
    geno_col = "genotype" if "genotype" in pcoa_df.columns else ("target_gene" if "target_gene" in pcoa_df.columns else pcoa_df.columns[0])
    if not pheno_groups.empty:
        pg_geno_col = "genotype" if "genotype" in pheno_groups.columns else pheno_groups.columns[0]
        pcoa_df = pcoa_df.merge(pheno_groups, left_on=geno_col, right_on=pg_geno_col, how="left")

    group_col = "phenotype_group" if "phenotype_group" in pcoa_df.columns else None
    if group_col and pcoa_df[group_col].notna().any():
        groups = sorted(pcoa_df[group_col].dropna().unique())
        group_palette = dict(zip(groups, sns.color_palette("tab10", len(groups))))
        for grp in groups:
            sub = pcoa_df[pcoa_df[group_col] == grp]
            ax1.scatter(sub["PCoA1"], sub["PCoA2"], s=70, color=group_palette[grp], label=grp, alpha=0.85, edgecolors="white", linewidth=0.5)
        ax1.legend(title="Phenotype Group", fontsize=9, loc="upper right", frameon=True)
    else:
        ax1.scatter(pcoa_df["PCoA1"], pcoa_df["PCoA2"], s=70, color="#2b6cb0", alpha=0.85, edgecolors="white", linewidth=0.5)

    for _, r in pcoa_df.iterrows():
        ax1.annotate(r[geno_col], (r["PCoA1"], r["PCoA2"]), fontsize=7.5, xytext=(4, 2), textcoords="offset points", alpha=0.85)

    ax1.set_title("A. Perturbation Distance Space (PCoA)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("PCoA 1", fontsize=10, fontweight="bold")
    ax1.set_ylabel("PCoA 2", fontsize=10, fontweight="bold")
    sns.despine(fig, ax1)

    # Panel B: Heatmap of pairwise Energy Distance
    sns.heatmap(
        dist_mat,
        cmap="viridis_r",
        linewidths=0.2,
        cbar_kws={"label": "Pairwise Energy Distance", "shrink": 0.8},
        ax=ax2,
    )
    ax2.set_title("B. Pairwise Phenotype Energy Distance Matrix", fontsize=11, fontweight="bold")
    ax2.set_xticklabels(ax2.get_xticklabels(), rotation=90, fontsize=7.5)
    ax2.set_yticklabels(ax2.get_yticklabels(), rotation=0, fontsize=7.5)

    fig.suptitle(
        "Perturbation Distance Space & Phenotypic Similarity Groups\n"
        "(Groups of perturbations whose global transcriptomic phenotypes are similar according to pairwise Energy Distance)",
        fontsize=12,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    fig.savefig(fig_dir / "14_distance_space.png", bbox_inches="tight")
    plt.close(fig)


def _fig15_module_program_strength(mod_results: Any, fig_dir: Path) -> None:
    """Figure 15: Module x Program Signed Effect Heatmap (M1-M6 x P1-P4)."""
    if mod_results is None:
        return
    mp_mat = getattr(mod_results, "module_program", None)
    if mp_mat is None or mp_mat.empty:
        logger.info("Skipping Figure 15: module_program strength matrix is empty.")
        return

    fig, ax = plt.subplots(figsize=(7, 6), dpi=300)
    sns.heatmap(
        mp_mat,
        cmap="RdBu_r",
        center=0,
        annot=True,
        fmt=".2f",
        linewidths=0.8,
        cbar_kws={"label": "Signed Regulatory Strength", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title("Co-functional Module × Gene Program Strength", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Downstream Gene Programs (P1–P4)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Co-functional Perturbation Modules (M1–M6)", fontsize=10, fontweight="bold")
    fig.savefig(fig_dir / "15_module_program_strength.png", bbox_inches="tight")
    plt.close(fig)


def _fig16_program_activity_celltype2(mod_results: Any, fig_dir: Path) -> None:
    """Figure 16: Program Activity across Curated Cell Types (P1-P4 x celltype_2)."""
    if mod_results is None:
        return
    p_act = getattr(mod_results, "program_activity", None)
    if p_act is None or p_act.empty:
        logger.info("Skipping Figure 16: program_activity matrix is empty.")
        return

    fig, ax = plt.subplots(figsize=(10, 5), dpi=300)
    p_act_plot = p_act.copy()
    cols = [c for c in CELLTYPE_ORDER if c in p_act_plot.columns]
    if cols:
        p_act_plot = p_act_plot.reindex(columns=cols)

    sns.heatmap(
        p_act_plot,
        cmap="mako",
        linewidths=0.5,
        cbar_kws={"label": "Mean Program Activity Score", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title("Downstream Gene Program Activity Across Curated Cell States", fontsize=12, fontweight="bold", pad=12)
    ax.set_xlabel("Curated Biological Cell State (celltype_2)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Gene Programs", fontsize=10, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    fig.savefig(fig_dir / "16_program_activity_celltype2.png", bbox_inches="tight")
    plt.close(fig)


def _fig17_program_enrichment(mod_results: Any, fig_dir: Path) -> None:
    """Figure 17: Program Biological Pathway Enrichment (P1-P4 strictly maintained as identifiers)."""
    if mod_results is None:
        return
    p_enrich = getattr(mod_results, "program_enrichment", None)
    if p_enrich is None or p_enrich.empty:
        logger.warning("Skipping Figure 17: program_enrichment table is empty.")
        return

    # Identify canonical program identifier column: program_id (fallback to program)
    prog_col = "program_id" if "program_id" in p_enrich.columns else ("program" if "program" in p_enrich.columns else p_enrich.columns[0])

    programs = sorted(
        p_enrich[prog_col].unique(),
        key=lambda x: (len(str(x)), str(x)),
    )
    n_progs = len(programs)
    if n_progs == 0:
        return

    fig, axes = plt.subplots(n_progs, 1, figsize=(10, max(3.5, 3.2 * n_progs)), dpi=300, sharex=False)
    if n_progs == 1:
        axes = [axes]

    for ax, prog in zip(axes, programs):
        sub = p_enrich[p_enrich[prog_col] == prog].copy()
        # Sort by FDR ascending, then p_value ascending
        sort_cols = [c for c in ["fdr", "adjusted_p_value", "p_value"] if c in sub.columns]
        if sort_cols:
            sub = sub.sort_values(sort_cols, ascending=True)
        sub = sub.head(5)

        if sub.empty:
            ax.text(0.5, 0.5, f"No enriched terms for {prog}", ha="center", va="center", fontsize=10)
            ax.set_title(f"Gene Program {prog} — Enriched Biological Pathways", fontsize=11, fontweight="bold", loc="left")
            sns.despine(fig, ax)
            continue

        fdr_col = "fdr" if "fdr" in sub.columns else ("adjusted_p_value" if "adjusted_p_value" in sub.columns else "p_value")
        fdr_vals = sub[fdr_col].fillna(1.0).values
        neg_log_fdr = -np.log10(np.maximum(fdr_vals, 1e-30))

        # Invert order so top term is at top of horizontal bar chart
        sub_plot = sub.iloc[::-1]
        neg_log_plot = neg_log_fdr[::-1]

        y_pos = np.arange(len(sub_plot))
        ax.barh(y_pos, neg_log_plot, color="#2b6cb0", height=0.6, alpha=0.85)
        ax.set_yticks(y_pos)

        # Term labels: prefer clean_term if present, otherwise clean term from term column
        if "clean_term" in sub_plot.columns and sub_plot["clean_term"].notna().all():
            terms = sub_plot["clean_term"].astype(str).tolist()
        else:
            term_col = "term" if "term" in sub_plot.columns else sub_plot.columns[1]
            terms = [clean_term_name(str(t)) for t in sub_plot[term_col]]

        ax.set_yticklabels(terms, fontsize=8.5)
        ax.set_xlabel("-log10(FDR)", fontsize=9, fontweight="bold")
        # Program identifier remains the canonical headline (P1, P2, P3, P4)
        ax.set_title(f"Gene Program {prog} — Enriched Biological Pathways", fontsize=11, fontweight="bold", loc="left")
        ax.axvline(-np.log10(0.05), color="#e53e3e", linestyle="--", linewidth=1, label="FDR=0.05")
        sns.despine(fig, ax)

    fig.suptitle("Gene Program Pathway Enrichment Analysis (Hallmark, Reactome, GO BP)", fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()
    fig.savefig(fig_dir / "17_program_enrichment.png", bbox_inches="tight")
    plt.close(fig)


def _fig18_module_network(mod_results: Any, fig_dir: Path) -> None:
    """Figure 18: Perturbation Co-functional Regulatory Network."""
    if mod_results is None:
        return
    tf_edges = getattr(mod_results, "tf_edges", None)
    if tf_edges is None or tf_edges.empty:
        logger.info("Skipping Figure 18: tf_edges is empty.")
        return

    try:
        import networkx as nx

        G = nx.DiGraph()
        edges_df = tf_edges.copy()
        src_col = "source" if "source" in edges_df.columns else ("source_tf" if "source_tf" in edges_df.columns else edges_df.columns[0])
        tgt_col = "target" if "target" in edges_df.columns else ("target_tf" if "target_tf" in edges_df.columns else edges_df.columns[1])
        wt_col = "log2fc" if "log2fc" in edges_df.columns else ("abs_log2fc" if "abs_log2fc" in edges_df.columns else None)

        for _, r in edges_df.iterrows():
            w = float(abs(r[wt_col])) if wt_col and pd.notna(r[wt_col]) else 1.0
            G.add_edge(str(r[src_col]), str(r[tgt_col]), weight=w)

        fig, ax = plt.subplots(figsize=(10, 9), dpi=300)
        pos = nx.spring_layout(G, seed=123, k=0.45)

        # Node colors by module
        mod_map = {}
        modules_df = getattr(mod_results, "modules", pd.DataFrame())
        if not modules_df.empty:
            gene_c = "target_gene" if "target_gene" in modules_df.columns else ("genotype" if "genotype" in modules_df.columns else modules_df.columns[0])
            mod_c = "module" if "module" in modules_df.columns else ("cofunctional_module" if "cofunctional_module" in modules_df.columns else modules_df.columns[1])
            mod_map = dict(zip(modules_df[gene_c].astype(str), modules_df[mod_c].astype(str)))

        unique_mods = sorted(set(mod_map.values())) if mod_map else ["M1"]
        mod_palette = dict(zip(unique_mods, sns.color_palette("tab10", len(unique_mods))))
        node_colors = [mod_palette.get(mod_map.get(str(node), unique_mods[0]), "#a0aec0") for node in G.nodes()]

        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=600, alpha=0.9, edgecolors="white", linewidths=1.5, ax=ax)
        nx.draw_networkx_labels(G, pos, font_size=8.5, font_weight="bold", ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color="#a0aec0", alpha=0.6, arrows=True, arrowsize=10, width=1.2, ax=ax)

        legend_elements = [Patch(facecolor=mod_palette[m], label=m) for m in unique_mods]
        ax.legend(handles=legend_elements, title="Co-functional Module", loc="upper right", fontsize=9)
        ax.set_title("Perturbation Co-functional Regulatory Network", fontsize=13, fontweight="bold", pad=12)
        ax.axis("off")
        fig.savefig(fig_dir / "18_module_network.png", bbox_inches="tight")
        plt.close(fig)

    except Exception as exc:
        logger.warning("Could not render module network graph: %s", exc)
        mod_conn = getattr(mod_results, "module_connectivity", pd.DataFrame())
        if not mod_conn.empty:
            fig, ax = plt.subplots(figsize=(6, 5), dpi=300)
            sns.heatmap(mod_conn, cmap="mako", annot=True, fmt=".2f", ax=ax)
            ax.set_title("Module x Module Connectivity", fontsize=11, fontweight="bold")
            fig.savefig(fig_dir / "18_module_network.png", bbox_inches="tight")
            plt.close(fig)


def _fig19_perturbation_summary(summary_df: pd.DataFrame, fig_dir: Path) -> None:
    """Figure 19: Perturbation Summary Multi-panel Atlas (Native Scales)."""
    if summary_df.empty:
        logger.warning("Skipping Figure 19: summary_df is empty.")
        return

    plot_df = summary_df.sort_values("n_cells", ascending=True).copy()
    geno_col = "genotype" if "genotype" in plot_df.columns else plot_df.columns[0]
    genotypes = plot_df[geno_col].values
    y_pos = np.arange(len(plot_df))

    fig, axes = plt.subplots(1, 5, figsize=(22, 11), dpi=300, sharey=True)

    # Panel 1: Number of cells
    axes[0].barh(y_pos, plot_df["n_cells"], color="#4a5568", height=0.65)
    axes[0].set_yticks(y_pos)
    axes[0].set_yticklabels(genotypes, fontsize=8.5)
    axes[0].set_xlabel("Number of Cells", fontsize=9.5, fontweight="bold")
    axes[0].set_title("Screen Representation", fontsize=11, fontweight="bold")
    sns.despine(fig, axes[0])

    # Panel 2: PS Median (0-1)
    ps_col = "ps_median" if "ps_median" in plot_df.columns else ("median_ps" if "median_ps" in plot_df.columns else None)
    if ps_col:
        ps_vals = plot_df[ps_col].fillna(0).values
        axes[1].barh(y_pos, ps_vals, color="#2b6cb0", height=0.65)
        axes[1].set_xlabel("PS Median (0–1)", fontsize=9.5, fontweight="bold")
        axes[1].set_xlim(0, 1.0)
        axes[1].axvline(0.5, color="#e53e3e", linestyle="--", linewidth=0.8)
        axes[1].set_title("Perturbation Penetrance (PS)", fontsize=11, fontweight="bold")
        sns.despine(fig, axes[1])

    # Panel 3: Energy Distance
    if "energy_distance" in plot_df.columns:
        edist_vals = plot_df["energy_distance"].fillna(0).values
        axes[2].barh(y_pos, edist_vals, color="#2f855a", height=0.65)
        axes[2].set_xlabel("Energy Distance vs WT", fontsize=9.5, fontweight="bold")
        axes[2].set_title("Global Transcriptomic Shift", fontsize=11, fontweight="bold")
        sns.despine(fig, axes[2])

    # Panel 4: Positive lochNESS Mean
    pos_col = "lochness_positive_mean" if "lochness_positive_mean" in plot_df.columns else None
    if pos_col:
        pos_vals = plot_df[pos_col].fillna(0).values
        axes[3].barh(y_pos, pos_vals, color="#319795", height=0.65)
        axes[3].set_xlabel("Mean Positive lochNESS", fontsize=9.5, fontweight="bold")
        axes[3].set_title("State-Space Enrichment", fontsize=11, fontweight="bold")
        sns.despine(fig, axes[3])

    # Panel 5: Negative lochNESS Mean
    neg_col = "lochness_negative_mean" if "lochness_negative_mean" in plot_df.columns else None
    if neg_col:
        neg_vals = plot_df[neg_col].fillna(0).values
        axes[4].barh(y_pos, neg_vals, color="#dd6b20", height=0.65)
        axes[4].set_xlabel("Mean Negative lochNESS", fontsize=9.5, fontweight="bold")
        axes[4].set_title("State-Space Depletion", fontsize=11, fontweight="bold")
        sns.despine(fig, axes[4])

    fig.suptitle("Diabetes Perturb-seq Multi-Metric Perturbation Atlas (Native Scales)", fontsize=13, fontweight="bold", y=0.98)
    fig.tight_layout()
    fig.savefig(fig_dir / "19_perturbation_summary.png", bbox_inches="tight")
    plt.close(fig)


# Aliases for backward compatibility
_fig10_distance_space = _fig14_distance_space
_fig11_module_program_strength = _fig15_module_program_strength
_fig12_program_activity_celltype2 = _fig16_program_activity_celltype2
_fig13_program_enrichment = _fig17_program_enrichment
_fig14_module_network = _fig18_module_network
_fig15_perturbation_summary = _fig19_perturbation_summary


def _fig20_umap_ps_score(
    adata: Optional[ad.AnnData],
    sample_idx: np.ndarray,
    umap: np.ndarray,
    fig_dir: Path,
) -> None:
    """Figure 20: UMAP colored by per-cell Perturbation Score (PS) on native scale [0, 1]."""
    if adata is None or "ps_score" not in adata.obs or len(sample_idx) == 0:
        logger.warning("Skipping Figure 20: AnnData or ps_score unavailable.")
        return

    ps_scores = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)
    ps_sample = ps_scores[sample_idx]
    umap_sample = umap[sample_idx]

    valid_mask = np.isfinite(ps_sample)
    if not np.any(valid_mask):
        logger.warning("Skipping Figure 20: no valid finite PS scores found in sample.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), dpi=300)

    # Panel A: All cells (unscored/control background in light grey + scored perturbed on top)
    unscored_mask = ~valid_mask
    if np.any(unscored_mask):
        ax1.scatter(
            umap_sample[unscored_mask, 0],
            umap_sample[unscored_mask, 1],
            s=4,
            c="#e2e8f0",
            label="Unscored / Control",
            alpha=0.5,
            rasterized=True,
        )
    sc1 = ax1.scatter(
        umap_sample[valid_mask, 0],
        umap_sample[valid_mask, 1],
        s=6,
        c=ps_sample[valid_mask],
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
        alpha=0.85,
        rasterized=True,
    )
    cbar1 = fig.colorbar(sc1, ax=ax1, shrink=0.75, pad=0.02)
    cbar1.set_label("Perturbation Score (PS)\n[0 = control-like, 1 = perturbed]", fontsize=9.5)
    ax1.set_title("A. All Cells (Manifold Context)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("UMAP 1", fontsize=10)
    ax1.set_ylabel("UMAP 2", fontsize=10)
    if np.any(unscored_mask):
        ax1.legend(loc="upper right", fontsize=8.5, frameon=True)
    sns.despine(fig, ax1)

    # Panel B: Non-WT perturbed cells with valid PS only
    sc2 = ax2.scatter(
        umap_sample[valid_mask, 0],
        umap_sample[valid_mask, 1],
        s=7,
        c=ps_sample[valid_mask],
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
        alpha=0.9,
        rasterized=True,
    )
    cbar2 = fig.colorbar(sc2, ax=ax2, shrink=0.75, pad=0.02)
    cbar2.set_label("Perturbation Score (PS)\n[0 = control-like, 1 = perturbed]", fontsize=9.5)
    ax2.set_title(f"B. Non-WT Perturbed Cells Only (n = {int(valid_mask.sum()):,})", fontsize=11, fontweight="bold")
    ax2.set_xlabel("UMAP 1", fontsize=10)
    ax2.set_ylabel("UMAP 2", fontsize=10)
    sns.despine(fig, ax2)

    fig.suptitle(
        "Per-Cell Perturbation Scores (PS) on Pancreatic Developmental Manifold (Native Scale [0, 1])\n"
        "(Where in the transcriptomic manifold do cells with strong perturbation responses occur?)",
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    fig.savefig(fig_dir / "20_umap_ps_score.png", bbox_inches="tight")
    fig.savefig(fig_dir / "umap_ps_score.png", bbox_inches="tight")
    plt.close(fig)


def _fig21_umap_lochness_score(
    adata: Optional[ad.AnnData],
    sample_idx: np.ndarray,
    umap: np.ndarray,
    fig_dir: Path,
) -> None:
    """Figure 21: UMAP colored by per-cell signed lochNESS score."""
    if adata is None or LOCHNESS_SELF not in adata.obs or len(sample_idx) == 0:
        logger.warning("Skipping Figure 21: AnnData or lochness_self unavailable.")
        return

    loch_scores = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)
    loch_sample = loch_scores[sample_idx]
    umap_sample = umap[sample_idx]

    valid_mask = np.isfinite(loch_sample)
    if not np.any(valid_mask):
        logger.warning("Skipping Figure 21: no valid finite lochNESS scores found in sample.")
        return

    vmax = max(1.5, min(6.0, float(np.percentile(np.abs(loch_sample[valid_mask]), 98))))

    fig, ax = plt.subplots(figsize=(9, 8), dpi=300)

    # Plot unscored cells in light grey
    unscored_mask = ~valid_mask
    if np.any(unscored_mask):
        ax.scatter(
            umap_sample[unscored_mask, 0],
            umap_sample[unscored_mask, 1],
            s=4,
            c="#e2e8f0",
            label="Unscored / Control",
            alpha=0.5,
            rasterized=True,
        )

    sc = ax.scatter(
        umap_sample[valid_mask, 0],
        umap_sample[valid_mask, 1],
        s=6,
        c=loch_sample[valid_mask],
        cmap="vlag",
        vmin=-vmax,
        vmax=vmax,
        alpha=0.85,
        rasterized=True,
    )
    cbar = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.02)
    cbar.set_label("Per-Cell Signed lochNESS\n[<0 Depleted, 0 Neutral, >0 Enriched]", fontsize=9.5)

    ax.set_title(
        "Pancreatic Differentiation — Per-Cell Signed lochNESS Localization\n"
        "(Where in transcriptomic state space do perturbation enrichment and depletion signals occur?)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("UMAP 1", fontsize=10)
    ax.set_ylabel("UMAP 2", fontsize=10)
    if np.any(unscored_mask):
        ax.legend(loc="upper right", fontsize=8.5, frameon=True)
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "21_umap_lochness_score.png", bbox_inches="tight")
    fig.savefig(fig_dir / "umap_lochness_score.png", bbox_inches="tight")
    plt.close(fig)


def _fig22_ps_by_genotype(
    adata: Optional[ad.AnnData],
    ps_by_genotype_df: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 22: Genotype-level PS distributions (boxplot + median on native scale)."""
    if adata is None or "ps_score" not in adata.obs:
        logger.warning("Skipping Figure 22: AnnData or ps_score unavailable.")
        return

    obs_df = adata.obs[["genotype", "ps_score"]].copy()
    obs_df["ps_score"] = pd.to_numeric(obs_df["ps_score"], errors="coerce")
    obs_valid = obs_df[(obs_df["genotype"] != "WT") & obs_df["ps_score"].notna()].copy()

    if obs_valid.empty:
        logger.warning("Skipping Figure 22: no non-WT cells with valid PS found.")
        return

    if not ps_by_genotype_df.empty and "median_ps" in ps_by_genotype_df.columns:
        ordered_genos = ps_by_genotype_df.dropna(subset=["median_ps"]).sort_values("median_ps", ascending=True)["genotype"].tolist()
    else:
        medians = obs_valid.groupby("genotype")["ps_score"].median().sort_values(ascending=True)
        ordered_genos = medians.index.tolist()

    obs_valid = obs_valid[obs_valid["genotype"].isin(ordered_genos)]

    fig, ax = plt.subplots(figsize=(8, max(6, 0.35 * len(ordered_genos))), dpi=300)

    sns.boxplot(
        data=obs_valid,
        y="genotype",
        x="ps_score",
        order=ordered_genos,
        color="#3182ce",
        fliersize=1.5,
        linewidth=0.8,
        width=0.6,
        ax=ax,
    )

    ax.set_xlim(-0.02, 1.02)
    ax.axvline(0.5, color="#e53e3e", linestyle="--", linewidth=1, label="Active threshold (0.5)")
    ax.set_xlabel("Per-Cell Perturbation Score (PS, Native 0–1 Scale)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Perturbation Genotype", fontsize=10, fontweight="bold")
    ax.set_title("Per-Cell Perturbation Score (PS) Distributions Across Genotypes", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=9)
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "22_ps_by_genotype.png", bbox_inches="tight")
    fig.savefig(fig_dir / "ps_by_genotype.png", bbox_inches="tight")
    plt.close(fig)


def _fig23_ps_by_celltype2(
    adata: Optional[ad.AnnData],
    ps_by_celltype2_df: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 23: Curated cell type (celltype_2) PS distributions (native scale)."""
    if adata is None or "ps_score" not in adata.obs or "celltype_2" not in adata.obs:
        logger.warning("Skipping Figure 23: AnnData or ps_score/celltype_2 unavailable.")
        return

    obs_df = adata.obs[["genotype", "celltype_2", "ps_score"]].copy()
    obs_df["ps_score"] = pd.to_numeric(obs_df["ps_score"], errors="coerce")
    obs_valid = obs_df[(obs_df["genotype"] != "WT") & obs_df["ps_score"].notna()].copy()

    if obs_valid.empty:
        logger.warning("Skipping Figure 23: no non-WT cells with valid PS found.")
        return

    present_cts = [ct for ct in CELLTYPE_ORDER if ct in obs_valid["celltype_2"].unique()]
    for ct in sorted(obs_valid["celltype_2"].unique()):
        if ct not in present_cts:
            present_cts.append(ct)

    fig, ax = plt.subplots(figsize=(8, max(5, 0.4 * len(present_cts))), dpi=300)

    palette = [CELLTYPE_PALETTE.get(ct, "#718096") for ct in present_cts]
    sns.boxplot(
        data=obs_valid,
        y="celltype_2",
        x="ps_score",
        order=present_cts,
        palette=palette,
        fliersize=1.5,
        linewidth=0.8,
        width=0.6,
        ax=ax,
    )

    ax.set_xlim(-0.02, 1.02)
    ax.axvline(0.5, color="#e53e3e", linestyle="--", linewidth=1, label="Active threshold (0.5)")
    ax.set_xlabel("Per-Cell Perturbation Score (PS, Native 0–1 Scale)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Curated Cell State (celltype_2)", fontsize=10, fontweight="bold")
    ax.set_title("Perturbation Response Strength (PS) Across Curated Cell States", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=9)
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "23_ps_by_celltype2.png", bbox_inches="tight")
    fig.savefig(fig_dir / "ps_by_celltype2.png", bbox_inches="tight")
    plt.close(fig)


def _fig24_ps_genotype_celltype_heatmap(
    ps_genotype_celltype_mat: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 24: Genotype x celltype_2 Mean PS Heatmap (Native scale [0, 1])."""
    if ps_genotype_celltype_mat is None or ps_genotype_celltype_mat.empty:
        logger.warning("Skipping Figure 24: ps_genotype_celltype_mat is empty.")
        return

    plot_mat = ps_genotype_celltype_mat.copy()
    cols = [c for c in CELLTYPE_ORDER if c in plot_mat.columns]
    if cols:
        plot_mat = plot_mat.reindex(columns=cols)

    fig, ax = plt.subplots(figsize=(13, 11), dpi=300)
    cmap = sns.color_palette("viridis", as_cmap=True).copy()
    try:
        cmap.set_bad(color="#edf2f7")  # Grey for groups with <10 valid cells
    except Exception:
        pass

    sns.heatmap(
        plot_mat,
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        linewidths=0.5,
        linecolor="#f0f0f0",
        cbar_kws={"label": "Mean Perturbation Score (PS)\n[0 = control-like, 1 = perturbed]", "shrink": 0.8},
        ax=ax,
    )

    ax.set_title(
        "Genotype × Cell State Perturbation Response Strength (Mean PS)\n"
        "(Native scale [0, 1] — Groups with <10 valid cells masked in grey)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.set_xlabel("Curated Cell State (celltype_2)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Perturbation Genotype", fontsize=11, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    fig.savefig(fig_dir / "24_ps_genotype_celltype_heatmap.png", bbox_inches="tight")
    fig.savefig(fig_dir / "ps_genotype_celltype_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def _fig25_lochness_by_genotype(
    adata: Optional[ad.AnnData],
    lochness_by_genotype_df: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 25: Genotype-level signed lochNESS distributions with zero reference line."""
    if adata is None or LOCHNESS_SELF not in adata.obs:
        logger.warning("Skipping Figure 25: AnnData or lochness_self unavailable.")
        return

    obs_df = adata.obs[["genotype", LOCHNESS_SELF]].copy()
    obs_df[LOCHNESS_SELF] = pd.to_numeric(obs_df[LOCHNESS_SELF], errors="coerce")
    obs_valid = obs_df[(obs_df["genotype"] != "WT") & obs_df[LOCHNESS_SELF].notna()].copy()

    if obs_valid.empty:
        logger.warning("Skipping Figure 25: no non-WT cells with valid lochNESS found.")
        return

    if not lochness_by_genotype_df.empty and "mean_lochness" in lochness_by_genotype_df.columns:
        ordered_genos = lochness_by_genotype_df.dropna(subset=["mean_lochness"]).sort_values("mean_lochness", ascending=True)["genotype"].tolist()
    else:
        means = obs_valid.groupby("genotype")[LOCHNESS_SELF].mean().sort_values(ascending=True)
        ordered_genos = means.index.tolist()

    obs_valid = obs_valid[obs_valid["genotype"].isin(ordered_genos)]

    fig, ax = plt.subplots(figsize=(9, max(6, 0.35 * len(ordered_genos))), dpi=300)

    sns.boxplot(
        data=obs_valid,
        y="genotype",
        x=LOCHNESS_SELF,
        order=ordered_genos,
        color="#319795",
        fliersize=1.5,
        linewidth=0.8,
        width=0.6,
        ax=ax,
    )

    ax.axvline(0, color="#e53e3e", linestyle="--", linewidth=1.2, label="Neutral expected frequency (0)")
    ax.set_xlabel("Per-Cell Signed lochNESS (<0 Depleted, 0 Neutral, >0 Enriched)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Perturbation Genotype", fontsize=10, fontweight="bold")
    ax.set_title(
        "Per-Cell Signed lochNESS Distributions Across Genotypes\n"
        "(Reveals positive, negative, mixed, and neutral state-space localization)",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    ax.legend(loc="lower right", fontsize=9)
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "25_lochness_by_genotype.png", bbox_inches="tight")
    fig.savefig(fig_dir / "lochness_by_genotype.png", bbox_inches="tight")
    plt.close(fig)


def _fig26_lochness_by_celltype2(
    adata: Optional[ad.AnnData],
    lochness_by_celltype2_df: pd.DataFrame,
    fig_dir: Path,
) -> None:
    """Figure 26: Curated cell type (celltype_2) signed lochNESS distributions with zero line."""
    if adata is None or LOCHNESS_SELF not in adata.obs or "celltype_2" not in adata.obs:
        logger.warning("Skipping Figure 26: AnnData or lochness_self/celltype_2 unavailable.")
        return

    obs_df = adata.obs[["genotype", "celltype_2", LOCHNESS_SELF]].copy()
    obs_df[LOCHNESS_SELF] = pd.to_numeric(obs_df[LOCHNESS_SELF], errors="coerce")
    obs_valid = obs_df[(obs_df["genotype"] != "WT") & obs_df[LOCHNESS_SELF].notna()].copy()

    if obs_valid.empty:
        logger.warning("Skipping Figure 26: no non-WT cells with valid lochNESS found.")
        return

    present_cts = [ct for ct in CELLTYPE_ORDER if ct in obs_valid["celltype_2"].unique()]
    for ct in sorted(obs_valid["celltype_2"].unique()):
        if ct not in present_cts:
            present_cts.append(ct)

    fig, ax = plt.subplots(figsize=(9, max(5, 0.4 * len(present_cts))), dpi=300)

    palette = [CELLTYPE_PALETTE.get(ct, "#718096") for ct in present_cts]
    sns.boxplot(
        data=obs_valid,
        y="celltype_2",
        x=LOCHNESS_SELF,
        order=present_cts,
        palette=palette,
        fliersize=1.5,
        linewidth=0.8,
        width=0.6,
        ax=ax,
    )

    ax.axvline(0, color="#e53e3e", linestyle="--", linewidth=1.2, label="Neutral expected frequency (0)")
    ax.set_xlabel("Per-Cell Signed lochNESS (<0 Depleted, 0 Neutral, >0 Enriched)", fontsize=10, fontweight="bold")
    ax.set_ylabel("Curated Cell State (celltype_2)", fontsize=10, fontweight="bold")
    ax.set_title("Signed lochNESS Distributions Across Curated Cell States", fontsize=12, fontweight="bold", pad=12)
    ax.legend(loc="lower right", fontsize=9)
    sns.despine(fig, ax)
    fig.savefig(fig_dir / "26_lochness_by_celltype2.png", bbox_inches="tight")
    fig.savefig(fig_dir / "lochness_by_celltype2.png", bbox_inches="tight")
    plt.close(fig)


def _fig27_umap_ps_lochness_comparison(
    adata: Optional[ad.AnnData],
    sample_idx: np.ndarray,
    umap: np.ndarray,
    fig_dir: Path,
) -> None:
    """Figure 27: Side-by-side comparison figure of PS (Panel A) and lochNESS (Panel B) on identical UMAP coordinates."""
    if adata is None or len(sample_idx) == 0:
        logger.warning("Skipping Figure 27: AnnData or UMAP coordinates unavailable.")
        return

    has_ps = "ps_score" in adata.obs
    has_loch = LOCHNESS_SELF in adata.obs
    if not has_ps and not has_loch:
        logger.warning("Skipping Figure 27: neither ps_score nor lochness_self present.")
        return

    umap_sample = umap[sample_idx]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8), dpi=300)

    # Panel A: PS score
    if has_ps:
        ps_scores = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)
        ps_sample = ps_scores[sample_idx]
        valid_ps = np.isfinite(ps_sample)

        unscored_ps = ~valid_ps
        if np.any(unscored_ps):
            ax1.scatter(
                umap_sample[unscored_ps, 0],
                umap_sample[unscored_ps, 1],
                s=4,
                c="#e2e8f0",
                label="Unscored / Control",
                alpha=0.5,
                rasterized=True,
            )
        if np.any(valid_ps):
            sc1 = ax1.scatter(
                umap_sample[valid_ps, 0],
                umap_sample[valid_ps, 1],
                s=6,
                c=ps_sample[valid_ps],
                cmap="viridis",
                vmin=0.0,
                vmax=1.0,
                alpha=0.85,
                rasterized=True,
            )
            cbar1 = fig.colorbar(sc1, ax=ax1, shrink=0.75, pad=0.02)
            cbar1.set_label("Perturbation Score (PS)\n[0 = control-like, 1 = perturbed]", fontsize=9.5)
        ax1.set_title("A. Perturbation Response Strength (PS)", fontsize=12, fontweight="bold")
        ax1.set_xlabel("UMAP 1", fontsize=10)
        ax1.set_ylabel("UMAP 2", fontsize=10)
        if np.any(unscored_ps):
            ax1.legend(loc="upper right", fontsize=8.5, frameon=True)
        sns.despine(fig, ax1)
    else:
        ax1.text(0.5, 0.5, "PS Score Unavailable", ha="center", va="center", fontsize=12)
        ax1.set_title("A. Perturbation Score (PS)", fontsize=12, fontweight="bold")
        sns.despine(fig, ax1)

    # Panel B: Signed lochNESS
    if has_loch:
        loch_scores = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)
        loch_sample = loch_scores[sample_idx]
        valid_loch = np.isfinite(loch_sample)

        unscored_loch = ~valid_loch
        if np.any(unscored_loch):
            ax2.scatter(
                umap_sample[unscored_loch, 0],
                umap_sample[unscored_loch, 1],
                s=4,
                c="#e2e8f0",
                label="Unscored / Control",
                alpha=0.5,
                rasterized=True,
            )
        if np.any(valid_loch):
            vmax = max(1.5, min(6.0, float(np.percentile(np.abs(loch_sample[valid_loch]), 98))))
            sc2 = ax2.scatter(
                umap_sample[valid_loch, 0],
                umap_sample[valid_loch, 1],
                s=6,
                c=loch_sample[valid_loch],
                cmap="vlag",
                vmin=-vmax,
                vmax=vmax,
                alpha=0.85,
                rasterized=True,
            )
            cbar2 = fig.colorbar(sc2, ax=ax2, shrink=0.75, pad=0.02)
            cbar2.set_label("Per-Cell Signed lochNESS\n[<0 Depleted, 0 Neutral, >0 Enriched]", fontsize=9.5)
        ax2.set_title("B. State-Space Localization (Signed lochNESS)", fontsize=12, fontweight="bold")
        ax2.set_xlabel("UMAP 1", fontsize=10)
        ax2.set_ylabel("UMAP 2", fontsize=10)
        if np.any(unscored_loch):
            ax2.legend(loc="upper right", fontsize=8.5, frameon=True)
        sns.despine(fig, ax2)
    else:
        ax2.text(0.5, 0.5, "lochNESS Unavailable", ha="center", va="center", fontsize=12)
        ax2.set_title("B. Signed lochNESS", fontsize=12, fontweight="bold")
        sns.despine(fig, ax2)

    fig.suptitle(
        "Pancreatic Differentiation — Response Strength (PS) vs State-Space Localization (lochNESS)\n"
        "(Comparison on identical transcriptomic manifold coordinates)",
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )
    fig.tight_layout()
    fig.savefig(fig_dir / "27_umap_ps_lochness_comparison.png", bbox_inches="tight")
    fig.savefig(fig_dir / "umap_ps_lochness_comparison.png", bbox_inches="tight")
    plt.close(fig)


def _fig28_umap_highlight_genotypes(
    adata: Optional[ad.AnnData],
    sample_idx: np.ndarray,
    umap: np.ndarray,
    fig_dir: Path,
    highlight_genotypes: Optional[Union[str, Sequence[str]]] = None,
) -> None:
    """Figure 28: Genotype-specific highlight panels on the common UMAP embedding."""
    if adata is None or len(sample_idx) == 0:
        logger.warning("Skipping Figure 28: AnnData or UMAP coordinates unavailable.")
        return

    if highlight_genotypes is None:
        highlight_list = ["PDX1", "FOXA2", "RFX6", "NEUROG3"]
    elif isinstance(highlight_genotypes, str):
        highlight_list = [g.strip() for g in highlight_genotypes.split(",") if g.strip()]
    else:
        highlight_list = list(highlight_genotypes)

    genotypes = adata.obs["genotype"].iloc[sample_idx].astype(str).to_numpy()
    umap_sample = umap[sample_idx]

    available_highlights = [g for g in highlight_list if g in genotypes]
    if not available_highlights:
        non_wt = [g for g in pd.Series(genotypes).value_counts().index if g != "WT"]
        available_highlights = non_wt[:4]

    if not available_highlights:
        logger.warning("Skipping Figure 28: no highlighted genotypes found in dataset.")
        return

    n_panels = len(available_highlights)
    n_cols = min(4, n_panels)
    n_rows = (n_panels + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(4.5 * n_cols, 4.2 * n_rows), dpi=300, squeeze=False)

    has_loch = LOCHNESS_SELF in adata.obs
    loch_scores = None
    vmax = 3.0
    if has_loch:
        loch_scores = pd.to_numeric(adata.obs[LOCHNESS_SELF].iloc[sample_idx], errors="coerce").to_numpy(dtype=np.float64)
        if np.any(np.isfinite(loch_scores)):
            vmax = max(1.5, min(6.0, float(np.percentile(np.abs(loch_scores[np.isfinite(loch_scores)]), 98))))

    for idx, target in enumerate(available_highlights):
        r, c = idx // n_cols, idx % n_cols
        ax = axes[r, c]

        other_mask = (genotypes != target)
        target_mask = (genotypes == target)
        n_target = int(target_mask.sum())

        ax.scatter(
            umap_sample[other_mask, 0],
            umap_sample[other_mask, 1],
            s=2.5,
            c="#e2e8f0",
            alpha=0.4,
            rasterized=True,
        )

        if has_loch and loch_scores is not None and np.any(np.isfinite(loch_scores[target_mask])):
            ax.scatter(
                umap_sample[target_mask, 0],
                umap_sample[target_mask, 1],
                s=12,
                c=loch_scores[target_mask],
                cmap="vlag",
                vmin=-vmax,
                vmax=vmax,
                alpha=0.9,
                edgecolors="none",
                rasterized=True,
            )
        else:
            ax.scatter(
                umap_sample[target_mask, 0],
                umap_sample[target_mask, 1],
                s=12,
                c="#2b6cb0",
                alpha=0.9,
                edgecolors="none",
                rasterized=True,
            )

        ax.set_title(f"{target} (n = {n_target:,})", fontsize=10.5, fontweight="bold")
        ax.set_xlabel("UMAP 1", fontsize=8.5)
        ax.set_ylabel("UMAP 2", fontsize=8.5)
        sns.despine(fig, ax)

    for idx in range(n_panels, n_rows * n_cols):
        r, c = idx // n_cols, idx % n_cols
        axes[r, c].axis("off")

    fig.suptitle("Selected Perturbation State-Space Localization on Developmental Manifold", fontsize=12, fontweight="bold", y=1.02)
    fig.tight_layout()
    fig.savefig(fig_dir / "28_umap_highlight_genotypes.png", bbox_inches="tight")
    fig.savefig(fig_dir / "umap_highlight_genotypes.png", bbox_inches="tight")
    plt.close(fig)


# ===========================================================================
# Per-Perturbation / Per-Genotype UMAP Atlases
# ===========================================================================


def _plot_single_genotype_ps_umap(
    adata: ad.AnnData,
    genotype: str,
    umap: np.ndarray,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    out_path: Path,
) -> bool:
    """Generate individual PS UMAP for a single genotype on the common manifold."""
    if "ps_score" not in adata.obs:
        return False

    geno_arr = adata.obs["genotype"].astype(str).to_numpy()
    ps_arr = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)

    fg_mask = (geno_arr == genotype)
    n_cells = int(np.sum(fg_mask))
    if n_cells == 0:
        return False

    fg_ps = ps_arr[fg_mask]
    valid_mask = np.isfinite(fg_ps)
    n_valid = int(np.sum(valid_mask))
    if n_valid == 0:
        # Missing PS scores: do NOT set PS=0, do NOT create misleading colored panel
        return False

    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=200)

    # Background: sample if large to prevent memory ballooning
    if len(umap) > 30000:
        rng = np.random.default_rng(123)
        bg_idx = rng.choice(len(umap), size=30000, replace=False)
        ax.scatter(umap[bg_idx, 0], umap[bg_idx, 1], s=2.0, c="#e2e8f0", alpha=0.35, rasterized=True)
    else:
        ax.scatter(umap[:, 0], umap[:, 1], s=2.0, c="#e2e8f0", alpha=0.35, rasterized=True)

    # Foreground: genotype cells with valid PS
    fg_indices = np.flatnonzero(fg_mask)[valid_mask]
    sc = ax.scatter(
        umap[fg_indices, 0],
        umap[fg_indices, 1],
        s=8.0,
        c=fg_ps[valid_mask],
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
        alpha=0.85,
        rasterized=True,
    )

    cbar = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.02)
    cbar.set_label("Perturbation Score (PS)\n[0 = control-like, 1 = perturbed]", fontsize=9.5)

    med_ps = float(np.median(fg_ps[valid_mask]))
    if n_valid == n_cells:
        title_str = f"{genotype}\nPS response\nn = {n_cells:,} | median PS = {med_ps:.2f}"
    else:
        title_str = f"{genotype}\nPS response\nn = {n_cells:,} (valid PS = {n_valid:,}) | median PS = {med_ps:.2f}"

    ax.set_title(title_str, fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("UMAP 1", fontsize=9.5)
    ax.set_ylabel("UMAP 2", fontsize=9.5)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    sns.despine(fig, ax)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    plt.close("all")
    return True


def _plot_single_genotype_lochness_umap(
    adata: ad.AnnData,
    genotype: str,
    umap: np.ndarray,
    vmax_lochness: float,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    out_path: Path,
) -> bool:
    """Generate individual signed lochNESS UMAP for a single genotype on the common manifold."""
    if LOCHNESS_SELF not in adata.obs:
        return False

    geno_arr = adata.obs["genotype"].astype(str).to_numpy()
    loch_arr = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)

    fg_mask = (geno_arr == genotype)
    n_cells = int(np.sum(fg_mask))
    if n_cells == 0:
        return False

    fg_loch = loch_arr[fg_mask]
    valid_mask = np.isfinite(fg_loch)
    n_valid = int(np.sum(valid_mask))
    if n_valid == 0:
        return False

    valid_scores = fg_loch[valid_mask]
    pos_pct = float(100.0 * np.mean(valid_scores > 0)) if n_valid > 0 else 0.0
    neg_pct = float(100.0 * np.mean(valid_scores < 0)) if n_valid > 0 else 0.0

    fig, ax = plt.subplots(figsize=(8.0, 7.0), dpi=200)

    # Background: sample if large
    if len(umap) > 30000:
        rng = np.random.default_rng(123)
        bg_idx = rng.choice(len(umap), size=30000, replace=False)
        ax.scatter(umap[bg_idx, 0], umap[bg_idx, 1], s=2.0, c="#e2e8f0", alpha=0.35, rasterized=True)
    else:
        ax.scatter(umap[:, 0], umap[:, 1], s=2.0, c="#e2e8f0", alpha=0.35, rasterized=True)

    # Foreground: genotype cells with signed lochNESS
    fg_indices = np.flatnonzero(fg_mask)[valid_mask]
    sc = ax.scatter(
        umap[fg_indices, 0],
        umap[fg_indices, 1],
        s=8.0,
        c=valid_scores,
        cmap="vlag",
        vmin=-vmax_lochness,
        vmax=vmax_lochness,
        alpha=0.85,
        rasterized=True,
    )

    cbar = fig.colorbar(sc, ax=ax, shrink=0.75, pad=0.02)
    cbar.set_label("Per-Cell Signed lochNESS\n[<0 Depleted, 0 Neutral, >0 Enriched]", fontsize=9.5)

    title_str = f"{genotype}\nsigned lochNESS\nn = {n_cells:,} | +: {pos_pct:.0f}% | -: {neg_pct:.0f}%"
    ax.set_title(title_str, fontsize=11, fontweight="bold", pad=10)
    ax.set_xlabel("UMAP 1", fontsize=9.5)
    ax.set_ylabel("UMAP 2", fontsize=9.5)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    sns.despine(fig, ax)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    plt.close("all")
    return True


def _plot_single_genotype_combined_umap(
    adata: ad.AnnData,
    genotype: str,
    umap: np.ndarray,
    vmax_lochness: float,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    out_path: Path,
    ps_skip_reason: str = "",
) -> bool:
    """Generate paired 3-panel UMAP (celltype_2 context, PS score, signed lochNESS) for a single genotype."""
    geno_arr = adata.obs["genotype"].astype(str).to_numpy()
    fg_mask = (geno_arr == genotype)
    n_cells = int(np.sum(fg_mask))
    if n_cells == 0:
        return False

    has_ps = "ps_score" in adata.obs
    has_loch = LOCHNESS_SELF in adata.obs
    has_ct = "celltype_2" in adata.obs

    ps_arr = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64) if has_ps else np.full(len(geno_arr), np.nan)
    loch_arr = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64) if has_loch else np.full(len(geno_arr), np.nan)
    ct_arr = adata.obs["celltype_2"].astype(str).to_numpy() if has_ct else np.array(["Unknown"] * len(geno_arr))

    fg_ps = ps_arr[fg_mask]
    valid_ps_mask = np.isfinite(fg_ps)
    n_valid_ps = int(np.sum(valid_ps_mask))

    fg_loch = loch_arr[fg_mask]
    valid_loch_mask = np.isfinite(fg_loch)
    n_valid_loch = int(np.sum(valid_loch_mask))

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(19.5, 6.0), dpi=200)

    if len(umap) > 30000:
        rng = np.random.default_rng(123)
        bg_idx = rng.choice(len(umap), size=30000, replace=False)
        bg_u0, bg_u1 = umap[bg_idx, 0], umap[bg_idx, 1]
    else:
        bg_u0, bg_u1 = umap[:, 0], umap[:, 1]

    # ----------------- Panel A: Cell State Context (celltype_2) -----------------
    ax1.scatter(bg_u0, bg_u1, s=1.8, c="#e2e8f0", alpha=0.35, rasterized=True)
    if has_ct:
        fg_cts = ct_arr[fg_mask]
        unique_fg_cts = [ct for ct in CELLTYPE_ORDER if ct in set(fg_cts)]
        for ct in sorted(set(fg_cts)):
            if ct not in unique_fg_cts:
                unique_fg_cts.append(ct)
        for ct in unique_fg_cts:
            ct_sub_mask = (geno_arr == genotype) & (ct_arr == ct)
            color = CELLTYPE_PALETTE.get(ct, "#718096")
            ax1.scatter(
                umap[ct_sub_mask, 0],
                umap[ct_sub_mask, 1],
                s=8.0,
                c=color,
                label=f"{ct} ({int(ct_sub_mask.sum()):,})",
                alpha=0.85,
                rasterized=True,
            )
        if len(unique_fg_cts) <= 10:
            ax1.legend(loc="upper right", fontsize=7.5, frameon=True, markerscale=1.5, handletextpad=0.2)
    ax1.set_title(f"A. Curated Cell State (celltype_2)\n{genotype} (n = {n_cells:,})", fontsize=11, fontweight="bold", pad=8)
    ax1.set_xlabel("UMAP 1", fontsize=9.5)
    ax1.set_ylabel("UMAP 2", fontsize=9.5)
    ax1.set_xlim(xlim)
    ax1.set_ylim(ylim)
    sns.despine(fig, ax1)

    # ----------------- Panel B: Perturbation Response Strength (PS) -----------------
    ax2.scatter(bg_u0, bg_u1, s=1.8, c="#e2e8f0", alpha=0.35, rasterized=True)
    if n_valid_ps > 0:
        fg_ps_indices = np.flatnonzero(fg_mask)[valid_ps_mask]
        sc2 = ax2.scatter(
            umap[fg_ps_indices, 0],
            umap[fg_ps_indices, 1],
            s=8.0,
            c=fg_ps[valid_ps_mask],
            cmap="viridis",
            vmin=0.0,
            vmax=1.0,
            alpha=0.85,
            rasterized=True,
        )
        cbar2 = fig.colorbar(sc2, ax=ax2, shrink=0.75, pad=0.02)
        cbar2.set_label("Perturbation Score (PS)\n[0 = control-like, 1 = perturbed]", fontsize=9.0)
        med_ps = float(np.median(fg_ps[valid_ps_mask]))
        title_b = f"B. Perturbation Response Strength (PS)\nmedian PS = {med_ps:.2f} (valid = {n_valid_ps:,})"
    else:
        # PS unavailable
        fg_indices = np.flatnonzero(fg_mask)
        ax2.scatter(umap[fg_indices, 0], umap[fg_indices, 1], s=8.0, c="#a0aec0", alpha=0.5, rasterized=True)
        reason_msg = f"PS Unavailable\n({ps_skip_reason or 'Skipped / Unscored'})"
        ax2.text(
            0.5, 0.5, reason_msg,
            ha="center", va="center", transform=ax2.transAxes,
            fontsize=10.5, fontweight="bold", color="#4a5568",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#edf2f7", edgecolor="#cbd5e0"),
        )
        title_b = "B. Perturbation Response Strength (PS)\nPS Unavailable"
    ax2.set_title(title_b, fontsize=11, fontweight="bold", pad=8)
    ax2.set_xlabel("UMAP 1", fontsize=9.5)
    ax2.set_ylabel("UMAP 2", fontsize=9.5)
    ax2.set_xlim(xlim)
    ax2.set_ylim(ylim)
    sns.despine(fig, ax2)

    # ----------------- Panel C: State-Space Localization (Signed lochNESS) -----------------
    ax3.scatter(bg_u0, bg_u1, s=1.8, c="#e2e8f0", alpha=0.35, rasterized=True)
    if n_valid_loch > 0:
        fg_loch_indices = np.flatnonzero(fg_mask)[valid_loch_mask]
        valid_loch_scores = fg_loch[valid_loch_mask]
        sc3 = ax3.scatter(
            umap[fg_loch_indices, 0],
            umap[fg_loch_indices, 1],
            s=8.0,
            c=valid_loch_scores,
            cmap="vlag",
            vmin=-vmax_lochness,
            vmax=vmax_lochness,
            alpha=0.85,
            rasterized=True,
        )
        cbar3 = fig.colorbar(sc3, ax=ax3, shrink=0.75, pad=0.02)
        cbar3.set_label("Per-Cell Signed lochNESS\n[<0 Depleted, 0 Neutral, >0 Enriched]", fontsize=9.0)
        pos_pct = float(100.0 * np.mean(valid_loch_scores > 0))
        neg_pct = float(100.0 * np.mean(valid_loch_scores < 0))
        title_c = f"C. State-Space Localization (lochNESS)\n+: {pos_pct:.0f}% | -: {neg_pct:.0f}%"
    else:
        ax3.text(
            0.5, 0.5, "lochNESS Unavailable",
            ha="center", va="center", transform=ax3.transAxes,
            fontsize=10.5, fontweight="bold", color="#4a5568",
        )
        title_c = "C. State-Space Localization (lochNESS)\nUnavailable"
    ax3.set_title(title_c, fontsize=11, fontweight="bold", pad=8)
    ax3.set_xlabel("UMAP 1", fontsize=9.5)
    ax3.set_ylabel("UMAP 2", fontsize=9.5)
    ax3.set_xlim(xlim)
    ax3.set_ylim(ylim)
    sns.despine(fig, ax3)

    fig.suptitle(
        f"Biological Perturbation: {genotype} — Multi-Scale Profiling on Global Developmental Manifold",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    plt.close("all")
    return True


def _plot_multipanel_ps_atlas(
    adata: ad.AnnData,
    scored_genotypes: Sequence[str],
    umap: np.ndarray,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    out_png: Path,
    out_pdf: Optional[Path] = None,
) -> bool:
    """Generate multi-panel UMAP atlas for all genotypes with valid PS scores."""
    if len(scored_genotypes) == 0:
        return False

    geno_arr = adata.obs["genotype"].astype(str).to_numpy()
    ps_arr = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64)

    n_panels = len(scored_genotypes)
    n_cols = 4
    n_rows = (n_panels + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.8 * n_cols, 3.6 * n_rows), dpi=150, squeeze=False)

    if len(umap) > 15000:
        rng = np.random.default_rng(123)
        bg_idx = rng.choice(len(umap), size=15000, replace=False)
        bg_u0, bg_u1 = umap[bg_idx, 0], umap[bg_idx, 1]
    else:
        bg_u0, bg_u1 = umap[:, 0], umap[:, 1]

    last_sc = None
    for idx, target in enumerate(scored_genotypes):
        r, c = idx // n_cols, idx % n_cols
        ax = axes[r, c]

        # Background
        ax.scatter(bg_u0, bg_u1, s=1.0, c="#e2e8f0", alpha=0.3, rasterized=True)

        # Foreground
        fg_mask = (geno_arr == target)
        n_cells = int(np.sum(fg_mask))
        fg_ps = ps_arr[fg_mask]
        valid_mask = np.isfinite(fg_ps)
        fg_indices = np.flatnonzero(fg_mask)[valid_mask]

        if len(fg_indices) > 0:
            last_sc = ax.scatter(
                umap[fg_indices, 0],
                umap[fg_indices, 1],
                s=4.5,
                c=fg_ps[valid_mask],
                cmap="viridis",
                vmin=0.0,
                vmax=1.0,
                alpha=0.85,
                rasterized=True,
            )
            med_ps = float(np.median(fg_ps[valid_mask]))
            ax.set_title(f"{target}\n(n={n_cells:,} | med PS={med_ps:.2f})", fontsize=9.5, fontweight="bold", pad=4)
        else:
            ax.set_title(f"{target}\n(n={n_cells:,} | PS N/A)", fontsize=9.5, fontweight="bold", pad=4)

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        sns.despine(fig, ax)

    for idx in range(n_panels, n_rows * n_cols):
        r, c = idx // n_cols, idx % n_cols
        axes[r, c].axis("off")

    if last_sc is not None:
        cbar = fig.colorbar(last_sc, ax=axes.ravel().tolist(), shrink=0.5, pad=0.02, aspect=25)
        cbar.set_label("Perturbation Score (PS) [0 = control-like, 1 = perturbed]", fontsize=11, fontweight="bold")

    fig.suptitle(
        "Diabetes Perturb-seq — Per-Perturbation Response Score (PS) Atlas (Native Scale [0, 1])",
        fontsize=13.5,
        fontweight="bold",
        y=0.995,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight", dpi=150)
    if out_pdf is not None:
        try:
            fig.savefig(out_pdf, bbox_inches="tight", dpi=150)
        except Exception as exc:
            logger.warning("Failed to save PDF atlas %s: %s", out_pdf, exc)
    plt.close(fig)
    plt.close("all")
    gc.collect()
    return True


def _plot_multipanel_lochness_atlas(
    adata: ad.AnnData,
    genotypes: Sequence[str],
    umap: np.ndarray,
    vmax_lochness: float,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
    out_png: Path,
    out_pdf: Optional[Path] = None,
) -> bool:
    """Generate multi-panel UMAP atlas for all eligible genotypes colored by signed continuous lochNESS."""
    if len(genotypes) == 0 or LOCHNESS_SELF not in adata.obs:
        return False

    geno_arr = adata.obs["genotype"].astype(str).to_numpy()
    loch_arr = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)

    n_panels = len(genotypes)
    n_cols = 4
    n_rows = (n_panels + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.8 * n_cols, 3.6 * n_rows), dpi=150, squeeze=False)

    if len(umap) > 15000:
        rng = np.random.default_rng(123)
        bg_idx = rng.choice(len(umap), size=15000, replace=False)
        bg_u0, bg_u1 = umap[bg_idx, 0], umap[bg_idx, 1]
    else:
        bg_u0, bg_u1 = umap[:, 0], umap[:, 1]

    last_sc = None
    for idx, target in enumerate(genotypes):
        r, c = idx // n_cols, idx % n_cols
        ax = axes[r, c]

        # Background
        ax.scatter(bg_u0, bg_u1, s=1.0, c="#e2e8f0", alpha=0.3, rasterized=True)

        # Foreground
        fg_mask = (geno_arr == target)
        n_cells = int(np.sum(fg_mask))
        fg_loch = loch_arr[fg_mask]
        valid_mask = np.isfinite(fg_loch)
        fg_indices = np.flatnonzero(fg_mask)[valid_mask]

        if len(fg_indices) > 0:
            valid_scores = fg_loch[valid_mask]
            last_sc = ax.scatter(
                umap[fg_indices, 0],
                umap[fg_indices, 1],
                s=4.5,
                c=valid_scores,
                cmap="vlag",
                vmin=-vmax_lochness,
                vmax=vmax_lochness,
                alpha=0.85,
                rasterized=True,
            )
            pos_pct = float(100.0 * np.mean(valid_scores > 0))
            neg_pct = float(100.0 * np.mean(valid_scores < 0))
            ax.set_title(f"{target}\n(n={n_cells:,} | +:{pos_pct:.0f}% -:{neg_pct:.0f}%)", fontsize=9.5, fontweight="bold", pad=4)
        else:
            ax.set_title(f"{target}\n(n={n_cells:,} | lochNESS N/A)", fontsize=9.5, fontweight="bold", pad=4)

        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
        sns.despine(fig, ax)

    for idx in range(n_panels, n_rows * n_cols):
        r, c = idx // n_cols, idx % n_cols
        axes[r, c].axis("off")

    if last_sc is not None:
        cbar = fig.colorbar(last_sc, ax=axes.ravel().tolist(), shrink=0.5, pad=0.02, aspect=25)
        cbar.set_label("Per-Cell Signed lochNESS [<0 Depleted, 0 Neutral, >0 Enriched]", fontsize=11, fontweight="bold")

    fig.suptitle(
        "Diabetes Perturb-seq — Per-Perturbation State-Space Localization (lochNESS) Atlas",
        fontsize=13.5,
        fontweight="bold",
        y=0.995,
    )

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight", dpi=150)
    if out_pdf is not None:
        try:
            fig.savefig(out_pdf, bbox_inches="tight", dpi=150)
        except Exception as exc:
            logger.warning("Failed to save PDF atlas %s: %s", out_pdf, exc)
    plt.close(fig)
    plt.close("all")
    gc.collect()
    return True


def generate_per_genotype_umaps(
    adata: Optional[ad.AnnData],
    fig_dir: Path,
    tables_dir: Optional[Path] = None,
    ps_summary: Optional[pd.DataFrame] = None,
    ps_skipped: Optional[pd.DataFrame] = None,
    lochness_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Generate per-perturbation PS, lochNESS, combined UMAPs, and perturbation atlases.

    Parameters
    ----------
    adata : Optional[ad.AnnData]
        Annotated dataset containing 'genotype', 'ps_score', 'lochness_self', 'celltype_2', and 'X_umap'.
    fig_dir : Path
        Directory to write figure files.
    tables_dir : Optional[Path]
        Directory to write tables. Defaults to fig_dir.parent / "tables".
    ps_summary : Optional[pd.DataFrame]
        Summary of PS scores.
    ps_skipped : Optional[pd.DataFrame]
        Table of skipped PS perturbations with reasons.
    lochness_df : Optional[pd.DataFrame]
        Summary of lochNESS scores.

    Returns
    -------
    pd.DataFrame
        Manifest DataFrame mapping each perturbation to cell counts and generated figure paths.
    """
    if adata is None:
        logger.warning("Skipping per-genotype UMAPs: AnnData is None.")
        return pd.DataFrame()

    if tables_dir is None:
        tables_dir = fig_dir.parent / "tables"

    fig_dir.mkdir(parents=True, exist_ok=True)
    tables_dir.mkdir(parents=True, exist_ok=True)

    ps_dir = fig_dir / "per_genotype_ps"
    loch_dir = fig_dir / "per_genotype_lochness"
    comb_dir = fig_dir / "per_genotype_combined"
    ps_dir.mkdir(parents=True, exist_ok=True)
    loch_dir.mkdir(parents=True, exist_ok=True)
    comb_dir.mkdir(parents=True, exist_ok=True)

    # 1. Retrieve or derive UMAP representation
    if "X_umap" in adata.obsm:
        umap = np.asarray(adata.obsm["X_umap"], dtype=np.float32)
    elif "X_pca" in adata.obsm:
        umap = np.asarray(adata.obsm["X_pca"][:, :2], dtype=np.float32)
    else:
        logger.warning("Skipping per-genotype UMAPs: neither X_umap nor X_pca found in AnnData.")
        return pd.DataFrame()

    # Global coordinate bounds for consistent panel scaling
    x_min, x_max = float(np.nanmin(umap[:, 0])), float(np.nanmax(umap[:, 0]))
    y_min, y_max = float(np.nanmin(umap[:, 1])), float(np.nanmax(umap[:, 1]))
    x_pad = 0.05 * (x_max - x_min) if x_max > x_min else 1.0
    y_pad = 0.05 * (y_max - y_min) if y_max > y_min else 1.0
    xlim = (x_min - x_pad, x_max + x_pad)
    ylim = (y_min - y_pad, y_max + y_pad)

    # 2. Derive global symmetric lochNESS scale
    vmax_lochness = 3.0
    has_loch = LOCHNESS_SELF in adata.obs
    if has_loch:
        global_loch = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64)
        valid_global = global_loch[np.isfinite(global_loch)]
        if len(valid_global) > 0:
            q99 = float(np.nanquantile(np.abs(valid_global), 0.99))
            vmax_lochness = max(1.5, min(10.0, q99))

    # 3. Read / build skip reason mapping
    skip_reasons = {}
    if ps_skipped is not None and not ps_skipped.empty:
        g_col = "genotype" if "genotype" in ps_skipped.columns else "target_gene"
        r_col = "reason" if "reason" in ps_skipped.columns else "skip_reason"
        if g_col in ps_skipped.columns and r_col in ps_skipped.columns:
            for _, r in ps_skipped.iterrows():
                skip_reasons[str(r[g_col])] = str(r[r_col])
    elif (tables_dir / "ps_score_skipped.csv").is_file():
        try:
            sk_df = pd.read_csv(tables_dir / "ps_score_skipped.csv")
            g_col = "genotype" if "genotype" in sk_df.columns else "target_gene"
            r_col = "reason" if "reason" in sk_df.columns else "skip_reason"
            if g_col in sk_df.columns and r_col in sk_df.columns:
                for _, r in sk_df.iterrows():
                    skip_reasons[str(r[g_col])] = str(r[r_col])
        except Exception:
            pass

    # 4. Identify all non-WT genotypes
    genotypes = adata.obs["genotype"].astype(str).to_numpy()
    non_wt_genotypes = sorted(set(genotypes[genotypes != "WT"]))

    has_ps = "ps_score" in adata.obs
    ps_arr = pd.to_numeric(adata.obs["ps_score"], errors="coerce").to_numpy(dtype=np.float64) if has_ps else np.full(len(genotypes), np.nan)
    loch_arr = pd.to_numeric(adata.obs[LOCHNESS_SELF], errors="coerce").to_numpy(dtype=np.float64) if has_loch else np.full(len(genotypes), np.nan)

    manifest_rows = []
    scored_ps_genotypes = []
    scored_loch_genotypes = []

    logger.info("Generating per-genotype UMAPs for %d perturbations...", len(non_wt_genotypes))

    for idx, g in enumerate(non_wt_genotypes):
        t_mask = (genotypes == g)
        n_cells = int(np.sum(t_mask))
        safe_name = sanitize_identifier(g)

        # Check PS validity
        g_ps = ps_arr[t_mask]
        n_valid_ps = int(np.sum(np.isfinite(g_ps)))
        ps_avail = (n_valid_ps > 0)

        # Check lochNESS validity
        g_loch = loch_arr[t_mask]
        n_valid_loch = int(np.sum(np.isfinite(g_loch)))
        loch_avail = (n_valid_loch > 0)

        # Determine skip reason
        reason = ""
        if not ps_avail:
            reason = skip_reasons.get(g, "target gene not in the expression matrix" if "het" in g or "/" in g or "e" in g else "No valid PS scores computed")

        # Paths
        ps_png_rel = f"figures/per_genotype_ps/{safe_name}_ps_umap.png" if ps_avail else ""
        loch_png_rel = f"figures/per_genotype_lochness/{safe_name}_lochness_umap.png" if loch_avail else ""
        comb_png_rel = f"figures/per_genotype_combined/{safe_name}_ps_lochness_umap.png"

        ps_out = ps_dir / f"{safe_name}_ps_umap.png"
        loch_out = loch_dir / f"{safe_name}_lochness_umap.png"
        comb_out = comb_dir / f"{safe_name}_ps_lochness_umap.png"

        # 1. Individual PS UMAP (only if valid PS available)
        if ps_avail:
            _plot_single_genotype_ps_umap(adata, g, umap, xlim, ylim, ps_out)
            scored_ps_genotypes.append(g)

        # 2. Individual lochNESS UMAP
        if loch_avail:
            _plot_single_genotype_lochness_umap(adata, g, umap, vmax_lochness, xlim, ylim, loch_out)
            scored_loch_genotypes.append(g)

        # 3. Individual Combined Paired UMAP
        _plot_single_genotype_combined_umap(adata, g, umap, vmax_lochness, xlim, ylim, comb_out, ps_skip_reason=reason)

        manifest_rows.append({
            "genotype": g,
            "n_cells": n_cells,
            "n_valid_ps": n_valid_ps,
            "ps_available": ps_avail,
            "lochness_available": loch_avail,
            "ps_png": ps_png_rel,
            "lochness_png": loch_png_rel,
            "combined_png": comb_png_rel,
            "ps_skip_reason": reason,
        })

        if (idx + 1) % 10 == 0 or (idx + 1) == len(non_wt_genotypes):
            gc.collect()

    # Write manifest immediately
    manifest_df = pd.DataFrame(manifest_rows)
    manifest_path = tables_dir / "per_genotype_umap_manifest.csv"
    manifest_df.to_csv(manifest_path, index=False)
    logger.info("Per-genotype UMAP manifest written to %s (%d genotypes).", manifest_path, len(manifest_df))

    # 5. Multi-panel PS Atlas
    if scored_ps_genotypes:
        ps_atlas_png = fig_dir / "ps_per_genotype_umap_atlas.png"
        ps_atlas_pdf = fig_dir / "ps_per_genotype_umap_atlas.pdf"
        _plot_multipanel_ps_atlas(adata, scored_ps_genotypes, umap, xlim, ylim, ps_atlas_png, ps_atlas_pdf)
        try:
            _plot_multipanel_ps_atlas(adata, scored_ps_genotypes, umap, xlim, ylim, ps_dir / "ps_per_genotype_umap_atlas.png", ps_dir / "ps_per_genotype_umap_atlas.pdf")
        except Exception:
            pass

    # 6. Multi-panel lochNESS Atlas
    if scored_loch_genotypes:
        loch_atlas_png = fig_dir / "lochness_per_genotype_umap_atlas.png"
        loch_atlas_pdf = fig_dir / "lochness_per_genotype_umap_atlas.pdf"
        _plot_multipanel_lochness_atlas(adata, scored_loch_genotypes, umap, vmax_lochness, xlim, ylim, loch_atlas_png, loch_atlas_pdf)
        try:
            _plot_multipanel_lochness_atlas(adata, scored_loch_genotypes, umap, vmax_lochness, xlim, ylim, loch_dir / "lochness_per_genotype_umap_atlas.png", loch_dir / "lochness_per_genotype_umap_atlas.pdf")
        except Exception:
            pass

    logger.info("  PS UMAPs generated:       %d", len(scored_ps_genotypes))
    logger.info("  lochNESS UMAPs generated: %d", len(scored_loch_genotypes))
    logger.info("  Combined UMAPs generated: %d", len(manifest_rows))

    gc.collect()
    return manifest_df





def generate_diabetes_figures(
    adata: Optional[ad.AnnData],
    summary_df: pd.DataFrame,
    ps_summary: pd.DataFrame,
    dist_table: pd.DataFrame,
    dist_mat: pd.DataFrame,
    coords: pd.DataFrame,
    pheno_groups: pd.DataFrame,
    lochness_df: pd.DataFrame,
    log_or_matrix: pd.DataFrame,
    sig_matrix: pd.DataFrame,
    mod_results: Optional[Any],
    fig_dir: Path,
    lochness_celltype_matrix: Optional[pd.DataFrame] = None,
    ps_genotype_celltype_matrix: Optional[pd.DataFrame] = None,
    ps_by_genotype_df: Optional[pd.DataFrame] = None,
    ps_by_celltype2_df: Optional[pd.DataFrame] = None,
    lochness_by_genotype_df: Optional[pd.DataFrame] = None,
    lochness_by_celltype2_df: Optional[pd.DataFrame] = None,
    highlight_genotypes: Optional[Union[str, Sequence[str]]] = None,
    per_genotype_umaps: bool = True,
) -> Dict[str, Any]:
    """Generate all 28 presentation-grade figures with safe error isolation."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="ticks", font_scale=1.0)
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["font.family"] = "sans-serif"

    # Derive lochness_celltype_matrix if not provided
    if lochness_celltype_matrix is None or lochness_celltype_matrix.empty:
        if adata is not None and LOCHNESS_SELF in adata.obs:
            _, lochness_celltype_matrix = compute_lochness_by_celltype(adata, min_cells=10)
        else:
            by_ct_file = fig_dir.parent / "tables" / "lochness_by_genotype_celltype.csv"
            if not by_ct_file.is_file():
                by_ct_file = fig_dir.parent / "tables" / "lochness_by_celltype.csv"
            if by_ct_file.is_file():
                by_ct = pd.read_csv(by_ct_file)
                if not by_ct.empty and "genotype" in by_ct.columns and "celltype_2" in by_ct.columns:
                    p_mat = by_ct.pivot(index="genotype", columns="celltype_2", values="mean_lochness")
                    p_n = by_ct.pivot(index="genotype", columns="celltype_2", values="n_cells").fillna(0)
                    p_mat[p_n < 10] = np.nan
                    lochness_celltype_matrix = p_mat
                else:
                    lochness_celltype_matrix = pd.DataFrame()
            else:
                lochness_celltype_matrix = pd.DataFrame()

    # Derive ps_genotype_celltype_matrix if not provided
    if ps_genotype_celltype_matrix is None or ps_genotype_celltype_matrix.empty:
        if adata is not None and "ps_score" in adata.obs:
            _, ps_genotype_celltype_matrix = compute_ps_by_genotype_celltype(adata, min_cells=10)
        else:
            by_ct_file = fig_dir.parent / "tables" / "ps_by_genotype_celltype.csv"
            if by_ct_file.is_file():
                by_ct = pd.read_csv(by_ct_file)
                if not by_ct.empty and "genotype" in by_ct.columns and "celltype_2" in by_ct.columns:
                    p_mat = by_ct.pivot(index="genotype", columns="celltype_2", values="mean_ps")
                    n_col = "n_valid_ps" if "n_valid_ps" in by_ct.columns else ("n_cells" if "n_cells" in by_ct.columns else None)
                    if n_col:
                        p_n = by_ct.pivot(index="genotype", columns="celltype_2", values=n_col).fillna(0)
                        p_mat[p_n < 10] = np.nan
                    ps_genotype_celltype_matrix = p_mat
                else:
                    ps_genotype_celltype_matrix = pd.DataFrame()
            else:
                ps_genotype_celltype_matrix = pd.DataFrame()

    # Derive ps_by_genotype_df if not provided
    if ps_by_genotype_df is None or ps_by_genotype_df.empty:
        if adata is not None and "ps_score" in adata.obs:
            ps_by_genotype_df = compute_ps_by_genotype(adata)
        else:
            by_g_file = fig_dir.parent / "tables" / "ps_by_genotype.csv"
            if by_g_file.is_file():
                ps_by_genotype_df = pd.read_csv(by_g_file)
            else:
                ps_by_genotype_df = pd.DataFrame()

    # Derive ps_by_celltype2_df if not provided
    if ps_by_celltype2_df is None or ps_by_celltype2_df.empty:
        if adata is not None and "ps_score" in adata.obs:
            ps_by_celltype2_df = compute_ps_by_celltype2(adata)
        else:
            by_ct2_file = fig_dir.parent / "tables" / "ps_by_celltype2.csv"
            if by_ct2_file.is_file():
                ps_by_celltype2_df = pd.read_csv(by_ct2_file)
            else:
                ps_by_celltype2_df = pd.DataFrame()

    # Derive lochness_by_genotype_df if not provided
    if lochness_by_genotype_df is None or lochness_by_genotype_df.empty:
        if adata is not None and LOCHNESS_SELF in adata.obs:
            lochness_by_genotype_df = compute_lochness_by_genotype(adata)
        else:
            by_g_file = fig_dir.parent / "tables" / "lochness_by_genotype.csv"
            if by_g_file.is_file():
                lochness_by_genotype_df = pd.read_csv(by_g_file)
            else:
                lochness_by_genotype_df = pd.DataFrame()

    # Derive lochness_by_celltype2_df if not provided
    if lochness_by_celltype2_df is None or lochness_by_celltype2_df.empty:
        if adata is not None and LOCHNESS_SELF in adata.obs:
            lochness_by_celltype2_df = compute_lochness_by_celltype2(adata)
        else:
            by_ct2_file = fig_dir.parent / "tables" / "lochness_by_celltype2.csv"
            if not by_ct2_file.is_file():
                by_ct2_file = fig_dir.parent / "tables" / "lochness_celltype_summary.csv"
            if by_ct2_file.is_file():
                lochness_by_celltype2_df = pd.read_csv(by_ct2_file)
            else:
                lochness_by_celltype2_df = pd.DataFrame()

    # Subsample cells for UMAP scatters if large
    n_plot = min(adata.n_obs, 50_000) if adata is not None and adata.n_obs > 0 else 0
    sample_idx = np.array([], dtype=int)
    umap = np.zeros((0, 2), dtype=np.float32)
    if n_plot > 0 and adata is not None:
        rng = np.random.default_rng(123)
        sample_idx = rng.choice(adata.n_obs, size=n_plot, replace=False)
        sample_idx.sort()
        umap = np.asarray(adata.obsm.get("X_umap", adata.obsm.get("X_pca", np.zeros((adata.n_obs, 2)))[:, :2]))

    figures = [
        ("Figure 01: 01_umap_celltype2.png", _fig01_umap_celltype2, (adata, sample_idx, umap, fig_dir)),
        ("Figure 02: 02_umap_development_stage.png", _fig02_umap_development_stage, (adata, sample_idx, umap, fig_dir)),
        ("Figure 03: 03_stage_celltype_composition.png", _fig03_stage_celltype_composition, (adata, fig_dir)),
        ("Figure 04: 04_genotype_celltype_enrichment.png", _fig04_genotype_celltype_enrichment, (log_or_matrix, sig_matrix, fig_dir)),
        ("Figure 05: 05_ps_by_perturbation.png", _fig05_ps_by_perturbation, (ps_summary, fig_dir)),
        ("Figure 06: 06_energy_distance_by_perturbation.png", _fig06_energy_distance_by_perturbation, (dist_table, fig_dir)),
        ("Figure 07: 07_ps_vs_distance.png", _fig07_ps_vs_distance, (summary_df, fig_dir)),
        ("Figure 08: 08_distance_vs_lochness_positive.png", _fig08_distance_vs_lochness_positive, (summary_df, fig_dir)),
        ("Figure 09: 09_distance_vs_lochness_negative.png", _fig09_distance_vs_lochness_negative, (summary_df, fig_dir)),
        ("Figure 10: 10_ps_vs_lochness_positive.png", _fig10_ps_vs_lochness_positive, (summary_df, fig_dir)),
        ("Figure 11: 11_ps_vs_lochness_negative.png", _fig11_ps_vs_lochness_negative, (summary_df, fig_dir)),
        ("Figure 12: 12_distance_vs_lochness_absolute.png", _fig12_distance_vs_lochness_absolute, (summary_df, fig_dir)),
        ("Figure 13: 13_lochness_by_celltype.png", _fig13_lochness_by_celltype, (lochness_celltype_matrix, fig_dir)),
        ("Figure 14: 14_distance_space.png", _fig14_distance_space, (dist_mat, coords, pheno_groups, fig_dir)),
        ("Figure 15: 15_module_program_strength.png", _fig15_module_program_strength, (mod_results, fig_dir)),
        ("Figure 16: 16_program_activity_celltype2.png", _fig16_program_activity_celltype2, (mod_results, fig_dir)),
        ("Figure 17: 17_program_enrichment.png", _fig17_program_enrichment, (mod_results, fig_dir)),
        ("Figure 18: 18_module_network.png", _fig18_module_network, (mod_results, fig_dir)),
        ("Figure 19: 19_perturbation_summary.png", _fig19_perturbation_summary, (summary_df, fig_dir)),
        ("Figure 20: 20_umap_ps_score.png", _fig20_umap_ps_score, (adata, sample_idx, umap, fig_dir)),
        ("Figure 21: 21_umap_lochness_score.png", _fig21_umap_lochness_score, (adata, sample_idx, umap, fig_dir)),
        ("Figure 22: 22_ps_by_genotype.png", _fig22_ps_by_genotype, (adata, ps_by_genotype_df, fig_dir)),
        ("Figure 23: 23_ps_by_celltype2.png", _fig23_ps_by_celltype2, (adata, ps_by_celltype2_df, fig_dir)),
        ("Figure 24: 24_ps_genotype_celltype_heatmap.png", _fig24_ps_genotype_celltype_heatmap, (ps_genotype_celltype_matrix, fig_dir)),
        ("Figure 25: 25_lochness_by_genotype.png", _fig25_lochness_by_genotype, (adata, lochness_by_genotype_df, fig_dir)),
        ("Figure 26: 26_lochness_by_celltype2.png", _fig26_lochness_by_celltype2, (adata, lochness_by_celltype2_df, fig_dir)),
        ("Figure 27: 27_umap_ps_lochness_comparison.png", _fig27_umap_ps_lochness_comparison, (adata, sample_idx, umap, fig_dir)),
        ("Figure 28: 28_umap_highlight_genotypes.png", _fig28_umap_highlight_genotypes, (adata, sample_idx, umap, fig_dir, highlight_genotypes)),
    ]

    generated = []
    failed = []

    for name, func, args in figures:
        ok = safe_generate_figure(name, func, *args)
        if ok:
            generated.append(name)
        else:
            failed.append(name)

    manifest = {
        "total_attempted": len(figures),
        "total_generated": len(generated),
        "total_failed": len(failed),
        "generated": generated,
        "failed": failed,
    }

    logger.info("=" * 70)
    logger.info("FIGURE GENERATION SUMMARY")
    logger.info("  Figures attempted: %d", manifest["total_attempted"])
    logger.info("  Figures generated: %d", manifest["total_generated"])
    logger.info("  Figures failed:    %d", manifest["total_failed"])
    if failed:
        logger.warning("Failed figures:")
        for f in failed:
            logger.warning("  %s", f)
    logger.info("=" * 70)

    # Write manifest json
    with open(fig_dir / "figure_manifest.json", "w") as fp:
        json.dump(manifest, fp, indent=2)

    # Per-perturbation / per-genotype UMAP atlases
    if per_genotype_umaps and adata is not None:
        try:
            generate_per_genotype_umaps(
                adata=adata,
                fig_dir=fig_dir,
                tables_dir=fig_dir.parent / "tables",
                ps_summary=ps_summary,
                lochness_df=lochness_df,
            )
        except Exception as exc:
            logger.exception("Failed to generate per-genotype UMAP atlases: %s", exc)

    return manifest


def export_lean_h5ad(adata: ad.AnnData, out_path: Path) -> None:
    """Export lean AnnData containing only essential cell annotations and embeddings."""
    logger.info("=== Exporting Lean Output H5AD ===")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Core obs columns to retain
    obs_cols = [
        "genotype",
        "sgrna",
        "celltype_2",
        "development_stage",
        "orig.ident",
        "time_point",
        "ps_score",
        "ps_quadrant",
        LOCHNESS_SELF,
    ]
    avail_obs = [c for c in obs_cols if c in adata.obs.columns]
    lean_obs = adata.obs[avail_obs].copy()

    # Core embeddings
    lean_obsm = {}
    if "X_pca" in adata.obsm:
        lean_obsm["X_pca"] = np.asarray(adata.obsm["X_pca"], dtype=np.float32)
    if "X_umap" in adata.obsm:
        lean_obsm["X_umap"] = np.asarray(adata.obsm["X_umap"], dtype=np.float32)

    # Construct lean AnnData preserving sparse expression
    lean_adata = ad.AnnData(
        X=adata.X,
        obs=lean_obs,
        var=pd.DataFrame(index=adata.var_names),
        obsm=lean_obsm,
    )

    lean_adata.write_h5ad(out_path, compression="gzip")
    file_size_mb = out_path.stat().st_size / (1024 * 1024)
    logger.info("Wrote lean H5AD to %s (%.1f MB)", out_path, file_size_mb)


# ===========================================================================
# Recovery Driver (Plotting & Outputs from Checkpoint Tables)
# ===========================================================================


@dataclass
class CheckpointModulesResults:
    """Lightweight container mimicking ModulesResults for recovered Stage 7 tables."""

    modules: pd.DataFrame = field(default_factory=pd.DataFrame)
    gene_programs: pd.DataFrame = field(default_factory=pd.DataFrame)
    module_program: pd.DataFrame = field(default_factory=pd.DataFrame)
    program_activity: pd.DataFrame = field(default_factory=pd.DataFrame)
    program_enrichment: pd.DataFrame = field(default_factory=pd.DataFrame)
    program_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    tf_edges: pd.DataFrame = field(default_factory=pd.DataFrame)
    module_connectivity: pd.DataFrame = field(default_factory=pd.DataFrame)
    n_modules: int = 6
    n_programs: int = 4


def recover_and_finish_diabetes_run(
    input_path: Union[str, Path],
    outdir: Union[str, Path],
    highlight_genotypes: Optional[Union[str, Sequence[str]]] = None,
    per_genotype_umaps: bool = True,
) -> Path:
    """Recover and complete figure generation & lean H5AD export from saved checkpoint tables.

    Avoids recomputing expensive Stage 1-7 analytical pipelines if tables already exist on disk.
    """
    outdir = Path(outdir)
    tables_dir = outdir / "tables"
    figures_dir = outdir / "figures"
    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== RECOVERY MODE: Loading Checkpoint Tables from %s ===", tables_dir)

    def _read_csv(name: str, index_col: Optional[Union[int, str]] = None) -> pd.DataFrame:
        p = tables_dir / name
        if p.is_file():
            return pd.read_csv(p, index_col=index_col)
        return pd.DataFrame()

    ps_summary = _read_csv("ps_score_summary.csv")
    lochness_df = _read_csv("lochness_summary.csv")
    lochness_by_celltype = _read_csv("lochness_by_celltype.csv")
    if lochness_by_celltype.empty:
        lochness_by_celltype = _read_csv("lochness_by_genotype_celltype.csv")
    dist_table = _read_csv("distance_results.csv")
    if dist_table.empty:
        dist_table = _read_csv("distance_test.csv")
    dist_mat = _read_csv("distance_space_matrix.csv", index_col=0)
    coords = _read_csv("distance_space_coordinates.csv")
    pheno_groups = _read_csv("phenotype_groups.csv")
    celltype_enrich = _read_csv("celltype_enrichment.csv")
    mod_assignments = _read_csv("module_assignments.csv")
    gene_progs = _read_csv("gene_programs.csv")
    mod_prog = _read_csv("module_program_strength.csv", index_col=0)
    prog_act = _read_csv("program_activity_celltype.csv", index_col=0)
    prog_enrich = _read_csv("program_enrichment.csv")
    prog_summary = _read_csv("program_summary.csv")

    ps_by_genotype_df = _read_csv("ps_by_genotype.csv")
    ps_by_celltype2_df = _read_csv("ps_by_celltype2.csv")
    ps_by_genotype_celltype_df = _read_csv("ps_by_genotype_celltype.csv")
    ps_stage_df = _read_csv("ps_by_development_stage.csv")
    lochness_by_genotype_df = _read_csv("lochness_by_genotype.csv")
    lochness_by_celltype2_df = _read_csv("lochness_by_celltype2.csv")
    if lochness_by_celltype2_df.empty:
        lochness_by_celltype2_df = _read_csv("lochness_celltype_summary.csv")
    lochness_stage_df = _read_csv("lochness_by_development_stage.csv")

    mod_results = CheckpointModulesResults(
        modules=mod_assignments,
        gene_programs=gene_progs,
        module_program=mod_prog,
        program_activity=prog_act,
        program_enrichment=prog_enrich,
        program_summary=prog_summary,
        tf_edges=pd.DataFrame(),
        module_connectivity=pd.DataFrame(),
        n_modules=mod_assignments["module"].nunique() if not mod_assignments.empty and "module" in mod_assignments.columns else 6,
        n_programs=prog_enrich["program_id"].nunique() if not prog_enrich.empty and "program_id" in prog_enrich.columns else 4,
    )

    # Reconstruct log_or_matrix and sig_matrix from celltype_enrichment if available
    log_or_matrix = pd.DataFrame()
    sig_matrix = pd.DataFrame()
    if not celltype_enrich.empty:
        g_col = "genotype" if "genotype" in celltype_enrich.columns else "target_gene"
        c_col = "celltype_2" if "celltype_2" in celltype_enrich.columns else "cluster"
        if "control" in celltype_enrich.columns:
            primary_ctrl = "other" if "other" in celltype_enrich["control"].values else celltype_enrich["control"].iloc[0]
            enrich_sub = celltype_enrich[celltype_enrich["control"] == primary_ctrl]
        else:
            enrich_sub = celltype_enrich.drop_duplicates(subset=[g_col, c_col])
        if "log2_odds_ratio" in enrich_sub.columns:
            log_or_matrix = enrich_sub.pivot(index=g_col, columns=c_col, values="log2_odds_ratio")
        if "fdr" in enrich_sub.columns:
            sig_matrix = enrich_sub.pivot(index=g_col, columns=c_col, values="fdr")

    # Load AnnData for cell-level visualizations & lean export
    adata = None
    lean_p = outdir / "diabetes_analysis.h5ad"
    input_p = Path(input_path)
    if lean_p.is_file() and (input_path == "../data/diabetes.h5ad" or not input_p.is_file() or input_p.resolve() == lean_p.resolve()):
        logger.info("Loading existing AnnData from %s for cell-level embeddings...", lean_p)
        adata = ad.read_h5ad(lean_p)
    elif input_p.is_file():
        logger.info("Loading input AnnData from %s for cell-level embeddings...", input_p)
        adata = ad.read_h5ad(input_p)
        cfg_dummy = Config()
        adata = prepare_diabetes_anndata(adata, cfg_dummy)
    elif lean_p.is_file():
        logger.info("Loading existing AnnData from %s for cell-level embeddings...", lean_p)
        adata = ad.read_h5ad(lean_p)

    lochness_celltype_matrix = pd.DataFrame()
    ps_genotype_celltype_matrix = pd.DataFrame()

    # If adata is loaded, compute and persist any missing per-cell summary tables
    if adata is not None:
        if "ps_score" in adata.obs:
            if ps_by_genotype_df.empty:
                ps_by_genotype_df = compute_ps_by_genotype(adata)
                if not ps_by_genotype_df.empty:
                    ps_by_genotype_df.to_csv(tables_dir / "ps_by_genotype.csv", index=False)
            if ps_by_celltype2_df.empty:
                ps_by_celltype2_df = compute_ps_by_celltype2(adata)
                if not ps_by_celltype2_df.empty:
                    ps_by_celltype2_df.to_csv(tables_dir / "ps_by_celltype2.csv", index=False)
            if ps_by_genotype_celltype_df.empty or ps_genotype_celltype_matrix.empty:
                ps_by_genotype_celltype_df, ps_genotype_celltype_matrix = compute_ps_by_genotype_celltype(adata, min_cells=10)
                if not ps_by_genotype_celltype_df.empty:
                    ps_by_genotype_celltype_df.to_csv(tables_dir / "ps_by_genotype_celltype.csv", index=False)
            if ps_stage_df.empty:
                ps_stage_df = compute_ps_by_development_stage(adata)
                if not ps_stage_df.empty:
                    ps_stage_df.to_csv(tables_dir / "ps_by_development_stage.csv", index=False)

        if LOCHNESS_SELF in adata.obs:
            lochness_self_arr = np.asarray(adata.obs[LOCHNESS_SELF], dtype=np.float64)
            labels = adata.obs["genotype"].astype(str).to_numpy()
            targets = sorted(set(labels[labels != "WT"]))

            # If lochness_df is missing directional columns, derive them
            if lochness_df.empty or "lochness_positive_mean" not in lochness_df.columns:
                updated_rows = []
                for target in targets:
                    t_mask = (labels == target)
                    scores = lochness_self_arr[t_mask]
                    scores_finite = scores[np.isfinite(scores)]
                    if len(scores_finite) == 0:
                        continue
                    dir_stats = compute_lochness_directional_summary(scores_finite)
                    target_celltypes = adata.obs.loc[t_mask, "celltype_2"]
                    ct_counts = target_celltypes.value_counts()
                    dom_ct = ct_counts.index[0] if len(ct_counts) > 0 else "Unknown"
                    dom_frac = float(ct_counts.iloc[0] / len(scores)) if len(ct_counts) > 0 else 0.0
                    dom_mask = t_mask & (adata.obs["celltype_2"] == dom_ct).to_numpy()
                    dom_scores = lochness_self_arr[dom_mask]
                    dom_finite = dom_scores[np.isfinite(dom_scores)]
                    dom_loch = float(np.mean(dom_finite)) if len(dom_finite) > 0 else np.nan

                    updated_rows.append(
                        {
                            "genotype": target,
                            "n_cells": int(t_mask.sum()),
                            **dir_stats,
                            "lochness_peak": float(np.percentile(scores_finite, 95)),
                            "dominant_celltype_2": dom_ct,
                            "dominant_celltype_fraction": dom_frac,
                            "dominant_celltype_lochness": dom_loch,
                        }
                    )
                lochness_df = pd.DataFrame(updated_rows)
                lochness_df.to_csv(tables_dir / "lochness_summary.csv", index=False)

            # Compute / update genotype x celltype_2 signed lochNESS table and matrix
            by_ct_df, lochness_celltype_matrix = compute_lochness_by_celltype(
                adata, lochness_self=lochness_self_arr, min_cells=10
            )
            if not by_ct_df.empty:
                by_ct_df.to_csv(tables_dir / "lochness_by_celltype.csv", index=False)
                by_ct_df.to_csv(tables_dir / "lochness_by_genotype_celltype.csv", index=False)
                lochness_by_celltype = by_ct_df

            if lochness_by_genotype_df.empty:
                lochness_by_genotype_df = compute_lochness_by_genotype(adata)
                if not lochness_by_genotype_df.empty:
                    lochness_by_genotype_df.to_csv(tables_dir / "lochness_by_genotype.csv", index=False)

            if lochness_by_celltype2_df.empty:
                lochness_by_celltype2_df = compute_lochness_by_celltype2(adata)
                if not lochness_by_celltype2_df.empty:
                    lochness_by_celltype2_df.to_csv(tables_dir / "lochness_by_celltype2.csv", index=False)
                    lochness_by_celltype2_df.to_csv(tables_dir / "lochness_celltype_summary.csv", index=False)

            if lochness_stage_df.empty:
                lochness_stage_df = compute_lochness_by_development_stage(adata)
                if not lochness_stage_df.empty:
                    lochness_stage_df.to_csv(tables_dir / "lochness_by_development_stage.csv", index=False)
    else:
        if not lochness_by_celltype.empty and "genotype" in lochness_by_celltype.columns and "celltype_2" in lochness_by_celltype.columns:
            p_mat = lochness_by_celltype.pivot(index="genotype", columns="celltype_2", values="mean_lochness")
            p_n = lochness_by_celltype.pivot(index="genotype", columns="celltype_2", values="n_cells").fillna(0)
            p_mat[p_n < 10] = np.nan
            lochness_celltype_matrix = p_mat
        if not ps_by_genotype_celltype_df.empty and "genotype" in ps_by_genotype_celltype_df.columns and "celltype_2" in ps_by_genotype_celltype_df.columns:
            p_mat = ps_by_genotype_celltype_df.pivot(index="genotype", columns="celltype_2", values="mean_ps")
            n_col = "n_valid_ps" if "n_valid_ps" in ps_by_genotype_celltype_df.columns else ("n_cells" if "n_cells" in ps_by_genotype_celltype_df.columns else None)
            if n_col:
                p_n = ps_by_genotype_celltype_df.pivot(index="genotype", columns="celltype_2", values=n_col).fillna(0)
                p_mat[p_n < 10] = np.nan
            ps_genotype_celltype_matrix = p_mat

    # Build master summary table and write
    summary_df = _read_csv("perturbation_summary.csv")
    if adata is not None:
        summary_df = build_master_summary_table(
            adata,
            ps_summary=ps_summary,
            dist_table=dist_table,
            lochness_df=lochness_df,
            pheno_groups=pheno_groups,
            mod_results=mod_results,
        )
        summary_df.to_csv(tables_dir / "perturbation_summary.csv", index=False)

    # Export Lean H5AD if full AnnData was loaded
    if adata is not None and not (outdir / "diabetes_analysis.h5ad").is_file():
        h5ad_out = outdir / "diabetes_analysis.h5ad"
        export_lean_h5ad(adata, h5ad_out)

    # Generate Figures
    fig_manifest = generate_diabetes_figures(
        adata=adata,
        summary_df=summary_df,
        ps_summary=ps_summary,
        dist_table=dist_table,
        dist_mat=dist_mat,
        coords=coords,
        pheno_groups=pheno_groups,
        lochness_df=lochness_df,
        log_or_matrix=log_or_matrix,
        sig_matrix=sig_matrix,
        mod_results=mod_results,
        fig_dir=figures_dir,
        lochness_celltype_matrix=lochness_celltype_matrix,
        ps_genotype_celltype_matrix=ps_genotype_celltype_matrix,
        ps_by_genotype_df=ps_by_genotype_df,
        ps_by_celltype2_df=ps_by_celltype2_df,
        lochness_by_genotype_df=lochness_by_genotype_df,
        lochness_by_celltype2_df=lochness_by_celltype2_df,
        highlight_genotypes=highlight_genotypes,
        per_genotype_umaps=per_genotype_umaps,
    )

    logger.info("=" * 70)
    logger.info("RECOVERY & FIGURE REGENERATION COMPLETE")
    logger.info("  Tables:     %s", tables_dir)
    logger.info("  Figures:    %s", figures_dir)
    logger.info("=" * 70)
    return outdir


# ===========================================================================
# CLI & Main Workflow Driver
# ===========================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Pancreatic diabetes Perturb-seq analysis workflow",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="../data/diabetes.h5ad",
        help="Path to input diabetes.h5ad file",
    )
    parser.add_argument(
        "--outdir",
        "-o",
        type=str,
        default="results/diabetes_specific",
        help="Directory to write output tables and figures",
    )
    parser.add_argument(
        "--n-jobs",
        "-j",
        type=int,
        default=32,
        help="Number of CPU workers for parallel computation",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=123,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--min-cells",
        type=int,
        default=10,
        help="Minimum cells per perturbation required for testing",
    )
    parser.add_argument(
        "--max-cells-per-target",
        type=int,
        default=2000,
        help="Maximum cells sampled per perturbation in Distance / DistanceSpace",
    )
    parser.add_argument(
        "--max-control-cells",
        type=int,
        default=5000,
        help="Maximum WT control cells sampled for DistanceTest",
    )
    parser.add_argument(
        "--n-permutations",
        type=int,
        default=1000,
        help="Number of permutations for DistanceTest significance",
    )
    parser.add_argument(
        "--n-modules",
        type=int,
        default=6,
        help="Number of co-functional perturbation modules (M1-M6)",
    )
    parser.add_argument(
        "--n-programs",
        type=int,
        default=4,
        help="Number of downstream gene programs (P1-P4)",
    )
    parser.add_argument(
        "--hvg-count",
        type=int,
        default=3000,
        help="Number of highly variable genes for PCA",
    )
    parser.add_argument(
        "--n-pcs",
        type=int,
        default=50,
        help="Number of principal components",
    )
    parser.add_argument(
        "--highlight-genotypes",
        type=str,
        default="PDX1,FOXA2,RFX6,NEUROG3",
        help="Comma-separated genotypes to highlight in Figure 28 UMAP panels",
    )
    parser.add_argument(
        "--per-genotype-umaps",
        action="store_true",
        default=True,
        help="Generate per-perturbation PS, lochNESS, and paired UMAP atlases (default: True)",
    )
    parser.add_argument(
        "--no-per-genotype-umaps",
        action="store_false",
        dest="per_genotype_umaps",
        help="Disable generation of per-perturbation UMAP atlases",
    )
    parser.add_argument(
        "--recover",
        "--plot-only",
        "--plots-only",
        "--resume",
        action="store_true",
        dest="recover",
        help="Recover and regenerate figures/tables from saved checkpoint tables without re-running analysis",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output directory",
    )
    return parser.parse_args()


def run_diabetes_workflow(
    input_path: Union[str, Path],
    outdir: Union[str, Path],
    n_jobs: int = 32,
    seed: int = 123,
    min_cells: int = 10,
    max_cells_per_target: int = 2000,
    max_control_cells: int = 5000,
    n_permutations: int = 1000,
    n_modules: int = 6,
    n_programs: int = 4,
    hvg_count: int = 3000,
    n_pcs: int = 50,
    highlight_genotypes: Optional[Union[str, Sequence[str]]] = None,
    per_genotype_umaps: bool = True,
) -> Path:
    """Run the end-to-end diabetes Perturb-seq analysis workflow with immediate table persistence."""
    start_time = time.time()
    input_path = Path(input_path)
    outdir = Path(outdir)
    tables_dir = outdir / "tables"
    figures_dir = outdir / "figures"

    tables_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path.resolve()}")

    logger.info("Starting Diabetes Perturb-seq Analysis Workflow")
    logger.info("  Input:    %s", input_path.resolve())
    logger.info("  Outdir:   %s", outdir.resolve())
    logger.info("  Workers:  %d", n_jobs)
    logger.info("  Seed:     %d", seed)

    # 1. Load data
    logger.info("Loading input AnnData from %s...", input_path)
    adata = ad.read_h5ad(input_path)

    # 2. Validate dataset
    validate_dataset(adata)

    # 3. Configure pipeline parameters
    cfg = Config()
    cfg.run.seed = seed
    cfg.compute.n_jobs = n_jobs
    cfg.compute.cpu_workers = n_jobs
    cfg.cluster.n_top_genes = hvg_count
    cfg.cluster.n_pcs = n_pcs
    cfg.cluster.batch_key = None  # Do NOT batch-correct orig.ident (Requirement 6)

    cfg.ps_score.enabled = True
    cfg.ps_score.compute_lda_umap = False
    cfg.ps_score.min_cells_per_target = min_cells

    cfg.lochness.enabled = True
    cfg.lochness.genotype_key = "genotype"
    cfg.lochness.use_rep = "X_pca"
    cfg.lochness.n_pcs = n_pcs
    cfg.lochness.min_cells_per_target = min_cells

    cfg.distance.enabled = True
    cfg.distance.representation = "X_pca"
    cfg.distance.min_cells = min_cells
    cfg.distance.max_cells_per_target = max_cells_per_target
    cfg.distance.max_control_cells = max_control_cells
    cfg.distance.n_permutations = n_permutations
    cfg.distance.fdr_threshold = 0.05
    cfg.distance.random_seed = seed

    cfg.distance_space.enabled = True
    cfg.distance_space.representation = "X_pca"
    cfg.distance_space.min_cells = min_cells
    cfg.distance_space.max_cells_per_target = max_cells_per_target
    cfg.distance_space.random_seed = seed

    cfg.enrichment.enabled = True
    cfg.enrichment.cluster_key = "celltype_2"
    cfg.enrichment.stratify_by = "orig.ident"

    cfg.modules.enabled = True
    cfg.modules.cluster_key = "celltype_2"
    cfg.modules.n_modules = n_modules
    cfg.modules.n_programs = n_programs

    # 4. Prepare annotations & PCA
    adata = prepare_diabetes_anndata(adata, cfg)

    # 5. Run PS Score analysis & save intermediate
    ps_summary, ps_skipped = run_diabetes_ps_analysis(adata, cfg)
    if not ps_summary.empty:
        ps_summary.to_csv(tables_dir / "ps_score_summary.csv", index=False)
    if not ps_skipped.empty:
        ps_skipped.to_csv(tables_dir / "ps_score_skipped.csv", index=False)

    ps_by_genotype_df = compute_ps_by_genotype(adata)
    if not ps_by_genotype_df.empty:
        ps_by_genotype_df.to_csv(tables_dir / "ps_by_genotype.csv", index=False)

    ps_by_celltype2_df = compute_ps_by_celltype2(adata)
    if not ps_by_celltype2_df.empty:
        ps_by_celltype2_df.to_csv(tables_dir / "ps_by_celltype2.csv", index=False)

    ps_by_genotype_celltype_df, ps_genotype_celltype_matrix = compute_ps_by_genotype_celltype(adata, min_cells=min_cells)
    if not ps_by_genotype_celltype_df.empty:
        ps_by_genotype_celltype_df.to_csv(tables_dir / "ps_by_genotype_celltype.csv", index=False)

    ps_stage_df = compute_ps_by_development_stage(adata)
    if not ps_stage_df.empty:
        ps_stage_df.to_csv(tables_dir / "ps_by_development_stage.csv", index=False)

    # 6. Run lochNESS State-Space Localization & save intermediate
    lochness_df, lochness_by_celltype, lochness_celltype_matrix, _ = run_diabetes_lochness_analysis(adata, cfg)
    if not lochness_df.empty:
        lochness_df.to_csv(tables_dir / "lochness_summary.csv", index=False)
    if not lochness_by_celltype.empty:
        lochness_by_celltype.to_csv(tables_dir / "lochness_by_celltype.csv", index=False)
        lochness_by_celltype.to_csv(tables_dir / "lochness_by_genotype_celltype.csv", index=False)

    lochness_by_genotype_df = compute_lochness_by_genotype(adata)
    if not lochness_by_genotype_df.empty:
        lochness_by_genotype_df.to_csv(tables_dir / "lochness_by_genotype.csv", index=False)

    lochness_by_celltype2_df = compute_lochness_by_celltype2(adata)
    if not lochness_by_celltype2_df.empty:
        lochness_by_celltype2_df.to_csv(tables_dir / "lochness_by_celltype2.csv", index=False)
        lochness_by_celltype2_df.to_csv(tables_dir / "lochness_celltype_summary.csv", index=False)

    lochness_stage_df = compute_lochness_by_development_stage(adata)
    if not lochness_stage_df.empty:
        lochness_stage_df.to_csv(tables_dir / "lochness_by_development_stage.csv", index=False)

    # 7. Run Energy Distance / DistanceTest vs WT & save intermediate
    dist_table, dist_skipped = run_diabetes_distance_analysis(adata, cfg)
    if not dist_table.empty:
        dist_table.to_csv(tables_dir / "distance_results.csv", index=False)
        dist_table.to_csv(tables_dir / "distance_test.csv", index=False)
    if not dist_skipped.empty:
        dist_skipped.to_csv(tables_dir / "distance_skipped.csv", index=False)

    # 8. Run DistanceSpace (Pairwise Manifold & Phenotype Groups) & save intermediate
    dist_mat, coords, neighbors, pheno_groups = run_diabetes_distance_space_analysis(adata, cfg)
    if not dist_mat.empty:
        dist_mat.to_csv(tables_dir / "distance_space_matrix.csv")
    if not coords.empty:
        coords.to_csv(tables_dir / "distance_space_coordinates.csv", index=False)
    if not neighbors.empty:
        neighbors.to_csv(tables_dir / "distance_space_neighbors.csv", index=False)
    if not pheno_groups.empty:
        pheno_groups.to_csv(tables_dir / "phenotype_groups.csv", index=False)

    # 9. Run Cell-Type Enrichment (Stratified by orig.ident) & save intermediate
    enrich_table, log_or_matrix, sig_matrix = run_diabetes_enrichment_analysis(adata, cfg)
    if not enrich_table.empty:
        enrich_table.to_csv(tables_dir / "celltype_enrichment.csv", index=False)

    # 10. Run Stage 7 Co-functional Modules & Gene Programs & save intermediate
    mod_results = run_diabetes_modules_analysis(adata, cfg)
    if mod_results is not None:
        if not mod_results.modules.empty:
            mod_results.modules.to_csv(tables_dir / "module_assignments.csv", index=False)
        if not mod_results.gene_programs.empty:
            mod_results.gene_programs.to_csv(tables_dir / "gene_programs.csv", index=False)
        if not mod_results.module_program.empty:
            mod_results.module_program.to_csv(tables_dir / "module_program_strength.csv")
        if not mod_results.program_activity.empty:
            mod_results.program_activity.to_csv(tables_dir / "program_activity_celltype.csv")
        if not mod_results.program_enrichment.empty:
            mod_results.program_enrichment.to_csv(tables_dir / "program_enrichment.csv", index=False)
        if not mod_results.program_summary.empty:
            mod_results.program_summary.to_csv(tables_dir / "program_summary.csv", index=False)

    # 11. Assemble & Persist Master Summary Table BEFORE Optional Figures
    summary_df = build_master_summary_table(
        adata,
        ps_summary=ps_summary,
        dist_table=dist_table,
        lochness_df=lochness_df,
        pheno_groups=pheno_groups,
        mod_results=mod_results,
    )
    summary_df.to_csv(tables_dir / "perturbation_summary.csv", index=False)

    # 12. Export Lean H5AD BEFORE Optional Figures
    h5ad_out = outdir / "diabetes_analysis.h5ad"
    export_lean_h5ad(adata, h5ad_out)

    # 13. Generate All Primary Figures (Each isolated with safe_generate_figure)
    fig_manifest = generate_diabetes_figures(
        adata=adata,
        summary_df=summary_df,
        ps_summary=ps_summary,
        dist_table=dist_table,
        dist_mat=dist_mat,
        coords=coords,
        pheno_groups=pheno_groups,
        lochness_df=lochness_df,
        log_or_matrix=log_or_matrix,
        sig_matrix=sig_matrix,
        mod_results=mod_results,
        fig_dir=figures_dir,
        lochness_celltype_matrix=lochness_celltype_matrix,
        ps_genotype_celltype_matrix=ps_genotype_celltype_matrix,
        ps_by_genotype_df=ps_by_genotype_df,
        ps_by_celltype2_df=ps_by_celltype2_df,
        lochness_by_genotype_df=lochness_by_genotype_df,
        lochness_by_celltype2_df=lochness_by_celltype2_df,
        highlight_genotypes=highlight_genotypes,
        per_genotype_umaps=per_genotype_umaps,
    )

    elapsed = time.time() - start_time
    logger.info("=" * 70)
    logger.info("DIABETES ANALYSIS WORKFLOW COMPLETE")
    logger.info("  Runtime:    %.1f seconds (%.2f minutes)", elapsed, elapsed / 60.0)
    logger.info("  Tables:     %s", tables_dir)
    logger.info("  Figures:    %s", figures_dir)
    logger.info("  Lean H5AD:  %s", h5ad_out)
    logger.info("=" * 70)

    return outdir


def main() -> None:
    """CLI entry point."""
    args = parse_args()
    if getattr(args, "recover", False):
        recover_and_finish_diabetes_run(
            input_path=args.input,
            outdir=args.outdir,
            highlight_genotypes=getattr(args, "highlight_genotypes", None),
            per_genotype_umaps=getattr(args, "per_genotype_umaps", True),
        )
    else:
        run_diabetes_workflow(
            input_path=args.input,
            outdir=args.outdir,
            n_jobs=args.n_jobs,
            seed=args.seed,
            min_cells=args.min_cells,
            max_cells_per_target=args.max_cells_per_target,
            max_control_cells=args.max_control_cells,
            n_permutations=args.n_permutations,
            n_modules=args.n_modules,
            n_programs=args.n_programs,
            hvg_count=args.hvg_count,
            n_pcs=args.n_pcs,
            highlight_genotypes=getattr(args, "highlight_genotypes", None),
            per_genotype_umaps=getattr(args, "per_genotype_umaps", True),
        )


if __name__ == "__main__":
    main()

