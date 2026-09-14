# Shared preamble for the Hanrui QC SLURM jobs: activate the project env and
# print enough to prove the job runs inside the perturbseq-pipeline env.
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
echo "HOST: $(hostname)"
echo "DATE: $(date)"
echo "PWD: $(pwd)"
echo "SLURM_JOB_ID: ${SLURM_JOB_ID:-none}  CPUS: ${SLURM_CPUS_PER_TASK:-?}  MEM: ${SLURM_MEM_PER_NODE:-?}"
echo "GIT: $(git rev-parse --abbrev-ref HEAD) $(git rev-parse --short HEAD)"
which python
python --version
which perturbseq-pipeline
conda info --envs | grep -E "^\*|perturbseq-pipeline" || true
export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export OPENBLAS_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
export MKL_NUM_THREADS=${SLURM_CPUS_PER_TASK:-8}
