"""Normalization, dimensionality reduction, embedding and Leiden clustering.

After :func:`normalize`, the downstream contract is:

* ``layers['counts']``  — raw integer counts
* ``layers['lognorm']`` — log1p library-size-normalized counts
* ``adata.X``           — log-normalized values

For large datasets, this module uses a memory-aware path:

* Avoid unnecessary full-matrix copies.
* Estimate highly variable genes (HVGs) on a representative subset of cells.
* Perform scaling/PCA only on HVGs.
* Never regress covariates across the full gene matrix for multi-million-cell
  datasets.
* Avoid copying the full log-normalized matrix merely to restore ``adata.X``.

This is particularly important for datasets such as KOLF with millions of
cells and tens of thousands of genes.
"""

from __future__ import annotations

import gc
import logging
from typing import Optional

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc

from .config import Config
from .io import LANE_KEY


logger = logging.getLogger(__name__)

LOGNORM_LAYER = "lognorm"
CLUSTER_KEY = "leiden"


def normalize(expr: ad.AnnData, cfg: Config) -> ad.AnnData:
    """Library-size normalize and log1p-transform while preserving raw counts.

    Small datasets retain the previous behaviour.

    Large datasets avoid unnecessary copies of the complete expression matrix.
    This is critical for matrices containing millions of cells.
    """

    is_large = cfg.use_large_mode(expr.n_obs)

    # --------------------------------------------------------------
    # Already normalized
    # --------------------------------------------------------------
    if LOGNORM_LAYER in expr.layers:
        logger.info(
            "Using pre-computed '%s' layer; skipping normalization",
            LOGNORM_LAYER,
        )

        if is_large:
            # Do NOT duplicate a potentially enormous sparse matrix.
            expr.X = expr.layers[LOGNORM_LAYER]
            logger.info(
                "Large-dataset memory mode: using '%s' directly as X "
                "without making a full copy",
                LOGNORM_LAYER,
            )
        else:
            expr.X = expr.layers[LOGNORM_LAYER].copy()

        return expr

    # --------------------------------------------------------------
    # Preserve counts
    # --------------------------------------------------------------
    if "counts" not in expr.layers:
        logger.info(
            "No 'counts' layer found; preserving current X as raw counts"
        )
        expr.layers["counts"] = expr.X.copy()
        gc.collect()

    else:
        logger.info("Using existing 'counts' layer as raw expression")

    # --------------------------------------------------------------
    # Create writable normalized expression
    # --------------------------------------------------------------
    #
    # counts must remain unchanged, so normalization requires a writable
    # matrix distinct from layers['counts'].
    #
    # Assignment replaces the previous X reference. Explicit collection is
    # useful for huge AnnData objects where the previous matrix may itself be
    # many GB.
    expr.X = expr.layers["counts"].copy()
    gc.collect()

    sc.pp.normalize_total(
        expr,
        target_sum=cfg.cluster.target_sum,
    )

    sc.pp.log1p(expr)

    # --------------------------------------------------------------
    # Preserve normalized expression
    # --------------------------------------------------------------
    if is_large:
        # Important:
        # Do not immediately make yet another full copy.
        #
        # Downstream large-dataset operations in this module do not modify
        # expr.X in place. Scaling occurs only on a temporary HVG subset.
        expr.layers[LOGNORM_LAYER] = expr.X

        logger.info(
            "Normalized to %s counts per cell and log1p-transformed "
            "[large-dataset memory mode; no duplicate lognorm copy]",
            cfg.cluster.target_sum or "median library size",
        )
    else:
        expr.layers[LOGNORM_LAYER] = expr.X.copy()

        logger.info(
            "Normalized to %s counts per cell and log1p-transformed",
            cfg.cluster.target_sum or "median library size",
        )

    gc.collect()

    return expr


