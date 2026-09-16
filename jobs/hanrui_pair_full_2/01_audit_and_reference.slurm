#!/bin/bash
#SBATCH --job-name=hpf2_01_audit
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=4
#SBATCH --time=03:00:00
#SBATCH --mem=32G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/%x_%j.err
# Step 1: audit of every dataset file, the NEW experimental documents (oligo-pool construct map, scaffold
# sequences), FASTQ scaffold consensus, Cell Ranger metadata; writes the design record, evidence matrix and
# the document-derived pair-guide reference. CPU/IO only -> ihc-grid-1-1-1 (the h200 node rejects CPU-only
# allocations without --gres; a GPU would be idle here).
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_2/_env.sh
/usr/bin/time -v python jobs/hanrui_pair_full_2/audit_and_reference.py --data "$DATA" --repo "$REPO" --out "$OUT" --prev "$PREV" \
  --prev-design-audit "$REPO/results/Hanrui_Fang_library_design_audit" --qc-config config/hanrui_fang.yaml \
  --cellranger-root results/outputs/hanrui_fang_inputs/cellranger 2>&1 | tee "$OUT/slurm/01_audit.log" | tail -30
echo "DONE $(date -Is)"
