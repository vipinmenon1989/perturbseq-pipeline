"""Configuration schema for the Perturb-seq pipeline.

A run is fully described by one YAML file. Every threshold that appeared as a
magic number in the prototype notebooks is a named key here with a documented
default.

Configuration philosophy
------------------------
Biological/statistical parameters and computational scaling parameters are kept
separate.

For example:

    perturbation.min_cells_per_target
    lochness.n_neighbors
    modules.hub_lfc_threshold

describe the analysis itself.

By contrast:

    scaling.mode
    scaling.large_n_cells
    scaling.effect_gene_chunk
    scaling.marker_max_cells

describe *how* the same analysis is executed on different dataset sizes.

This distinction is important: Replogle-scale and KOLF-scale datasets should
use the same biological definitions wherever possible, while the implementation
changes automatically when a dense or all-cell operation would become
impractical.

Adaptive execution
------------------
``scaling.mode`` supports three modes:

``auto``
    Recommended default. STANDARD implementations are used below the configured
    thresholds and LARGE implementations above them.

``standard``
    Force the original implementations regardless of dataset size. Primarily
    useful for regression tests or reproducing an older run. This may exhaust
    memory on million-cell datasets.

``large``
    Force the scalable implementations regardless of dataset size. Useful when
    a dataset below one million cells is still unusually wide, has thousands of
    perturbations, or when memory is limited.

Existing configuration files remain valid because every scaling parameter has a
default.
"""

from __future__ import annotations

import copy

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
    get_type_hints,
)

import yaml


# ===========================================================================
# Run
# ===========================================================================


@dataclass
class RunConfig:
    """Top-level run identity and output location."""

    name: str = "perturbseq_run"
    outdir: str = "results"
    seed: int = 0


# ===========================================================================
# Input
# ===========================================================================


@dataclass
class InputConfig:
    """Where the data comes from.

    Two entry points are supported.

    ``mtx``
        One or more 10x MTX directories holding gene-expression and optionally
        guide features.

    ``h5ad``
        An existing AnnData object. Guide information may live in ``var``, in a
        companion guide h5ad, in a long barcode/guide table, or in a
        pre-computed ``obs`` column.
    """

    mode: str = "auto"  # auto | mtx | h5ad

    mtx_dirs: Union[
        Dict[str, str],
        List[str],
        None,
    ] = None

    guide_mtx_dirs: Optional[
        Dict[str, str]
    ] = None

    h5ad: Optional[str] = None

    guide_h5ad: Optional[str] = None

    guide_obs_column: Optional[str] = None

    feature_type_column: str = "feature_types"

    gex_feature_type: str = "Gene Expression"

    guide_feature_types: List[str] = field(
        default_factory=lambda: [
            "Custom",
            "CRISPR Guide Capture",
        ]
    )

    var_names: str = "gene_symbols"

    cache_mtx: bool = True

    #: h5ad layer containing raw counts.
    counts_layer: Optional[str] = None

    #: h5ad layer already containing log-normalized expression.
    normalized_layer: Optional[str] = None

    #: Optional long barcode -> guide table.
    guide_table: Optional[str] = None

    guide_table_cell_column: str = "cell"

    guide_table_gene_column: str = "gene"

    guide_table_guide_column: Optional[
        str
    ] = "sgrna"

    guide_table_count_column: Optional[
        str
    ] = "umi_count"

    guide_table_strip_prefix: bool = True

    def resolved_mtx_dirs(
        self,
    ) -> Dict[str, str]:
        """Return ``{lane_id: path}`` regardless of input spelling."""

        if not self.mtx_dirs:
            return {}

        if isinstance(
            self.mtx_dirs,
            dict,
        ):
            return dict(
                self.mtx_dirs
            )

        out: Dict[
            str,
            str,
        ] = {}

        for path in (
            self.mtx_dirs
        ):

            lane = (
                Path(
                    path
                ).name
            )

            for prefix in (
                "filtered_feature_bc_matrix_",
                "raw_feature_bc_matrix_",
            ):

                if lane.startswith(
                    prefix
                ):

                    lane = lane[
                        len(
                            prefix
                        ):
                    ]

            out[
                lane
                or Path(
                    path
                ).name
            ] = path

        return out


# ===========================================================================
# Metadata
# ===========================================================================


@dataclass
class MetadataConfig:
    """Per-lane sample metadata."""

    file: Optional[str] = None

    key_column: str = "lane_id"

    require_for_multilane: bool = True