def _select_hvgs(expr: ad.AnnData, cfg: Config) -> None:
    """Select highly variable genes.

    For large datasets, HVGs are estimated from a reproducible random subset
    rather than all cells. The resulting HVG mask is then copied back to the
    complete AnnData object.

    This preserves all cells for downstream PCA/neighbors/Leiden while avoiding
    a very expensive full-dataset HVG calculation.
    """

    c = cfg.cluster
    n_top = min(c.n_top_genes, expr.n_vars)

    if not cfg.use_large_mode(expr.n_obs):
        sc.pp.highly_variable_genes(
            expr,
            n_top_genes=n_top,
        )

        logger.info(
            "Selected %d highly variable genes",
            int(expr.var["highly_variable"].sum()),
        )

        return

    # --------------------------------------------------------------
    # Large dataset HVG estimation
    # --------------------------------------------------------------
    n_sample = min(cfg.scaling.marker_max_cells, expr.n_obs)

    logger.info(
        "Large dataset detected: %d cells x %d genes",
        expr.n_obs,
        expr.n_vars,
    )

    logger.info(
        "Estimating %d HVGs using a reproducible subset of %d cells",
        n_top,
        n_sample,
    )

    rng = np.random.default_rng(cfg.run.seed)

    sampled_idx = rng.choice(
        expr.n_obs,
        size=n_sample,
        replace=False,
    )

    # Sorting makes sparse row slicing somewhat friendlier and deterministic.
    sampled_idx.sort()

    # Only a cell subset is copied. We deliberately do not copy the entire
    # multi-million-cell object.
    hvg_expr = expr[sampled_idx, :].copy()

    sc.pp.highly_variable_genes(
        hvg_expr,
        n_top_genes=n_top,
    )

    hvg_mask = (
        hvg_expr.var["highly_variable"]
        .to_numpy()
        .astype(bool)
    )

    if hvg_mask.sum() == 0:
        raise RuntimeError(
            "Large-dataset HVG selection returned zero highly variable genes."
        )

    expr.var["highly_variable"] = hvg_mask

    logger.info(
        "Selected %d highly variable genes from %d-cell reference subset",
        int(hvg_mask.sum()),
        n_sample,
    )

    del hvg_expr
    del sampled_idx
    del hvg_mask

    gc.collect()


def _run_pca_on_hvgs(expr: ad.AnnData, cfg: Config) -> None:
    """Run PCA using only highly variable genes.

    A temporary HVG AnnData object is created so that operations such as
    scaling never densify or modify all genes in the parent dataset.
    """

    c = cfg.cluster

    if "highly_variable" not in expr.var.columns:
        raise RuntimeError(
            "Cannot run PCA because highly variable genes have not been selected."
        )

    hvg_mask = expr.var["highly_variable"].to_numpy(dtype=bool)
    n_hvg = int(hvg_mask.sum())

    if n_hvg < 2:
        raise RuntimeError(
            f"Only {n_hvg} highly variable genes available; PCA requires at least 2."
        )

    n_pcs = int(
        min(
            c.n_pcs,
            expr.n_obs - 1,
            n_hvg - 1,
        )
    )

    logger.info(
        "Creating PCA working matrix: %d cells x %d HVGs",
        expr.n_obs,
        n_hvg,
    )

    # This copy contains only ~3000 genes rather than all ~37k genes.
    pca_expr = expr[:, hvg_mask].copy()

    # --------------------------------------------------------------
    # Optional covariate regression
    # --------------------------------------------------------------
    if c.regress_out:
        missing = [
            key
            for key in c.regress_out
            if key not in pca_expr.obs.columns
        ]

        if missing:
            raise ValueError(
                "cluster.regress_out refers to missing obs columns: "
                f"{missing}"
            )

        logger.info(
            "Regressing out %s on HVG working matrix",
            c.regress_out,
        )

        # Regression is now restricted to HVGs rather than every gene.
        sc.pp.regress_out(
            pca_expr,
            c.regress_out,
        )

    # --------------------------------------------------------------
    # Optional scaling
    # --------------------------------------------------------------
    if c.scale_max_value is not None:
        logger.info(
            "Scaling HVG working matrix with max_value=%s",
            c.scale_max_value,
        )

        sc.pp.scale(
            pca_expr,
            max_value=c.scale_max_value,
        )

    # --------------------------------------------------------------
    # PCA
    # --------------------------------------------------------------
    sc.tl.pca(
        pca_expr,
        n_comps=n_pcs,
        svd_solver="arpack",
        random_state=cfg.run.seed,
    )

    # Preserve only PCA results in the original object.
    expr.obsm["X_pca"] = pca_expr.obsm["X_pca"]

    if "pca" in pca_expr.uns:
        expr.uns["pca"] = pca_expr.uns["pca"]

    logger.info(
        "PCA: %d components on %d HVGs",
        n_pcs,
        n_hvg,
    )

    del pca_expr
    del hvg_mask

    gc.collect()


