#!/bin/bash
#SBATCH --job-name=hpf2_00_docs
#SBATCH --account=ihc
#SBATCH --partition=ihc
#SBATCH --nodelist=ihc-grid-1-1-1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --mem=8G
#SBATCH --output=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/%x_%j.out
#SBATCH --error=/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/Hanrui_Fang_pair_guide_full_2/slurm/%x_%j.err
# Step 0: dump the newly supplied Excel / Word documents to text (Excel/Word parsing is not allowed on the login node).
# CPU-only -> ihc-grid-1-1-1 (the h200 node rejects CPU-only allocations without --gres).
source /local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/jobs/hanrui_pair_full_2/_env.sh
python -c "import docx" 2>/dev/null || pip install --quiet python-docx
python jobs/hanrui_pair_full_2/dump_documents.py "$DATA" "$OUT/audit/documents"
echo "DONE $(date -Is)"
