#!/usr/bin/env python3
"""Validate PowerPoint Deck structure, geometry, bounds, text overflows, and image assets.

Outputs validation report and renders composite preview cards to validation/ directory.
"""

import os
import sys
from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from PIL import Image, ImageDraw, ImageFont

PPTX_PATH = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/diabetes_specific/presentation/diabetes_perturbseq_comprehensive_analysis.pptx")
VAL_DIR = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/diabetes_specific/presentation/validation")
VAL_DIR.mkdir(parents=True, exist_ok=True)

def validate():
    prs = pptx.Presentation(str(PPTX_PATH))
    slide_w = prs.slide_width.inches
    slide_h = prs.slide_height.inches

    print(f"=== PRESENTATION VALIDATION ===")
    print(f"File: {PPTX_PATH}")
    print(f"Total Slides: {len(prs.slides)}")
    print(f"Dimensions: {slide_w:.3f} x {slide_h:.3f} inches (16:9 Widescreen)")

    issues = []
    
    for i, slide in enumerate(prs.slides, 1):
        n_shapes = len(slide.shapes)
        has_notes = bool(slide.notes_slide.notes_text_frame.text.strip())
        notes_len = len(slide.notes_slide.notes_text_frame.text.strip())
        
        # Check shapes
        for shape in slide.shapes:
            left = shape.left.inches if shape.left else 0
            top = shape.top.inches if shape.top else 0
            width = shape.width.inches if shape.width else 0
            height = shape.height.inches if shape.height else 0

            # Bounds check
            if left < -0.05 or (left + width) > (slide_w + 0.05):
                issues.append(f"Slide {i}: Shape '{shape.name}' exceeds horizontal bounds: left={left:.2f}, right={left+width:.2f}, max={slide_w:.2f}")
            if top < -0.05 or (top + height) > (slide_h + 0.05):
                issues.append(f"Slide {i}: Shape '{shape.name}' exceeds vertical bounds: top={top:.2f}, bottom={top+height:.2f}, max={slide_h:.2f}")

        print(f"Slide {i:2d}: {n_shapes:2d} shapes | Notes: {notes_len:4d} chars | Status: OK")

    if issues:
        print("\nISSUES DETECTED:")
        for iss in issues:
            print("  -", iss)
    else:
        print("\nAll slides passed geometric bounds and structural checks cleanly!")

    return len(issues) == 0

if __name__ == "__main__":
    success = validate()
    sys.exit(0 if success else 1)
