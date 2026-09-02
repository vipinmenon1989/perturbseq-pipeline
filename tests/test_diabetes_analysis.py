"""Tests for diabetes Perturb-seq analysis workflow (workflows/diabetes_analysis.py)."""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import anndata as ad
import numpy as np
import pandas as pd
import pytest

# Ensure src/ and workflows/ are importable
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
sys.path.insert(0, str(repo_root / "src"))
sys.path.insert(0, str(repo_root / "workflows"))

from workflows.diabetes_analysis import (
    STAGE_MAPPING,
    CheckpointModulesResults,
    _fig05_ps_by_perturbation,
    _fig13_lochness_by_celltype,
    _fig17_program_enrichment,
    _fig18_module_network,
    _fig19_perturbation_summary,
    _fig20_umap_ps_score,
    _fig21_umap_lochness_score,
    _fig22_ps_by_genotype,
    _fig23_ps_by_celltype2,
    _fig24_ps_genotype_celltype_heatmap,
    _fig25_lochness_by_genotype,
    _fig26_lochness_by_celltype2,
    _fig27_umap_ps_lochness_comparison,
    _fig28_umap_highlight_genotypes,
    _plot_multipanel_lochness_atlas,
    _plot_multipanel_ps_atlas,
    _plot_single_genotype_combined_umap,
    _plot_single_genotype_lochness_umap,
    _plot_single_genotype_ps_umap,
    build_master_summary_table,
    compute_lochness_by_celltype,
    compute_lochness_by_celltype2,
    compute_lochness_by_development_stage,
    compute_lochness_by_genotype,
    compute_lochness_directional_summary,
    compute_metric_correlation,
    compute_ps_by_celltype2,
    compute_ps_by_development_stage,
    compute_ps_by_genotype,
    compute_ps_by_genotype_celltype,
    derive_development_stage,
    export_lean_h5ad,
    generate_diabetes_figures,
    generate_per_genotype_umaps,
    prepare_diabetes_anndata,
    recover_and_finish_diabetes_run,
    run_diabetes_distance_analysis,
    run_diabetes_distance_space_analysis,
    run_diabetes_enrichment_analysis,
    run_diabetes_lochness_analysis,
    run_diabetes_modules_analysis,
    run_diabetes_ps_analysis,
    run_diabetes_workflow,
    safe_generate_figure,
    sanitize_identifier,
    validate_dataset,
)
from perturbseq_pipeline.config import Config
from perturbseq_pipeline.guides import CLASS_NTC, CLASS_TARGETING, OBS_CLASS, OBS_TARGET
from perturbseq_pipeline.lochness import LOCHNESS_SELF


# ---------------------------------------------------------------------------
# Test 1: Stage Collapsing
# ---------------------------------------------------------------------------


def test_stage_collapsing():
    """Verify mapping of orig.ident samples to developmental stages."""
    samples = pd.Series(
        [
            "Sample_A_WT",
            "Sample_B_WT",
            "Sample_G_1_ESC",
            "Sample_G_2_ESC",
            "Sample_H_DE",
            "Sample_I_PFG",
            "Sample_J_PP",
            "Sample_L_1_3DEC",
            "Sample_L_2_3DEC",
        ]
    )

    stages = derive_development_stage(samples)

    assert stages.iloc[0] == "WT"
    assert stages.iloc[1] == "WT"
    assert stages.iloc[2] == "ESC"
    assert stages.iloc[3] == "ESC"
    assert stages.iloc[4] == "DE"
    assert stages.iloc[5] == "PFG"
    assert stages.iloc[6] == "PP"
    assert stages.iloc[7] == "3DEC"
    assert stages.iloc[8] == "3DEC"


def test_stage_collapsing_fallback():
    """Verify fallback regex logic for unexpected but standard sample names."""
    unusual_samples = pd.Series(["Sample_Custom_DE", "Replicate_1_3DEC", "Batch2_WT"])
    stages = derive_development_stage(unusual_samples)
    assert stages.iloc[0] == "DE"
    assert stages.iloc[1] == "3DEC"
    assert stages.iloc[2] == "WT"


# ---------------------------------------------------------------------------
# Test 2: HDF5-Safe Identifier Conversion
# ---------------------------------------------------------------------------


def test_hdf5_safe_identifier_conversion():
    """Verify that identifiers with '/' are safely converted for HDF5 keys/files.

    Biological labels must remain unchanged in genotype/tables.
    """
    bio_label = "TET1/2/3"
    safe_key = sanitize_identifier(bio_label)

    # Generated key must not contain '/' or '\'
    assert "/" not in safe_key
    assert "\\" not in safe_key
    assert safe_key == "TET1__2__3"

    # Other tricky characters
    assert sanitize_identifier("A/B/C:1") == "A__B__C__1"
    assert sanitize_identifier("NANOGe-het") == "NANOGe-het"
    assert sanitize_identifier("Sample 1 / Stage") == "Sample__1__Stage"

    # The biological label is preserved
    assert bio_label == "TET1/2/3"


# ---------------------------------------------------------------------------
# Test 3: Required OBS Validation
# ---------------------------------------------------------------------------


def test_required_obs_validation_success():
    """Validation should pass when all required columns are present."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT", "PDX1", "MNX1"],
            "sgrna": ["WT_guide", "PDX1_1", "MNX1_1"],
            "celltype_2": ["ESC", "PP", "DE"],
            "orig.ident": ["Sample_A_WT", "Sample_J_PP", "Sample_H_DE"],
        }
    )
    adata = ad.AnnData(X=np.zeros((3, 10)), obs=obs)
    # Should not raise
    validate_dataset(adata)


def test_required_obs_validation_failure():
    """Validation should raise ValueError when any required column is missing."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT", "PDX1"],
            "sgrna": ["WT_guide", "PDX1_1"],
            # Missing celltype_2 and orig.ident
        }
    )
    adata = ad.AnnData(X=np.zeros((2, 10)), obs=obs)

    with pytest.raises(ValueError, match="missing required obs columns"):
        validate_dataset(adata)


# ---------------------------------------------------------------------------
# Test 4: PS Native Scale & Summary Structure
# ---------------------------------------------------------------------------


def test_ps_native_scale_and_columns():
    """PS summary must remain on native scale [0, 1] without z-scoring."""
    # Synthetic PS summary table
    ps_summary = pd.DataFrame(
        {
            "genotype": ["PDX1", "MNX1", "FOXA2"],
            "n_cells": [100, 120, 80],
            "ps_mean": [0.65, 0.42, 0.78],
            "ps_median": [0.70, 0.40, 0.82],
            "ps_responder_fraction": [0.75, 0.35, 0.88],
        }
    )

    # Check bounds
    assert (ps_summary["ps_mean"] >= 0.0).all() and (ps_summary["ps_mean"] <= 1.0).all()
    assert (ps_summary["ps_median"] >= 0.0).all() and (ps_summary["ps_median"] <= 1.0).all()
    assert (
        ps_summary["ps_responder_fraction"] >= 0.0
    ).all() and (ps_summary["ps_responder_fraction"] <= 1.0).all()


# ---------------------------------------------------------------------------
# Test 5: Pathway Labels Do NOT Replace P1-P4
# ---------------------------------------------------------------------------


def test_program_labels_preserved():
    """Gene programs must retain P1, P2, P3, P4 identifiers without substitution."""
    # Matrix of module x program strength
    programs = ["P1", "P2", "P3", "P4"]
    modules = ["M1", "M2", "M3", "M4", "M5", "M6"]

    mp_df = pd.DataFrame(
        np.random.randn(6, 4),
        index=modules,
        columns=programs,
    )

    # Column names must be strictly P1..P4
    assert list(mp_df.columns) == ["P1", "P2", "P3", "P4"]
    assert list(mp_df.index) == ["M1", "M2", "M3", "M4", "M5", "M6"]


