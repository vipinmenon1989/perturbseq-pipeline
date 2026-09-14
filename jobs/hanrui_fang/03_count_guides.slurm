#!/bin/bash
#SBATCH --job-name=hf_03_count_guides
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=24
#SBATCH --time=06:00:00
#SBATCH --mem=160G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 5: scaffold-aware guide quantification of HF011AF/HF011BF/HF012AF/HF012BF
# (exact + unambiguous 1-mismatch + +/-1 nt shift), one matrix per well over the
# paired GEX barcode universe. Raw data are read only.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
CR=$REPO/results/outputs/hanrui_fang_inputs/cellranger
for w in HF011A HF011B HF012A HF012B; do
  if [ ! -f "$CR/$w/filtered_feature_bc_matrix/barcodes.tsv.gz" ]; then
    echo "staged Cell Ranger matrix missing for $w -> staging from the outs tar (read-only on the raw tree)"
    bash jobs/stage_hanrui_cellranger.sh
    break
  fi
done
mkdir -p "$RES/logs"
/usr/bin/time -v python jobs/hanrui_fang/count_guides_hanrui.py \
  --qc-config config/hanrui_fang.yaml \
  --data-root "$DATA" \
  --cellranger-root "$CR" \
  --out-root "$RES" \
  --max-mismatches 1 \
  --n-workers 8 \
  --prior-stats-root results/outputs/hanrui_fang_qc/guide_counts 2>&1 | tee "$RES/logs/03_count_guides.log"
echo "DONE $(date -Is)"
