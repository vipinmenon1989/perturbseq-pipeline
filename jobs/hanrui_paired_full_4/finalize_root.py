#!/usr/bin/env python
"""Iteration 4 root deliverables: root figures/ (top-six per analysis + overview figures of the combined run), tables/
(cross-run + all-target tables), logs/ (SLURM + run logs), README notes."""
import json, os, shutil, sys
from datetime import datetime
from pathlib import Path
import pandas as pd

REPO = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline")
OUT = REPO / "results" / "Hanrui_Fang_paired_guide_full_4"
WELLS = ["HF011A", "HF011B", "HF012A", "HF012B"]
comb = OUT / "combined"
summ = json.load(open(OUT / "report_rebuild_summary.json"))
man = pd.read_csv(comb / "tables" / "figure_manifest.csv", dtype=str, keep_default_na=False)
# figures: overview (in_report) figures of every section + top-six per-target figures
copied = []
for _, r in man.iterrows():
    sec, name, path = r["section"], r["name"], Path(r["path"])
    if not path.is_file():
        continue
    keep = str(r["in_report"]).lower() == "true" and "/" not in sec
    for key, targets in summ["root"]["top6"].items():
        prefix = {"perturbation": "perturbation_", "enrichment": "enrichment_", "ps_score": "ps_quadrant_", "lochness": "lochness_"}.get(key)
        if prefix and any(name == __import__("re").sub(r"[^A-Za-z0-9._-]+", "_", f"{prefix}{t}").strip("_") for t in targets):
            keep = True
    if keep:
        dst = OUT / "figures" / sec / path.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dst)
        copied.append({"section": sec, "name": name, "source": str(path), "copy": str(dst)})
pd.DataFrame(copied).to_csv(OUT / "figures" / "root_figures_index.csv", index=False)
# tables: every combined all-target table + top-six tables (cross-run tables are already in tables/)
for p in sorted((comb / "tables").glob("*.csv")):
    shutil.copy2(p, OUT / "tables" / f"combined__{p.name}")
for w in WELLS:
    for n in ("pair_perturbation_primary", "ps_score", "lochness", "perturbation_distance", "cofunctional_modules", "module_status", "pair_assignment_per_lane"):
        p = OUT / "samples" / w / "tables" / f"{n}.csv"
        if p.is_file():
            shutil.copy2(p, OUT / "tables" / f"{w}__{n}.csv")
# logs
(OUT / "logs").mkdir(exist_ok=True)
for p in list(REPO.glob("hanrui_fang_full_4_*.out")) + list(REPO.glob("hanrui_fang_full_4_*.err")) + list((OUT / "slurm").glob("*.log")) + list((OUT / "slurm").glob("*.out")) + list((OUT / "slurm").glob("*.err")):
    shutil.copy2(p, OUT / "logs" / p.name)
for k in ["combined"] + WELLS:
    d = comb if k == "combined" else OUT / "samples" / k
    if (d / "logs" / "run.log").is_file():
        shutil.copy2(d / "logs" / "run.log", OUT / "logs" / f"{k}_run.log")
# name mapping tables
maps = list(OUT.rglob("*_column_name_mapping.csv"))
if maps:
    pd.concat([pd.read_csv(m).assign(file=str(m)) for m in maps], ignore_index=True).to_csv(OUT / "tables" / "column_name_mapping_all_runs.csv", index=False)
# module status
ms = OUT / "tables" / "module_status_all_runs.csv"
readme = (OUT / "README.md").read_text() if (OUT / "README.md").is_file() else "# Hanrui_Fang_paired_guide_full_4\n"
readme += f"""
## Iteration 4 additions ({datetime.now():%Y-%m-%d})

- All optional perturbation modules enabled (enrichment, co-functional modules / programs, PS score, lochNESS, energy distance + MMD, perturbation distance space, meta table). Module completion: `tables/module_status_all_runs.csv`.
- `report.html` / `report.md`: root full report (pipeline Jinja renderer, `rebuild-report`); each run has its own `report.html` / `report.md`; textual builders kept as `report_textual_backup.*`.
- `figures/`: overview figures of the combined run plus the best-six per-target figures of every analysis (`figures/root_figures_index.csv`); `tables/`: cross-run tables, `combined__*` all-target tables, `<well>__*` per-well tables, `top6_*` selections (inside each run's tables/), `column_name_mapping_all_runs.csv`.
- `logs/`: SLURM stdout/stderr, per-run logs, `run_times.txt`; `config/`: the exact configuration; `inputs/`: md5-verified copies of the iteration-3 guide matrices; `audit/`: iteration-3 experimental information record and pair reference.
"""
(OUT / "README.md").write_text(readme)
print(f"root figures copied: {len(copied)}; name-mapping files: {len(maps)}")
