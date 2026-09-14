"""Root report over several completed pair-guide runs (per-sample + combined).

``perturbseq-pipeline pair-report -c cfg.yaml --run HF011A=... --run combined=... -o ROOT``
writes ``ROOT/report.html`` (full primary pair-guide analysis report with the
per-run reports embedded by link and key figures inlined), ``ROOT/run_manifest.json``,
``ROOT/config_used.yaml`` and ``ROOT/README.md``.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import yaml

from . import dual_guides as dg
from .config import Config

logger = logging.getLogger(__name__)

_CSS = ("body{font-family:system-ui,sans-serif;margin:24px;max-width:1500px;color:#222}table.t{border-collapse:collapse;font-size:11px}"
        "table.t td,table.t th{border:1px solid #ddd;padding:2px 6px}figure{margin:10px 0}figcaption{font-size:10px;color:#666}"
        "h2{border-bottom:1px solid #ccc;margin-top:36px}h3{margin-top:24px}.warn{background:#fff4e5;padding:8px;border-left:4px solid #eda100}"
        "nav a{margin-right:12px}code{background:#f3f3f3;padding:1px 3px}")


def _img(path: Path, rel_root: Path) -> str:
    if not path.is_file():
        return f"<p class='warn'>missing figure {path}</p>"
    b = base64.b64encode(path.read_bytes()).decode()
    return f"<figure><img src='data:image/png;base64,{b}' style='max-width:100%'><figcaption>{os.path.relpath(path, rel_root)}</figcaption></figure>"


def _table(df: Optional[pd.DataFrame], n: int = 80) -> str:
    if df is None or not len(df):
        return "<p><i>not available</i></p>"
    return df.head(n).to_html(index=False, float_format=lambda x: f"{x:.3g}", classes="t", border=0, na_rep="")


def _csv(run_dir: Path, name: str) -> Optional[pd.DataFrame]:
    p = run_dir / "tables" / f"{name}.csv"
    return pd.read_csv(p) if p.is_file() else None


def _git(repo: Path) -> Dict[str, str]:
    out = {}
    for k, cmd in (("branch", ["git", "rev-parse", "--abbrev-ref", "HEAD"]), ("commit", ["git", "rev-parse", "HEAD"]),
                   ("status", ["git", "status", "--short"])):
        try:
            out[k] = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, check=False).stdout.strip()
        except Exception:  # pragma: no cover
            out[k] = "n/a"
    return out


def build_root_report(cfg: Config, runs: Dict[str, str], outdir: Path, audit_dir: Optional[Path] = None,
                      config_path: Optional[str] = None, job_ids: Optional[List[str]] = None) -> Path:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    run_dirs = {k: Path(v) for k, v in runs.items()}
    comb_key = "combined" if "combined" in run_dirs else list(run_dirs)[-1]
    samples = [k for k in run_dirs if k != comb_key]
    repo = Path(__file__).resolve().parents[2]
    git = _git(repo)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # ---- gather tables --------------------------------------------------------------
    cc = pd.concat([_csv(run_dirs[k], "cell_counts_before_after").assign(run=k) for k in run_dirs if _csv(run_dirs[k], "cell_counts_before_after") is not None], ignore_index=True)
    pa = pd.concat([_csv(run_dirs[k], "pair_assignment_per_lane").assign(run=k) for k in run_dirs if _csv(run_dirs[k], "pair_assignment_per_lane") is not None], ignore_index=True)
    pq = pd.concat([_csv(run_dirs[k], "pair_guide_qc_per_lane").assign(run=k) for k in run_dirs if _csv(run_dirs[k], "pair_guide_qc_per_lane") is not None], ignore_index=True)
    hc = pd.concat([_csv(run_dirs[k], "pair_perturbation_hit_counts_per_lane").assign(run=k) for k in run_dirs if _csv(run_dirs[k], "pair_perturbation_hit_counts_per_lane") is not None], ignore_index=True)
    prim = {k: _csv(run_dirs[k], "pair_perturbation_primary") for k in run_dirs}
    sg = pd.concat([_csv(run_dirs[k], "single_guide_diagnostic_vs_pair").assign(run=k) for k in run_dirs if _csv(run_dirs[k], "single_guide_diagnostic_vs_pair") is not None], ignore_index=True)
    clusters = pd.concat([_csv(run_dirs[k], "cluster_sizes").assign(run=k) for k in run_dirs if _csv(run_dirs[k], "cluster_sizes") is not None], ignore_index=True)

    # ---- cross-run target support -----------------------------------------------------------
    targets = sorted(set().union(*[set(df["target_gene"]) for df in prim.values() if df is not None]))
    rows = []
    for t in targets:
        r = {"target_gene": t}
        n_t = n_h = 0
        for k in samples:
            df = prim.get(k)
            sub = df[(df.target_gene == t)] if df is not None else pd.DataFrame()
            sub = sub[sub.lane_id != "ALL"] if len(sub) else sub
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
        r["well_level_support"] = f"{n_h}/{n_t} per-sample runs" if n_t else "not tested per sample"
        ch = r.get("combined_hit")
        r["support_class"] = ("depletion in all tested per-sample runs and combined" if n_t >= 2 and n_h == n_t and ch
                              else "depletion in some per-sample runs and combined" if ch and n_h > 0
                              else "combined only" if ch else "per-sample only" if n_h > 0
                              else "no depletion association" if (n_t or ch is not None) else "not tested")
        r["biological_replicate_evidence"] = "not available (well replicate identity unknown)"
        rows.append(r)
    support = pd.DataFrame(rows)
    (outdir / "tables").mkdir(exist_ok=True)
    support.to_csv(outdir / "tables" / "target_support_matrix_across_runs.csv", index=False)
    for name, df in (("cell_counts_before_after_all_runs", cc), ("pair_assignment_per_lane_all_runs", pa), ("pair_guide_qc_all_runs", pq),
                     ("pair_perturbation_hit_counts_all_runs", hc), ("single_guide_diagnostic_all_runs", sg), ("cluster_sizes_all_runs", clusters)):
        if len(df):
            df.to_csv(outdir / "tables" / f"{name}.csv", index=False)

    # ---- audit -----------------------------------------------------------------------------
    audit_html = ""
    if audit_dir and Path(audit_dir).is_dir():
        for md in sorted(Path(audit_dir).glob("*.md")):
            audit_html += f"<h3>{md.name}</h3><pre style='white-space:pre-wrap;font-size:11px;background:#f7f7f7;padding:8px'>{md.read_text()[:20000]}</pre>"
        ref = Path(audit_dir) / "pair_guide_reference.csv"
        if ref.is_file():
            rdf = pd.read_csv(ref, dtype=str, keep_default_na=False)
            audit_html += f"<h3>Pair-guide reference ({len(rdf)} guides)</h3><p>scaffold: {rdf['scaffold'].value_counts().to_dict() if 'scaffold' in rdf else ''}; "
            audit_html += f"explicit pair ids: {int((rdf['pair_id'] != '').sum()) if 'pair_id' in rdf else 0}</p>" + _table(rdf.head(15), 15)

    def figs(k, names):
        return "".join(_img(run_dirs[k] / "figures" / n, outdir) for n in names)

    def run_link(k):
        rel = os.path.relpath(run_dirs[k] / "report.html", outdir)
        return f"<a href='{rel}'>{rel}</a>"

    parts = [f"<html><head><meta charset='utf-8'><title>{cfg.run.name}: pair-guide Perturb-seq report</title><style>{_CSS}</style></head><body>",
             f"<h1>{cfg.run.name}: pair-guide QC, clustering, ECDF and perturbation analysis</h1>",
             f"<p>Generated {now}. Branch <code>{git['branch']}</code>, commit <code>{git['commit']}</code>. Config: <code>{config_path}</code>. "
             "Primary labels are pair assignments; the single-guide rule appears only in section 11 as a diagnostic. "
             "Hits are <i>target-transcript depletion associations</i> (no knockout / CRISPRi / CRISPRa claim: modality undocumented).</p>",
             "<nav>" + "".join(f"<a href='#s{i}'>{i}. {t}</a>" for i, t in enumerate(
                 ["Dataset and samples", "Inputs and guide-design audit", "Expression QC", "Pair-guide QC", "Per-sample analysis", "Combined analysis",
                  "Clustering", "ECDF and perturbation", "FDR and effect sizes", "Target support", "Single-guide diagnostic", "Limitations", "Reproducibility"], 1)) + "</nav>"]
    # 1
    parts.append("<h2 id='s1'>1. Dataset and sample structure</h2>")
    lanes = cfg.input.mtx_dirs if isinstance(cfg.input.mtx_dirs, dict) else {}
    parts.append(_table(pd.DataFrame([{"sample": k, "gex_matrix": v, "guide_matrix": (cfg.input.guide_mtx_dirs or {}).get(k, "")} for k, v in lanes.items()])))
    parts.append(_table(cc[cc.lane_id != "ALL"].drop_duplicates(["run", "lane_id"]) if len(cc) else None))
    parts.append(f"<p>Per-run reports: {', '.join(f'{k}: {run_link(k)}' for k in run_dirs)}</p>")
    # 2
    parts.append("<h2 id='s2'>2. Input files and guide-design audit</h2>" + (audit_html or "<p>no audit directory given</p>"))
    # 3
    parts.append("<h2 id='s3'>3. Expression QC before and after filtering</h2>" + _table(cc) + figs(comb_key, ["qc/cell_counts_before_after_per_lane.png", "qc/ecdf_total_counts_before_after.png", "qc/ecdf_n_genes_by_counts_before_after.png", "qc/ecdf_pct_counts_mt_before_after.png", "qc/genes_vs_umis_before_after.png", "qc/pct_mt_vs_genes_and_umis.png", "qc/qc_violin_before_filtering.png", "qc/qc_violin_after_filtering.png"]))
    # 4
    parts.append("<h2 id='s4'>4. Pair-guide quantification and assignment QC</h2>" + _table(pa) + _table(pq) + figs(comb_key, ["guides/pair_guide_umis_detection_by_scaffold.png", "guides/pair_assignment_status_counts_and_fractions.png", "guides/target_pair_cells_per_lane.png"]))
    # 5
    parts.append("<h2 id='s5'>5. Per-sample analysis</h2>")
    for k in samples:
        parts.append(f"<h3>{k}</h3><p>Full report: {run_link(k)}</p>" + _table(pa[pa.run == k]) + _table(hc[hc.run == k]) + figs(k, ["guides/pair_assignment_status_counts_and_fractions.png", "clustering/umap_by_sample_condition_pair_status.png", "perturbation/pair_volcano_target_level.png", "perturbation/pair_ecdf_overview_top_targets.png"]))
    # 6
    parts.append(f"<h2 id='s6'>6. Combined analysis (four wells concatenated, no batch correction; batch_key = {cfg.cluster.batch_key})</h2><p>Full report: {run_link(comb_key)}</p>" + _table(pa[pa.run == comb_key]) + _table(hc[hc.run == comb_key]))
    # 7
    parts.append("<h2 id='s7'>7. PCA, UMAP and Leiden clustering</h2>" + figs(comb_key, ["clustering/pca_variance.png", "clustering/pca_by_sample_condition_pair_status.png", "clustering/umap_clusters.png", "clustering/umap_by_sample_condition_pair_status.png", "clustering/cluster_sizes.png", "clustering/cluster_composition_sample_pairstatus_class.png"]) + _table(clusters.pivot_table(index="cluster", columns="run", values="n_cells", aggfunc="first").reset_index() if len(clusters) else None, 40))
    # 8
    parts.append("<h2 id='s8'>8. ECDF and perturbation-expression analysis</h2><p>Targeting pairs versus NTC pairs on the target transcript (lognorm). Per-target ECDFs for every tested target are in each run's <code>figures/perturbation/ecdf/</code>.</p>" + figs(comb_key, ["perturbation/pair_ecdf_overview_top_targets.png", "perturbation/pair_level_expression_distributions.png", "perturbation/pair_waterfall_target_log2fc.png"]))
    ecdf_links = []
    for k in run_dirs:
        d = run_dirs[k] / "figures" / "perturbation" / "ecdf"
        if d.is_dir():
            ecdf_links.append(f"<li>{k}: {len(list(d.glob('ecdf_*.png')))} per-target ECDF figures in <a href='{os.path.relpath(d, outdir)}'>{os.path.relpath(d, outdir)}</a></li>")
    parts.append("<ul>" + "".join(ecdf_links) + "</ul>")
    # 9
    parts.append("<h2 id='s9'>9. FDR and effect-size results</h2>" + figs(comb_key, ["perturbation/pair_volcano_target_level.png", "perturbation/pair_volcano_pair_level.png", "perturbation/pair_heatmap_log2fc_by_lane.png", "perturbation/pair_heatmap_neg_log10_fdr_by_lane.png", "perturbation/pair_hit_counts_per_lane.png"]))
    pc = prim.get(comb_key)
    parts.append(_table(pc[pc.lane_id == "ALL"][["target_gene", "n_target_pair_cells", "n_ntc_pair_cells", "log2fc", "pct_knockdown", "ks_pval", "fdr_ks", "neg_log10_fdr", "is_hit", "hit_status"]].sort_values("log2fc") if pc is not None else None, 60))
    # 10
    parts.append("<h2 id='s10'>10. Per-sample / combined target support</h2>" + support["support_class"].value_counts().to_frame("targets").reset_index().rename(columns={"index": "support_class"}).to_html(index=False, classes="t", border=0) + _table(support, 80) + figs(comb_key, ["perturbation/pair_hit_counts_per_lane.png"]))
    # 11
    parts.append("<h2 id='s11'>11. Single-guide diagnostic comparison (not used for any result)</h2>" + _table(sg) + figs(comb_key, ["guides/single_guide_diagnostic_vs_pair_status.png"]))
    # 12
    lim = ["The design workbook carries no explicit pair/construct id; pairs are reconstructed only when both scaffold slots resolve to the same target (or both NTC). Vector-level pairing is therefore provisional and every pair label carries <code>pair_assignment_provisional = True</code>.",
           "Targeting+NTC, dual-target, incomplete, scaffold-ambiguous, unknown-guide and unresolved cells are excluded from primary testing (statuses in section 4).",
           "Well identity of biological replicates is not documented: agreement across wells is reported as well-level support only.",
           "CRISPR modality/effector is undocumented: results are target-transcript depletion associations.",
           "No batch correction was applied (by design); clusters are computed per object and are not comparable across runs.",
           "Doublets are not filtered; cells with several strong guides per scaffold are reported as ambiguous."]
    parts.append("<h2 id='s12'>12. Scientific limitations and unresolved pair assignments</h2><ul>" + "".join(f"<li>{x}</li>" for x in lim) + "</ul>")
    # 13
    manifest = {"generated": now, "git_branch": git["branch"], "git_commit": git["commit"], "git_status_short": git["status"], "config": config_path,
                "runs": {k: str(v) for k, v in run_dirs.items()}, "slurm_job_ids": job_ids or [], "assignment_mode": cfg.guides.assignment_mode,
                "pair_reference": cfg.guides.pair_map_file or cfg.guides.pair_reference, "batch_key": cfg.cluster.batch_key,
                "disabled_modules": {k: getattr(cfg, k).enabled for k in ("ps_score", "lochness", "modules", "distance", "distance_space", "meta_analysis")}}
    (outdir / "run_manifest.json").write_text(json.dumps(manifest, indent=1))
    if config_path:
        shutil.copy(config_path, outdir / "config_used.yaml")
    parts.append("<h2 id='s13'>13. Reproducibility</h2><pre style='font-size:11px'>" + json.dumps(manifest, indent=1) + "</pre>")
    parts.append("<h3>Resolved configuration (combined run)</h3><pre style='font-size:10px;max-height:500px;overflow:auto'>" + (run_dirs[comb_key] / "logs" / "resolved_config.yaml").read_text() + "</pre></body></html>")
    (outdir / "report.html").write_text("\n".join(parts))
    readme = [f"# {cfg.run.name}", "", f"Generated {now}; branch `{git['branch']}` commit `{git['commit']}`.", "",
              "- `report.html`: root pair-guide analysis report (13 sections) linking the per-run reports",
              "- `combined/`: pooled four-well run (report.html, processed h5ad, figures/, tables/)",
              "- `samples/<well>/`: independent per-sample runs with the same structure",
              "- `audit/`: dataset inventory, workbook audit, pair-guide reference", "- `tables/`: cross-run tables (target support, pair fractions)",
              "- `slurm/`: job scripts and logs; `run_manifest.json`, `config_used.yaml`", "",
              "Primary labels = pair assignments (pair_targeting vs pair_non_targeting). Single-guide rule = diagnostic only."]
    (outdir / "README.md").write_text("\n".join(readme) + "\n")
    logger.info("Root report written to %s", outdir / "report.html")
    return outdir / "report.html"
