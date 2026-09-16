#!/bin/bash
#SBATCH --job-name=hpf4_05_validate
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
#SBATCH --mem=64G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.err
# Re-run only the validation checklist (validator now parses the 100+ MB reports with huge_tree=True).
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_paired_full_4/_env.sh
cp jobs/hanrui_paired_full_4/validate_full_4.py jobs/hanrui_paired_full_4/05_revalidate.slurm "$OUT/slurm/"
set +e
python jobs/hanrui_paired_full_4/validate_full_4.py 2>&1 | tee "$OUT/slurm/05_validation.log" | tail -40
rc=${PIPESTATUS[0]}
{ echo; echo "## Re-validation (job ${SLURM_JOB_ID}, $(date -Is))"; echo; echo "Validator re-run after fixing its HTML parser limit (huge_tree); exit code $rc; see final_validation.txt."; } >> "$OUT/execution_commands.md"
cp "$OUT/slurm/05_validation.log" "$OUT/logs/"
echo "validation exit=$rc"; echo "DONE $(date -Is)"; exit $rc
