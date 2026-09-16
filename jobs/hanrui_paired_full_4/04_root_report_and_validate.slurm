#!/bin/bash
#SBATCH --job-name=hpf4_04_report
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=06:00:00
#SBATCH --mem=160G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_paired_guide_full_4/slurm/%x_%j.err
# Step 4: cross-run tables + provenance (pair-report), full HTML/Markdown reports (rebuild-report), root deliverables, validation.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_paired_full_4/_env.sh
BASE=$(cat "$OUT/slurm/base_commit.txt")
IDS=$(grep -oE '^[0-9]{2}=[0-9]+' "$OUT/slurm/job_ids.txt" | cut -d= -f2 | tr '\n' ',' | sed 's/,$//')
cp jobs/hanrui_paired_full_4/*.slurm jobs/hanrui_paired_full_4/*.py jobs/hanrui_paired_full_4/_env.sh "$OUT/slurm/"
RUNS="--run HF011A=$OUT/samples/HF011A --run HF011B=$OUT/samples/HF011B --run HF012A=$OUT/samples/HF012A --run HF012B=$OUT/samples/HF012B --run combined=$OUT/combined"
perturbseq-pipeline pair-report -c "$CFG" -o "$OUT" --audit-dir "$OUT/audit" --previous-run "$PREV" --base-commit "$BASE" --slurm-dir "$OUT/slurm" --job-ids "$IDS,${SLURM_JOB_ID}" $RUNS
mv "$OUT/report.html" "$OUT/report_textual_backup.html"; mv "$OUT/report.md" "$OUT/report_textual_backup.md"
perturbseq-pipeline rebuild-report --root "$OUT" --previous-run "$PREV" $RUNS 2>&1 | tee "$OUT/slurm/04_rebuild_report.log"
python jobs/hanrui_paired_full_4/finalize_root.py
set +e
python jobs/hanrui_paired_full_4/validate_full_4.py 2>&1 | tee "$OUT/slurm/04_validation.log" | tail -80
rc=${PIPESTATUS[0]}
echo "validation exit=$rc"; echo "DONE $(date -Is)"; exit $rc
