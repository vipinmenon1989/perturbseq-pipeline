#!/bin/bash
#SBATCH --job-name=hpf3_04_report
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00
#SBATCH --mem=120G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_3/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_3/slurm/%x_%j.err
# Step 4: root report (21 sections, Markdown + HTML), run manifest, execution record, previous-vs-new comparison, validation.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_3/_env.sh
BASE=$(cat "$OUT/slurm/base_commit.txt" 2>/dev/null || echo 6a2f32bf769688da9c855d1824e9b30f665f3ad1)
IDS=$(grep -oE '^[0-9]{2}=[0-9]+' "$OUT/slurm/job_ids.txt" | cut -d= -f2 | tr '\n' ',' | sed 's/,$//')
cp jobs/hanrui_pair_full_3/*.slurm jobs/hanrui_pair_full_3/*.py jobs/hanrui_pair_full_3/_env.sh "$OUT/slurm/"
perturbseq-pipeline pair-report -c "$CFG" -o "$OUT" --audit-dir "$OUT/audit" --previous-run "$PREV" --base-commit "$BASE" --slurm-dir "$OUT/slurm" --job-ids "$IDS,${SLURM_JOB_ID}" \
  --run HF011A="$OUT/samples/HF011A" --run HF011B="$OUT/samples/HF011B" --run HF012A="$OUT/samples/HF012A" --run HF012B="$OUT/samples/HF012B" --run combined="$OUT/combined"
set +e
python jobs/hanrui_pair_full_3/validate_pair_full_3.py 2>&1 | tee "$OUT/slurm/04_validation.log" | tail -80
rc=${PIPESTATUS[0]}
echo "validation exit=$rc"; echo "DONE $(date -Is)"; exit $rc
