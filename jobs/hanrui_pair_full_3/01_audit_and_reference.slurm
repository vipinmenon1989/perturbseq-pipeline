#!/bin/bash
#SBATCH --job-name=hpf3_01_audit
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=4
#SBATCH --time=03:00:00
#SBATCH --mem=32G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_3/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_3/slurm/%x_%j.err
# Step 1 (iteration 3): re-derive the experimental information record, source inventory, construct map and
# guide reference from the documents (Excel / Word / FASTQ parsing -> SLURM only); copy the scaffold-specific
# guide count matrices of iteration 2 with md5 verification. CPU/IO only -> ihc-grid-1-1-1.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_3/_env.sh
/usr/bin/time -v python jobs/hanrui_pair_full_3/audit_and_reference_3.py --data "$DATA" --repo "$REPO" --out "$OUT" --prev "$PREV" \
  --prev-design-audit "$REPO/results/Hanrui_Fang_library_design_audit" --qc-config config/hanrui_fang.yaml \
  --cellranger-root results/outputs/hanrui_fang_inputs/cellranger \
  --prev-guide-ref "$REPO/results/Hanrui_Fang_pair_guide_full/audit/pair_guide_reference.csv" --prev-counts "$PREV" \
  --manifest-name Hanrui_Fang_pair_guide_full_3_sample_manifest.csv 2>&1 | tee "$OUT/slurm/01_audit.log" | tail -30
echo "DONE $(date -Is)"
