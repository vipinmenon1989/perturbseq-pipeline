"""Reopen the core-run outputs and verify the documented contract (run on a compute node)."""
import sys
from pathlib import Path
import anndata as ad, numpy as np, pandas as pd, scipy.sparse as sp, yaml

RES = Path(sys.argv[1]); cfg = yaml.safe_load(open(RES / "logs" / "resolved_config.yaml")); lines = []
def rec(name, cond, detail=""):
    lines.append(f"  {'PASS' if cond else 'FAIL'}  {name}{(': ' + detail) if detail else ''}")
p = ad.read_h5ad(RES / cfg["output"]["h5ad_name"]); a = ad.read_h5ad(RES / cfg["output"]["unfiltered_h5ad_name"])
lines.append(f"[{cfg['output']['h5ad_name']}] {p.shape}"); rec("unique obs/var names", p.obs_names.is_unique and p.var_names.is_unique)
rec("layers counts + lognorm", "counts" in p.layers and "lognorm" in p.layers, str(list(p.layers)))
rec("counts integer", np.issubdtype(p.layers["counts"].dtype, np.integer) or bool(np.all(np.mod(sp.csr_matrix(p.layers["counts"])[:2000].data, 1) == 0)), str(p.layers["counts"].dtype))
for c in ("well", "lane_id", "sample", "condition", "replicate", "replicate_type", "condition_status", "total_counts", "n_genes_by_counts", "pct_counts_mt", "pct_counts_ribo", "pct_counts_hb", "target_gene", "guide_id", "perturbation_class", "top_guide_count", "second_guide_count", "total_guide_counts", "n_guides_detected", "leiden"):
    rec(f"obs.{c}", c in p.obs)
rec("obsm X_pca/X_umap/guide_counts", all(k in p.obsm for k in ("X_pca", "X_umap", "guide_counts")), str(list(p.obsm)))
rec("guide_counts columns == uns guide_names (560)", p.obsm["guide_counts"].shape[1] == len(p.uns.get("guide_names", [])) == 560, str(p.obsm["guide_counts"].shape))
rec("obs_names start with well_", bool(p.obs_names.str.match(r"^HF01[12][AB]_").all()))
lines.append("  classes: " + str(dict(p.obs["perturbation_class"].value_counts()))); lines.append("  wells: " + str(dict(p.obs["well"].value_counts().sort_index()))); lines.append(f"  leiden clusters: {p.obs['leiden'].nunique()}")
lines.append(f"[{cfg['output']['unfiltered_h5ad_name']}] {a.shape}"); rec("all loaded cells present (163,991)", a.n_obs == 163991, str(a.n_obs)); rec("processed cells subset of all-cells", p.obs_names.isin(a.obs_names).all())
rec("QC metrics present pre-QC", all(c in a.obs for c in ("total_counts", "n_genes_by_counts", "pct_counts_mt"))); rec("no lognorm (raw checkpoint)", "lognorm" not in a.layers); rec("obsm guide_counts", "guide_counts" in a.obsm)
rec("uns qc_stage note", "qc_stage" in a.uns, str(a.uns.get("qc_stage")))
for t in ("cell_counts_before_after.csv", "perturbation_expression_by_target.csv", "perturbation_expression_by_guide.csv", "perturbation_replicate_summary.csv", "qc_steps.csv", "guide_qc.csv", "clusters.csv", "enrichment.csv"):
    f = RES / "tables" / t; rec(f"tables/{t}", f.is_file() and f.stat().st_size > 0)
for d in ("qc", "guides", "clustering", "perturbation"):
    n = len(list((RES / "figures" / d).glob("*.png"))); rec(f"figures/{d} ({n} png)", n > 0)
rec("report.html", (RES / "report.html").stat().st_size > 1e6); rec("logs/run.log + resolved_config.yaml", (RES / "logs" / "run.log").is_file() and (RES / "logs" / "resolved_config.yaml").is_file())
rec("disabled modules in resolved config", all(not cfg[s]["enabled"] for s in ("modules", "ps_score", "lochness", "distance", "distance_space", "meta_analysis")))
rec("enrichment enabled", cfg["enrichment"]["enabled"]); rec("no Harmony (batch_key null)", cfg["cluster"]["batch_key"] is None)
cc = pd.read_csv(RES / "tables" / "cell_counts_before_after.csv"); rec("cell_counts has per-well rows", set(cc["well"]) >= {"HF011A", "HF011B", "HF012A", "HF012B", "ALL"}, str(sorted(set(cc["well"]))))
text = "\n".join(lines); (RES / "tables" / "final_validation.txt").write_text(text + "\n"); print(text); print("ALL PASS" if all(" FAIL " not in l for l in lines) else "SOME FAIL")
