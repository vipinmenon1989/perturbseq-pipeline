from pathlib import Path

import scanpy as sc
import pandas as pd


DATA = Path("../data/diabetes.h5ad")


def main():
    print("=" * 80)
    print("DIABETES H5AD INSPECTION")
    print("=" * 80)

    if not DATA.is_file():
        print(f"ERROR: file not found: {DATA.resolve()}")
        return

    # Backed mode avoids loading the full expression matrix into RAM.
    adata = sc.read_h5ad(DATA, backed="r")

    try:
        print(f"\nFILE: {DATA}")
        print(f"Shape: {adata.shape}")
        print(f"Cells: {adata.n_obs:,}")
        print(f"Genes/features: {adata.n_vars:,}")

        print("\n" + "=" * 80)
        print("EXPRESSION STORAGE")
        print("=" * 80)

        print("X type:", type(adata.X))
        print("Raw slot available:", adata.raw is not None)
        print("Layers:", list(adata.layers.keys()))

        print("\n" + "=" * 80)
        print("OBS COLUMNS")
        print("=" * 80)

        for i, col in enumerate(adata.obs.columns, 1):
            s = adata.obs[col]

            print(
                f"{i:3d}. {col:<35} "
                f"dtype={str(s.dtype):<15} "
                f"unique={s.nunique(dropna=False):,}"
            )

        print("\n" + "=" * 80)
        print("CELLTYPE_2")
        print("=" * 80)

        if "celltype_2" in adata.obs.columns:
            print(
                adata.obs["celltype_2"]
                .value_counts(dropna=False)
                .to_string()
            )
        else:
            print("WARNING: obs['celltype_2'] does not exist.")

        print("\n" + "=" * 80)
        print("CANDIDATE PERTURBATION / GUIDE COLUMNS")
        print("=" * 80)

        keywords = [
            "gene",
            "target",
            "guide",
            "perturb",
            "crispr",
            "grna",
            "sgrna",
            "condition",
            "treatment",
        ]

        candidates = [
            col
            for col in adata.obs.columns
            if any(k in col.lower() for k in keywords)
        ]

        if not candidates:
            print("No obvious candidate columns found.")
        else:
            for col in candidates:
                print(f"\n--- obs['{col}'] ---")
                print("Unique values:", adata.obs[col].nunique(dropna=False))
                print(
                    adata.obs[col]
                    .value_counts(dropna=False)
                    .head(20)
                    .to_string()
                )

        print("\n" + "=" * 80)
        print("POSSIBLE BATCH / DONOR / SAMPLE COLUMNS")
        print("=" * 80)

        keywords = [
            "batch",
            "donor",
            "patient",
            "sample",
            "replicate",
            "library",
            "individual",
        ]

        candidates = [
            col
            for col in adata.obs.columns
            if any(k in col.lower() for k in keywords)
        ]

        if not candidates:
            print("No obvious batch/donor/sample columns found.")
        else:
            for col in candidates:
                print(f"\n--- obs['{col}'] ---")
                print("Unique values:", adata.obs[col].nunique(dropna=False))
                print(
                    adata.obs[col]
                    .value_counts(dropna=False)
                    .head(20)
                    .to_string()
                )

        print("\n" + "=" * 80)
        print("VAR COLUMNS")
        print("=" * 80)

        for i, col in enumerate(adata.var.columns, 1):
            print(
                f"{i:3d}. {col:<35} "
                f"dtype={str(adata.var[col].dtype):<15} "
                f"unique={adata.var[col].nunique(dropna=False):,}"
            )

        print("\n" + "=" * 80)
        print("EMBEDDINGS / OBSP / UNS")
        print("=" * 80)

        print("obsm:", list(adata.obsm.keys()))
        print("obsp:", list(adata.obsp.keys()))
        print("uns:", list(adata.uns.keys()))

        print("\n" + "=" * 80)
        print("FIRST 5 OBS ROWS")
        print("=" * 80)

        with pd.option_context(
            "display.max_columns", None,
            "display.width", 250
        ):
            print(adata.obs.head().to_string())

    finally:
        adata.file.close()


if __name__ == "__main__":
    main()
