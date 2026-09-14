"""Shared helpers for the Hanrui Fang dual-guide supplementary analysis (tables part).

Everything here is derived from pipeline outputs (processed / all-cells h5ad, tables,
resolved_config.yaml) plus the job-03 guide quantification tables. Statistics reuse
perturbation.compare_groups (two-sided KS, one-sided MWU 'less', log2FC on de-logged
lognorm with pseudocount 0.01) and perturbation.benjamini_hochberg. The hit rule is the
pipeline default (ks FDR < fdr_alpha and log2fc < max_log2fc_for_hit).

FDR convention: fdr_ks is the BH FDR of the two-sided KS p-value; neg_log10_fdr = -log10(fdr_ks)
(a positive number, larger = more significant). It is never a cell count.
"""
from __future__ import annotations

import json
import re
import warnings
from pathlib import Path

import anndata as ad
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.sparse as sp
import yaml

from perturbseq_pipeline.perturbation import benjamini_hochberg, compare_groups
from perturbseq_pipeline import dual_guides as dg

warnings.filterwarnings("ignore")
REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
RES = REPO / "results" / "Hanrui_fang_dual_guide"
CR_ROOT = REPO / "results" / "outputs" / "hanrui_fang_inputs" / "cellranger"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
COND = {"HF011A": "HF011", "HF011B": "HF011", "HF012A": "HF012", "HF012B": "HF012"}
REP = {"HF011A": "A", "HF011B": "B", "HF012A": "A", "HF012B": "B"}
COLORS = {"HF011A": "#2a78d6", "HF011B": "#8ab4e8", "HF012A": "#eb6834", "HF012B": "#f3a98a", "ALL": "#52514e", "pooled": "#52514e"}
CLASS_COLORS = {"targeting": "#2a78d6", "non-targeting": "#1baf7a", "ambiguous": "#eda100", "unassigned": "#9a9a9a", "QC-failed": "#e34948"}
STATUS_COLORS = {
    "same_target_pair": "#2a78d6", "target_ntc_provisional": "#8ab4e8", "ntc_pair": "#1baf7a", "dual_target": "#4a3aa7",
    "target_ntc_unconfirmed": "#c7b5f0", "invalid_pair": "#e34948", "incomplete_A_only": "#eda100", "incomplete_C_only": "#f7cf6a",
    "ambiguous_A_slot": "#eb6834", "ambiguous_C_slot": "#f3a98a", "ambiguous_both_slots": "#b04a20", "below_min_umi": "#c9c9c9",
    "no_guide": "#7a7a7a", "QC-failed": "#e0e0e0",
}
ALIASES = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3"}
DPI = 130
QC_COLS = ["total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "pct_counts_hb"]
STRICT = "same_target_pairs_only"
ALL_TARGETING = "all_targeting_incl_provisional_target_ntc"


def log(*a):
    print(*a, flush=True)


def save(fig, figdir: Path, sub: str, name: str):
    p = figdir / sub / f"{name}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    log("  fig", p.relative_to(RES))
    return p


def style(ax):
    ax.grid(True, color="#e0dfda", linewidth=0.6)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def ecdf(ax, values, label, color, log_x=False, ls="-"):
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return
    v = np.sort(v)
    y = np.arange(1, v.size + 1) / v.size
    if log_x:
        v = v + 1
        ax.set_xscale("log")
    ax.step(v, y, where="post", color=color, linewidth=1.4, linestyle=ls, label=f"{label} (n={v.size:,})")


def symbol_of(label):
    s = re.sub(r"\s*\(rs\d+\)\s*$", "", str(label)).strip()
    return ALIASES.get(s, s)


def wells_in(obs) -> list:
    return [w for w in WELLS if (obs["well"].astype(str) == w).any()]


# ------------------------------------------------------------------------------------------ loading


class Run:
    """One pipeline run directory (per-sample or combined)."""

    def __init__(self, run_dir: Path, label: str):
        self.dir = Path(run_dir)
        self.label = label
        self.fig = self.dir / "figures"
        self.tab = self.dir / "tables"
        self.cfg = yaml.safe_load(open(self.dir / "logs" / "resolved_config.yaml"))
        self.proc = ad.read_h5ad(self.dir / self.cfg["output"]["h5ad_name"])
        self.allc = ad.read_h5ad(self.dir / self.cfg["output"]["unfiltered_h5ad_name"])
        proc, allc = self.proc, self.allc
        log(f"[{label}] processed {proc.shape} | all cells {allc.shape}")
        assert allc.obs_names.is_unique and proc.obs_names.is_unique
        in_proc = allc.obs_names.isin(proc.obs_names)
        assert in_proc.sum() == proc.n_obs
        allc.obs["pipeline_qc_pass"] = in_proc
        for col, fill in (("perturbation_class", "QC-failed"), ("target_gene", "QC-failed"), (dg.OBS_PAIR_STATUS, "QC-failed"),
                          (dg.OBS_PAIR, "QC-failed"), ("guide_id", "QC-failed"), ("leiden", "QC-failed")):
            if col in proc.obs.columns:
                s = pd.Series(proc.obs[col].astype(str).to_numpy(), index=proc.obs_names)
                allc.obs[col] = allc.obs_names.map(s).fillna(fill).to_numpy()
        # guide metadata: the processed object carries names + scaffold via uns (io round-trip)
        names = np.array([str(x) for x in proc.uns["guide_names"]], dtype=object)
        gvar = pd.DataFrame(index=names)
        gvar["target_gene_name"] = [str(x) for x in proc.uns["guide_target_gene_names"]]
        gvar["target_gene"] = [str(x) for x in proc.uns["guide_target_genes"]] if "guide_target_genes" in proc.uns else gvar["target_gene_name"]
        gvar["scaffold"] = [str(x) for x in proc.uns["guide_scaffolds"]] if "guide_scaffolds" in proc.uns else "unknown"
        gvar["is_non_targeting"] = gvar["target_gene_name"].str.lower().isin(["ntc", "no-target", "non-targeting"])
        self.gvar = gvar
        self.scaf = gvar["scaffold"].to_numpy().astype(str)
        for a in (proc, allc):
            G = sp.csr_matrix(a.obsm["guide_counts"])
            assert G.shape[1] == len(names)
            min_umi = int(self.cfg["guides"]["min_umi"])
            a.obs["guide_umi_total"] = np.asarray(G.sum(axis=1)).ravel()
            a.obs["n_guides_ge_min_umi"] = np.asarray((G >= min_umi).sum(axis=1)).ravel()
            a.obs["n_strong_guides_A_any"] = np.asarray((G[:, self.scaf == "A"] >= min_umi).sum(axis=1)).ravel()
            a.obs["n_strong_guides_C_any"] = np.asarray((G[:, self.scaf == "C"] >= min_umi).sum(axis=1)).ravel()
        self.wells = wells_in(proc.obs)
        self.groups = self.wells + (["ALL"] if len(self.wells) > 1 else [])

    def mask(self, obs, g):
        return pd.Series(True, index=obs.index) if g == "ALL" else obs["well"].astype(str) == g


def cellranger_metrics() -> pd.DataFrame:
    rows = []
    for w in WELLS:
        p = CR_ROOT / w / "metrics_summary.csv"
        if p.is_file():
            r = pd.read_csv(p).iloc[0].to_dict()
            r = {k: (float(str(v).replace(",", "").replace("%", "")) if isinstance(v, str) and re.fullmatch(r"[\d,]+(\.\d+)?%?", v) else v) for k, v in r.items()}
            r["well"] = w
            rows.append(r)
    df = pd.DataFrame(rows)
    return df[["well"] + [c for c in df.columns if c != "well"]] if len(df) else df


# ------------------------------------------------------------------------------------------ tables


def cell_counts(run: Run, tested_targets) -> pd.DataFrame:
    q = run.cfg["qc"]
    cr = cellranger_metrics().set_index("well") if len(cellranger_metrics()) else None
    a, p = run.allc.obs, run.proc.obs
    rows = []
    for g in run.groups:
        ma, mp = run.mask(a, g), run.mask(p, g)
        sa, spp = a[ma], p[mp]
        cond, rep = COND.get(g, "pooled"), REP.get(g, "pooled")
        n_cr = int(sum(cr.loc[w, "Estimated Number of Cells"] for w in (run.wells if g == "ALL" else [g]))) if cr is not None else len(sa)
        st = []
        st.append(("00_cellranger_called", "input cells (Cell Ranger filtered)", n_cr))
        st.append(("01_loaded", "cells loaded by pipeline", len(sa)))
        pre = sa["n_genes_by_counts"] >= q["min_genes_per_cell"]
        st.append(("02_prefilter_min_genes_200", f"pass >= {q['min_genes_per_cell']} genes", int(pre.sum())))
        st.append(("02_prefilter_min_genes_200", f"fail < {q['min_genes_per_cell']} genes", int((~pre).sum())))
        fin = pre & (sa["n_genes_by_counts"] >= q["min_genes_final"])
        st.append(("03_min_genes_final_1000", f"pass >= {q['min_genes_final']} genes", int(fin.sum())))
        st.append(("03_min_genes_final_1000", f"fail < {q['min_genes_final']} genes (of prefilter pass)", int((pre & ~fin).sum())))
        mt = fin & (sa["pct_counts_mt"] < q["max_pct_mt"])
        st.append(("04_max_pct_mt_20", f"pass mt < {q['max_pct_mt']}% (derived final QC pass)", int(mt.sum())))
        st.append(("04_max_pct_mt_20", f"fail mt >= {q['max_pct_mt']}% (of gene-pass)", int((fin & ~mt).sum())))
        st.append(("04_final_qc_pass_pipeline", "cells in processed object (pipeline QC pass)", int(sa["pipeline_qc_pass"].sum())))
        st.append(("04_final_qc_pass_pipeline", "cells failing any expression QC", int((~sa["pipeline_qc_pass"]).sum())))
        status = spp[dg.OBS_PAIR_STATUS].astype(str)
        klass = spp["perturbation_class"].astype(str)
        st.append(("05_guides", "guide-zero cells (0 guide UMIs)", int((spp["guide_umi_total"] == 0).sum())))
        st.append(("05_guides", "no guide at min_umi (no_guide + below_min_umi)", int(status.isin(["no_guide", "below_min_umi"]).sum())))
        st.append(("05_guides", "targeting cells (perturbation_class)", int((klass == "targeting").sum())))
        st.append(("05_guides", "non-targeting cells (perturbation_class)", int((klass == "non-targeting").sum())))
        st.append(("05_guides", "pair-assigned cells (targeting + non-targeting)", int(klass.isin(["targeting", "non-targeting"]).sum())))
        st.append(("05_guides", "  of which same-target pairs", int((status == "same_target_pair").sum())))
        st.append(("05_guides", "  of which NTC pairs", int((status == "ntc_pair").sum())))
        st.append(("05_guides", "  of which targeting+NTC pairs (provisional)", int((status == "target_ntc_provisional").sum())))
        st.append(("05_guides", "dual-target cells (two different targets; ambiguous)", int((status == "dual_target").sum())))
        st.append(("05_guides", "incomplete-pair cells (one scaffold slot only)", int(status.str.startswith("incomplete").sum())))
        st.append(("05_guides", "pair-ambiguous cells (multiple strong guides in a slot)", int(status.str.startswith("ambiguous").sum())))
        st.append(("05_guides", "ambiguous cells total (perturbation_class)", int((klass == "ambiguous").sum())))
        st.append(("05_guides", "unassigned cells (perturbation_class)", int((klass == "unassigned").sum())))
        st.append(("06_clustering", "cells used for clustering", len(spp)))
        tested = ((klass == "targeting") & spp["target_gene"].astype(str).isin(tested_targets)) | (klass == "non-targeting")
        st.append(("07_perturbation_testing", "cells used for perturbation testing (targeting of tested targets + NTC)", int(tested.sum())))
        st.append(("08_final", "final analyzed cells (processed object)", len(spp)))
        prev = {"00_cellranger_called": None, "01_loaded": n_cr, "02_prefilter_min_genes_200": len(sa), "03_min_genes_final_1000": int(pre.sum()),
                "04_max_pct_mt_20": int(fin.sum()), "04_final_qc_pass_pipeline": len(sa), "05_guides": len(spp), "06_clustering": len(spp),
                "07_perturbation_testing": len(spp), "08_final": len(spp)}
        for stage, cat, n in st:
            pv = prev[stage]
            rows.append({"run": run.label, "well": g, "condition": cond, "replicate": rep, "replicate_type": "unknown", "condition_status": "inferred",
                         "pipeline_stage": stage, "cell_category": cat, "cell_count": int(n),
                         "pct_of_input": round(100 * n / max(n_cr, 1), 3), "pct_of_previous_stage": round(100 * n / pv, 3) if pv else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(run.tab / "cell_counts_before_after.csv", index=False)
    wide = df.pivot_table(index=["run", "well", "condition", "replicate"], columns="cell_category", values="cell_count", aggfunc="first")
    wide.to_csv(run.tab / "cell_counts_before_after_wide.csv")
    return df


def qc_tables(run: Run):
    a = run.allc.obs
    cols = QC_COLS + ["guide_umi_total", "n_guides_ge_min_umi", "n_strong_guides_A_any", "n_strong_guides_C_any"]
    per_cell = a[["well", "condition", "replicate", "cell_barcode"] + cols + ["pipeline_qc_pass", "perturbation_class", "target_gene", dg.OBS_PAIR_STATUS]].copy()
    per_cell.insert(0, "cell_id", a.index)
    per_cell.to_csv(run.tab / "qc_metrics_per_cell.csv", index=False)
    rows = []
    for g in run.groups:
        m = run.mask(a, g)
        for stage, mm in (("before_qc", m), ("after_qc", m & a["pipeline_qc_pass"])):
            s = a[mm]
            rows.append({"run": run.label, "well": g, "stage": stage, "n_cells": len(s),
                         **{f"median_{c}": float(s[c].median()) for c in cols},
                         **{f"mean_{c}": float(s[c].mean()) for c in QC_COLS},
                         "frac_pct_mt_ge_10": float((s["pct_counts_mt"] >= 10).mean()) if len(s) else np.nan,
                         "frac_pass_qc": float(s["pipeline_qc_pass"].mean()) if len(s) else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(run.tab / "qc_metrics_per_well.csv", index=False)
    return per_cell, df


def guide_assignment_summary(run: Run) -> pd.DataFrame:
    p = run.proc.obs
    rows = []
    for g in run.groups:
        s = p[run.mask(p, g)]
        n = len(s)
        d = {"run": run.label, "well": g, "n_qc_pass_cells": n, "assignment_mode": str(s[dg.OBS_MODE].iloc[0]) if n else ""}
        for k in ("targeting", "non-targeting", "ambiguous", "unassigned"):
            d[f"n_{k}"] = int((s["perturbation_class"].astype(str) == k).sum())
            d[f"pct_{k}"] = round(100 * d[f"n_{k}"] / max(n, 1), 3)
        for st in dg.PAIR_STATUS_ORDER:
            d[f"n_{st}"] = int((s[dg.OBS_PAIR_STATUS].astype(str) == st).sum())
        d["n_provisional_assignments"] = int(s[dg.OBS_PAIR_PROVISIONAL].astype(bool).sum())
        d["n_targets_with_ge10_targeting_cells"] = int((s.loc[s["perturbation_class"].astype(str) == "targeting", "target_gene"].value_counts() >= 10).sum())
        d["median_guide_umis_per_cell"] = float(s["guide_umi_total"].median()) if n else np.nan
        d["median_n_strong_A"] = float(s["n_strong_guides_A_any"].median()) if n else np.nan
        d["median_n_strong_C"] = float(s["n_strong_guides_C_any"].median()) if n else np.nan
        rows.append(d)
    df = pd.DataFrame(rows)
    df.to_csv(run.tab / "guide_assignment_summary.csv", index=False)
    return df


def default_vs_dual(run: Run) -> pd.DataFrame:
    """Re-run the single-guide baseline rule on the same guide matrix and cross-tabulate."""
    from perturbseq_pipeline.config import Config
    from perturbseq_pipeline.guides import assign_guides
    proc = run.proc
    cfg = Config.from_dict(run.cfg)
    cfg.guides.assignment_mode = "single_guide"
    g = ad.AnnData(X=sp.csr_matrix(proc.obsm["guide_counts"]))
    g.obs_names = proc.obs_names
    g.var_names = pd.Index(run.gvar.index)
    g.var["target_gene_name"] = run.gvar["target_gene_name"].to_numpy()
    tmp = ad.AnnData(X=sp.csr_matrix((proc.n_obs, 1)), obs=pd.DataFrame(index=proc.obs_names))
    tmp = assign_guides(tmp, g, cfg)
    single = tmp.obs["perturbation_class"].astype(str).to_numpy()
    single_t = tmp.obs["target_gene"].astype(str).to_numpy()
    dual = proc.obs["perturbation_class"].astype(str).to_numpy()
    dual_t = proc.obs["target_gene"].astype(str).to_numpy()
    status = proc.obs[dg.OBS_PAIR_STATUS].astype(str).to_numpy()
    well = proc.obs["well"].astype(str).to_numpy()

    def dual_cat(k, s):
        if k == "targeting":
            return "targeting (provisional target+NTC)" if s == "target_ntc_provisional" else "targeting (same-target pair)"
        if k == "non-targeting":
            return "non-targeting (NTC pair)"
        if s == "dual_target":
            return "dual-target (ambiguous)"
        if s.startswith("incomplete"):
            return "incomplete pair (ambiguous)"
        if s.startswith("ambiguous"):
            return "multiple strong guides in a slot (ambiguous)"
        if s == "below_min_umi":
            return "below min_umi (ambiguous)"
        return "unassigned (no guide)"
    dcat = np.array([dual_cat(k, s) for k, s in zip(dual, status)], dtype=object)
    rows = []
    for g_ in run.groups:
        m = np.ones(len(dual), bool) if g_ == "ALL" else well == g_
        ct = pd.crosstab(pd.Series(single[m], name="single_guide_class"), pd.Series(dcat[m], name="dual_guide_category"))
        for sc in ct.index:
            for dc in ct.columns:
                rows.append({"run": run.label, "well": g_, "single_guide_class": sc, "dual_guide_category": dc, "n_cells": int(ct.loc[sc, dc]),
                             "pct_of_cells": round(100 * ct.loc[sc, dc] / m.sum(), 3)})
        same_target_when_both_assigned = ((single == "targeting") & (dual == "targeting") & m)
        rows.append({"run": run.label, "well": g_, "single_guide_class": "targeting", "dual_guide_category": "targeting: same target as single-guide call",
                     "n_cells": int((same_target_when_both_assigned & (single_t == dual_t)).sum()), "pct_of_cells": np.nan})
        rows.append({"run": run.label, "well": g_, "single_guide_class": "targeting", "dual_guide_category": "targeting: different target than single-guide call",
                     "n_cells": int((same_target_when_both_assigned & (single_t != dual_t)).sum()), "pct_of_cells": np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(run.tab / "default_vs_dual_assignment.csv", index=False)
    # movement summary for ambiguous cells of the baseline
    amb = single == "ambiguous"
    mv = pd.Series(dcat[amb]).value_counts()
    log(f"[{run.label}] single-guide ambiguous cells: {int(amb.sum()):,} -> " + ", ".join(f"{k}: {int(v):,}" for k, v in mv.items()))
    run.single_class = single
    run.dual_cat = dcat
    return df


# ------------------------------------------------------------------------------------------ perturbation


def _vec(proc, gene):
    X = proc.layers["lognorm"] if "lognorm" in proc.layers else proc.X
    col = X[:, proc.var_names.get_loc(gene)]
    return np.asarray(col.todense()).ravel() if sp.issparse(col) else np.asarray(col).ravel()


def perturbation_tables(run: Run):
    cfg, proc = run.cfg, run.proc
    pc = cfg["perturbation"]
    alpha, max_lfc, min_cells, min_ctrl = pc["fdr_alpha"], pc["max_log2fc_for_hit"], pc["min_cells_per_target"], pc["min_control_cells"]
    obs = proc.obs
    klass = obs["perturbation_class"].astype(str).to_numpy(); tgt = obs["target_gene"].astype(str).to_numpy()
    gid = obs["guide_id"].astype(str).to_numpy(); well = obs["well"].astype(str).to_numpy()
    status = obs[dg.OBS_PAIR_STATUS].astype(str).to_numpy()
    gA = obs[dg.OBS_SLOT_ID.format(c="A")].astype(str).to_numpy(); gC = obs[dg.OBS_SLOT_ID.format(c="C")].astype(str).to_numpy()
    pair_id = obs[dg.OBS_PAIR_ID].astype(str).to_numpy()
    mode = str(obs[dg.OBS_MODE].iloc[0])
    targets = sorted(set(tgt[klass == "targeting"]))
    present = {t: symbol_of(t) for t in targets if symbol_of(t) in proc.var_names}
    absent = sorted(set(targets) - set(present))
    log(f"[{run.label}] {len(targets)} assigned targets; {len(present)} testable by symbol; absent from matrix: {absent}")
    cache = {}
    vec = lambda g: cache.setdefault(g, _vec(proc, g))
    strata = {ALL_TARGETING: np.ones(len(obs), bool), STRICT: status == "same_target_pair"}
    n_assigned = {w: int(np.isin(klass[(well == w) if w != "ALL" else np.ones(len(obs), bool)], ["targeting", "non-targeting"]).sum()) for w in run.groups}

    def one(mp, mc, gene):
        if mp.sum() < min_cells or mc.sum() < min_ctrl:
            return None
        v = vec(gene)
        return compare_groups(v[mp], v[mc])

    bt, bg, bi = [], [], []
    for t, gene in present.items():
        for w in run.groups:
            wm = np.ones(len(obs), bool) if w == "ALL" else well == w
            m_ntc = (klass == "non-targeting") & wm
            for stratum, sm in strata.items():
                mp = (klass == "targeting") & (tgt == t) & wm & sm
                m_oth = (klass == "targeting") & (tgt != t) & wm & sm
                base = {"run": run.label, "target_gene_name": t, "target_gene": gene, "alias_mapped": gene != t, "well": w,
                        "condition": COND.get(w, "pooled"), "replicate": REP.get(w, "pooled"), "assignment_mode": mode, "assignment_stratum": stratum,
                        "n_guide_assigned_cells": n_assigned[w], "n_targeting_cells": int(mp.sum()), "n_non_targeting_cells": int(m_ntc.sum()),
                        "n_other_control_cells": int(m_oth.sum())}
                for ctrl, mc in (("ntc", m_ntc), ("other", m_oth)):
                    r = one(mp, mc, gene)
                    row = dict(base, control=ctrl,
                               median_lognorm_targeting=float(np.median(vec(gene)[mp])) if mp.any() else np.nan,
                               median_lognorm_control=float(np.median(vec(gene)[mc])) if mc.any() else np.nan)
                    row.update(r if r is not None else {"skipped_reason": f"< {min_cells} targeting or < {min_ctrl} control cells"})
                    bt.append(row)
                if stratum != ALL_TARGETING:
                    continue
                # per pair (guide_id = "A|C")
                for g in sorted(set(gid[mp])):
                    mg = mp & (gid == g)
                    r = one(mg, m_ntc, gene)
                    a_id, c_id = (g.split("|") + [""])[:2]
                    row = dict(base, guide_id=g, guide_A_id=a_id, guide_C_id=c_id, pair_id=str(pd.Series(pair_id[mg]).mode().iloc[0]) if mg.any() else "",
                               pair_assignment_status=str(pd.Series(status[mg]).mode().iloc[0]) if mg.any() else "", control="ntc",
                               n_targeting_cells=int(mg.sum()))
                    row.update(r if r is not None else {"skipped_reason": f"< {min_cells} cells with this pair or < {min_ctrl} controls"})
                    bg.append(row)
                # per individual guide (any cell where the guide occupies its slot)
                for slot, arr in (("A", gA), ("C", gC)):
                    for g in sorted(set(arr[mp]) - {"ambiguous", "unassigned"}):
                        mg = mp & (arr == g)
                        r = one(mg, m_ntc, gene)
                        row = dict(base, guide_id=g, scaffold=slot, control="ntc", n_targeting_cells=int(mg.sum()))
                        row.update(r if r is not None else {"skipped_reason": f"< {min_cells} cells with this guide or < {min_ctrl} controls"})
                        bi.append(row)

    def finish(rows, keys):
        df = pd.DataFrame(rows)
        for c in ("ks_pval", "mwu_pval_less", "log2fc"):
            if c not in df:
                df[c] = np.nan
        df["fdr_ks"] = np.nan; df["fdr_mwu"] = np.nan
        for _, idx in df.groupby(keys, dropna=False).groups.items():
            df.loc[idx, "fdr_ks"] = benjamini_hochberg(df.loc[idx, "ks_pval"].to_numpy(float))
            df.loc[idx, "fdr_mwu"] = benjamini_hochberg(df.loc[idx, "mwu_pval_less"].to_numpy(float))
        df["raw_pvalue_ks"] = df["ks_pval"]; df["raw_pvalue_mwu_less"] = df["mwu_pval_less"]
        df["neg_log10_fdr"] = -np.log10(np.clip(df["fdr_ks"].astype(float), 1e-300, 1))
        df["neg_log10_fdr_mwu"] = -np.log10(np.clip(df["fdr_mwu"].astype(float), 1e-300, 1))
        df["direction"] = np.select([df["log2fc"] < 0, df["log2fc"] > 0], ["down", "up"], "none")
        df.loc[df["log2fc"].isna(), "direction"] = "not_tested"
        df["default_hit"] = (df["fdr_ks"] < alpha) & (df["log2fc"] < max_lfc)
        df["hit_status"] = np.where(df["log2fc"].isna(), "not_tested", np.where(df["default_hit"], "target_transcript_depletion_association", "not_significant"))
        df["hit_rule"] = f"fdr_ks < {alpha} and log2fc < {max_lfc} (pipeline default; BH within run x well x stratum x control)"
        df["fdr_convention"] = "fdr_ks = BH FDR of two-sided KS p (raw); neg_log10_fdr = -log10(fdr_ks) (positive; not a cell count)"
        return df

    bt = finish(bt, ["well", "control", "assignment_stratum"])
    bg = finish(bg, ["well"])
    bi = finish(bi, ["well", "scaffold"])
    bt.to_csv(run.tab / "perturbation_expression_by_target.csv", index=False)
    bg.to_csv(run.tab / "perturbation_expression_by_guide.csv", index=False)
    bi.to_csv(run.tab / "perturbation_expression_by_individual_guide.csv", index=False)
    per_well = bt[(bt.control == "ntc") & (bt.assignment_stratum == ALL_TARGETING)].copy()
    per_well.to_csv(run.tab / "perturbation_per_well.csv", index=False)
    rows = []
    for t, gene in present.items():
        base = bt[(bt.target_gene_name == t) & (bt.control == "ntc") & (bt.assignment_stratum == ALL_TARGETING)]
        sub = base[base.well != "ALL"]
        tested = sub[sub["log2fc"].notna()]
        pooled = base[base.well == "ALL"].iloc[0] if (base.well == "ALL").any() else (sub.iloc[0] if len(sub) else None)
        if pooled is None:
            continue
        strict = bt[(bt.target_gene_name == t) & (bt.control == "ntc") & (bt.assignment_stratum == STRICT) & (bt.well == ("ALL" if (base.well == "ALL").any() else sub.well.iloc[0]))]
        row = {"run": run.label, "target_gene_name": t, "target_gene": gene, "n_wells_with_targeting_cells": int((sub["n_targeting_cells"] > 0).sum()),
               "n_wells_tested": int(len(tested)),
               "n_wells_consistent_direction_with_pooled": int((np.sign(tested["log2fc"]) == np.sign(pooled["log2fc"])).sum()) if np.isfinite(pooled["log2fc"]) else np.nan,
               "n_wells_passing_fdr_0.05_and_down": int(tested["default_hit"].sum()), "pooled_n_targeting_cells": int(pooled["n_targeting_cells"]),
               "pooled_log2fc": pooled["log2fc"], "pooled_fdr_ks": pooled["fdr_ks"], "pooled_neg_log10_fdr": pooled["neg_log10_fdr"], "pooled_hit": bool(pooled["default_hit"]),
               "strict_same_target_log2fc": float(strict["log2fc"].iloc[0]) if len(strict) else np.nan,
               "strict_same_target_fdr_ks": float(strict["fdr_ks"].iloc[0]) if len(strict) else np.nan,
               "strict_same_target_hit": bool(strict["default_hit"].iloc[0]) if len(strict) else False,
               "replicate_type": "unknown (well-level / capture-level comparison; A/B not confirmed as biological replicates)",
               "evidence_level": "combined pooled evidence" if run.label == "combined" else "per-well evidence"}
        for w in run.wells:
            r = sub[sub.well == w]
            row[f"log2fc_{w}"] = float(r["log2fc"].iloc[0]) if len(r) else np.nan
            row[f"fdr_ks_{w}"] = float(r["fdr_ks"].iloc[0]) if len(r) else np.nan
            row[f"n_targeting_{w}"] = int(r["n_targeting_cells"].iloc[0]) if len(r) else 0
        n, k = row["n_wells_tested"], row["n_wells_passing_fdr_0.05_and_down"]
        row["reproducibility"] = ("depletion in all tested wells (exploratory; replicate type unconfirmed)" if n >= 2 and k == n
                                  else "depletion in some wells (exploratory)" if k > 0 else "not significant in any well" if n >= 2 else "single well")
        rows.append(row)
    rep = pd.DataFrame(rows)
    rep.to_csv(run.tab / "perturbation_replicate_summary.csv", index=False)
    layers = {"run": run.label, "guide_assigned_cells": int(np.isin(klass, ["targeting", "non-targeting"]).sum()),
              "targeting_cells": int((klass == "targeting").sum()), "targeting_cells_same_target_pairs": int((status == "same_target_pair").sum()),
              "targeting_cells_provisional_target_ntc": int((status == "target_ntc_provisional").sum()),
              "targets_assigned": len(targets), "targets_testable_by_symbol": len(present), "targets_not_in_expression_matrix": ",".join(absent),
              "targets_with_significant_depletion_pooled_or_single_run": int(rep["pooled_hit"].sum()) if len(rep) else 0,
              "targets_with_significant_depletion_strict_same_target": int(rep["strict_same_target_hit"].sum()) if len(rep) else 0,
              "targeting_cells_of_depleted_targets": int(((klass == "targeting") & np.isin(tgt, rep.loc[rep.pooled_hit, "target_gene_name"] if len(rep) else [])).sum())}
    pd.DataFrame([layers]).to_csv(run.tab / "perturbation_response_layers.csv", index=False)
    return bt, bg, bi, rep, present
