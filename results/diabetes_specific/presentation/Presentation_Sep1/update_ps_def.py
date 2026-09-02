# -*- coding: utf-8 -*-
with open('WIP_scientific_reading.md', 'r') as f:
    text = f.read()

old_block = """#### 3. Method & Input Representation
- **Method:** Adapted from the Mixscape framework. For each perturbed cell $i$, PS calculates the probability that the cell has departed from the local control distribution in high-dimensional gene expression space.
- **Input:** Normalized count expression matrix of single cells and target gene expression.
- **Score Range:** Bounded native probability range $[0.0, 1.0]$.
- **Level of Analysis:** Cell-level score, aggregated to perturbation-level (mean PS, median PS, responder fraction where $\\text{PS} > 0.5$)."""

new_block = """#### 3. Method & Input Representation
- **Method:** Adapted from the Mixscape Gaussian Mixture / local perturbation framework. PS is a continuous, cell-level score measuring the probability that an individual single cell has genuinely departed from the local unperturbed (WT) control distribution in high-dimensional gene expression space.
- **Input:** Normalized single-cell gene expression matrix and target gene identity.
- **Score Scale:** Native continuous probability range $[0.0, 1.0]$, where values near 1.0 indicate strong single-cell perturbation response, and values near 0.0 indicate non-responders or unperturbed 'escapers'.
- **Level of Analysis:** Inherently a cell-level continuous metric, which is summarized at the perturbation level using the median PS and an explicit responder fraction (percentage of cells with $\\text{PS} > 0.5$).
- **Missing Data Clarification:** Skipped/unavailable PS (for 10 compound/heterozygous lines) is an analytical lookup constraint (target name not matching a single gene symbol in the RNA matrix), NOT a zero response."""

text = text.replace(old_block, new_block)
with open('WIP_scientific_reading.md', 'w') as f:
    f.write(text)
print('Updated PS block in WIP_scientific_reading.md')
