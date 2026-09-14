#!/bin/bash
#SBATCH --job-name=hf_02_guide_design
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
#SBATCH --mem=16G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 3: inspect the guide-design workbook (all worksheets) and write the
# guide reference, design audit, and (provisional) pair map.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
mkdir -p "$RES/tables" "$RES/logs"
python jobs/hanrui_fang/audit_guide_design.py \
  --web-dir "$DATA/web_summaries" \
  --qc-config config/hanrui_fang.yaml \
  --prior-feature-table results/outputs/hanrui_fang_qc/tables/guide_feature_table.tsv \
  --out-tables "$RES/tables" \
  --out-md "$RES/guide_design_audit.md" 2>&1 | tee "$RES/logs/02_audit_guide_design.log"
echo "DONE $(date -Is)"
