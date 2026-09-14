#!/bin/bash
#SBATCH --job-name=hf_05_tests
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=48G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/%x_%j.err
# Step 7: run the new dual-guide unit tests first (fast fail), then the whole suite.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_fang/_env.sh
mkdir -p "$RES/logs"
set +e
python -m pytest tests/test_dual_guide_assignment.py -q -p no:cacheprovider 2>&1 | tee "$RES/logs/05_tests_dual_guide.log"
rc1=${PIPESTATUS[0]}
python -m pytest tests -q -p no:cacheprovider 2>&1 | tee "$RES/logs/05_tests_full_suite.log" | tail -40
rc2=${PIPESTATUS[0]}
set -e
echo "dual-guide tests exit=$rc1 ; full suite exit=$rc2"
[ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ]
echo "DONE $(date -Is)"
