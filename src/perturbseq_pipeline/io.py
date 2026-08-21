"""Data loading: 10x MTX directories and ``.h5ad`` files, plus sample metadata.

The pipeline has two entry points (see :mod:`perturbseq_pipeline.config`), and
both converge on the same pair of objects:

``expr``
    An :class:`~anndata.AnnData` containing gene expression.

``guides``
    An optional :class:`~anndata.AnnData` containing guide counts.

Large-dataset execution
-----------------------
For ordinary datasets the original behavior is preserved.

For million-cell H5AD objects, repeated copies of the complete expression
matrix can dominate memory usage. A 2–3 million-cell dataset may already occupy
hundreds of GB in memory, so creating independent copies for ``X``,
``layers['counts']`` and ``layers['lognorm']`` can trigger out-of-memory
termination even before downstream analysis begins.

Large-data mode therefore avoids unnecessary full-matrix copies when an
existing matrix/layer can safely be reused. This does not alter the biological
content of the input; it only changes ownership/reference semantics in memory.

Execution mode is selected automatically at >=1 million cells.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc

from .config import Config

logger = logging.getLogger(__name__)


LANE_KEY = "lane_id"
RAW_GUIDE_LABEL = "guide_id_raw"

LARGE_DATASET_N_CELLS = 1_000_000


@dataclass
class LoadedData:
    expr: ad.AnnData
    guides: Optional[ad.AnnData]
    guide_source: str
    lanes: Dict[str, str]

    @property
    def n_lanes(self) -> int:
        return len(self.lanes)


def _is_large_dataset(adata: ad.AnnData) -> bool:
    return adata.n_obs >= LARGE_DATASET_N_CELLS


def load_data(cfg: Config) -> LoadedData:
    """Load input and attach metadata."""

    mode = cfg.resolved_mode()

    logger.info(
        "Loading input in %r mode",
        mode,
    )

    data = (
        _load_mtx(cfg)
        if mode == "mtx"
        else _load_h5ad(cfg)
    )

    if mode == "h5ad":
        data.expr = apply_layer_choices(
            data.expr,
            cfg,
        )

    data.expr = attach_sample_metadata(
        data.expr,
        cfg,
        n_lanes=data.n_lanes,
    )

    if data.guides is not None:

        shared_cols = [
            col
            for col in data.expr.obs.columns
            if col not in data.guides.obs.columns
        ]

        for col in shared_cols:

            data.guides.obs[col] = (
                data.expr.obs[col]
                .reindex(
                    data.guides.obs_names
                )
            )

    logger.info(
        "Loaded %d cells x %d genes (%s guide features) from %d lane(s)",
        data.expr.n_obs,
        data.expr.n_vars,
        (
            data.guides.n_vars
            if data.guides is not None
            else "no"
        ),
        data.n_lanes,
    )

    return data