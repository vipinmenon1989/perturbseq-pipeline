"""Dump every worksheet of every workbook and every paragraph/table of every Word document under
web_summaries to plain text so the analyst can read them (runs under SLURM only)."""
import sys, json, zipfile, re
from pathlib import Path
import pandas as pd
DATA = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
prov = {}
for xl in sorted(DATA.rglob("*.xls*")):
    if "/data_audit/" in str(xl): continue
    sheets = pd.read_excel(xl, sheet_name=None, header=None, dtype=str)
    prov[str(xl)] = {"type": "xlsx", "sheets": {}}
    try:
        z = zipfile.ZipFile(xl); core = z.read("docProps/core.xml").decode("utf8", "replace")
        prov[str(xl)]["core_xml"] = core
    except Exception as e:
        prov[str(xl)]["core_xml"] = f"ERR {e}"
    for name, df in sheets.items():
        df = df.dropna(how="all").dropna(axis=1, how="all")
        p = OUT / f"{xl.stem}__{re.sub(r'[^A-Za-z0-9_.-]+','_',name)}.tsv"
        df.to_csv(p, sep="\t", index=False, header=False)
        prov[str(xl)]["sheets"][name] = {"rows": int(df.shape[0]), "cols": int(df.shape[1]), "dump": str(p),
                                         "head": df.head(8).fillna("").values.tolist()}
        print(f"== {xl.name} :: sheet '{name}' {df.shape}")
        print(df.head(12).fillna("").to_string(index=False, header=False))
for dx in sorted(DATA.rglob("*.doc*")):
    if "/data_audit/" in str(dx): continue
    import docx
    d = docx.Document(dx)
    lines = []
    for i, para in enumerate(d.paragraphs):
        if para.text.strip():
            lines.append(f"[para {i} style={para.style.name}] {para.text}")
    for ti, t in enumerate(d.tables):
        lines.append(f"[table {ti}] {len(t.rows)} rows x {len(t.columns)} cols")
        for ri, row in enumerate(t.rows):
            lines.append(f"[table {ti} row {ri}] " + " | ".join(c.text.replace("\n", " ") for c in row.cells))
    z = zipfile.ZipFile(dx)
    core = z.read("docProps/core.xml").decode("utf8", "replace") if "docProps/core.xml" in z.namelist() else ""
    raw_xml = z.read("word/document.xml").decode("utf8", "replace")
    p = OUT / f"{dx.stem}__text.txt"
    p.write_text("\n".join(lines) + "\n\n[core.xml]\n" + core + "\n")
    (OUT / f"{dx.stem}__document.xml").write_text(raw_xml)
    prov[str(dx)] = {"type": "docx", "n_paragraphs": len(d.paragraphs), "n_tables": len(d.tables), "dump": str(p), "core_xml": core}
    print(f"== {dx.name}: {len(d.paragraphs)} paragraphs, {len(d.tables)} tables")
    print("\n".join(lines))
(OUT / "document_dump_provenance.json").write_text(json.dumps(prov, indent=2, default=str))
