#!/bin/bash
# Extract the Cell Ranger filtered matrices (and small summaries) from the
# outs tars into the QC output tree. Idempotent; never writes into the raw
# HF01* directories. Meant to be sourced/run inside a SLURM job.
set -euo pipefail
DATA=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/data/260720_HANRUI_FANG_2_HUMAN_10X
OUT=${1:-/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc}
SAMPLES=${SAMPLES:-"HF011A HF011B HF012A HF012B"}
for S in $SAMPLES; do
  DEST="$OUT/cellranger/$S"
  if [[ -s "$DEST/filtered_feature_bc_matrix.h5" ]]; then
    echo "[stage] $S: filtered_feature_bc_matrix.h5 already present"
    continue
  fi
  TAR=$(ls "$DATA/$S"/analysis/*/"${S}_cellranger_count_outs.tar")
  echo "[stage] $S: extracting from $TAR"
  mkdir -p "$DEST"
  tar -xf "$TAR" -C "$DEST" --strip-components=1 --wildcards \
      "${S}_cellranger_count_outs/filtered_feature_bc_matrix.h5" \
      "${S}_cellranger_count_outs/metrics_summary.csv" \
      "${S}_cellranger_count_outs/web_summary.html"
  ls -la "$DEST"
done
