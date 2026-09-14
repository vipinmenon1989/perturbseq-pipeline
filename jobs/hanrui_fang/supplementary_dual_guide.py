#!/usr/bin/env python
"""Step 11-15 driver: supplementary tables/figures for the four per-sample runs and the
combined run, the per-sample-versus-combined comparison and comparison_report.html.

SLURM only (jobs/hanrui_fang/08_supplementary.slurm)."""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from supp_common import (ALL_TARGETING, COLORS, COND, REP, RES, STRICT, WELLS, Run, cell_counts, default_vs_dual, guide_assignment_summary, log,
                         perturbation_tables, qc_tables, save, style)
from supp_figures import guide_figures, perturbation_figures, qc_figures
from perturbseq_pipeline import dual_guides as dg

FIG, TAB = RES / "figures", RES / "tables"


def process_run(run_dir: Path, label: str) -> dict:
    run = Run(run_dir, label)
    run.tab.mkdir(exist_ok=True)
    bt, bg, bi, rep, present = perturbation_tables(run)
    tested = set(bt.loc[bt.log2fc.notna(), "target_gene_name"])
    counts = cell_counts(run, tested)
    qc_tables(run)
    asg = guide_assignment_summary(run)
    dv = default_vs_dual(run)
    qc_figures(run, counts)
    guide_figures(run, asg, dv)
    perturbation_figures(run, bt, bg, bi, rep, present)
    return {"run": run, "bt": bt, "bg": bg, "bi": bi, "rep": rep, "counts": counts, "asg": asg, "dv": dv}


