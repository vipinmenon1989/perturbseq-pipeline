"""``input.cell_id_format`` for MTX input: ``prefix`` names cells ``<lane>_<barcode>``
so a single-lane run is an exact row subset of the combined multi-lane run."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from make_synthetic import make_split_lane  # noqa: E402

from perturbseq_pipeline.config import Config  # noqa: E402
from perturbseq_pipeline.io import BARCODE_KEY, load_data  # noqa: E402


def _two_lane_config(tmp_path, cell_id_format: str) -> dict:
    lanes, guide_dirs = {}, {}
    for i, lane in enumerate(["L1", "L2"]):
        paths = make_split_lane(tmp_path / "split", lane, n_cells=120, seed=i)
        lanes[lane], guide_dirs[lane] = paths["gex"], paths["guides"]
    meta = tmp_path / "meta.csv"
    pd.DataFrame({"lane_id": list(lanes), "sample": ["S1", "S2"]}).to_csv(meta, index=False)
    return {
        "input": {"mtx_dirs": lanes, "guide_mtx_dirs": guide_dirs, "cell_id_format": cell_id_format},
        "metadata": {"file": str(meta)},
    }


def test_prefix_ids_single_lane_matches_combined_subset(tmp_path):
    base = _two_lane_config(tmp_path, "prefix")
    both = load_data(Config.from_dict(base))
    one_lane = {
        **base,
        "input": {
            **base["input"],
            "mtx_dirs": {"L1": base["input"]["mtx_dirs"]["L1"]},
            "guide_mtx_dirs": {"L1": base["input"]["guide_mtx_dirs"]["L1"]},
        },
    }
    one = load_data(Config.from_dict(one_lane))

    assert all(n.startswith(("L1_", "L2_")) for n in both.expr.obs_names)
    assert list(one.expr.obs_names) == [n for n in both.expr.obs_names if n.startswith("L1_")]
    assert both.guides.obs_names.equals(both.expr.obs_names)
    assert one.guides.obs_names.equals(one.expr.obs_names)
    assert BARCODE_KEY in both.expr.obs.columns
    # The stored barcode plus the lane reconstructs the new id.
    lane = both.expr.obs["lane_id"].astype(str)
    assert (lane + "_" + both.expr.obs[BARCODE_KEY].astype(str) == both.expr.obs_names).all()


def test_suffix_format_is_the_unchanged_default(tmp_path):
    base = _two_lane_config(tmp_path, "suffix")
    assert Config.from_dict({"input": {"mtx_dirs": {"a": "x"}}}).input.cell_id_format == "suffix"
    both = load_data(Config.from_dict(base))
    assert all(n.endswith(("-L1", "-L2")) for n in both.expr.obs_names)
    assert BARCODE_KEY not in both.expr.obs.columns


def test_unknown_cell_id_format_is_rejected():
    with pytest.raises(ValueError, match="cell_id_format"):
        Config.from_dict({"input": {"mtx_dirs": {"a": "x"}, "cell_id_format": "bogus"}}).validate()
