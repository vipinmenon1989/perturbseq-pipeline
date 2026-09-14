#!/bin/bash
#SBATCH --job-name=hanrui_qc
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=128
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_qc_%j.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/hanrui_qc_%j.err

# Full Hanrui Fang basic QC: 4 GEX wells + 4 guide libraries, stop after QC.
# The GPU request only follows the cluster's job template; no QC algorithm
# in this stage uses the GPU (compute.backend: cpu).
set -euo pipefail
mkdir -p /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/
source jobs/_slurm_env.sh
bash jobs/stage_hanrui_cellranger.sh /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/outputs/hanrui_fang_qc
/usr/bin/time -v perturbseq-pipeline run --config config/hanrui_fang.yaml
