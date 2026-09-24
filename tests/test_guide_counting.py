"""Guide counting: design-table parser, streaming FASTQ read parser and the
per-sample UMI counter, on synthetic reads with known ground truth."""

from __future__ import annotations

import gzip
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from make_synthetic_guides import SCAFFOLDS, TSO, guide_config, make_dataset  # noqa: E402

from perturbseq_pipeline.config import Config  # noqa: E402
from perturbseq_pipeline.guide_counting import (  # noqa: E402
    FEATURE_SEP,
    GuideCountJob,
    GuideReadSpec,
    build_protospacer_index,
    count_fastq_file,
    count_guides,
    expand_design_by_scaffold,
    find_guide_fastqs,
    read_guide_counts,
    write_guide_counts,
)
from perturbseq_pipeline.guide_design import load_guide_design  # noqa: E402


@pytest.fixture(scope="session")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("guide_counting_synthetic")
    return make_dataset(out, samples=("W1",), n_cells=320)


def _design_cfg(path, **design_overrides) -> Config:
    design = {"path": str(path)}
    design.update(design_overrides)
    return Config.from_dict({"guides": {"design": design}})


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def test_guide_counting_config_defaults_and_validation():
    cfg = Config()
    assert cfg.guides.design.path is None
    assert cfg.guides.fastq.scaffolds == {"A": "GTTTAAGAGCTA", "C": "GTTTCAGAGCTA"}
    assert cfg.guides.fastq.max_mismatches == 0
    Config.from_dict({"input": {"h5ad": "x.h5ad"}}).validate()
    with pytest.raises(ValueError, match="max_mismatches"):
        Config.from_dict({"input": {"h5ad": "x.h5ad"}, "guides": {"fastq": {"max_mismatches": 2}}}).validate()
    with pytest.raises(ValueError, match="nucleotide"):
        Config.from_dict({"input": {"h5ad": "x.h5ad"}, "guides": {"fastq": {"scaffolds": {"A": "hello"}}}}).validate()
    with pytest.raises(ValueError, match="Unknown config key"):
        Config.from_dict({"guides": {"fastq": {"not_a_key": 1}}})


# ---------------------------------------------------------------------------
# Design table
# ---------------------------------------------------------------------------


def test_guide_design_parser_keeps_all_designed_guides(dataset):
    # The workbook labels controls "NO-TARGET", which guides.ntc_patterns does not
    # cover; guides.design.control_patterns overrides the patterns for the table.
    design = load_guide_design(_design_cfg(dataset["design_path"], control_patterns=[r"^no[-_ ]?target"]))
    truth = dataset["design"]
    assert len(design) == len(truth) == 14
    assert design["guide_id"].is_unique
    assert design["is_control"].sum() == 5  # 4 sequenced + 1 unsequenced NO-TARGET
    assert (design.loc[design["is_control"], "target"] == "control").all()
    assert set(design.loc[~design["is_control"], "target"]) == {"GENEA", "GENEB", "GENEC", "GENED"}
    assert design["protospacer"].tolist() == truth["seq"].tolist()
    assert "on_target_efficacy_score" in design.columns and "beginswithg" in design.columns
    assert (design["scaffold"] == "unknown").all()  # no scaffold column in the workbook
    assert design["guide_id"].iloc[0] == "GENEA_1" and design["guide_id"].iloc[8] == "NO-TARGET_1"
    # without the override the default guides.ntc_patterns decide
    plain = load_guide_design(_design_cfg(dataset["design_path"]))
    assert plain["is_control"].sum() == 0 and len(plain) == 14


def test_guide_design_explicit_columns_and_errors(tmp_path):
    p = tmp_path / "d.csv"
    pd.DataFrame({"sgRNA": ["ACGT" * 5, "TTTT" * 5], "Target": ["G1", "ntc"], "scaffold": ["A", "C"]}).to_csv(p, index=False)
    d = load_guide_design(_design_cfg(p, protospacer_column="sgRNA", target_column="Target"))
    assert d["scaffold"].tolist() == ["A", "C"] and d["is_control"].tolist() == [False, True]
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"seq": ["ACGTN", "hello"], "gene": ["a", "b"]}).to_csv(bad, index=False)
    with pytest.raises(ValueError, match="not nucleotide"):
        load_guide_design(_design_cfg(bad))
    with pytest.raises(ValueError, match="guides.design.path is not set"):
        load_guide_design(Config())


# ---------------------------------------------------------------------------
# FASTQ read parser
# ---------------------------------------------------------------------------