def embed_and_cluster(expr: ad.AnnData, cfg: Config) -> ad.AnnData:
    """HVG selection, PCA, optional Harmony, neighbors, UMAP and Leiden."""

    c = cfg.cluster
    sc.settings.seed = cfg.run.seed

    # --------------------------------------------------------------
    # 1. Highly variable genes
    # --------------------------------------------------------------
    _select_hvgs(expr, cfg)

    # --------------------------------------------------------------
    # 2. PCA on HVGs only
    # --------------------------------------------------------------
    _run_pca_on_hvgs(expr, cfg)

    n_pcs = int(expr.obsm["X_pca"].shape[1])

    # --------------------------------------------------------------
    # 3. Optional Harmony
    # --------------------------------------------------------------
    use_rep = "X_pca"

    if c.batch_key:
        harmony_rep = _run_harmony(expr, cfg)

        if harmony_rep is not None:
            use_rep = harmony_rep

    # --------------------------------------------------------------
    # 4. Neighbor graph
    # --------------------------------------------------------------
    logger.info(
        "Computing %d-nearest-neighbor graph using %s",
        c.n_neighbors,
        use_rep,
    )

    sc.pp.neighbors(
        expr,
        n_neighbors=c.n_neighbors,
        n_pcs=n_pcs,
        use_rep=use_rep,
        random_state=cfg.run.seed,
    )

    gc.collect()

    # --------------------------------------------------------------
    # 5. UMAP
    # --------------------------------------------------------------
    #
    # UMAP on several million cells may still be expensive. We keep the
    # existing behaviour for now so pipeline semantics do not change.
    # If KOLF later stalls here, this should become the next large-dataset
    # optimisation target.
    logger.info(
        "Computing UMAP for %d cells",
        expr.n_obs,
    )

    sc.tl.umap(
        expr,
        min_dist=c.umap_min_dist,
        random_state=cfg.run.seed,
    )

    gc.collect()

    # --------------------------------------------------------------
    # 6. Leiden
    # --------------------------------------------------------------
    sc.tl.leiden(
        expr,
        key_added=CLUSTER_KEY,
        resolution=c.leiden_resolution,
        flavor="igraph",
        n_iterations=2,
        directed=False,
        random_state=cfg.run.seed,
    )

    n_clusters = expr.obs[CLUSTER_KEY].nunique()

    logger.info(
        "Leiden clustering at resolution %.2f: %d clusters",
        c.leiden_resolution,
        n_clusters,
    )

    # --------------------------------------------------------------
    # Restore X
    # --------------------------------------------------------------
    #
    # Scaling/regression happened only on the temporary HVG object, so the
    # parent's X was never changed.
    #
    # For a large dataset, avoid another enormous copy.
    if LOGNORM_LAYER in expr.layers:
        if cfg.use_large_mode(expr.n_obs):
            expr.X = expr.layers[LOGNORM_LAYER]

            logger.info(
                "Large-dataset memory mode: restored X from '%s' "
                "without making a full copy",
                LOGNORM_LAYER,
            )
        else:
            expr.X = expr.layers[LOGNORM_LAYER].copy()

    gc.collect()

    return expr


def reset_embedding(expr: ad.AnnData) -> ad.AnnData:
    """Drop everything :func:`embed_and_cluster` produced, in place.

    Used when a subset of an already-embedded object is re-embedded on its own
    (``cluster.assigned_only``).

    The ``counts`` and ``lognorm`` layers are preserved.
    """

    for key in (
        "X_pca",
        "X_pca_harmony",
        "X_umap",
    ):
        if key in expr.obsm:
            del expr.obsm[key]

    for key in list(expr.obsp.keys()):
        del expr.obsp[key]

    for key in (
        "pca",
        "neighbors",
        "umap",
        CLUSTER_KEY,
        f"{CLUSTER_KEY}_colors",
    ):
        expr.uns.pop(key, None)

    if "highly_variable" in expr.var.columns:
        del expr.var["highly_variable"]

    if CLUSTER_KEY in expr.obs.columns:
        del expr.obs[CLUSTER_KEY]

    gc.collect()

    return expr


