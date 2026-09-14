#!/bin/bash
#SBATCH --job-name=hf_09_validate
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --mem=150G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 17: final validation of all outputs.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
set +e
python jobs/hanrui_fang/validate_dual_guide_outputs.py 2>&1 | tee "$RES/logs/09_validate.log"
rc=${PIPESTATUS[0]}
echo "validation exit=$rc"
echo "DONE $(date -Is)"
exit $rc