def _write_fastq(path: Path, seqs):
    with gzip.open(path, "wt") as fh:
        for i, s in enumerate(seqs):
            fh.write(f"@r{i}\n{s}\n+\n{'F' * len(s)}\n")


def test_guide_parser_handles_each_read_class(tmp_path):
    cfg = Config()
    spec = GuideReadSpec.from_config(cfg.guides.fastq)
    g1 = "AAACCCGGGTTTACGTACGA"  # guide 0 (scaffold A by construction)
    g2 = "TTGACCATGGACCTAGGCAT"  # guide 1 (scaffold C)
    exact, mm = build_protospacer_index([g1, g2], 0)
    bc_ok = "ACGTACGTACGTACGT"
    bc_bad = "GGGGGGGGGGGGGGGG"
    umi1, umi2, umi_n = "AAAAAAAAAAAA", "CCCCCCCCCCCC", "AAAAAAAAAAAN"
    A, C = SCAFFOLDS["A"], SCAFFOLDS["C"]
    reads = [
        f"{bc_ok}{umi1}{TSO}GG{g1}{A}",      # valid guide 0, scaffold A
        f"{bc_ok}{umi1}{TSO}GG{g1}{A}",      # duplicate UMI -> same molecule
        f"{bc_ok}{umi2}{TSO}GGG{g1}{A}",     # different UMI -> second molecule (3 Gs)
        f"{bc_ok}{umi1}{TSO}{g2}{C}",        # guide 1, scaffold C, zero Gs
        f"{bc_ok}{umi1}{TSO}GG{'ACGT' * 5}{A}",  # unknown guide
        f"{bc_bad}{umi1}{TSO}GG{g1}{A}",     # invalid barcode -> counted, not stored
        f"{bc_ok}{umi_n}{TSO}GG{g2}{C}",     # bad UMI
        "ACGT" * 37,                         # no anchor
        f"{bc_ok}{umi2}{TSO}GG{g2}A{C}",     # 1-nt insertion before the anchor -> shifted exact match
    ]
    reads = [r[:151].ljust(60, "A") for r in reads]
    p = tmp_path / "t_R1_.fastq.gz"
    _write_fastq(p, reads)
    res = count_fastq_file(str(p), spec, exact, mm, {bc_ok.encode(): 0}, 2, decompressor="python")
    st = res["stats"]
    assert st["reads_total"] == 9
    assert st["reads_with_scaffold_anchor"] == 8
    assert st["reads_spacer_matched"] == 7 and st["reads_spacer_unmatched"] == 1
    assert st["reads_spacer_matched_via_shift"] == 1
    assert st["reads_matched_barcode_not_in_gex"] == 1
    assert st["reads_invalid_umi"] == 1
    assert st["reads_scaffold_A"] == 5 and st["reads_scaffold_C"] == 3
    assert st["reads_with_tso"] == 8
    # unique (cell, guide, UMI): g1/umi1, g1/umi2, g2/umi1, g2/umi2(shift) = 4
    assert res["codes"].size == 4
    assert res["guide_reads"].tolist() == [4, 3]
    assert res["guide_scaffold_reads"].tolist() == [[4, 0], [0, 3]]
    assert list(res["unmatched"].values()) == [1]

    # position_shift = 0 disables the positional fallback
    spec0 = GuideReadSpec.from_config(Config.from_dict({"guides": {"fastq": {"position_shift": 0}}}).guides.fastq)
    res0 = count_fastq_file(str(p), spec0, exact, mm, {bc_ok.encode(): 0}, 2, decompressor="python")
    assert res0["stats"]["reads_spacer_matched"] == 6 and res0["codes"].size == 3

    # explicit 1-mismatch mode
    exact1, mm1 = build_protospacer_index([g1, g2], 1)
    assert g1[:-1].encode() + b"T" in mm1 if g1[-1] != "T" else True
    _write_fastq(p, [f"{bc_ok}{umi1}{TSO}GG{g1[:-1]}{'T' if g1[-1] != 'T' else 'A'}{A}"[:151]])
    res1 = count_fastq_file(str(p), spec0, exact1, mm1, {bc_ok.encode(): 0}, 2, decompressor="python")
    assert res1["stats"]["reads_spacer_matched_via_mismatch"] == 1


# ---------------------------------------------------------------------------
# Per-sample counter
# ---------------------------------------------------------------------------


