#!/bin/bash
#SBATCH --job-name=hanrui_design_audit
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --mem=120G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_library_design_audit/slurm/slurm_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_library_design_audit/slurm/slurm_%j.err
# Allocation note: the task template names ihc-h200-1 with 128 CPUs + 1 GPU; this audit is CPU/IO-only
# (Excel, FASTQ sampling, HDF5 obs, text), so it runs on the CPU node ihc-grid-1-1-1 (the GPU node rejects
# CPU-only allocations without --gres, and a GPU would be idle). Documented in provenance.json.
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
export MPLBACKEND=Agg PYTHONUNBUFFERED=1
echo "HOST: $(hostname) DATE: $(date -Is) JOB: $SLURM_JOB_ID ENV: $CONDA_DEFAULT_ENV GIT: $(git rev-parse --abbrev-ref HEAD) $(git rev-parse HEAD)"
/usr/bin/time -v python jobs/hanrui_design_audit/design_audit.py
cp jobs/hanrui_design_audit/design_audit.py jobs/hanrui_design_audit/hanrui_design_audit.slurm results/Hanrui_Fang_library_design_audit/slurm/
echo "DONE $(date -Is)"
