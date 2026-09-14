#!/bin/bash
#SBATCH --job-name=hanrui_dev_h5ad
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=32

#SBATCH --time=24:00:00
#SBATCH --mem=200G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_dev_h5ad_%j.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_dev_h5ad_%j.err
set -euo pipefail
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
source jobs/_slurm_env.sh
/usr/bin/time -v perturbseq-pipeline run --config config/Hanrui_fang_dev_default.yaml
