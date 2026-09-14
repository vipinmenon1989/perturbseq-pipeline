#!/bin/bash
#SBATCH --job-name=tests_main
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=48G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/tests_main_%j.log
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/logs/tests_main_%j.err
# pytest suite of origin/main (read-only worktree), executed with main's sources on PYTHONPATH.
set -euo pipefail
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
source jobs/_slurm_env.sh
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/../perturbseq-pipeline-main
export PYTHONPATH=$PWD/src
python -c "import perturbseq_pipeline; print('testing', perturbseq_pipeline.__file__)"
python -m pytest tests -q -p no:cacheprovider 2>&1 | tail -60
