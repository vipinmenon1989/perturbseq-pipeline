import scanpy as sc
import pandas as pd

a = sc.read_h5ad("../data/diabetes.h5ad", backed="r")

print("\n=== GENOTYPE COUNTS ===")
print(a.obs["genotype"].value_counts(dropna=False).to_string())

print("\n=== GUIDE -> GENOTYPE MAPPING ===")
mapping = (
    a.obs[["sgrna", "gene", "genotype"]]
    .drop_duplicates()
    .sort_values(["genotype", "sgrna"])
)
print(mapping.to_string(index=False))

print("\n=== NUMBER OF GUIDES PER GENOTYPE ===")
print(
    mapping.groupby("genotype")["sgrna"]
    .nunique()
    .sort_values(ascending=False)
    .to_string()
)

print("\n=== TIME POINT COUNTS ===")
print(a.obs["time_point"].value_counts(dropna=False).sort_index().to_string())

print("\n=== ORIG.IDENT COUNTS ===")
print(a.obs["orig.ident"].value_counts(dropna=False).to_string())

print("\n=== GENOTYPE x TIME POINT ===")
print(pd.crosstab(a.obs["genotype"], a.obs["time_point"]).to_string())

print("\n=== CELLTYPE_2 x TIME POINT ===")
print(pd.crosstab(a.obs["celltype_2"], a.obs["time_point"]).to_string())

print("\n=== GENOTYPE x ORIG.IDENT ===")
print(pd.crosstab(a.obs["genotype"], a.obs["orig.ident"]).to_string())

a.file.close()
