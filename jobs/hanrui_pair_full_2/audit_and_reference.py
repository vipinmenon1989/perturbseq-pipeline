#!/usr/bin/env python
"""Iteration 2, step 1 (SLURM only): full audit of the Hanrui Fang dataset with the NEWLY supplied
experimental documents (20250822_OligoPool_TwistAddG.xlsx = construct / oligo map, Scaffold_seq.docx =
scaffold sequences), the experimental design record, the evidence matrix and the document-derived
pair-guide reference (one row per count-matrix feature = designed protospacer x scaffold class).

Everything here reads Excel / Word / FASTQ / HDF5-derived files, so it must run inside SLURM.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guide_design import load_guide_design

WELLS = {"HF011A": "HF011AF", "HF011B": "HF011BF", "HF012A": "HF012AF", "HF012B": "HF012BF"}
ANCHORS = {"A": "GTTTAAGAGCTA", "C": "GTTTCAGAGCTA"}
ILLUMINA_ADAPTER = "AGATCGGAAGAGC"
SYMBOL_FIX = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3", "CBWD1": "ZNG1A"}  # current HGNC symbols used by GRCh38-2024-A
JOB = os.environ.get("SLURM_JOB_ID", "n/a")
NOW = datetime.now()


def md5(path: Path, limit_bytes: int = 300_000_000) -> str:
    if path.stat().st_size > limit_bytes:
        return ""
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def sh(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd).stdout


def md_table(df: pd.DataFrame, max_rows: int = 400) -> str:
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.head(max_rows).iterrows():
        lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in r.tolist()) + " |")
    if len(df) > max_rows:
        lines.append(f"\n({len(df) - max_rows} more rows in the CSV)")
    return "\n".join(lines)


def md_to_html(md: str, title: str) -> str:
    from markdown_it import MarkdownIt
    body = MarkdownIt("commonmark").enable("table").render(md)
    css = ("body{font-family:system-ui,sans-serif;margin:24px;max-width:1400px;color:#222;line-height:1.4}table{border-collapse:collapse;font-size:11px}"
           "td,th{border:1px solid #ddd;padding:2px 6px;vertical-align:top}h2{border-bottom:1px solid #ccc;margin-top:32px}code{background:#f3f3f3;padding:1px 3px}"
           "pre{background:#f7f7f7;padding:8px;overflow:auto;font-size:11px}")
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title><style>{css}</style></head><body>{body}</body></html>"


def core_props(path: Path) -> dict:
    out = {}
    try:
        z = zipfile.ZipFile(path)
        if "docProps/core.xml" in z.namelist():
            core = z.read("docProps/core.xml").decode("utf8", "replace")
            for tag in ("dc:creator", "cp:lastModifiedBy", "dcterms:created", "dcterms:modified"):
                m = re.search(rf"<{tag}[^>]*>([^<]*)</{tag}>", core)
                out[tag.split(":")[1]] = m.group(1) if m else ""
    except Exception as exc:  # pragma: no cover
        out["error"] = str(exc)
    return out


def hamming(a: str, b: str) -> int:
    n = min(len(a), len(b))
    return sum(x != y for x, y in zip(a[:n].upper(), b[:n].upper()))


def mismatch_positions(a: str, b: str):
    n = min(len(a), len(b))
    return [i + 1 for i in range(n) if a[i].upper() != b[i].upper()]


# --------------------------------------------------------------------------------------------------
# FASTQ scaffold consensus (2M reads per well; fresh evidence for the scaffold audit)
# --------------------------------------------------------------------------------------------------


def scaffold_consensus(fastq: Path, n_reads: int, keep: int = 300_000, tail_len: int = 100):
    pat = re.compile("(" + ANCHORS["A"] + ")|(" + ANCHORS["C"] + ")")
    tails = {"A": [], "C": []}
    counts = {"A": 0, "C": 0}
    n = 0
    with gzip.open(fastq, "rt") as fh:
        for i, line in enumerate(fh):
            if i % 4 != 1:
                continue
            n += 1
            if n > n_reads:
                break
            seq = line.strip()
            m = pat.search(seq, 40)
            if not m:
                continue
            cls = "A" if m.lastindex == 1 else "C"
            counts[cls] += 1
            if len(tails[cls]) < keep:
                tails[cls].append(seq[m.start(): m.start() + tail_len])
    out = {}
    for cls, seqs in tails.items():
        if not seqs:
            out[cls] = {"n_anchor_reads": counts[cls], "consensus": "", "agreement": []}
            continue
        L = max(len(s) for s in seqs)
        cons, agree = [], []
        for p in range(L):
            col = Counter(s[p] for s in seqs if len(s) > p)
            tot = sum(col.values())
            if tot < 0.5 * len(seqs):
                break
            base, k = col.most_common(1)[0]
            cons.append(base)
            agree.append(k / tot)
        c = "".join(cons)
        ad = c.find(ILLUMINA_ADAPTER)
        out[cls] = {"n_anchor_reads": counts[cls], "n_reads_sampled": n, "consensus": c, "agreement": [round(a, 3) for a in agree],
                    "illumina_adapter_at": ad, "consensus_insert": c[:ad] if ad > 0 else c}
    return out


# --------------------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--prev", required=True, help="previous result directory (read-only)")
    ap.add_argument("--prev-design-audit", required=True, help="results/Hanrui_Fang_library_design_audit")
    ap.add_argument("--qc-config", required=True, help="config with guides.design.* (design_out_v2 ids)")
    ap.add_argument("--cellranger-root", required=True)
    ap.add_argument("--fastq-sample-reads", type=int, default=2_000_000)
    a = ap.parse_args()
    data, repo, out, prev = Path(a.data), Path(a.repo), Path(a.out), Path(a.prev)
    audit = out / "audit"
    audit.mkdir(parents=True, exist_ok=True)
    facts = []  # evidence matrix rows

    def fact(fid, question, source, where, text, interpretation, etype, status="answered"):
        facts.append({"fact_id": fid, "question": question, "source_file": str(source), "worksheet_or_section": where, "exact_text_or_field": text,
                      "interpretation": interpretation, "evidence_type": etype, "status": status})

    # ============================================================================================
    # 1. Data inventory (every file under the dataset root + inputs staged in the repo)
    # ============================================================================================
    rows = []
    md5_sidecars = {}
    for cs in data.rglob("checksum.md5"):
        for line in cs.read_text().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                md5_sidecars[Path(parts[-1]).name] = parts[0]
    for p in sorted(data.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(data)
        top = rel.parts[0]
        if top == "web_summaries":
            cls = "experimental_document" if p.suffix.lower() in (".xlsx", ".docx") else "cellranger_web_summary_copy"
        elif top == "data_audit":
            cls = "previous_analyst_audit"
        elif top.endswith("F"):
            cls = "guide_fastq"
        elif "fastq" in rel.parts:
            cls = "gex_fastq"
        elif "bam" in rel.parts:
            cls = "cellranger_bam"
        elif "analysis" in rel.parts:
            cls = "cellranger_delivery"
        else:
            cls = "other"
        st = p.stat()
        small = st.st_size < 50_000_000 and cls in ("experimental_document", "cellranger_web_summary_copy", "cellranger_delivery")
        rows.append({"path": str(p), "relative_path": str(rel), "size_bytes": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes"),
                     "class": cls, "md5": md5(p) if small else md5_sidecars.get(p.name, ""), "md5_source": "computed" if small else ("vendor checksum.md5" if p.name in md5_sidecars else ""),
                     "used_in_iteration_2": cls in ("experimental_document", "guide_fastq", "cellranger_delivery", "cellranger_web_summary_copy")})
    for w in WELLS:
        d = Path(a.cellranger_root) / w
        for f in sorted(d.rglob("*")):
            if f.is_file():
                st = f.stat()
                rows.append({"path": str(f), "relative_path": f"staged_cellranger/{w}/{f.relative_to(d)}", "size_bytes": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="minutes"),
                             "class": "cellranger_staged_matrix", "md5": md5(f) if st.st_size < 50_000_000 else "", "md5_source": "computed" if st.st_size < 50_000_000 else "", "used_in_iteration_2": True})
    for f in sorted(prev.rglob("*")):
        if f.is_file() and f.suffix in (".yaml", ".json", ".md", ".csv", ".html", ".txt"):
            rows.append({"path": str(f), "relative_path": f"previous_run/{f.relative_to(prev)}", "size_bytes": f.stat().st_size, "mtime": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes"),
                         "class": "previous_result", "md5": "", "md5_source": "", "used_in_iteration_2": "comparison only"})
    inv = pd.DataFrame(rows)
    inv.to_csv(audit / "data_inventory.csv", index=False)
    usb = [r for r in rows if "usb" in r["relative_path"].lower()]
    fact("F01", "Are there USB-delivered or otherwise hidden files?", data, "find over the dataset root", f"{len(usb)} path(s) containing 'usb'", "no USB folder exists; all experimental documents live in web_summaries/", "filesystem", "answered")
    docs = inv[inv["class"] == "experimental_document"]
    fact("F02", "Which experimental documents exist?", data / "web_summaries", "directory listing",
         "; ".join(f"{Path(p).name} ({s:,} B, mtime {m}, md5 {h})" for p, s, m, h in docs[["path", "size_bytes", "mtime", "md5"]].itertuples(index=False)),
         "three documents: design_out_v2.xlsx (guide design, 2026-09-13), 20250822_OligoPool_TwistAddG.xlsx and Scaffold_seq.docx (both supplied 2026-09-15)", "experimental_document")

    # ============================================================================================
    # 2. Documents: guide design workbook, oligo-pool construct workbook, scaffold Word document
    # ============================================================================================
    xl_design = data / "web_summaries" / "design_out_v2.xlsx"
    xl_oligo = data / "web_summaries" / "20250822_OligoPool_TwistAddG.xlsx"
    docx_scaf = data / "web_summaries" / "Scaffold_seq.docx"
    props = {p.name: core_props(p) for p in (xl_design, xl_oligo, docx_scaf)}
    (audit / "document_properties.json").write_text(json.dumps(props, indent=1))
    for p in (xl_design, xl_oligo, docx_scaf):
        pr = props[p.name]
        fact("F03", "Who authored the documents and when?", p, "docProps/core.xml", json.dumps(pr), "document metadata (author, creation / modification time)", "experimental_document")

    cfg = Config.from_yaml(a.qc_config)
    cfg.guides.design.path = str(xl_design)
    design = load_guide_design(cfg)  # 560 rows: guide_id (<gene>_<n>), protospacer, target_raw, is_control, design_index
    assert len(design) == 560, len(design)
    design["excel_row"] = design["design_index"] + 2
    fact("F04", "What does design_out_v2.xlsx contain?", xl_design, "Sheet1", "columns gene / seq / On-Target Efficacy Score / BeginsWithG; 560 rows",
         f"{len(design)} designed 20-nt protospacers for {design.loc[~design.is_control, 'target_raw'].nunique()} target labels + {int(design.is_control.sum())} NO-TARGET guides; "
         "no scaffold, pair, construct or position column. Guide ids are synthesised as <gene>_<n> (row order within target).", "experimental_document")
    fact("F05", "Does 'BeginsWithG' denote a scaffold?", xl_design, "Sheet1 column BeginsWithG",
         f"BeginsWithG == (seq[0] == 'G') for {int((design['beginswithg'].astype(str).str.lower() == design['protospacer'].str.startswith('G').astype(str).str.lower()).sum()) if 'beginswithg' in design.columns else 'n/a'}/560 rows",
         "BeginsWithG is a derived sequence property (first base is G), not a scaffold or cassette label; it is NOT used as a scaffold label", "experimental_document")

    raw = pd.read_excel(xl_oligo, sheet_name=None, header=None, dtype=str)
    assert len(raw) == 1, list(raw)
    sheet_name = list(raw)[0]
    o = raw[sheet_name].dropna(how="all").dropna(axis=1, how="all")
    header = [str(x).strip() for x in o.iloc[0]]
    o = o.iloc[1:].reset_index(drop=True)
    o.columns = header
    o["excel_row"] = np.arange(2, len(o) + 2)
    col_name = [c for c in header if c.lower().startswith("name")][0]
    col_p1 = [c for c in header if c.lower().startswith("position 1")][0]
    col_p2 = [c for c in header if c.lower().startswith("position 2")][0]
    col_bb = [c for c in header if c.lower() == "backbone"][0]
    col_blp = [c for c in header if "blpi" in c.lower()][0]
    col_bst = [c for c in header if "bstxi" in c.lower()][0]
    col_al = [c for c in header if "adaptor left" in c.lower()][0]
    col_ar = [c for c in header if "adaptor right" in c.lower()][0]
    col_full = [c for c in header if "oligo" in c.lower()][0]
    fact("F06", "What does the oligo-pool workbook contain?", xl_oligo, sheet_name, f"columns: {header}; {len(o)} construct rows",
         "one row per cloned dual-guide construct: construct name, PCR adaptors, BstXI site, position-1 sgRNA (21 nt), backbone, position-2 sgRNA (21 nt), BlpI site, full 5'->3' oligo", "experimental_document")
    # constant parts
    consts = {c: o[c].str.strip().unique().tolist() for c in (col_al, col_bst, col_bb, col_blp, col_ar)}
    fact("F07", "Which parts of the oligo are constant?", xl_oligo, sheet_name, json.dumps(consts),
         "all adaptor / cloning-site / backbone columns are identical across the 236 constructs -> one vector architecture for the whole library", "experimental_document")
    backbone = consts[col_bb][0]
    blp = consts[col_blp][0]
    # scaffold document
    import docx as _docx
    d = _docx.Document(docx_scaf)
    paras = [p.text.strip() for p in d.paragraphs if p.text.strip()]
    scaf_doc = {}
    for i, t in enumerate(paras):
        m = re.match(r"^Scaffold\s*(\d+)\s*:?\s*$", t, re.I)
        if m and i + 1 < len(paras):
            scaf_doc[f"Scaffold {m.group(1)}"] = re.sub(r"\s+", "", paras[i + 1]).upper()
        m2 = re.match(r"^Scaffold\s*(\d+)\s*:\s*([ACGTacgt]+)$", t)
        if m2:
            scaf_doc[f"Scaffold {m2.group(1)}"] = m2.group(2).upper()
    assert len(scaf_doc) == 2, paras
    fact("F08", "What are the scaffold sequences?", docx_scaf, "paragraphs 1-5", " | ".join(f"{k}: {v}" for k, v in scaf_doc.items()),
         "two full sgRNA scaffold (tracrRNA + terminator) sequences; Scaffold 1 begins GTTTCAGAGCTA (read class C), Scaffold 2 begins GTTTAAGAGCTA (read class A)", "experimental_document")

    # ---- constructs --------------------------------------------------------------------------
    design_by_seq = {s: gid for s, gid in zip(design["protospacer"], design["guide_id"])}
    design_row = design.set_index("guide_id")
    cons_rows = []
    for _, r in o.iterrows():
        name_raw = str(r[col_name]).strip()
        name = re.sub(r"\s+", "", name_raw)
        anomaly = "" if name == name_raw else f"name contains whitespace: {name_raw!r} -> normalised {name!r}"
        p1, p2 = str(r[col_p1]).strip().upper(), str(r[col_p2]).strip().upper()
        full = re.sub(r"\s+", "", str(r[col_full])).upper()  # the workbook cell contains a space between the BstXI site and the spacer
        expected_full = (consts[col_al][0] + consts[col_bst][0] + p1 + backbone + p2 + blp + consts[col_ar][0]).upper()
        rec = {"construct_id": name, "construct_name_in_workbook": name_raw, "excel_row": int(r["excel_row"]), "name_anomaly": anomaly,
               "position1_oligo_21nt": p1, "position2_oligo_21nt": p2, "position1_first_base": p1[:1], "position2_first_base": p2[:1],
               "full_oligo_matches_concatenation": full == expected_full}
        for pos, seq21 in (("1", p1), ("2", p2)):
            sp = seq21[1:] if len(seq21) == 21 else seq21
            gid = design_by_seq.get(sp)
            alt = design_by_seq.get(seq21[:20]) if gid is None else None
            rec[f"position{pos}_spacer20"] = sp
            rec[f"position{pos}_design_id"] = gid or (alt or "")
            rec[f"position{pos}_match"] = ("G + designed 20-mer (exact)" if gid else ("designed 20-mer + trailing base" if alt else "NOT IN DESIGN WORKBOOK"))
            g = gid or alt
            rec[f"position{pos}_target"] = design_row.loc[g, "target_raw"] if g else ""
            rec[f"position{pos}_is_ntc"] = bool(design_row.loc[g, "is_control"]) if g else None
        rec["position1_scaffold_class"] = "C"  # backbone starts with Scaffold-1 (GTTTCAGAGC...) directly after position 1
        rec["position2_scaffold_class"] = "A"  # BlpI cloning-site column = GTTTAAGAGCTAAGCTG = start of Scaffold 2
        n1, n2 = rec["position1_is_ntc"], rec["position2_is_ntc"]
        t1, t2 = rec["position1_target"], rec["position2_target"]
        if n1 and n2:
            ctype = "ntc_pair"
        elif n1 or n2:
            ctype = "targeting_plus_ntc"
        elif t1 == t2:
            ctype = "dual_targeting_same_target"
        else:
            ctype = "dual_targeting_DIFFERENT_targets"
        rec["construct_type"] = ctype
        rec["construct_target"] = "ntc" if ctype == "ntc_pair" else (t1 if not n1 else t2)
        rec["name_suffix"] = re.sub(r"^.*_", "", name)
        rec["name_gene"] = re.sub(r"_[^_]+$", "", name)
        cons_rows.append(rec)
    constructs = pd.DataFrame(cons_rows)
    constructs.to_csv(audit / "pair_mapping_audit.csv", index=False)
    assert constructs["construct_id"].is_unique
    unmatched = constructs[(constructs.position1_design_id == "") | (constructs.position2_design_id == "")]
    fact("F09", "Do the oligo spacers match the designed guides?", xl_oligo, sheet_name,
         f"position 1: {constructs.position1_match.value_counts().to_dict()}; position 2: {constructs.position2_match.value_counts().to_dict()}; first base G in {int((constructs.position1_first_base == 'G').sum())}/{len(constructs)} and {int((constructs.position2_first_base == 'G').sum())}/{len(constructs)}",
         "every oligo spacer is exactly 'G' + a designed 20-mer from design_out_v2 (the workbook name 'TwistAddG' = a G was prepended to every spacer); design ids are therefore recoverable for every slot", "experimental_document", "answered" if unmatched.empty else "PARTIAL")
    fact("F10", "How many constructs of which type?", xl_oligo, sheet_name, json.dumps(constructs.construct_type.value_counts().to_dict()) + "; name suffix classes: " + json.dumps(constructs.name_suffix.str.replace(r"\d+", "", regex=True).value_counts().to_dict()),
         "135 '<gene>_<n>F' constructs = two guides of the same target (dual targeting); 41 '<gene>_S1' = one targeting guide (position 1, identical to the _1F position-1 guide) + the NO-TARGET guide GAAACGAGAAGTTTGTACTA in position 2 (designed single-guide constructs); "
         "63 'NO-TARGET_<n>F' = two NO-TARGET guides (NTC pairs). No construct combines two different targets.", "experimental_document")
    fact("F11", "Which promoter/scaffold follows each position?", xl_oligo, sheet_name, f"backbone column = {backbone}; BlpI column = {blp}",
         "the backbone begins with 'gtttcagagc' = first 10 nt of Scaffold 1 (docx) -> position-1 guide is transcribed with Scaffold 1 (read class C); the BlpI column 'GTTTAAGAGCTAAGCTG' = first 17 nt of Scaffold 2 (docx) -> position-2 guide uses Scaffold 2 (read class A). "
         "The remaining backbone (BsmBI-flanked stuffer 'gagacg...cgtctc' + 'agaaacatg') marks where the rest of scaffold 1, the terminator and the second promoter are inserted during cloning (dual-cassette architecture as in Replogle/Adamson-type dual-guide vectors).", "experimental_document + sequence inference")

    # per-target construct summary
    per_target = constructs.groupby("construct_target").agg(n_constructs=("construct_id", "count"), construct_types=("construct_type", lambda s: ";".join(sorted(set(s)))),
                                                             constructs=("construct_id", lambda s: ";".join(s))).reset_index()
    per_target.to_csv(audit / "constructs_per_target.csv", index=False)

    # ---- guide-level (design guide) audit ------------------------------------------------------
    slot_rows = []
    for _, c in constructs.iterrows():
        for pos in ("1", "2"):
            slot_rows.append({"construct_id": c["construct_id"], "construct_type": c["construct_type"], "position": int(pos), "design_id": c[f"position{pos}_design_id"],
                              "scaffold": c[f"position{pos}_scaffold_class"], "spacer20": c[f"position{pos}_spacer20"], "oligo21": c[f"position{pos}_oligo_21nt"], "excel_row": c["excel_row"]})
    slots = pd.DataFrame(slot_rows)
    prev_ref = pd.read_csv(prev / "audit" / "pair_guide_reference.csv", dtype=str, keep_default_na=False).set_index("guide_id")
    prev_audit_ref = None
    g_rows = []
    for gid, r in design_row.iterrows():
        s = slots[slots.design_id == gid]
        scafs = sorted(set(s.scaffold))
        pe = prev_ref.loc[gid] if gid in prev_ref.index else None
        prev_scaf = pe["scaffold"] if pe is not None else ""
        agree = ("n/a (not cloned)" if not scafs else ("agree" if prev_scaf in scafs else ("previous unknown" if prev_scaf in ("unknown", "") else "DISAGREE")))
        g_rows.append({"design_guide_id": gid, "guide_sequence": r["protospacer"], "target_gene": r["target_raw"], "is_non_targeting": bool(r["is_control"]), "design_excel_row": int(r["excel_row"]),
                       "in_oligo_pool": len(s) > 0, "n_construct_slots": len(s), "construct_ids": ";".join(s.construct_id), "positions": ";".join(map(str, sorted(set(s.position)))),
                       "scaffold_classes_by_design": ";".join(scafs), "previous_empirical_scaffold": prev_scaf,
                       "previous_reads_scaffold_A": pe["reads_scaffold_A"] if pe is not None else "", "previous_reads_scaffold_C": pe["reads_scaffold_C"] if pe is not None else "",
                       "previous_umis_in_cells_all_wells": pe["umis_in_cells_all_wells"] if pe is not None else "", "design_vs_previous_empirical_scaffold": agree})
    gaudit = pd.DataFrame(g_rows)
    gaudit.to_csv(audit / "guide_reference_audit.csv", index=False)
    n_cloned = int(gaudit.in_oligo_pool.sum())
    n_both = int((gaudit.scaffold_classes_by_design == "A;C").sum())
    fact("F12", "How many designed guides were cloned, and does the document scaffold agree with the read-derived scaffold?", xl_oligo, sheet_name,
         f"{n_cloned}/560 designed spacers appear in the oligo pool ({int(gaudit.n_construct_slots.sum())} slots); {n_both} spacer(s) used with BOTH scaffolds; design-vs-previous-empirical scaffold: {gaudit.design_vs_previous_empirical_scaffold.value_counts().to_dict()}",
         "the document-derived scaffold agrees with the read-derived scaffold for every cloned guide that was observed; the spacer NO-TARGET_1 (GAAACGAGAAGTTTGTACTA) is used with Scaffold 1 in NO-TARGET_1F and with Scaffold 2 in the 41 _S1 constructs, so guide counting must be scaffold-specific. "
         f"{560 - n_cloned} designed spacers (incl. all MIF-AS1 guides) were never cloned, which explains the 'unobserved guides' of previous iterations.", "experimental_document vs FASTQ-derived")
    not_cloned_prev_observed = gaudit[(~gaudit.in_oligo_pool) & (pd.to_numeric(gaudit.previous_umis_in_cells_all_wells, errors="coerce").fillna(0) > 0)]
    fact("F13", "Were non-cloned designed spacers observed in reads?", prev / "audit" / "pair_guide_reference.csv", "umis_in_cells_all_wells",
         f"{len(not_cloned_prev_observed)} non-cloned spacers had >0 UMIs in the previous count matrices (max {pd.to_numeric(not_cloned_prev_observed.previous_umis_in_cells_all_wells, errors='coerce').max() if len(not_cloned_prev_observed) else 0:.0f} UMIs over all wells)",
         "low-level counts on non-cloned spacers are sequencing / 1-mismatch artefacts; iteration 2 keeps them as off-design features that can only make a cell unresolved, never assigned", "computational_inference")

    # ============================================================================================
    # 3. Scaffold audit: Word document vs oligo workbook vs reads
    # ============================================================================================
    cons_by_well = {}
    for w, lib in WELLS.items():
        fq = sorted((data / lib).rglob("*_L004_R1_001.fastq.gz"))[0]
        cons_by_well[w] = scaffold_consensus(fq, a.fastq_sample_reads)
        cons_by_well[w]["file"] = str(fq)
    (audit / "scaffold_read_consensus.json").write_text(json.dumps(cons_by_well, indent=1))
    prev_scaf = pd.read_csv(Path(a.prev_design_audit) / "scaffold_evidence.csv") if (Path(a.prev_design_audit) / "scaffold_evidence.csv").is_file() else None
    srows = []
    doc_for_class = {"C": "Scaffold 1", "A": "Scaffold 2"}
    for cls in ("A", "C"):
        doc_label = doc_for_class[cls]
        doc_seq = scaf_doc[doc_label]
        srows.append({"item": f"document {doc_label}", "scaffold_class": cls, "source": str(docx_scaf), "where": doc_label, "sequence": doc_seq, "length": len(doc_seq), "evidence_type": "experimental_document",
                      "comparison": "reference sequence", "mismatch_positions_vs_document": "", "n_mismatches_over_compared_length": ""})
        partial = backbone.upper() if cls == "C" else blp.upper()
        pl = 10 if cls == "C" else len(partial)
        srows.append({"item": f"oligo workbook partial scaffold after position {'1' if cls == 'C' else '2'}", "scaffold_class": cls, "source": str(xl_oligo), "where": f"column '{col_bb if cls == 'C' else col_blp}'",
                      "sequence": partial[:pl], "length": pl, "evidence_type": "experimental_document", "comparison": f"first {pl} nt vs document {doc_label}",
                      "mismatch_positions_vs_document": ";".join(map(str, mismatch_positions(partial[:pl], doc_seq[:pl]))), "n_mismatches_over_compared_length": f"{hamming(partial[:pl], doc_seq[:pl])}/{pl}"})
        for w in WELLS:
            c = cons_by_well[w][cls]
            ins = c.get("consensus_insert", "")
            srows.append({"item": f"read consensus {w} ({cons_by_well[w]['file'].split('/')[-1]}, first {c.get('n_reads_sampled', 0):,} reads, {c['n_anchor_reads']:,} anchored)", "scaffold_class": cls, "source": cons_by_well[w]["file"],
                          "where": f"R1 from anchor {ANCHORS[cls]} to Illumina adapter (at {c.get('illumina_adapter_at')} nt)", "sequence": ins, "length": len(ins), "evidence_type": "fastq_derived",
                          "comparison": f"sequenced insert vs document {doc_label}[:{len(ins)}]", "mismatch_positions_vs_document": ";".join(map(str, mismatch_positions(ins, doc_seq))),
                          "n_mismatches_over_compared_length": f"{hamming(ins, doc_seq)}/{min(len(ins), len(doc_seq))}"})
        if prev_scaf is not None:
            for _, r in prev_scaf[prev_scaf.scaffold_class == cls].iterrows():
                srows.append({"item": f"previous design-audit consensus {r.well} (SLURM 20045629)", "scaffold_class": cls, "source": str(Path(a.prev_design_audit) / "scaffold_evidence.csv"), "where": f"row well={r.well}",
                              "sequence": r.observed_scaffold_consensus_from_anchor, "length": len(str(r.observed_scaffold_consensus_from_anchor)), "evidence_type": "fastq_derived (previous iteration)",
                              "comparison": f"vs document {doc_label}", "mismatch_positions_vs_document": ";".join(map(str, mismatch_positions(str(r.observed_scaffold_consensus_from_anchor), doc_seq))),
                              "n_mismatches_over_compared_length": f"{hamming(str(r.observed_scaffold_consensus_from_anchor), doc_seq)}/{min(len(str(r.observed_scaffold_consensus_from_anchor)), len(doc_seq))}"})
    scaffold_audit = pd.DataFrame(srows)
    scaffold_audit.to_csv(audit / "scaffold_audit.csv", index=False)
    mmA = scaffold_audit[(scaffold_audit.scaffold_class == "A") & scaffold_audit.item.str.startswith("read consensus")]["n_mismatches_over_compared_length"].unique().tolist()
    mmC = scaffold_audit[(scaffold_audit.scaffold_class == "C") & scaffold_audit.item.str.startswith("read consensus")]["n_mismatches_over_compared_length"].unique().tolist()
    posC = scaffold_audit[(scaffold_audit.scaffold_class == "C") & scaffold_audit.item.str.startswith("read consensus")]["mismatch_positions_vs_document"].unique().tolist()
    fact("F14", "Do the sequenced scaffolds match the Word document?", docx_scaf, "Scaffold 1 / Scaffold 2 vs R1 read consensus",
         f"class A (Scaffold 2) mismatches over sequenced insert: {mmA}; class C (Scaffold 1): {mmC} at positions {posC}",
         "Scaffold 2 (class A) matches the reads exactly over the sequenced 63 nt. Scaffold 1 (class C) differs from the reads at two adjacent positions (~53-54, document 'gtccgtttacaac' vs reads 'GTCCGTTATCAAC'); the reads are identical across all four wells, so the "
         "document text most likely carries a transposition typo in that region (the canonical scaffold reads ...GTCCGTTATCAACTTG...). The anchor used for counting (first 12 nt) is identical in both sources. The terminator region beyond 63 nt is not sequenced (Illumina adapter follows).", "experimental_document vs fastq_derived")

    # ============================================================================================
    # 4. Cell Ranger / sample metadata
    # ============================================================================================
    ws_rows = []
    for w in WELLS:
        ms = Path(a.cellranger_root) / w / "metrics_summary.csv"
        m = pd.read_csv(ms).iloc[0].to_dict() if ms.is_file() else {}
        js = data / "data_audit" / "tmp" / f"{w}_web_summary.json"
        chem = pipe = ref = ""
        if js.is_file():
            txt = js.read_text(errors="ignore")
            mm = re.search(r'"Chemistry",\s*"([^"]+)"', txt); chem = mm.group(1) if mm else ""
            mm = re.search(r'"Pipeline Version",\s*"([^"]+)"', txt); pipe = mm.group(1) if mm else ""
            mm = re.search(r'"Transcriptome",\s*"([^"]+)"', txt); ref = mm.group(1) if mm else ""
        readme = (data / w / "analysis")
        readme_txt = next(iter(readme.rglob("README.txt")), None)
        gex_fq = sorted((data / w / "fastq").rglob("*_R1_001.fastq.gz"))
        gd_fq = sorted((data / WELLS[w]).rglob("*_R1_001.fastq.gz"))
        ws_rows.append({"sample": w, "guide_library": WELLS[w], "cellranger_estimated_cells": m.get("Estimated Number of Cells", ""), "cellranger_mean_reads_per_cell": m.get("Mean Reads per Cell", ""),
                        "cellranger_median_genes_per_cell": m.get("Median Genes per Cell", ""), "cellranger_number_of_reads": m.get("Number of Reads", ""), "cellranger_sequencing_saturation": m.get("Sequencing Saturation", ""),
                        "chemistry": chem, "pipeline_version": pipe, "transcriptome": ref, "gex_fastq_files_R1": ";".join(p.name for p in gex_fq), "guide_fastq_files_R1": ";".join(p.name for p in gd_fq),
                        "flowcell_run": gex_fq[0].parent.name if gex_fq else "", "sample_index_number_gex": re.search(r"_S(\d+)_", gex_fq[0].name).group(1) if gex_fq else "", "sample_index_number_guide": re.search(r"_S(\d+)_", gd_fq[0].name).group(1) if gd_fq else "",
                        "well_group_from_id": w[:5], "well_letter_from_id": w[5:], "condition_meaning": "UNKNOWN (no experimental document defines HF011 vs HF012)", "replicate_type": "UNKNOWN (biological vs technical not documented)",
                        "cell_line": "UNKNOWN (not documented)", "crispr_modality_effector": "UNKNOWN (not documented)", "documents_mentioning_sample": "none of the three documents mentions HF011/HF012/A/B",
                        "metadata_source": "Cell Ranger metrics_summary.csv + web_summary.html + FASTQ names; condition/replicate labels are analyst-derived from the well id (inferred)"})
    smeta = pd.DataFrame(ws_rows)
    smeta.to_csv(audit / "sample_metadata_audit.csv", index=False)
    fact("F15", "What are HF011A/B and HF012A/B?", data, "directory names, FASTQ names, Cell Ranger metrics", "; ".join(f"{r.sample}: {r.cellranger_estimated_cells} cells, S{r.sample_index_number_gex}/S{r.sample_index_number_guide}, {r.chemistry}, {r.pipeline_version}" for r in smeta.itertuples()),
         "four separate 10x 5' GEM wells (own Cell Ranger run, own guide-capture library, flowcell 260826_LH00131_0676_A23YCWJLT4 lanes 4+5). HF011 vs HF012 and A vs B are NOT defined by any document: treated as well-group / well labels; biological vs technical replicate status unknown.", "cellranger + filesystem", "PARTIAL")
    fact("F16", "Cell line, CRISPR modality, effector, MOI?", docx_scaf, "all documents", "no statement in design_out_v2.xlsx, 20250822_OligoPool_TwistAddG.xlsx or Scaffold_seq.docx",
         "not documented; the analysis reports target-transcript depletion associations and observed guide multiplicity, without a modality or MOI claim", "gap", "NOT_ANSWERED")
    manifest = pd.DataFrame({"lane_id": list(WELLS), "sample": list(WELLS), "lane": list(WELLS), "gem_well": [w[-1] for w in WELLS], "guide_library": list(WELLS.values()),
                             "cell_line": "unknown", "condition": [w[:5] for w in WELLS], "replicate": [w[-1] for w in WELLS], "replicate_type": "unknown", "condition_status": "well_id_derived_label_not_experimental_metadata",
                             "metadata_source": "analyst; no sample sheet or experimental metadata file exists (audit F15/F16)"})
    man_path = repo / "config" / "Hanrui_Fang_pair_guide_full_2_sample_manifest.csv"
    manifest.to_csv(man_path, index=False)

    # ============================================================================================
    # 5. Pair-guide reference (one row per count-matrix feature: designed spacer x scaffold class)
    # ============================================================================================
    ref_rows = []
    for gid, r in design_row.iterrows():
        for cls in ("A", "C"):
            s = slots[(slots.design_id == gid) & (slots.scaffold == cls)]
            designed = len(s) > 0
            tgt_raw = r["target_raw"]
            is_ntc = bool(r["is_control"])
            ctypes = sorted(set(s.construct_type)) if designed else []
            ref_rows.append({
                "guide_id": f"{gid}:{cls}", "design_guide_id": gid, "guide_sequence": r["protospacer"], "oligo_sequence_21nt": s.oligo21.iloc[0] if designed else "",
                "target_gene": tgt_raw, "target_gene_name": "ntc" if is_ntc else tgt_raw,
                "target_symbol": "ntc" if is_ntc else SYMBOL_FIX.get(re.sub(r"\s*\(rs\d+\)\s*$", "", tgt_raw), re.sub(r"\s*\(rs\d+\)\s*$", "", tgt_raw)),
                "scaffold": cls, "scaffold_document_label": doc_for_class[cls], "scaffold_sequence_document": scaf_doc[doc_for_class[cls]], "scaffold_anchor_used_for_counting": ANCHORS[cls],
                "construct_position": (1 if cls == "C" else 2) if designed else "", "designed_slot": designed,
                "pair_id": ";".join(s.construct_id) if designed else "", "construct_id": ";".join(s.construct_id) if designed else "", "n_constructs": len(s),
                "construct_types": ";".join(ctypes), "control_status": "non_targeting" if is_ntc else "targeting", "is_non_targeting": is_ntc,
                "source_file": f"{xl_oligo.name} + {xl_design.name}" if designed else xl_design.name,
                "source_sheet_or_page": (f"{xl_oligo.name}:{sheet_name} rows {','.join(map(str, s.excel_row))}; " if designed else "") + f"{xl_design.name}:Sheet1 row {int(r['excel_row'])}",
                "sequence_match_status": ("oligo 21-mer == 'G' + designed 20-mer (exact); scaffold from oligo backbone / BlpI column" if designed else
                                          ("designed spacer NOT in the oligo pool (never cloned): feature kept as off-design diagnostic" if len(slots[slots.design_id == gid]) == 0 else
                                           f"designed spacer cloned only with scaffold {slots[slots.design_id == gid].scaffold.iloc[0]}: this feature = off-design (wrong-scaffold) diagnostic")),
                "feature_role": "designed_slot" if designed else ("non_cloned_spacer" if len(slots[slots.design_id == gid]) == 0 else "wrong_scaffold_chimera_diagnostic"),
            })
    ref = pd.DataFrame(ref_rows)
    assert ref.guide_id.is_unique
    ref.to_csv(audit / "pair_guide_reference.csv", index=False)
    designed_ref = ref[ref.designed_slot]
    fact("F17", "What is the pair reference used by the pipeline?", audit / "pair_guide_reference.csv", "derived table",
         f"{len(ref)} features ({len(designed_ref)} designed slots: {designed_ref.scaffold.value_counts().to_dict()}; {int((ref.feature_role == 'wrong_scaffold_chimera_diagnostic').sum())} wrong-scaffold diagnostics; {int((ref.feature_role == 'non_cloned_spacer').sum())} non-cloned); pair_id = construct id(s) from the oligo workbook ({int((designed_ref.n_constructs > 1).sum())} slot features belong to >1 construct)",
         "explicit, document-derived construct map -> the pair module runs in explicit mode: a cell is a designed pair only when its strongest A and strongest C features share a construct id", "derived from experimental documents")

    # ============================================================================================
    # 6. Repository state
    # ============================================================================================
    g = {k: sh(cmd, cwd=repo).strip() for k, cmd in (("branch", "git rev-parse --abbrev-ref HEAD"), ("head", "git rev-parse HEAD"), ("status", "git status --short"), ("log", "git log --oneline -8"))}
    (audit / "repository_state.json").write_text(json.dumps(g, indent=1))

    # ============================================================================================
    # 7. Evidence matrix + experimental design record
    # ============================================================================================
    ev = pd.DataFrame(facts)
    ev.to_csv(audit / "evidence_matrix.csv", index=False)

    n_ntc_constructs = int((constructs.construct_type == "ntc_pair").sum())
    n_dual = int((constructs.construct_type == "dual_targeting_same_target").sum())
    n_s1 = int((constructs.construct_type == "targeting_plus_ntc").sum())
    n_diff = int((constructs.construct_type == "dual_targeting_DIFFERENT_targets").sum())
    s1_ntc = constructs.loc[constructs.construct_type == "targeting_plus_ntc", "position2_design_id"].unique().tolist()
    targets = sorted(set(constructs.loc[constructs.construct_type != "ntc_pair", "construct_target"]))
    rec = [
        f"# Experimental design record: Hanrui Fang dual-guide Perturb-seq (iteration 2)",
        "",
        f"Generated by SLURM job {JOB} on {NOW:%Y-%m-%d %H:%M} from the files in `{data}`. Every statement is tagged **[DOC]** (experimental document), **[FASTQ]** (derived from reads), **[CR]** (Cell Ranger output), **[INF]** (computational inference) or **[UNKNOWN]** (no source). The evidence matrix (`evidence_matrix.csv`) gives file / sheet / exact text for each fact.",
        "",
        "## Documents read",
        "",
        md_table(pd.DataFrame([{"file": p.name, "size_bytes": p.stat().st_size, "md5": md5(p), **props[p.name]} for p in (xl_design, xl_oligo, docx_scaf)])),
        "",
        "## Design record",
        "",
        "| # | Question | Answer | Evidence |",
        "|---|---|---|---|",
        f"| 1 | Are scaffold A and scaffold C physically used in the same construct? | **Yes.** Every oligo row carries a position-1 sgRNA followed by the start of Scaffold 1 (`{backbone[:10]}...`, read class **C**) and a position-2 sgRNA followed by the start of Scaffold 2 (`{blp}`, read class **A**). One vector = one C-scaffold guide + one A-scaffold guide. | [DOC] F07, F08, F11 |",
        f"| 2 | Is the experiment truly dual-guide? | **Yes.** {len(constructs)} constructs, all two-cassette: {n_dual} same-target dual-guide constructs (`<gene>_1F/_2F/_3F`), {n_s1} single-targeting constructs (`<gene>_S1`: targeting guide + NO-TARGET filler), {n_ntc_constructs} NTC-NTC constructs (`NO-TARGET_<n>F`); {n_diff} constructs combine two different targets. | [DOC] F10 |",
        "| 3 | Was one A+C pair per cell expected? | **Not stated.** No document gives the intended MOI or transduction scheme. One construct per cell is the natural expectation of a fixed-pair library but is **not documented**; observed multiplicity is reported and cells with several strong features per scaffold are labelled ambiguous, not forced into one pair. | [UNKNOWN] F16; [INF] observed multiplicity in the run reports |",
        "| 4 | Expected MOI? | **Not documented.** | [UNKNOWN] F16 |",
        f"| 5 | Exact A/C scaffold sequences | Scaffold 2 (class A) = `{scaf_doc['Scaffold 2']}`; Scaffold 1 (class C) = `{scaf_doc['Scaffold 1']}`. Reads match Scaffold 2 exactly over the sequenced 63 nt; Scaffold 1 differs from the reads at 2 adjacent positions (~53-54; identical in all 4 wells) -> probable typo in the document; counting anchors (first 12 nt) are identical in both sources. | [DOC] F08; [FASTQ] F14; `scaffold_audit.csv` |",
        f"| 6 | Official A-to-C pair map | **Provided**: `20250822_OligoPool_TwistAddG.xlsx`, one row per construct (`pair_mapping_audit.csv`, {len(constructs)} rows). Position 1 (C) and position 2 (A) spacers are 'G' + a designed 20-mer of `design_out_v2.xlsx` for all {2 * len(constructs)} slots. | [DOC] F06, F09 |",
        "| 7 | Is any same-target A+C combination valid? | **No.** The map fixes three specific (position-1, position-2) guide pairs per target; other same-target A x C combinations are not constructs and are labelled `unresolved_pair` (detail `same_target_not_designed`), excluded from primary testing and shown only as a sensitivity stratum. | [DOC] F10; rule = conservative reading of the map |",
        f"| 8 | How are NTC-NTC pairs defined? | The {n_ntc_constructs} `NO-TARGET_<n>F` constructs (two NO-TARGET spacers, consecutive rows of the design workbook). Only these designed NTC pairs form the `pair_non_targeting` control group. | [DOC] F10 |",
        f"| 9 | Are targeting+NTC cells valid constructs? | **Yes, for the {n_s1} designed `_S1` constructs** (position-1 targeting guide identical to the `_1F` position-1 guide + NO-TARGET guide `{s1_ntc}` in position 2). These are designed single-guide perturbations and are assigned to their target with status `pair_targeting_plus_ntc` (construct_type `targeting_plus_ntc`), reported separately from the dual-guide constructs. Any other targeting+NTC combination is `unresolved_pair`. | [DOC] F10 |",
        "| 10 | CRISPR modality and effector | **Not documented** (no Cas9 / dCas9-KRAB / dCas9-VPR statement). Results are reported as target-transcript depletion associations. | [UNKNOWN] F16 |",
        "| 11 | Cell line | **Not documented.** | [UNKNOWN] F16 |",
        "| 12 | Meaning of HF011A / HF011B / HF012A / HF012B | Four separate 10x 5' GEM wells (Cell Ranger 9.0.1, Single Cell 5' PE v3, GRCh38-2024-A), each with its own guide-capture library (HF0xxxF). The meaning of HF011 vs HF012 and A vs B is **not documented**; the sample manifest labels them `condition = well group` / `replicate = well letter` with `condition_status = well_id_derived_label_not_experimental_metadata`. | [CR] F15; [UNKNOWN] |",
        "| 13 | Biological vs technical replicate structure | **Unknown.** Cross-well agreement is reported as well-level support only, never as biological replication. | [UNKNOWN] F15 |",
        f"| 14 | Expected guide recovery / library representation | {n_cloned} of 560 designed spacers were cloned ({len(designed_ref)} scaffold-specific slot features); {560 - n_cloned} designed spacers (incl. all MIF-AS1 guides) are absent from the pool by design. No plasmid-pool NGS QC was supplied; representation is measured from the data (per-feature UMI / cell counts in the run reports). | [DOC] F12; [UNKNOWN] plasmid QC |",
        "| 15 | FASTQ read structure | Guide libraries (FB_OTHER_10X): R1 = 16 nt cell barcode + 12 nt UMI + TSO (TTTCTTATATGGG at ~29) + 0-4 non-templated bases (mostly G) + 20 nt protospacer (preceded in the transcript by the added 5' G) + scaffold (63 nt sequenced, then Illumina adapter); R2 = reverse complement. GEX libraries (SC_5PGEX_10X) processed by Cell Ranger. | [FASTQ] previous design audit `fastq_read_structure_audit.csv`; confirmed by F14 |",
        "| 16 | Guide-counting method and error correction | Streaming scaffold-aware counter: read must contain a scaffold anchor (exact 12-mer, class A or C) at >= position 40; protospacer = 20 nt immediately 5' of the anchor; exact match to the 560 designed 20-mers, else unambiguous 1-mismatch match, else +/-1 nt positional shift; UMI-deduplicated per (cell barcode, feature, UMI); cells = Cell Ranger filtered GEX barcodes. **New in iteration 2:** features are (designed spacer x scaffold class), so the NO-TARGET_1 spacer is counted separately with each scaffold and wrong-scaffold reads become explicit off-design features. | [INF] pipeline code + config |",
        "",
        "## Consequences for the analysis",
        "",
        "- The pair module runs in **explicit** mode with the construct ids as `pair_id` (a slot feature may belong to several constructs, e.g. `ACYP1_1:C` -> `ACYP1_1F;ACYP1_S1`).",
        "- Primary perturbation label of a cell = the designed construct shared by its strongest A and strongest C feature. `pair_targeting` (dual-guide constructs) and `pair_targeting_plus_ntc` (designed `_S1` constructs) are both valid targeting labels and are reported separately (construct_type) as well as pooled per target.",
        "- `pair_non_targeting` = designed NTC-NTC constructs only.",
        "- Not designed: same-target non-construct combinations, targeting+NTC other than `_S1`, NTC+NTC other than the 63 constructs -> `unresolved_pair` (with `pair_resolution_detail`); two different targets -> `dual_target_ambiguous`. One slot only -> `incomplete_pair`; several strong features in a slot -> `ambiguous_scaffold_*`. None of these enters primary testing.",
        "- `min_umi` stays at the default 3 (no document justifies a different threshold).",
        "",
        "## Open questions (do not block the analysis)",
        "",
        "1. Intended MOI / constructs per cell.", "2. CRISPR modality, effector and cell line.", "3. Meaning of HF011 vs HF012 and A vs B (biological vs technical replicates).",
        "4. Confirmation of the Scaffold 1 sequence at positions ~53-54 (document vs reads).", "5. Plasmid-pool representation QC.",
        "",
        "## Construct map (from the oligo workbook)",
        "",
        md_table(constructs[["construct_id", "construct_type", "construct_target", "position1_design_id", "position1_scaffold_class", "position2_design_id", "position2_scaffold_class", "excel_row", "name_anomaly"]]),
        "",
        "## Constructs per target", "", md_table(per_target),
        "",
        "## Scaffold audit", "", md_table(scaffold_audit[["item", "scaffold_class", "length", "n_mismatches_over_compared_length", "mismatch_positions_vs_document", "evidence_type"]]),
        "",
        "## Evidence matrix", "", md_table(ev[["fact_id", "question", "worksheet_or_section", "interpretation", "evidence_type", "status"]]),
    ]
    md = "\n".join(rec) + "\n"
    (audit / "experimental_design_audit.md").write_text(md)
    (audit / "experimental_design_audit.html").write_text(md_to_html(md, "Experimental design record (Hanrui Fang, iteration 2)"))

    # ============================================================================================
    # 8. Previous vs new: reference-level comparison (part 1; run-level part appended after the runs)
    # ============================================================================================
    prev_cfg = (prev / "config_used.yaml").read_text() if (prev / "config_used.yaml").is_file() else ""
    cmp_rows = [
        {"aspect": "pairing source", "previous_run": "no pair ids; provisional same-target rule (any A x C of the same target)", "new_run": f"explicit construct map from {xl_oligo.name} ({len(constructs)} constructs)"},
        {"aspect": "scaffold per guide", "previous_run": "empirical majority scaffold of matched reads (purity >= 0.9)", "new_run": "from the oligo backbone / BlpI columns (position 1 -> Scaffold 1 = C, position 2 -> Scaffold 2 = A); agrees with the empirical class for every observed cloned guide"},
        {"aspect": "count-matrix features", "previous_run": "560 designed spacers (scaffold-agnostic)", "new_run": f"{len(ref)} = 560 spacers x 2 scaffold classes ({len(designed_ref)} designed slots; NO-TARGET_1 has one slot per scaffold)"},
        {"aspect": "targeting+NTC cells", "previous_run": "all labelled pair_targeting_plus_ntc and excluded (ambiguous)", "new_run": f"designed _S1 constructs ({n_s1}) = valid targeting label (reported separately); other combinations unresolved"},
        {"aspect": "same-target non-designed pairs", "previous_run": "accepted as pair_targeting", "new_run": "unresolved_pair (sensitivity stratum only)"},
        {"aspect": "NTC pairs", "previous_run": "any two NO-TARGET guides (A + C)", "new_run": f"only the {n_ntc_constructs} designed NO-TARGET_<n>F constructs"},
        {"aspect": "guides never observed", "previous_run": "144-159 'unknown scaffold' guides, unexplained", "new_run": f"{560 - n_cloned} designed spacers were never cloned (oligo pool) -> expected absence"},
        {"aspect": "scaffold sequences", "previous_run": "consensus from reads only", "new_run": "documented in Scaffold_seq.docx; class C document sequence differs from reads at 2 positions (probable typo)"},
        {"aspect": "MOI / modality / cell line / replicate meaning", "previous_run": "unknown", "new_run": "still unknown (not in the new documents)"},
    ]
    cmp_df = pd.DataFrame(cmp_rows)
    cmp_df.to_csv(audit / "previous_vs_new_reference_comparison.csv", index=False)
    part1 = ["# Previous versus new analysis", "", f"Part 1 (reference level, SLURM job {JOB}, {NOW:%Y-%m-%d %H:%M}); part 2 (run-level results) is appended by the root-report job.", "",
             f"Previous run: `{prev}` (not modified). New run: `{out}`.", "", md_table(cmp_df), "",
             "## Scaffold agreement per cloned guide (document vs previous empirical class)", "", md_table(gaudit[gaudit.in_oligo_pool].design_vs_previous_empirical_scaffold.value_counts().rename_axis("agreement").reset_index(name="n_guides")), ""]
    (audit / "previous_vs_new_analysis.md").write_text("\n".join(part1) + "\n")

    # ============================================================================================
    # 9. Short initial-audit summary
    # ============================================================================================
    summary = [f"# Initial audit summary (SLURM {JOB}, {NOW:%Y-%m-%d %H:%M})", "",
               f"- files inventoried: {len(inv)} (`data_inventory.csv`); experimental documents: {len(docs)}; USB folders: {len(usb)}",
               f"- constructs: {len(constructs)} ({constructs.construct_type.value_counts().to_dict()}); targets with constructs: {len(targets)}",
               f"- designed spacers cloned: {n_cloned}/560; slot features: {len(designed_ref)}; spacer with both scaffolds: {n_both}",
               f"- scaffold class agreement (document vs previous empirical): {gaudit[gaudit.in_oligo_pool].design_vs_previous_empirical_scaffold.value_counts().to_dict()}",
               f"- sample manifest written to `{man_path}`",
               f"- repository: {g['branch']} @ {g['head']}", "", "Outputs: experimental_design_audit.md/.html, evidence_matrix.csv, pair_guide_reference.csv, pair_mapping_audit.csv, scaffold_audit.csv, guide_reference_audit.csv, sample_metadata_audit.csv, data_inventory.csv, previous_vs_new_analysis.md"]
    (audit / "initial_audit_summary.md").write_text("\n".join(summary) + "\n")
    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
