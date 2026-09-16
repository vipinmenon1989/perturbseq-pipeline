#!/usr/bin/env python
"""Validate the rebuilt full_3 HTML reports (SLURM only) and write report_rebuild.md / report_rebuild_commands.md."""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from lxml import html as lxml_html

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
OUT = REPO / "results" / "Hanrui_Fang_pair_guide_full_3"
PREV = REPO / "results" / "Hanrui_Fang_pair_guide_full_2"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
REPORTS = {"root": OUT / "report.html", "combined": OUT / "combined" / "report.html", **{w: OUT / "samples" / w / "report.html" for w in WELLS}}
RUN_DIRS = {"root": OUT / "combined", "combined": OUT / "combined", **{w: OUT / "samples" / w for w in WELLS}}
REQUIRED_IDS = ["summary", "qc", "guides", "clustering", "perturbation", "enrichment", "repro"]
ROOT_IDS = REQUIRED_IDS + ["index", "support", "previous"]
KEY_TABLES = ["qc_steps", "pair_assignment_per_lane", "pair_resolution_detail_per_lane", "pair_slot_summary_by_status", "pair_assignment_per_cell", "clusters", "pair_perturbation_primary", "pair_perturbation_by_pair", "enrichment", "target_support_matrix", "figure_manifest"]
JOB = os.environ.get("SLURM_JOB_ID", "n/a")
checks = []
stats = {}


def _md_table(df):
    cols = [str(c) for c in df.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(v).replace("|", "/") for v in r.tolist()) + " |")
    return "\n".join(lines)


def check(name, ok, detail=""):
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:600]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {str(detail)[:300]}", flush=True)


