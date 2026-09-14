#!/bin/bash
#SBATCH --job-name=hpf_02_tests
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=48G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.err
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full/_env.sh
set +e
python -m pytest tests/test_dual_guide_assignment.py tests/test_pair_mode_pipeline.py -q -p no:cacheprovider -x 2>&1 | tee "$OUT/slurm/02_tests_pair.log" | tail -30
rc1=${PIPESTATUS[0]}
python -m pytest tests -q -p no:cacheprovider 2>&1 | tee "$OUT/slurm/02_tests_full_suite.log" | tail -15
rc2=${PIPESTATUS[0]}
echo "pair tests exit=$rc1 ; full suite exit=$rc2"
[ "$rc1" -eq 0 ] && [ "$rc2" -eq 0 ]
