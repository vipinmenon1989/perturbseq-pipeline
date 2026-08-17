from pathlib import Path

import scanpy as sc


DATA_DIR = Path("../data")


def main():
    files = {
        DATA_DIR / "KOLF_Pan_Genome_QC_Filtered.h5ad": "gene_target",
        DATA_DIR / "ReplogleWeissman2022_K562_essential.h5ad": "gene",
    }

    for path, column in files.items():
        print(f"\nFILE: {path}")

        if not path.is_file():
            print("ERROR: file not found")
            continue

        # Read metadata without loading the full expression matrix.
        adata = sc.read_h5ad(path, backed="r")

        print("Shape:", adata.shape)
        print("Cells:", adata.n_obs)
        print("Genes:", adata.n_vars)
        print("Raw slot available:", adata.raw is not None)
        print("Layers:", list(adata.layers.keys()))
        print(f"Column '{column}' exists:", column in adata.obs.columns)

        if column in adata.obs.columns:
            print(f"Top values in obs['{column}']:")
            print(adata.obs[column].value_counts(dropna=False).head(10))

        print("obs columns:", list(adata.obs.columns))
        print("var columns:", list(adata.var.columns))
        print("obsm keys:", list(adata.obsm.keys()))
        print("uns keys:", list(adata.uns.keys()))

        adata.file.close()


if __name__ == "__main__":
    main()