# ===========================================================================
# QC
# ===========================================================================


@dataclass
class QCConfig:
    """Standard single-cell QC thresholds."""

    min_genes_per_cell: Optional[
        int
    ] = 200

    min_cells_per_gene: Optional[
        int
    ] = 3

    min_genes_final: Optional[
        int
    ] = 1000

    max_pct_mt: Optional[
        float
    ] = 20.0

    max_pct_hb: Optional[
        float
    ] = None

    min_counts_per_cell: Optional[
        int
    ] = None

    mito_prefix: str = "MT-"

    ribo_prefix: List[str] = field(
        default_factory=lambda: [
            "RPS",
            "RPL",
        ]
    )

    hb_pattern: str = "^HB[^(P)]"


# ===========================================================================
# Guide calling
# ===========================================================================


@dataclass
class GuideConfig:
    """Guide-calling rules."""

    min_umi: int = 3

    dominance_ratio: float = 2.0

    #: -1 disables the runner-up UMI gate.
    max_second_umi: int = -1

    detection_threshold: int = 3

    target_regex: Optional[
        str
    ] = None

    target_split_delims: List[str] = field(
        default_factory=lambda: [
            "_",
            "-",
            ".",
        ]
    )

    ntc_patterns: List[str] = field(
        default_factory=lambda: [
            r"^non[-_.]?targeting",
            r"^non$",
            r"^ntc",
            r"scramble",
            r"^safe[-_.]?harbor",
        ]
    )

    unassigned_label: str = "unassigned"

    ambiguous_label: str = "ambiguous"

    ntc_label: str = "non-targeting"


# ===========================================================================
# Clustering
# ===========================================================================


@dataclass
class ClusterConfig:
    """Normalization, dimensionality reduction and clustering."""

    target_sum: Optional[
        float
    ] = None

    n_top_genes: int = 3000

    n_pcs: int = 50

    n_neighbors: int = 15

    leiden_resolution: float = 1.0

    umap_min_dist: float = 0.5

    batch_key: Optional[
        str
    ] = None

    regress_out: List[str] = field(
        default_factory=list
    )

    scale_max_value: Optional[
        float
    ] = 10.0

    assigned_only: bool = False


# ===========================================================================
# Perturbation strength
# ===========================================================================


@dataclass
class PerturbationConfig:
    """Target-gene perturbation-strength testing."""

    controls: List[str] = field(
        default_factory=lambda: [
            "ntc",
            "other",
        ]
    )

    primary_control: str = "ntc"

    min_cells_per_target: int = 10

    min_control_cells: int = 10

    min_pct_expressing_control: float = 1.0

    fdr_alpha: float = 0.05

    max_log2fc_for_hit: float = 0.0

    top_n_report: int = 12

    umap_background_fraction: float = 0.1


# ===========================================================================
# Cluster enrichment
# ===========================================================================


@dataclass
class EnrichmentConfig:
    """Enrichment/depletion of perturbations across cell-state clusters."""

    enabled: bool = True

    cluster_key: str = "leiden"

    controls: List[str] = field(
        default_factory=lambda: [
            "ntc",
            "other",
        ]
    )

    primary_control: str = "other"

    fdr_alpha: float = 0.05

    min_cells_per_target: int = 10

    min_cells_per_cluster: int = 20

    min_reference_cells: int = 10

    odds_pseudocount: float = 0.5

    stratify_by: Optional[
        str
    ] = None

    guide_concordance: bool = True

    min_cells_per_guide: int = 5

    permutations: int = 1000

    top_n_report: int = 12


# ===========================================================================
# Regulome / modules
# ===========================================================================


@dataclass
class ModulesConfig:
    """Co-functional modules and co-regulated gene programs."""

    enabled: bool = True

    cluster_key: str = "leiden"

    gene_selection: str = "cluster_markers"

    n_marker_genes_per_cluster: int = 100

    marker_method: str = "wilcoxon"

    min_cells_per_perturbation: int = 20

    control: str = "ntc"

    program_correlation: str = "pearson"

    module_correlation: str = "spearman"

    linkage_method: str = "average"

    n_programs: Optional[
        int
    ] = 4

    n_modules: Optional[
        int
    ] = 9

    cluster_distance_threshold: Optional[
        float
    ] = 0.7

    #: Per-cell program scoring is useful but expensive at very large scale.
    score_programs: bool = True

    hub_lfc_threshold: float = 0.5

    de_fdr_alpha: float = 0.05

    draw_networks: bool = True

    min_perturbations: int = 5

    min_genes: int = 10

    top_n_report: int = 12