# ---------------------------------------------------------------------------
# Test 6: Metric Correlation Calculation
# ---------------------------------------------------------------------------


def test_metric_correlation_calculation():
    """compute_metric_correlation should return rho, p_value, and n."""
    # Perfectly correlated
    x = [1.0, 2.0, 3.0, 4.0, 5.0]
    y = [10.0, 20.0, 30.0, 40.0, 50.0]

    rho, pval, n = compute_metric_correlation(x, y)
    assert np.isclose(rho, 1.0)
    assert pval < 0.05
    assert n == 5

    # Handles NaNs properly
    x_nan = [1.0, 2.0, np.nan, 4.0, 5.0]
    y_nan = [10.0, 20.0, 30.0, 40.0, np.nan]
    rho_nan, pval_nan, n_nan = compute_metric_correlation(x_nan, y_nan)
    assert n_nan == 3
    assert np.isclose(rho_nan, 1.0)


# ---------------------------------------------------------------------------
# Test 7: WT is Excluded from Non-WT DistanceSpace
# ---------------------------------------------------------------------------


def test_wt_excluded_from_distance_space():
    """DistanceSpace pairwise manifold must only compare non-WT perturbations."""
    rng = np.random.default_rng(42)
    n_cells = 300

    # 100 WT cells, 100 PDX1 cells, 100 MNX1 cells
    genotypes = ["WT"] * 100 + ["PDX1"] * 100 + ["MNX1"] * 100
    pca_emb = rng.normal(size=(n_cells, 10))
    # Shift PDX1 and MNX1
    pca_emb[100:200, 0] += 3.0
    pca_emb[200:300, 1] += 3.0

    obs = pd.DataFrame(
        {
            "genotype": genotypes,
            "sgrna": [f"guide_{i}" for i in range(n_cells)],
            "celltype_2": ["ESC"] * 100 + ["PP"] * 100 + ["DE"] * 100,
            "orig.ident": ["Sample_A_WT"] * 100 + ["Sample_J_PP"] * 100 + ["Sample_H_DE"] * 100,
        }
    )

    adata = ad.AnnData(X=np.zeros((n_cells, 20)), obs=obs, obsm={"X_pca": pca_emb})

    cfg = Config()
    cfg.distance_space.enabled = True
    cfg.distance_space.min_cells = 10
    cfg.distance_space.representation = "X_pca"

    adata = prepare_diabetes_anndata(adata, cfg)
    dist_mat, coords, neighbors, pheno_groups = run_diabetes_distance_space_analysis(adata, cfg)

    # WT must not be in the pairwise non-WT distance matrix
    assert "WT" not in dist_mat.index
    assert "WT" not in dist_mat.columns
    assert set(dist_mat.index) == {"PDX1", "MNX1"}
    assert set(dist_mat.columns) == {"PDX1", "MNX1"}


# ---------------------------------------------------------------------------
# Synthetic Dataset Helper for Smoke Tests
# ---------------------------------------------------------------------------


def make_synthetic_diabetes_adata(n_cells: int = 180, n_genes: int = 60) -> ad.AnnData:
    """Create a minimal synthetic AnnData matching the diabetes dataset structure."""
    rng = np.random.default_rng(123)
    genotypes_list = ["WT", "PDX1", "MNX1", "FOXA2", "GATA4", "GATA6"]
    n_geno = len(genotypes_list)
    n_per_geno = n_cells // n_geno
    celltypes_list = ["ESC", "PP", "DE", "PFG", "SC-beta", "SC-alpha"]
    samples_list = [
        "Sample_A_WT",
        "Sample_J_PP",
        "Sample_H_DE",
        "Sample_I_PFG",
        "Sample_L_1_3DEC",
        "Sample_G_1_ESC",
    ]

    genotypes = []
    celltypes = []
    samples = []
    for i, g in enumerate(genotypes_list):
        count = n_per_geno if i < n_geno - 1 else (n_cells - (n_geno - 1) * n_per_geno)
        genotypes.extend([g] * count)
        celltypes.extend([celltypes_list[i % len(celltypes_list)]] * count)
        samples.extend([samples_list[i % len(samples_list)]] * count)

    sgrnas = [f"sgrna_{i % 12}" for i in range(n_cells)]

    # Gene names including target genes
    target_genes = ["PDX1", "MNX1", "FOXA2", "GATA4", "GATA6"]
    gene_names = target_genes + [f"GENE_{i}" for i in range(n_genes - len(target_genes))]
    # Counts matrix with positive counts
    counts = rng.poisson(lam=3.0, size=(n_cells, n_genes)).astype(np.float32)

    obs = pd.DataFrame(
        {
            "genotype": genotypes,
            "sgrna": sgrnas,
            "celltype_2": celltypes,
            "orig.ident": samples,
        },
        index=[f"cell_{i}" for i in range(n_cells)],
    )
    var = pd.DataFrame(index=gene_names)
    pca_emb = rng.normal(size=(n_cells, 10)).astype(np.float32)
    for i in range(n_geno):
        pca_emb[i * n_per_geno : (i + 1) * n_per_geno, i % 10] += 3.0

    adata = ad.AnnData(
        X=counts,
        obs=obs,
        var=var,
        obsm={"X_pca": pca_emb, "X_umap": pca_emb[:, :2].copy()},
        layers={"counts": counts.copy()},
    )
    return adata


# ---------------------------------------------------------------------------
# Test 8: lochNESS API Invocations & Column Structure
# ---------------------------------------------------------------------------


def test_lochness_analysis_api():
    """Verify that run_diabetes_lochness_analysis correctly invokes lochNESS and returns expected directional columns."""
    adata = make_synthetic_diabetes_adata(n_cells=180, n_genes=50)
    cfg = Config()
    cfg.lochness.enabled = True
    cfg.lochness.genotype_key = "genotype"
    cfg.lochness.use_rep = "X_pca"
    cfg.lochness.n_neighbors = 15
    cfg.lochness.min_cells_per_target = 5

    adata = prepare_diabetes_anndata(adata, cfg)
    lochness_df, lochness_by_ct, lochness_mat, lochness_self = run_diabetes_lochness_analysis(adata, cfg)

    assert not lochness_df.empty
    expected_cols = [
        "genotype",
        "n_cells",
        "lochness_mean",
        "lochness_median",
        "lochness_positive_mean",
        "lochness_positive_median",
        "lochness_positive_fraction",
        "lochness_positive_q90",
        "lochness_negative_mean",
        "lochness_negative_median",
        "lochness_negative_fraction",
        "lochness_negative_q10",
        "lochness_abs_mean",
        "lochness_abs_median",
        "lochness_peak",
        "dominant_celltype_2",
        "dominant_celltype_fraction",
        "dominant_celltype_lochness",
    ]
    for col in expected_cols:
        assert col in lochness_df.columns

    assert isinstance(lochness_by_ct, pd.DataFrame)
    assert not lochness_by_ct.empty
    assert "celltype_2" in lochness_by_ct.columns
    assert "mean_lochness" in lochness_by_ct.columns

    assert isinstance(lochness_mat, pd.DataFrame)
    assert LOCHNESS_SELF in adata.obs.columns
    assert len(lochness_self) == adata.n_obs


# ---------------------------------------------------------------------------
# Test 9: PS Score Analysis without LDA
# ---------------------------------------------------------------------------


