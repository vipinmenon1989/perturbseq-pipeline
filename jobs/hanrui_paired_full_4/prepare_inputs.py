#!/usr/bin/env python
"""Iteration 4, step 1 (SLURM only): copy the validated iteration-3 inputs (scaffold-specific guide count
matrices, pair reference, audit record) into the iteration-4 tree with md5 verification and provenance."""
import hashlib, os, shutil, sys
from datetime import datetime
from pathlib import Path
import pandas as pd

PREV, OUT = Path(sys.argv[1]), Path(sys.argv[2])
JOB = os.environ.get("SLURM_JOB_ID", "n/a")


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 22), b""):
            h.update(c)
    return h.hexdigest()


rows = []
for rel in ["inputs/guide_counts", "audit"]:
    for f in sorted((PREV / rel).rglob("*")):
        if f.is_file():
            dst = OUT / rel / f.relative_to(PREV / rel)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dst)
            m1, m2 = md5(f), md5(dst)
            assert m1 == m2, f
            rows.append({"source": str(f), "copy": str(dst), "md5": m1, "identical": m1 == m2, "bytes": f.stat().st_size})
df = pd.DataFrame(rows)
df.to_csv(OUT / "audit" / "iteration4_input_provenance.csv", index=False)
ref = pd.read_csv(OUT / "audit" / "guide_reference_used.csv", dtype=str, keep_default_na=False)
(OUT / "inputs" / "PROVENANCE.md").write_text(
    f"# Iteration-4 inputs\n\nCopied by SLURM job {JOB} on {datetime.now():%Y-%m-%d %H:%M} from `{PREV}` with md5 verification "
    f"({len(df)} files, all identical; `audit/iteration4_input_provenance.csv`).\n\n- guide count matrices: scaffold-specific features "
    f"(iteration-2 counting job 20049321), `inputs/guide_counts/<well>/`\n- pair reference: `audit/guide_reference_used.csv` ({len(ref)} features, "
    f"{int((ref['designed_slot'].str.lower() == 'true').sum())} designed slots)\n- experimental information record and audit tables: `audit/` (iteration 3, unchanged experimental documents)\n")
print(f"copied {len(df)} files; all md5 identical: {bool(df['identical'].all())}")
