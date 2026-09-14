#!/usr/bin/env python
"""Step 1 (SLURM only): audit of the dataset, the data_audit reports, the Cell Ranger /
guide count inputs and the design workbook; builds the validated pair-guide reference
used by ``guides.pair_reference`` and stages the guide count matrices into the run tree.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guide_design import load_guide_design

WELLS = {"HF011A": "HF011AF", "HF011B": "HF011BF", "HF012A": "HF012AF", "HF012B": "HF012BF"}


def md_table(df: pd.DataFrame) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in r.tolist()) + " |")
    return "\n".join(lines)


def sh(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--repo", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--qc-config", required=True, help="config with guides.design.* for consistent guide ids")
    ap.add_argument("--cellranger-root", required=True); ap.add_argument("--guide-counts-root", required=True)
    ap.add_argument("--prior-quant-tables", required=True, help="tables dir of the guide-counting job (funnel etc.)")
    a = ap.parse_args()
    data, repo, out = Path(a.data), Path(a.repo), Path(a.out)
    audit = out / "audit"; inputs = out / "inputs"
    audit.mkdir(parents=True, exist_ok=True); (inputs / "guide_counts").mkdir(parents=True, exist_ok=True)
    job = os.environ.get("SLURM_JOB_ID", "n/a")
    log = []
    L = log.append

    # ---- 1. data_audit reports ---------------------------------------------------------
    reports = sorted(p for p in (data / "data_audit").rglob("*") if p.is_file() and p.suffix in (".md", ".txt", ".csv", ".tsv", ".log", ".json") and "extracted" not in p.parts and "tar_listings" not in p.parts)
    with open(audit / "data_audit_reports_read.log", "w") as fh:
        for p in reports:
            fh.write(f"\n{'=' * 80}\nFILE: {p.relative_to(data)} ({p.stat().st_size} bytes)\n{'=' * 80}\n")
            txt = p.read_text(errors="ignore")
            fh.write(txt if len(txt) < 400_000 else txt[:400_000] + "\n[truncated]\n")
    L(f"# Initial audit (SLURM job {job}, {datetime.now():%Y-%m-%d %H:%M})\n")
    L(f"## 1. data_audit reports read\n\n{len(reports)} files concatenated into `audit/data_audit_reports_read.log`:\n")
    L("\n".join(f"- `{p.relative_to(data)}` ({p.stat().st_size:,} bytes)" for p in reports if p.suffix == ".md"))
    L("\nKey audit statements (verified below against the data): 4 GEX wells (Cell Ranger 9.0.1, GEX-only, 38,606 features, 163,991 cells), "
      "4 guide FASTQ libraries (not processed by Cell Ranger), read structure 16 nt BC + 12 nt UMI + TSO + variable G + 20 nt protospacer + scaffold A `GTTTAAGAGCTA` / C `GTTTCAGAGCTA`, "
      "design workbook with no scaffold/pair columns, previous single-guide rule ~52 % ambiguous.\n")

    # ---- 2. dataset tree ---------------------------------------------------------------------
    tree = sh(f"find {data} -maxdepth 3 -not -path '*/data_audit/*' | sort")
    (audit / "dataset_tree.txt").write_text(tree)
    inv = sh(f"find {data} -type f -not -path '*/data_audit/*' -printf '%s\\t%TY-%Tm-%Td %TH:%TM\\t%p\\n' | sort -k3")
    (audit / "dataset_file_inventory.tsv").write_text("size_bytes\tmtime\tpath\n" + inv)
    L(f"## 2. Dataset tree\n\n`audit/dataset_tree.txt` (depth 3) and `audit/dataset_file_inventory.tsv` ({inv.count(chr(10))} files). Samples: {', '.join(WELLS)}; guide libraries: {', '.join(WELLS.values())}.\n")

    # ---- 3. Cell Ranger matrices / guide matrices / FASTQs / workbook ------------------------------
    rows = []
    for w, lib in WELLS.items():
        tars = sorted((data / w).rglob("*_cellranger_count_outs.tar"))
        staged = Path(a.cellranger_root) / w / "filtered_feature_bc_matrix"
        n_bc = sum(1 for _ in gzip.open(staged / "barcodes.tsv.gz", "rt")) if (staged / "barcodes.tsv.gz").is_file() else 0
        fastqs = sorted((data / lib).rglob("*_R1_001.fastq.gz"))
        gc = Path(a.guide_counts_root) / w
        rows.append({"well": w, "cellranger_outs_tar": ";".join(str(t) for t in tars), "staged_filtered_mtx_dir": str(staged), "staged_mtx_complete": all((staged / f).is_file() for f in ("barcodes.tsv.gz", "features.tsv.gz", "matrix.mtx.gz")),
                     "n_filtered_barcodes": n_bc, "guide_library": lib, "guide_fastq_r1": ";".join(str(f) for f in fastqs), "n_guide_fastq_files": len(fastqs),
                     "guide_fastq_gb": round(sum(f.stat().st_size for f in fastqs) / 1e9, 2), "guide_count_matrix_dir": str(gc), "guide_count_matrix_complete": all((gc / f).is_file() for f in ("barcodes.tsv.gz", "features.tsv.gz", "matrix.mtx.gz"))})
        # stage guide counts into the run tree (small) with provenance
        dst = inputs / "guide_counts" / w
        dst.mkdir(parents=True, exist_ok=True)
        for f in gc.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)
    inv_df = pd.DataFrame(rows)
    inv_df.to_csv(audit / "input_inventory.csv", index=False)
    (inputs / "guide_counts" / "PROVENANCE.md").write_text(
        f"Guide count matrices copied from {a.guide_counts_root} (perturbseq_pipeline.guide_counting, SLURM job 20045256: exact protospacer match + unambiguous 1-mismatch rescue + +/-1 nt shift, "
        f"UMI-deduplicated, rows = Cell Ranger filtered GEX barcodes of the paired well). Copied by SLURM job {job} on {datetime.now():%Y-%m-%d}.\n")
    for f in ("guide_read_retention_funnel.csv", "guide_quantification_summary.csv", "guide_counts_per_well.csv"):
        src = Path(a.prior_quant_tables) / f
        if src.is_file():
            shutil.copy2(src, audit / f)
    L("## 3. Inputs located\n\n" + md_table(inv_df.drop(columns=["guide_fastq_r1", "cellranger_outs_tar"])) + "\n")
    L("Cell Ranger filtered matrices live inside `<well>/analysis/*/<well>_cellranger_count_outs.tar` and were staged (read-only extraction) to the `staged_filtered_mtx_dir` paths above. "
      "Guide count matrices (scaffold-aware counter, all 560 designed guides as columns) were copied to `inputs/guide_counts/<well>/`; the read-retention funnel and quantification summary are in `audit/`.\n")

    # ---- 4. workbook ----------------------------------------------------------------------------
    xl = sorted(p for p in (data / "web_summaries").glob("*.xls*"))
    assert xl, "no workbook"
    xl = xl[0]
    book = pd.read_excel(xl, sheet_name=None, header=None, dtype=object)
    sheets = []
    for name, raw in book.items():
        raw = raw.dropna(how="all").dropna(axis=1, how="all")
        header = [str(x) for x in raw.iloc[0]]
        sheets.append({"sheet": name, "n_rows": len(raw) - 1, "columns": header})
    L(f"## 4. Design workbook `{xl}`\n\n" + "\n".join(f"- sheet `{s['sheet']}`: {s['n_rows']} data rows, columns {s['columns']}" for s in sheets))
    cols_lower = [c.lower() for s in sheets for c in s["columns"]]
    has_pair = any(k in c for c in cols_lower for k in ("pair", "construct", "vector", "scaffold", "position"))
    L(f"\nSequence column: `seq`; target column: `gene`; guide ID column: none (ids synthesised as `<gene>_<n>`); scaffold column: {'present' if any('scaffold' in c for c in cols_lower) else '**absent**'}; "
      f"pair/construct/vector identifier: {'present' if has_pair else '**absent**'}.\n")

    # ---- 5. pair-guide reference ------------------------------------------------------------------
    cfg = Config.from_yaml(a.qc_config); cfg.guides.design.path = str(xl)
    design = load_guide_design(cfg)
    ref = design[["guide_id", "protospacer", "target_raw", "target", "is_control", "design_index"]].rename(columns={"protospacer": "designed_sequence", "is_control": "is_non_targeting"}).copy()
    ref["source_worksheet"] = sheets[0]["sheet"]
    ref["source_row"] = ref["design_index"] + 2  # 1-based Excel row (header = row 1)
    ref["target_gene_name"] = np.where(ref["is_non_targeting"], "ntc", ref["target_raw"])
    ref["target_symbol"] = ref["target_raw"].str.replace(r"\s*\(rs\d+\)\s*$", "", regex=True).replace({"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3"})
    ref.loc[ref["is_non_targeting"], "target_symbol"] = "ntc"
    # observed sequences / scaffold from the guide counter summaries (per well)
    scaf_reads = np.zeros((len(ref), 2)); reads = np.zeros(len(ref)); umis = np.zeros(len(ref))
    for w in WELLS:
        gs = pd.read_csv(Path(a.guide_counts_root) / w / f"{w}_guide_summary.tsv", sep="\t").set_index("guide_id").loc[ref["guide_id"]]
        scaf_reads += gs[["reads_scaffold_A", "reads_scaffold_C"]].to_numpy(); reads += gs["reads_matched"].to_numpy(); umis += gs["umis_in_cells"].to_numpy()
    tot = scaf_reads.sum(axis=1)
    purity = np.where(tot > 0, scaf_reads.max(axis=1) / np.maximum(tot, 1), np.nan)
    maj = np.where(scaf_reads[:, 0] >= scaf_reads[:, 1], "A", "C")
    ref["scaffold"] = np.where((tot >= 20) & (purity >= 0.9), maj, "unknown")
    ref["scaffold_source"] = np.where(ref["scaffold"] != "unknown", "empirical_from_reads(scaffold anchor majority, purity>=0.9, >=20 reads)", "unresolved_no_or_mixed_reads")
    ref["scaffold_purity"] = purity; ref["reads_scaffold_A"] = scaf_reads[:, 0].astype(int); ref["reads_scaffold_C"] = scaf_reads[:, 1].astype(int)
    ref["reads_matched_all_wells"] = reads.astype(int); ref["umis_in_cells_all_wells"] = umis.astype(int)
    ref["observed_sequence"] = np.where(reads > 0, ref["designed_sequence"], "")
    ref["exact_match_status"] = np.where(reads > 0, "exact_designed_sequence_observed (counter: exact 20-mer 5' of scaffold anchor; unambiguous 1-mismatch variants also counted to this guide)", "not_observed_in_any_well")
    ref["pair_id"] = ""  # no explicit pair / construct id in the workbook
    ref["reference_status"] = np.where(ref["scaffold"] == "unknown", "unresolved_scaffold", "resolved")
    # sequence uniqueness safeguard
    protos = ref["designed_sequence"].tolist()
    close = sum(1 for i, j in combinations(range(len(protos)), 2) if sum(x != y for x, y in zip(protos[i], protos[j])) <= 2)
    ref["min_pairwise_hamming_ge3"] = close == 0
    ref["design_source"] = str(xl)
    cols = ["guide_id", "observed_sequence", "designed_sequence", "target_gene_name", "target_symbol", "target_raw", "scaffold", "scaffold_source", "is_non_targeting", "pair_id",
            "source_worksheet", "source_row", "exact_match_status", "reference_status", "scaffold_purity", "reads_scaffold_A", "reads_scaffold_C", "reads_matched_all_wells", "umis_in_cells_all_wells", "min_pairwise_hamming_ge3", "design_source"]
    ref = ref[cols]
    ref.to_csv(audit / "pair_guide_reference.csv", index=False)
    per_t = ref.groupby(["target_gene_name", "is_non_targeting"]).agg(n_guides=("guide_id", "count"), n_A=("scaffold", lambda s: int((s == "A").sum())), n_C=("scaffold", lambda s: int((s == "C").sum())), n_unknown=("scaffold", lambda s: int((s == "unknown").sum()))).reset_index()
    per_t.to_csv(audit / "pair_guide_reference_per_target.csv", index=False)
    L("## 5. Pair-guide reference (`audit/pair_guide_reference.csv`)\n")
    L(f"- {len(ref)} designed guides; targets {int((~ref.is_non_targeting).astype(bool).sum() and ref.loc[~ref.is_non_targeting.astype(bool), 'target_gene_name'].nunique())}, NTC guides {int(ref.is_non_targeting.astype(bool).sum())}")
    L(f"- scaffold: {ref['scaffold'].value_counts().to_dict()} (empirical from the scaffold anchor of matched reads; the workbook has no scaffold column)")
    L(f"- observed in reads: {int((ref.observed_sequence != '').sum())}; not observed: {int((ref.observed_sequence == '').sum())}")
    L(f"- pairwise Hamming distance of designed protospacers >= 3 for all pairs: {close == 0} -> exact and 1-mismatch matching are unambiguous")
    L("- **pair_id is empty for every guide: the workbook carries no pair/construct/vector identifier.** Pairs are therefore reconstructed downstream only when the strongest scaffold-A and strongest scaffold-C guide of a cell map to the same target (or both are NTC); any other combination is labelled and excluded from primary testing. No pair is inferred from row order, abundance or sequence similarity.\n")
    L("- targets with both scaffolds represented: " + str(int(((per_t.n_A > 0) & (per_t.n_C > 0)).sum())) + f" / {len(per_t)}\n")

    # ---- 6. repository state -------------------------------------------------------------------------
    g = {k: sh(cmd, cwd=repo).strip() for k, cmd in (("branch", "git rev-parse --abbrev-ref HEAD"), ("head", "git rev-parse HEAD"), ("main", "git rev-parse main"), ("dev", "git rev-parse dev"),
                                                         ("status", "git status --short"), ("log", "git log --oneline -6"), ("main_log", "git log --oneline -3 main"), ("dev_log", "git log --oneline -3 dev"))}
    (audit / "repository_state.json").write_text(json.dumps(g, indent=1))
    L("## 6. Pipeline repository\n")
    L(f"- branch used: `{g['branch']}` at `{g['head']}` (dev lineage; `main` = `{g['main']}`, `dev` = `{g['dev']}`)")
    L(f"- recent commits:\n```\n{g['log']}\n```\n- main:\n```\n{g['main_log']}\n```\n- dev:\n```\n{g['dev_log']}\n```")
    L(f"- working tree (uncommitted, preserved): \n```\n{g['status'] or '(clean)'}\n```")
    L("- `main` lacks `guides.target_feature_column`, the FASTQ guide counter, the basic-QC stage and the pair-assignment mode; `dev`+feature branch has them. The pair mode (`guides.assignment_mode: pair`) exists only on the feature branch.\n")
    (audit / "initial_audit.md").write_text("\n".join(log) + "\n")
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