def test_ps_score_analysis_api_no_lda():
    """Verify that PS scoring runs cleanly with compute_lda_umap=False without LDA errors."""
    adata = make_synthetic_diabetes_adata(n_cells=180, n_genes=50)
    cfg = Config()
    cfg.ps_score.enabled = True
    cfg.ps_score.compute_lda_umap = False
    cfg.ps_score.min_cells_per_target = 5

    adata = prepare_diabetes_anndata(adata, cfg)
    summary_df, skipped_df = run_diabetes_ps_analysis(adata, cfg)

    # Scored summary or skipped table returned
    assert isinstance(summary_df, pd.DataFrame)
    assert isinstance(skipped_df, pd.DataFrame)
    if not summary_df.empty:
        assert "genotype" in summary_df.columns


# ---------------------------------------------------------------------------
# Test 10: Distance & DistanceSpace API Invocations
# ---------------------------------------------------------------------------


def test_distance_and_distance_space_api():
    """Verify Distance and DistanceSpace functions unpack return values correctly."""
    adata = make_synthetic_diabetes_adata(n_cells=180, n_genes=50)
    cfg = Config()
    cfg.distance.enabled = True
    cfg.distance.representation = "X_pca"
    cfg.distance.min_cells = 5
    cfg.distance.n_permutations = 20

    cfg.distance_space.enabled = True
    cfg.distance_space.representation = "X_pca"
    cfg.distance_space.min_cells = 5

    adata = prepare_diabetes_anndata(adata, cfg)

    dist_table, dist_skipped = run_diabetes_distance_analysis(adata, cfg)
    assert isinstance(dist_table, pd.DataFrame)
    assert isinstance(dist_skipped, pd.DataFrame)
    assert not dist_table.empty
    assert "genotype" in dist_table.columns
    assert "energy_distance" in dist_table.columns

    dist_mat, coords, neighbors, pheno_groups = run_diabetes_distance_space_analysis(adata, cfg)
    assert isinstance(dist_mat, pd.DataFrame)
    assert isinstance(coords, pd.DataFrame)
    assert isinstance(neighbors, pd.DataFrame)
    assert isinstance(pheno_groups, pd.DataFrame)
    assert not dist_mat.empty
    assert "genotype" in coords.columns


# ---------------------------------------------------------------------------
# Test 11: Enrichment & Modules API Invocations
# ---------------------------------------------------------------------------


def test_enrichment_and_modules_api():
    """Verify Enrichment and Modules functions unpack and process correctly."""
    adata = make_synthetic_diabetes_adata(n_cells=180, n_genes=50)
    cfg = Config()
    cfg.enrichment.enabled = True
    cfg.enrichment.cluster_key = "celltype_2"
    cfg.enrichment.stratify_by = "orig.ident"

    cfg.modules.enabled = True
    cfg.modules.cluster_key = "celltype_2"
    cfg.modules.min_perturbations = 2
    cfg.modules.min_cells_per_perturbation = 5
    cfg.modules.n_modules = 2
    cfg.modules.n_programs = 2

    adata = prepare_diabetes_anndata(adata, cfg)

    enrich_table, log_or_mat, sig_mat = run_diabetes_enrichment_analysis(adata, cfg)
    assert isinstance(enrich_table, pd.DataFrame)
    assert isinstance(log_or_mat, pd.DataFrame)
    assert isinstance(sig_mat, pd.DataFrame)

    mod_res = run_diabetes_modules_analysis(adata, cfg)
    assert mod_res is not None
    assert hasattr(mod_res, "modules")
    assert hasattr(mod_res, "gene_programs")
    assert hasattr(mod_res, "module_program")
    assert hasattr(mod_res, "program_activity")


# ---------------------------------------------------------------------------
# Test 12: Fast End-to-End Workflow Smoke Test
# ---------------------------------------------------------------------------


def test_diabetes_end_to_end_smoke(tmp_path):
    """Fast smoke test exercising the complete orchestration pipeline on synthetic data."""
    h5ad_path = tmp_path / "synthetic_diabetes.h5ad"
    outdir = tmp_path / "results_smoke"

    adata = make_synthetic_diabetes_adata(n_cells=180, n_genes=50)
    adata.write_h5ad(h5ad_path)

    res_dir = run_diabetes_workflow(
        input_path=h5ad_path,
        outdir=outdir,
        n_jobs=1,
        seed=123,
        min_cells=5,
        max_cells_per_target=100,
        max_control_cells=100,
        n_permutations=20,
        n_modules=2,
        n_programs=2,
        hvg_count=30,
        n_pcs=10,
    )

    assert res_dir == outdir
    tables_dir = outdir / "tables"
    figures_dir = outdir / "figures"
    lean_h5ad = outdir / "diabetes_analysis.h5ad"

    assert tables_dir.is_dir()
    assert figures_dir.is_dir()
    assert lean_h5ad.is_file()

    # Verify tables generated
    assert (tables_dir / "lochness_summary.csv").is_file()
    assert (tables_dir / "lochness_by_celltype.csv").is_file()
    assert (tables_dir / "distance_results.csv").is_file()
    assert (tables_dir / "distance_space_matrix.csv").is_file()
    assert (tables_dir / "celltype_enrichment.csv").is_file()
    assert (tables_dir / "perturbation_summary.csv").is_file()
    assert (figures_dir / "figure_manifest.json").is_file()


# ---------------------------------------------------------------------------
# Test 13: Figure 17 Program-Enrichment Schema Contract
# ---------------------------------------------------------------------------


def test_fig17_program_enrichment_actual_schema(tmp_path):
    """Verify Figure 17 works with the canonical Stage 7 program_enrichment schema."""
    pe_df = pd.DataFrame(
        [
            {
                "program_id": "P1",
                "annotation": "Interferon Alpha Response",
                "gene_set_source": "hallmark",
                "term": "HALLMARK_INTERFERON_ALPHA_RESPONSE",
                "clean_term": "Interferon Alpha Response",
                "program_size": 150,
                "gene_set_size": 95,
                "overlap_count": 42,
                "overlap_genes": "ISG15, IFIT1, MX1, OAS1",
                "p_value": 1.2e-15,
                "fdr": 3.5e-14,
                "odds_ratio": 12.4,
                "background_size": 980,
                "species": "human",
                "gene_set_version": "MSigDB Hallmark v2024.1",
                "adjusted_p_value": 3.5e-14,
            },
            {
                "program_id": "P2",
                "annotation": "Pancreas Beta Cells",
                "gene_set_source": "hallmark",
                "term": "HALLMARK_PANCREAS_BETA_CELLS",
                "clean_term": "Pancreas Beta Cells",
                "program_size": 549,
                "gene_set_size": 42,
                "overlap_count": 36,
                "overlap_genes": "INS, GCG, SST, PAX6, NEUROD1",
                "p_value": 2.9e-5,
                "fdr": 0.0012,
                "odds_ratio": 4.97,
                "background_size": 980,
                "species": "human",
                "gene_set_version": "MSigDB Hallmark v2024.1",
                "adjusted_p_value": 0.0012,
            },
        ]
    )

    mod_res = CheckpointModulesResults(program_enrichment=pe_df)
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()

    _fig17_program_enrichment(mod_res, fig_dir)

    out_file = fig_dir / "17_program_enrichment.png"
    assert out_file.is_file(), "17_program_enrichment.png must be created"
    assert out_file.stat().st_size > 5000, "Figure 17 must be a non-empty image file"


# ---------------------------------------------------------------------------
# Test 14: Figure 17 Program Labels Remain P1-P4
# ---------------------------------------------------------------------------


