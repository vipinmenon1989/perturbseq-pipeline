#!/bin/bash
#SBATCH --job-name=hanrui_perturbseq
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=128
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/Hanrui_fang_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/Hanrui_fang_%j.err
# Final core-workflow run (dev): combined H5AD input, default QC/clustering/perturbation, advanced modules disabled.
set -euo pipefail
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
source jobs/_slurm_env.sh
/usr/bin/time -v perturbseq-pipeline run --config config/Hanrui_fang.yaml
