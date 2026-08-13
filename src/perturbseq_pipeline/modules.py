"""Co-functional modules and co-regulated gene programs (the "regulome" map).

Reimplements the network analysis of Chen et al. (Nature 2023,
`s41586-023-06733-x <https://www.nature.com/articles/s41586-023-06733-x>`_,
GSE216909): build a **perturbation x gene matrix of log2FC vs control**, then

* cluster the **gene** axis into **co-regulated programs** (Pearson correlation), and
* cluster the **perturbation** axis into **co-functional modules** (Spearman correlation),

and relate the two with a signed module x program strength matrix, plus a
TF-hub / module-module network.

Two deliberate simplifications vs the paper, both stated so results stay honest:

* The effect value is a pseudobulk **mean-difference log2FC** (de-logged group
  means, exactly the quantity :func:`perturbation.compare_groups` reports), not a
  per-gene Wilcoxon ``FindMarkers`` log2FC. It is the same quantity (log2FC) and
  far faster; gene *selection* still uses ``rank_genes_groups``.
* The number of programs/modules is a **chosen parameter** (``modules.n_programs``
  / ``modules.n_modules``, or an auto cut at ``cluster_distance_threshold``).
  Clusters are labelled numerically (``P1..``/``M1..``) — never given biological
  names here; annotate them from the per-program top genes / per-module TFs.

The stage returns ``None`` (skips) when too few perturbations or genes survive —
a single small lane cannot support a meaningful map; the full multi-lane run can.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import anndata as ad
import numpy as np
import pandas as pd
from scipy import sparse

from .cluster import CLUSTER_KEY, LOGNORM_LAYER
from .config import Config
from .guides import CLASS_TARGETING, OBS_CLASS, OBS_TARGET
from .perturbation import CONTROL_NTC, CONTROL_OTHER, control_masks

logger = logging.getLogger(__name__)

_PSEUDO = 1e-9  # keeps log2 finite at zero means, matching the perturbation test


@dataclass
class ModulesResults:
    """Everything the report/plots need about the module/program analysis."""

    #: Perturbation x gene log2FC-vs-control matrix (the input to everything else).
    effect_matrix: pd.DataFrame
    #: One row per gene: its program label (and the program's size).
    gene_programs: pd.DataFrame
    #: One row per perturbation: its module label, cell count, and #DE genes.
    modules: pd.DataFrame
    #: Signed module x program regulatory strength (mean program-gene log2FC).
    module_program: pd.DataFrame
    #: Program x cluster mean activity score (empty when scoring is off).
    program_activity: pd.DataFrame
    #: Directed TF->TF regulatory edges (|log2FC| > hub threshold).
    tf_edges: pd.DataFrame
    #: Per-TF hub size = number of DE genes it perturbs.
    hubs: pd.DataFrame
    #: Module x module connectivity (normalised TF-TF edge counts).
    module_connectivity: pd.DataFrame

    control: str = CONTROL_NTC
    n_programs: int = 0
    n_modules: int = 0
    program_correlation: str = "pearson"
    module_correlation: str = "spearman"
    linkage_method: str = "average"
    #: Ordered labels and the leaf order of each axis (for the clustered heatmap).
    program_labels: List[str] = field(default_factory=list)
    module_labels: List[str] = field(default_factory=list)
    gene_order: List[str] = field(default_factory=list)
    perturbation_order: List[str] = field(default_factory=list)
    #: label -> member genes / member TFs.
    program_genes: Dict[str, List[str]] = field(default_factory=dict)
    module_members: Dict[str, List[str]] = field(default_factory=dict)
    score_columns: List[str] = field(default_factory=list)
    note: str = ""


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


def select_perturbations(expr: ad.AnnData, cfg: Config) -> List[str]:
    """Target genes assigned to enough cells to estimate an effect profile."""
    klass = expr.obs[OBS_CLASS].astype(str).to_numpy()
    targets = expr.obs[OBS_TARGET].astype(str).to_numpy()
    mask = klass == CLASS_TARGETING
    counts = pd.Series(targets[mask]).value_counts()
    keep = counts[counts >= cfg.modules.min_cells_per_perturbation].index.tolist()
    return sorted(keep)


def select_genes(expr: ad.AnnData, cfg: Config) -> List[str]:
    """The downstream gene panel: union of top cluster markers (or HVGs)."""
    import scanpy as sc

    mcfg = cfg.modules
    if mcfg.gene_selection == "hvg":
        if "highly_variable" in expr.var:
            return expr.var_names[expr.var["highly_variable"].to_numpy()].tolist()
        return expr.var_names.tolist()

    key = mcfg.cluster_key
    if key not in expr.obs or expr.obs[key].nunique() < 2:
        logger.warning(
            "modules: '%s' has < 2 groups; falling back to highly variable genes "
            "for the gene panel.",
            key,
        )
        if "highly_variable" in expr.var:
            return expr.var_names[expr.var["highly_variable"].to_numpy()].tolist()
        return expr.var_names.tolist()

    # Cluster markers, ranked by log2FC, unioned across clusters (the paper's panel).
    adata = expr
    if adata.obs[key].dtype.name != "category":
        adata = expr.copy()
        adata.obs[key] = adata.obs[key].astype("category")
    sc.tl.rank_genes_groups(
        adata, key, method=mcfg.marker_method, n_genes=mcfg.n_marker_genes_per_cluster
    )
    df = sc.get.rank_genes_groups_df(adata, group=None)
    df = df[df["logfoldchanges"] > 0]
    genes: List[str] = []
    for _, sub in df.groupby("group"):
        top = sub.sort_values("logfoldchanges", ascending=False).head(
            mcfg.n_marker_genes_per_cluster
        )
        genes.extend(top["names"].tolist())
    # Deduplicate, preserving first-seen order.
    seen: Dict[str, None] = {}
    for g in genes:
        if g in expr.var_names:
            seen.setdefault(g, None)
    return list(seen)


# ---------------------------------------------------------------------------
# Effect matrix
# ---------------------------------------------------------------------------


def _dense_layer(expr: ad.AnnData, gene_idx: np.ndarray) -> np.ndarray:
    """Log-normalized expression for the selected genes as a dense cells x genes array."""
    layer = expr.layers[LOGNORM_LAYER] if LOGNORM_LAYER in expr.layers else expr.X
    sub = layer[:, gene_idx]
    if sparse.issparse(sub):
        sub = sub.toarray()
    return np.asarray(sub, dtype=np.float64)


def build_effect_matrix(
    expr: ad.AnnData, genes: List[str], targets: List[str], cfg: Config
) -> Tuple[pd.DataFrame, str, pd.DataFrame]:
    """Perturbation x gene log2FC vs control, the control used, and a DE mask.

    log2FC is computed on de-logged group means (like
    :func:`perturbation.compare_groups`): ``log2((mean_perturbed + eps) /
    (mean_control + eps))``. Control is NTC when available, else all
    other-target cells (leave-the-target-out), matching ``perturbation`` /
    ``enrichment`` semantics.

    The DE mask marks genes that are BOTH large (|log2FC| > hub_lfc_threshold)
    AND significant (per-gene Welch t-test on the log-normalized values,
    BH-corrected within the perturbation, FDR < de_fdr_alpha). The significance
    gate is what stops low-cell-count perturbations from looking like hubs on
    noise alone — hub sizes and TF-network edges use this mask, not raw |log2FC|.
    """
    from scipy.stats import t as _tdist

    from .perturbation import benjamini_hochberg

    base = control_masks(expr, cfg)
    control = cfg.modules.control
    if control == CONTROL_NTC and not base[CONTROL_NTC].any():
        logger.warning(
            "modules: no non-targeting cells; using 'other' (other-target cells) "
            "as the control instead of 'ntc'."
        )
        control = CONTROL_OTHER

    gene_idx = np.array([expr.var_names.get_loc(g) for g in genes])
    log = _dense_layer(expr, gene_idx)  # cells x genes, log-normalized
    lin = np.expm1(log)  # de-logged, for the fold change

    obs_targets = expr.obs[OBS_TARGET].astype(str).to_numpy()
    target_pos = {t: i for i, t in enumerate(targets)}
    rows, cols = [], []
    for cell, t in enumerate(obs_targets):
        j = target_pos.get(t)
        if j is not None:
            rows.append(j)
            cols.append(cell)
    ind = sparse.csr_matrix(
        (np.ones(len(rows)), (rows, cols)), shape=(len(targets), expr.n_obs)
    )
    n_p = np.asarray(ind.sum(axis=1)).ravel()  # cells per perturbation
    n_p_col = n_p[:, None]
    sum_lin = ind @ lin
    mean_perturbed = sum_lin / n_p_col  # de-logged, for log2FC
    # Log-space moments (for the t-test).
    s_log = ind @ log
    ss_log = ind @ (log * log)
    mean_p = s_log / n_p_col
    var_p = (ss_log - s_log * mean_p) / np.clip(n_p_col - 1, 1, None)

    if control == CONTROL_NTC:
        ntc = base[CONTROL_NTC]
        mean_control = lin[ntc].mean(axis=0)[None, :]  # broadcasts to all targets
        log_c = log[ntc]
        mean_c = log_c.mean(axis=0)[None, :]
        var_c = log_c.var(axis=0, ddof=1)[None, :]
        n_c = np.array([[max(int(ntc.sum()), 1)]], dtype=float)
    else:
        targeting = base[CONTROL_OTHER]  # class == targeting
        n_tot = int(targeting.sum())
        tot_lin = lin[targeting].sum(axis=0)
        mean_control = (tot_lin[None, :] - sum_lin) / np.clip(n_tot - n_p_col, 1, None)
        tot_log = log[targeting].sum(axis=0)
        tot_log2 = (log[targeting] ** 2).sum(axis=0)
        n_c = np.clip(n_tot - n_p_col, 1, None).astype(float)
        s_log_c = tot_log[None, :] - s_log
        mean_c = s_log_c / n_c
        var_c = (tot_log2[None, :] - ss_log - s_log_c * mean_c) / np.clip(n_c - 1, 1, None)

    log2fc = np.log2((mean_perturbed + _PSEUDO) / (mean_control + _PSEUDO))

    # Welch's t-test, per (perturbation, gene), on the log-normalized values.
    term_p = var_p / n_p_col
    term_c = var_c / n_c
    se2 = term_p + term_c
    with np.errstate(divide="ignore", invalid="ignore"):
        tstat = (mean_p - mean_c) / np.sqrt(se2)
        df = se2 ** 2 / (
            term_p ** 2 / np.clip(n_p_col - 1, 1, None)
            + term_c ** 2 / np.clip(n_c - 1, 1, None)
        )
        pvals = 2.0 * _tdist.sf(np.abs(tstat), np.clip(df, 1, None))
    pvals = np.where(np.isfinite(pvals) & (se2 > 0), pvals, 1.0)
    fdr = np.vstack([benjamini_hochberg(pvals[i]) for i in range(pvals.shape[0])])

    de = (np.abs(log2fc) > cfg.modules.hub_lfc_threshold) & (fdr < cfg.modules.de_fdr_alpha)
    effect = pd.DataFrame(log2fc, index=targets, columns=genes)
    de_mask = pd.DataFrame(de, index=targets, columns=genes)
    return effect, control, de_mask


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def cluster_axis(
    items: pd.DataFrame,
    correlation: str,
    linkage_method: str,
    k: Optional[int],
    threshold: Optional[float],
    prefix: str,
) -> Tuple[pd.Series, List[str], List[str]]:
    """Correlation hierarchical clustering of ``items`` (rows = things to group).

    Returns ``(labels, ordered_item_names, ordered_labels)`` where labels are
    ``<prefix>1..<prefix>K`` numbered along the dendrogram leaf order.
    """
    from scipy.cluster.hierarchy import fcluster, leaves_list, linkage
    from scipy.spatial.distance import squareform

    names = list(items.index)
    n = len(names)
    if n < 2:
        lab = pd.Series([f"{prefix}1"] * n, index=names)
        return lab, names, [f"{prefix}1"] if n else []

    corr = items.T.corr(method=correlation).to_numpy()
    dist = 1.0 - corr
    dist = np.nan_to_num(dist, nan=1.0, posinf=2.0, neginf=0.0)
    dist = (dist + dist.T) / 2.0
    np.fill_diagonal(dist, 0.0)
    dist[dist < 0] = 0.0
    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method=linkage_method)

    kk = None if k is None else max(2, min(k, n))
    if kk is not None:
        raw = fcluster(Z, kk, criterion="maxclust")
    else:
        raw = fcluster(Z, threshold, criterion="distance")

    order_idx = leaves_list(Z)
    ordered_names = [names[i] for i in order_idx]

    # Renumber clusters by first appearance along the leaf order (adjacent groups
    # get consecutive labels → block-diagonal heatmap).
    remap: Dict[int, str] = {}
    for i in order_idx:
        c = int(raw[i])
        if c not in remap:
            remap[c] = f"{prefix}{len(remap) + 1}"
    labels = pd.Series([remap[int(c)] for c in raw], index=names)
    ordered_labels = [remap[c] for c in dict.fromkeys(int(raw[i]) for i in order_idx)]
    return labels, ordered_names, ordered_labels


def module_program_strength(
    effect: pd.DataFrame,
    gene_program: pd.Series,
    perturbation_module: pd.Series,
    program_labels: List[str],
    module_labels: List[str],
) -> pd.DataFrame:
    """Signed strength: mean program-gene log2FC per perturbation, averaged in module."""
    out = pd.DataFrame(index=module_labels, columns=program_labels, dtype=float)
    for m in module_labels:
        perts = perturbation_module.index[perturbation_module == m]
        for p in program_labels:
            genes = gene_program.index[gene_program == p]
            block = effect.loc[perts, genes]
            out.loc[m, p] = float(np.nanmean(block.to_numpy())) if block.size else np.nan
    return out


# ---------------------------------------------------------------------------
# Networks
# ---------------------------------------------------------------------------


def tf_network(
    effect: pd.DataFrame,
    de_mask: pd.DataFrame,
    perturbation_module: pd.Series,
    n_cells: pd.Series,
    cfg: Config,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """TF->TF edges, per-TF hub size, and module-module connectivity.

    An edge TF_i -> gene_j exists when gene_j is a **significant** DE gene of
    perturbation i (``de_mask``: |log2FC| > threshold AND BH-FDR < alpha). Hub
    size of TF_i = number of such DE genes. Because the mask is significance-
    gated, a low-cell-count perturbation cannot inflate its hub size on noise.
    Module-module connectivity = TF-TF edges between the two modules /
    (size_i * size_j). ``n_cells`` is carried on the hub table so the reader can
    still see how many cells each perturbation had.
    """
    # Hub size: number of significant DE genes per perturbation.
    hub_counts = de_mask.sum(axis=1)
    hubs = pd.DataFrame(
        {
            "target_gene": hub_counts.index,
            "module": perturbation_module.reindex(hub_counts.index).to_numpy(),
            "n_cells": [int(n_cells.get(t, 0)) for t in hub_counts.index],
            "n_de_genes": hub_counts.to_numpy().astype(int),
        }
    ).sort_values("n_de_genes", ascending=False, ignore_index=True)

    # TF->TF edges: genes that are themselves perturbed TFs.
    tf_genes = [g for g in effect.columns if g in effect.index]
    edges = []
    for src in effect.index:
        for tgt in tf_genes:
            if src == tgt:
                continue
            if bool(de_mask.at[src, tgt]):
                val = effect.at[src, tgt]
                edges.append(
                    {
                        "source": src,
                        "target": tgt,
                        "log2fc": float(val),
                        "sign": "positive" if val > 0 else "negative",
                        "source_module": perturbation_module.get(src, ""),
                        "target_module": perturbation_module.get(tgt, ""),
                    }
                )
    tf_edges = pd.DataFrame(
        edges, columns=["source", "target", "log2fc", "sign", "source_module", "target_module"]
    )

    # Module-module connectivity, normalised by module sizes.
    labels = sorted(perturbation_module.unique(), key=lambda s: (len(s), s))
    sizes = perturbation_module.value_counts()
    conn = pd.DataFrame(0.0, index=labels, columns=labels)
    if not tf_edges.empty:
        for _, e in tf_edges.iterrows():
            a, b = e["source_module"], e["target_module"]
            if a in labels and b in labels:
                conn.loc[a, b] += 1.0
    for a in labels:
        for b in labels:
            denom = float(sizes.get(a, 1) * sizes.get(b, 1))
            conn.loc[a, b] = conn.loc[a, b] / denom if denom else 0.0
    return tf_edges, hubs, conn


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def compute_modules(expr: ad.AnnData, cfg: Config) -> Optional[ModulesResults]:
    """Run the full module/program analysis, or return ``None`` if underpowered."""
    mcfg = cfg.modules

    targets = select_perturbations(expr, cfg)
    if len(targets) < mcfg.min_perturbations:
        logger.info(
            "modules: only %d perturbation(s) with >= %d cells (need %d) — skipping "
            "the module/program analysis (run more lanes for a meaningful map).",
            len(targets), mcfg.min_cells_per_perturbation, mcfg.min_perturbations,
        )
        return None

    genes = select_genes(expr, cfg)
    if len(genes) < mcfg.min_genes:
        logger.info(
            "modules: only %d gene(s) selected (need %d) — skipping.",
            len(genes), mcfg.min_genes,
        )
        return None

    effect, control, de_mask = build_effect_matrix(expr, genes, targets, cfg)
    n_cells = pd.Series(expr.obs[OBS_TARGET].astype(str).value_counts())
    logger.info(
        "modules: effect matrix %d perturbations x %d genes (log2FC vs %s); "
        "median %d significant DE genes/perturbation",
        effect.shape[0], effect.shape[1], control, int(de_mask.sum(axis=1).median()),
    )

    # Programs (genes) and modules (perturbations).
    gene_program, gene_order, program_labels = cluster_axis(
        effect.T, mcfg.program_correlation, mcfg.linkage_method,
        mcfg.n_programs, mcfg.cluster_distance_threshold, prefix="P",
    )
    pert_module, pert_order, module_labels = cluster_axis(
        effect, mcfg.module_correlation, mcfg.linkage_method,
        mcfg.n_modules, mcfg.cluster_distance_threshold, prefix="M",
    )
    logger.info(
        "modules: %d gene program(s), %d co-functional module(s)",
        len(program_labels), len(module_labels),
    )

    mp = module_program_strength(
        effect, gene_program, pert_module, program_labels, module_labels
    )
    tf_edges, hubs, conn = tf_network(effect, de_mask, pert_module, n_cells, cfg)

    # Per-cell program scores + program activity by cluster.
    score_columns: List[str] = []
    program_activity = pd.DataFrame()
    program_genes = {
        p: gene_program.index[gene_program == p].tolist() for p in program_labels
    }
    if mcfg.score_programs:
        import scanpy as sc

        for p in program_labels:
            col = f"program_{p}_score"
            sc.tl.score_genes(expr, program_genes[p], score_name=col, ctrl_size=50)
            score_columns.append(col)
        key = mcfg.cluster_key
        if key in expr.obs and score_columns:
            act = expr.obs.groupby(key, observed=True)[score_columns].mean()
            act.columns = program_labels  # P1..Pk instead of program_P1_score
            program_activity = act.T  # programs x clusters
            program_activity.index.name = "program"

    modules_tbl = pd.DataFrame(
        {
            "target_gene": pert_module.index,
            "module": pert_module.to_numpy(),
            "n_cells": [int(n_cells.get(t, 0)) for t in pert_module.index],
            "n_de_genes": [int(de_mask.loc[t].sum()) for t in pert_module.index],
        }
    ).sort_values(["module", "n_de_genes"], ascending=[True, False], ignore_index=True)

    gene_sizes = gene_program.value_counts()
    programs_tbl = pd.DataFrame(
        {
            "gene": gene_program.index,
            "program": gene_program.to_numpy(),
            "program_size": [int(gene_sizes.get(p, 0)) for p in gene_program.to_numpy()],
        }
    ).sort_values("program", ignore_index=True)

    module_members = {
        m: pert_module.index[pert_module == m].tolist() for m in module_labels
    }

    return ModulesResults(
        effect_matrix=effect,
        gene_programs=programs_tbl,
        modules=modules_tbl,
        module_program=mp,
        program_activity=program_activity,
        tf_edges=tf_edges,
        hubs=hubs,
        module_connectivity=conn,
        control=control,
        n_programs=len(program_labels),
        n_modules=len(module_labels),
        program_correlation=mcfg.program_correlation,
        module_correlation=mcfg.module_correlation,
        linkage_method=mcfg.linkage_method,
        program_labels=program_labels,
        module_labels=module_labels,
        gene_order=gene_order,
        perturbation_order=pert_order,
        program_genes=program_genes,
        module_members=module_members,
        score_columns=score_columns,
    )