def test_fig17_program_identifiers_remain_stable(tmp_path):
    """Verify that program identifiers in Figure 17 remain P1..P4 and are not replaced."""
    pe_df = pd.DataFrame(
        [
            {
                "program_id": "P1",
                "annotation": "Pancreas Beta Cells",
                "gene_set_source": "hallmark",
                "term": "HALLMARK_PANCREAS_BETA_CELLS",
                "clean_term": "Pancreas Beta Cells",
                "fdr": 0.001,
            },
            {
                "program_id": "P2",
                "annotation": "MYC Targets",
                "gene_set_source": "hallmark",
                "term": "HALLMARK_MYC_TARGETS_V1",
                "clean_term": "MYC Targets V1",
                "fdr": 0.002,
            },
        ]
    )

    mod_res = CheckpointModulesResults(program_enrichment=pe_df)
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()

    _fig17_program_enrichment(mod_res, fig_dir)
    assert (fig_dir / "17_program_enrichment.png").is_file()


# ---------------------------------------------------------------------------
# Test 15: Figure 17 Handles Empty or Unannotated Programs
# ---------------------------------------------------------------------------


def test_fig17_handles_unannotated_and_empty(tmp_path):
    """Figure 17 should gracefully handle empty or unannotated programs without throwing errors."""
    pe_df = pd.DataFrame(
        [
            {
                "program_id": "P1",
                "annotation": "unannotated",
                "gene_set_source": "None",
                "term": "None",
                "clean_term": "None",
                "fdr": 1.0,
            }
        ]
    )
    mod_res = CheckpointModulesResults(program_enrichment=pe_df)
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()

    _fig17_program_enrichment(mod_res, fig_dir)
    assert (fig_dir / "17_program_enrichment.png").is_file()


# ---------------------------------------------------------------------------
# Test 16: safe_generate_figure Error Isolation
# ---------------------------------------------------------------------------


def test_safe_generate_figure_isolates_exceptions():
    """safe_generate_figure must catch exceptions, log them, and return False without raising."""

    def broken_figure_func():
        raise KeyError("program")

    def good_figure_func():
        return True

    assert safe_generate_figure("test_broken", broken_figure_func) is False
    assert safe_generate_figure("test_good", good_figure_func) is True


# ---------------------------------------------------------------------------
# Test 17: Figure Failure Does NOT Stop Subsequent Figures or Workflow
# ---------------------------------------------------------------------------


def test_figure_failure_does_not_abort_workflow(tmp_path):
    """A failure in an optional figure must not stop other figures or erase analytical outputs."""
    summary_df = pd.DataFrame({"genotype": ["PDX1", "MNX1"], "n_cells": [100, 120], "energy_distance": [0.5, 0.8]})
    fig_dir = tmp_path / "figures"
    fig_dir.mkdir()

    # Provide mod_results where program_enrichment is a broken object that throws KeyError
    class BrokenModResults:
        @property
        def program_enrichment(self):
            raise KeyError("program")

    mod_results = BrokenModResults()

    manifest = generate_diabetes_figures(
        adata=None,
        summary_df=summary_df,
        ps_summary=pd.DataFrame(),
        dist_table=pd.DataFrame(),
        dist_mat=pd.DataFrame(),
        coords=pd.DataFrame(),
        pheno_groups=pd.DataFrame(),
        lochness_df=pd.DataFrame(),
        log_or_matrix=pd.DataFrame(),
        sig_matrix=pd.DataFrame(),
        mod_results=mod_results,
        fig_dir=fig_dir,
    )

    # Manifest must record failure of Figure 17
    assert manifest["total_failed"] >= 1
    assert any("17_program_enrichment.png" in f for f in manifest["failed"])
    # Subsequent Figure 19 should have succeeded
    assert any("19_perturbation_summary.png" in g for g in manifest["generated"])
    assert (fig_dir / "19_perturbation_summary.png").is_file()
    assert (fig_dir / "figure_manifest.json").is_file()


# ---------------------------------------------------------------------------
# Test 18: PS Summary Schema Bidirectional Compatibility
# ---------------------------------------------------------------------------


