#!/bin/bash
#SBATCH --job-name=hanrui_pair_qc
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=128
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.err
# Step 3: four independent per-sample runs, then the combined run, all from the one config.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full/_env.sh
for w in HF011A HF011B HF012A HF012B; do
  echo "=== per-sample run $w  $(date -Is) ==="
  /usr/bin/time -v perturbseq-pipeline run -c "$CFG" --lane "$w" 2>&1 | tee "$OUT/slurm/03_run_$w.log" | grep -E "Stage|WARNING|ERROR|Done in|Elapsed|Maximum resident|Exit status" || true
  test -f "$OUT/samples/$w/report.html" || { echo "FAILED: $w"; exit 1; }
done
echo "=== combined run  $(date -Is) ==="
/usr/bin/time -v perturbseq-pipeline run -c "$CFG" --combined-subdir combined 2>&1 | tee "$OUT/slurm/03_run_combined.log" | grep -E "Stage|WARNING|ERROR|Done in|Elapsed|Maximum resident|Exit status" || true
test -f "$OUT/combined/report.html" || { echo "FAILED: combined"; exit 1; }
echo "DONE $(date -Is)"
