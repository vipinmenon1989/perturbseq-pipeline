"""Smoke tests (STANDARD vs FORCED LARGE) and medium-scale sparse stress test.

Executes:
1. Synthetic dataset generation with 3 batches, NTC + 10 targets, sparse counts.
2. STANDARD mode full CLI execution.
3. FORCED LARGE mode full CLI execution.
4. Numerical & statistical consistency comparison.
5. Medium-scale sparse stress test (100k cells x 2k genes x 500 targets).
"""

from __future__ import annotations

import os
import sys
import time
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
import anndata as ad
import psutil

from perturbseq_pipeline.config import Config
from perturbseq_pipeline.cli import run_pipeline


def get_rss_gb() -> float:
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 ** 3)


def make_smoke_dataset(out_path: Path, n_cells: int = 600, n_genes: int = 120, n_targets: int = 10, seed: int = 0):
    rng = np.random.default_rng(seed)
    targets = [f"TARGET{i}" for i in range(n_targets)] + ["non-targeting"]
    
    cell_targets = []
    cell_classes = []
    for i in range(n_cells):
        if i < n_cells // 2:
            t = targets[i % n_targets]
            cell_targets.append(t)
            cell_classes.append("targeting")
        else:
            cell_targets.append("non-targeting")
            cell_classes.append("non-targeting")
            
    batches = [f"B_{i % 3 + 1}" for i in range(n_cells)]
    gene_names = [f"TARGET{i}" if i < n_targets else f"GENE{i}" for i in range(n_genes)]
    
    # Sparse counts (poisson)
    raw = rng.poisson(1.5, size=(n_cells, n_genes)).astype(np.float32)
    # Knockdown signal for TARGET0, TARGET1
    for i in range(n_cells):
        if cell_targets[i] == "TARGET0":
            raw[i, 0] = 0
        elif cell_targets[i] == "TARGET1":
            raw[i, 1] = 0
            
    X_sparse = sp.csr_matrix(raw)
    
    adata = ad.AnnData(
        X=X_sparse.copy(),
        obs=pd.DataFrame({
            "gene_target": cell_targets,
            "perturbation_class": cell_classes,
            "lane_id": batches,
        }, index=[f"cell_{i}" for i in range(n_cells)]),
        var=pd.DataFrame(index=gene_names),
    )
    adata.layers["counts"] = X_sparse.copy()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    adata.write_h5ad(out_path)
    print(f"Created smoke dataset: {out_path} ({n_cells} cells x {n_genes} genes, {n_targets} targets)")
    return out_path