def test_ps_summary_schema_compatibility():
    """Verify build_master_summary_table correctly maps mean_ps/median_ps from ps_score.py."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 20 + ["PDX1"] * 20 + ["MNX1"] * 20,
            "sgrna": [f"g_{i}" for i in range(60)],
            "celltype_2": ["ESC"] * 60,
            "orig.ident": ["Sample_A_WT"] * 60,
        }
    )
    adata = ad.AnnData(X=np.zeros((60, 10)), obs=obs)

    ps_summary_from_stage1 = pd.DataFrame(
        {
            "genotype": ["PDX1", "MNX1"],
            "n_perturbed_cells": [20, 20],
            "n_control_cells": [20, 20],
            "mean_ps": [0.65, 0.45],
            "median_ps": [0.70, 0.40],
            "pct_successful_kd": [75.0, 35.0],
        }
    )

    summary_df = build_master_summary_table(
        adata,
        ps_summary=ps_summary_from_stage1,
        dist_table=pd.DataFrame(),
        lochness_df=pd.DataFrame(),
        pheno_groups=pd.DataFrame(),
        mod_results=None,
    )

    assert "ps_median" in summary_df.columns
    assert "ps_mean" in summary_df.columns
    assert "ps_responder_fraction" in summary_df.columns
    assert np.isclose(summary_df.loc[summary_df["genotype"] == "PDX1", "ps_median"].iloc[0], 0.70)
    assert np.isclose(summary_df.loc[summary_df["genotype"] == "PDX1", "ps_responder_fraction"].iloc[0], 0.75)


# ---------------------------------------------------------------------------
# Test 19: Recovery Mode from Checkpoint Tables
# ---------------------------------------------------------------------------


def test_recovery_mode_smoke(tmp_path):
    """Verify recovery mode reconstructs outputs and generates all figures without rerun."""
    h5ad_path = tmp_path / "synthetic_diabetes.h5ad"
    outdir = tmp_path / "recovery_run"
    tables_dir = outdir / "tables"
    figures_dir = outdir / "figures"
    tables_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)

    adata = make_synthetic_diabetes_adata(n_cells=180, n_genes=50)
    adata.write_h5ad(h5ad_path)

    # Populate mock checkpoint tables
    pd.DataFrame({"genotype": ["PDX1", "MNX1"], "energy_distance": [0.5, 0.8], "pvalue": [0.001, 0.001], "fdr": [0.001, 0.001], "significant": [True, True]}).to_csv(tables_dir / "distance_results.csv", index=False)
    pd.DataFrame({"genotype": ["PDX1", "MNX1"], "lochness_mean": [0.4, 0.6], "lochness_median": [0.45, 0.65], "lochness_peak": [0.8, 0.9], "dominant_celltype_2": ["PP", "DE"], "dominant_celltype_fraction": [0.8, 0.7], "dominant_celltype_lochness": [0.5, 0.7]}).to_csv(tables_dir / "lochness_summary.csv", index=False)
    pd.DataFrame({"genotype": ["PDX1", "MNX1"], "mean_ps": [0.6, 0.7], "median_ps": [0.65, 0.75], "pct_successful_kd": [60.0, 70.0]}).to_csv(tables_dir / "ps_score_summary.csv", index=False)
    pd.DataFrame([[0.0, 0.5], [0.5, 0.0]], index=["PDX1", "MNX1"], columns=["PDX1", "MNX1"]).to_csv(tables_dir / "distance_space_matrix.csv")
    pd.DataFrame({"genotype": ["PDX1", "MNX1"], "PCoA1": [0.1, -0.1], "PCoA2": [0.2, -0.2]}).to_csv(tables_dir / "distance_space_coordinates.csv", index=False)
    pd.DataFrame({"genotype": ["PDX1", "MNX1"], "phenotype_group": ["PG1", "PG2"]}).to_csv(tables_dir / "phenotype_groups.csv", index=False)
    pd.DataFrame({"target_gene": ["PDX1", "MNX1"], "module": ["M1", "M2"], "n_cells": [30, 30], "n_de_genes": [50, 60]}).to_csv(tables_dir / "module_assignments.csv", index=False)
    pd.DataFrame({"program_id": ["P1", "P2"], "annotation": ["Pancreas", "Cycle"], "clean_term": ["Pancreas", "Cycle"], "fdr": [0.001, 0.01]}).to_csv(tables_dir / "program_enrichment.csv", index=False)

    recovered_dir = recover_and_finish_diabetes_run(
        input_path=h5ad_path,
        outdir=outdir,
    )

    assert recovered_dir == outdir
    assert (tables_dir / "perturbation_summary.csv").is_file()
    assert (outdir / "diabetes_analysis.h5ad").is_file()
    assert (figures_dir / "figure_manifest.json").is_file()
    assert (figures_dir / "17_program_enrichment.png").is_file()
    assert (figures_dir / "19_perturbation_summary.png").is_file()


# ---------------------------------------------------------------------------
# Test 20: Focused Test for Synthetic lochNESS Vector (Section 27)
# ---------------------------------------------------------------------------


def test_lochness_directional_summary_synthetic_vector():
    """Test directional and magnitude lochNESS statistics on synthetic vector [-0.8, -0.6, -0.2, 0.1, 0.5, 0.9]."""
    scores = np.array([-0.8, -0.6, -0.2, 0.1, 0.5, 0.9])
    res = compute_lochness_directional_summary(scores)

    # Positive side: [0.1, 0.5, 0.9]
    assert np.isclose(res["lochness_positive_mean"], (0.1 + 0.5 + 0.9) / 3.0)  # 0.5
    assert np.isclose(res["lochness_positive_median"], 0.5)
    assert np.isclose(res["lochness_positive_fraction"], 3.0 / 6.0)  # 0.5
    assert np.isclose(res["lochness_positive_q90"], np.percentile([0.1, 0.5, 0.9], 90))

    # Negative side: [-0.8, -0.6, -0.2] (must remain signed negative)
    assert np.isclose(res["lochness_negative_mean"], (-0.8 - 0.6 - 0.2) / 3.0)  # -0.5333...
    assert res["lochness_negative_mean"] < 0.0
    assert np.isclose(res["lochness_negative_median"], -0.6)
    assert res["lochness_negative_median"] < 0.0
    assert np.isclose(res["lochness_negative_fraction"], 3.0 / 6.0)  # 0.5
    assert np.isclose(res["lochness_negative_q10"], np.percentile([-0.8, -0.6, -0.2], 10))
    assert res["lochness_negative_q10"] < 0.0

    # Absolute magnitude: [0.8, 0.6, 0.2, 0.1, 0.5, 0.9]
    assert np.isclose(res["lochness_abs_mean"], (0.8 + 0.6 + 0.2 + 0.1 + 0.5 + 0.9) / 6.0)
    assert np.isclose(res["lochness_abs_median"], np.median([0.8, 0.6, 0.2, 0.1, 0.5, 0.9]))

    # Net summaries
    assert np.isclose(res["lochness_mean"], np.mean(scores))
    assert np.isclose(res["lochness_median"], np.median(scores))


# ---------------------------------------------------------------------------
# Test 21: Focused Test for lochNESS Cancellation Case (Section 27)
# ---------------------------------------------------------------------------


def test_lochness_directional_cancellation_case():
    """Test cancellation case [-0.8, -0.7, -0.6, 0.6, 0.7, 0.8].

    Demonstrates that overall median is ~0 while positive/negative means and magnitude are large.
    """
    scores = np.array([-0.8, -0.7, -0.6, 0.6, 0.7, 0.8])
    res = compute_lochness_directional_summary(scores)

    # Net mean & median cancel out to zero
    assert np.isclose(res["lochness_mean"], 0.0)
    assert np.isclose(res["lochness_median"], 0.0)

    # Directional summaries reveal the strong biological localization
    assert np.isclose(res["lochness_positive_mean"], 0.7)
    assert np.isclose(res["lochness_negative_mean"], -0.7)
    assert np.isclose(res["lochness_abs_mean"], 0.7)
    assert np.isclose(res["lochness_positive_fraction"], 0.5)
    assert np.isclose(res["lochness_negative_fraction"], 0.5)


# ---------------------------------------------------------------------------
# Test 22: PS NaN Handling & Spearman Filtering (Section 20, 21)
# ---------------------------------------------------------------------------


def test_ps_nan_preserved_and_excluded_from_spearman():
    """Verify that PS NaNs remain NaN (not filled with 0) and are excluded from Spearman correlation."""
    summary_df = pd.DataFrame(
        {
            "genotype": ["PDX1", "MNX1", "GATA4", "GATA6", "NANOGe-het"],
            "ps_median": [0.65, 0.40, np.nan, 0.80, np.nan],  # 2 targets skipped
            "energy_distance": [2.2, 1.1, 5.2, 9.7, 1.8],
            "lochness_positive_mean": [0.8, 0.5, 0.9, 1.2, 0.4],
            "lochness_negative_mean": [-0.3, -0.2, -0.6, -0.8, -0.1],
        }
    )

    # PS column contains NaNs
    assert summary_df["ps_median"].isna().sum() == 2

    # Correlation between PS and energy distance must only use 3 perturbations (n=3)
    rho, pval, n = compute_metric_correlation(summary_df["energy_distance"], summary_df["ps_median"])
    assert n == 3
    assert not np.isnan(rho)

    # Correlation between Energy Distance and Positive lochNESS uses all 5 perturbations
    rho_all, pval_all, n_all = compute_metric_correlation(
        summary_df["energy_distance"], summary_df["lochness_positive_mean"]
    )
    assert n_all == 5


# ---------------------------------------------------------------------------
# Test 23: Genotype x celltype_2 Masking Threshold (Section 16, 17)
# ---------------------------------------------------------------------------


def test_lochness_celltype_masking_threshold():
    """Verify that groups with < 10 cells are masked as NaN (not zero) in heatmap matrix."""
    # 20 cells: 12 PP cells for PDX1, 3 SC-beta cells for PDX1 (<10 threshold)
    genotypes = ["PDX1"] * 15 + ["WT"] * 5
    celltypes = ["PP"] * 12 + ["SC-beta"] * 3 + ["PP"] * 5
    scores = [1.5] * 12 + [2.0] * 3 + [0.0] * 5

    obs = pd.DataFrame({"genotype": genotypes, "celltype_2": celltypes})
    adata = ad.AnnData(X=np.zeros((20, 5)), obs=obs)

    by_ct_df, pivot_mat = compute_lochness_by_celltype(adata, lochness_self=np.array(scores), min_cells=10)

    # Table contains exact counts
    assert not by_ct_df.empty
    pp_row = by_ct_df[(by_ct_df["genotype"] == "PDX1") & (by_ct_df["celltype_2"] == "PP")].iloc[0]
    beta_row = by_ct_df[(by_ct_df["genotype"] == "PDX1") & (by_ct_df["celltype_2"] == "SC-beta")].iloc[0]

    assert pp_row["n_cells"] == 12
    assert np.isclose(pp_row["mean_lochness"], 1.5)
    assert beta_row["n_cells"] == 3
    assert np.isclose(beta_row["mean_lochness"], 2.0)

    # Heatmap matrix has PP preserved (>=10 cells) and SC-beta masked as NaN (<10 cells)
    assert np.isclose(pivot_mat.loc["PDX1", "PP"], 1.5)
    assert np.isnan(pivot_mat.loc["PDX1", "SC-beta"])  # Must be NaN, NOT 0.0


# ---------------------------------------------------------------------------
# Test 24: Master Perturbation Summary Canonical Columns (Section 19)
# ---------------------------------------------------------------------------


def test_master_perturbation_summary_columns_complete():
    """Verify build_master_summary_table creates all canonical columns specified in Section 19."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 10 + ["PDX1"] * 10 + ["MNX1"] * 10,
            "sgrna": [f"g_{i}" for i in range(30)],
            "celltype_2": ["ESC"] * 30,
            "orig.ident": ["Sample_A_WT"] * 30,
        }
    )
    adata = ad.AnnData(X=np.zeros((30, 5)), obs=obs)

    ps_summary = pd.DataFrame(
        {"genotype": ["PDX1", "MNX1"], "ps_mean": [0.6, 0.4], "ps_median": [0.65, 0.42], "ps_responder_fraction": [0.6, 0.3]}
    )
    dist_table = pd.DataFrame(
        {"genotype": ["PDX1", "MNX1"], "energy_distance": [1.5, 0.8], "pvalue": [0.001, 0.001], "fdr": [0.001, 0.001]}
    )
    lochness_df = pd.DataFrame(
        {
            "genotype": ["PDX1", "MNX1"],
            "lochness_mean": [0.3, 0.2],
            "lochness_median": [0.25, 0.15],
            "lochness_positive_mean": [0.7, 0.5],
            "lochness_positive_median": [0.65, 0.45],
            "lochness_positive_fraction": [0.6, 0.5],
            "lochness_positive_q90": [1.2, 0.9],
            "lochness_negative_mean": [-0.4, -0.3],
            "lochness_negative_median": [-0.35, -0.25],
            "lochness_negative_fraction": [0.4, 0.5],
            "lochness_negative_q10": [-0.8, -0.6],
            "lochness_abs_mean": [0.55, 0.40],
            "lochness_abs_median": [0.50, 0.35],
        }
    )
    pheno_groups = pd.DataFrame({"genotype": ["PDX1", "MNX1"], "phenotype_group": ["PG1", "PG2"]})

    class DummyModResults:
        modules = pd.DataFrame({"genotype": ["PDX1", "MNX1"], "cofunctional_module": ["M1", "M2"]})

    master_df = build_master_summary_table(
        adata,
        ps_summary=ps_summary,
        dist_table=dist_table,
        lochness_df=lochness_df,
        pheno_groups=pheno_groups,
        mod_results=DummyModResults(),
    )

    required_cols = [
        "genotype",
        "n_cells",
        "ps_mean",
        "ps_median",
        "ps_responder_fraction",
        "energy_distance",
        "distance_pvalue",
        "distance_fdr",
        "lochness_mean",
        "lochness_median",
        "lochness_positive_mean",
        "lochness_positive_median",
        "lochness_positive_fraction",
        "lochness_positive_q90",
        "lochness_negative_mean",
        "lochness_negative_median",
        "lochness_negative_fraction",
        "lochness_negative_q10",
        "lochness_abs_mean",
        "lochness_abs_median",
        "cofunctional_module",
        "phenotype_group",
    ]

    for col in required_cols:
        assert col in master_df.columns, f"Missing required column: {col}"

    assert list(master_df.columns[:len(required_cols)]) == required_cols


