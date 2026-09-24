# Running on SLURM

The pipeline is a single command, so a SLURM job is a thin wrapper around it.
Two rules keep runs reproducible and keep login nodes usable:

1. Load real datasets only inside a job. The login node is for `git`, config
   editing and the synthetic unit tests.
2. Run the pipeline from a committed checkout. `logs/run_manifest.json`
   records the git commit and marks the tree as dirty when uncommitted changes
   were present.

## One run

```bash
#!/bin/bash
#SBATCH --job-name=perturbseq_run
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=06:00:00
#SBATCH --output=slurm/%x_%j.out

source /path/to/conda/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK} OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK} MPLBACKEND=Agg

perturbseq-pipeline run --config config/my_run.yaml
```

`compute.n_jobs` is capped by `SLURM_CPUS_PER_TASK` when that variable is set,
so a config written for a workstation does not oversubscribe a shared node.
Worker processes limit their BLAS threads to `compute.blas_threads_per_worker`.

## Per-lane and combined runs

For multi-lane inputs the same config drives one job per lane and one pooled
job. Per-lane runs write to `<outdir>/samples/<lane>` and the pooled run to
`<outdir>/<subdir>`; with `input.cell_id_format: prefix` a per-lane object is a
row subset of the combined object.

```bash
for lane in W1 W2 W3 W4; do
  sbatch --job-name=psq_$lane --wrap "perturbseq-pipeline run -c config/my_run.yaml --lane $lane"
done
sbatch --job-name=psq_combined --wrap "perturbseq-pipeline run -c config/my_run.yaml --combined-subdir combined"
```

## Large datasets

| Setting | Effect |
|---|---|
| `scaling.mode: auto` | LARGE execution paths above `scaling.large_n_cells` / `large_n_perturbations` (sparse PCA scaling, chunked effect matrices, chunked lochNESS, bounded LDA, sampled plotting); statistics unchanged |
| `storage.mode: auto` | backed `.h5ad` reading above `storage.backed_threshold_cells` |
| `compute.backend: auto` | CPU by default; GPU only when the `gpu` extra is installed and a device is present (`--gres=gpu:1`) |
| `modules.draw_networks: false`, `ps_score.compute_lda_umap: false` | skip the most expensive figures |
| `distance_space.enabled: false` | all-vs-all distances grow with the square of the target count; enable deliberately |
| `output.archive: false` | skip the multi-gigabyte tarball while iterating |

Rough resource guidance: 16 to 32 CPUs, 180 to 200 GB and up to 12 hours for a
screen of about 2.5 million cells; a few hours and well under 64 GB for
screens of a few hundred thousand cells. Peak memory depends on sparsity, the
number of targets and the lochNESS neighbourhood size.

## Tests

The unit tests use small synthetic fixtures and finish in about ten minutes on
eight cores:

```bash
sbatch --cpus-per-task=8 --mem=48G --time=02:00:00 \
  --wrap "conda activate perturbseq-pipeline && pytest -q tests/"
```

Integration tests on real matrices are SLURM jobs by definition; never load
them on a login node.
