#!/bin/bash
#SBATCH --job-name=hf_06_per_sample
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=128
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 9: four per-sample runs (same dual-guide, QC, clustering and perturbation
# parameters as the combined run), executed sequentially.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
mkdir -p "$RES/logs"
for w in HF011A HF011B HF012A HF012B; do
  echo "=== per-sample run $w  $(date -Is) ==="
  /usr/bin/time -v perturbseq-pipeline run --config "config/Hanrui_fang_dual_guide/$w.yaml" 2>&1 | tee "$RES/logs/06_run_per_sample_$w.log" | grep -E "Stage|WARNING|ERROR|Done in|Elapsed|Maximum resident|Exit status" || true
  test -f "$RES/per_sample/$w/report.html" || { echo "FAILED: $w produced no report"; exit 1; }
done
echo "DONE $(date -Is)"
