#!/bin/bash
#SBATCH --job-name=pert_tf
#SBATCH --account=ihc
#SBATCH --partition=ihc         # or whichever partition you use
#SBATCH --nodelist=ihc-l40s-1
#SBATCH --gres=gpu:1
#SBATCH --time=36:00:00          # 30 days
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/reploge-v1.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/reploge-v1.err

cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/

source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh

conda activate perturbseq-pipeline

perturbseq-pipeline run --config config/reploge.yaml


