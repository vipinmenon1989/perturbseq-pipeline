#!/bin/bash
#SBATCH --job-name=hf_01_read_audit
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 2: read every completed audit report (Markdown, text, CSV, log, validation)
# under data_audit/ and concatenate them into a single read log that the
# audit_report_summary.md is written from. Read-only with respect to the raw data.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
AUDIT=$DATA/data_audit
mkdir -p "$RES/pipeline_comparison" "$RES/logs"
LOG=$RES/logs/audit_report_read.log
: > "$LOG"
{
  echo "# Audit report read log"
  echo "job=${SLURM_JOB_ID:-none} host=$(hostname) date=$(date -Is)"
  echo "audit_dir=$AUDIT"
  echo
  echo "## Inventory (find, sorted)"
  find "$AUDIT" -type f | sort | while read -r f; do
    printf '%12d  %s  %s\n' "$(stat -c %s "$f")" "$(stat -c %y "$f" | cut -d. -f1)" "${f#$AUDIT/}"
  done
  echo
  echo "## Report contents"
  # Markdown / text / CSV / TSV / log / validation reports, in a stable order.
  find "$AUDIT" -type f \( -name '*.md' -o -name '*.txt' -o -name '*.csv' -o -name '*.tsv' \
        -o -name '*.log' -o -name '*.err' -o -name '*.json' -o -name '*.yaml' -o -name '*.yml' \) \
        ! -path '*/extracted/*' ! -path '*/tar_listings/*' | sort | while read -r f; do
    sz=$(stat -c %s "$f")
    echo
    echo "=================================================================="
    echo "FILE: ${f#$AUDIT/}  (${sz} bytes)"
    echo "=================================================================="
    if [ "$sz" -gt 400000 ]; then
      echo "[large file: first 400 lines shown]"
      head -n 400 "$f"
    else
      cat "$f"
    fi
  done
  echo
  echo "## Large / binary artefacts not inlined"
  find "$AUDIT" -type f \( -path '*/extracted/*' -o -path '*/tar_listings/*' -o -name '*.html' -o -name '*.png' -o -name '*.pdf' -o -name '*.py' -o -name '*.sbatch' \) | sort | while read -r f; do
    printf '%12d  %s\n' "$(stat -c %s "$f")" "${f#$AUDIT/}"
  done
  echo
  echo "## Raw-tree checksum guard (mtimes of the raw sample directories, for later no-modification check)"
  for s in HF011A HF011AF HF011B HF011BF HF012A HF012AF HF012B HF012BF web_summaries; do
    printf '%s  %s\n' "$(stat -c %y "$DATA/$s" | cut -d. -f1)" "$s"
  done
  find "$DATA" -path "$DATA/data_audit" -prune -o -type f -printf '%T@ %s %p\n' | sort -k3 > "$RES/logs/raw_tree_manifest_before.txt"
  echo "raw file manifest written: $RES/logs/raw_tree_manifest_before.txt ($(wc -l < "$RES/logs/raw_tree_manifest_before.txt") files)"
  echo "DONE $(date -Is)"
} | tee -a "$LOG" > /dev/null
echo "wrote $LOG ($(wc -l < "$LOG") lines)"
