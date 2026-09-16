#!/bin/bash
#SBATCH --job-name=pert_tf
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=128
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/hanrui_fang_full_4_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/hanrui_fang_full_4_%j.err
# ALLOCATION NOTE: the requested ihc-h200-1 node had all 8 GPUs allocated to other users (estimated start > 5 h later);
# the pipeline runs on CPU for this cell count (161k < compute.gpu_min_cells), so the equivalent CPU allocation
# (128 CPUs, 350 GB) on ihc-grid-1-1-1 without --gres is used. Documented in execution_commands.md / job_ids.txt.
# Iteration 4 production runs: four per-sample runs + combined, all optional perturbation modules enabled.
# Parallelism (compute block of the config): 32 workers, 16 module workers, 1 lochNESS worker, 1 BLAS thread per worker.
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_paired_full_4/_env.sh
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMBA_NUM_THREADS=32
echo "START $(date -Is) job ${SLURM_JOB_ID}" | tee -a "$OUT/logs/run_times.txt"
for w in HF011A HF011B HF012A HF012B; do
  echo "=== per-sample run $w  $(date -Is) ===" | tee -a "$OUT/logs/run_times.txt"
  /usr/bin/time -v perturbseq-pipeline run -c "$CFG" --lane "$w" 2>&1 | tee "$OUT/slurm/03_run_$w.log" | grep -E "Stage|WARNING|ERROR|Traceback|Pair assignment|disabled|skipp|Done in|Elapsed|Maximum resident|Exit status" || true
  test -f "$OUT/samples/$w/report.html" -a -f "$OUT/samples/$w/report.md" || { echo "FAILED: $w"; exit 1; }
done
echo "=== combined run  $(date -Is) ===" | tee -a "$OUT/logs/run_times.txt"
/usr/bin/time -v perturbseq-pipeline run -c "$CFG" --combined-subdir combined 2>&1 | tee "$OUT/slurm/03_run_combined.log" | grep -E "Stage|WARNING|ERROR|Traceback|Pair assignment|disabled|skipp|Done in|Elapsed|Maximum resident|Exit status" || true
test -f "$OUT/combined/report.html" -a -f "$OUT/combined/report.md" || { echo "FAILED: combined"; exit 1; }
echo "END $(date -Is) job ${SLURM_JOB_ID}" | tee -a "$OUT/logs/run_times.txt"
echo "DONE $(date -Is)"
