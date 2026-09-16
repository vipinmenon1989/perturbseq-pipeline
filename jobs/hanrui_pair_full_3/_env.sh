# Shared preamble for the Hanrui Fang pair-guide full-analysis iteration 3 SLURM jobs.
set -euo pipefail
REPO=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
DATA=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X
OUT=$REPO/results/Hanrui_Fang_pair_guide_full_3
PREV=$REPO/results/Hanrui_Fang_pair_guide_full_2
CFG=$REPO/config/Hanrui_Fang_pair_guide_full_3.yaml
cd "$REPO"
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8} OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8} MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8} NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export MPLBACKEND=Agg PYTHONUNBUFFERED=1
echo "HOST: $(hostname)  DATE: $(date -Is)  JOB: ${SLURM_JOB_NAME:-?}/${SLURM_JOB_ID:-none}  CPUS: ${SLURM_CPUS_PER_TASK:-?}  MEM: ${SLURM_MEM_PER_NODE:-?}  ENV: ${CONDA_DEFAULT_ENV:-?}"
echo "GIT: $(git rev-parse --abbrev-ref HEAD) $(git rev-parse HEAD)"
echo "PYTHON: $(which python) $(python --version 2>&1)"
