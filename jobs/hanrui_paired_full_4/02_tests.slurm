#!/bin/bash
#SBATCH --job-name=hpf4_02_tests
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --mem=48G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.err
# Step 2: unit / integration tests for the code changes (scaffold-specific counting, multi-construct pair ids,
# resolution details, Markdown report, root report) + validation that the iteration-2 config parses.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_paired_full_4/_env.sh
python -c "from perturbseq_pipeline.config import Config; c=Config.from_yaml('$CFG'); c.validate(); print('config OK:', c.guides.assignment_mode, 'pair_reference =', c.guides.pair_reference)"
set +e
python -m pytest -x -q tests/test_dual_guide_assignment.py tests/test_basic_qc.py tests/test_pair_mode_pipeline.py tests/test_guide_metadata.py tests/test_pipeline.py -p no:cacheprovider 2>&1 | tee "$OUT/slurm/02_tests.log" | tail -30
rc=${PIPESTATUS[0]}
echo "pytest exit=$rc"; echo "DONE $(date -Is)"; exit $rc
