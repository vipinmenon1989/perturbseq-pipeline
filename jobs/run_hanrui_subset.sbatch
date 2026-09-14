#!/bin/bash
#SBATCH --job-name=hanrui_qc_subset
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=16
#SBATCH --time=06:00:00
#SBATCH --mem=120G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_qc_subset_%j.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_qc_subset_%j.err

# Real-data subset validation: HF011A GEX + first 10M reads of HF011AF L004.
set -euo pipefail
source jobs/_slurm_env.sh 2>/dev/null || { cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/ && source jobs/_slurm_env.sh; }
SAMPLES="HF011A" bash jobs/stage_hanrui_cellranger.sh /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc
/usr/bin/time -v perturbseq-pipeline run --config config/hanrui_fang_subset.yaml
