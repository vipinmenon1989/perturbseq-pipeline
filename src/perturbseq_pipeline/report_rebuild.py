"""Rebuild the full HTML report of a finished pair-guide run (and the root index report) from its
on-disk outputs, using the pipeline's own Jinja report machinery (``templates/report_full.html``
shares the CSS, summary cards, figure rendering and table conventions of ``templates/report.html``).

Nothing is recomputed: figures come from ``tables/figure_manifest.csv`` (every PNG is verified to
exist and be non-empty and is embedded as a data URI, with a link to the full-resolution file),
tables from ``tables/*.csv`` (rendered with a row cap and a link to the complete CSV), the
configuration from ``logs/resolved_config.yaml`` and the per-cell slot values (top / second guide
UMIs, dominance ratio, slot status, primary-versus-sensitivity flag) from the processed H5AD ``obs``.

    perturbseq-pipeline rebuild-report --root results/<run> --run HF011A=... --run combined=... \
        [--previous-run OLD_ROOT] [--title ...]
"""
from __future__ import annotations

import datetime as _dt
import html as _html
import json
import logging
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from . import __version__
from . import dual_guides as dg
from .config import Config
from .plots import FigureRecord
from .report import TEMPLATE_DIR, _versions

logger = logging.getLogger(__name__)

RENDERER = "report_rebuild (templates/report_full.html)"
BACKUP_NAME = "report_textual_backup.html"
PER_CELL_TABLE = "pair_assignment_per_cell"
SLOT_SUMMARY_TABLE = "pair_slot_summary_by_status"

GROUP_OF_STATUS = {
    dg.STATUS_PAIR_TARGETING: "strict primary construct pair (targeting)",
    dg.STATUS_PAIR_NTC: "strict primary construct pair (NTC control)",
    dg.STATUS_PAIR_TARGET_NTC: "targeting-plus-NTC sensitivity class (designed construct)",
    dg.STATUS_PAIR_TARGET_NTC_PROVISIONAL: "targeting-plus-NTC provisional",
    dg.STATUS_DUAL_TARGET: "dual-target ambiguity",
    dg.STATUS_INCOMPLETE: "incomplete pair",
    "ambiguous_scaffold_A": "scaffold ambiguity (A)",
    "ambiguous_scaffold_C": "scaffold ambiguity (C)",
    "ambiguous_scaffold_A_and_C": "scaffold ambiguity (A and C)",
    dg.STATUS_UNKNOWN_GUIDE: "unknown guide",
    dg.STATUS_BELOW_MIN_UMI: "below min_umi",
    dg.STATUS_NO_GUIDE: "no guide",
}
GROUP_ORDER = list(dict.fromkeys(list(GROUP_OF_STATUS.values()) + ["same-target inferred pair (not a construct)", "unresolved pair (not a construct)"]))

KEY_SAMPLE_FIGURES = ["pair_assignment_status_counts_and_fractions", "umap_by_sample_condition_pair_status", "pair_volcano_target_level", "pair_heatmap_log2fc_by_lane"]


# --------------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------------


def _rel(path: Path, base: Path) -> str:
    try:
        return os.path.relpath(Path(path), Path(base))
    except ValueError:  # pragma: no cover
        return str(path)


def _fmt(v):
    if isinstance(v, (float, np.floating)):
        if pd.isna(v):
            return ""
        if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e6):
            return f"{v:.3g}"
        return f"{v:.4g}" if abs(v) < 10 else f"{v:,.2f}".rstrip("0").rstrip(".")
    if isinstance(v, (int, np.integer)):
        return f"{int(v):,}"
    return str(v)


def table_html(df: Optional[pd.DataFrame], name: str, csv_href: Optional[str], max_rows: int = 60, note: str = "") -> Markup:
    """Readable first section of a table + total rows + link to the complete CSV (never silently truncated)."""
    if df is None or len(df) == 0:
        return Markup(f'<p class="sub">Table <code>{_html.escape(name)}</code>: not available for this run.</p>')
    shown = df.head(max_rows)
    body = shown.to_html(index=False, escape=True, border=0, na_rep="", formatters={c: _fmt for c in shown.columns})
    meta = f"<b>{_html.escape(name)}</b> &mdash; {len(df):,} rows &times; {df.shape[1]} columns"
    if len(df) > max_rows:
        meta += f"; showing the first {max_rows:,} rows"
    if csv_href:
        meta += f' &mdash; complete CSV: <a href="{_html.escape(csv_href)}">{_html.escape(os.path.basename(csv_href))}</a>'
    if note:
        meta += f" &mdash; {note}"
    return Markup(f'<p class="tblmeta">{meta}</p><div class="scroll">{body}</div>')


def figure_html(rec: FigureRecord, out_dir: Path, embed: bool = True, small: bool = False) -> Markup:
    """Embedded figure with title, caption, full-resolution link and relative path (pipeline conventions)."""
    href = _rel(rec.path, out_dir)
    src = rec.data_uri() if embed else href
    cap = f"<b>{_html.escape(rec.title)}.</b> {_html.escape(rec.caption)}" if rec.caption else f"<b>{_html.escape(rec.title)}.</b>"
    lazy = ' loading="lazy"' if small else ""
    return Markup(
        f'<figure><a href="{_html.escape(href)}"><img src="{src}" alt="{_html.escape(rec.title)}"{lazy}></a>'
        f'<figcaption>{cap} <span class="figlink"><a href="{_html.escape(href)}">full resolution</a> &middot; <span class="mono">{_html.escape(href)}</span></span></figcaption></figure>'
    )


def _captions_from_html(paths: List[Path]) -> Dict[str, str]:
    """Recover figure captions from a previously rendered pipeline report (title -> caption)."""
    out: Dict[str, str] = {}
    pat = re.compile(r"<figcaption><b>(.*?)\.</b>\s*(.*?)</figcaption>", re.S)
    for p in paths:
        if p and Path(p).is_file():
            txt = Path(p).read_text(errors="ignore")
            for t, c in pat.findall(txt):
                c = re.sub(r"<[^>]+>", "", c).strip()
                out.setdefault(_html.unescape(t).strip(), _html.unescape(c))
    return out


def load_figures(run_dir: Path, caption_sources: List[Path]) -> Tuple[List[FigureRecord], List[str]]:
    """Figure records from the run's manifest; missing / empty files are reported, not embedded."""
    man = pd.read_csv(run_dir / "tables" / "figure_manifest.csv", dtype=str, keep_default_na=False)
    caps = _captions_from_html(caption_sources)
    recs, missing = [], []
    for _, r in man.iterrows():
        p = Path(r["path"])
        if not p.is_absolute():
            p = run_dir / p
        if not p.is_file() or p.stat().st_size == 0:
            missing.append(str(p))
            continue
        cap = r.get("caption", "") if "caption" in man.columns else ""
        if not cap:
            cap = caps.get(r["title"], "")
        recs.append(FigureRecord(path=p, name=r["name"], section=r["section"], title=r["title"], caption=cap, in_report=str(r["in_report"]).lower() == "true"))
    return recs, missing


def load_tables(run_dir: Path) -> Dict[str, pd.DataFrame]:
    out = {}
    for p in sorted((run_dir / "tables").glob("*.csv")):
        try:
            out[p.stem] = pd.read_csv(p)
        except Exception as exc:  # pragma: no cover
            logger.warning("could not read %s: %s", p, exc)
    return out


def _read_obs(h5ad: Path) -> pd.DataFrame:
    import anndata as ad
    import h5py

    with h5py.File(h5ad, "r") as f:
        return ad.io.read_elem(f["obs"]) if hasattr(ad, "io") else ad.experimental.read_elem(f["obs"])