def main():
    for k, rp in REPORTS.items():
        d = rp.parent
        check(f"{k}: report.html exists and is large enough to hold embedded figures", rp.is_file() and rp.stat().st_size > 5_000_000, f"{rp} ({rp.stat().st_size / 1e6:.1f} MB)" if rp.is_file() else "missing")
        check(f"{k}: textual report backed up", (d / "report_textual_backup.html").is_file(), str(d / "report_textual_backup.html"))
        if not rp.is_file():
            continue
        doc = lxml_html.fromstring(rp.read_text(errors="ignore"))
        imgs = doc.xpath("//img")
        srcs = [i.get("src", "") for i in imgs]
        bad = [s[:60] for s in srcs if not s.startswith("data:image/png;base64,")]
        small = 0
        for s in srcs:
            if s.startswith("data:image/png;base64,"):
                try:
                    if len(base64.b64decode(s.split(",", 1)[1][:4000])) < 1000:
                        small += 1
                except Exception:
                    small += 1
        check(f"{k}: every <img> is an embedded PNG data URI ({len(imgs)} figures)", not bad and not small and len(imgs) >= 40, f"{len(imgs)} embedded; non-data-URI: {bad[:3]}; tiny: {small}")
        hrefs = [a.get("href", "") for a in doc.xpath("//a[@href]")]
        rel = [h for h in hrefs if h and not h.startswith(("#", "http://", "https://", "mailto:"))]
        missing = sorted({h for h in rel if not (d / h).exists()})
        check(f"{k}: every relative link (figures, CSV tables, H5AD, reports) resolves ({len(rel)} links)", not missing, missing[:6])
        check(f"{k}: no image, table, H5AD or report link points to full_2", not any("Hanrui_Fang_pair_guide_full_2" in h for h in rel + srcs), [h for h in rel if "full_2" in h][:3])
        csvs = [h for h in rel if h.endswith(".csv")]
        h5 = [h for h in rel if h.endswith(".h5ad")]
        check(f"{k}: CSV links ({len(csvs)}) and H5AD links ({len(h5)}) present and existing", len(csvs) >= 15 and len(h5) >= 1 and all((d / h).is_file() for h in csvs + h5))
        ids = {e.get("id") for e in doc.xpath("//h2[@id]")}
        req = ROOT_IDS if k == "root" else REQUIRED_IDS
        check(f"{k}: all required sections present {req}", set(req) <= ids, sorted(ids))
        txt = doc.text_content()
        na = re.findall(r"Table ([a-z_0-9]+): not available", txt)
        check(f"{k}: key tables rendered (none of {len(KEY_TABLES)} key tables missing)", not any(t in na for t in KEY_TABLES), f"unavailable: {na}")
        check(f"{k}: no placeholder text", not re.search(r"\bTODO\b|lorem ipsum|PLACEHOLDER|\{\{|\}\}", txt))
        check(f"{k}: standalone (no external scripts / stylesheets)", not doc.xpath("//script[@src]") and not doc.xpath("//link[@href]"))
        # summary counts vs tables
        rd = RUN_DIRS[k]
        cc = pd.read_csv(rd / "tables" / "cell_counts_before_after.csv").set_index("lane_id")
        pooled = "ALL" if k in ("root", "combined") else k
        n_ret = int(cc.loc[pooled, "final_cells_retained"])
        hc = pd.read_csv(rd / "tables" / "pair_perturbation_hit_counts_per_lane.csv").set_index("lane_id")
        cards = {kk.text_content().strip(): v.text_content().strip() for v, kk in zip(doc.xpath("//div[@class='card']/div[@class='v']"), doc.xpath("//div[@class='card']/div[@class='k']"))}
        check(f"{k}: summary cards match the full_3 tables (cells {n_ret:,}; hits {int(hc.loc[pooled, 'targets_hit'])}/{int(hc.loc[pooled, 'targets_tested'])})",
              cards.get("Cells analysed") == f"{n_ret:,}" and cards.get("Effective perturbations") == f"{int(hc.loc[pooled, 'targets_hit'])} / {int(hc.loc[pooled, 'targets_tested'])}", {c: cards.get(c) for c in ("Cells analysed", "Effective perturbations", "Strict primary pairs")})
        pa = pd.read_csv(rd / "tables" / "pair_assignment_per_lane.csv").set_index("lane_id")
        check(f"{k}: strict primary card equals n_pair_assigned_primary", cards.get("Strict primary pairs", "").startswith(f"{int(pa.loc[pooled, 'n_pair_assigned_primary']):,}"), cards.get("Strict primary pairs"))
        man = pd.read_csv(rd / "tables" / "figure_manifest.csv")
        gal = {"perturbation/per_gene": len(doc.xpath("//h3[contains(text(),'Per-target perturbation figures')]")), "perturbation/ecdf": 0, "enrichment/per_target": 0}
        n_gallery_imgs = len(doc.xpath("//div[@class='gallery']//img"))
        exp_gallery = int((man.section == "perturbation/ecdf").sum()) + int((man.section == "enrichment/per_target").sum())
        check(f"{k}: per-target galleries embed every ECDF and enrichment figure (+ overflow per-gene figures)", n_gallery_imgs >= exp_gallery, f"{n_gallery_imgs} gallery images vs {exp_gallery} ECDF+enrichment manifest figures")
        check(f"{k}: all manifest figures embedded", len(imgs) >= len(man) - 0, f"{len(imgs)} images vs {len(man)} manifest rows")
        check(f"{k}: dominance rule and category vocabulary stated", all(s in txt for s in ("(top guide UMI + 1) / (second guide UMI + 1)", "strict primary construct pair", "targeting-plus-NTC sensitivity class", "same-target inferred pair", "single-guide diagnostic", "dual-target ambiguity", "scaffold ambiguity", "unresolved pair", "incomplete pair")))
        check(f"{k}: raw FDR column present in rendered tables", "fdr_ks" in txt and "neg_log10_fdr" in txt)
        stats[k] = {"size_mb": round(rp.stat().st_size / 1e6, 1), "embedded_figures": len(imgs), "manifest_figures": int(len(man)), "relative_links": len(rel), "csv_links": len(csvs), "h5ad_links": len(h5), "gallery_images": n_gallery_imgs, "unavailable_tables": na}
    # previous result untouched
    prev_ok = all((PREV / f).is_file() and datetime.fromtimestamp((PREV / f).stat().st_mtime) < datetime(2026, 9, 16, 8, 0) for f in ("report.html", "combined/report.html", "run_manifest.json"))
    check("full_2 reports not modified", prev_ok)
    check("no full_3 figures/tables/h5ad/audit deleted (counts vs manifest)", all((RUN_DIRS[k] / "tables" / "figure_manifest.csv").is_file() and len(list((RUN_DIRS[k] / "figures").rglob("*.png"))) >= len(pd.read_csv(RUN_DIRS[k] / "tables" / "figure_manifest.csv")) for k in RUN_DIRS))
    df = pd.DataFrame(checks)
    df.to_csv(OUT / "tables" / "report_rebuild_validation.csv", index=False)
    n_pass = int((df.status == "PASS").sum())
    print(f"\n{n_pass}/{len(df)} checks passed")
    (OUT / "report_rebuild_validation.txt").write_text("\n".join(f"[{r.status}] {r.check}: {r.detail}" for r in df.itertuples()) + f"\n\n{n_pass}/{len(df)} checks passed\n")
    # ---- documentation ---------------------------------------------------------------------
    summ = json.load(open(OUT / "report_rebuild_summary.json")) if (OUT / "report_rebuild_summary.json").is_file() else {}
    git = subprocess.run(["git", "status", "--short"], cwd=REPO, capture_output=True, text=True).stdout
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    sec_counts = {}
    for k in ("combined",):
        man = pd.read_csv(RUN_DIRS[k] / "tables" / "figure_manifest.csv")
        sec_counts = man.groupby("section").size().to_dict()
    missing_figs = {k: v.get("missing_figures", []) for k, v in summ.items()}
    md = [f"# Report rebuild (Hanrui Fang pair-guide full_3)", "", f"SLURM job {JOB}, {datetime.now():%Y-%m-%d %H:%M}; branch `{branch}` commit `{commit}`; conda env `{os.environ.get('CONDA_DEFAULT_ENV', '')}`.", "",
          "## How full_2 was inspected", "",
          "- `results/Hanrui_Fang_pair_guide_full_2/report.html` (root, built by `multi_run_report.py`) and `combined/report.html` (per-run pipeline report from `templates/report.html`): structure (summary cards, numbered sections, embedded base64 PNGs with `<figure>/<figcaption>`, scrollable tables, `<details>` blocks, TOC), CSS and figure/table conventions were read from the HTML and from the renderer code.",
          "- `combined/figures/` (sections qc, guides, clustering, perturbation, perturbation/per_gene, perturbation/ecdf, enrichment, enrichment/per_target) and `combined/tables/` (figure_manifest.csv and the result CSVs) were listed to learn how figures are registered and tables written.",
          "- Renderer code inspected: `src/perturbseq_pipeline/report.py` (Jinja environment, `ReportInputs`, `_render_figure`, `_df_to_html`, summary cards, per-target extras, output manifest), `templates/report.html` (CSS, section order), `plots.py` (`FigureRegistry` / `FigureRecord`, `manifest()`), `multi_run_report.py` (previous root builder), `pair_guide_report.py` (figure/table names).", "",
          "## Renderer reused", "",
          "- New template `src/perturbseq_pipeline/templates/report_full.html`: the CSS block of `templates/report.html` verbatim (identical look: cards, notes, warn boxes, scroll tables, figures, TOC, footer) plus a small gallery/tag extension; the same Jinja `Environment` / `TEMPLATE_DIR` as `report.py`.",
          "- New module `src/perturbseq_pipeline/report_rebuild.py`: reconstructs the report context from the run outputs (figure manifest -> `FigureRecord`s embedded via `FigureRecord.data_uri()`, `tables/*.csv`, `logs/resolved_config.yaml`, processed H5AD `obs` for the per-cell slot table) and renders the per-run and root reports. No Markdown-to-HTML conversion is involved.",
          "- `plots.py`: `FigureRegistry.manifest()` now records the figure caption (future runs); captions of the current outputs were recovered from the previous pipeline renders.",
          "- `cli.py`: new sub-command `perturbseq-pipeline rebuild-report --root ... --run LABEL=DIR ... [--previous-run]`.", "",
          "## Code files changed", "", "```", git.strip(), "```", "",
          "## Figures and tables included", "", f"Combined-run figure manifest by section: {sec_counts}. Every manifest figure that exists and is non-empty is embedded (major figures inline, per-target perturbation / ECDF / enrichment figures in galleries with full-resolution links).", "",
          _md_table(pd.DataFrame(stats).T.reset_index().rename(columns={"index": "report"})) if stats else "", "",
          "Tables rendered inline with row caps and links to the complete CSVs: QC steps, per-lane QC, before/after cell counts, QC metrics before/after, pair-assignment status, resolution details (primary / sensitivity / ambiguous), construct types, per-slot dominance summary and the new per-cell slot table (`tables/pair_assignment_per_cell.csv`: top / second / ratio / status per scaffold, primary-vs-sensitivity flag), pair-guide QC, strong guides per scaffold, barcode overlap, off-design UMI fraction, target and construct representation, guide / feature representation, single-guide diagnostic, clusters, cluster sizes and composition, hit counts, target-level and construct-level perturbation results, strata comparison, ranked pipeline table, untestable targets, target support, enrichment (significant pairs, effect magnitude, composition), figure manifest; root report adds run index, cross-run support and hit tables and the labelled previous-run comparison.", "",
          "## Figures not available", "", json.dumps(missing_figs, indent=1) if any(missing_figs.values()) else "none: every manifest figure was present and non-empty.", "",
          "## Validation", "", f"{n_pass}/{len(df)} checks passed (`report_rebuild_validation.txt`, `tables/report_rebuild_validation.csv`). Headless browser rendering was not available on the node; the HTML was parsed with lxml and every embedded image, relative link, CSV and H5AD reference was checked instead.", "",
          "## Final report paths", ""] + [f"- `{p}` ({stats.get(k, {}).get('size_mb', '?')} MB, {stats.get(k, {}).get('embedded_figures', '?')} embedded figures)" for k, p in REPORTS.items()] + ["", "Textual reports preserved as `report_textual_backup.html` next to each rebuilt report."]
    (OUT / "report_rebuild.md").write_text("\n".join(md) + "\n")
    return 0 if n_pass == len(df) else 1


if __name__ == "__main__":
    sys.exit(main())