def run_smoke_tests():
    data_dir = Path("scratch/smoke_data")
    data_path = data_dir / "smoke_dataset.h5ad"
    make_smoke_dataset(data_path)
    
    # 1. STANDARD Smoke Test
    print("\n" + "=" * 70)
    print("RUNNING STANDARD MODE SMOKE TEST")
    print("=" * 70)
    
    out_std = Path("scratch/results_standard_smoke")
    if out_std.exists():
        shutil.rmtree(out_std)
        
    cfg_std_dict = {
        "run": {"name": "smoke_standard", "outdir": str(out_std), "seed": 42},
        "input": {"mode": "h5ad", "h5ad": str(data_path), "guide_obs_column": "gene_target", "counts_layer": "counts"},
        "metadata": {"require_for_multilane": False},
        "qc": {"min_genes_per_cell": 10, "min_genes_final": 10, "max_pct_mt": 100},
        "scaling": {"mode": "standard", "log_memory": True},
        "cluster": {"n_top_genes": 50, "n_pcs": 10},
        "perturbation": {"min_cells_per_target": 5, "min_control_cells": 5},
        "enrichment": {"min_cells_per_target": 5, "min_cells_per_cluster": 5, "permutations": 100},
        "modules": {"enabled": True, "min_cells_per_perturbation": 5, "min_perturbations": 3, "draw_networks": False},
        "lochness": {"enabled": True, "n_neighbors": 15, "min_cells_per_target": 5},
        "ps_score": {"enabled": True, "compute_lda_umap": False, "min_cells_per_target": 5},
    }
    
    cfg_std = Config.from_dict(cfg_std_dict)
    t0 = time.time()
    rss0 = get_rss_gb()
    res_std = run_pipeline(cfg_std)
    t_std = time.time() - t0
    rss_std = get_rss_gb()
    
    print(f"\nSTANDARD Mode Finished in {t_std:.2f}s | Peak RSS: {rss_std:.2f} GB")
    print(f"Summary: {res_std.summary()}")
    
    # Verify outputs
    assert (out_std / "report.html").is_file(), "Standard report missing"
    assert (out_std / "tables" / "perturbation.csv").is_file(), "Standard perturbation table missing"
    assert (out_std / "tables" / "enrichment_full.csv").is_file(), "Standard enrichment table missing"
    assert (out_std / "tables" / "effect_matrix.csv").is_file(), "Standard effect matrix missing"
    assert (out_std / "tables" / "lochness.csv").is_file(), "Standard lochness table missing"
    assert (out_std / "tables" / "ps_score.csv").is_file(), "Standard ps_score table missing"
    
    # 2. FORCED LARGE Smoke Test
    print("\n" + "=" * 70)
    print("RUNNING FORCED LARGE MODE SMOKE TEST")
    print("=" * 70)
    
    out_large = Path("scratch/results_large_smoke")
    if out_large.exists():
        shutil.rmtree(out_large)
        
    cfg_large_dict = {
        "run": {"name": "smoke_large", "outdir": str(out_large), "seed": 42},
        "input": {"mode": "h5ad", "h5ad": str(data_path), "guide_obs_column": "gene_target", "counts_layer": "counts"},
        "metadata": {"require_for_multilane": False},
        "qc": {"min_genes_per_cell": 10, "min_genes_final": 10, "max_pct_mt": 100},
        "scaling": {"mode": "large", "log_memory": True, "effect_gene_chunk": 16},
        "cluster": {"n_top_genes": 50, "n_pcs": 10},
        "perturbation": {"min_cells_per_target": 5, "min_control_cells": 5},
        "enrichment": {"min_cells_per_target": 5, "min_cells_per_cluster": 5, "permutations": 100},
        "modules": {"enabled": True, "min_cells_per_perturbation": 5, "min_perturbations": 3, "draw_networks": False},
        "lochness": {"enabled": True, "n_neighbors": 15, "min_cells_per_target": 5},
        "ps_score": {"enabled": True, "compute_lda_umap": False, "min_cells_per_target": 5},
    }
    
    cfg_large = Config.from_dict(cfg_large_dict)
    t0 = time.time()
    res_large = run_pipeline(cfg_large)
    t_large = time.time() - t0
    rss_large = get_rss_gb()
    
    print(f"\nFORCED LARGE Mode Finished in {t_large:.2f}s | Peak RSS: {rss_large:.2f} GB")
    print(f"Summary: {res_large.summary()}")
    
    # Verify outputs
    assert (out_large / "report.html").is_file(), "Large report missing"
    assert (out_large / "tables" / "perturbation.csv").is_file(), "Large perturbation table missing"
    assert (out_large / "tables" / "enrichment_full.csv").is_file(), "Large enrichment table missing"
    assert (out_large / "tables" / "effect_matrix.csv").is_file(), "Large effect matrix missing"
    assert (out_large / "tables" / "lochness.csv").is_file(), "Large lochness table missing"
    assert (out_large / "tables" / "ps_score.csv").is_file(), "Large ps_score table missing"
    
    # 3. Compare Standard vs Large Outputs
    print("\n" + "=" * 70)
    print("COMPARING STANDARD VS LARGE RESULTS")
    print("=" * 70)
    
    pert_std = res_std.perturbation_table.set_index("target_gene").sort_index()
    pert_large = res_large.perturbation_table.set_index("target_gene").sort_index()
    assert (pert_std["n_perturbed"] == pert_large["n_perturbed"]).all()
    np.testing.assert_allclose(pert_std["log2fc_ntc"], pert_large["log2fc_ntc"], rtol=1e-4, atol=1e-4)
    print("✓ Perturbation statistics match identically")
    
    enrich_std = pd.read_csv(out_std / "tables" / "enrichment_full.csv").sort_values(["target_gene", "cluster", "control"]).reset_index(drop=True)
    enrich_large = pd.read_csv(out_large / "tables" / "enrichment_full.csv").sort_values(["target_gene", "cluster", "control"]).reset_index(drop=True)
    assert (enrich_std["n_target_cells"] == enrich_large["n_target_cells"]).all()
    np.testing.assert_allclose(enrich_std["odds_ratio"], enrich_large["odds_ratio"], rtol=1e-4, atol=1e-4)
    print("✓ Enrichment statistics match identically")
    
    loch_std = pd.read_csv(out_std / "tables" / "lochness.csv").set_index("target_gene").sort_index()
    loch_large = pd.read_csv(out_large / "tables" / "lochness.csv").set_index("target_gene").sort_index()
    np.testing.assert_allclose(loch_std["mean_lochness_in_own_cells"], loch_large["mean_lochness_in_own_cells"], rtol=1e-4, atol=1e-4)
    print("✓ lochNESS summaries match identically")
    
    eff_std = pd.read_csv(out_std / "tables" / "effect_matrix.csv", index_col=0)
    eff_large = pd.read_csv(out_large / "tables" / "effect_matrix.csv", index_col=0)
    np.testing.assert_allclose(eff_std.to_numpy(), eff_large.to_numpy(), rtol=1e-4, atol=1e-4)
    print("✓ Module effect matrix matches identically")
    
    print("\nALL SMOKE TESTS AND CROSS-MODE COMPARISONS PASSED SUCCESSFULLY!")
    return {
        "std_runtime": t_std, "std_rss": rss_std,
        "large_runtime": t_large, "large_rss": rss_large,
    }


