#!/bin/bash
#SBATCH --job-name=hpf_01_audit
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00
#SBATCH --mem=16G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.err
# Step 1: initial audit (reports, dataset tree, inputs, workbook, repo state) and pair-guide reference.
# CPU-only work runs on ihc-grid-1-1-1 (the GPU node rejects CPU-only allocations without --gres).
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full/_env.sh
python jobs/hanrui_pair_full/audit_and_reference.py --data "$DATA" --repo "$REPO" --out "$OUT" \
  --qc-config config/hanrui_fang.yaml \
  --cellranger-root results/outputs/hanrui_fang_inputs/cellranger \
  --guide-counts-root results/Hanrui_fang_dual_guide/guide_counts \
  --prior-quant-tables results/Hanrui_fang_dual_guide/tables 2>&1 | tee "$OUT/slurm/01_audit.log" | tail -40
echo "DONE $(date -Is)"