def per_cell_assignment_tables(run_dir: Path, cfg: Config) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """Per-cell slot table (top / second / ratio / status per scaffold + primary-vs-sensitivity flag) and its summary."""
    h5 = run_dir / cfg.output.h5ad_name
    if not h5.is_file():
        return None, None
    obs = _read_obs(h5)
    cA, cC = [str(c) for c in cfg.guides.scaffold_classes]
    cols = ["lane_id", dg.OBS_PAIR_STATUS, dg.OBS_PAIR_DETAIL, "perturbation_class", dg.OBS_PAIR_PRIMARY, dg.OBS_CONSTRUCT_TYPE, dg.OBS_PAIR_ID, "target_gene"]
    for c in (cA, cC):
        cols += [dg.OBS_SLOT_ID.format(c=c), dg.OBS_SLOT_COUNT.format(c=c), dg.OBS_SLOT_SECOND.format(c=c), dg.OBS_SLOT_RATIO.format(c=c), dg.OBS_SLOT_STATUS.format(c=c)]
    cols += [c for c in (dg.OBS_SG_CLASS, dg.OBS_SG_TARGET) if c in obs.columns]
    cols = [c for c in cols if c in obs.columns]
    df = obs[cols].copy()
    df.insert(0, "cell_id", obs.index.astype(str))
    status = df[dg.OBS_PAIR_STATUS].astype(str)
    detail = df[dg.OBS_PAIR_DETAIL].astype(str) if dg.OBS_PAIR_DETAIL in df.columns else pd.Series("", index=df.index)
    group = status.map(GROUP_OF_STATUS).fillna("unresolved pair (not a construct)")
    group = group.where(~((status == dg.STATUS_UNRESOLVED) & (detail == dg.DETAIL_SAME_TARGET_NOT_DESIGNED)), "same-target inferred pair (not a construct)")
    group = group.where(~((status == dg.STATUS_UNRESOLVED) & (detail != dg.DETAIL_SAME_TARGET_NOT_DESIGNED)), "unresolved pair (not a construct)")
    prim = df[dg.OBS_PAIR_PRIMARY].astype(bool) if dg.OBS_PAIR_PRIMARY in df.columns else pd.Series(False, index=df.index)
    flag = np.where(prim, "primary", np.where(status == dg.STATUS_PAIR_TARGET_NTC, "sensitivity", np.where(status == dg.STATUS_NO_GUIDE, "unassigned", "ambiguous / excluded")))
    df.insert(2, "assignment_group", group.to_numpy())
    df.insert(3, "primary_vs_sensitivity", flag)
    for c in (cA, cC):
        df[dg.OBS_SLOT_RATIO.format(c=c)] = df[dg.OBS_SLOT_RATIO.format(c=c)].astype(float).round(3)
    rows = []
    for g in GROUP_ORDER:
        m = df["assignment_group"] == g
        if not m.any():
            continue
        r = {"assignment_group": g, "primary_vs_sensitivity": ";".join(sorted(set(df.loc[m, "primary_vs_sensitivity"]))), "n_cells": int(m.sum()), "pct_of_cells": round(100.0 * m.sum() / len(df), 2)}
        for c in (cA, cC):
            r[f"median_top_umi_{c}"] = float(df.loc[m, dg.OBS_SLOT_COUNT.format(c=c)].median())
            r[f"median_second_umi_{c}"] = float(df.loc[m, dg.OBS_SLOT_SECOND.format(c=c)].median())
            r[f"median_dominance_ratio_{c}"] = float(df.loc[m, dg.OBS_SLOT_RATIO.format(c=c)].median())
            r[f"frac_slot_{c}_resolved"] = float((df.loc[m, dg.OBS_SLOT_STATUS.format(c=c)].astype(str) == dg.SLOT_RESOLVED).mean())
        rows.append(r)
    return df, pd.DataFrame(rows)


def _cards_from_html(paths: List[Path]) -> Dict[str, str]:
    pat = re.compile(r'<div class="card"><div class="v">([^<]*)</div><div class="k">([^<]*)</div>')
    out = {}
    for p in paths:
        if p and Path(p).is_file():
            for v, k in pat.findall(Path(p).read_text(errors="ignore")):
                out.setdefault(_html.unescape(k).strip(), _html.unescape(v).strip())
    return out


def _omnibus_from_html(paths: List[Path]) -> str:
    pat = re.compile(r"chi-square\s*=\s*</b>\s*([^<]*)</b>\s*on\s*([0-9]+)\s*degrees of\s*freedom,\s*permutation\s*<b>p\s*=\s*([^<]*)</b>", re.S)
    for p in paths:
        if p and Path(p).is_file():
            m = pat.search(Path(p).read_text(errors="ignore"))
            if m:
                return f"Omnibus test of the whole target-by-cluster table: chi-square = {m.group(1).strip()} on {m.group(2)} degrees of freedom, permutation p = {m.group(3).strip()}."
    return "Omnibus statistics are recorded in the run log (logs/run.log); the per-pair Fisher tests below are the reported results."


def _slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_")


def _top_six(df: Optional[pd.DataFrame], support_col: str, min_support: int, rank_cols: List[Tuple[str, bool]], label: str, extra_filter=None, n: int = 6) -> Tuple[Optional[pd.DataFrame], str, str]:
    """Deterministic best-n selection: support filter, then sort by (primary significance, tie-break effect).

    Returns (table, rule_text, note_text)."""
    if df is None or len(df) == 0 or support_col not in df.columns:
        return None, "", ""
    sub = df[df[support_col].astype(float) >= min_support].copy()
    if extra_filter is not None:
        sub = sub[extra_filter(sub)]
    cols = [(c, asc) for c, asc in rank_cols if c in sub.columns]
    if not cols:
        return None, "", ""
    sub = sub.sort_values([c for c, _ in cols], ascending=[a for _, a in cols], kind="mergesort").reset_index(drop=True)
    sub.insert(0, "rank", np.arange(1, len(sub) + 1))
    rule = (f"{label}: keep targets with {support_col} \u2265 {min_support}; rank by " + ", then ".join(f"{c} ({'ascending' if a else 'descending'})" for c, a in cols) +
            "; ties broken by the next key, then by target name (stable sort).")
    note = f"{min(n, len(sub))} of {len(sub)} eligible targets shown." + (f" Fewer than {n} targets passed the support filter." if len(sub) < n else "")
    return sub.head(n), rule, note


def _figs_for(names: List[str], by_sec: Dict[str, List[FigureRecord]], section: str, prefix: str, out_dir: Path) -> List[Markup]:
    have = {r.name: r for r in by_sec.get(section, [])}
    out = []
    for t in names:
        rec = have.get(_slug(f"{prefix}{t}"))
        if rec is not None:
            out.append(figure_html(rec, out_dir))
    return out


def _md_table(df: Optional[pd.DataFrame], max_rows: int = 40) -> str:
    from .report_markdown import md_table
    return md_table(df, max_rows)


