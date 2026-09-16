#!/usr/bin/env python
"""Iteration 4 validation (SLURM only): task section 10 checklist for results/Hanrui_Fang_paired_guide_full_4."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
import anndata as ad, h5py, numpy as np, pandas as pd, yaml
from lxml import html as lxml_html
_HP = lxml_html.HTMLParser(huge_tree=True)  # 100+ MB reports with embedded figures exceed libxml2 default limits
from perturbseq_pipeline import dual_guides as dg

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
OUT = REPO / "results" / "Hanrui_Fang_paired_guide_full_4"
PREV = REPO / "results" / "Hanrui_Fang_pair_guide_full_3"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
RUNS = {"combined": OUT / "combined", **{w: OUT / "samples" / w for w in WELLS}}
MODULE_TABLES = {"enrichment": ["enrichment", "enrichment_full"], "modules": ["cofunctional_modules", "gene_programs", "program_summary", "program_enrichment", "tf_hubs", "module_program_strength"],
                 "ps_score": ["ps_score"], "lochness": ["lochness", "lochness_by_cluster"], "distance": ["perturbation_distance"], "distance_space": ["perturbation_space_coordinates", "phenotype_modules", "perturbation_neighbors"], "meta": ["perturbation_meta"]}
MODULE_FIG_SECTIONS = {"enrichment": ["enrichment", "enrichment/per_target"], "modules": ["modules"], "ps_score": ["ps_score", "ps_score/per_target"], "lochness": ["lochness", "lochness/per_target"], "distance": ["distance"], "distance_space": ["distance_space"]}
SECTIONS = ["summary", "qc", "guides", "clustering", "perturbation", "enrichment", "ps", "lochness", "distance", "distance_space", "modules", "meta", "repro"]
checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:600]})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {str(detail)[:300]}", flush=True)


def read_elem(f, key):
    return ad.io.read_elem(f[key]) if hasattr(ad, "io") else ad.experimental.read_elem(f[key])


def main():
    prev_pa = {w: pd.read_csv(PREV / "samples" / w / "tables" / "pair_assignment_per_lane.csv").set_index("lane_id") for w in WELLS}
    obs_all, counts = {}, {}
    for k, d in RUNS.items():
        rc = d / "logs" / "resolved_config.yaml"
        cfg = yaml.safe_load(open(rc)) if rc.is_file() else None
        ok = cfg is not None and (d / "report.html").is_file() and (d / "report.md").is_file() and (d / cfg["output"]["h5ad_name"]).is_file()
        check(f"1 {k}: run completed (report.html + report.md + processed h5ad + resolved config)", ok, str(d))
        if not ok:
            continue
        h5 = d / cfg["output"]["h5ad_name"]
        with h5py.File(h5, "r") as f:
            o = read_elem(f, "obs"); obsm = list(f["obsm"].keys()); uns_keys = list(f["uns"].keys())
        obs_all[k] = o
        check(f"6 {k}: processed h5ad opens ({len(o):,} cells, {len(o.columns)} obs columns)", len(o) > 1000, str(h5))
        lane = "ALL" if k == "combined" else k
        pa = pd.read_csv(d / "tables" / "pair_assignment_per_lane.csv").set_index("lane_id")
        if k != "combined":
            same = all(int(pa.loc[lane, s]) == int(prev_pa[k].loc[lane, s]) for s in (dg.STATUS_PAIR_TARGETING, dg.STATUS_PAIR_NTC, dg.STATUS_PAIR_TARGET_NTC, dg.STATUS_UNRESOLVED, dg.STATUS_DUAL_TARGET, dg.STATUS_INCOMPLETE))
            check(f"2 {k}: strict pair-assignment counts identical to iteration 3", same, f"pair_targeting {int(pa.loc[lane, dg.STATUS_PAIR_TARGETING])} vs {int(prev_pa[k].loc[lane, dg.STATUS_PAIR_TARGETING])}")
        st = o[dg.OBS_PAIR_STATUS].astype(str); kl = o["perturbation_class"].astype(str)
        check(f"12 {k}: primary classes = strict pairs only; ambiguous / sensitivity / unresolved cells not targeting or NTC",
              ((kl == "targeting") == (st == dg.STATUS_PAIR_TARGETING)).all() and ((kl == "non-targeting") == (st == dg.STATUS_PAIR_NTC)).all() and (kl[st == dg.STATUS_PAIR_TARGET_NTC] == "ambiguous").all(), st.value_counts().to_dict())
        check(f"11 {k}: no Harmony (batch_key null, no X_pca_harmony) and no doublet removal (input cells == QC accounting)", cfg["cluster"]["batch_key"] is None and "X_pca_harmony" not in obsm and not any("doublet" in c.lower() and "removed" in c.lower() for c in o.columns), obsm)
        man = pd.read_csv(d / "tables" / "figure_manifest.csv")
        secs = set(man.section)
        check(f"3 {k}: QC, guide and clustering figures exist", all(s in secs for s in ("qc", "guides", "clustering")) and all(Path(p).is_file() and Path(p).stat().st_size > 1000 for p in man[man.section.isin(["qc", "guides", "clustering"])].path))
        for mod, tabs in MODULE_TABLES.items():
            missing_t = [t for t in tabs if not (d / "tables" / f"{t}.csv").is_file()]
            n_f = int(man.section.isin(MODULE_FIG_SECTIONS.get(mod, [])).sum())
            check(f"4/5 {k}: module {mod} executed (tables {tabs}; {n_f} figures)", not missing_t and (n_f > 0 or mod == "meta"), f"missing tables: {missing_t}")
        ms = pd.read_csv(d / "tables" / "module_status.csv") if (d / "tables" / "module_status.csv").is_file() else None
        check(f"13 {k}: module status table shows every enabled module completed", ms is not None and (ms[ms.enabled_in_config]["status"] == "completed").all(), ms[["module", "status"]].to_dict(orient="records") if ms is not None else "missing")
        lo = pd.read_csv(d / "tables" / "lochness.csv") if (d / "tables" / "lochness.csv").is_file() else None
        mapping = h5.with_name(h5.stem + "_column_name_mapping.csv")
        unsafe = [t for t in (lo["target_gene"] if lo is not None else []) if re.search(r"[^A-Za-z0-9_.:+\-]", str(t))]
        check(f"7 {k}: target names with special characters written safely ({len(unsafe)} such lochNESS targets; mapping saved)", (not unsafe) or (mapping.is_file() and "column_name_mapping" in uns_keys and all(re.fullmatch(r"[A-Za-z0-9_.:+\-]+", c) for c in o.columns)), f"unsafe targets: {unsafe[:4]}; mapping: {mapping.name if mapping.is_file() else 'none'}")
        check(f"10 {k}: all-target result tables present for every analysis", all((d / "tables" / f"{t}.csv").is_file() for t in ("pair_perturbation_primary", "pair_perturbation_by_target", "pair_perturbation_by_pair", "ps_score", "lochness", "perturbation_distance", "perturbation_space_coordinates", "cofunctional_modules", "enrichment_full", "perturbation_meta")))
        top6 = sorted(p.name for p in (d / "tables").glob("top6_*.csv"))
        check(f"9 {k}: top-six tables for every analysis", {"top6_perturbation.csv", "top6_ps_score.csv", "top6_lochness.csv", "top6_distance.csv", "top6_enrichment.csv", "top6_modules.csv", "top6_distance_space.csv"} <= set(top6), top6)
        doc = lxml_html.fromstring((d / "report.html").read_text(errors="ignore"), parser=_HP)
        ids = {e.get("id") for e in doc.xpath("//h2[@id]")}
        imgs = doc.xpath("//img"); bad = [i.get("src", "")[:40] for i in imgs if not i.get("src", "").startswith("data:image/png;base64,")]
        hrefs = [a.get("href") for a in doc.xpath("//a[@href]") if a.get("href") and not a.get("href").startswith(("#", "http"))]
        broken = [h for h in hrefs if not (d / h).exists()]
        txt = doc.text_content()
        check(f"8 {k}: report.html has every section, {len(imgs)} embedded figures, no broken links", set(SECTIONS) <= ids and not bad and not broken and len(imgs) >= 150, f"missing sections {sorted(set(SECTIONS) - ids)}; broken {broken[:3]}")
        check(f"9 {k}: report shows 'Best six' blocks for direct perturbation, enrichment, PS, lochNESS, distance, perturbation space, hubs", txt.count("Best six") >= 7 and "Ranking rule" in txt, f"{txt.count('Best six')} blocks")
        check(f"8 {k}: report states single-guide rule is diagnostic only and lists excluded categories", "diagnostic" in txt and "excluded from primary" in txt)
        cc = pd.read_csv(d / "tables" / "cell_counts_before_after.csv").set_index("lane_id"); counts[k] = cc
        check(f"1 {k}: QC accounting consistent with the object", int(cc.loc[lane, "final_cells_retained"]) == len(o))
        log = (d / "logs" / "run.log").read_text(errors="ignore")
        tb = [l for l in log.splitlines() if "Traceback" in l or " ERROR " in l]
        disabled = [l for l in log.splitlines() if re.search(r"disabled|skipp", l, re.I) and not re.search(r"harmony|batch|distance_space|meta|doublet", l, re.I)]
        check(f"13 {k}: run log has no tracebacks / errors", not tb, tb[:3])
        check(f"13 {k}: no silently disabled requested module in the run log (informational skips listed)", not any(re.search(r"(ps_score|lochness|modules|distance|enrichment).*(disabled)", l, re.I) for l in disabled), [l[:160] for l in disabled[:5]])
    if all(k in counts for k in RUNS):
        comb = counts["combined"]
        check("1 combined input cells == sum of per-sample inputs; per-well retained cells equal", int(comb.loc["ALL", "input_cells"]) == sum(int(counts[w].loc[w, "input_cells"]) for w in WELLS) and all(int(comb.loc[w, "final_cells_retained"]) == int(counts[w].loc[w, "final_cells_retained"]) for w in WELLS))
        check("2 combined barcodes unique and union of per-sample cells", obs_all["combined"].index.is_unique and set(obs_all["combined"].index) == set().union(*[set(obs_all[w].index) for w in WELLS]))
    for f in ("report.html", "report.md", "README.md", "execution_commands.md", "run_manifest.json", "config/Hanrui_Fang_paired_guide_full_4.yaml", "config_used.yaml", "audit/guide_reference_used.csv", "audit/experimental_information_used.md", "audit/iteration4_input_provenance.csv",
              "tables/target_support_matrix_across_runs.csv", "tables/module_status_all_runs.csv", "tables/run_index.csv", "figures/root_figures_index.csv", "logs/run_times.txt", "inputs/PROVENANCE.md"):
        check(f"9 root output {f}", (OUT / f).is_file() and (OUT / f).stat().st_size > 0)
    root = lxml_html.fromstring((OUT / "report.html").read_text(errors="ignore"), parser=_HP) if (OUT / "report.html").is_file() else None
    if root is not None:
        ids = {e.get("id") for e in root.xpath("//h2[@id]")}
        imgs = root.xpath("//img"); hrefs = [a.get("href") for a in root.xpath("//a[@href]") if a.get("href") and not a.get("href").startswith(("#", "http"))]
        broken = [h for h in hrefs if not (OUT / h).exists()]
        check(f"8 root report: all sections incl. index/support/previous, {len(imgs)} embedded figures, no broken links, links to every per-run report", set(SECTIONS + ["index", "support", "previous"]) <= ids and not broken and all(f"{p}/report.html" in hrefs for p in ["combined"] + [f"samples/{w}" for w in WELLS]), f"missing {sorted(set(SECTIONS + ['index', 'support', 'previous']) - ids)}; broken {broken[:3]}")
        check("8 root report: no full_3 numerical links", not any("pair_guide_full_3" in h for h in hrefs))
    logs = list(REPO.glob("hanrui_fang_full_4_*.err")) + list(REPO.glob("hanrui_fang_full_4_*.out"))
    tb = [p.name for p in logs if "Traceback" in p.read_text(errors="ignore")]
    check("13 SLURM production logs have no tracebacks", logs and not tb, tb)
    check("PREV iteration-3 results untouched", all((PREV / f).is_file() for f in ("report.html", "run_manifest.json")) and not any(p.stat().st_mtime > (OUT / "config" / "Hanrui_Fang_paired_guide_full_4.yaml").stat().st_mtime for p in [PREV / "report.html", PREV / "run_manifest.json", PREV / "combined" / "report.html"]))
    df = pd.DataFrame(checks); df.to_csv(OUT / "tables" / "final_validation.csv", index=False)
    n = int((df.status == "PASS").sum()); (OUT / "final_validation.txt").write_text("\n".join(f"[{r.status}] {r.check}: {r.detail}" for r in df.itertuples()) + f"\n\n{n}/{len(df)} checks passed\n")
    print(f"\n{n}/{len(df)} checks passed")
    return 0 if n == len(df) else 1


if __name__ == "__main__":
    sys.exit(main())
