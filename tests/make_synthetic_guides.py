"""Synthetic guide FASTQs and design workbook for the guide-counting tests.

Writes, per sample:

* two gzipped guide "R1" FASTQ files with the 10x 5' feature-barcode read
  structure ``[16 bc][12 UMI][TSO][0-4 G][20 spacer][scaffold ...]``.

The design workbook mimics ``design_out_v2.xlsx`` (columns ``gene``, ``seq``,
``On-Target Efficacy Score``, ``BeginsWithG``) and includes ``NO-TARGET``
controls plus two guides that are designed but never sequenced.

Ground truth returned alongside the files: the cell barcodes, the expected
guide UMI counts per cell and the total number of reads written.
"""

from __future__ import annotations

import gzip
import random
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

TSO = "TTTCTTATATGGG"
SCAFFOLDS = {
    "A": "GTTTAAGAGCTAAGCTGGAAACAGCATAGCAAGTTTAAATAAGGCTAGTCCGTTATCAACTTGAGATCGGAAGAGCACACGTCTGAAC",
    "C": "GTTTCAGAGCTAAGCACAAGAGTGCATAGCAAGTTGAAATAAGGCTAGTCCGTTATCAACTTGAGATCGGAAGAGCACACGTCTGAAC",
}
TARGETS = ["GENEA", "GENEB", "GENEC", "GENED"]


def _rand_seq(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("ACGT") for _ in range(n))


def make_design(path: Path, seed: int = 0) -> pd.DataFrame:
    """Design workbook: 4 targets x (1 A + 1 C) + 4 NO-TARGET (2 A, 2 C) + 2 unsequenced."""
    rng = random.Random(seed)
    rows = []
    seen = set()

    def spacer():
        while True:
            s = _rand_seq(rng, 20)
            if s not in seen and "GTTT" not in s:
                seen.add(s)
                return s

    scaffold_of = {}
    for t in TARGETS:
        for scaf in ("A", "C"):
            s = spacer()
            rows.append({"gene": t, "seq": s, "On-Target Efficacy Score": round(rng.uniform(0.2, 1.2), 3), "BeginsWithG": s.startswith("G")})
            scaffold_of[s] = scaf
    for i in range(4):
        s = spacer()
        rows.append({"gene": "NO-TARGET", "seq": s, "On-Target Efficacy Score": float("nan"), "BeginsWithG": s.startswith("G")})
        scaffold_of[s] = "A" if i % 2 == 0 else "C"
    for t in ("GENEA", "NO-TARGET"):  # designed but never observed
        s = spacer()
        rows.append({"gene": t, "seq": s, "On-Target Efficacy Score": 0.1, "BeginsWithG": s.startswith("G")})
        scaffold_of[s] = "unsequenced"
    df = pd.DataFrame(rows)
    df.to_excel(path, index=False)
    df["_scaffold_truth"] = df["seq"].map(scaffold_of)
    return df


