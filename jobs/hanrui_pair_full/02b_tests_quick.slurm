#!/bin/bash
#SBATCH --job-name=hpf_02b_tests
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --mem=48G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.err
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full/_env.sh
python -m pytest tests/test_pair_mode_pipeline.py tests/test_dual_guide_assignment.py tests/test_pipeline.py -q -p no:cacheprovider 2>&1 | tee "$OUT/slurm/02b_tests_after_barcode_fix.log" | tail -8
