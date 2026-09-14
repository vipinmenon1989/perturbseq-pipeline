#!/bin/bash
#SBATCH --job-name=perturbseq_tests
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=48G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/tests_%j.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/tests_%j.err

# Full pytest suite (existing tests + basic QC tests) off the login node.
set -euo pipefail
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/
source jobs/_slurm_env.sh
python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -80
