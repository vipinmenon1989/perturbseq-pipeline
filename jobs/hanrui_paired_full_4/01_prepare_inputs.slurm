#!/bin/bash
#SBATCH --job-name=hpf4_01_prepare
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=2
#SBATCH --time=01:00:00
#SBATCH --mem=8G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.err
# Step 1: stage the validated iteration-3 inputs (guide matrices, pair reference, audit) with md5 verification. CPU/IO only.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_paired_full_4/_env.sh
python jobs/hanrui_paired_full_4/prepare_inputs.py "$PREV" "$OUT"
cp "$CFG" "$OUT/config/"
echo "DONE $(date -Is)"
