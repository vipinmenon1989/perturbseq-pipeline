#!/bin/bash
#SBATCH --job-name=hf_07_combined
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=96   # trimmed from the 128-CPU template so it co-schedules with 06 (pipeline uses <= 32 workers)
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 10: combined four-well run (concatenation, no Harmony) with dual-guide assignment.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
mkdir -p "$RES/logs"
/usr/bin/time -v perturbseq-pipeline run --config config/Hanrui_fang_dual_guide.yaml 2>&1 | tee "$RES/logs/07_run_combined.log" | grep -E "Stage|WARNING|ERROR|Done in|Elapsed|Maximum resident|Exit status" || true
test -f "$RES/combined/report.html" || { echo "FAILED: combined run produced no report"; exit 1; }
echo "DONE $(date -Is)"
