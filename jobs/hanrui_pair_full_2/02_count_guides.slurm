#!/bin/bash
#SBATCH --job-name=hpf2_02_count
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=16
#SBATCH --time=06:00:00
#SBATCH --mem=160G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/%x_%j.err
# Step 2: scaffold-specific guide quantification (8 FASTQ files, one worker each). CPU-only -> ihc-grid-1-1-1.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_2/_env.sh
/usr/bin/time -v python jobs/hanrui_pair_full_2/count_guides_scaffold_split.py --qc-config config/hanrui_fang.yaml --data-root "$DATA" \
  --cellranger-root results/outputs/hanrui_fang_inputs/cellranger --out "$OUT" --max-mismatches 1 --n-workers 8 2>&1 | tee "$OUT/slurm/02_count_guides.log" | grep -vE "^\s+(Average|Swaps|Socket|Signals|Page size|File system|Minor|Major|Voluntary|Involuntary)"
echo "DONE $(date -Is)"
