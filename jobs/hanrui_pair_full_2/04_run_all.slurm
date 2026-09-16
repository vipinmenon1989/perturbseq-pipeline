#!/bin/bash
#SBATCH --job-name=pert_tf
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=128
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/slurm_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/slurm_%j.err
# Step 4 (the task's production template): four independent per-sample runs, then the combined run, all from
# the single iteration-2 config. The GPU is allocated because the requested node requires --gres; the
# pipeline itself is CPU-only (documented in execution_commands.md).
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_2/_env.sh
python jobs/hanrui_pair_full_2/fix_reference_symbols.py "$OUT/audit/pair_guide_reference.csv"
for w in HF011A HF011B HF012A HF012B; do
  echo "=== per-sample run $w  $(date -Is) ==="
  /usr/bin/time -v perturbseq-pipeline run -c "$CFG" --lane "$w" 2>&1 | tee "$OUT/slurm/04_run_$w.log" | grep -E "Stage|WARNING|ERROR|Pair assignment|Done in|Elapsed|Maximum resident|Exit status" || true
  test -f "$OUT/samples/$w/report.html" -a -f "$OUT/samples/$w/report.md" || { echo "FAILED: $w"; exit 1; }
done
echo "=== combined run  $(date -Is) ==="
/usr/bin/time -v perturbseq-pipeline run -c "$CFG" --combined-subdir combined 2>&1 | tee "$OUT/slurm/04_run_combined.log" | grep -E "Stage|WARNING|ERROR|Pair assignment|Done in|Elapsed|Maximum resident|Exit status" || true
test -f "$OUT/combined/report.html" -a -f "$OUT/combined/report.md" || { echo "FAILED: combined"; exit 1; }
echo "DONE $(date -Is)"