# ===========================================================================
# PS score
# ===========================================================================


@dataclass
class PSScoreConfig:
    """Per-cell perturbation-response scoring through ``pertps``."""

    enabled: bool = True

    require: bool = False

    top_n_biomarkers: int = 100

    scale_factor: float = 3.0

    ps_threshold: float = 0.5

    expression_cut: str = "mean"

    expression_cut_quantile: float = 0.75

    min_cells_per_target: int = 10

    min_control_cells: int = 10

    top_n_report: int = 12

    compute_lda_umap: bool = True

    lda_n_pcs: int = 40

    lda_max_genes: Optional[
        int
    ] = 5000

    lda_highlight_threshold: float = 0.8

    #: LARGE-mode LDA visualization is restricted to this many cells.
    #: The PS score itself does not need to use this subset.
    lda_large_max_cells: int = 200_000

    #: In LARGE mode choose the visualization subset with approximately
    #: perturbation/control-stratified sampling.
    lda_large_stratified: bool = True


# ===========================================================================
# lochNESS
# ===========================================================================


@dataclass
class LochnessConfig:
    """Local neighbourhood enrichment of each perturbation."""

    enabled: bool = True

    genotype_key: str = "target_gene"

    n_neighbors: int = 300

    n_pcs: int = 20

    use_rep: Optional[
        str
    ] = None

    recompute_neighbors: bool = True

    min_cells_per_target: int = 10

    enrichment_cut: float = 0.5

    noise_delta: float = 0.0

    top_n_report: int = 12

    #: Number of perturbations processed together by LARGE implementations.
    target_chunk_size: int = 128

    #: Whether one ``lochness_<TARGET>`` column is added for every target.
    #: Fine for small screens, but impossible for 10k-target million-cell runs.
    store_all_target_scores: bool = True

    #: In AUTO/LARGE execution, individual target columns should not be written
    #: into obs above this many targets. ``lochness_self`` remains available.
    max_targets_in_obs: int = 500


# ===========================================================================
# Adaptive scaling
# ===========================================================================


@dataclass
class ScalingConfig:
    """Computational scaling policy.

    These options change how an analysis is executed, not what biological
    quantity is being measured.

    ``mode = auto``
        Automatically use LARGE implementations above the configured
        thresholds.

    ``mode = standard``
        Force the original implementations. Useful for regression testing but
        potentially unsafe for very large objects.

    ``mode = large``
        Force memory-aware implementations even below the normal threshold.
        This is useful for machines with limited RAM, unusually wide matrices,
        or screens containing thousands of perturbations.
    """

    mode: str = "auto"

    #: Main global cell-count trigger.
    large_n_cells: int = 1_000_000

    #: Modules/regulome may independently need LARGE handling because an
    #: enormous number of perturbations creates a large correlation matrix.
    large_n_perturbations: int = 5_000

    #: Maximum cells used for feature/marker discovery in LARGE mode.
    #: Full effect estimation still uses all cells.
    marker_max_cells: int = 200_000

    #: Gene chunk size for LARGE perturbation x gene calculations.
    effect_gene_chunk: int = 256

    #: Standard guide-calling chunk size.
    guide_chunk_size: int = 20_000

    #: A dense guide block larger than this many scalar values should instead
    #: use the sparse guide implementation.
    guide_max_dense_elements: int = 20_000_000

    #: Call Python garbage collection between expensive stages in LARGE mode.
    collect_between_stages: bool = True

    #: Log process resident memory when psutil is available.
    log_memory: bool = True

    #: Maximum rows of a huge table retained for HTML report assembly. The
    #: complete table remains written to disk.
    report_preview_rows: int = 500


# ===========================================================================
# Report
# ===========================================================================


@dataclass
class ReportConfig:
    """HTML report assembly."""

    title: str = "Perturb-seq analysis report"

    embed_figures: bool = True

    figure_format: str = "png"

    figure_dpi: int = 150

    max_table_rows: int = 100


# ===========================================================================
# Outputs
# ===========================================================================