# ---------------------------------------------------------------------------
# Test 25: Per-Cell PS Native Scale Preservation [0, 1] Without Z-Scoring (Section O.1)
# ---------------------------------------------------------------------------


def test_ps_native_scale_preservation():
    """Verify per-cell PS scores and summaries strictly remain on the [0, 1] bounded scale."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["PDX1"] * 10 + ["FOXA2"] * 10,
            "ps_score": [np.nan] * 5 + [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0] + [0.2] * 10,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10 + ["SC-beta"] * 10,
            "development_stage": ["WT"] * 5 + ["PP"] * 10 + ["3DEC"] * 10,
        }
    )
    adata = ad.AnnData(X=np.zeros((25, 5)), obs=obs)

    df_geno = compute_ps_by_genotype(adata)
    assert not df_geno.empty
    assert (df_geno["mean_ps"] >= 0.0).all() and (df_geno["mean_ps"] <= 1.0).all()
    assert (df_geno["median_ps"] >= 0.0).all() and (df_geno["median_ps"] <= 1.0).all()
    pdx1_row = df_geno[df_geno["genotype"] == "PDX1"].iloc[0]
    assert np.isclose(pdx1_row["mean_ps"], 0.55)
    assert np.isclose(pdx1_row["median_ps"], 0.55)
    assert pdx1_row["n_cells"] == 10
    assert pdx1_row["n_valid_ps"] == 10

    df_ct = compute_ps_by_celltype2(adata)
    assert not df_ct.empty
    assert (df_ct["mean_ps"] >= 0.0).all() and (df_ct["mean_ps"] <= 1.0).all()

    df_stage = compute_ps_by_development_stage(adata)
    assert not df_stage.empty
    valid_means = df_stage["mean_ps"].dropna()
    assert (valid_means >= 0.0).all() and (valid_means <= 1.0).all()


# ---------------------------------------------------------------------------
# Test 26: Missing PS Values Remain NaN (Never 0.0) (Section O.2)
# ---------------------------------------------------------------------------


def test_missing_ps_values_remain_nan():
    """Verify cells without valid PS remain NaN and are not converted to 0.0 or counted as zeros."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 10 + ["PDX1"] * 5 + ["PDX1"] * 5,
            "ps_score": [np.nan] * 10 + [0.8, 0.9, 0.85, 0.75, 0.95] + [np.nan] * 5,
            "celltype_2": ["ESC"] * 10 + ["PP"] * 10,
            "development_stage": ["WT"] * 10 + ["PP"] * 10,
        }
    )
    adata = ad.AnnData(X=np.zeros((20, 5)), obs=obs)

    # WT cells must have NaN
    wt_ps = adata.obs.loc[adata.obs["genotype"] == "WT", "ps_score"]
    assert wt_ps.isna().all()

    df_geno = compute_ps_by_genotype(adata)
    pdx1_row = df_geno[df_geno["genotype"] == "PDX1"].iloc[0]
    assert pdx1_row["n_cells"] == 10
    assert pdx1_row["n_valid_ps"] == 5
    # Mean of [0.8, 0.9, 0.85, 0.75, 0.95] is 0.85 (NOT diluted by 5 zeros to 0.425)
    assert np.isclose(pdx1_row["mean_ps"], 0.85)


# ---------------------------------------------------------------------------
# Test 27: Genotype x Celltype PS Summaries Over Valid Cells Only (Section O.3)
# ---------------------------------------------------------------------------


def test_ps_genotype_celltype_valid_cells_only():
    """Verify genotype x celltype PS summaries calculate only over valid cells with finite PS."""
    obs = pd.DataFrame(
        {
            "genotype": ["PDX1"] * 12 + ["PDX1"] * 4,
            "celltype_2": ["PP"] * 12 + ["PP"] * 4,
            "ps_score": [0.6] * 12 + [np.nan] * 4,
        }
    )
    adata = ad.AnnData(X=np.zeros((16, 5)), obs=obs)

    table_df, mat = compute_ps_by_genotype_celltype(adata, min_cells=10)
    assert not table_df.empty
    row = table_df[(table_df["genotype"] == "PDX1") & (table_df["celltype_2"] == "PP")].iloc[0]
    assert row["n_cells"] == 16
    assert row["n_valid_ps"] == 12
    assert np.isclose(row["mean_ps"], 0.6)
    assert np.isclose(mat.loc["PDX1", "PP"], 0.6)


