#!/usr/bin/env python3
"""Render visual slide mockups for all 30 slides to presentation/validation/.

Extracts shapes, text, colors, and embedded images from the generated PPTX
and renders 1920x1080 preview PNG images to verify layout, text wrapping, and image placement.
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

# Image scale: 1920 x 1080 (144 DPI for 13.333 x 7.5 inches)
SCALE = 144.0

def emu_to_px(emu):
    return int(round((emu / 914400.0) * SCALE))

def render_previews():
    prs = pptx.Presentation(str(PPTX_PATH))
    w_px = emu_to_px(prs.slide_width)
    h_px = emu_to_px(prs.slide_height)

    # Try to load fonts
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 26)
        font_cat = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 14)
        font_card_title = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 16)
        font_bold = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", 13)
        font_body = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 13)
        font_foot = ImageFont.truetype("/usr/share/fonts/dejavu/DejaVuSans.ttf", 12)
    except Exception:
        font_title = font_cat = font_card_title = font_bold = font_body = font_foot = ImageFont.load_default()

    for idx, slide in enumerate(prs.slides, 1):
        img = Image.new("RGB", (w_px, h_px), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        for shape in slide.shapes:
            x = emu_to_px(shape.left) if shape.left else 0
            y = emu_to_px(shape.top) if shape.top else 0
            w = emu_to_px(shape.width) if shape.width else 0
            h = emu_to_px(shape.height) if shape.height else 0

            # 1. Pictures
            if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
                try:
                    blob = shape.image.blob
                    from io import BytesIO
                    p_img = Image.open(BytesIO(blob)).convert("RGB")
                    p_img_resized = p_img.resize((w, h), Image.Resampling.LANCZOS)
                    img.paste(p_img_resized, (x, y))
                    draw.rectangle([x, y, x + w, y + h], outline=(226, 232, 240), width=1)
                except Exception as e:
                    draw.rectangle([x, y, x + w, y + h], fill=(240, 240, 240), outline=(200, 200, 200))
                    draw.text((x + 10, y + 10), f"Image: {shape.name}", fill=(100, 100, 100), font=font_body)

            # 2. Rounded Rectangles / Cards
            elif shape.has_text_frame or shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.AUTO_SHAPE:
                if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.AUTO_SHAPE:
                    draw.rounded_rectangle([x, y, x + w, y + h], radius=8, fill=(248, 249, 250), outline=(226, 232, 240), width=1)

                if shape.has_text_frame:
                    cur_y = y + 10
                    for p in shape.text_frame.paragraphs:
                        text_str = p.text.strip()
                        if not text_str:
                            continue

                        # Check runs for colors
                        cur_x = x + 10
                        if p.font and p.font.size and p.font.size.pt >= 18:
                            f = font_title
                            color = (26, 32, 44)
                        elif p.font and p.font.size and p.font.size.pt <= 10.5 and p.font.bold:
                            f = font_cat
                            color = (49, 151, 149)
                        elif p.font and p.font.bold:
                            f = font_bold
                            color = (43, 108, 176)
                        else:
                            f = font_body
                            color = (40, 40, 40)

                        draw.text((cur_x, cur_y), text_str[:120], fill=color, font=f)
                        cur_y += 18

        out_path = VAL_DIR / f"slide_{idx:02d}.png"
        img.save(out_path)

    print(f"Rendered {len(prs.slides)} preview slides to: {VAL_DIR}")

if __name__ == "__main__":
    render_previews()
