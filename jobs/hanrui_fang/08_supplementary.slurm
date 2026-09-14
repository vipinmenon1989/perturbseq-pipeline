#!/bin/bash
#SBATCH --job-name=hf_08_supplementary
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
#SBATCH --mem=250G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Steps 11-15: supplementary QC / guide / perturbation tables and figures for the five
# runs, per-sample-vs-combined comparison and comparison_report.html.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
mkdir -p "$RES/logs" "$RES/figures" "$RES/tables"
/usr/bin/time -v python jobs/hanrui_fang/supplementary_dual_guide.py 2>&1 | tee "$RES/logs/08_supplementary.log" | grep -vE "^\s+fig " || true
echo "DONE $(date -Is)"
