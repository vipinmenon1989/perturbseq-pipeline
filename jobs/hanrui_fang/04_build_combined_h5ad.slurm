#!/bin/bash
#SBATCH --job-name=hf_04_build_h5ad
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=150G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 6: combined + per-well H5AD objects from staged Cell Ranger GEX and the
# job-03 guide counts.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
mkdir -p "$WORK/per_sample" "$RES/logs"
/usr/bin/time -v python jobs/hanrui_fang/build_combined_h5ad.py \
  --cellranger-root results/outputs/hanrui_fang_inputs/cellranger \
  --guide-counts-root "$RES/guide_counts" \
  --reference "$RES/tables/guide_reference_used.csv" \
  --quant-summary "$RES/tables/guide_quantification_summary.csv" \
  --out "$WORK/Hanrui_fang_combined.h5ad" \
  --per-sample-dir "$WORK/per_sample" \
  --tables "$RES/tables" \
  --design "$DATA/web_summaries/design_out_v2.xlsx" 2>&1 | tee "$RES/logs/04_build_combined_h5ad.log"
echo "DONE $(date -Is)"