def _run_harmony(
    expr: ad.AnnData,
    cfg: Config,
) -> Optional[str]:
    """Batch-correct PCA embedding with Harmony.

    Returns the corrected representation key.
    """

    key = cfg.cluster.batch_key

    if key not in expr.obs.columns:
        raise ValueError(
            f"cluster.batch_key={key!r} is not an obs column. "
            f"Available: {sorted(expr.obs.columns)[:30]}"
        )

    n_batches = expr.obs[key].nunique()

    if n_batches < 2:
        logger.warning(
            "cluster.batch_key=%r has a single level; "
            "skipping batch correction.",
            key,
        )
        return None

    try:
        import harmonypy
    except (ImportError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            "Harmony batch correction requested but harmonypy is not installed. "
            "Install it with: pip install 'perturbseq-pipeline[harmony]'"
        ) from exc

    # --------------------------------------------------------------
    # Harmony requires dense PCA embeddings, but this is only
    # cells x PCs rather than cells x genes.
    # --------------------------------------------------------------
    embedding = np.asarray(
        expr.obsm["X_pca"],
        dtype=np.float64,
    )

    logger.info(
        "Running Harmony on embedding of shape %s across %d batches",
        embedding.shape,
        n_batches,
    )

    out = harmonypy.run_harmony(
        embedding,
        expr.obs,
        key,
    )

    corrected = np.asarray(
        out.result()
        if hasattr(out, "result")
        else out.Z_corr
    )

    # Orient defensively.
    if corrected.shape != embedding.shape:
        if corrected.T.shape == embedding.shape:
            corrected = corrected.T
        else:
            raise RuntimeError(
                "Harmony returned an embedding of shape "
                f"{corrected.shape}, which matches neither "
                f"{embedding.shape} nor its transpose."
            )

    # float32 is sufficient for neighbor search and halves the memory
    # requirement compared with Harmony's float64 output.
    expr.obsm["X_pca_harmony"] = corrected.astype(
        np.float32,
        copy=False,
    )

    del corrected
    del embedding
    del out

    gc.collect()

    logger.info(
        "Harmony batch correction on %r across %d batches",
        key,
        n_batches,
    )

    return "X_pca_harmony"


def cluster_summary(
    expr: ad.AnnData,
    lane_key: str = LANE_KEY,
) -> pd.DataFrame:
    """Cluster sizes and lane composition.

    A cluster dominated by one lane is a classic indication of batch effects,
    so the per-lane share is reported in addition to cluster size.
    """

    if CLUSTER_KEY not in expr.obs.columns:
        return pd.DataFrame()

    obs = expr.obs
    rows = []

    for cl, sub in obs.groupby(
        obs[CLUSTER_KEY].astype(str),
        observed=True,
    ):
        row = {
            "cluster": cl,
            "n_cells": len(sub),
            "pct_of_total": round(
                100 * len(sub) / expr.n_obs,
                2,
            ),
        }

        if "n_genes_by_counts" in sub.columns:
            row["median_genes"] = float(
                np.median(sub["n_genes_by_counts"])
            )

        if "pct_counts_mt" in sub.columns:
            row["median_pct_mt"] = round(
                float(np.median(sub["pct_counts_mt"])),
                2,
            )

        if (
            lane_key in sub.columns
            and obs[lane_key].nunique() > 1
        ):
            share = (
                sub[lane_key]
                .astype(str)
                .value_counts(normalize=True)
            )

            row["top_lane"] = share.index[0]
            row["top_lane_pct"] = round(
                100 * float(share.iloc[0]),
                1,
            )

        rows.append(row)

    out = pd.DataFrame(rows)

    return (
        out.sort_values(
            "n_cells",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def cluster_composition(
    expr: ad.AnnData,
    group_key: str,
) -> pd.DataFrame:
    """Contingency table of Leiden cluster against another obs column."""

    if (
        CLUSTER_KEY not in expr.obs.columns
        or group_key not in expr.obs.columns
    ):
        return pd.DataFrame()

    return (
        expr.obs
        .groupby(
            [CLUSTER_KEY, group_key],
            observed=True,
        )
        .size()
        .unstack(fill_value=0)
    )