def run_medium_stress_test(n_cells: int = 100_000, n_genes: int = 2_000, n_targets: int = 500):
    print("\n" + "=" * 70)
    print(f"RUNNING MEDIUM-SCALE SPARSE STRESS TEST ({n_cells:,} cells x {n_genes:,} genes x {n_targets:,} targets)")
    print("=" * 70)
    
    stress_dir = Path("scratch/stress_test")
    stress_dir.mkdir(parents=True, exist_ok=True)
    stress_data_path = stress_dir / "stress_100k.h5ad"
    
    if not stress_data_path.is_file():
        print(f"Generating synthetic sparse dataset with {n_cells:,} cells...")
        rng = np.random.default_rng(999)
        
        # Realistically sparse count matrix (~7% nonzeros, Poisson distributed)
        # Construct CSR directly from random indices to avoid dense allocation
        target_names = [f"TARGET{i}" for i in range(n_targets)] + ["non-targeting"]
        cell_targets = []
        cell_classes = []
        for i in range(n_cells):
            if i < int(n_cells * 0.9):
                cell_targets.append(target_names[i % n_targets])
                cell_classes.append("targeting")
            else:
                cell_targets.append("non-targeting")
                cell_classes.append("non-targeting")
                
        batches = [f"B_{i % 4 + 1}" for i in range(n_cells)]
        
        # Generate sparse matrix with approx 120 non-zero entries per cell (~6% sparsity)
        nnz_per_row = 120
        total_nnz = n_cells * nnz_per_row
        
        indptr = np.arange(0, total_nnz + 1, nnz_per_row, dtype=np.int64)
        
        # Generate random unique column indices per row
        indices_list = []
        for _ in range(n_cells):
            cols = np.sort(rng.choice(n_genes, size=nnz_per_row, replace=False))
            indices_list.append(cols)
        indices = np.concatenate(indices_list).astype(np.int32)
        data = rng.poisson(2.0, size=total_nnz).astype(np.float32) + 1.0
        
        X_sparse = sp.csr_matrix((data, indices, indptr), shape=(n_cells, n_genes))
        
        gene_names = [f"TARGET{i}" if i < n_targets else f"GENE{i}" for i in range(n_genes)]
        
        adata = ad.AnnData(
            X=X_sparse.copy(),
            obs=pd.DataFrame({
                "gene_target": cell_targets,
                "perturbation_class": cell_classes,
                "lane_id": batches,
            }, index=[f"cell_{i}" for i in range(n_cells)]),
            var=pd.DataFrame(index=gene_names),
        )
        adata.layers["counts"] = X_sparse.copy()
        adata.write_h5ad(stress_data_path)
        print(f"Saved stress dataset to {stress_data_path} (size: {stress_data_path.stat().st_size / 1e6:.1f} MB)")
        del X_sparse, adata, indices, data, indptr
    
    out_stress = stress_dir / "results_stress_100k"
    if out_stress.exists():
        shutil.rmtree(out_stress)
        
    cfg_dict = {
        "run": {"name": "stress_100k", "outdir": str(out_stress), "seed": 42},
        "input": {"mode": "h5ad", "h5ad": str(stress_data_path), "guide_obs_column": "gene_target", "counts_layer": "counts"},
        "metadata": {"require_for_multilane": False},
        "qc": {"min_genes_per_cell": 10, "min_genes_final": 10, "max_pct_mt": 100},
        "scaling": {
            "mode": "large",
            "log_memory": True,
            "marker_max_cells": 50_000,
            "effect_gene_chunk": 256,
            "guide_chunk_size": 20_000,
            "collect_between_stages": True,
        },
        "cluster": {"n_top_genes": 500, "n_pcs": 20},
        "perturbation": {"min_cells_per_target": 10, "min_control_cells": 50},
        "enrichment": {"min_cells_per_target": 10, "min_cells_per_cluster": 10, "permutations": 100},
        "modules": {"enabled": True, "min_cells_per_perturbation": 10, "min_perturbations": 5, "draw_networks": False},
        "lochness": {"enabled": True, "n_neighbors": 30, "min_cells_per_target": 10},
        "ps_score": {"enabled": True, "compute_lda_umap": False, "min_cells_per_target": 10},
    }
    
    cfg = Config.from_dict(cfg_dict)
    
    print("\nStarting 100k cell stress test pipeline...")
    t0 = time.time()
    rss_start = get_rss_gb()
    print(f"Initial RSS: {rss_start:.2f} GB")
    
    result = run_pipeline(cfg)
    
    t_total = time.time() - t0
    rss_end = get_rss_gb()
    
    print("\n" + "=" * 70)
    print(f"STRESS TEST COMPLETED SUCCESSFULLY IN {t_total:.2f}s ({t_total/60:.2f} min)")
    print(f"Ending RSS: {rss_end:.2f} GB")
    print(f"Summary: {result.summary()}")
    print("=" * 70)
    
    return {
        "runtime": t_total,
        "rss_start": rss_start,
        "rss_end": rss_end,
    }


if __name__ == "__main__":
    smoke_res = run_smoke_tests()
    stress_res = run_medium_stress_test()
    print("\nAll tests completed successfully!")
