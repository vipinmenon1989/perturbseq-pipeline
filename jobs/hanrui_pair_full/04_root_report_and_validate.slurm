#!/bin/bash
#SBATCH --job-name=hpf_04_report
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --mem=120G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full/slurm/%x_%j.err
# Step 4: root pair-guide report over the five runs, then validation.
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full/_env.sh
IDS=$(grep -oE '^[0-9]{2}=[0-9]+' "$OUT/slurm/job_ids.txt" | cut -d= -f2 | tr '\n' ',' | sed 's/,$//')
perturbseq-pipeline pair-report -c "$CFG" -o "$OUT" --audit-dir "$OUT/audit" --job-ids "$IDS,${SLURM_JOB_ID}" \
  --run HF011A="$OUT/samples/HF011A" --run HF011B="$OUT/samples/HF011B" --run HF012A="$OUT/samples/HF012A" --run HF012B="$OUT/samples/HF012B" --run combined="$OUT/combined"
cp jobs/hanrui_pair_full/*.slurm jobs/hanrui_pair_full/*.py jobs/hanrui_pair_full/_env.sh "$OUT/slurm/"
set +e
python jobs/hanrui_pair_full/validate_pair_full.py 2>&1 | tee "$OUT/slurm/04_validation.log" | tail -60
rc=${PIPESTATUS[0]}
echo "validation exit=$rc"; echo "DONE $(date -Is)"; exit $rc