@dataclass
class OutputConfig:
    """Output files and artifact handling."""

    h5ad_name: str = "processed.h5ad"

    report_name: str = "report.html"

    write_unfiltered_h5ad: bool = True

    unfiltered_h5ad_name: Optional[
        str
    ] = None

    large_file_dir: Optional[
        str
    ] = None

    large_file_threshold_mb: float = 50.0

    merge_guides_into_h5ad: bool = True

    guide_obsm_key: str = "guide_counts"

    write_guide_h5ad: bool = False

    save_figures_pdf: bool = False

    archive: bool = True

    archive_name: Optional[
        str
    ] = None

    archive_exclude: List[str] = field(
        default_factory=lambda: [
            "*.h5ad",
            "*.h5",
            "*.loom",
            "*.tar.gz",
        ]
    )

    write_guide_table: bool = True

    guide_table_name: Optional[
        str
    ] = None

    guide_table_min_umi: int = 3


# ===========================================================================
# Full configuration
# ===========================================================================


@dataclass
class Config:
    """Complete pipeline configuration."""

    run: RunConfig = field(
        default_factory=RunConfig
    )

    input: InputConfig = field(
        default_factory=InputConfig
    )

    metadata: MetadataConfig = field(
        default_factory=MetadataConfig
    )

    qc: QCConfig = field(
        default_factory=QCConfig
    )

    guides: GuideConfig = field(
        default_factory=GuideConfig
    )

    cluster: ClusterConfig = field(
        default_factory=ClusterConfig
    )

    perturbation: PerturbationConfig = field(
        default_factory=PerturbationConfig
    )

    enrichment: EnrichmentConfig = field(
        default_factory=EnrichmentConfig
    )

    modules: ModulesConfig = field(
        default_factory=ModulesConfig
    )

    ps_score: PSScoreConfig = field(
        default_factory=PSScoreConfig
    )

    lochness: LochnessConfig = field(
        default_factory=LochnessConfig
    )

    # Central scaling policy.
    scaling: ScalingConfig = field(
        default_factory=ScalingConfig
    )

    report: ReportConfig = field(
        default_factory=ReportConfig
    )

    output: OutputConfig = field(
        default_factory=OutputConfig
    )

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(
        cls,
        data: Optional[
            Dict[str, Any]
        ],
    ) -> "Config":
        """Build from a partial nested mapping, rejecting unknown keys."""

        return _build(
            cls,
            data or {},
            path="",
        )

    @classmethod
    def from_yaml(
        cls,
        path: Union[
            str,
            Path,
        ],
    ) -> "Config":
        """Load and validate a YAML configuration."""

        path = Path(
            path
        )

        if not path.is_file():

            raise FileNotFoundError(
                f"Config file not found: {path}"
            )

        with open(
            path
        ) as handle:

            data = (
                yaml.safe_load(
                    handle
                )
                or {}
            )

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                f"Config file must contain a YAML mapping: {path}"
            )

        cfg = cls.from_dict(
            data
        )

        cfg.validate()

        return cfg

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(
        self,
    ) -> Dict[str, Any]:
        """Return configuration as a nested plain dictionary."""

        return _asdict(
            self
        )

    def dump_yaml(
        self,
        path: Union[
            str,
            Path,
        ],
    ) -> None:
        """Write the fully resolved configuration."""

        path = Path(
            path
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            path,
            "w",
        ) as handle:

            yaml.safe_dump(
                self.to_dict(),
                handle,
                sort_keys=False,
                default_flow_style=False,
            )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(
        self,
    ) -> None:
        """Check internal consistency."""

        # ==============================================================
        # Input
        # ==============================================================

        inp = (
            self.input
        )

        if inp.mode not in (
            "auto",
            "mtx",
            "h5ad",
        ):

            raise ValueError(
                "input.mode must be one of "
                "'auto', 'mtx', 'h5ad' "
                f"(got {inp.mode!r})"
            )

        has_mtx = bool(
            inp.resolved_mtx_dirs()
        )

        has_h5ad = bool(
            inp.h5ad
        )

        if (
            inp.mode == "mtx"
            and not has_mtx
        ):

            raise ValueError(
                "input.mode is 'mtx' but input.mtx_dirs is empty"
            )

        if (
            inp.mode == "h5ad"
            and not has_h5ad
        ):

            raise ValueError(
                "input.mode is 'h5ad' but input.h5ad is not set"
            )

        if (
            inp.mode == "auto"
        ):

            if (
                has_mtx
                and has_h5ad
            ):

                raise ValueError(
                    "Both input.mtx_dirs and input.h5ad are set; "
                    "set input.mode explicitly."
                )

            if (
                not has_mtx
                and not has_h5ad
            ):

                raise ValueError(
                    "No input given: set input.mtx_dirs or input.h5ad."
                )

        if inp.guide_mtx_dirs:

            lanes = set(
                inp.resolved_mtx_dirs()
            )

            guide_lanes = set(
                inp.guide_mtx_dirs
            )

            missing = (
                lanes
                - guide_lanes
            )

            if missing:

                raise ValueError(
                    "input.guide_mtx_dirs must cover every lane; "
                    f"missing {sorted(missing)}"
                )

            extra = (
                guide_lanes
                - lanes
            )

            if extra:

                raise ValueError(
                    "input.guide_mtx_dirs contains lanes not in mtx_dirs: "
                    f"{sorted(extra)}"
                )

        # ==============================================================
        # Guides
        # ==============================================================

        if (
            self.guides.dominance_ratio
            < 1
        ):

            raise ValueError(
                "guides.dominance_ratio must be >= 1"
            )

        if (
            self.guides.min_umi
            < 0
        ):

            raise ValueError(
                "guides.min_umi must be >= 0"
            )

        if (
            self.guides.detection_threshold
            < 0
        ):

            raise ValueError(
                "guides.detection_threshold must be >= 0"
            )

        # ==============================================================
        # Clustering
        # ==============================================================

        if (
            self.cluster.n_top_genes
            < 1
        ):

            raise ValueError(
                "cluster.n_top_genes must be >= 1"
            )

        if (
            self.cluster.n_pcs
            < 2
        ):

            raise ValueError(
                "cluster.n_pcs must be >= 2"
            )

        if (
            self.cluster.n_neighbors
            < 2
        ):

            raise ValueError(
                "cluster.n_neighbors must be >= 2"
            )

        # ==============================================================
        # Control definitions
        # ==============================================================

        valid_controls = {
            "ntc",
            "other",
        }

        bad = (
            set(
                self.perturbation.controls
            )
            - valid_controls
        )

        if bad:

            raise ValueError(
                "perturbation.controls may only contain "
                f"{sorted(valid_controls)}; got {sorted(bad)}"
            )

        if not self.perturbation.controls:

            raise ValueError(
                "perturbation.controls must not be empty"
            )

        if (
            self.perturbation.primary_control
            not in self.perturbation.controls
        ):

            raise ValueError(
                "perturbation.primary_control must occur in "
                "perturbation.controls"
            )

        if not (
            0
            < self.perturbation.fdr_alpha
            < 1
        ):

            raise ValueError(
                "perturbation.fdr_alpha must be in (0, 1)"
            )

        if not (
            0
            < self.perturbation.umap_background_fraction
            <= 1
        ):

            raise ValueError(
                "perturbation.umap_background_fraction must be in (0, 1]"
            )

        # ==============================================================
        # Enrichment
        # ==============================================================

        bad = (
            set(
                self.enrichment.controls
            )
            - valid_controls
        )

        if bad:

            raise ValueError(
                "enrichment.controls may only contain "
                f"{sorted(valid_controls)}; got {sorted(bad)}"
            )

        if not self.enrichment.controls:

            raise ValueError(
                "enrichment.controls must not be empty"
            )

        if (
            self.enrichment.primary_control
            not in self.enrichment.controls
        ):

            raise ValueError(
                "enrichment.primary_control must occur in enrichment.controls"
            )

        if not (
            0
            < self.enrichment.fdr_alpha
            < 1
        ):

            raise ValueError(
                "enrichment.fdr_alpha must be in (0, 1)"
            )

        # ==============================================================
        # Modules
        # ==============================================================

        modules = (
            self.modules
        )

        if (
            modules.control
            not in valid_controls
        ):

            raise ValueError(
                "modules.control must be one of "
                f"{sorted(valid_controls)} "
                f"(got {modules.control!r})"
            )

        if (
            modules.gene_selection
            not in (
                "cluster_markers",
                "hvg",
            )
        ):

            raise ValueError(
                "modules.gene_selection must be "
                "'cluster_markers' or 'hvg'"
            )

        for name in (
            "program_correlation",
            "module_correlation",
        ):

            value = getattr(
                modules,
                name,
            )

            if value not in (
                "pearson",
                "spearman",
            ):

                raise ValueError(
                    f"modules.{name} must be 'pearson' or 'spearman'"
                )

        if (
            modules.linkage_method
            not in (
                "average",
                "complete",
                "single",
                "ward",
                "weighted",
            )
        ):

            raise ValueError(
                "modules.linkage_method must be a supported scipy "
                "hierarchical linkage method"
            )

        if not (
            0
            < modules.de_fdr_alpha
            < 1
        ):

            raise ValueError(
                "modules.de_fdr_alpha must be in (0, 1)"
            )

        for name in (
            "n_programs",
            "n_modules",
        ):

            value = getattr(
                modules,
                name,
            )

            if (
                value is not None
                and value < 2
            ):

                raise ValueError(
                    f"modules.{name} must be >=2 or null"
                )

            if (
                value is None
                and modules.cluster_distance_threshold
                is None
            ):

                raise ValueError(
                    f"modules.{name} is null and "
                    "modules.cluster_distance_threshold is null"
                )

        # ==============================================================
        # PS
        # ==============================================================

        ps = (
            self.ps_score
        )

        if (
            ps.expression_cut
            not in (
                "mean",
                "median",
                "quantile",
            )
        ):

            raise ValueError(
                "ps_score.expression_cut must be "
                "'mean', 'median' or 'quantile'"
            )

        if not (
            0
            < ps.expression_cut_quantile
            < 1
        ):

            raise ValueError(
                "ps_score.expression_cut_quantile must be in (0, 1)"
            )

        if (
            ps.lda_n_pcs
            < 2
        ):

            raise ValueError(
                "ps_score.lda_n_pcs must be >= 2"
            )

        if (
            ps.lda_max_genes is not None
            and ps.lda_max_genes < 2
        ):

            raise ValueError(
                "ps_score.lda_max_genes must be >=2 or null"
            )

        if (
            ps.lda_large_max_cells
            < 10
        ):

            raise ValueError(
                "ps_score.lda_large_max_cells must be >=10"
            )

        # ==============================================================
        # lochNESS
        # ==============================================================

        loch = (
            self.lochness
        )

        if (
            loch.n_neighbors
            < 2
        ):

            raise ValueError(
                "lochness.n_neighbors must be >= 2"
            )

        if (
            loch.target_chunk_size
            < 1
        ):

            raise ValueError(
                "lochness.target_chunk_size must be >= 1"
            )

        if (
            loch.max_targets_in_obs
            < 1
        ):

            raise ValueError(
                "lochness.max_targets_in_obs must be >= 1"
            )

        # ==============================================================
        # Scaling
        # ==============================================================

        scaling = (
            self.scaling
        )

        if (
            scaling.mode
            not in (
                "auto",
                "standard",
                "large",
            )
        ):

            raise ValueError(
                "scaling.mode must be "
                "'auto', 'standard' or 'large' "
                f"(got {scaling.mode!r})"
            )

        if (
            scaling.large_n_cells
            < 1
        ):

            raise ValueError(
                "scaling.large_n_cells must be >= 1"
            )

        if (
            scaling.large_n_perturbations
            < 1
        ):

            raise ValueError(
                "scaling.large_n_perturbations must be >= 1"
            )

        if (
            scaling.marker_max_cells
            < 1
        ):

            raise ValueError(
                "scaling.marker_max_cells must be >= 1"
            )

        if (
            scaling.effect_gene_chunk
            < 1
        ):

            raise ValueError(
                "scaling.effect_gene_chunk must be >= 1"
            )

        if (
            scaling.guide_chunk_size
            < 1
        ):

            raise ValueError(
                "scaling.guide_chunk_size must be >= 1"
            )

        if (
            scaling.guide_max_dense_elements
            < 1
        ):

            raise ValueError(
                "scaling.guide_max_dense_elements must be >= 1"
            )

        if (
            scaling.report_preview_rows
            < 1
        ):

            raise ValueError(
                "scaling.report_preview_rows must be >= 1"
            )

        # ==============================================================
        # Report / output
        # ==============================================================

        if (
            self.report.figure_dpi
            < 1
        ):

            raise ValueError(
                "report.figure_dpi must be >=1"
            )

        if (
            self.report.max_table_rows
            < 1
        ):

            raise ValueError(
                "report.max_table_rows must be >=1"
            )

        if (
            self.output.large_file_threshold_mb
            < 0
        ):

            raise ValueError(
                "output.large_file_threshold_mb must be >=0"
            )

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def outdir(
        self,
    ) -> Path:
        """Run output directory."""

        return Path(
            self.run.outdir
        )

    def resolved_mode(
        self,
    ) -> str:
        """Effective input mode after ``auto`` resolution."""

        if (
            self.input.mode
            != "auto"
        ):

            return (
                self.input.mode
            )

        return (
            "mtx"
            if self.input.resolved_mtx_dirs()
            else "h5ad"
        )

    # ------------------------------------------------------------------
    # Adaptive execution API
    # ------------------------------------------------------------------

    def use_large_mode(
        self,
        n_cells: int,
        n_perturbations: Optional[
            int
        ] = None,
    ) -> bool:
        """Return whether LARGE implementations should be used.

        Explicit mode selection has highest priority.

        ``large``
            Always True.

        ``standard``
            Always False.

        ``auto``
            True when either the global cell threshold or, when supplied, the
            perturbation-count threshold is reached.

        Examples
        --------
        Replogle:

            cfg.use_large_mode(310_385)
            -> False

        KOLF:

            cfg.use_large_mode(2_659_209)
            -> True

        Smaller dataset forced to scalable algorithms:

            scaling.mode: large

            cfg.use_large_mode(150_000)
            -> True

        Million-cell regression test forced through old implementation:

            scaling.mode: standard

            cfg.use_large_mode(2_659_209)
            -> False

        The final case is permitted deliberately but may exhaust RAM.
        """

        mode = (
            self.scaling.mode
        )

        if (
            mode == "large"
        ):

            return True

        if (
            mode == "standard"
        ):

            return False

        if (
            n_cells
            >= self.scaling.large_n_cells
        ):

            return True

        if (
            n_perturbations
            is not None
            and n_perturbations
            >= self.scaling.large_n_perturbations
        ):

            return True

        return False

    def execution_mode(
        self,
        n_cells: int,
        n_perturbations: Optional[
            int
        ] = None,
    ) -> str:
        """Return ``'standard'`` or ``'large'`` for logging/provenance."""

        return (
            "large"
            if self.use_large_mode(
                n_cells,
                n_perturbations,
            )
            else "standard"
        )


