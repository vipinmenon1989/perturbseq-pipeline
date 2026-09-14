#!/bin/bash
#SBATCH --job-name=hanrui_qc_validate
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=200G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_qc_validate_%j.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_qc_validate_%j.err

# Reopen the production QC outputs and verify the documented contract.
set -euo pipefail
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/
source jobs/_slurm_env.sh
python jobs/validate_qc_outputs.py /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc
