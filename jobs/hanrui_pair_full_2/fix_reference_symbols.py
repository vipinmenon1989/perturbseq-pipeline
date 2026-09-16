#!/usr/bin/env python
"""Apply the current HGNC symbol map to audit/pair_guide_reference.csv (target_symbol) in place, keeping the
empirical columns appended by the counting step. CBWD1 was renamed ZNG1A in the GRCh38-2024-A annotation."""
import sys
from pathlib import Path
import pandas as pd
SYMBOL_FIX = {"CEBPb": "CEBPB", "C6orf106": "ILRUN", "CCBL2": "KYAT3", "CBWD1": "ZNG1A"}
p = Path(sys.argv[1])
ref = pd.read_csv(p, dtype=str, keep_default_na=False)
base = ref["target_gene"].str.replace(r"\s*\(rs\d+\)\s*$", "", regex=True)
new = base.map(lambda x: SYMBOL_FIX.get(x, x))
new[ref["is_non_targeting"].str.lower() == "true"] = "ntc"
changed = int((ref["target_symbol"] != new).sum())
ref["target_symbol"] = new
ref["target_symbol_source"] = "design label; HGNC renames applied: " + "; ".join(f"{k}->{v}" for k, v in SYMBOL_FIX.items()) + "; SNP-locus labels -> gene symbol"
ref.to_csv(p, index=False)
print(f"target_symbol updated for {changed} feature rows; symbols: {sorted(set(new))}")