def make_sample(
    outdir: Path,
    sample_id: str,
    design: pd.DataFrame,
    n_cells: int = 320,
    n_multiplet: int = 30,
    n_noguide: int = 15,
    seed: int = 0,
) -> Dict[str, object]:
    """Write one sample's two guide FASTQ lanes; return paths and truth."""
    rng = np.random.default_rng(seed)
    prng = random.Random(seed)
    barcodes = [f"{_rand_seq(prng, 16)}-1" for _ in range(n_cells)]
    assert len(set(barcodes)) == n_cells

    d = design[design["_scaffold_truth"] != "unsequenced"].reset_index(drop=True)
    A = d[d["_scaffold_truth"] == "A"]["seq"].tolist()
    C = d[d["_scaffold_truth"] == "C"]["seq"].tolist()
    spacer_scaf = dict(zip(d["seq"], d["_scaffold_truth"]))
    truth_umis: Dict[str, Dict[str, int]] = {}
    order = rng.permutation(n_cells)
    multiplet_cells = set(order[:n_multiplet].tolist())
    noguide_cells = set(order[n_multiplet:n_multiplet + n_noguide].tolist())
    for i, bc in enumerate(barcodes):
        bare = bc.split("-")[0]
        guides: Dict[str, int] = {}
        if i in noguide_cells:
            # a single sub-threshold UMI on one guide for some of them
            if prng.random() < 0.5:
                guides[prng.choice(A)] = 1
        else:
            a = prng.choice(A)
            c = prng.choice(C)
            guides[a] = int(rng.integers(5, 40))
            guides[c] = int(rng.integers(5, 40))
            if i in multiplet_cells:
                extra = prng.choice([g for g in A if g != a])
                guides[extra] = int(rng.integers(4, 30))
        truth_umis[bare] = guides

    # FASTQ reads
    reads: List[Tuple[str, str]] = []
    unknown_spacer = "ACGTACGTACGTACGTACGT"
    for bc, guides in truth_umis.items():
        for spacer, n_umi in guides.items():
            scaf = SCAFFOLDS[spacer_scaf[spacer]]
            for _ in range(n_umi):
                umi = _rand_seq(prng, 12)
                n_reads = 1 + int(rng.poisson(1.5))
                for _ in range(n_reads):  # PCR duplicates -> same UMI
                    gs = "G" * prng.choice([0, 1, 2, 2, 2, 3, 4])
                    reads.append((f"{bc}{umi}{TSO}{gs}{spacer}{scaf}"[:151], bc))
    # noise: invalid barcodes, unknown spacers, reads without an anchor
    for _ in range(300):
        bc = _rand_seq(prng, 16)
        reads.append((f"{bc}{_rand_seq(prng, 12)}{TSO}GG{prng.choice(A)}{SCAFFOLDS['A']}"[:151], "invalid"))
    for _ in range(200):
        bc = barcodes[prng.randrange(n_cells)].split("-")[0]
        reads.append((f"{bc}{_rand_seq(prng, 12)}{TSO}GG{unknown_spacer}{SCAFFOLDS['C']}"[:151], "unknown"))
    for _ in range(100):
        reads.append((_rand_seq(prng, 151), "noanchor"))
    prng.shuffle(reads)
    fq_dir = outdir / f"{sample_id}F" / "fastq"
    fq_dir.mkdir(parents=True, exist_ok=True)
    half = len(reads) // 2
    files = []
    for lane, chunk in (("L001", reads[:half]), ("L002", reads[half:])):
        p = fq_dir / f"{sample_id}F_S1_{lane}_R1_001.fastq.gz"
        with gzip.open(p, "wt") as fh:
            for k, (seq, _) in enumerate(chunk):
                fh.write(f"@synthetic:{sample_id}:{lane}:{k} 1:N:0:ACGT\n{seq}\n+\n{'F' * len(seq)}\n")
        files.append(p)
    return {
        "sample_id": sample_id,
        "fastq_dir": fq_dir,
        "fastqs": files,
        "barcodes": barcodes,
        "n_cells": n_cells,
        "truth_umis": truth_umis,
        "n_reads": len(reads),
    }


def make_dataset(outdir: Path, samples: Tuple[str, ...] = ("W1",), n_cells: int = 320) -> Dict[str, object]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    design_path = outdir / "design.xlsx"
    design = make_design(design_path, seed=1)
    out = {"design_path": design_path, "design": design, "samples": {}}
    for i, s in enumerate(samples):
        out["samples"][s] = make_sample(outdir, s, design, n_cells=n_cells, seed=10 + i)
    return out


def guide_config(dataset: Dict[str, object], **fastq_overrides) -> Dict[str, object]:
    """Config dict for :func:`perturbseq_pipeline.config.Config.from_dict`."""
    fastq = {"read_pattern": "*_R1_*.fastq.gz", "n_workers": 1}
    fastq.update(fastq_overrides)
    design = {"path": str(dataset["design_path"]), "control_patterns": [r"^no[-_ ]?target"]}
    return {"guides": {"design": design, "fastq": fastq}}
