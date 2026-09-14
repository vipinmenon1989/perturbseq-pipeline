#!/usr/bin/env python
"""Step 3: audit the Hanrui Fang guide-design workbook (every worksheet) and
write the designed-guide reference, the guide-design audit table, the pair
map (explicit if the workbook has one, otherwise an explicitly *provisional*
same-target map) and a Markdown audit.

Runs inside SLURM only (jobs/hanrui_fang/02_audit_guide_design.slurm).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guide_design import load_guide_design, _norm

# Keywords we look for in worksheet column names, per requested item.
ITEMS = {
    "guide_id": ("guide_id", "id", "sgrna_id", "name", "guide"),
    "protospacer": ("seq", "sequence", "spacer", "protospacer", "sgrna", "guide_sequence"),
    "target_gene": ("gene", "target", "target_gene", "symbol", "gene_symbol"),
    "target_label": ("label", "target_label", "category", "class", "type"),
    "scaffold": ("scaffold", "scaffold_class", "tracr", "backbone"),
    "non_targeting": ("ntc", "non_targeting", "control", "no_target", "notarget"),
    "guide_position": ("position", "pos", "slot", "order", "cassette"),
    "vector_id": ("vector", "vector_id", "plasmid", "construct", "oligo"),
    "pair_id": ("pair", "pair_id", "dual", "partner", "pairing"),
    "scaffold_pairing": ("scaffold_a", "scaffold_c", "a_guide", "c_guide", "guide_a", "guide_c"),
    "efficacy_score": ("efficacy", "score", "on_target", "ontarget", "rs3", "azimuth"),
    "starts_with_g": ("beginswithg", "begins_with_g", "starts_with_g", "startswithg", "g_prefix"),
    "aliases_rsid": ("alias", "aliases", "rsid", "rs_id", "snp", "synonym"),
}


def find_workbook(web_dir: Path) -> Path:
    hits = sorted(p for p in web_dir.rglob("*") if p.suffix.lower() in (".xlsx", ".xlsm", ".xls"))
    if not hits:
        raise FileNotFoundError(f"no Excel workbook under {web_dir}")
    if len(hits) > 1:
        print(f"WARNING: {len(hits)} workbooks found, using the first: {hits}")
    return hits[0]


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--web-dir", required=True)
    ap.add_argument("--qc-config", required=True, help="config with guides.design.* (consistent guide ids)")
    ap.add_argument("--prior-feature-table", default=None,
                    help="previous guide_feature_table.tsv with empirical scaffold per guide (optional)")
    ap.add_argument("--out-tables", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()

    out_tables = Path(args.out_tables)
    out_tables.mkdir(parents=True, exist_ok=True)
    xlsx = find_workbook(Path(args.web_dir))
    print(f"workbook: {xlsx} ({xlsx.stat().st_size} bytes, mtime {datetime.fromtimestamp(xlsx.stat().st_mtime)})")

    # ---- 1. every worksheet, raw ------------------------------------------------
    book = pd.read_excel(xlsx, sheet_name=None, header=None, dtype=object)
    sheet_summaries = []
    col_hits = []
    for name, raw in book.items():
        raw = raw.dropna(how="all").dropna(axis=1, how="all")
        header = [str(x) for x in raw.iloc[0].tolist()] if len(raw) else []
        body = raw.iloc[1:].reset_index(drop=True) if len(raw) else raw
        body.columns = header
        summ = {"sheet": name, "n_rows_incl_header": int(len(raw)), "n_data_rows": int(len(body)),
                "n_columns": int(raw.shape[1]), "columns": header}
        for c in header:
            col = body[c]
            n_unique = int(col.astype(str).nunique(dropna=True))
            example = col.dropna().astype(str).head(3).tolist()
            nc = _norm(c)
            matched = [item for item, kws in ITEMS.items() if any(k in nc for k in kws)]
            if "efficacy" in nc or "score" in nc:
                matched = [m for m in matched if m == "efficacy_score"]
            col_hits.append({"sheet": name, "column": c, "n_non_null": int(col.notna().sum()),
                             "n_unique": n_unique, "examples": "|".join(example),
                             "requested_items_matched": ";".join(matched) or ""})
        sheet_summaries.append(summ)
        print(f"sheet {name!r}: {summ['n_data_rows']} data rows x {summ['n_columns']} cols; header={header}")
    col_hits_df = pd.DataFrame(col_hits)
    col_hits_df.to_csv(out_tables / "guide_design_worksheet_columns.csv", index=False)

    # ---- 2. designed-guide reference via the pipeline's own loader ----------------
    cfg = Config.from_yaml(args.qc_config)
    cfg.guides.design.path = str(xlsx)
    design = load_guide_design(cfg)
    n = len(design)
    print(f"designed guides: {n}; targets: {design.loc[~design.is_control, 'target'].nunique()}; controls: {int(design.is_control.sum())}")

    # explicit pair / scaffold / vector columns anywhere in the workbook?
    explicit = {k: sorted({f"{r.sheet}:{r.column}" for r in col_hits_df.itertuples() if k in r.requested_items_matched.split(';')})
                for k in ("pair_id", "scaffold", "vector_id", "guide_position", "scaffold_pairing")}
    has_explicit_pair_map = bool(explicit["pair_id"] or explicit["scaffold_pairing"] or explicit["vector_id"])

    # ---- 3. scaffold: from workbook if present, else empirical from prior reads -----
    ref = design.copy()
    ref["scaffold_design"] = ref["scaffold"].where(ref["scaffold_source"] == "design_table", other="unknown")
    if args.prior_feature_table and Path(args.prior_feature_table).is_file():
        prior = pd.read_csv(args.prior_feature_table, sep="\t")
        prior = prior[["protospacer", "scaffold", "scaffold_purity", "scaffold_reads_total", "scaffold_reads_A", "scaffold_reads_C"]]
        prior = prior.rename(columns={"scaffold": "scaffold_empirical", "scaffold_purity": "scaffold_empirical_purity",
                                      "scaffold_reads_total": "scaffold_empirical_reads",
                                      "scaffold_reads_A": "scaffold_empirical_reads_A", "scaffold_reads_C": "scaffold_empirical_reads_C"})
        ref = ref.merge(prior, on="protospacer", how="left")
        ref["scaffold_empirical"] = ref["scaffold_empirical"].fillna("unknown")
        print("empirical scaffold table merged:", ref["scaffold_empirical"].value_counts(dropna=False).to_dict())
    else:
        ref["scaffold_empirical"] = "unknown"
        ref["scaffold_empirical_purity"] = np.nan
    if (ref["scaffold_design"] != "unknown").any():
        ref["scaffold"] = ref["scaffold_design"]
        ref["scaffold_source"] = "design_table"
    else:
        ref["scaffold"] = ref["scaffold_empirical"]
        ref["scaffold_source"] = np.where(ref["scaffold_empirical"] != "unknown", "empirical_from_reads_prior_run", "unspecified")

    # ---- 4. tidy reference columns --------------------------------------------------
    ref["target_gene_name"] = np.where(ref["is_control"], "ntc", ref["target"])
    ref["is_non_targeting"] = ref["is_control"].astype(bool)
    eff_col = next((c for c in ref.columns if "efficacy" in c), None)
    g_col = next((c for c in ref.columns if "beginswithg" in c or "begins_with_g" in c), None)
    ref["efficacy_score"] = pd.to_numeric(ref[eff_col], errors="coerce") if eff_col else np.nan
    ref["begins_with_g_design"] = ref[g_col].astype(str).str.lower().isin(["true", "1", "yes"]) if g_col else pd.NA
    ref["protospacer_starts_with_G"] = ref["protospacer"].str.startswith("G")
    ref["protospacer_length"] = ref["protospacer"].str.len()
    ref["guide_index_within_target"] = ref.groupby("target_raw").cumcount() + 1
    ref["n_guides_for_target"] = ref.groupby("target_raw")["guide_id"].transform("count")

    # near-identical protospacers (matching-rule safety)
    protos = ref["protospacer"].tolist()
    dup = ref["protospacer"].duplicated(keep=False)
    close = []
    for i, j in combinations(range(n), 2):
        d = hamming(protos[i], protos[j])
        if d <= 2:
            close.append({"guide_id_1": ref.guide_id[i], "guide_id_2": ref.guide_id[j], "hamming": d,
                          "target_1": ref.target_raw[i], "target_2": ref.target_raw[j]})
    close_df = pd.DataFrame(close, columns=["guide_id_1", "guide_id_2", "hamming", "target_1", "target_2"])
    close_df.to_csv(out_tables / "guide_design_near_identical_protospacers.csv", index=False)
    min_pairwise = int(close_df.hamming.min()) if len(close_df) else 3
    print(f"duplicate protospacers: {int(dup.sum())}; pairs with Hamming<=2: {len(close_df)}; min pairwise Hamming: {min_pairwise if len(close_df) else '>=3'}")

    # ---- 5. pair map ------------------------------------------------------------------
    if has_explicit_pair_map:
        pair_map_source = "design_sheet_explicit"
        raise SystemExit("Explicit pair/vector columns detected in the workbook; implement explicit parsing before continuing: "
                         + json.dumps(explicit))
    pair_map_source = "none_in_design_sheet__provisional_same_target_rule"
    pair_map = ref[["guide_id", "protospacer", "target_gene_name", "target_raw", "is_non_targeting", "scaffold", "scaffold_source"]].copy()
    pair_map["pair_id"] = ""                          # no explicit vector-level pairing exists
    pair_map["pair_map_source"] = pair_map_source
    pair_map["pair_rule"] = "provisional: scaffold-A guide + scaffold-C guide are a valid pair iff target_gene_name is identical (ntc+ntc valid ntc pair); targeting+ntc pairs are NOT confirmed by design and are labelled provisional"
    pair_map["pair_map_status"] = "provisional"
    pair_map.to_csv(out_tables / "guide_pair_map.csv", index=False)

    # ---- 6. write reference + audit tables ---------------------------------------------
    ref_cols = ["guide_id", "protospacer", "target_gene_name", "target_raw", "is_non_targeting", "scaffold", "scaffold_source",
                "scaffold_design", "scaffold_empirical", "scaffold_empirical_purity", "efficacy_score", "begins_with_g_design",
                "protospacer_starts_with_G", "protospacer_length", "design_index", "guide_index_within_target", "n_guides_for_target"]
    ref_out = ref[ref_cols].copy()
    ref_out["pair_id"] = ""
    ref_out["design_source"] = str(xlsx)
    ref_out.to_csv(out_tables / "guide_reference_used.csv", index=False)
    ref.assign(protospacer_duplicated=dup.values).to_csv(out_tables / "guide_design_audit.csv", index=False)

    # per-target summary
    tsum = (ref.groupby(["target_gene_name", "is_non_targeting"])
              .agg(n_guides=("guide_id", "count"),
                   n_scaffold_A=("scaffold", lambda s: int((s == "A").sum())),
                   n_scaffold_C=("scaffold", lambda s: int((s == "C").sum())),
                   n_scaffold_unknown=("scaffold", lambda s: int((~s.isin(["A", "C"])).sum())),
                   mean_efficacy=("efficacy_score", "mean"))
              .reset_index().sort_values("target_gene_name"))
    tsum.to_csv(out_tables / "guide_design_per_target.csv", index=False)

    # ---- 7. Markdown audit ------------------------------------------------------------------
    scaf_counts = ref["scaffold"].value_counts(dropna=False).to_dict()
    scaf_by_target_balanced = int(((tsum.n_scaffold_A > 0) & (tsum.n_scaffold_C > 0)).sum())
    lines = []
    L = lines.append
    L("# Hanrui Fang guide-design workbook audit")
    L("")
    L(f"- Workbook (found programmatically under `{args.web_dir}`): `{xlsx}`")
    L(f"- Size / mtime: {xlsx.stat().st_size} bytes / {datetime.fromtimestamp(xlsx.stat().st_mtime):%Y-%m-%d %H:%M}")
    L(f"- Audit date: {datetime.now():%Y-%m-%d %H:%M}; SLURM job: {Path('/proc/self').resolve().name if False else ''}{__import__('os').environ.get('SLURM_JOB_ID', 'n/a')}")
    L(f"- Guide-id rule: `{cfg.guides.design.id_format}` (target sanitised + 1-based index within target, workbook row order) via `perturbseq_pipeline.guide_design.load_guide_design`, identical to the earlier QC iteration so guide ids are stable across runs.")
    L("")
    L("## Worksheets")
    L("")
    L("| sheet | data rows | columns | header |")
    L("|---|---|---|---|")
    for s in sheet_summaries:
        L(f"| {s['sheet']} | {s['n_data_rows']} | {s['n_columns']} | {', '.join(s['columns'])} |")
    L("")
    L("## Requested items versus what the workbook contains")
    L("")
    L("| item | present in workbook? | column(s) | how the analysis obtains it |")
    L("|---|---|---|---|")
    def present(item):
        hits = sorted({f"{r.sheet}:{r.column}" for r in col_hits_df.itertuples() if item in r.requested_items_matched.split(';')})
        return ("yes" if hits else "no"), (", ".join(hits) if hits else "-")
    how = {
        "guide_id": "synthetic `<gene>_<n>` (no id column)",
        "protospacer": "column `seq` (20 nt)",
        "target_gene": "column `gene`",
        "target_label": "derived: `ntc` for NO-TARGET rows, else gene symbol",
        "scaffold": "NOT in workbook; scaffold A/C classified per read by the guide counter and summarised per guide (empirical, prior run purity shown in guide_reference_used.csv)",
        "non_targeting": "derived from `gene` matching guides.ntc_patterns (`^no[-_. ]?target`)",
        "guide_position": "NOT in workbook",
        "vector_id": "NOT in workbook",
        "pair_id": "NOT in workbook -> pair map is PROVISIONAL (same-target rule)",
        "scaffold_pairing": "NOT in workbook",
        "efficacy_score": "column `On-Target Efficacy Score`",
        "starts_with_g": "column `BeginsWithG`; also recomputed from the protospacer",
        "aliases_rsid": "no alias column; three target labels embed an rsID in the gene column (`FHL3 (rs114296424)`, `ILRUN (rs16878812)`, `LIPA (rs1412444)`) and are kept as distinct target labels",
    }
    for item in ITEMS:
        p, cols = present(item)
        if item in ("guide_id", "target_label", "non_targeting") and p == "yes" and item == "guide_id":
            pass
        L(f"| {item} | {p} | {cols} | {how[item]} |")
    L("")
    L("## Designed guides")
    L("")
    L(f"- Designed guides: **{n}** (all retained in the reference, observed or not)")
    L(f"- Targets (non-control): **{int(ref.loc[~ref.is_non_targeting, 'target_gene_name'].nunique())}**; control guides (NO-TARGET -> `ntc`): **{int(ref.is_non_targeting.sum())}**")
    L(f"- Guides per target: {ref.loc[~ref.is_non_targeting].groupby('target_gene_name').size().value_counts().sort_index().to_dict()} (n_guides: n_targets)")
    L(f"- Protospacer lengths: {ref.protospacer_length.value_counts().to_dict()}; duplicated protospacers: {int(dup.sum())}")
    L(f"- Protospacers starting with G: {int(ref.protospacer_starts_with_G.sum())}; workbook BeginsWithG==True: {int(ref.begins_with_g_design.sum()) if g_col else 'n/a'}")
    L(f"- Pairs of designed protospacers within Hamming distance 2: {len(close_df)} (min pairwise Hamming: {'>=3' if not len(close_df) else min_pairwise}). "
      + ("Exact matching is therefore unambiguous and 1-mismatch matching would also be unambiguous." if min_pairwise >= 3 else "1-mismatch matching would be AMBIGUOUS for these pairs; the counter must not rescue them."))
    L(f"- Scaffold class per guide (source: {ref.scaffold_source.value_counts().to_dict()}): {scaf_counts}")
    L(f"- Targets with at least one scaffold-A and one scaffold-C guide: {scaf_by_target_balanced} / {len(tsum)}")
    L("")
    L("## Pair map")
    L("")
    if has_explicit_pair_map:
        L("An explicit pair map was found and is used as authoritative.")
    else:
        L("**The workbook contains no explicit A–C pair map** (no vector ID, pair ID, guide position or scaffold column). "
          "Vector-level pairing therefore cannot be reconstructed from the design sheet.")
        L("")
        L("Consequences for the analysis:")
        L("- `tables/guide_pair_map.csv` carries every designed guide with its scaffold class and target but an **empty `pair_id`** and `pair_map_status = provisional`.")
        L("- The dual-guide assignment uses the documented **provisional same-target rule**: the strongest eligible scaffold-A guide and the strongest eligible scaffold-C guide form a valid pair only when they name the same target (or are both NTC). "
          "Targeting+NTC combinations cannot be confirmed by design and are labelled `provisional_target_ntc`; two different targets are `dual_target`.")
        L("- Pairs were **not** inferred from row order, guide abundance or sequence similarity.")
        L("- Final vector-level assignment is **not** claimed to be solved; every pair-level label written by the pipeline is tagged provisional.")
    L("")
    L("## Outputs")
    L("")
    for f in ("guide_design_audit.csv", "guide_reference_used.csv", "guide_pair_map.csv", "guide_design_per_target.csv",
              "guide_design_worksheet_columns.csv", "guide_design_near_identical_protospacers.csv"):
        L(f"- `{out_tables / f}`")
    Path(args.out_md).write_text("\n".join(lines) + "\n")
    print("wrote", args.out_md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
