#!/bin/bash
#SBATCH --job-name=diabetes_analysis
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --cpus-per-task=48
#SBATCH --mem=256G
#SBATCH --time=08:00:00
#SBATCH --output=results/diabetes_specific/logs/diabetes_analysis_%j.log
#SBATCH --error=results/diabetes_specific/logs/diabetes_analysis_%j.err

set -euo pipefail

# Project directory
PROJECT_DIR="/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline"
cd "${PROJECT_DIR}"

# Create logs directory
mkdir -p results/diabetes_specific/logs

# Activate conda environment
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline

echo "================================================================="
echo "Running Pancreatic Diabetes Perturb-seq Analysis Workflow"
echo "Job ID:    ${SLURM_JOB_ID:-manual}"
echo "Host:      $(hostname)"
echo "CPUs:      ${SLURM_CPUS_PER_TASK:-48}"
echo "Start:     $(date)"
echo "================================================================="

# Execute diabetes workflow
python workflows/diabetes_analysis.py \
    --input ../data/diabetes.h5ad \
    --outdir results/diabetes_specific \
    --n-jobs 48 \
    --seed 123 \
    --n-permutations 1000 \
    --max-cells-per-target 2000 \
    --max-control-cells 5000 \
    --n-modules 6 \
    --n-programs 4

echo "================================================================="
echo "Analysis Completed: $(date)"
echo "================================================================="
