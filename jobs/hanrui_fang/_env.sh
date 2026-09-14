# Shared preamble for the Hanrui Fang dual-guide SLURM jobs.
# Sourced by every jobs/hanrui_fang/*.slurm script.
set -euo pipefail
REPO=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
DATA=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X
RES=$REPO/results/Hanrui_fang_dual_guide
WORK=$REPO/work/Hanrui_fang
cd "$REPO"
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export MPLBACKEND=Agg
export PYTHONUNBUFFERED=1
echo "HOST: $(hostname)  DATE: $(date -Is)  JOB: ${SLURM_JOB_NAME:-?}/${SLURM_JOB_ID:-none}"
echo "CPUS: ${SLURM_CPUS_PER_TASK:-?}  MEM: ${SLURM_MEM_PER_NODE:-?}  PWD: $(pwd)"
echo "GIT: $(git rev-parse --abbrev-ref HEAD) $(git rev-parse HEAD)"
echo "PYTHON: $(which python) $(python --version 2>&1)"