def write_markdown(md_path: Path, ctx: Dict[str, object]) -> Path:
    """Markdown twin of the HTML report: same sections, tables as GitHub tables (row-capped), figures as relative links."""
    out_dir = md_path.parent
    L: List[str] = [f"# {ctx['title']}", "", f"Run `{ctx['run_name']}` · {ctx['report_kind']} · generated {ctx['generated_at']} · perturbseq-pipeline v{ctx['version']} · branch `{ctx['git']['branch']}` commit `{ctx['git']['commit']}`. HTML twin: `report.html`.", ""]
    L += ["## Run summary", "", _md_table(pd.DataFrame(ctx["summary_cards"], columns=["item", "value"]), 40), "", _md_table(pd.DataFrame(ctx["meta_rows"], columns=["item", "value"]), 40), "",
          "**Primary cell-assignment rule.** " + ctx["rule_text"], "", "**Limitations.**", ""] + [f"- {w}" for w in ctx["warnings"]] + [""]
    figs = ctx["fig_records"]; tabs = ctx["raw_tables"]

    def T(name, n=40):
        return _md_table(tabs.get(name), n) + "\n" + (f"Complete CSV: `{ctx['csv_paths'][name]}`\n" if name in ctx["csv_paths"] else "")

    def F(section, only_in_report=True):
        recs = [r for r in figs.get(section, []) if (r.in_report or not only_in_report)]
        return "\n".join(f"![{r.title}]({_rel(r.path, out_dir)})\n\n_{r.title}. {r.caption}_ (`{_rel(r.path, out_dir)}`)\n" for r in recs) or "_no figures_\n"

    def G(section):
        recs = sorted(figs.get(section, []), key=lambda r: (not r.in_report, r.name))
        return "\n".join(f"- [{r.title}]({_rel(r.path, out_dir)})" for r in recs) + "\n"

    def TS(key):
        t = ctx["topsix"].get(key)
        if not t:
            return "_not available_\n"
        return f"**Ranking rule.** {t['rule']} {t['note']}\n\n" + _md_table(t["df"], 10) + ("\n".join(f"![{n}]({p})" for n, p in t["fig_paths"]) + "\n" if t["fig_paths"] else "")

    if ctx["is_root"]:
        L += ["## Per-run index", "", T("run_index"), ""] + [f"- **{r['name']}**: [report.html]({r['html']}) · [report.md]({r['md']}) · [figures/]({r['figures']}) · [tables/]({r['tables']})" for r in ctx["run_links"]] + [""]
    L += ["## 1. Quality control", "", T("qc_steps"), T("qc_summary"), T("cell_counts_before_after"), T("qc_metrics_per_lane_before_after"), F("qc"), ""]
    L += ["## 2. Pair-guide QC", "", "Slot rule: top guide UMI ≥ min_umi and (top guide UMI + 1) / (second guide UMI + 1) ≥ 2 per scaffold; strict primary pairs = designed targeting-targeting and NTC-NTC constructs; targeting-plus-NTC constructs = sensitivity class; same-target inferred pairs, dual-target, scaffold-ambiguous, unresolved, incomplete, below-threshold and guide-free cells are excluded from primary testing; the single-guide rule is diagnostic only.", "",
          _md_table(pd.DataFrame(ctx["guide_cards"], columns=["item", "value"]), 20), "", T("pair_assignment_per_lane"), T("pair_resolution_detail_per_lane"), T("construct_type_per_lane"), T(SLOT_SUMMARY_TABLE), T(PER_CELL_TABLE, 20), T("pair_guide_qc_per_lane"),
          T("strong_guides_per_scaffold_per_lane"), T("guide_gex_barcode_overlap"), T("off_design_umi_fraction_per_lane"), T("target_cells_per_lane"), T("construct_cells_per_lane"), T("guide_representation"), T("guide_feature_representation"), F("guides"), T("single_guide_diagnostic_vs_pair"), ""]
    L += ["## 3. Clustering", "", T("clusters"), T("cluster_sizes"), T("cluster_composition"), F("clustering"), ""]
    L += ["## 4. Perturbation strength", "", _md_table(pd.DataFrame(ctx["perturbation_cards"], columns=["item", "value"]), 20), "", T("pair_perturbation_hit_counts_per_lane"), F("perturbation"), "### Target-level (strict pairs vs NTC pairs)", "", T("pair_perturbation_primary", 80),
          "### Construct-level", "", T("pair_perturbation_by_pair", 80), "### Primary versus sensitivity strata", "", T("pair_perturbation_strata_comparison", 60), "### Ranked pipeline table", "", T("perturbation", 60), T("skipped"), T("target_support_matrix", 60),
          "### Best six targets (direct perturbation)", "", TS("perturbation"), "### All per-target figures", "", G("perturbation/per_gene"), "### ECDF figures", "", G("perturbation/ecdf"), ""]
    L += ["## 5. Perturbation enrichment across clusters", "", (ctx["enrichment"] or {}).get("omnibus_text", ""), "", F("enrichment"), T("enrichment", 60), T("enrichment_effect_magnitude"), T("enrichment_composition"), "### Best six targets (enrichment)", "", TS("enrichment"), "### All per-target enrichment figures", "", G("enrichment/per_target"), ""]
    if ctx["has_ps"]:
        L += ["## 6. PS score", "", _md_table(pd.DataFrame(ctx["ps_cards"], columns=["item", "value"]), 20), "", F("ps_score"), T("ps_score", 60), T("ps_vs_perturbation", 60), T("ps_skipped"), "### Best six targets (PS score)", "", TS("ps_score"), "### All per-target PS figures", "", G("ps_score/per_target"), G("ps_score/lda"), ""]
    if ctx["has_lochness"]:
        L += ["## 7. lochNESS", "", _md_table(pd.DataFrame(ctx["lochness_cards"], columns=["item", "value"]), 20), "", F("lochness"), T("lochness", 60), T("lochness_by_cluster", 60), "### Best six targets (lochNESS)", "", TS("lochness"), "### All per-target lochNESS maps", "", G("lochness/per_target"), ""]
    if ctx["has_distance"]:
        L += ["## 8. Energy distance / MMD", "", _md_table(pd.DataFrame(ctx["distance_cards"], columns=["item", "value"]), 20), "", F("distance"), T("perturbation_distance", 60), "### Best six targets (distance)", "", TS("distance"), ""]
    if ctx["has_distance_space"]:
        L += ["## 9. Perturbation distance space", "", F("distance_space"), T("phenotype_modules", 60), T("perturbation_space_coordinates", 60), T("perturbation_neighbors", 60), "### Best six targets (perturbation space)", "", TS("distance_space"), ""]
    if ctx["has_modules"]:
        L += ["## 10. Co-functional modules, gene programs and networks", "", _md_table(pd.DataFrame(ctx["modules_cards"], columns=["item", "value"]), 20), "", F("modules"), T("cofunctional_modules", 60), T("tf_hubs", 60), T("module_program_strength"), T("module_connectivity", 40), "### Best six perturbations (network hubs)", "", TS("modules"), T("program_summary"), T("program_enrichment", 60), T("gene_programs", 40), T("program_activity_by_cluster", 40), ""]
    if ctx["has_meta"]:
        L += ["## 11. Master perturbation meta table", "", T("perturbation_meta", 60), ""]
    if ctx["is_root"]:
        L += ["## 12. Target and construct support across samples", "", T("support_classes"), T("target_support_matrix_across_runs", 80), T("pair_perturbation_hit_counts_all_runs"), T("pair_assignment_per_lane_all_runs"), T("module_status_all_runs"), ""]
        L += ["## 13. Comparison with the previous run (supplemental)", "", f"Previous run: `{ctx['previous_run']}` (not modified).", "", T("previous_vs_new_reference_comparison"), T("previous_vs_new_summary"), T("previous_vs_new_target_hits", 60), ""]
    L += ["## Reproducibility", "", _md_table(pd.DataFrame(ctx["repro_rows"], columns=["item", "value"]), 30), "", "### Module completion status", "", T("module_status"), "### Inputs", "", _md_table(ctx["raw_tables"].get("inputs"), 40), "", "### Outputs", ""] + [f"- {r['deliverable']}: `{r['path']}`" for r in ctx["outputs_rows"]] + ["", "### Resolved configuration", "", "```yaml", ctx["config_yaml"], "```", "", "### Execution commands", "", ctx["execution_md"], "", "### Code changes versus the base commit", "", "```", ctx["code_changes"], "```", "", "### Software versions", "", "```", ctx["versions"], "```", ""]
    md_path.write_text("\n".join(L))
    return md_path


# --------------------------------------------------------------------------------------------------
# main builder
# --------------------------------------------------------------------------------------------------