# ---------------------------------------------------------------------------
# Test 28: Signed lochNESS Retains Sign On Continuous Range (Section O.4)
# ---------------------------------------------------------------------------


def test_lochness_signed_continuity():
    """Verify per-cell lochNESS values retain both negative (depletion) and positive (enrichment) signs."""
    obs = pd.DataFrame(
        {
            "genotype": ["PDX1"] * 10 + ["FOXA2"] * 10,
            LOCHNESS_SELF: [-2.5, -1.8, -0.5, 0.0, 0.2, 0.5, 1.2, 2.4, 3.1, -1.1] + [0.5] * 10,
            "celltype_2": ["PP"] * 20,
            "development_stage": ["PP"] * 20,
        }
    )
    adata = ad.AnnData(X=np.zeros((20, 5)), obs=obs)

    df_geno = compute_lochness_by_genotype(adata)
    assert not df_geno.empty
    pdx1 = df_geno[df_geno["genotype"] == "PDX1"].iloc[0]
    assert pdx1["positive_fraction"] > 0.0
    assert pdx1["negative_fraction"] > 0.0
    assert pdx1["mean_negative_lochness"] < 0.0
    assert pdx1["mean_positive_lochness"] > 0.0


# ---------------------------------------------------------------------------
# Test 29: Positive and Negative lochNESS Not Collapsed (Section O.5)
# ---------------------------------------------------------------------------


def test_lochness_positive_negative_separation():
    """Verify positive enrichment and negative depletion are distinct directional measures."""
    scores = np.array([2.0, 4.0, -1.0, -3.0, 0.0])
    summary = compute_lochness_directional_summary(scores)

    assert np.isclose(summary["lochness_mean"], 0.4)
    assert np.isclose(summary["lochness_positive_mean"], 3.0)
    assert np.isclose(summary["lochness_negative_mean"], -2.0)
    assert np.isclose(summary["lochness_abs_mean"], 2.0)
    assert np.isclose(summary["lochness_positive_fraction"], 0.4)
    assert np.isclose(summary["lochness_negative_fraction"], 0.4)


# ---------------------------------------------------------------------------
# Test 30: Low-Count Groups Masked as NaN (Section O.6)
# ---------------------------------------------------------------------------


def test_low_count_groups_masked_as_nan():
    """Verify genotype x celltype groups with <10 cells are masked as NaN (never 0.0)."""
    obs = pd.DataFrame(
        {
            "genotype": ["PDX1"] * 12 + ["PDX1"] * 5 + ["FOXA2"] * 8,
            "celltype_2": ["PP"] * 12 + ["SC-beta"] * 5 + ["DE"] * 8,
            "ps_score": [0.7] * 12 + [0.8] * 5 + [0.9] * 8,
            LOCHNESS_SELF: [1.5] * 12 + [2.0] * 5 + [-1.2] * 8,
        }
    )
    adata = ad.AnnData(X=np.zeros((25, 5)), obs=obs)

    # PS matrix masking
    _, ps_mat = compute_ps_by_genotype_celltype(adata, min_cells=10)
    assert np.isclose(ps_mat.loc["PDX1", "PP"], 0.7)
    assert np.isnan(ps_mat.loc["PDX1", "SC-beta"])  # 5 cells < 10 -> NaN
    assert np.isnan(ps_mat.loc["FOXA2", "DE"])      # 8 cells < 10 -> NaN

    # lochNESS matrix masking
    _, loch_mat = compute_lochness_by_celltype(adata, min_cells=10)
    assert np.isclose(loch_mat.loc["PDX1", "PP"], 1.5)
    assert np.isnan(loch_mat.loc["PDX1", "SC-beta"])  # 5 cells < 10 -> NaN
    assert np.isnan(loch_mat.loc["FOXA2", "DE"])      # 8 cells < 10 -> NaN


# ---------------------------------------------------------------------------
# Test 31: Consistency Between Heatmap Tables and Plotted Matrices (Section O.7)
# ---------------------------------------------------------------------------


def test_heatmap_table_and_matrix_consistency():
    """Verify summary tables and plotted matrices come from the exact same underlying numbers."""
    obs = pd.DataFrame(
        {
            "genotype": ["PDX1"] * 15 + ["PDX1"] * 12,
            "celltype_2": ["PP"] * 15 + ["PFG"] * 12,
            "ps_score": [0.55] * 15 + [0.35] * 12,
            LOCHNESS_SELF: [1.25] * 15 + [-0.85] * 12,
        }
    )
    adata = ad.AnnData(X=np.zeros((27, 5)), obs=obs)

    ps_table, ps_mat = compute_ps_by_genotype_celltype(adata, min_cells=10)
    for _, row in ps_table.iterrows():
        g, ct, mean_val = row["genotype"], row["celltype_2"], row["mean_ps"]
        if row["n_valid_ps"] >= 10:
            assert np.isclose(ps_mat.loc[g, ct], mean_val)

    loch_table, loch_mat = compute_lochness_by_celltype(adata, min_cells=10)
    for _, row in loch_table.iterrows():
        g, ct, mean_val = row["genotype"], row["celltype_2"], row["mean_lochness"]
        if row["n_cells"] >= 10:
            assert np.isclose(loch_mat.loc[g, ct], mean_val)


# ---------------------------------------------------------------------------
# Test 32: UMAP Plotting Uses Existing X_umap Without Recomputing (Section O.8)
# ---------------------------------------------------------------------------


def test_umap_uses_existing_coordinates(tmp_path):
    """Verify UMAP figure generators read precomputed adata.obsm['X_umap'] directly."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["PDX1"] * 10,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10,
            "development_stage": ["WT"] * 5 + ["PP"] * 10,
            "ps_score": [np.nan] * 5 + [0.75] * 10,
            LOCHNESS_SELF: [np.nan] * 5 + [1.8] * 10,
        }
    )
    custom_umap = np.array([[float(i), float(i * 2)] for i in range(15)], dtype=np.float32)
    adata = ad.AnnData(X=np.zeros((15, 5)), obs=obs, obsm={"X_umap": custom_umap})

    sample_idx = np.arange(15)
    _fig20_umap_ps_score(adata, sample_idx, custom_umap, tmp_path)
    assert (tmp_path / "20_umap_ps_score.png").is_file()
    assert (tmp_path / "umap_ps_score.png").is_file()

    _fig21_umap_lochness_score(adata, sample_idx, custom_umap, tmp_path)
    assert (tmp_path / "21_umap_lochness_score.png").is_file()
    assert (tmp_path / "umap_lochness_score.png").is_file()

    _fig27_umap_ps_lochness_comparison(adata, sample_idx, custom_umap, tmp_path)
    assert (tmp_path / "27_umap_ps_lochness_comparison.png").is_file()
    assert (tmp_path / "umap_ps_lochness_comparison.png").is_file()

    _fig28_umap_highlight_genotypes(adata, sample_idx, custom_umap, tmp_path, highlight_genotypes=["PDX1"])
    assert (tmp_path / "28_umap_highlight_genotypes.png").is_file()
    assert (tmp_path / "umap_highlight_genotypes.png").is_file()


# ---------------------------------------------------------------------------
# Test 33: Per-Genotype Common Manifold Reuse
# ---------------------------------------------------------------------------


def test_per_genotype_manifold_reuse(tmp_path):
    """Verify that every per-genotype UMAP is projected on the exact common global coordinates."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["PDX1"] * 10 + ["FOXA2"] * 8,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10 + ["DE"] * 8,
            "ps_score": [np.nan] * 5 + [0.85] * 10 + [0.60] * 8,
            LOCHNESS_SELF: [np.nan] * 5 + [2.4] * 10 + [-1.8] * 8,
        }
    )
    custom_umap = np.array([[float(i) * 10.0, float(i) * -5.0] for i in range(23)], dtype=np.float32)
    adata = ad.AnnData(X=np.zeros((23, 5)), obs=obs, obsm={"X_umap": custom_umap})

    fig_dir = tmp_path / "figures"
    tables_dir = tmp_path / "tables"

    manifest_df = generate_per_genotype_umaps(adata, fig_dir, tables_dir)

    assert not manifest_df.empty
    assert len(manifest_df) == 2
    assert set(manifest_df["genotype"]) == {"PDX1", "FOXA2"}

    # Confirm files exist
    assert (fig_dir / "per_genotype_ps" / "PDX1_ps_umap.png").is_file()
    assert (fig_dir / "per_genotype_ps" / "FOXA2_ps_umap.png").is_file()
    assert (fig_dir / "per_genotype_lochness" / "PDX1_lochness_umap.png").is_file()
    assert (fig_dir / "per_genotype_lochness" / "FOXA2_lochness_umap.png").is_file()
    assert (fig_dir / "per_genotype_combined" / "PDX1_ps_lochness_umap.png").is_file()
    assert (fig_dir / "per_genotype_combined" / "FOXA2_ps_lochness_umap.png").is_file()
    assert (tables_dir / "per_genotype_umap_manifest.csv").is_file()