def comparison(results: dict):
    """Per-sample runs vs the combined run."""
    comb = results["combined"]
    # ---- assignment comparison ------------------------------------------------------------
    rows = []
    for w in WELLS:
        ps = results[w]["asg"].iloc[0].to_dict()
        cb = comb["asg"].set_index("well").loc[w].to_dict()
        for k in [c for c in ps if c.startswith(("n_", "pct_", "median_"))]:
            rows.append({"well": w, "metric": k, "per_sample_run": ps.get(k), "combined_run_same_well": cb.get(k),
                         "identical": (ps.get(k) == cb.get(k)) if isinstance(ps.get(k), (int, np.integer)) else bool(np.isclose(float(ps.get(k)), float(cb.get(k)), equal_nan=True))})
    ac = pd.DataFrame(rows)
    ac.to_csv(TAB / "assignment_comparison.csv", index=False)
    log("assignment identical per-sample vs combined (all metrics):", bool(ac["identical"].all()))

    # ---- sample comparison (cells + per target) --------------------------------------------
    rows = []
    for w in WELLS:
        pr, cr = results[w], comb
        pc = pr["counts"].set_index("cell_category")["cell_count"]
        cc = cr["counts"][cr["counts"].well == w].set_index("cell_category")["cell_count"]
        for cat in pc.index:
            rows.append({"well": w, "condition": COND[w], "replicate": REP[w], "level": "cells", "item": cat,
                         "per_sample_run": int(pc[cat]), "combined_run_same_well": int(cc.get(cat, np.nan)) if cat in cc else np.nan,
                         "combined_pooled": int(cr["counts"][(cr["counts"].well == "ALL")].set_index("cell_category")["cell_count"].get(cat, np.nan))})
        pbt = pr["bt"][(pr["bt"].control == "ntc") & (pr["bt"].assignment_stratum == ALL_TARGETING)].set_index("target_gene_name")
        cbt = cr["bt"][(cr["bt"].control == "ntc") & (cr["bt"].assignment_stratum == ALL_TARGETING) & (cr["bt"].well == w)].set_index("target_gene_name")
        pool = cr["bt"][(cr["bt"].control == "ntc") & (cr["bt"].assignment_stratum == ALL_TARGETING) & (cr["bt"].well == "ALL")].set_index("target_gene_name")
        for t in sorted(set(pbt.index) | set(cbt.index)):
            p_ = pbt.loc[t] if t in pbt.index else None
            c_ = cbt.loc[t] if t in cbt.index else None
            g_ = pool.loc[t] if t in pool.index else None
            def val(r, k):
                return r[k] if r is not None and k in r else np.nan
            rows.append({"well": w, "condition": COND[w], "replicate": REP[w], "level": "target", "item": t,
                         "per_sample_n_targeting": val(p_, "n_targeting_cells"), "combined_same_well_n_targeting": val(c_, "n_targeting_cells"),
                         "per_sample_n_ntc": val(p_, "n_non_targeting_cells"), "combined_same_well_n_ntc": val(c_, "n_non_targeting_cells"),
                         "per_sample_log2fc": val(p_, "log2fc"), "combined_same_well_log2fc": val(c_, "log2fc"), "combined_pooled_log2fc": val(g_, "log2fc"),
                         "per_sample_fdr_ks": val(p_, "fdr_ks"), "combined_same_well_fdr_ks": val(c_, "fdr_ks"), "combined_pooled_fdr_ks": val(g_, "fdr_ks"),
                         "per_sample_neg_log10_fdr": val(p_, "neg_log10_fdr"), "combined_same_well_neg_log10_fdr": val(c_, "neg_log10_fdr"), "combined_pooled_neg_log10_fdr": val(g_, "neg_log10_fdr"),
                         "per_sample_hit": val(p_, "default_hit"), "combined_same_well_hit": val(c_, "default_hit"), "combined_pooled_hit": val(g_, "default_hit"),
                         "direction_consistent_per_sample_vs_pooled": (np.sign(val(p_, "log2fc")) == np.sign(val(g_, "log2fc"))) if np.isfinite(val(p_, "log2fc")) and np.isfinite(val(g_, "log2fc")) else np.nan,
                         "evidence_levels": "per-well evidence (per-sample run) | combined pooled evidence (combined run, ALL) | condition-level: see target_hit_support_matrix | biological-replicate evidence: NOT available (replicate_type unknown)"})
    sc = pd.DataFrame(rows)
    sc.to_csv(TAB / "sample_comparison.csv", index=False)

    # ---- target hit support matrix -------------------------------------------------------------
    targets = sorted(set(comb["bt"]["target_gene_name"]) | set().union(*[set(results[w]["bt"]["target_gene_name"]) for w in WELLS]))
    rows = []
    for t in targets:
        r = {"target_gene_name": t}
        pool = comb["bt"][(comb["bt"].target_gene_name == t) & (comb["bt"].control == "ntc") & (comb["bt"].assignment_stratum == ALL_TARGETING)].set_index("well")
        strict = comb["bt"][(comb["bt"].target_gene_name == t) & (comb["bt"].control == "ntc") & (comb["bt"].assignment_stratum == STRICT)].set_index("well")
        oth = comb["bt"][(comb["bt"].target_gene_name == t) & (comb["bt"].control == "other") & (comb["bt"].assignment_stratum == ALL_TARGETING)].set_index("well")
        n_ps_hit = 0; n_ps_tested = 0
        for w in WELLS:
            ps = results[w]["bt"]; ps = ps[(ps.target_gene_name == t) & (ps.control == "ntc") & (ps.assignment_stratum == ALL_TARGETING)]
            h = bool(ps["default_hit"].iloc[0]) if len(ps) and pd.notna(ps["log2fc"].iloc[0]) else None
            r[f"per_sample_run_hit_{w}"] = h; r[f"per_sample_run_log2fc_{w}"] = float(ps["log2fc"].iloc[0]) if len(ps) else np.nan
            r[f"combined_well_hit_{w}"] = bool(pool.loc[w, "default_hit"]) if w in pool.index and pd.notna(pool.loc[w, "log2fc"]) else None
            n_ps_tested += h is not None; n_ps_hit += bool(h)
        r["n_per_sample_runs_tested"] = n_ps_tested; r["n_per_sample_runs_hit"] = n_ps_hit
        for cond in ("HF011", "HF012"):
            ws = [f"{cond}A", f"{cond}B"]
            hits = [r[f"per_sample_run_hit_{w}"] for w in ws]
            r[f"condition_level_{cond}"] = ("both wells depleted" if all(h is True for h in hits) else "one well depleted" if any(h is True for h in hits)
                                            else "neither well depleted" if all(h is False for h in hits) else "not tested in both wells")
        r["combined_pooled_hit"] = bool(pool.loc["ALL", "default_hit"]) if "ALL" in pool.index and pd.notna(pool.loc["ALL", "log2fc"]) else None
        r["combined_pooled_log2fc"] = pool.loc["ALL", "log2fc"] if "ALL" in pool.index else np.nan
        r["combined_pooled_fdr_ks"] = pool.loc["ALL", "fdr_ks"] if "ALL" in pool.index else np.nan
        r["combined_pooled_neg_log10_fdr"] = pool.loc["ALL", "neg_log10_fdr"] if "ALL" in pool.index else np.nan
        r["combined_pooled_other_control_hit"] = bool(oth.loc["ALL", "default_hit"]) if "ALL" in oth.index and pd.notna(oth.loc["ALL", "log2fc"]) else None
        r["strict_same_target_pairs_hit"] = bool(strict.loc["ALL", "default_hit"]) if "ALL" in strict.index and pd.notna(strict.loc["ALL", "log2fc"]) else None
        r["strict_same_target_pairs_log2fc"] = strict.loc["ALL", "log2fc"] if "ALL" in strict.index else np.nan
        r["biological_replicate_evidence"] = "not available: A/B replicate type unknown (well-level evidence only)"
        r["support_class"] = ("reproducible depletion (all 4 per-sample runs + pooled + strict pairs)" if n_ps_tested == 4 and n_ps_hit == 4 and r["combined_pooled_hit"] and r["strict_same_target_pairs_hit"]
                              else "depletion in all tested per-sample runs + pooled" if n_ps_tested >= 2 and n_ps_hit == n_ps_tested and r["combined_pooled_hit"]
                              else "pooled depletion, partial per-sample support" if r["combined_pooled_hit"] and n_ps_hit > 0
                              else "pooled depletion only (no per-sample support)" if r["combined_pooled_hit"]
                              else "per-sample depletion without pooled support" if n_ps_hit > 0
                              else "no depletion association" if n_ps_tested > 0 or r["combined_pooled_hit"] is not None else "not tested")
        rows.append(r)
    hs = pd.DataFrame(rows)
    hs.to_csv(TAB / "target_hit_support_matrix.csv", index=False)
    log("support classes:\n" + hs["support_class"].value_counts().to_string())

    # ---- top-level perturbation tables (combined run + per-sample runs stacked) ---------------------
    for key, name in (("bt", "perturbation_expression_by_target.csv"), ("bg", "perturbation_expression_by_guide.csv"), ("rep", "perturbation_replicate_summary.csv")):
        pd.concat([results["combined"][key]] + [results[w][key] for w in WELLS], ignore_index=True).to_csv(TAB / name, index=False)
    pw = pd.concat([comb["bt"][(comb["bt"].control == "ntc") & (comb["bt"].assignment_stratum == ALL_TARGETING) & (comb["bt"].well != "ALL")].assign(evidence="combined run, per-well stratum")]
                   + [results[w]["bt"][(results[w]["bt"].control == "ntc") & (results[w]["bt"].assignment_stratum == ALL_TARGETING)].assign(evidence="per-sample run") for w in WELLS], ignore_index=True)
    pw.to_csv(TAB / "perturbation_per_well.csv", index=False)
    pd.concat([results[k]["counts"] for k in ["combined"] + WELLS], ignore_index=True).to_csv(TAB / "cell_counts_before_after.csv", index=False)
    pd.concat([results[k]["asg"] for k in ["combined"] + WELLS], ignore_index=True).to_csv(TAB / "guide_assignment_summary.csv", index=False)
    pd.concat([results[k]["dv"] for k in ["combined"] + WELLS], ignore_index=True).to_csv(TAB / "default_vs_dual_assignment.csv", index=False)
    pd.concat([pd.read_csv(results[k]["run"].tab / "qc_metrics_per_well.csv") for k in ["combined"] + WELLS], ignore_index=True).to_csv(TAB / "qc_metrics_per_well.csv", index=False)
    shutil.copy(comb["run"].fig / "guides" / "default_vs_dual_assignment.png", FIG / "guides" / "default_vs_dual_assignment.png") if (FIG / "guides").mkdir(parents=True, exist_ok=True) is None else None

    # ---- comparison figures --------------------------------------------------------------------------
    m = sc[sc.level == "target"].copy()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    for w in WELLS:
        s = m[m.well == w]
        axes[0].scatter(s["combined_pooled_log2fc"], s["per_sample_log2fc"], s=14, color=COLORS[w], label=w, alpha=0.8)
        axes[1].scatter(s["combined_pooled_neg_log10_fdr"], s["per_sample_neg_log10_fdr"], s=14, color=COLORS[w], label=w, alpha=0.8)
    axes[0].plot([-5, 1], [-5, 1], color="#999", lw=0.6); axes[0].set_xlabel("combined pooled log2FC"); axes[0].set_ylabel("per-sample run log2FC"); axes[0].set_title("Per-sample vs combined log2FC", fontsize=9); axes[0].legend(fontsize=7, frameon=False); style(axes[0])
    axes[1].axhline(-np.log10(0.05), color="#e34948", ls="--", lw=0.7); axes[1].axvline(-np.log10(0.05), color="#e34948", ls="--", lw=0.7)
    axes[1].set_xlabel("combined pooled -log10(FDR)"); axes[1].set_ylabel("per-sample run -log10(FDR)"); axes[1].set_title("Per-sample vs combined -log10(FDR)", fontsize=9); style(axes[1])
    fig.tight_layout(); save(fig, FIG, "perturbation", "per_sample_vs_combined_log2fc_and_fdr")
    # same-well: per-sample run vs combined run stratified by well (should be near-identical for counts, different normalisation)
    fig, ax = plt.subplots(figsize=(5.5, 4.6))
    for w in WELLS:
        s = m[m.well == w]
        ax.scatter(s["combined_same_well_log2fc"], s["per_sample_log2fc"], s=14, color=COLORS[w], label=w, alpha=0.8)
    ax.plot([-5, 1], [-5, 1], color="#999", lw=0.6); ax.set_xlabel("combined run, same-well stratum log2FC"); ax.set_ylabel("per-sample run log2FC"); ax.set_title("Same well: separate run vs stratum of the combined run", fontsize=9); ax.legend(fontsize=7, frameon=False); style(ax)
    save(fig, FIG, "perturbation", "per_sample_run_vs_combined_same_well_log2fc")
    # QC comparison per-sample vs combined
    qc = pd.read_csv(TAB / "qc_metrics_per_well.csv")
    qa = qc[(qc.stage == "after_qc") & (qc.well != "ALL")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, c in zip(axes, ("median_total_counts", "median_n_genes_by_counts", "median_pct_counts_mt")):
        piv = qa.pivot_table(index="well", columns="run", values=c, aggfunc="first").reindex(WELLS)
        piv.plot.bar(ax=ax, width=0.8); ax.set_title(c, fontsize=8); ax.legend(fontsize=6, frameon=False); style(ax)
    fig.suptitle("Per-sample runs vs combined run: QC medians per well (identical QC rule; different objects)", fontsize=9); fig.tight_layout()
    save(fig, FIG, "qc", "per_sample_vs_combined_qc_comparison")
    hit_counts = pd.DataFrame({"per-sample run": [int(results[w]["rep"]["pooled_hit"].sum()) for w in WELLS],
                               "combined run (same well)": [int(comb["bt"][(comb["bt"].well == w) & (comb["bt"].control == "ntc") & (comb["bt"].assignment_stratum == ALL_TARGETING)]["default_hit"].sum()) for w in WELLS]}, index=WELLS)
    fig, ax = plt.subplots(figsize=(6, 4)); hit_counts.plot.bar(ax=ax, color=["#2a78d6", "#8ab4e8"]); ax.axhline(int(comb["rep"]["pooled_hit"].sum()), color="#52514e", ls="--", label="combined pooled"); ax.set_ylabel("targets with depletion association"); ax.legend(fontsize=7, frameon=False); style(ax)
    save(fig, FIG, "perturbation", "significant_targets_per_sample_vs_combined")
    return ac, sc, hs


def html_report(results, ac, sc, hs):
    def img(p):
        return f'<figure><img src="data:image/png;base64,{base64.b64encode(open(p, "rb").read()).decode()}" style="max-width:100%"><figcaption>{Path(p).relative_to(RES)}</figcaption></figure>'
    def table(df, n=60):
        return df.head(n).to_html(index=False, float_format=lambda x: f"{x:.3g}", classes="t", border=0)
    comb = results["combined"]
    parts = [f"<html><head><meta charset='utf-8'><title>Hanrui Fang dual-guide: per-sample vs combined</title>"
             "<style>body{font-family:system-ui,sans-serif;margin:24px;max-width:1400px}table.t{border-collapse:collapse;font-size:11px}table.t td,table.t th{border:1px solid #ddd;padding:2px 6px}figure{margin:8px 0}figcaption{font-size:10px;color:#666}h2{border-bottom:1px solid #ccc}</style></head><body>",
             f"<h1>Hanrui Fang dual-guide Perturb-seq: per-sample versus combined comparison</h1><p>Generated {datetime.now():%Y-%m-%d %H:%M}, SLURM job {os.environ.get('SLURM_JOB_ID', 'n/a')}. "
             "Evidence levels: <b>per-well evidence</b> = per-sample runs (HF011A/B, HF012A/B); <b>condition-level evidence</b> = agreement of the two wells of a condition; "
             "<b>combined pooled evidence</b> = combined run, all four wells concatenated without batch correction; <b>biological-replicate evidence</b> = not available (A/B replicate type unknown, condition labels inferred). "
             "'Hit' = target-transcript depletion association (KS FDR &lt; 0.05 and log2FC &lt; 0 versus NTC pairs); the CRISPR modality is undocumented, so no knockout/CRISPRi/CRISPRa claim is made.</p>"]
    parts.append("<h2>1. Cells per run</h2>" + table(pd.concat([results[k]["counts"] for k in ["combined"] + WELLS]).pivot_table(index=["run", "well"], columns="cell_category", values="cell_count", aggfunc="first").reset_index(), 20))
    parts.append("<h2>2. Guide / pair assignment</h2>" + table(pd.concat([results[k]["asg"] for k in ["combined"] + WELLS])[["run", "well", "n_qc_pass_cells", "n_targeting", "pct_targeting", "n_non-targeting", "pct_non-targeting", "n_ambiguous", "pct_ambiguous", "n_unassigned", "n_same_target_pair", "n_target_ntc_provisional", "n_ntc_pair", "n_dual_target", "n_incomplete_A_only", "n_incomplete_C_only", "n_ambiguous_A_slot", "n_ambiguous_C_slot", "n_ambiguous_both_slots", "n_below_min_umi", "n_no_guide"]]))
    parts.append(f"<p>Per-sample runs versus the same well inside the combined run: {int(ac['identical'].sum())}/{len(ac)} assignment metrics identical (assignment is per cell and does not depend on the other wells).</p>")
    parts.append(img(comb["run"].fig / "guides" / "default_vs_dual_assignment.png") + img(comb["run"].fig / "guides" / "pair_assignment_categories_and_fractions.png"))
    parts.append("<h2>3. Per-sample versus combined perturbation results</h2>" + img(FIG / "perturbation" / "per_sample_vs_combined_log2fc_and_fdr.png") + img(FIG / "perturbation" / "per_sample_run_vs_combined_same_well_log2fc.png") + img(FIG / "perturbation" / "significant_targets_per_sample_vs_combined.png"))
    parts.append("<h2>4. Target hit support matrix</h2><p>" + hs["support_class"].value_counts().to_frame("targets").to_html(classes="t", border=0) + "</p>" + table(hs[["target_gene_name", "support_class", "n_per_sample_runs_tested", "n_per_sample_runs_hit", "condition_level_HF011", "condition_level_HF012", "combined_pooled_hit", "combined_pooled_log2fc", "combined_pooled_fdr_ks", "combined_pooled_neg_log10_fdr", "combined_pooled_other_control_hit", "strict_same_target_pairs_hit", "strict_same_target_pairs_log2fc", "biological_replicate_evidence"]].sort_values("combined_pooled_log2fc"), 80))
    parts.append("<h2>5. Combined-run perturbation figures</h2>" + img(comb["run"].fig / "perturbation" / "volcano_log2fc_vs_neglog10fdr.png") + img(comb["run"].fig / "perturbation" / "heatmap_log2fc_by_sample.png") + img(comb["run"].fig / "perturbation" / "heatmap_neg_log10_fdr_by_sample.png") + img(comb["run"].fig / "perturbation" / "well_consistency_log2fc_A_vs_B.png"))
    parts.append("<h2>6. QC comparison</h2>" + img(FIG / "qc" / "per_sample_vs_combined_qc_comparison.png") + img(comb["run"].fig / "qc" / "cell_counts_before_after.png") + img(comb["run"].fig / "qc" / "umap_by_well_condition_qcstatus_pairstatus.png"))
    parts.append("<h2>7. Tables</h2><ul>" + "".join(f"<li>{p.relative_to(RES)}</li>" for p in sorted(TAB.glob('*.csv'))) + "</ul></body></html>")
    (RES / "comparison_report.html").write_text("\n".join(parts))
    log("wrote", RES / "comparison_report.html")


def main():
    results = {}
    results["combined"] = process_run(RES / "combined", "combined")
    for w in WELLS:
        results[w] = process_run(RES / "per_sample" / w, w)
    ac, sc, hs = comparison(results)
    html_report(results, ac, sc, hs)
    summary = {k: {"n_cells_processed": int(v["run"].proc.n_obs), "n_cells_all": int(v["run"].allc.n_obs),
                   "targets_tested": int(v["rep"]["pooled_log2fc"].notna().sum()) if len(v["rep"]) else 0,
                   "targets_hit": int(v["rep"]["pooled_hit"].sum()) if len(v["rep"]) else 0,
                   "targets_hit_strict_same_target": int(v["rep"]["strict_same_target_hit"].sum()) if len(v["rep"]) else 0,
                   "clusters": int(v["run"].proc.obs["leiden"].nunique())} for k, v in results.items()}
    summary["support_classes"] = hs["support_class"].value_counts().to_dict()
    json.dump(summary, open(TAB / "supplementary_summary.json", "w"), indent=1)
    log(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
