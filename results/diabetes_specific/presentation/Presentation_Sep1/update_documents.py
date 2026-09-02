# -*- coding: utf-8 -*-
import re

def update_file(filename, replacements):
    with open(filename, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(filename, 'w') as f:
        f.write(content)
    print(f'Updated {filename}')

# 1. Update WIP_scientific_reading.md
wip_replacements = [
    ("orthogonal coordinates", "complementary phenotype dimensions"),
    ("orthogonal, complementary dimensions", "complementary, partially coupled dimensions"),
    ("orthogonal or coupled biological dimensions", "complementary or partially coupled biological dimensions"),
    ("three orthogonal, complementary coordinates", "three complementary, partially coupled coordinates"),
    ("three orthogonal coordinates", "three complementary coordinates"),
    ("orthogonal dimensions", "complementary dimensions"),
    ("Energy Distance = 0.3129", "Energy Distance = 13.6337 (MMD = 0.3129)"),
    ("Energy Distance = 0.2307", "Energy Distance = 10.4732 (MMD = 0.2307)"),
    ("Energy Distance = 0.2087", "Energy Distance = 9.3204 (MMD = 0.2087)"),
    ("Energy Distance = 0.2034", "Energy Distance = 8.9955 (MMD = 0.2034)"),
    ("Energy Distance = 0.1854", "Energy Distance = 7.9693 (MMD = 0.1854)"),
    ("Energy Distance = 0.1590", "Energy Distance = 9.7045 (MMD = 0.1590)"),
    ("Energy Distance = 0.1255", "Energy Distance = 5.8760 (MMD = 0.1255)"),
    ("Energy Distance = 0.1262", "Energy Distance = 5.6360 (MMD = 0.1262)"),
    ("Energy Distance = 0.1227", "Energy Distance = 5.6227 (MMD = 0.1227)"),
    ("Energy Distance = 0.1063", "Energy Distance = 5.4466 (MMD = 0.1063)"),
    ("Energy Distance = 0.0381", "Energy Distance = 1.6372 (MMD = 0.0381)"),
    ("Energy Distance = 0.0386", "Energy Distance = 1.8385 (MMD = 0.0386)"),
    ("Energy Distance = 0.0402", "Energy Distance = 1.7656 (MMD = 0.0402)"),
    ("Energy Distance = 0.0416", "Energy Distance = 2.0519 (MMD = 0.0416)"),
    ("Energy Distance (0.038)", "Energy Distance (1.637, MMD 0.038)"),
    ("Peak lochNESS = +13.740", "dominant celltype lochNESS = +13.740 (Peak cell lochNESS = +18.307)"),
    ("Peak lochNESS = +13.625", "dominant celltype lochNESS = +13.625 (Peak cell lochNESS = +25.564)"),
    ("Peak lochNESS = +4.530", "dominant celltype lochNESS = +4.530 (Peak cell lochNESS = +37.059)"),
    ("Peak lochNESS = +4.129", "dominant celltype lochNESS = +4.129 (Peak cell lochNESS = +9.820)"),
    ("Peak lochNESS = +3.304", "dominant celltype lochNESS = +3.304 (Peak cell lochNESS = +7.969)"),
    ("Peak lochNESS = +3.084", "dominant celltype lochNESS = +3.084 (Peak cell lochNESS = +9.326)"),
    ("phenotype-aware foundation models", "phenotype-aware perturbation prediction models")
]
update_file('WIP_scientific_reading.md', wip_replacements)

# 2. Update pertTF_scientific_reading.md
pert_replacements = [
    ("foundation model", "context-aware perturbation model"),
    ("Foundation model", "Context-aware perturbation model"),
    ("Macro F1 = 0.985, AUPR = 0.998, Accuracy = 0.987, outperforming scGPT (F1 = 0.932, AUPR = 0.945), scFoundation (F1 = 0.918, AUPR = 0.931), and Geneformer (F1 = 0.904, AUPR = 0.912)",
     "Macro F1 > 0.98, AUPR > 0.99, Accuracy > 0.98 (approx. from Fig. 1c), outperforming scGPT (F1 ~ 0.93), scFoundation (F1 ~ 0.92), and Geneformer (F1 ~ 0.90)"),
    ("Macro F1 = 0.842, AUPR = 0.887, Accuracy = 0.856, whereas scGPT achieved Macro F1 = 0.612, AUPR = 0.654",
     "Macro F1 ~ 0.84, AUPR ~ 0.88, Accuracy ~ 0.85 (approx. from Fig. 1d), whereas scGPT achieved Macro F1 ~ 0.61, AUPR ~ 0.65"),
    ("Pearson $r = 0.88$ for *PDX1*, $r = 0.84$ for *TADA2B*, $r = 0.82$ for *GATA6*",
     "Pearson $r \\approx 0.88$ for *PDX1*, $r \\approx 0.84$ for *TADA2B*, $r \\approx 0.82$ for *GATA6* (approx. from Fig. 2d)"),
    ("AUC = 0.86 vs AUC = 0.64", "AUC ~ 0.86 vs AUC ~ 0.64 (approx. from Fig. 2e)"),
    ("Cosine Similarity = 0.912 vs scGPT = 0.741, GEARS = 0.682, scFoundation = 0.715",
     "Cosine Similarity ~ 0.91 vs scGPT ~ 0.74, GEARS ~ 0.68, scFoundation ~ 0.71 (approx. from Fig. 3b)"),
    ("PCC-delta = 0.724 (pertTF) vs 0.481 (scGPT) vs 0.392 (GEARS)",
     "PCC-delta ~ 0.72 (pertTF) vs ~ 0.48 (scGPT) vs ~ 0.39 (GEARS) (approx. from Fig. 3b)"),
    ("DE-direction matching = 84.6% (pertTF) vs 63.2% (scGPT)",
     "DE-direction matching ~ 85% (pertTF) vs ~ 63% (scGPT) (approx. from Fig. 3b)"),
    ("Average Cosine Similarity = 0.864 (pertTF) vs 0.698 (scGPT) vs 0.642 (GEARS)",
     "Average Cosine Similarity ~ 0.86 (pertTF) vs ~ 0.70 (scGPT) vs ~ 0.64 (GEARS) (approx. from Fig. 3c)"),
    ("Cosine Similarity = 0.812 and PCC-delta = 0.615, significantly exceeding scGPT (Cosine = 0.594, PCC = 0.341)",
     "Cosine Similarity ~ 0.81 and PCC-delta ~ 0.61 (approx. from Fig. 3d), exceeding scGPT (Cosine ~ 0.59, PCC ~ 0.34)"),
    ("Cosine Similarity = 0.892 vs scGPT = 0.684, scFoundation = 0.697",
     "Cosine Similarity ~ 0.89 vs scGPT ~ 0.68, scFoundation ~ 0.70 (approx. from Fig. 4b)"),
    ("Pearson $r = 0.781$ (pertTF) vs $r = 0.512$ (scGPT)",
     "Pearson $r \\approx 0.78$ (pertTF) vs $r \\approx 0.51$ (scGPT) (approx. from Fig. 4d)"),
    ("3.8-fold in T2D donors", "~3.8-fold in T2D donors (approx. from Fig. 5d, $p < 0.0001$)"),
    ("4.2-fold depletion", "marked depletion (approx. from Fig. 5e)"),
    ("78.4% of knockdown cells as *RFX6*-perturbed (versus <4.1% in non-targeting controls), and predicted cell embedding shifts with Cosine Similarity = 0.873",
     "~78% of knockdown cells as *RFX6*-perturbed (versus <5% in controls; approx. from Fig. 5g), with Cosine Similarity ~ 0.87 (Fig. 5h)")
]
update_file('pertTF_scientific_reading.md', pert_replacements)

# 3. Update Master_Scientific_Story.md
story_replacements = [
    ("orthogonal coordinates", "complementary phenotype dimensions"),
    ("orthogonal", "complementary"),
    ("Orthogonal", "Complementary"),
    ("foundation models", "perturbation prediction models"),
    ("foundation model", "context-aware perturbation model"),
    ("phenotype-aware foundation models", "phenotype-aware perturbation models"),
    ("Cosine Sim = 0.912 and PCC-delta = 0.724", "Cosine Sim ~ 0.91 and PCC-delta ~ 0.72 (approx. from Fig. 3b)"),
    ("mean Cosine = 0.864", "mean Cosine ~ 0.86 (approx. from Fig. 3c)"),
    ("Cosine = 0.812", "Cosine ~ 0.81 (approx. from Fig. 3d)"),
    ("Cosine Sim = 0.892", "Cosine Sim ~ 0.89 (approx. from Fig. 4b)"),
    ("3.8-fold", "~3.8-fold (approx. from Fig. 5d)"),
    ("78.4% accuracy", "~78% accuracy (approx. from Fig. 5g)"),
    ("Energy Distance (0.3129 in *PDX1het*)", "Energy Distance (13.6337, MMD 0.3129 in *PDX1het*)"),
    ("Energy Distance = 0.1590", "Energy Distance = 9.7045 (MMD = 0.1590)"),
    ("Energy Distance = 0.1063", "Energy Distance = 5.4466 (MMD = 0.1063)"),
    ("Peak lochNESS = +13.740", "dominant celltype lochNESS = +13.740 (Peak = +18.307)")
]
update_file('Master_Scientific_Story.md', story_replacements)

# 4. Update Case_Study_Map.md
case_replacements = [
    ("orthogonal", "complementary"),
    ("Orthogonal", "Complementary"),
    ("foundation model", "context-aware perturbation model"),
    ("PDX1het = 0.3129", "PDX1het = 13.6337 (MMD = 0.3129)"),
    ("Energy Distance = 0.1590", "Energy Distance = 9.7045 (MMD = 0.1590)"),
    ("Energy Distance = 0.1063", "Energy Distance = 5.4466 (MMD = 0.1063)"),
    ("Energy Distance = 0.0543", "Energy Distance = 2.1159 (MMD = 0.0543)"),
    ("Energy Distance = 0.1854", "Energy Distance = 7.9693 (MMD = 0.1854)"),
    ("HHEXhet = 0.2307", "HHEXhet = 10.4732 (MMD = 0.2307)"),
    ("HHEX = 0.2034", "HHEX = 8.9955 (MMD = 0.2034)"),
    ("HHEXe = 0.1227", "HHEXe = 5.6227 (MMD = 0.1227)"),
    ("Energy Distance = 0.0512", "Energy Distance = 1.9542 (MMD = 0.0512)"),
    ("Energy Distance = 0.0381", "Energy Distance = 1.6372 (MMD = 0.0381)"),
    ("0.3129 in *PDX1het*", "13.6337 (MMD 0.3129) in *PDX1het*"),
    ("Peak lochNESS = +13.740", "dominant celltype lochNESS = +13.740 (Peak = +18.307)"),
    ("Peak lochNESS = +13.625", "dominant celltype lochNESS = +13.625 (Peak = +25.564)"),
    ("Peak lochNESS = +4.530", "dominant celltype lochNESS = +4.530 (Peak = +37.059)"),
    ("Peak lochNESS = +4.129", "dominant celltype lochNESS = +4.129 (Peak = +9.820)"),
    ("Peak lochNESS = +3.304", "dominant celltype lochNESS = +3.304 (Peak = +7.969)"),
    ("Peak lochNESS = +3.084", "dominant celltype lochNESS = +3.084 (Peak = +9.326)"),
    ("3.8-fold", "~3.8-fold (approx. from Fig. 5d)"),
    ("78.4%", "~78% (approx. from Fig. 5g)")
]
update_file('Case_Study_Map.md', case_replacements)