def test_guide_counter_reproduces_synthetic_truth_and_writes_mtx(dataset, tmp_path):
    info = dataset["samples"]["W1"]
    cfg = Config.from_dict(guide_config(dataset))
    design = load_guide_design(cfg)
    files = find_guide_fastqs(info["fastq_dir"], cfg.guides.fastq.read_pattern)
    assert files == sorted(str(f) for f in info["fastqs"])
    bare = [b.split("-")[0] for b in info["barcodes"]]
    job = GuideCountJob("W1", files, bare)
    res = count_guides([job], design, cfg, n_workers=2)["W1"]
    assert res.counts.shape == (info["n_cells"], len(design))
    seq_to_col = {s: i for i, s in enumerate(design["protospacer"])}
    dense = res.counts.toarray()
    for i, bc in enumerate(bare):
        expected = np.zeros(len(design), dtype=int)
        for spacer, n in info["truth_umis"][bc].items():
            expected[seq_to_col[spacer]] = n
        assert dense[i].tolist() == expected.tolist(), f"cell {bc}"
    assert res.stats["reads_total"] == info["n_reads"]
    assert res.stats["reads_matched_barcode_not_in_gex"] == 300
    assert res.stats["n_files"] == 2
    # designed-but-unsequenced guides keep zero columns
    assert (dense[:, -2:] == 0).all()
    assert res.stats["guides_detected_any_umi"] == len(design) - 2
    paths = write_guide_counts(res, design, tmp_path / "gc")
    mat, bcs, gids = read_guide_counts(tmp_path / "gc", "W1")
    assert mat.shape == res.counts.shape and (mat != res.counts).nnz == 0
    assert bcs == bare and gids == design["guide_id"].tolist()
    summary = pd.read_csv(paths["guide_summary"], sep="\t")
    assert len(summary) == len(design)
    assert summary["umis_in_cells"].tolist() == dense.sum(axis=0).tolist()


def test_guide_counter_scaffold_specific_features(dataset, tmp_path):
    """Features = designed spacer x scaffold class; UMIs land in the (spacer, true scaffold) column only."""
    info = dataset["samples"]["W1"]
    cfg = Config.from_dict(guide_config(dataset, scaffold_specific_features=True))
    design = load_guide_design(cfg)
    bare = [b.split("-")[0] for b in info["barcodes"]]
    job = GuideCountJob("W1", [str(f) for f in info["fastqs"]], bare)
    res = count_guides([job], design, cfg, n_workers=2)["W1"]
    names = list(cfg.guides.fastq.scaffolds)
    assert res.counts.shape == (info["n_cells"], 2 * len(design))
    assert res.feature_design is not None and len(res.feature_design) == 2 * len(design)
    fd = res.feature_design
    assert list(fd["guide_id"]) == [f"{g}{FEATURE_SEP}{c}" for g in design["guide_id"] for c in names]
    assert list(fd["guide_id"]) == res.guide_ids
    col = {(s, c): i for i, (s, c) in enumerate(zip(fd["protospacer"], fd["scaffold"]))}
    truth_scaf = dataset["design"].set_index("seq")["_scaffold_truth"]
    dense = res.counts.toarray()
    for i, bc in enumerate(bare):
        expected = np.zeros(dense.shape[1], dtype=int)
        for spacer, n in info["truth_umis"][bc].items():
            expected[col[(spacer, truth_scaf[spacer])]] = n
        assert dense[i].tolist() == expected.tolist(), f"cell {bc}"
    # collapsing the two scaffold columns reproduces the scaffold-agnostic count matrix
    res0 = count_guides([job], design, Config.from_dict(guide_config(dataset)), n_workers=2)["W1"]
    collapsed = dense.reshape(dense.shape[0], len(design), len(names)).sum(axis=2)
    assert (collapsed == res0.counts.toarray()).all()
    assert res.stats["features"] == 2 * len(design) and res.stats["scaffold_specific_features"] is True
    paths = write_guide_counts(res, design, tmp_path / "gc_split")
    mat, bcs, gids = read_guide_counts(tmp_path / "gc_split", "W1")
    assert mat.shape == res.counts.shape and gids == res.guide_ids
    summary = pd.read_csv(paths["guide_summary"], sep="\t")
    assert len(summary) == 2 * len(design) and {"design_guide_id", "scaffold", "designed_slot"} <= set(summary.columns)
    # expansion helper keeps the design's own scaffold declaration when it has one
    d = design.copy()
    d["scaffold"] = ["A"] + ["unknown"] * (len(d) - 1)
    ex = expand_design_by_scaffold(d, names)
    assert ex["designed_slot"].tolist()[:2] == [True, False]