def rebuild_run_report(run_dir: Path, out_path: Path, *, root_dir: Optional[Path] = None, is_root: bool = False, runs: Optional[Dict[str, Path]] = None,
                       previous_run: Optional[Path] = None, title: Optional[str] = None, n_per_gene_inline: int = 12, backup: bool = True) -> Dict[str, object]:
    run_dir, out_path = Path(run_dir), Path(out_path)
    out_dir = out_path.parent
    root_dir = Path(root_dir) if root_dir else out_dir
    runs = {k: Path(v) for k, v in (runs or {}).items()}
    cfg = Config.from_yaml(run_dir / "logs" / "resolved_config.yaml")
    tables = load_tables(run_dir)
    # existing renders (for captions / cards recovery), then back them up
    old_html = [out_dir / "report.html", out_dir / BACKUP_NAME, run_dir / "report.html", run_dir / BACKUP_NAME]
    if backup and out_path.is_file() and not (out_dir / BACKUP_NAME).is_file():
        shutil.copy2(out_path, out_dir / BACKUP_NAME)
        logger.info("Backed up %s -> %s", out_path, out_dir / BACKUP_NAME)
    figs, missing = load_figures(run_dir, old_html)
    old_cards = _cards_from_html(old_html)
    T = lambda k: tables.get(k)

    def csv_href(name: str, base: Path = run_dir) -> Optional[str]:
        p = base / "tables" / f"{name}.csv"
        return _rel(p, out_dir) if p.is_file() else None

    def tab(name: str, max_rows: int = 60, df: Optional[pd.DataFrame] = None, base: Path = run_dir, note: str = "") -> Markup:
        return table_html(T(name) if df is None else df, name, csv_href(name, base), max_rows, note)

    # ---- per-cell slot tables ------------------------------------------------------------------
    per_cell, slot_summary = per_cell_assignment_tables(run_dir, cfg)
    if per_cell is not None:
        per_cell.to_csv(run_dir / "tables" / f"{PER_CELL_TABLE}.csv", index=False)
        slot_summary.to_csv(run_dir / "tables" / f"{SLOT_SUMMARY_TABLE}.csv", index=False)
        tables[PER_CELL_TABLE], tables[SLOT_SUMMARY_TABLE] = per_cell, slot_summary

    # ---- key numbers -------------------------------------------------------------------------
    lanes = sorted(T("cell_counts_before_after")["lane_id"].astype(str).unique()) if T("cell_counts_before_after") is not None else []
    lanes = [l for l in lanes if l != "ALL"]
    pooled = "ALL" if len(lanes) > 1 else (lanes[0] if lanes else "ALL")
    cc = T("cell_counts_before_after").set_index("lane_id") if T("cell_counts_before_after") is not None else pd.DataFrame()
    n_in = int(cc.loc[pooled, "input_cells"]) if pooled in cc.index else None
    n_ret = int(cc.loc[pooled, "final_cells_retained"]) if pooled in cc.index else None
    qs = T("qc_steps")
    n_genes = int(qs["genes_after"].iloc[-1]) if qs is not None and "genes_after" in qs.columns else old_cards.get("Genes", "n/a")
    pa = T("pair_assignment_per_lane").set_index("lane_id") if T("pair_assignment_per_lane") is not None else pd.DataFrame()
    st = lambda k: int(pa.loc[pooled, k]) if (pooled in pa.index and k in pa.columns) else 0
    n_strict = int(pa.loc[pooled, "n_pair_assigned_primary"]) if pooled in pa.index and "n_pair_assigned_primary" in pa.columns else st(dg.STATUS_PAIR_TARGETING) + st(dg.STATUS_PAIR_NTC)
    hc = T("pair_perturbation_hit_counts_per_lane").set_index("lane_id") if T("pair_perturbation_hit_counts_per_lane") is not None else pd.DataFrame()
    tested = int(hc.loc[pooled, "targets_tested"]) if pooled in hc.index else 0
    hits = int(hc.loc[pooled, "targets_hit"]) if pooled in hc.index else 0
    n_clusters = len(T("cluster_sizes")) if T("cluster_sizes") is not None else old_cards.get("Clusters", "n/a")
    n_targets = len(T("target_cells_per_lane")) if T("target_cells_per_lane") is not None else old_cards.get("Target genes", "n/a")
    prim_tab = T("pair_perturbation_primary")
    n_ntc = int(prim_tab[prim_tab.lane_id == pooled]["n_ntc_pair_cells"].max()) if prim_tab is not None and len(prim_tab) else st(dg.STATUS_PAIR_NTC)
    pct = lambda a, b: f"{100.0 * a / b:.1f} %" if b else "n/a"
    summary_cards = [("Cells analysed", f"{n_ret:,}" if n_ret is not None else "n/a"), ("Cells loaded", f"{n_in:,}" if n_in is not None else "n/a"), ("Genes", f"{n_genes:,}" if isinstance(n_genes, int) else str(n_genes)),
                     ("Samples / lanes", f"{len(lanes)}"), ("Target genes", f"{n_targets}"), ("Leiden clusters", f"{n_clusters}"), ("Effective perturbations", f"{hits} / {tested}"),
                     ("Strict primary pairs", f"{n_strict:,} ({pct(n_strict, n_ret or 1)})"), ("Execution mode", old_cards.get("Execution mode", "STANDARD"))]
    root_manifest = json.load(open(root_dir / "run_manifest.json")) if (root_dir / "run_manifest.json").is_file() else {}
    git = {"branch": root_manifest.get("git_branch", "n/a"), "commit": root_manifest.get("git_commit", "n/a"), "commit_short": str(root_manifest.get("git_commit", "n/a"))[:12],
           "base": root_manifest.get("git_base_commit", "")}
    h5ads = sorted(run_dir.glob("*.h5ad"))
    meta_rows = [("Pipeline version", __version__), ("Branch / commit", f"{git['branch']} @ {git['commit']}" + (f" (base {git['base']})" if git["base"] else "")),
                 ("Configuration", f"{root_manifest.get('config', '')}  (resolved: {_rel(run_dir / 'logs' / 'resolved_config.yaml', out_dir)})"),
                 ("Input mode", cfg.resolved_mode() if hasattr(cfg, "resolved_mode") else cfg.input.mode), ("Input source", "; ".join(f"{k}: {v}" for k, v in (cfg.input.mtx_dirs or {}).items())),
                 ("Guide matrices", "; ".join(f"{k}: {v}" for k, v in (cfg.input.guide_mtx_dirs or {}).items())), ("Sample metadata", cfg.metadata.file or "none"),
                 ("Assignment mode", f"{cfg.guides.assignment_mode}; pair reference {cfg.guides.pair_map_file or cfg.guides.pair_reference}"),
                 ("Output directory", str(run_dir)), ("Processed H5AD", "; ".join(_rel(h, out_dir) for h in h5ads) or "n/a"), ("Report generated", _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))]
    pseudocount = f"{float(getattr(cfg.guides, 'dominance_pseudocount', 1.0)):g}"
    s1_primary = bool(getattr(cfg.guides, "designed_targeting_plus_ntc_primary", True))
    rule_text = (f"For each scaffold slot (A and C) independently: top guide UMI ≥ {cfg.guides.min_umi} and (top guide UMI + {pseudocount}) / (second guide UMI + {pseudocount}) ≥ {cfg.guides.dominance_ratio:g}. "
                 f"A strict primary pair needs both slots resolved and a documented construct shared by the two features; strict primary labels are targeting–targeting constructs (pair_targeting) and NTC–NTC constructs (pair_non_targeting). "
                 + ("Designed targeting+NTC constructs are a sensitivity class, excluded from primary testing. " if not s1_primary else "Designed targeting+NTC constructs are pooled into the primary targeting label. ")
                 + f"Strict primary pairs: {n_strict:,} of {n_ret:,} QC-pass cells ({pct(n_strict, n_ret or 1)}); the remaining cells are ambiguous, unresolved, incomplete, below threshold or without guide and carry no perturbation identity.")
    n_sens = st(dg.STATUS_PAIR_TARGET_NTC)
    warnings = [
        f"Only {pct(n_strict, n_ret or 1)} of QC-pass cells carry a strict primary perturbation identity; {pct((n_ret or 0) - n_strict, n_ret or 1)} are ambiguous, unresolved, incomplete, below threshold, sensitivity-only or guide-free and are excluded from primary testing.",
        "Hits are target-transcript depletion associations (KS FDR < %g and log2FC < %g); CRISPR modality, effector and cell line are not documented, so no knockout / knockdown mechanism is claimed." % (cfg.perturbation.fdr_alpha, cfg.perturbation.max_log2fc_for_hit),
        "HF011 / HF012 and A / B are not defined by any experimental document; agreement across wells is well-level support, not biological replication.",
        "Guide multiplicity is high (many cells carry several strong guides per scaffold); multi-construct cells appear as scaffold-ambiguous, dual-target or unresolved and are never collapsed onto one construct.",
        "No batch correction was applied (batch_key: null); Leiden clusters are computed per object and are not comparable across runs. Doublets are not removed.",
        "The single-guide diagnostic is shown for comparison only; no biological result uses it.",
    ]
    if missing:
        warnings.append(f"{len(missing)} figure(s) listed in the manifest are missing or empty and were not embedded (see report_rebuild.md).")

    # ---- figures -------------------------------------------------------------------------------
    by_sec: Dict[str, List[FigureRecord]] = {}
    for r in figs:
        by_sec.setdefault(r.section, []).append(r)
    def sec_html(section: str, only_in_report: bool = True) -> List[Markup]:
        recs = [r for r in by_sec.get(section, []) if (r.in_report or not only_in_report)]
        return [figure_html(r, out_dir) for r in recs]
    gallery = lambda section: [figure_html(r, out_dir, small=True) for r in sorted(by_sec.get(section, []), key=lambda r: (not r.in_report, r.name))]
    figures = {"qc": sec_html("qc"), "guides": sec_html("guides"), "clustering": sec_html("clustering"), "perturbation": sec_html("perturbation"), "enrichment": sec_html("enrichment"),
               "ps_score": sec_html("ps_score"), "ps_lda_overview": [figure_html(r, out_dir) for r in by_sec.get("ps_score/lda", []) if r.in_report and not r.name.startswith("ps_lda_")][:2],
               "lochness": sec_html("lochness"), "distance": sec_html("distance"), "distance_space": sec_html("distance_space"), "modules": sec_html("modules")}
    galleries = {"per_gene": gallery("perturbation/per_gene"), "ecdf": gallery("perturbation/ecdf"), "enrichment_per_target": gallery("enrichment/per_target"),
                 "ps_per_target": gallery("ps_score/per_target"), "ps_lda": gallery("ps_score/lda"), "lochness_per_target": gallery("lochness/per_target")}
    has_ps = bool(by_sec.get("ps_score") or T("ps_score") is not None)
    has_lochness = bool(by_sec.get("lochness") or T("lochness") is not None)
    has_distance = T("perturbation_distance") is not None
    has_distance_space = T("perturbation_space_coordinates") is not None or T("phenotype_modules") is not None
    has_modules = T("cofunctional_modules") is not None or bool(by_sec.get("modules"))
    has_meta = T("perturbation_meta") is not None
    n_embedded = sum(len(v) for v in figures.values()) + sum(len(v) for v in galleries.values())

    # ---- guide cards ---------------------------------------------------------------------------
    guide_cards = [("Strict primary pairs", f"{n_strict:,}"), ("pair_targeting", f"{st(dg.STATUS_PAIR_TARGETING):,}"), ("pair_non_targeting (control)", f"{st(dg.STATUS_PAIR_NTC):,}"),
                   ("Targeting+NTC sensitivity", f"{n_sens:,}"), ("Dual-target ambiguous", f"{st(dg.STATUS_DUAL_TARGET):,}"), ("Unresolved pair", f"{st(dg.STATUS_UNRESOLVED):,}"),
                   ("Scaffold-ambiguous", f"{st('ambiguous_scaffold_A') + st('ambiguous_scaffold_C') + st('ambiguous_scaffold_A_and_C'):,}"), ("Incomplete pair", f"{st(dg.STATUS_INCOMPLETE):,}"),
                   ("Below min_umi / no guide", f"{st(dg.STATUS_BELOW_MIN_UMI):,} / {st(dg.STATUS_NO_GUIDE):,}")]

    # ---- perturbation cards + strata comparison ---------------------------------------------------
    sk = T("skipped")
    bp = T("pair_perturbation_by_pair")
    n_constructs = int(hc.loc[pooled, "constructs_tested"]) if pooled in hc.index and "constructs_tested" in hc.columns else 0
    n_constructs_hit = int(hc.loc[pooled, "constructs_hit"]) if pooled in hc.index and "constructs_hit" in hc.columns else 0
    perturbation_cards = [("Targets tested", f"{tested}"), ("Depletion associations (hits)", f"{hits}"), ("NTC-pair control cells", f"{n_ntc:,}"), ("Targets not testable", f"{len(sk) if sk is not None else 0}"),
                          ("Constructs tested / hit", f"{n_constructs} / {n_constructs_hit}")]
    bt = T("pair_perturbation_by_target")
    strata_cmp = None
    if bt is not None and len(bt):
        sub = bt[(bt.control == "ntc") & (bt.lane_id == pooled)]
        if len(sub):
            strata_cmp = sub.pivot_table(index="target_gene", columns="assignment_stratum", values=["n_target_pair_cells", "log2fc", "fdr_ks", "is_hit"], aggfunc="first")
            strata_cmp.columns = [f"{v}__{s}" for v, s in strata_cmp.columns]
            strata_cmp = strata_cmp.reset_index()
            strata_cmp.to_csv(run_dir / "tables" / "pair_perturbation_strata_comparison.csv", index=False)
            tables["pair_perturbation_strata_comparison"] = strata_cmp
    prim_pooled = prim_tab[prim_tab.lane_id == pooled].sort_values("log2fc") if prim_tab is not None and len(prim_tab) else None
    bp_pooled = bp[bp.lane_id == pooled].sort_values("log2fc") if bp is not None and len(bp) else None

    # ---- enrichment ------------------------------------------------------------------------------
    enr_full, enr = T("enrichment_full"), T("enrichment")
    enrichment = None
    if enr_full is not None and len(enr_full):
        sig_col = next((c for c in enr_full.columns if c.lower() == "significant"), None)
        lp_col = next((c for c in enr_full.columns if c.lower().replace("_", " ") == "low power"), None)
        tcol = next((c for c in enr_full.columns if c.lower() in ("target", "target_gene")), enr_full.columns[0])
        ccol = next((c for c in enr_full.columns if c.lower() == "cluster"), None)
        sig = enr_full[sig_col].astype(str).str.lower().isin(["true", "1"]) if sig_col else pd.Series(False, index=enr_full.index)
        enrichment = {"n_tests": len(enr_full), "n_hits": int(sig.sum()), "n_targets_with_hits": int(enr_full.loc[sig, tcol].nunique()), "n_clusters": int(enr_full[ccol].nunique()) if ccol else "n/a",
                      "n_low_power": int(enr_full[lp_col].astype(str).str.lower().isin(["true", "1"]).sum()) if lp_col else 0, "control_label": "NTC pairs (pair_non_targeting)",
                      "omnibus_text": _omnibus_from_html(old_html)}

    # ---- module cards -----------------------------------------------------------------------------
    ps_t, lo_t, di_t, mo_t, hub_t, ds_t, nb_t = T("ps_score"), T("lochness"), T("perturbation_distance"), T("cofunctional_modules"), T("tf_hubs"), T("perturbation_space_coordinates"), T("perturbation_neighbors")
    ps_cards = [("Targets scored", f"{len(ps_t)}"), ("Median % knocked down", f"{ps_t['pct_successful_kd'].median():.1f} %"), ("Median % escapers", f"{ps_t['pct_escaper'].median():.1f} %"),
                ("Best target", f"{ps_t.sort_values('pct_successful_kd', ascending=False)['target_gene'].iloc[0]} ({ps_t['pct_successful_kd'].max():.1f} %)")] if ps_t is not None and len(ps_t) else []
    lochness_cards = [("Perturbations scored", f"{len(lo_t)}"), ("Neighbours per cell", f"{cfg.lochness.n_neighbors}"), ("Self-enriched above cut", f"{int((lo_t['mean_lochness_in_own_cells'] > cfg.lochness.enrichment_cut).sum())}"),
                      ("Strongest", f"{lo_t.sort_values('mean_lochness_in_own_cells', ascending=False)['target_gene'].iloc[0]} ({lo_t['mean_lochness_in_own_cells'].max():.2f})")] if lo_t is not None and len(lo_t) else []
    distance_cards = [("Targets tested", f"{len(di_t)}"), (f"Significant (FDR < {cfg.distance.fdr_threshold})", f"{int(di_t['significant'].astype(str).str.lower().isin(['true', '1']).sum())}"),
                      ("Largest distance", f"{di_t.sort_values('energy_distance', ascending=False)['target_gene'].iloc[0]} ({di_t['energy_distance'].max():.3g})"), ("Metric", f"{cfg.distance.primary_metric}" + (f" + {cfg.distance.secondary_metric}" if cfg.distance.secondary_metric else ""))] if di_t is not None and len(di_t) else []
    modules_cards = [("Co-functional modules", f"{mo_t['module'].nunique()}"), ("Perturbations in modules", f"{len(mo_t)}"), ("Gene programs", f"{len(T('program_summary')) if T('program_summary') is not None else 'n/a'}"),
                     ("Top hub", f"{hub_t.sort_values('n_de_genes', ascending=False)['target_gene'].iloc[0]} ({int(hub_t['n_de_genes'].max())} DE genes)" if hub_t is not None and len(hub_t) else "n/a")] if mo_t is not None and len(mo_t) else []

    # ---- top-six selections (deterministic; documented rule) --------------------------------------
    topsix: Dict[str, Dict[str, object]] = {}

    def add_topsix(key, df, support_col, min_support, rank_cols, label, section, prefix, extra_filter=None, cols=None):
        t, rule, note = _top_six(df, support_col, min_support, rank_cols, label, extra_filter)
        if t is None or not len(t):
            return
        show = t[[c for c in (cols or list(t.columns)) if c in t.columns]]
        recs = {r.name: r for r in by_sec.get(section, [])} if section else {}
        fig_paths = [(str(g), _rel(recs[_slug(f"{prefix}{g}")].path, out_dir)) for g in t["target_gene"] if section and _slug(f"{prefix}{g}") in recs]
        show.to_csv(run_dir / "tables" / f"top6_{key}.csv", index=False)
        topsix[key] = {"rule": rule, "note": note, "df": show, "table": table_html(show, f"top6_{key}", csv_href(f"top6_{key}"), 10),
                       "figures": _figs_for(list(t["target_gene"]), by_sec, section, prefix, out_dir) if section else [], "fig_paths": fig_paths}

    if prim_pooled is not None and len(prim_pooled):
        pp = prim_pooled.copy()
        add_topsix("perturbation", pp, "n_target_pair_cells", cfg.perturbation.min_cells_per_target, [("fdr_ks", True), ("log2fc", True)], "Direct perturbation (strict pairs vs NTC pairs)", "perturbation/per_gene", "perturbation_",
                   extra_filter=lambda d: d["n_ntc_pair_cells"].astype(float) >= cfg.perturbation.min_control_cells, cols=["rank", "target_gene", "measured_transcript", "n_target_pair_cells", "n_ntc_pair_cells", "log2fc", "pct_knockdown", "fdr_ks", "neg_log10_fdr", "is_hit"])
    if enr_full is not None and len(enr_full):
        tcol = next((c for c in enr_full.columns if c.lower() in ("target", "target_gene")), enr_full.columns[0])
        fcol = next((c for c in enr_full.columns if c.lower() == "fdr"), None)
        em = T("enrichment_effect_magnitude")
        if fcol and em is not None:
            best = enr_full.groupby(tcol)[fcol].min().rename("min_fdr").reset_index().rename(columns={tcol: "target_gene"})
            emx = em.merge(best, on="target_gene", how="left")
            add_topsix("enrichment", emx, "n_cells", cfg.enrichment.min_cells_per_target, [("min_fdr", True), ("composition_shift_pct", False)], "Cluster enrichment", "enrichment/per_target", "enrichment_",
                       cols=["rank", "target_gene", "n_cells", "n_significant_clusters", "min_fdr", "composition_shift_pct"])
    if ps_t is not None and len(ps_t):
        add_topsix("ps_score", ps_t, "n_perturbed_cells", cfg.ps_score.min_cells_per_target, [("pct_successful_kd", False), ("mean_ps", False)], "PS score (no FDR is defined; the analysis-specific score is the fraction of cells called knocked down)", "ps_score/per_target", "ps_quadrant_",
                   extra_filter=lambda d: d["n_control_cells"].astype(float) >= cfg.ps_score.min_control_cells, cols=["rank", "target_gene", "n_perturbed_cells", "n_control_cells", "mean_ps", "median_ps", "pct_successful_kd", "pct_escaper", "net_pct_kd"])
    if lo_t is not None and len(lo_t):
        add_topsix("lochness", lo_t, "n_cells", cfg.lochness.min_cells_per_target, [("mean_lochness_in_own_cells", False), ("pct_cells_enriched", False)], "lochNESS (no FDR is defined; the analysis-specific score is the mean lochNESS in the target's own cells)", "lochness/per_target", "lochness_",
                   cols=["rank", "target_gene", "n_cells", "mean_lochness_in_own_cells", "mean_lochness_all_cells", "max_lochness", "pct_cells_enriched", "top_cluster"])
    if di_t is not None and len(di_t):
        add_topsix("distance", di_t, "n_cells", cfg.distance.min_cells, [("fdr", True), ("energy_distance", False)], "Energy distance / MMD (permutation FDR, then distance)", None, "",
                   cols=["rank", "target_gene", "n_cells", "n_control", "energy_distance"] + [c for c in ("mmd", "mmd_distance", "mmd_pvalue", "mmd_fdr") if c in di_t.columns] + ["pvalue", "fdr", "significant"])
    if ds_t is not None and len(ds_t) and di_t is not None:
        merged = di_t.merge(ds_t, on="target_gene", how="inner")
        pm = T("phenotype_modules")
        if pm is not None:
            merged = merged.merge(pm, on="target_gene", how="left")
        if nb_t is not None and "target" in nb_t.columns:
            nn1 = nb_t[nb_t["rank"] == 1][["target", "neighbor", "distance"]].rename(columns={"target": "target_gene", "neighbor": "nearest_neighbor", "distance": "nearest_distance"})
            merged = merged.merge(nn1, on="target_gene", how="left")
        add_topsix("distance_space", merged, "n_cells", cfg.distance_space.min_cells, [("fdr", True), ("energy_distance", False)], "Perturbation space (targets ranked by their control-distance FDR, then energy distance; coordinates, phenotype module and nearest neighbour shown)", None, "",
                   cols=["rank", "target_gene", "n_cells", "energy_distance", "fdr", "phenotype_module", "nearest_neighbor", "nearest_distance", "PCoA1", "PCoA2"])
    if hub_t is not None and len(hub_t):
        add_topsix("modules", hub_t, "n_cells", cfg.modules.min_cells_per_perturbation, [("n_de_genes", False)], "Network hubs (perturbations ranked by the number of differentially expressed genes versus NTC pairs; module membership shown)", None, "",
                   cols=["rank", "target_gene", "module", "n_cells", "n_de_genes"])

    # ---- module completion status ------------------------------------------------------------------
    status_rows = []
    for mod, enabled, tabs_needed, secs in (("enrichment", cfg.enrichment.enabled, ["enrichment", "enrichment_full"], ["enrichment", "enrichment/per_target"]), ("modules", cfg.modules.enabled, ["cofunctional_modules", "gene_programs", "program_enrichment"], ["modules"]),
                                            ("ps_score", cfg.ps_score.enabled, ["ps_score"], ["ps_score", "ps_score/per_target", "ps_score/lda"]), ("lochness", cfg.lochness.enabled, ["lochness"], ["lochness", "lochness/per_target"]),
                                            ("distance", cfg.distance.enabled, ["perturbation_distance"], ["distance"]), ("distance_space", cfg.distance_space.enabled, ["perturbation_space_coordinates", "phenotype_modules"], ["distance_space"]),
                                            ("meta_analysis", cfg.meta_analysis.enabled, ["perturbation_meta"], []), ("harmony / batch correction", cfg.cluster.batch_key is not None, [], []), ("doublet removal", False, [], [])):
        have_t = [t for t in tabs_needed if T(t) is not None]
        n_f = sum(len(by_sec.get(sc, [])) for sc in secs)
        st_ = ("disabled (by design)" if not enabled else ("completed" if (len(have_t) == len(tabs_needed) and (n_f > 0 or not secs)) else ("partial" if have_t or n_f else "NOT RUN / no outputs")))
        status_rows.append({"module": mod, "enabled_in_config": bool(enabled), "tables_present": ";".join(have_t) or "-", "n_figures": n_f, "status": st_})
    module_status = pd.DataFrame(status_rows)
    module_status.to_csv(run_dir / "tables" / "module_status.csv", index=False)
    tables["module_status"] = module_status

    # ---- root-only context -----------------------------------------------------------------------
    run_links, root_tables = [], {}
    if is_root and runs:
        for k, d in runs.items():
            rec_figs, _ = load_figures(d, [d / "report.html", d / BACKUP_NAME])
            key = [figure_html(r, out_dir, small=True) for r in rec_figs if r.name in KEY_SAMPLE_FIGURES]
            h5 = sorted(d.glob("*processed.h5ad"))
            run_links.append({"name": k, "html": _rel(d / "report.html", out_dir), "md": _rel(d / "report.md", out_dir), "figures": _rel(d / "figures", out_dir), "tables": _rel(d / "tables", out_dir),
                              "h5ad": _rel(h5[0], out_dir) if h5 else "", "key_figures": key})
        rows = []
        for k, d in runs.items():
            t = load_tables(d)
            lane = "ALL" if k == "combined" else k
            c2 = t.get("cell_counts_before_after"); p2 = t.get("pair_assignment_per_lane"); h2 = t.get("pair_perturbation_hit_counts_per_lane")
            g = lambda df, col: (df.set_index("lane_id").loc[lane, col] if df is not None and lane in df["lane_id"].astype(str).tolist() else np.nan)
            n_r = g(c2, "final_cells_retained"); n_p = g(p2, "n_pair_assigned_primary")
            rows.append({"run": k, "input_cells": g(c2, "input_cells"), "qc_pass_cells": n_r, "strict_primary_pairs": n_p, "strict_primary_pct": round(100.0 * float(n_p) / float(n_r), 1) if pd.notna(n_r) and n_r else np.nan,
                         "pair_targeting": g(p2, dg.STATUS_PAIR_TARGETING), "pair_non_targeting": g(p2, dg.STATUS_PAIR_NTC), "targeting_plus_ntc_sensitivity": g(p2, dg.STATUS_PAIR_TARGET_NTC),
                         "targets_tested": g(h2, "targets_tested"), "targets_hit": g(h2, "targets_hit"), "constructs_tested": g(h2, "constructs_tested"), "constructs_hit": g(h2, "constructs_hit"),
                         "report": _rel(d / "report.html", out_dir)})
        root_tables["run_index"] = pd.DataFrame(rows)
        root_tables["run_index"].to_csv(root_dir / "tables" / "run_index.csv", index=False)
        ms_rows = []
        for k, d in runs.items():
            p_ms = d / "tables" / "module_status.csv"
            if p_ms.is_file():
                ms_rows.append(pd.read_csv(p_ms).assign(run=k))
        if ms_rows:
            root_tables["module_status_all_runs"] = pd.concat(ms_rows, ignore_index=True)
            root_tables["module_status_all_runs"].to_csv(root_dir / "tables" / "module_status_all_runs.csv", index=False)
        for name in ("target_support_matrix_across_runs", "pair_perturbation_hit_counts_all_runs", "pair_assignment_per_lane_all_runs", "previous_vs_new_summary", "previous_vs_new_target_hits"):
            p = root_dir / "tables" / f"{name}.csv"
            if p.is_file():
                root_tables[name] = pd.read_csv(p)
        if "target_support_matrix_across_runs" in root_tables:
            root_tables["support_classes"] = root_tables["target_support_matrix_across_runs"]["support_class"].value_counts().rename_axis("support_class").reset_index(name="targets")
        p = root_dir / "audit" / "previous_vs_new_reference_comparison.csv"
        if p.is_file():
            root_tables["previous_vs_new_reference_comparison"] = pd.read_csv(p)

    # ---- tables html -------------------------------------------------------------------------------
    tables_html: Dict[str, Markup] = {}
    caps = {"cluster_composition": 120, "guide_representation": 60, "guide_feature_representation": 60, "pair_perturbation_primary": 250, "pair_perturbation_by_pair": 250, "perturbation": 120, "enrichment": 150,
            "enrichment_composition": 60, "enrichment_effect_magnitude": 60, "target_support_matrix": 80, "pair_resolution_detail_per_lane": 60, PER_CELL_TABLE: 40, "figure_manifest": 400,
            "target_cells_per_lane": 80, "construct_cells_per_lane": 80, "pair_perturbation_strata_comparison": 80}
    for name in ("qc_steps", "qc_summary", "cell_counts_before_after", "qc_metrics_per_lane_before_after", "pair_assignment_per_lane", "pair_resolution_detail_per_lane", "construct_type_per_lane", SLOT_SUMMARY_TABLE,
                 PER_CELL_TABLE, "pair_guide_qc_per_lane", "strong_guides_per_scaffold_per_lane", "guide_gex_barcode_overlap", "off_design_umi_fraction_per_lane", "target_cells_per_lane", "construct_cells_per_lane",
                 "guide_representation", "guide_feature_representation", "single_guide_diagnostic_vs_pair", "clusters", "cluster_sizes", "cluster_composition", "pair_perturbation_hit_counts_per_lane", "perturbation",
                 "skipped", "target_support_matrix", "enrichment", "enrichment_effect_magnitude", "enrichment_composition", "figure_manifest",
                 "ps_score", "ps_vs_perturbation", "ps_skipped", "lochness", "lochness_by_cluster", "perturbation_distance", "phenotype_modules", "perturbation_space_coordinates", "perturbation_neighbors",
                 "cofunctional_modules", "tf_hubs", "module_program_strength", "module_connectivity", "program_summary", "program_enrichment", "gene_programs", "program_activity_by_cluster", "perturbation_meta", "module_status"):
        tables_html[name] = tab(name, caps.get(name, 60))
    tables_html["pair_perturbation_primary"] = tab("pair_perturbation_primary", caps["pair_perturbation_primary"], df=prim_pooled, note=f"pooled lane <code>{pooled}</code>; every lane is in the CSV")
    tables_html["pair_perturbation_by_pair"] = tab("pair_perturbation_by_pair", caps["pair_perturbation_by_pair"], df=bp_pooled, note=f"pooled lane <code>{pooled}</code>")
    tables_html["strata_comparison"] = tab("pair_perturbation_strata_comparison", caps["pair_perturbation_strata_comparison"], df=strata_cmp)
    input_map = {**{f"GEX {k}": v for k, v in (cfg.input.mtx_dirs or {}).items()}, **{f"guides {k}": v for k, v in (cfg.input.guide_mtx_dirs or {}).items()},
                 "sample metadata": cfg.metadata.file, "pair reference": cfg.guides.pair_map_file or cfg.guides.pair_reference}
    tables_html["inputs"] = table_html(pd.DataFrame([{"input": k, "path": v} for k, v in input_map.items()]), "inputs", None, 40)
    outs = [{"deliverable": f"processed / all-cells H5AD", "path": _rel(h, out_dir)} for h in h5ads] + [{"deliverable": "tables/", "path": _rel(run_dir / "tables", out_dir)}, {"deliverable": "figures/", "path": _rel(run_dir / "figures", out_dir)},
            {"deliverable": "Markdown report", "path": _rel(run_dir / "report.md", out_dir)}, {"deliverable": "run log", "path": _rel(run_dir / "logs" / "run.log", out_dir)}, {"deliverable": "resolved config", "path": _rel(run_dir / "logs" / "resolved_config.yaml", out_dir)}]
    if is_root:
        outs += [{"deliverable": "run manifest", "path": _rel(root_dir / "run_manifest.json", out_dir)}, {"deliverable": "execution record", "path": _rel(root_dir / "execution_commands.md", out_dir)}, {"deliverable": "audit/", "path": _rel(root_dir / "audit", out_dir)}]
    outs = [dict(o) for o in outs]
    odf = pd.DataFrame(outs)
    odf["path"] = odf["path"].map(lambda x: Markup(f'<a href="{_html.escape(x)}">{_html.escape(x)}</a>'))
    tables_html["outputs"] = Markup('<div class="scroll">' + odf.to_html(index=False, escape=False, border=0) + "</div>")
    for name, df in root_tables.items():
        tables_html[name] = table_html(df, name, csv_href(name, root_dir), 120)
    for name in ("run_index", "support_classes", "target_support_matrix_across_runs", "pair_perturbation_hit_counts_all_runs", "pair_assignment_per_lane_all_runs", "previous_vs_new_reference_comparison", "previous_vs_new_summary", "previous_vs_new_target_hits", "module_status_all_runs"):
        tables_html.setdefault(name, Markup(""))
    caps.update({"perturbation_neighbors": 60, "gene_programs": 60, "program_enrichment": 80, "perturbation_meta": 60, "lochness_by_cluster": 60, "perturbation_space_coordinates": 60})

    # ---- reproducibility ------------------------------------------------------------------------------
    exec_md = (root_dir / "execution_commands.md").read_text() if (root_dir / "execution_commands.md").is_file() else "execution_commands.md not found"
    repro_rows = [("Branch / commit", f"{git['branch']} @ {git['commit']}"), ("Base commit", git["base"] or "n/a"), ("SLURM job ids", ", ".join(map(str, root_manifest.get("slurm_job_ids", []))) or "see execution_commands.md"),
                  ("Conda environment", f"{root_manifest.get('conda_env', os.environ.get('CONDA_DEFAULT_ENV', ''))} ({root_manifest.get('conda_prefix', os.environ.get('CONDA_PREFIX', ''))})"),
                  ("Pipeline version", __version__), ("Configuration", str(root_manifest.get("config", cfg.run.name))), ("Run start / end (run.log)", json.dumps(root_manifest.get("run_times", {}).get("combined" if is_root else _run_key(run_dir), {}))),
                  ("Report renderer", RENDERER), ("Report generated", _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))]
    code_changes = (root_manifest.get("git_changed_files_vs_base", "") or "") + "\n\nworking tree:\n" + (root_manifest.get("git_status_short", "") or "")
    audit_rows = []
    if is_root and (root_dir / "audit").is_dir():
        for p in sorted((root_dir / "audit").iterdir()):
            if p.is_file():
                audit_rows.append((p.name, Markup(f'<a href="{_html.escape(_rel(p, out_dir))}">{_html.escape(_rel(p, out_dir))}</a>')))

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=select_autoescape(["html"]))
    tpl = env.get_template("report_full.html")
    html = tpl.render(
        title=title or (f"{cfg.report.title} — root report" if is_root else cfg.report.title), run_name=cfg.run.name, version=__version__, generated_at=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        report_kind="root index and full summary" if is_root else "per-run full report", git=git, is_root=is_root, cfg=cfg, summary_cards=summary_cards, meta_rows=meta_rows, rule_text=rule_text, warnings=warnings,
        run_links=run_links, tables=tables_html, figures=figures, galleries=galleries, guide_cards=guide_cards, pseudocount=pseudocount,
        pair_reference_name=os.path.basename(str(cfg.guides.pair_map_file or cfg.guides.pair_reference or "")), per_cell_table_name=f"tables/{PER_CELL_TABLE}.csv", per_cell_table_href=csv_href(PER_CELL_TABLE),
        perturbation_cards=perturbation_cards, n_per_gene_inline=n_per_gene_inline, enrichment=enrichment, previous_run=str(previous_run) if previous_run else "n/a",
        repro_rows=repro_rows, config_yaml=yaml.safe_dump(cfg.to_dict(), sort_keys=False), execution_md=exec_md, code_changes=code_changes, versions=_versions(), n_figures=len(figs), n_embedded=n_embedded,
        audit_rows=audit_rows, renderer=RENDERER,
        has_ps=has_ps, has_lochness=has_lochness, has_distance=has_distance, has_distance_space=has_distance_space, has_modules=has_modules, has_meta=has_meta,
        ps_cards=ps_cards, lochness_cards=lochness_cards, distance_cards=distance_cards, modules_cards=modules_cards, topsix=topsix,
    )
    out_path.write_text(html, encoding="utf-8")
    # Markdown twin
    csv_paths = {n: _rel(run_dir / "tables" / f"{n}.csv", out_dir) for n in tables if (run_dir / "tables" / f"{n}.csv").is_file()}
    csv_paths.update({n: _rel(root_dir / "tables" / f"{n}.csv", out_dir) for n in root_tables if (root_dir / "tables" / f"{n}.csv").is_file()})
    raw_tables = dict(tables); raw_tables.update(root_tables); raw_tables["inputs"] = pd.DataFrame([{"input": k, "path": v} for k, v in input_map.items()])
    raw_tables["pair_perturbation_primary"] = prim_pooled if prim_pooled is not None else tables.get("pair_perturbation_primary"); raw_tables["pair_perturbation_by_pair"] = bp_pooled if bp_pooled is not None else tables.get("pair_perturbation_by_pair")
    ctx = dict(title=title or (f"{cfg.report.title} — root report" if is_root else cfg.report.title), run_name=cfg.run.name, report_kind="root index and full summary" if is_root else "per-run full report", generated_at=_dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
               version=__version__, git=git, summary_cards=summary_cards, meta_rows=meta_rows, rule_text=rule_text, warnings=warnings, fig_records=by_sec, raw_tables=raw_tables, csv_paths=csv_paths, topsix=topsix, is_root=is_root, run_links=run_links,
               guide_cards=guide_cards, perturbation_cards=perturbation_cards, enrichment=enrichment, has_ps=has_ps, has_lochness=has_lochness, has_distance=has_distance, has_distance_space=has_distance_space, has_modules=has_modules, has_meta=has_meta,
               ps_cards=ps_cards, lochness_cards=lochness_cards, distance_cards=distance_cards, modules_cards=modules_cards, previous_run=str(previous_run) if previous_run else "n/a", repro_rows=repro_rows, outputs_rows=outs,
               config_yaml=yaml.safe_dump(cfg.to_dict(), sort_keys=False), execution_md=exec_md, code_changes=code_changes, versions=_versions())
    md_path = out_path.with_suffix(".md")
    if md_path.is_file() and not md_path.with_name("report_textual_backup.md").is_file() and backup:
        shutil.copy2(md_path, md_path.with_name("report_textual_backup.md"))
    write_markdown(md_path, ctx)
    logger.info("Wrote %s (%.1f MB, %d figures embedded)", out_path, out_path.stat().st_size / 1e6, n_embedded)
    return {"report": str(out_path), "markdown": str(md_path), "size_mb": round(out_path.stat().st_size / 1e6, 1), "n_figures_manifest": len(figs), "n_figures_embedded": n_embedded, "missing_figures": missing,
            "n_tables": len(tables), "cells": n_ret, "strict_primary": n_strict, "targets_tested": tested, "targets_hit": hits, "modules": module_status.to_dict(orient="records"), "top6": {k: list(v["df"]["target_gene"]) for k, v in topsix.items()}}


def _run_key(run_dir: Path) -> str:
    return run_dir.name


def rebuild_all(root: Path, runs: Dict[str, Path], previous_run: Optional[Path] = None, title: Optional[str] = None) -> Dict[str, object]:
    """Per-run full reports for every run, then the root index report from the combined run."""
    root = Path(root)
    summary = {}
    for k, d in runs.items():
        summary[k] = rebuild_run_report(Path(d), Path(d) / "report.html", root_dir=root, is_root=False, title=title)
    comb = runs.get("combined") or list(runs.values())[-1]
    summary["root"] = rebuild_run_report(Path(comb), root / "report.html", root_dir=root, is_root=True, runs=runs, previous_run=previous_run, title=title)
    (root / "report_rebuild_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return summary
