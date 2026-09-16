#!/bin/bash
#SBATCH --job-name=pert_tf_report
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-h200-1
#SBATCH --cpus-per-task=128
#SBATCH --gres=gpu:1
#SBATCH --time=72:00:00
#SBATCH --mem=350G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_3/report_slurm_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_3/report_slurm_%j.err
# Rebuild the full_3 HTML reports (per-run + root) with the pipeline's Jinja renderer, then validate.
cd /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline
source /local/projects-t3/lilab/vmenon/anaconda3/etc/profile.d/conda.sh
conda activate perturbseq-pipeline
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_3/_env.sh
START=$(date -Is)
python -m pytest -q tests/test_pair_mode_pipeline.py -p no:cacheprovider 2>&1 | tail -3
/usr/bin/time -v perturbseq-pipeline rebuild-report --root "$OUT" --previous-run "$PREV" \
  --run HF011A="$OUT/samples/HF011A" --run HF011B="$OUT/samples/HF011B" --run HF012A="$OUT/samples/HF012A" --run HF012B="$OUT/samples/HF012B" --run combined="$OUT/combined" 2>&1 | tee "$OUT/slurm/05_rebuild_report.log" | grep -vE "^\s+(Average|Swaps|Socket|Signals|Page size|File system|Minor|Major|Voluntary|Involuntary)"
set +e
python jobs/hanrui_pair_full_3/validate_report_rebuild.py 2>&1 | tee "$OUT/slurm/05_report_validation.log" | tail -60
rc=${PIPESTATUS[0]}
END=$(date -Is)
{
  echo "# Report rebuild commands (full_3)"; echo; echo "SLURM job ${SLURM_JOB_ID} on $(hostname); start $START; end $END; conda env ${CONDA_DEFAULT_ENV}; python $(python --version 2>&1)"; echo
  echo "## SBATCH script"; echo; echo '```bash'; cat jobs/hanrui_pair_full_3/05_rebuild_report.slurm; echo '```'; echo
  echo "## Commands"; echo; echo '```bash'
  echo "perturbseq-pipeline rebuild-report --root $OUT --previous-run $PREV --run HF011A=$OUT/samples/HF011A --run HF011B=$OUT/samples/HF011B --run HF012A=$OUT/samples/HF012A --run HF012B=$OUT/samples/HF012B --run combined=$OUT/combined"
  echo "python jobs/hanrui_pair_full_3/validate_report_rebuild.py"; echo '```'; echo
  echo "## Git"; echo; echo '```'; git rev-parse --abbrev-ref HEAD; git rev-parse HEAD; git status --short; echo '```'; echo
  echo "## Validation exit code: $rc"; echo; echo "See report_rebuild.md, report_rebuild_validation.txt and slurm/05_report_validation.log."
} > "$OUT/report_rebuild_commands.md"
cp jobs/hanrui_pair_full_3/05_rebuild_report.slurm jobs/hanrui_pair_full_3/validate_report_rebuild.py "$OUT/slurm/"
echo "validation exit=$rc"; echo "DONE $(date -Is)"; exit $rc