# ===========================================================================
# Dict -> dataclass
# ===========================================================================


def _build(
    cls: type,
    data: Dict[
        str,
        Any,
    ],
    path: str,
) -> Any:
    """Recursively instantiate nested dataclasses and reject unknown keys."""

    known = {
        item.name: item
        for item
        in fields(
            cls
        )
    }

    unknown = (
        set(
            data
        )
        - set(
            known
        )
    )

    if unknown:

        where = (
            path
            or "<root>"
        )

        raise ValueError(
            f"Unknown config key(s) under {where}: "
            f"{sorted(unknown)}. "
            f"Valid keys: {sorted(known)}"
        )

    hints = (
        get_type_hints(
            cls
        )
    )

    kwargs: Dict[
        str,
        Any,
    ] = {}

    for name in (
        known
    ):

        if (
            name
            not in data
        ):

            continue

        value = (
            data[
                name
            ]
        )

        field_type = (
            hints.get(
                name
            )
        )

        if (
            is_dataclass(
                field_type
            )
            and isinstance(
                value,
                dict,
            )
        ):

            kwargs[
                name
            ] = _build(
                field_type,
                value,
                (
                    f"{path}.{name}"
                    if path
                    else name
                ),
            )

        else:

            kwargs[
                name
            ] = copy.deepcopy(
                value
            )

    return cls(
        **kwargs
    )


# ===========================================================================
# Dataclass -> dict
# ===========================================================================


def _asdict(
    obj: Any,
) -> Any:
    """Recursively turn dataclasses into YAML-safe structures."""

    if is_dataclass(
        obj
    ):

        return {
            item.name: _asdict(
                getattr(
                    obj,
                    item.name,
                )
            )
            for item
            in fields(
                obj
            )
        }

    if isinstance(
        obj,
        dict,
    ):

        return {
            key: _asdict(
                value
            )
            for key, value
            in obj.items()
        }

    if isinstance(
        obj,
        (
            list,
            tuple,
        ),
    ):

        return [
            _asdict(
                value
            )
            for value
            in obj
        ]

    if isinstance(
        obj,
        Path,
    ):

        return str(
            obj
        )

    return obj


# ===========================================================================
# Fully resolved defaults
# ===========================================================================


DEFAULTS: Dict[
    str,
    Any,
] = (
    Config()
    .to_dict()
)