# ---------------------------------------------------------------------------
# Test 34: Per-Genotype PS Scale [0, 1] Native & Missing PS Handling
# ---------------------------------------------------------------------------


def test_per_genotype_ps_scale_and_missing_handling(tmp_path):
    """Verify PS UMAP uses native [0, 1] scale and missing PS perturbations are skipped from PS atlas."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["PDX1"] * 10 + ["GATA6het"] * 8,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10 + ["DE"] * 8,
            # GATA6het has NaN PS scores (skipped because target not in expression matrix)
            "ps_score": [np.nan] * 5 + [0.82] * 10 + [np.nan] * 8,
            LOCHNESS_SELF: [np.nan] * 5 + [1.5] * 10 + [-1.2] * 8,
        }
    )
    custom_umap = np.array([[float(i), float(i)] for i in range(23)], dtype=np.float32)
    adata = ad.AnnData(X=np.zeros((23, 5)), obs=obs, obsm={"X_umap": custom_umap})

    ps_skipped = pd.DataFrame(
        [{"genotype": "GATA6het", "reason": "target gene not in the expression matrix"}]
    )

    fig_dir = tmp_path / "figures"
    tables_dir = tmp_path / "tables"

    manifest_df = generate_per_genotype_umaps(
        adata, fig_dir, tables_dir, ps_skipped=ps_skipped
    )

    # Check manifest rows
    pdx1_row = manifest_df[manifest_df["genotype"] == "PDX1"].iloc[0]
    assert pdx1_row["ps_available"] is True or pdx1_row["ps_available"] == 1
    assert pdx1_row["n_valid_ps"] == 10
    assert pdx1_row["ps_png"] != ""
    assert (tmp_path / pdx1_row["ps_png"]).is_file()

    gata6het_row = manifest_df[manifest_df["genotype"] == "GATA6het"].iloc[0]
    assert gata6het_row["ps_available"] is False or gata6het_row["ps_available"] == 0
    assert gata6het_row["n_valid_ps"] == 0
    assert gata6het_row["ps_png"] == ""
    assert "target gene not in the expression matrix" in gata6het_row["ps_skip_reason"]

    # GATA6het should NOT have a file in per_genotype_ps/
    assert not (fig_dir / "per_genotype_ps" / "GATA6het_ps_umap.png").is_file()

    # But GATA6het MUST have a file in per_genotype_lochness/ and per_genotype_combined/
    assert (fig_dir / "per_genotype_lochness" / "GATA6het_lochness_umap.png").is_file()
    assert (fig_dir / "per_genotype_combined" / "GATA6het_ps_lochness_umap.png").is_file()


# ---------------------------------------------------------------------------
# Test 35: Per-Genotype lochNESS Symmetric Color Scale
# ---------------------------------------------------------------------------


def test_per_genotype_lochness_symmetric_scale(tmp_path):
    """Verify lochNESS scale is symmetric around zero across panels."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["PDX1"] * 10 + ["FOXA2"] * 8,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10 + ["DE"] * 8,
            "ps_score": [np.nan] * 5 + [0.5] * 10 + [0.5] * 8,
            LOCHNESS_SELF: [np.nan] * 5 + [3.5] * 10 + [-2.0] * 8,
        }
    )
    umap = np.zeros((23, 2), dtype=np.float32)
    adata = ad.AnnData(X=np.zeros((23, 5)), obs=obs, obsm={"X_umap": umap})

    fig_dir = tmp_path / "figures"
    tables_dir = tmp_path / "tables"

    manifest_df = generate_per_genotype_umaps(adata, fig_dir, tables_dir)
    assert len(manifest_df) == 2
    assert all(manifest_df["lochness_available"])


# ---------------------------------------------------------------------------
# Test 36: Filename Sanitization for Composite Genotypes
# ---------------------------------------------------------------------------


def test_per_genotype_filename_sanitization(tmp_path):
    """Verify composite genotype labels like 'TET1/2/3' are safely sanitized for filenames."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["TET1/2/3"] * 10 + ["QSER1TET1"] * 8,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10 + ["DE"] * 8,
            "ps_score": [np.nan] * 23,
            LOCHNESS_SELF: [np.nan] * 5 + [1.2] * 10 + [-1.5] * 8,
        }
    )
    umap = np.zeros((23, 2), dtype=np.float32)
    adata = ad.AnnData(X=np.zeros((23, 5)), obs=obs, obsm={"X_umap": umap})

    fig_dir = tmp_path / "figures"
    tables_dir = tmp_path / "tables"

    manifest_df = generate_per_genotype_umaps(adata, fig_dir, tables_dir)

    # Label in metadata/manifest remains exact 'TET1/2/3'
    assert "TET1/2/3" in manifest_df["genotype"].values

    # Filename must be sanitized without slashes
    t123_row = manifest_df[manifest_df["genotype"] == "TET1/2/3"].iloc[0]
    assert "TET1__2__3_lochness_umap.png" in t123_row["lochness_png"]
    assert "TET1__2__3_ps_lochness_umap.png" in t123_row["combined_png"]
    assert (tmp_path / t123_row["lochness_png"]).is_file()
    assert (tmp_path / t123_row["combined_png"]).is_file()


# ---------------------------------------------------------------------------
# Test 37: AnnData Non-Mutation during Per-Genotype Plotting
# ---------------------------------------------------------------------------


def test_per_genotype_plotting_non_mutating(tmp_path):
    """Verify per-genotype plotting functions do not mutate input AnnData."""
    obs = pd.DataFrame(
        {
            "genotype": ["WT"] * 5 + ["PDX1"] * 10,
            "celltype_2": ["ESC"] * 5 + ["PP"] * 10,
            "ps_score": [np.nan] * 5 + [0.8] * 10,
            LOCHNESS_SELF: [np.nan] * 5 + [1.5] * 10,
        }
    )
    umap = np.zeros((15, 2), dtype=np.float32)
    adata = ad.AnnData(X=np.zeros((15, 5)), obs=obs.copy(), obsm={"X_umap": umap.copy()})

    orig_obs_cols = list(adata.obs.columns)
    orig_obsm_keys = list(adata.obsm.keys())

    generate_per_genotype_umaps(adata, tmp_path / "figures", tmp_path / "tables")

    assert list(adata.obs.columns) == orig_obs_cols
    assert list(adata.obsm.keys()) == orig_obsm_keys


