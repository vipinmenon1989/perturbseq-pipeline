"""Root report over several completed pair-guide runs (per-sample + combined).

``perturbseq-pipeline pair-report -c cfg.yaml --run HF011A=... --run combined=... -o ROOT
[--audit-dir ROOT/audit] [--previous-run OLD_ROOT] [--job-ids 1,2,3] [--base-commit SHA]``

writes a FULL analysis report in two formats (``ROOT/report.md`` and
``ROOT/report.html``; 21 sections: experimental information, inventory, sample
structure, guide design / pairing model, scaffold evidence, expression QC before
and after filtering, pair-guide QC, ambiguity, PCA / UMAP / Leiden, ECDF,
perturbation-expression, FDR / log2FC, per-sample and combined results, target
support, previous-vs-new comparison, limitations, reproducibility), plus
``run_manifest.json``, ``execution_commands.md``, ``config_used.yaml``,
``README.md`` and cross-run tables under ``ROOT/tables``. The per-run reports are
linked, key figures are inlined (HTML) or referenced by relative path (Markdown).
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml

from . import dual_guides as dg
from .config import Config
from .report_markdown import md_table

logger = logging.getLogger(__name__)

_CSS = ("body{font-family:system-ui,sans-serif;margin:24px;max-width:1500px;color:#222;line-height:1.35}table.t{border-collapse:collapse;font-size:11px}"
        "table.t td,table.t th{border:1px solid #ddd;padding:2px 6px;vertical-align:top}figure{margin:10px 0}figcaption{font-size:10px;color:#666}"
        "h2{border-bottom:1px solid #ccc;margin-top:36px}h3{margin-top:24px}.warn{background:#fff4e5;padding:8px;border-left:4px solid #eda100}"
        ".tag{display:inline-block;padding:0 5px;border-radius:3px;font-size:10px;background:#eef}nav a{margin-right:10px;font-size:12px}code{background:#f3f3f3;padding:1px 3px}"
        "pre{background:#f7f7f7;padding:8px;overflow:auto;font-size:11px;max-height:600px}")

Block = Tuple[str, object]  # ("md", text) | ("table", (df, max_rows)) | ("fig", (path, caption)) | ("pre", text)


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------


def _csv(run_dir: Path, name: str) -> Optional[pd.DataFrame]:
    p = Path(run_dir) / "tables" / f"{name}.csv"
    return pd.read_csv(p) if p.is_file() else None


def _acsv(audit_dir: Optional[Path], name: str, **kw) -> Optional[pd.DataFrame]:
    if audit_dir is None:
        return None
    p = Path(audit_dir) / name
    return pd.read_csv(p, **kw) if p.is_file() else None


def _concat(run_dirs: Dict[str, Path], name: str) -> pd.DataFrame:
    parts = []
    for k, d in run_dirs.items():
        df = _csv(d, name)
        if df is not None and len(df):
            parts.append(df.assign(run=k))
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def _git(repo: Path, base_commit: Optional[str]) -> Dict[str, str]:
    out = {}
    cmds = {"branch": ["git", "rev-parse", "--abbrev-ref", "HEAD"], "commit": ["git", "rev-parse", "HEAD"], "status": ["git", "status", "--short"],
            "log": ["git", "log", "--oneline", "-8"]}
    if base_commit:
        cmds["diff_stat_vs_base"] = ["git", "diff", "--stat", base_commit, "--"]
        cmds["changed_files_vs_base"] = ["git", "diff", "--name-status", base_commit, "--"]
    for k, cmd in cmds.items():
        try:
            out[k] = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=False).stdout.strip()
        except Exception as exc:  # pragma: no cover
            out[k] = f"n/a ({exc})"
    return out


def _sacct(job_ids: List[str]) -> pd.DataFrame:
    ids = [j.strip() for j in job_ids if j.strip()]
    if not ids or shutil.which("sacct") is None:
        return pd.DataFrame()
    fmt = "JobID,JobName,State,Start,End,Elapsed,NodeList,AllocCPUS,ReqMem,MaxRSS,ExitCode"
    try:
        txt = subprocess.run(["sacct", "-j", ",".join(ids), "-P", "-o", fmt], capture_output=True, text=True, check=False).stdout
    except Exception:  # pragma: no cover
        return pd.DataFrame()
    rows = [l.split("|") for l in txt.strip().splitlines()]
    if len(rows) < 2:
        return pd.DataFrame()
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df[~df["JobID"].str.contains(r"\.(extern|batch)$")]


def _versions() -> Dict[str, str]:
    mods = ["perturbseq_pipeline", "scanpy", "anndata", "numpy", "pandas", "scipy", "sklearn", "leidenalg", "igraph", "umap", "matplotlib", "h5py", "numba", "statsmodels", "pynndescent", "docx", "openpyxl", "markdown_it"]
    out = {"python": sys.version.split()[0]}
    for m in mods:
        try:
            mod = __import__(m)
            out[m] = str(getattr(mod, "__version__", "installed"))
        except Exception:
            out[m] = "not installed"
    return out


def _num(x, fmt="{:,}"):
    try:
        return fmt.format(int(x))
    except Exception:
        return str(x)


def _pct(a, b):
    try:
        return f"{100.0 * float(a) / float(b):.1f} %"
    except Exception:
        return "n/a"


# ---------------------------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------------------------


def _render_md(sections: List[Tuple[str, List[Block]]], outdir: Path, title: str, intro: str) -> str:
    L = [f"# {title}", "", intro, "", "## Contents", ""]
    L += [f"{i}. [{t}](#{i}-{re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')})" for i, (t, _) in enumerate(sections, 1)] + [""]
    for i, (t, blocks) in enumerate(sections, 1):
        L += [f"## {i}. {t}", ""]
        for kind, payload in blocks:
            if kind == "md":
                L += [str(payload), ""]
            elif kind == "table":
                df, n = payload
                L += [md_table(df, n), ""]
            elif kind == "fig":
                path, cap = payload
                path = Path(path)
                if path.is_file():
                    L += [f"![{cap}]({os.path.relpath(path, outdir)})", "", f"_{cap}_", ""]
                else:
                    L += [f"_missing figure: {os.path.relpath(path, outdir)}_", ""]
            elif kind == "pre":
                L += ["```", str(payload), "```", ""]
    return "\n".join(L) + "\n"


def _md_inline_html(text: str) -> str:
    """Minimal Markdown -> HTML for prose blocks (paragraphs, bullet lists, inline code / bold / links)."""
    try:
        from markdown_it import MarkdownIt
        return MarkdownIt("commonmark").enable("table").render(text)
    except Exception:  # pragma: no cover
        esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return "<p>" + esc.replace("\n\n", "</p><p>").replace("\n", "<br>") + "</p>"


def _render_html(sections: List[Tuple[str, List[Block]]], outdir: Path, title: str, intro: str) -> str:
    parts = [f"<html><head><meta charset='utf-8'><title>{title}</title><style>{_CSS}</style></head><body>", f"<h1>{title}</h1>", _md_inline_html(intro),
             "<nav>" + "".join(f"<a href='#s{i}'>{i}. {t}</a>" for i, (t, _) in enumerate(sections, 1)) + "</nav>"]
    for i, (t, blocks) in enumerate(sections, 1):
        parts.append(f"<h2 id='s{i}'>{i}. {t}</h2>")
        for kind, payload in blocks:
            if kind == "md":
                parts.append(_md_inline_html(str(payload)))
            elif kind == "table":
                df, n = payload
                if df is None or not len(df):
                    parts.append("<p><i>not available</i></p>")
                else:
                    d = df.head(n)
                    parts.append(d.to_html(index=False, float_format=lambda x: f"{x:.4g}", classes="t", border=0, na_rep="", escape=True))
                    if len(df) > n:
                        parts.append(f"<p style='font-size:11px;color:#666'>showing {n} of {len(df)} rows; full table in tables/</p>")
            elif kind == "fig":
                path, cap = payload
                path = Path(path)
                if path.is_file() and path.stat().st_size > 0:
                    b = base64.b64encode(path.read_bytes()).decode()
                    parts.append(f"<figure><img src='data:image/png;base64,{b}' style='max-width:100%'><figcaption>{cap} &mdash; <code>{os.path.relpath(path, outdir)}</code></figcaption></figure>")
                else:
                    parts.append(f"<p class='warn'>missing figure {os.path.relpath(path, outdir)}</p>")
            elif kind == "pre":
                esc = str(payload).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                parts.append(f"<pre>{esc}</pre>")
    parts.append("</body></html>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------------------------
# main builder
# ---------------------------------------------------------------------------------------------


def build_root_report(cfg: Config, runs: Dict[str, str], outdir: Path, audit_dir: Optional[Path] = None, config_path: Optional[str] = None,
                      job_ids: Optional[List[str]] = None, previous_run: Optional[Path] = None, base_commit: Optional[str] = None,
                      slurm_dir: Optional[Path] = None) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "tables").mkdir(exist_ok=True)
    run_dirs = {k: Path(v) for k, v in runs.items()}
    comb_key = "combined" if "combined" in run_dirs else list(run_dirs)[-1]
    samples = [k for k in run_dirs if k != comb_key]
    repo = Path(__file__).resolve().parents[2]
    git = _git(repo, base_commit)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    audit_dir = Path(audit_dir) if audit_dir else None
    slurm_dir = Path(slurm_dir) if slurm_dir else outdir / "slurm"
    previous_run = Path(previous_run) if previous_run else None
    job_ids = [j for j in (job_ids or []) if j]

    def fig(k, rel, cap=None):
        p = run_dirs[k] / "figures" / rel
        return ("fig", (p, cap or f"{k}: {Path(rel).stem.replace('_', ' ')}"))

    def tab(df, n=60):
        return ("table", (df, n))

    def run_link_md(k):
        return f"[{k}]({os.path.relpath(run_dirs[k] / 'report.html', outdir)}) / [{k} (Markdown)]({os.path.relpath(run_dirs[k] / 'report.md', outdir)})"

    # ---- gather run tables -------------------------------------------------------------------
    cc = _concat(run_dirs, "cell_counts_before_after")
    qcm = _concat(run_dirs, "qc_metrics_per_lane_before_after")
    pa = _concat(run_dirs, "pair_assignment_per_lane")
    pq = _concat(run_dirs, "pair_guide_qc_per_lane")
    det = _concat(run_dirs, "pair_resolution_detail_per_lane")
    ctl = _concat(run_dirs, "construct_type_per_lane")
    odf = _concat(run_dirs, "off_design_umi_fraction_per_lane")
    strong = _concat(run_dirs, "strong_guides_per_scaffold_per_lane")
    hc = _concat(run_dirs, "pair_perturbation_hit_counts_per_lane")
    prim = {k: _csv(run_dirs[k], "pair_perturbation_primary") for k in run_dirs}
    byt = {k: _csv(run_dirs[k], "pair_perturbation_by_target") for k in run_dirs}
    bypair = {k: _csv(run_dirs[k], "pair_perturbation_by_pair") for k in run_dirs}
    sg = _concat(run_dirs, "single_guide_diagnostic_vs_pair")
    clusters = _concat(run_dirs, "cluster_sizes")
    tcells = _concat(run_dirs, "target_cells_per_lane")
    constructs_cells = _concat(run_dirs, "construct_cells_per_lane")
    overlap = _concat(run_dirs, "guide_gex_barcode_overlap")
    feat = _csv(run_dirs[comb_key], "guide_feature_representation")

    # ---- cross-run target support -----------------------------------------------------------
    targets = sorted(set().union(*[set(df["target_gene"]) for df in prim.values() if df is not None]))
    rows = []
    for t in targets:
        r = {"target_gene": t}
        n_t = n_h = 0
        for k in samples:
            df = prim.get(k)
            sub = df[(df.target_gene == t) & (df.lane_id != "ALL")] if df is not None else pd.DataFrame()
            if len(sub) and pd.notna(sub["log2fc"].iloc[0]):
                h = bool(sub["is_hit"].iloc[0]); n_t += 1; n_h += h
                r[f"{k}_hit"], r[f"{k}_log2fc"], r[f"{k}_fdr_ks"], r[f"{k}_n_pair_cells"] = h, float(sub["log2fc"].iloc[0]), float(sub["fdr_ks"].iloc[0]), int(sub["n_target_pair_cells"].iloc[0])
            else:
                r[f"{k}_hit"] = None
        r["n_samples_tested"], r["n_samples_hit"] = n_t, n_h
        dfc = prim.get(comb_key)
        pool = dfc[(dfc.target_gene == t) & (dfc.lane_id == "ALL")] if dfc is not None else pd.DataFrame()
        if len(pool) and pd.notna(pool["log2fc"].iloc[0]):
            r["combined_hit"], r["combined_log2fc"], r["combined_fdr_ks"], r["combined_neg_log10_fdr"] = bool(pool["is_hit"].iloc[0]), float(pool["log2fc"].iloc[0]), float(pool["fdr_ks"].iloc[0]), float(pool["neg_log10_fdr"].iloc[0])
            r["combined_n_pair_cells"] = int(pool["n_target_pair_cells"].iloc[0])
        else:
            r["combined_hit"] = None
        bt = byt.get(comb_key)
        if bt is not None:
            for stratum in sorted(set(bt["assignment_stratum"]) - {"primary_pair_targeting"}):
                s2 = bt[(bt.target_gene == t) & (bt.control == "ntc") & (bt.assignment_stratum == stratum) & (bt.lane_id == "ALL")]
                r[f"combined_{stratum}_hit"] = bool(s2["is_hit"].iloc[0]) if len(s2) and pd.notna(s2["log2fc"].iloc[0]) else None
                r[f"combined_{stratum}_log2fc"] = float(s2["log2fc"].iloc[0]) if len(s2) and pd.notna(s2["log2fc"].iloc[0]) else None
        r["well_level_support"] = f"{n_h}/{n_t} per-sample runs" if n_t else "not tested per sample"
        ch = r.get("combined_hit")
        r["support_class"] = ("depletion in all tested per-sample runs and combined" if n_t >= 2 and n_h == n_t and ch
                              else "depletion in some per-sample runs and combined" if ch and n_h > 0
                              else "combined only" if ch else "per-sample only" if n_h > 0
                              else "no depletion association" if (n_t or ch is not None) else "not tested")
        r["biological_replicate_evidence"] = "not available: the documents do not define HF011/HF012 or A/B; well-level support only"
        rows.append(r)
    support = pd.DataFrame(rows)
    support.to_csv(outdir / "tables" / "target_support_matrix_across_runs.csv", index=False)
    for name, df in (("cell_counts_before_after_all_runs", cc), ("qc_metrics_before_after_all_runs", qcm), ("pair_assignment_per_lane_all_runs", pa), ("pair_guide_qc_all_runs", pq),
                     ("pair_resolution_detail_all_runs", det), ("construct_type_all_runs", ctl), ("off_design_umi_fraction_all_runs", odf), ("strong_guides_per_scaffold_all_runs", strong),
                     ("pair_perturbation_hit_counts_all_runs", hc), ("single_guide_diagnostic_all_runs", sg), ("cluster_sizes_all_runs", clusters), ("target_cells_all_runs", tcells),
                     ("construct_cells_all_runs", constructs_cells), ("guide_gex_barcode_overlap_all_runs", overlap)):
        if len(df):
            df.to_csv(outdir / "tables" / f"{name}.csv", index=False)
    prim_all = pd.concat([v.assign(run=k) for k, v in prim.items() if v is not None], ignore_index=True) if any(v is not None for v in prim.values()) else pd.DataFrame()
    if len(prim_all):
        prim_all.to_csv(outdir / "tables" / "pair_perturbation_primary_all_runs.csv", index=False)
    pairs_all = pd.concat([v.assign(run=k) for k, v in bypair.items() if v is not None], ignore_index=True) if any(v is not None for v in bypair.values()) else pd.DataFrame()
    if len(pairs_all):
        pairs_all.to_csv(outdir / "tables" / "pair_perturbation_by_pair_all_runs.csv", index=False)

    # ---- audit tables -------------------------------------------------------------------------
    def _first(*names, **kw):
        for nm in names:
            df = _acsv(audit_dir, nm, **kw)
            if df is not None:
                return df
        return None

    ev = _acsv(audit_dir, "evidence_matrix.csv", dtype=str, keep_default_na=False)
    inv = _first("source_file_inventory.csv", "data_inventory.csv")
    smeta = _acsv(audit_dir, "sample_metadata_audit.csv", dtype=str, keep_default_na=False)
    cmap = _first("construct_pair_map_used.csv", "pair_mapping_audit.csv", dtype=str, keep_default_na=False)
    cpt = _acsv(audit_dir, "constructs_per_target.csv", dtype=str, keep_default_na=False)
    scaf = _acsv(audit_dir, "scaffold_audit.csv", dtype=str, keep_default_na=False)
    ref = _first("guide_reference_used.csv", "pair_guide_reference.csv", dtype=str, keep_default_na=False)
    gaud = _acsv(audit_dir, "guide_reference_audit.csv", dtype=str, keep_default_na=False)
    funnel = _acsv(audit_dir, "guide_read_retention_funnel.csv")
    quant = _acsv(audit_dir, "guide_quantification_summary.csv")
    offd = _acsv(audit_dir, "off_design_feature_summary.csv")
    design_path = next((audit_dir / nm for nm in ("experimental_information_used.md", "experimental_design_audit.md") if audit_dir and (audit_dir / nm).is_file()), None)
    design_md = design_path.read_text() if design_path else ""
    what_changed = design_md.split("## What the confirmed experimental information changed")[1].split("\n## ")[0].strip() if "## What the confirmed experimental information changed" in design_md else ""
    rules_md = design_md.split("## Iteration-3 assignment rules")[1].split("\n## ")[0].strip() if "## Iteration-3 assignment rules" in design_md else ""
    design_record = design_md.split("## What the confirmed experimental information changed")[0].split("## Consequences for the analysis")[0].split("## Design record")[-1].strip() if design_md else ""
    consequences = design_md.split("## Consequences for the analysis")[1].split("## Open questions")[0].strip() if "## Consequences for the analysis" in design_md else ""
    consequences = consequences.split("\n", 1)[1].strip() if consequences.startswith("(iteration-2 wording") else consequences
    open_q = design_md.split("## Open questions (do not block the analysis)")[1].split("## Construct map")[0].strip() if "## Open questions" in design_md else ""
    docs = inv[inv["class"] == "experimental_document"][["relative_path", "size_bytes", "mtime", "md5"]] if inv is not None else None

    # ---- headline numbers ----------------------------------------------------------------------
    comb_cc = cc[(cc.run == comb_key)].set_index("lane_id") if len(cc) else pd.DataFrame()
    comb_pa = pa[(pa.run == comb_key)].set_index("lane_id") if len(pa) else pd.DataFrame()
    comb_hc = hc[(hc.run == comb_key)].set_index("lane_id") if len(hc) else pd.DataFrame()
    n_in = int(comb_cc.loc["ALL", "input_cells"]) if "ALL" in comb_cc.index else None
    n_ret = int(comb_cc.loc["ALL", "final_cells_retained"]) if "ALL" in comb_cc.index else None
    st_cols = [c for c in dg.PAIR_STATUS_ORDER if c in comb_pa.columns]

    def st(k):
        return int(comb_pa.loc["ALL", k]) if ("ALL" in comb_pa.index and k in comb_pa.columns) else 0

    n_t, n_tn, n_n = st(dg.STATUS_PAIR_TARGETING), st(dg.STATUS_PAIR_TARGET_NTC), st(dg.STATUS_PAIR_NTC)
    n_amb = sum(st(k) for k in st_cols if k not in (dg.STATUS_PAIR_TARGETING, dg.STATUS_PAIR_TARGET_NTC, dg.STATUS_PAIR_NTC, dg.STATUS_NO_GUIDE, dg.STATUS_BELOW_MIN_UMI))
    tested_c = int(comb_hc.loc["ALL", "targets_tested"]) if "ALL" in comb_hc.index else 0
    hit_c = int(comb_hc.loc["ALL", "targets_hit"]) if "ALL" in comb_hc.index else 0
    per_sample_hits = {k: (int(hc[(hc.run == k) & (hc.lane_id == k)]["targets_hit"].iloc[0]), int(hc[(hc.run == k) & (hc.lane_id == k)]["targets_tested"].iloc[0])) for k in samples if len(hc[(hc.run == k) & (hc.lane_id == k)])}
    support_counts = support["support_class"].value_counts().to_dict() if len(support) else {}
    explicit = ref is not None and "pair_id" in ref.columns and (ref["pair_id"] != "").any()
    n_constructs = len(cmap) if cmap is not None else 0
    ctype_counts = cmap["construct_type"].value_counts().to_dict() if cmap is not None else {}

    s1_primary = bool(getattr(cfg.guides, "designed_targeting_plus_ntc_primary", True))
    # ---- previous run comparison ------------------------------------------------------------------
    prev_blocks: List[Block] = []
    prev_cmp_rows = []
    if previous_run and previous_run.is_dir():
        p_pa = pd.read_csv(previous_run / "tables" / "pair_assignment_per_lane_all_runs.csv") if (previous_run / "tables" / "pair_assignment_per_lane_all_runs.csv").is_file() else pd.DataFrame()
        p_hc = pd.read_csv(previous_run / "tables" / "pair_perturbation_hit_counts_all_runs.csv") if (previous_run / "tables" / "pair_perturbation_hit_counts_all_runs.csv").is_file() else pd.DataFrame()
        p_sup = pd.read_csv(previous_run / "tables" / "target_support_matrix_across_runs.csv") if (previous_run / "tables" / "target_support_matrix_across_runs.csv").is_file() else pd.DataFrame()
        p_cc = pd.read_csv(previous_run / "tables" / "cell_counts_before_after_all_runs.csv") if (previous_run / "tables" / "cell_counts_before_after_all_runs.csv").is_file() else pd.DataFrame()

        def prev_st(k):
            sub = p_pa[(p_pa.run == "combined") & (p_pa.lane_id == "ALL")] if len(p_pa) else pd.DataFrame()
            return int(sub[k].iloc[0]) if len(sub) and k in sub.columns else None

        prev_n = int(p_cc[(p_cc.run == "combined") & (p_cc.lane_id == "ALL")]["final_cells_retained"].iloc[0]) if len(p_cc) else None
        for label, key in (("pair_targeting (dual-guide designed construct)", dg.STATUS_PAIR_TARGETING), ("pair_targeting_plus_ntc", dg.STATUS_PAIR_TARGET_NTC), ("pair_non_targeting", dg.STATUS_PAIR_NTC),
                           ("dual_target_ambiguous", dg.STATUS_DUAL_TARGET), ("unresolved_pair", dg.STATUS_UNRESOLVED), ("incomplete_pair", dg.STATUS_INCOMPLETE),
                           ("ambiguous_scaffold_A", "ambiguous_scaffold_A"), ("ambiguous_scaffold_C", "ambiguous_scaffold_C"), ("ambiguous_scaffold_A_and_C", "ambiguous_scaffold_A_and_C"), ("no_guide", dg.STATUS_NO_GUIDE), ("below_min_umi", dg.STATUS_BELOW_MIN_UMI)):
            pv, nv = prev_st(key), st(key)
            prev_cmp_rows.append({"quantity": label, "previous_run": pv, "previous_pct": _pct(pv, prev_n) if pv is not None and prev_n else "", "new_run": nv, "new_pct": _pct(nv, n_ret) if n_ret else "",
                                  "note": {"pair_targeting_plus_ntc": "designed _S1 constructs: primary targeting label in full_2; sensitivity stratum (class ambiguous) in full_3" if not s1_primary else "designed _S1 constructs (primary targeting label)"}.get(label, "same rule in both runs" if previous_run and "full_2" in str(previous_run) else "")})
        prev_cmp_rows.insert(0, {"quantity": "QC-pass cells (combined)", "previous_run": prev_n, "previous_pct": "", "new_run": n_ret, "new_pct": "", "note": "same GEX matrices and QC thresholds"})
        p_comb_hc = p_hc[(p_hc.run == "combined") & (p_hc.lane_id == "ALL")] if len(p_hc) else pd.DataFrame()
        prev_cmp_rows.append({"quantity": "targets tested (combined, primary)", "previous_run": int(p_comb_hc["targets_tested"].iloc[0]) if len(p_comb_hc) else None, "previous_pct": "", "new_run": tested_c, "new_pct": "", "note": ""})
        prev_cmp_rows.append({"quantity": "targets with depletion association (combined, primary)", "previous_run": int(p_comb_hc["targets_hit"].iloc[0]) if len(p_comb_hc) else None, "previous_pct": "", "new_run": hit_c, "new_pct": "", "note": ""})
        if len(p_sup) and len(support):
            m = p_sup[["target_gene", "combined_hit", "combined_log2fc", "support_class"]].merge(support[["target_gene", "combined_hit", "combined_log2fc", "support_class"]], on="target_gene", how="outer", suffixes=("_previous", "_new"))
            m["agreement"] = ["same" if a == b else "changed" for a, b in zip(m["combined_hit_previous"], m["combined_hit_new"])]
            m.to_csv(outdir / "tables" / "previous_vs_new_target_hits.csv", index=False)
            prev_cmp_rows.append({"quantity": "targets with identical combined hit call", "previous_run": "", "previous_pct": "", "new_run": int((m["agreement"] == "same").sum()), "new_pct": f"of {len(m)} targets", "note": "tables/previous_vs_new_target_hits.csv"})
            prev_blocks.append(("md", "Target-level agreement of the combined hit call (primary stratum) between the previous and the new run:"))
            prev_blocks.append(tab(m.sort_values("agreement"), 80))
    prev_cmp = pd.DataFrame(prev_cmp_rows)
    if len(prev_cmp):
        prev_cmp.to_csv(outdir / "tables" / "previous_vs_new_summary.csv", index=False)
    ref_cmp = _acsv(audit_dir, "previous_vs_new_reference_comparison.csv", dtype=str, keep_default_na=False)

    # ---- execution information ---------------------------------------------------------------------
    sacct = _sacct(job_ids)
    versions = _versions()
    slurm_scripts = sorted(slurm_dir.glob("*.slurm")) if slurm_dir.is_dir() else []
    ledger = (slurm_dir / "job_ids.txt").read_text() if (slurm_dir / "job_ids.txt").is_file() else ""
    resolved_cfg = (run_dirs[comb_key] / "logs" / "resolved_config.yaml").read_text() if (run_dirs[comb_key] / "logs" / "resolved_config.yaml").is_file() else ""
    run_logs = {k: (run_dirs[k] / "logs" / "run.log") for k in run_dirs}
    run_times = {}
    for k, lp in run_logs.items():
        if lp.is_file():
            lines = lp.read_text(errors="ignore").splitlines()
            ts = [re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", l) for l in lines]
            ts = [m.group(1) for m in ts if m]
            run_times[k] = {"start": ts[0] if ts else "", "end": ts[-1] if ts else "", "log": str(lp)}
    warnings_found = {}
    for k, lp in run_logs.items():
        if lp.is_file():
            w = [l for l in lp.read_text(errors="ignore").splitlines() if "WARNING" in l or "ERROR" in l]
            warnings_found[k] = w[:40]

    manifest = {
        "generated": now, "report": "root pair-guide analysis report (iteration 2, explicit construct map)", "git_branch": git["branch"], "git_commit": git["commit"], "git_base_commit": base_commit,
        "git_status_short": git["status"], "git_changed_files_vs_base": git.get("changed_files_vs_base", ""), "config": config_path, "runs": {k: str(v) for k, v in run_dirs.items()},
        "run_times": run_times, "slurm_job_ids": job_ids, "slurm_ledger": ledger, "slurm_accounting": sacct.to_dict(orient="records") if len(sacct) else [],
        "conda_env": os.environ.get("CONDA_DEFAULT_ENV", ""), "conda_prefix": os.environ.get("CONDA_PREFIX", ""), "python_executable": sys.executable, "versions": versions,
        "assignment_mode": cfg.guides.assignment_mode, "pair_reference": cfg.guides.pair_map_file or cfg.guides.pair_reference, "pair_reference_explicit_ids": bool(explicit),
        "designed_targeting_plus_ntc_primary": s1_primary, "slot_rule": f"top_umi >= {cfg.guides.min_umi} and (top_umi + {getattr(cfg.guides, 'dominance_pseudocount', 1.0):g}) / (second_umi + {getattr(cfg.guides, 'dominance_pseudocount', 1.0):g}) >= {cfg.guides.dominance_ratio:g}, per scaffold slot",
        "batch_key": cfg.cluster.batch_key, "harmony": False if cfg.cluster.batch_key is None else True,
        "disabled_modules": {k: getattr(cfg, k).enabled for k in ("ps_score", "lochness", "modules", "distance", "distance_space", "meta_analysis")},
        "inputs": {"gex_mtx_dirs": cfg.input.mtx_dirs, "guide_mtx_dirs": cfg.input.guide_mtx_dirs, "metadata_file": cfg.metadata.file},
        "outputs": {"root": str(outdir), "report_html": str(outdir / "report.html"), "report_md": str(outdir / "report.md"), "audit_dir": str(audit_dir) if audit_dir else None, "previous_run_compared": str(previous_run) if previous_run else None},
        "headline": {"input_cells_combined": n_in, "qc_pass_cells_combined": n_ret, "pair_targeting": n_t, "pair_targeting_plus_ntc": n_tn, "pair_non_targeting": n_n, "ambiguous_or_unresolved": n_amb,
                     "targets_tested_combined": tested_c, "targets_hit_combined": hit_c, "per_sample_hits_tested": per_sample_hits, "support_classes": support_counts, "constructs": n_constructs, "construct_types": ctype_counts},
        "warnings_in_run_logs": warnings_found,
    }
    (outdir / "run_manifest.json").write_text(json.dumps(manifest, indent=1, default=str))
    if config_path:
        shutil.copy(config_path, outdir / "config_used.yaml")

    exec_md = [f"# Execution record: {cfg.run.name}", "", f"Generated {now}. Branch `{git['branch']}`, commit `{git['commit']}`" + (f" (base commit at task start `{base_commit}`)" if base_commit else "") + ".", "",
               "## Configuration", "", f"- config: `{config_path}` (copied to `config_used.yaml`)", f"- pair reference: `{cfg.guides.pair_map_file or cfg.guides.pair_reference}`", f"- sample manifest: `{cfg.metadata.file}`", "",
               "## Inputs", ""] + [f"- GEX {k}: `{v}`" for k, v in (cfg.input.mtx_dirs or {}).items()] + [f"- guide counts {k}: `{v}`" for k, v in (cfg.input.guide_mtx_dirs or {}).items()] + ["",
               "## Outputs", "", f"- root: `{outdir}`"] + [f"- {k}: `{v}`" for k, v in run_dirs.items()] + ["",
               "## Pipeline commands", "", "```bash"] + [f"perturbseq-pipeline run -c {config_path} --lane {k}" for k in samples] + [f"perturbseq-pipeline run -c {config_path} --combined-subdir {comb_key}",
               f"perturbseq-pipeline pair-report -c {config_path} -o {outdir} --audit-dir {audit_dir} " + " ".join(f"--run {k}={v}" for k, v in run_dirs.items()) + (f" --previous-run {previous_run}" if previous_run else "") + f" --job-ids {','.join(job_ids)}" + (f" --base-commit {base_commit}" if base_commit else ""), "```", "",
               "## SLURM job ledger (job_ids.txt)", "", "```", ledger.strip(), "```", "", "## SLURM accounting (sacct)", "", md_table(sacct, 60) if len(sacct) else "_sacct not available_", "",
               "## Run start / end times (from run.log)", "", md_table(pd.DataFrame([{"run": k, **v} for k, v in run_times.items()]), 10), "",
               "## Environment", "", f"- conda env: `{manifest['conda_env']}` (`{manifest['conda_prefix']}`)", f"- python: `{sys.executable}`", "", md_table(pd.DataFrame(list(versions.items()), columns=["package", "version"]), 40), "",
               "## Code changes versus the base commit", "", "```", git.get("diff_stat_vs_base", "(no base commit given)"), "```", "", "```", git.get("changed_files_vs_base", ""), "```", "",
               "## Working-tree status at report time", "", "```", git["status"] or "(clean)", "```", "", "## Recent commits", "", "```", git["log"], "```", "",
               "## Warnings / errors found in run logs", ""] + ([f"- {k}: {len(v)} line(s)" + ("".join(f"\n  - `{l[:220]}`" for l in v[:8]) if v else "") for k, v in warnings_found.items()] or ["- none"]) + ["",
               "## SBATCH scripts", ""]
    for sp in slurm_scripts:
        exec_md += [f"### {sp.name}", "", "```bash", sp.read_text().strip(), "```", ""]
    exec_md += ["## Validation", "", "See `final_validation.txt` / `tables/final_validation.csv` (written by the validation step) for the checklist results.", ""]
    (outdir / "execution_commands.md").write_text("\n".join(exec_md))

    # ---- sections (17-section layout) -----------------------------------------------------------
    S: List[Tuple[str, List[Block]]] = []
    strict_note = ("Strict primary pairs = designed targeting-targeting constructs (`pair_targeting`) and designed NTC-NTC constructs (`pair_non_targeting`). "
                   + ("Designed targeting+NTC (_S1) constructs are a labelled **sensitivity stratum** (`pair_targeting_plus_ntc`, class ambiguous) and never enter primary hit calls." if not s1_primary
                      else "Designed targeting+NTC (_S1) constructs are pooled into the primary targeting label and also reported as their own stratum."))
    lim = [
        "Intended MOI, CRISPR modality / effector and cell line are not documented: results are target-transcript depletion associations, not knockout / knockdown claims, and multiplicity is described, not modelled.",
        "HF011 vs HF012 and A vs B are undefined in the documents: cross-well agreement is well-level support only; no biological-replicate inference is made.",
        "Cells whose strongest A and C features are not a designed targeting-targeting or NTC-NTC construct (same-target non-designed, targeting+NTC, two targets, several strong features per scaffold, one slot only) are excluded from primary testing; they are reported, never re-labelled.",
        strict_note,
        "Scaffold 1 in Scaffold_seq.docx differs from the sequenced reads at two adjacent positions (~53-54); the reads are identical across wells, so the document most likely carries a typo. Counting uses the first 12 nt, identical in both sources.",
        f"{560 - int((gaud['in_oligo_pool'].astype(str).str.lower() == 'true').sum()) if gaud is not None else 'n/a'} designed spacers were never cloned; they and wrong-scaffold reads are kept as off-design features and can only make a cell unresolved.",
        "No batch correction (by design); clusters are computed per object and are not comparable across runs. Doublets are not removed; multi-construct cells appear as ambiguous / unresolved.",
        "Target-transcript tests use the log-normalised expression of the target's HGNC symbol (SNP-locus labels are tested on their gene); targets whose transcript is absent from the filtered GEX matrix (not expressed) cannot be tested.",
    ]
    inv_sum = inv.groupby("class").agg(n_files=("path", "count"), total_gb=("size_bytes", lambda s_: round(s_.sum() / 1e9, 2)), used=("used_in_iteration_2", lambda s_: ";".join(sorted(set(map(str, s_)))))).reset_index() if inv is not None and "class" in inv.columns else None
    det_c = det[det.run == comb_key] if len(det) else pd.DataFrame()
    pcm = prim.get(comb_key)
    ecdf_links = []
    for k in run_dirs:
        d = run_dirs[k] / "figures" / "perturbation" / "ecdf"
        if d.is_dir():
            ecdf_links.append(f"- {k}: {len(list(d.glob('ecdf_*.png')))} per-target ECDF figures in `{os.path.relpath(d, outdir)}`")
    # 1
    S.append(("Experimental information incorporated", [
        ("md", f"**Hanrui Fang dual-guide Perturb-seq, `{cfg.run.name}`** — generated {now}; branch `{git['branch']}`, commit `{git['commit']}`; config `{config_path}`. "
               f"Experimental sources: the guide design workbook, the oligo-pool construct map (`20250822_OligoPool_TwistAddG.xlsx`, {n_constructs} constructs: {ctype_counts}) and the scaffold document (`Scaffold_seq.docx`). "
               "Every fact is tagged by evidence type (experimental_document / fastq_derived / cellranger / computational_inference / gap) in `audit/evidence_matrix.csv`; the full record is `audit/experimental_information_used.md`."),
        ("md", "\n".join([
            f"- Cells: {_num(n_in)} loaded, {_num(n_ret)} expression-QC-pass (combined object, four wells, no batch correction).",
            f"- Strict primary pairs (combined): pair_targeting {_num(n_t)} ({_pct(n_t, n_ret)}), pair_non_targeting {_num(n_n)} ({_pct(n_n, n_ret)}); designed targeting+NTC constructs {_num(n_tn)} ({_pct(n_tn, n_ret)}) = {'sensitivity stratum' if not s1_primary else 'primary targeting label'}; "
            f"ambiguous / incomplete / unresolved (excluding the designed targeting+NTC constructs) {_num(n_amb)} ({_pct(n_amb, n_ret)}); no guide {_num(st(dg.STATUS_NO_GUIDE))}; below threshold {_num(st(dg.STATUS_BELOW_MIN_UMI))}.",
            f"- Perturbation-expression (target transcript, strict pairs vs designed NTC pairs): combined {hit_c}/{tested_c} targets with a depletion association; per sample " + ", ".join(f"{k} {h}/{t}" for k, (h, t) in per_sample_hits.items()) + ".",
            f"- Target support classes: {support_counts}.",
        ])),
        ("md", "**Did the confirmed experimental information change the analysis?**"), ("md", what_changed or "_see audit/experimental_information_used.md_"),
        ("md", "Design record (question / answer / evidence):"), ("md", design_record or "_design record not available_"),
        ("md", "Per-run reports: " + "; ".join(run_link_md(k) for k in run_dirs) + "."),
    ]))
    # 2
    S.append(("Input files and provenance", [
        ("md", f"`audit/source_file_inventory.csv` lists every file under the dataset root plus the staged Cell Ranger matrices and previous result files ({len(inv) if inv is not None else 'n/a'} entries; md5 for documents / small files, vendor `checksum.md5` values for FASTQs)."),
        tab(docs, 10), tab(inv_sum, 20),
        ("md", "Inputs of this run:"), tab(pd.DataFrame([{"sample": k, "gex_matrix": v, "guide_matrix": (cfg.input.guide_mtx_dirs or {}).get(k, "")} for k, v in (cfg.input.mtx_dirs or {}).items()]), 10),
        ("md", "Guide FASTQ quantification (scaffold-specific features; `audit/guide_read_retention_funnel.csv`, `audit/guide_quantification_summary.csv`; matrices re-used from the previous iteration with md5 verification, see `inputs/guide_counts/PROVENANCE.md`):"), tab(funnel, 10), tab(quant, 10),
        ("md", "Evidence matrix:"), tab(ev[["fact_id", "question", "source_file", "worksheet_or_section", "interpretation", "evidence_type", "status"]] if ev is not None else None, 40),
        ("md", "Sample structure: four separate 10x 5' GEM wells; condition / replicate columns of the manifest are well-id labels, not experimental metadata (`audit/sample_manifest_used.csv`)."),
        tab(smeta[[c for c in smeta.columns if c not in ("gex_fastq_files_R1", "guide_fastq_files_R1", "documents_mentioning_sample", "metadata_source")]] if smeta is not None else None, 10),
    ]))
    # 3
    S.append(("Construct and pair-map interpretation", [
        ("md", f"Construct types in the oligo pool: {ctype_counts}. Position 1 = scaffold C (document Scaffold 1), position 2 = scaffold A (document Scaffold 2). Constructs per target (`audit/constructs_per_target.csv`):"), tab(cpt, 60),
        ("md", "Construct map used (`audit/construct_pair_map_used.csv`):"),
        tab(cmap[["construct_id", "construct_type", "construct_target", "position1_design_id", "position1_scaffold_class", "position2_design_id", "position2_scaffold_class", "position1_match", "position2_match", "excel_row", "name_anomaly"]] if cmap is not None else None, 240),
        ("md", f"Guide reference used (`audit/guide_reference_used.csv`, {len(ref) if ref is not None else 'n/a'} features = 560 designed spacers x 2 scaffold classes; feature roles: {ref['feature_role'].value_counts().to_dict() if ref is not None else ''})."),
        tab(ref[ref["feature_role"] == "designed_slot"][["guide_id", "guide_sequence", "target_gene", "target_symbol", "scaffold", "construct_position", "pair_id", "control_status", "source_sheet_or_page", "sequence_match_status"]] if ref is not None else None, 30),
        ("md", "Scaffold evidence (`audit/scaffold_audit.csv`):"), tab(scaf[["item", "scaffold_class", "evidence_type", "length", "comparison", "n_mismatches_over_compared_length", "mismatch_positions_vs_document"]] if scaf is not None else None, 30),
        ("md", "Document scaffold vs iteration-1 read-derived scaffold per cloned guide:"), tab(gaud["design_vs_previous_empirical_scaffold"].value_counts().rename_axis("document_vs_read_derived_scaffold").reset_index(name="n_designed_guides") if gaud is not None else None, 10),
    ]))
    # 4
    S.append(("Guide/scaffold assignment rules", [
        ("md", rules_md or consequences or "_see audit/experimental_information_used.md_"), ("md", strict_note),
        ("md", f"Configuration: `assignment_mode = {cfg.guides.assignment_mode}`, `min_umi = {cfg.guides.min_umi}`, `dominance_ratio = {cfg.guides.dominance_ratio}` (pseudocount {getattr(cfg.guides, 'dominance_pseudocount', 1.0):g}), `require_complete_pair = {cfg.guides.require_complete_pair}`, `unresolved_pair_policy = {cfg.guides.unresolved_pair_policy}`, `designed_targeting_plus_ntc_primary = {s1_primary}`, `single_guide_diagnostic = {cfg.guides.single_guide_diagnostic}` (diagnostic only)."),
        ("md", "Guide UMI mass by feature role per well (`audit/off_design_feature_summary.csv`):"), tab(offd, 20), fig(comb_key, "guides/guide_umi_fraction_by_feature_role.png", "combined: guide UMI fraction by feature role"),
    ]))
    # 5
    S.append(("Expression QC before and after filtering", [
        ("md", f"Thresholds: permissive gene filter >= {cfg.qc.min_genes_per_cell} genes, final gene filter >= {cfg.qc.min_genes_final}, mitochondrial < {cfg.qc.max_pct_mt} %, genes in >= {cfg.qc.min_cells_per_gene} cells. Cell accounting for every run (input, permissive, final gene filter, mitochondrial failures, retained):"),
        tab(cc, 30), ("md", "QC metric distributions before / after filtering (medians and means of total UMIs, detected genes, % mitochondrial, % ribosomal, % haemoglobin):"), tab(qcm, 30),
        fig(comb_key, "qc/cell_counts_before_after_per_lane.png", "combined: cells before and after QC per lane"), fig(comb_key, "qc/qc_violin_before_filtering.png", "combined: QC violins before filtering"),
        fig(comb_key, "qc/pct_mt_vs_genes_and_umis.png", "combined: % mitochondrial vs genes and UMIs (all loaded cells)"), fig(comb_key, "qc/qc_scatter_before_filtering.png", "combined: genes vs UMIs before filtering"),
        fig(comb_key, "qc/qc_violin_after_filtering.png", "combined: QC violins after filtering"), fig(comb_key, "qc/genes_vs_umis_before_after.png", "combined: genes vs UMIs before / after"),
        fig(comb_key, "qc/ecdf_total_counts_before_after.png", "combined: ECDF total UMIs"), fig(comb_key, "qc/ecdf_n_genes_by_counts_before_after.png", "combined: ECDF detected genes"),
        fig(comb_key, "qc/ecdf_pct_counts_mt_before_after.png", "combined: ECDF % mitochondrial"), fig(comb_key, "qc/ecdf_pct_counts_ribo_before_after.png", "combined: ECDF % ribosomal"), fig(comb_key, "qc/ecdf_pct_counts_hb_before_after.png", "combined: ECDF % haemoglobin"),
    ]))
    # 6
    S.append(("Pair-guide QC", [
        ("md", "Pair-assignment status per lane, all runs (`n_pair_assigned_primary` / `frac_strict_primary_pair` = strict primary pairs; `frac_complete_pair` = both slots resolved):"), tab(pa, 30),
        ("md", "Pair-guide QC per lane (guide UMIs and detected guides per cell, scaffold detection, top / second / dominance-ratio summaries per slot, complete / strict / ambiguous / incomplete / dual-target / unresolved fractions, targeting+NTC sensitivity cells, class counts):"), tab(pq, 30),
        ("md", "Construct type per lane:"), tab(ctl, 20), ("md", "Strong guides per scaffold slot:"), tab(strong, 30), ("md", "Guide / GEX barcode overlap:"), tab(overlap, 20),
        fig(comb_key, "guides/pair_guide_umis_detection_by_scaffold.png", "combined: guide UMIs, detected guides, scaffold A vs C"), fig(comb_key, "guides/slot_top_vs_second_guide.png", "combined: top vs second guide per slot"),
        fig(comb_key, "guides/slot_dominance_ratio_ecdf.png", "combined: per-slot dominance ratio distributions"), fig(comb_key, "guides/pair_assignment_status_counts_and_fractions.png", "combined: pair-assignment status per lane"),
        fig(comb_key, "guides/strong_guides_per_scaffold.png", "combined: strong guides per scaffold slot"), fig(comb_key, "guides/target_pair_cells_per_lane.png", "combined: strict targeting-pair cells per target and lane"),
        fig(comb_key, "guides/guide_feature_representation.png", "combined: designed slot feature representation"), fig(comb_key, "guides/guide_representation.png", "combined: guide representation (pipeline)"), fig(comb_key, "guides/target_representation.png", "combined: target representation (pipeline)"),
        ("md", "Cells per target (strict primary targeting pairs) and per construct:"), tab(tcells[tcells.run == comb_key] if len(tcells) else None, 60), tab(constructs_cells[constructs_cells.run == comb_key] if len(constructs_cells) else None, 60),
    ]))
    # 7
    S.append(("Ambiguity and unresolved-assignment analysis", [
        ("md", "Cells excluded from primary perturbation testing, with the reason (`pair_resolution_detail`). Categories: strict primary construct pairs (enter testing); targeting-plus-NTC designed constructs (sensitivity); inferred same-target pairs not in the construct map (`unresolved_pair` / `same_target_not_designed`, sensitivity); other unresolved combinations; dual-target ambiguous; scaffold-ambiguous; incomplete; below threshold; no guide. Ambiguous cells stay in the object and in the clustering but never become valid pairs."),
        tab(det_c[~det_c["enters_primary_testing"].astype(bool)] if len(det_c) else None, 60), ("md", "Strict primary constructs entering testing:"), tab(det_c[det_c["enters_primary_testing"].astype(bool)] if len(det_c) else None, 20),
        ("md", "Single-guide diagnostic comparison (historical top-vs-second rule, computed for comparison only, not used for any result):"), tab(sg[sg.run == comb_key] if len(sg) else None, 10), fig(comb_key, "guides/single_guide_diagnostic_vs_pair_status.png", "combined: single-guide diagnostic vs pair status"),
    ]))
    # 8
    S.append(("PCA, UMAP and Leiden clustering", [
        ("md", f"Normalisation, log1p, {cfg.cluster.n_top_genes} HVGs, {cfg.cluster.n_pcs} PCs, {cfg.cluster.n_neighbors}-neighbour graph, UMAP, Leiden {cfg.cluster.leiden_resolution}; expression-QC-pass cells; batch_key = {cfg.cluster.batch_key} (no Harmony)."),
        fig(comb_key, "clustering/pca_variance.png", "combined: PCA variance"), fig(comb_key, "clustering/pca_by_sample_condition_pair_status.png", "combined: PCA by sample, condition, pair status"),
        fig(comb_key, "clustering/umap_clusters.png", "combined: UMAP by Leiden cluster"), fig(comb_key, "clustering/umap_by_sample_condition_pair_status.png", "combined: UMAP by sample, condition, pair status, cluster"),
        fig(comb_key, "clustering/umap_assignment_class.png", "combined: UMAP by targeting / NTC / ambiguous class"), fig(comb_key, "clustering/umap_lane.png", "combined: UMAP by lane"),
        fig(comb_key, "clustering/cluster_sizes.png", "combined: cluster sizes"), fig(comb_key, "clustering/cluster_composition_sample_pairstatus_class.png", "combined: cluster composition by sample, pair status, class"), fig(comb_key, "clustering/cluster_lane_composition.png", "combined: cluster composition by lane"),
        tab(clusters.pivot_table(index="cluster", columns="run", values="n_cells", aggfunc="first").reset_index() if len(clusters) else None, 40),
    ]))
    # 9
    S.append(("ECDF analysis", [
        ("md", "Empirical cumulative distributions of the target transcript (log-normalised) in strict targeting pairs versus designed NTC pairs, per lane and pooled; one figure per tested target in each run plus overview panels."),
        ("md", "\n".join(ecdf_links)), fig(comb_key, "perturbation/pair_ecdf_overview_top_targets.png", "combined: ECDF overview (12 most significant targets)"), fig(comb_key, "perturbation/pair_level_expression_distributions.png", "combined: construct-level ECDFs for the top targets"),
    ] + [fig(k, "perturbation/pair_ecdf_overview_top_targets.png", f"{k}: ECDF overview") for k in samples]))
    # 10
    S.append(("Perturbation-expression results", [
        ("md", f"Test: two-sided Kolmogorov-Smirnov (and one-sided Mann-Whitney, perturbed < control) on the target transcript, strict targeting pairs vs designed NTC pairs (`primary_control = ntc`); log2FC of de-logged means (pseudocount); BH FDR within lane x control x stratum; "
               f"hit = `fdr_ks < {cfg.perturbation.fdr_alpha}` and `log2fc < {cfg.perturbation.max_log2fc_for_hit}`; >= {cfg.perturbation.min_cells_per_target} target cells and >= {cfg.perturbation.min_control_cells} controls. `neg_log10_fdr = -log10(max(fdr_ks, 1e-300))`. "
               "Strata: **primary_pair_targeting** (strict pairs); **single_guide_plus_ntc_constructs_only** (designed _S1 constructs); **sensitivity_incl_targeting_plus_ntc** (primary + _S1); **sensitivity_incl_same_target_not_designed** (primary + inferred same-target pairs absent from the map). Construct-level results: `tables/pair_perturbation_by_pair.csv` of each run."),
        ("md", "Hit counts per lane and run (targets and constructs; strict vs sensitivity strata):"), tab(hc, 30), fig(comb_key, "perturbation/pair_volcano_target_level.png", "combined: target-level volcano"), fig(comb_key, "perturbation/pair_volcano_pair_level.png", "combined: construct-level volcano"),
        fig(comb_key, "perturbation/pair_waterfall_target_log2fc.png", "combined: log2FC per target with sensitivity strata"), fig(comb_key, "perturbation/pair_hit_counts_per_lane.png", "combined: targets tested / hit per lane"), fig(comb_key, "perturbation/pair_level_hit_counts_per_lane.png", "combined: constructs tested / hit per lane"),
    ]))
    # 11
    S.append(("log2FC and FDR results", [
        ("md", "Combined-run primary results per target (pooled lane `ALL`): cell counts, log2FC, % knockdown, KS p, raw FDR, neg_log10_fdr, hit call."),
        tab(pcm[pcm.lane_id == "ALL"][["target_gene", "measured_transcript", "n_target_pair_cells", "n_ntc_pair_cells", "log2fc", "pct_knockdown", "ks_pval", "fdr_ks", "neg_log10_fdr", "mwu_pval_less", "fdr_mwu", "is_hit", "hit_status"]].sort_values("log2fc") if pcm is not None and "measured_transcript" in pcm.columns else (pcm[pcm.lane_id == "ALL"].sort_values("log2fc") if pcm is not None else None), 80),
        fig(comb_key, "perturbation/pair_heatmap_log2fc_by_lane.png", "combined: log2FC heatmap by lane"), fig(comb_key, "perturbation/pair_heatmap_neg_log10_fdr_by_lane.png", "combined: neg_log10_fdr heatmap by lane"),
        ("md", "Construct-level results (combined, pooled):"), tab(bypair[comb_key][bypair[comb_key].lane_id == "ALL"][["target_gene", "construct_id", "construct_type", "guide_pair", "n_target_pair_cells", "log2fc", "fdr_ks", "neg_log10_fdr", "is_hit"]].sort_values("log2fc") if bypair.get(comb_key) is not None and len(bypair[comb_key]) else None, 120),
        ("md", "Strict-pair versus sensitivity-stratum comparison (combined, pooled; all strata):"),
        tab(byt[comb_key][(byt[comb_key].control == "ntc") & (byt[comb_key].lane_id == "ALL")].pivot_table(index="target_gene", columns="assignment_stratum", values=["log2fc", "is_hit", "n_target_pair_cells"], aggfunc="first").reset_index() if byt.get(comb_key) is not None else None, 60),
    ]))
    # 12
    blocks = []
    for k in samples:
        pk = prim.get(k)
        blocks += [("md", f"### {k}\n\nFull reports: {run_link_md(k)}"), tab(pa[pa.run == k], 5), tab(hc[hc.run == k], 5),
                   tab(pk[pk.lane_id == k][["target_gene", "n_target_pair_cells", "n_ntc_pair_cells", "log2fc", "fdr_ks", "neg_log10_fdr", "is_hit"]].sort_values("log2fc") if pk is not None else None, 60),
                   fig(k, "guides/pair_assignment_status_counts_and_fractions.png"), fig(k, "clustering/umap_by_sample_condition_pair_status.png"), fig(k, "perturbation/pair_volcano_target_level.png"), fig(k, "perturbation/pair_heatmap_log2fc_by_lane.png")]
    S.append(("Per-sample results", blocks))
    # 13
    S.append(("Combined results", [
        ("md", f"Combined object: four wells concatenated with sample-prefixed cell ids (`<well>_<barcode>`), sample / condition / replicate / pair metadata retained, no batch correction (batch_key = {cfg.cluster.batch_key}). Full reports: {run_link_md(comb_key)}."),
        tab(pa[pa.run == comb_key], 10), tab(pq[pq.run == comb_key], 10), tab(hc[hc.run == comb_key], 10),
        ("md", "Per-well pair statuses inside the combined run equal the per-sample runs (validated in `final_validation.txt`)."),
    ]))
    # 14
    S.append(("Target and construct support across samples", [
        ("md", "Support = agreement of the primary hit call across the four per-sample runs and the combined run (well-level evidence only: replicate identity of the wells is undocumented). Additional columns give the sensitivity strata of the combined run. Construct-level results of every run: `tables/pair_perturbation_by_pair_all_runs.csv`."),
        tab(support["support_class"].value_counts().rename_axis("support_class").reset_index(name="targets"), 10), tab(support, 80),
        tab(pairs_all[pairs_all.lane_id.isin(samples + ["ALL"])].pivot_table(index=["target_gene", "construct_id"], columns="run", values="is_hit", aggfunc="first").reset_index() if len(pairs_all) and "construct_id" in pairs_all.columns else None, 120),
        fig(comb_key, "perturbation/pair_hit_counts_per_lane.png", "combined: hit counts per lane"),
    ] + [fig(k, "perturbation/pair_volcano_target_level.png", f"{k}: volcano") for k in samples]))
    # 15
    S.append(("Previous versus new run comparison", [
        ("md", f"Supplemental comparison with `{previous_run}` (not modified). Design / reference-level differences (`audit/previous_vs_new_reference_comparison.csv`):"),
        tab(ref_cmp, 20), ("md", "Run-level differences (`tables/previous_vs_new_summary.csv`):"), tab(prev_cmp, 30),
    ] + prev_blocks))
    # 16
    S.append(("Scientific limitations", [("md", "\n".join(f"- {x}" for x in lim)), ("md", "Open questions for the experimental team:\n\n" + (open_q or "_see audit/experimental_information_used.md_"))]))
    # 17
    S.append(("Complete execution provenance", [
        ("md", f"Branch `{git['branch']}`, commit `{git['commit']}`" + (f", base commit `{base_commit}`" if base_commit else "") + f". Conda env `{manifest['conda_env']}`. All substantial steps ran under SLURM (job ids {', '.join(job_ids) or 'see ledger'}); details, SBATCH scripts, sacct accounting, package versions and code changes are in `execution_commands.md`; machine-readable provenance in `run_manifest.json`."),
        tab(sacct, 40), tab(pd.DataFrame(list(versions.items()), columns=["package", "version"]), 30),
        ("md", "Code changes versus the base commit:"), ("pre", git.get("diff_stat_vs_base", "(no base commit given)")), ("md", "Resolved configuration of the combined run:"), ("pre", resolved_cfg[:20000]),
    ]))

    title = f"{cfg.run.name}: pair-guide Perturb-seq analysis report"
    intro = (f"Full analysis report generated {now}. Primary labels are explicit construct-map pair assignments (strict targeting-targeting and NTC-NTC constructs); the single-guide rule is diagnostic only. "
             "Hits are target-transcript depletion associations (modality undocumented). Facts are tagged by evidence type in sections 1 to 3.")
    (outdir / "report.md").write_text(_render_md(S, outdir, title, intro))
    (outdir / "report.html").write_text(_render_html(S, outdir, title, intro))

    # previous-vs-new part 2 appended to the audit file
    pvn = next((audit_dir / nm for nm in ("previous_vs_new_run.md", "previous_vs_new_analysis.md") if audit_dir and (audit_dir / nm).is_file()), None)
    if pvn is not None:
        txt = pvn.read_text()
        marker = "## Part 2: run-level comparison"
        txt = txt.split(marker)[0].rstrip() + f"\n\n{marker} (root report {now})\n\n" + md_table(prev_cmp, 40) + "\n" + ("Target-level hit agreement: `tables/previous_vs_new_target_hits.csv`.\n" if (outdir / "tables" / "previous_vs_new_target_hits.csv").is_file() else "")
        pvn.write_text(txt)

    readme = [f"# {cfg.run.name}", "", f"Generated {now}; branch `{git['branch']}` commit `{git['commit']}`.", "",
              "- `report.html` / `report.md`: root full analysis report (17 sections) linking the per-run reports", "- `combined/`: pooled four-well run (report.html, report.md, processed h5ad, figures/, tables/)",
              "- `samples/<well>/`: independent per-sample runs with the same structure", "- `audit/`: data inventory, experimental design record, evidence matrix, pair reference, construct / scaffold / sample audits, previous-vs-new comparison",
              "- `inputs/guide_counts/`: scaffold-specific guide UMI matrices", "- `tables/`: cross-run tables (target support, pair fractions, previous-vs-new)", "- `slurm/`: job scripts, logs and the job ledger",
              "- `execution_commands.md`, `run_manifest.json`, `config_used.yaml`, `final_validation.txt`", "",
              "Primary labels = explicit construct-map pair assignments (strict pair_targeting vs pair_non_targeting; designed targeting+NTC constructs per guides.designed_targeting_plus_ntc_primary). Single-guide rule = diagnostic only."]
    (outdir / "README.md").write_text("\n".join(readme) + "\n")
    logger.info("Root report written to %s", outdir / "report.html")
    return outdir / "report.html"
