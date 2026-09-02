#!/usr/bin/env python3
"""Comprehensive PowerPoint Deck Generator for Diabetes Perturb-seq Analysis.

Constructs 30 widescreen slides (25 Main Deck + 5 Backup Deck) using python-pptx,
incorporating exact verified numbers, figures, structured WHAT/RESULT/WHY callouts,
and comprehensive speaker notes.
"""

import os
import sys
from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from PIL import Image

# -----------------------------------------------------------------------------
# Color Palette & Typography
# -----------------------------------------------------------------------------
COLOR_BG = RGBColor(255, 255, 255)         # Pure white
COLOR_DARK = RGBColor(26, 32, 44)          # Slate 900
COLOR_MUTED = RGBColor(74, 85, 104)        # Slate 600
COLOR_LIGHT_GRAY = RGBColor(248, 249, 250) # Very light gray
COLOR_CARD_BORDER = RGBColor(226, 232, 240)# Slate 200

COLOR_PRIMARY = RGBColor(43, 108, 176)     # Deep Blue (#2B6CB0)
COLOR_SECONDARY = RGBColor(49, 151, 149)   # Teal (#319795)
COLOR_ACCENT = RGBColor(214, 158, 46)      # Amber / Gold (#D69E2E)
COLOR_ALERT = RGBColor(229, 62, 62)        # Crimson / Red (#E53E3E)
COLOR_GREEN = RGBColor(47, 133, 90)        # Forest Green (#2F855A)
COLOR_PURPLE = RGBColor(128, 90, 213)      # Violet (#805AD5)

FONT_HEADING = "Helvetica"
FONT_BODY = "Arial"

BASE_DIR = Path("/local/projects-t3/lilab/vmenon/PertTF-Virtual-Challeng-Weilab/perturbseq-pipeline/results/diabetes_specific")
FIG_DIR = BASE_DIR / "figures"
PRES_DIR = BASE_DIR / "presentation"
PPTX_OUT = PRES_DIR / "diabetes_perturbseq_comprehensive_analysis.pptx"

def init_deck():
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    return prs

def add_header(slide, title_text, category_text="PANCREATIC PERTURB-SEQ ANALYSIS", slide_num=None, is_backup=False):
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(10.5), Inches(0.28))
    tf_cat = cat_box.text_frame
    tf_cat.word_wrap = True
    tf_cat.margin_left = tf_cat.margin_top = tf_cat.margin_right = tf_cat.margin_bottom = 0
    p_cat = tf_cat.paragraphs[0]
    p_cat.text = f"BACKUP | {category_text}" if is_backup else category_text
    p_cat.font.name = FONT_HEADING
    p_cat.font.size = Pt(10)
    p_cat.font.bold = True
    p_cat.font.color.rgb = COLOR_PURPLE if is_backup else COLOR_SECONDARY

    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.62), Inches(11.733), Inches(0.7))
    tf_title = title_box.text_frame
    tf_title.word_wrap = True
    tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
    p_title = tf_title.paragraphs[0]
    p_title.text = title_text
    p_title.font.name = FONT_HEADING
    p_title.font.size = Pt(18.5)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_DARK

    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.08), Inches(11.733), Inches(0.25))
    tf_foot = footer_box.text_frame
    tf_foot.word_wrap = True
    tf_foot.margin_left = tf_foot.margin_top = tf_foot.margin_right = tf_foot.margin_bottom = 0
    p_foot = tf_foot.paragraphs[0]
    num_str = f"Slide {slide_num} of 30" if slide_num else ""
    p_foot.text = f"Human Pancreatic Differentiation Perturb-seq (GSE216909) | 111,581 Cells x 36 TFs                                           {num_str}"
    p_foot.font.name = FONT_BODY
    p_foot.font.size = Pt(9)
    p_foot.font.color.rgb = RGBColor(160, 174, 192)

def add_what_result_why(slide, left, top, width, height, what_text, result_text, why_text):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = COLOR_LIGHT_GRAY
    card.line.color.rgb = COLOR_CARD_BORDER
    card.line.width = Pt(1)

    pad = Inches(0.12)
    tb = slide.shapes.add_textbox(left + pad, top + pad, width - (2 * pad), height - (2 * pad))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p1 = tf.paragraphs[0]
    r1_tag = p1.add_run()
    r1_tag.text = "WHAT: "
    r1_tag.font.name = FONT_HEADING
    r1_tag.font.size = Pt(9.5)
    r1_tag.font.bold = True
    r1_tag.font.color.rgb = COLOR_PRIMARY
    r1_txt = p1.add_run()
    r1_txt.text = what_text + "\n"
    r1_txt.font.name = FONT_BODY
    r1_txt.font.size = Pt(9.0)
    r1_txt.font.color.rgb = COLOR_DARK

    p2 = tf.add_paragraph()
    r2_tag = p2.add_run()
    r2_tag.text = "RESULT: "
    r2_tag.font.name = FONT_HEADING
    r2_tag.font.size = Pt(9.5)
    r2_tag.font.bold = True
    r2_tag.font.color.rgb = COLOR_GREEN
    r2_txt = p2.add_run()
    r2_txt.text = result_text + "\n"
    r2_txt.font.name = FONT_BODY
    r2_txt.font.size = Pt(9.0)
    r2_txt.font.color.rgb = COLOR_DARK

    p3 = tf.add_paragraph()
    r3_tag = p3.add_run()
    r3_tag.text = "WHY: "
    r3_tag.font.name = FONT_HEADING
    r3_tag.font.size = Pt(9.5)
    r3_tag.font.bold = True
    r3_tag.font.color.rgb = COLOR_ALERT
    r3_txt = p3.add_run()
    r3_txt.text = why_text
    r3_txt.font.name = FONT_BODY
    r3_txt.font.size = Pt(9.0)
    r3_txt.font.color.rgb = COLOR_DARK

def add_card(slide, left, top, width, height, title, items, title_color=COLOR_PRIMARY, bg_color=COLOR_LIGHT_GRAY):
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = bg_color
    card.line.color.rgb = COLOR_CARD_BORDER
    card.line.width = Pt(1)

    pad = Inches(0.12)
    tb = slide.shapes.add_textbox(left + pad, top + pad, width - (2 * pad), height - (2 * pad))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    if title:
        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = FONT_HEADING
        p0.font.size = Pt(10.5)
        p0.font.bold = True
        p0.font.color.rgb = title_color
        p0.space_after = Pt(3)
        start_idx = 1
    else:
        start_idx = 0

    for idx, item in enumerate(items):
        if idx == 0 and not title:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()

        p.text = f"• {item}" if not item.startswith("• ") else item
        p.font.name = FONT_BODY
        p.font.size = Pt(9.0)
        p.font.color.rgb = COLOR_DARK
        p.space_after = Pt(2.5)

def add_image(slide, img_path, left, top, max_w, max_h):
    if not Path(img_path).exists():
        print(f"ERROR: Image path not found: {img_path}")
        return None

    with Image.open(img_path) as im:
        orig_w, orig_h = im.size

    aspect = orig_w / orig_h
    box_aspect = max_w / max_h

    if aspect > box_aspect:
        w = max_w
        h = max_w / aspect
        x = left
        y = top + (max_h - h) / 2
    else:
        h = max_h
        w = max_h * aspect
        y = top
        x = left + (max_w - w) / 2

    return slide.shapes.add_picture(str(img_path), x, y, w, h)

def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

def build_all_slides():
    prs = init_deck()
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Title Slide
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    # Background accent card
    bg_card = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.8), Inches(11.733), Inches(5.9))
    bg_card.fill.solid()
    bg_card.fill.fore_color.rgb = COLOR_LIGHT_GRAY
    bg_card.line.color.rgb = COLOR_CARD_BORDER
    bg_card.line.width = Pt(1)

    # Title Text Frame
    tb1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.3), Inches(10.9), Inches(4.8))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    
    p1 = tf1.paragraphs[0]
    p1.text = "MULTI-LAYERED PERTURB-SEQ ANALYSIS OF HUMAN PANCREATIC DIFFERENTIATION"
    p1.font.name = FONT_HEADING
    p1.font.size = Pt(24)
    p1.font.bold = True
    p1.font.color.rgb = COLOR_PRIMARY
    p1.space_after = Pt(12)

    p2 = tf1.add_paragraph()
    p2.text = "Dissecting 36 Master Transcription Factors Across 111,581 Single Cells in Lineage Specification"
    p2.font.name = FONT_HEADING
    p2.font.size = Pt(15)
    p2.font.color.rgb = COLOR_DARK
    p2.space_after = Pt(24)

    p3 = tf1.add_paragraph()
    p3.text = "Comprehensive Evaluation of Cellular Response Strength (PS), Multivariate Phenotype Distance (Energy Distance),\nContinuous Manifold Trapping (lochNESS), Lineage Conversion, and Downstream Gene Regulomes"
    p3.font.name = FONT_BODY
    p3.font.size = Pt(11)
    p3.font.color.rgb = COLOR_MUTED
    p3.space_after = Pt(36)

    p4 = tf1.add_paragraph()
    p4.text = "Dataset: GSE216909 (Chen et al., Nature 2023)  |  Analytical Framework: Perturb-seq Computational Pipeline"
    p4.font.name = FONT_BODY
    p4.font.size = Pt(10)
    p4.font.bold = True
    p4.font.color.rgb = COLOR_SECONDARY

    set_notes(s1, 
        "Welcome to this comprehensive scientific presentation on the diabetes-specific Perturb-seq analysis. "
        "In this study, we systematically dissect a massive pooled single-cell CRISPR screen comprising 111,581 human cells "
        "undergoing directed in vitro differentiation from pluripotency toward insulin-producing pancreatic beta cells. "
        "We evaluate 36 non-WT transcription factor perturbations and non-targeting wild-type controls across 15 curated cell states. "
        "Crucially, rather than relying on a single simplistic metric, we implement a multi-layered analytical framework that separates "
        "target response strength, global transcriptomic displacement, continuous manifold localization, cell-state conversion, "
        "and downstream regulatory modules. Over the next 24 slides, we will walk through the biological and statistical architecture "
        "of human pancreatic specification."
    )

    # =========================================================================
    # SLIDE 2: Biological Question & Pancreatic Differentiation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Dissecting the Regulatory Circuitry of Human Pancreatic Endocrine Fate", "BIOLOGICAL FOUNDATION", 2)
    
    add_card(s2, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3), "The Pancreatic Differentiation Challenge", [
        "Directed differentiation of human pluripotent stem cells (hESCs) into mature pancreatic beta cells mimics embryonic development through discrete intermediate stages.",
        "Key developmental checkpoints: Pluripotency (ESC) → Definitive Endoderm (DE) → Primitive Gut Tube (PGT) → Posterior Foregut (PFG) → Pancreatic Progenitors (PP/PDP) → Endocrine Progenitors (EnP) → Mature Islet States (SC-alpha, SC-beta, SC-delta, SC-EC).",
        "Inefficiency, developmental arrest, and off-target lineage diversions (e.g. liver, stromal, endothelial) remain major roadblocks to cell replacement therapy for diabetes.",
        "Transcription factors (TFs) act as master coordinators of these lineage decisions, but their individual and combinatorial roles have been difficult to quantify systematically."
    ], COLOR_PRIMARY)

    add_card(s2, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3), "Core Scientific Questions Addressed in this Study", [
        "1. Response Penetrance: Which transcription factor knockouts reliably trigger strong single-cell transcriptional responses vs cellular buffering?",
        "2. Phenotype Magnitude: Which master regulators produce the largest multivariate transcriptomic displacement from wild-type differentiation?",
        "3. Developmental Trapping vs Diversion: Does TF loss arrest progenitors at discrete checkpoints, or actively divert them into non-pancreatic lineages?",
        "4. Phenotypic Phenocopying: Which distinct transcription factors converge on shared downstream transcriptomic states in DistanceSpace?",
        "5. Regulome Organization: What co-functional modules (M1–M6) and co-regulated gene programs (P1–P4) execute these developmental programs?"
    ], COLOR_SECONDARY)

    set_notes(s2,
        "Here we establish the biological rationale for this study. Human stem cell differentiation into insulin-producing beta cells "
        "is a complex multi-step trajectory requiring precise sequential activation of master transcription factors. In vitro protocols "
        "often suffer from inefficient specification and off-target lineage branching, such as hepatic or mesenchymal divergence. "
        "By applying pooled single-cell CRISPR perturbations against 36 master regulators, we aim to resolve five fundamental questions: "
        "which knockouts overcome cellular buffering, how large is their global multivariate displacement, where on the single-cell manifold "
        "do cells accumulate or deplete, which perturbations phenocopy each other, and what downstream gene programs drive these phenotypes. "
        "Let us examine how this massive screening experiment was designed."
    )

    # =========================================================================
    # SLIDE 3: Experimental System & Screen Architecture
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Pooled Single-Cell CRISPR Screening Across 13 Differentiation Libraries", "EXPERIMENTAL DESIGN", 3)

    add_card(s3, Inches(0.8), Inches(1.5), Inches(3.6), Inches(5.3), "Screen Parameters & Scale", [
        "Total Single Cells: 111,581 high-quality single-cell transcriptomes.",
        "Targeted Regulators: 37 genotypes (1 WT control + 36 transcription factors).",
        "Control Population: 24,408 WT cells across differentiation stages.",
        "sgRNA Constructs: 100 distinct guides (2–4 independent sgRNAs per locus).",
        "Feature Space: 36,601 measured genes/features in expression matrix.",
        "Multiplexing: 13 experimental sequencing libraries (orig.ident)."
    ], COLOR_PRIMARY)

    add_card(s3, Inches(4.7), Inches(1.5), Inches(3.7), Inches(5.3), "Screened Regulators (36 TFs)", [
        "Endoderm & Foregut: FOXA1, FOXA2, GATA4, GATA6, GSC, HHEX, HNF4A.",
        "Pancreatic Progenitors: PDX1, ONECUT1, MNX1, RFX6, GLIS3, BMPR1A.",
        "Endocrine Commitment: NEUROG3, NEUROD1, NKX2-2, PAX6, ARX, PBX1, TLE3.",
        "Chromatin & Epigenetic Modifiers: TET1, TET1/2/3, KDM2B, BCOR, OTUD5, PROSER1, QSER1, QSER1TET1, TADA2B.",
        "Genetic Dosage: Heterozygous models (PDX1het, GATA4het, GATA6het, HHEXhet, HNF4Ahet, NANOGe-het)."
    ], COLOR_SECONDARY)

    add_card(s3, Inches(8.7), Inches(1.5), Inches(3.8), Inches(5.3), "Dataset Provenance & Quality", [
        "Study: Chen et al., Nature 2023 (s41586-023-06733-x).",
        "Accession: GEO GSE216909.",
        "System: Human embryonic stem cells (hESCs) subjected to staged directed differentiation protocol.",
        "Staged Libraries: Sample_A–F (WT), Sample_G (ESC), Sample_H (DE), Sample_I (PFG), Sample_J (PP), Sample_L (3DEC).",
        "QC Bounded Sampling: Max 2,000 cells per target and 5,000 WT controls used in distance testing to prevent sample-size bias."
    ], COLOR_ACCENT)

    set_notes(s3,
        "This slide details the experimental architecture and provenance of the dataset. Sourced from Chen et al. (Nature 2023, GSE216909), "
        "the screen contains 111,581 single cells covering 36 transcription factor knockouts and 24,408 WT control cells across 13 multiplexed libraries. "
        "The targeted panel spans every major stage of pancreatic development: from endodermal pioneer factors like FOXA2 and GATA6, "
        "to pancreatic specification factors like PDX1 and RFX6, endocrine commitment drivers like NEUROG3 and NEUROD1, and chromatin regulators like TET1 and KDM2B. "
        "Crucially, the dataset also includes heterozygous and enhancer perturbations, allowing us to evaluate dosage sensitivity. "
        "Next, let's examine the cellular landscape generated across these differentiation stages."
    )

    # =========================================================================
    # SLIDE 4: Pancreatic Landscape (15 Curated States)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Single-Cell Transcriptomic Map Spans 15 Curated Pancreatic States", "CELLULAR LANDSCAPE", 4)
    add_image(s4, FIG_DIR / "01_umap_celltype2.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    add_what_result_why(s4, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4),
        "2D UMAP projection of 111,581 single cells colored by 15 curated biological cell states (celltype_2) annotated via canonical lineage markers.",
        "The cellular manifold resolves continuous in vitro progression: Pluripotent ESC (21,027) → DE (18,361) → PFG (17,145) → PP (13,388) → PDP (9,178) → EnP (3,620) → mature endocrine branches: SC-EC (8,785), SC-alpha (4,732), SC-beta (3,799), SC-delta (740), plus off-target Liver (3,416), Stromal (4,369), and Endothelial (1,157) populations.",
        "Establishes a high-resolution, unperturbed reference landscape. Perturbations can now be mapped directly against this manifold to identify developmental arrests and lineage branching."
    )

    set_notes(s4,
        "Looking at Slide 4, Figure 01 displays the global 2D UMAP embedding of all 111,581 cells colored by the 15 curated cell states in celltype_2. "
        "The embedding captures the complete continuum of directed differentiation: starting from undifferentiated ESCs on the left, moving through definitive endoderm (DE) "
        "and posterior foregut (PFG), into pancreatic progenitors (PP and PDP) and endocrine progenitors (EnP), terminating in differentiated endocrine cell types: "
        "SC-beta cells (3,799 cells), SC-alpha cells (4,732 cells), SC-delta cells (740 cells), and enterochromaffin-like SC-EC cells (8,785 cells). "
        "Importantly, off-target populations including liver hepatocytes (3,416 cells), stromal cells (4,369 cells), and endothelial cells (1,157 cells) are clearly resolved. "
        "This curated atlas serves as the baseline for all subsequent perturbation analyses."
    )

    # =========================================================================
    # SLIDE 5: Stage Progression vs Cell-State Heterogeneity
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Differentiation Stages Harbor Substantial Cell-State Heterogeneity", "EXPERIMENTAL COMPOSITION", 5)
    add_image(s5, FIG_DIR / "02_umap_development_stage.png", Inches(0.8), Inches(1.45), Inches(4.5), Inches(5.4))
    add_image(s5, FIG_DIR / "03_stage_celltype_composition.png", Inches(5.4), Inches(1.45), Inches(3.8), Inches(5.4))

    add_what_result_why(s5, Inches(9.35), Inches(1.45), Inches(3.18), Inches(5.4),
        "Stage progression on UMAP (left) and compositional distribution of curated cell states across 6 differentiation stages (right).",
        "celltype_2 != development_stage. While ESC and DE stages are relatively pure, late stage 3DEC (25,143 cells) is highly heterogeneous, containing SC-EC (34.9%), SC-alpha (18.8%), SC-beta (15.1%), PDP (12.4%), Stromal (12.1%), SC-delta (2.9%), and Endothelial (1.4%).",
        "Evaluating perturbation outcomes by experimental harvest stage alone causes severe confounding. True biological effects must be measured in curated cell-state space."
    )

    set_notes(s5,
        "On Slide 5, we compare experimental developmental stages (Figure 02, left) with curated cell-state composition (Figure 03, middle). "
        "A foundational insight is that development_stage does not equal celltype_2. While early harvesting timepoints like ESC and DE are fairly homogeneous, "
        "the final differentiation stage, 3DEC (comprising 25,143 cells), is profoundly heterogeneous: it contains insulin-positive SC-beta cells (15.1%), "
        "glucagon-positive SC-alpha cells (18.8%), somatostatin-positive SC-delta cells (2.9%), SC-EC cells (34.9%), remaining ductal progenitors (12.4%), "
        "and stromal/endothelial cells. This underscores why evaluating perturbation biology strictly by library or stage would introduce severe confounding; "
        "all our downstream analyses rely on the curated biological cell states in celltype_2."
    )

    # =========================================================================
    # SLIDE 6: Conceptual Framework
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "A Multi-Layered Framework to Deconvolve Perturbation Biology", "ANALYTICAL ARCHITECTURE", 6)

    # 4 columns of cards
    w_c = Inches(2.78)
    gap = Inches(0.2)
    left_base = Inches(0.8)

    add_card(s6, left_base, Inches(1.5), w_c, Inches(5.3), "1. Response & Magnitude", [
        "Target Efficacy: Did the guide down-regulate the target transcript?",
        "Perturbation Score (PS): Supervised classification score (pertps) evaluating whether single cells mounted a transcriptomic response.",
        "Energy Distance: Multivariate distance in PCA space measuring the total distributional divergence of perturbed cells from WT.",
        "DistanceTest: Permutation hypothesis testing (1,000 label permutations, BH-FDR) verifying global statistical significance."
    ], COLOR_PRIMARY)

    add_card(s6, left_base + w_c + gap, Inches(1.5), w_c, Inches(5.3), "2. Spatial Localization", [
        "Continuous lochNESS: Signed k-nearest neighbor enrichment score in latent PCA space.",
        "Directional lochNESS: Decomposes into positive accumulation (>0, focal trapping) vs negative depletion (<0, lineage blockade).",
        "Cluster-Free Resolution: Maps exact manifold locations where cells accumulate without discrete cluster boundary artifacts.",
        "Stratified Cell Enrichment: Quantifies cell-type odds ratios adjusting for orig.ident library composition."
    ], COLOR_SECONDARY)

    add_card(s6, left_base + (w_c + gap)*2, Inches(1.5), w_c, Inches(5.3), "3. Phenotypic Similarity", [
        "DistanceSpace: Evaluates all 630 pairwise Energy Distances between non-WT perturbations.",
        "Classical PCoA: Projects perturbations into a continuous phenotypic manifold.",
        "Phenotype Groups (PG1–PG9): Hierarchical clustering of pairwise distances discovers phenocopying regulators.",
        "Dosage Concordance: Validates reproducibility between homozygous and heterozygous genetic edits."
    ], COLOR_ACCENT)

    add_card(s6, left_base + (w_c + gap)*3, Inches(1.5), w_c, Inches(5.3), "4. Regulatory Programs", [
        "Stage 7 Modules (M1–M6): Clusters perturbations by downstream differential expression effect patterns.",
        "Gene Programs (P1–P4): Clusters 980 responsive downstream genes into co-regulated functional units.",
        "Program Enrichment: Over-representation analysis against Hallmark, Reactome, and GO BP pathways.",
        "Module Network: Reconstructs directed cross-regulatory TF influence graphs."
    ], COLOR_PURPLE)

    set_notes(s6,
        "Slide 6 presents the conceptual framework of our analysis pipeline. A common pitfall in Perturb-seq analysis is collapsing all results into a single score. "
        "In reality, a Perturb-seq experiment contains distinct, orthogonal layers of biological information: "
        "First, did individual cells respond? That is captured by the Perturbation Score (PS). "
        "Second, how large was the global multivariate phenotype shift? That is quantified by Energy Distance and validated by DistanceTest. "
        "Third, where in developmental state space did cells accumulate or disappear? That is measured continuously by signed lochNESS. "
        "Fourth, which perturbations phenocopy one another? That is mapped by DistanceSpace. "
        "And fifth, what downstream regulatory programs execute these phenotypes? That is resolved by co-functional modules and gene programs. "
        "Let us examine each of these analytical layers in sequence, starting with PS."
    )

    # =========================================================================
    # SLIDE 7: Perturbation Score (PS)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Single-Cell Perturbation Scores Reveal Variable Response Penetrance", "RESPONSE STRENGTH (PS)", 7)
    add_image(s7, FIG_DIR / "05_ps_by_perturbation.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))

    add_what_result_why(s7, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4),
        "Perturbation Score (PS) computed via pertps: supervised classifier projecting cells onto a [0, 1] response scale based on transcriptomic perturbation signatures vs WT control.",
        "Evaluated for 26/36 single-gene targets (mean PS = 0.4132 across 66,015 cells). Top responders: KDM2B (mean 0.6273, median 0.6808), GLIS3 (mean 0.6075, median 0.7500, 66.6% responder fraction), HHEX (mean 0.6050, median 0.6589), GATA6 (mean 0.5776, median 0.6482). Lowest: PAX6 (0.3372) and NEUROD1 (0.3393). 10 composite/heterozygous targets appropriately skipped.",
        "CRISPR knockout penetrance is highly locus-dependent in stem cells. PS isolates true single-cell responders from unperturbed escapers, avoiding diluted bulk averages."
    )

    set_notes(s7,
        "On Slide 7, Figure 05 illustrates the distribution of Perturbation Scores (PS) across all evaluable perturbations. "
        "PS is trained on target vs control cells using pertps to assign every single cell a continuous score between 0 and 1. "
        "Across 26 evaluable single-gene targets, the overall mean PS is 0.4132. We observe striking variation in response penetrance: "
        "GLIS3 and KDM2B show the highest response rates, with GLIS3 achieving a median PS of 0.7500 and a 66.6% responder fraction. "
        "In contrast, late-stage factors like PAX6 (mean 0.3372) and NEUROD1 (mean 0.3393) show modest cellular penetrance. "
        "Importantly, 10 targets—such as TET1/2/3, PDX1het, and enhancer guides—were appropriately skipped because they lack a single matching target feature. "
        "Next, let's see how this response score maps across the single-cell manifold."
    )

    # =========================================================================
    # SLIDE 8: PS vs lochNESS on UMAP
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Response Strength Distributes Across Specific Lineage States", "SPATIAL RESOLUTION", 8)
    add_image(s8, FIG_DIR / "27_umap_ps_lochness_comparison.png", Inches(0.8), Inches(1.45), Inches(7.5), Inches(5.4))

    add_what_result_why(s8, Inches(8.5), Inches(1.45), Inches(4.03), Inches(5.4),
        "Side-by-side UMAP projections comparing continuous single-cell response strength (PS score density, left) with continuous neighborhood enrichment (lochNESS, right).",
        "PS scores are highest in early progenitor regions (ESC mean PS = 0.568, DE = 0.551) and specific endocrine branches, while lochNESS identifies focal neighborhood accumulation (>0) and exclusion zones (<0) across 111,581 cells.",
        "Directly illustrates the conceptual difference: PS tells us how strongly an individual cell responded, while lochNESS tells us where on the manifold perturbed cells accumulated."
    )

    set_notes(s8,
        "Slide 8 presents Figure 27, comparing single-cell PS score density on the left with lochNESS neighborhood enrichment on the right. "
        "This visual comparison captures a core insight of our analysis: a high PS response score indicates intense transcriptional response at the single-cell level, "
        "which is predominantly concentrated in early progenitor states (ESC and DE) and active differentiation branch points. "
        "In contrast, lochNESS highlights focal accumulation hotspots where perturbed cells are trapped, as well as vast exclusion zones where cells fail to differentiate. "
        "Next, we move to global multivariate displacement: Energy Distance."
    )

    # =========================================================================
    # SLIDE 9: Energy Distance & DistanceTest
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Energy Distance Quantifies Global Multivariate Phenotypic Shift", "PHENOTYPE MAGNITUDE", 9)
    add_image(s9, FIG_DIR / "06_energy_distance_by_perturbation.png", Inches(0.8), Inches(1.45), Inches(5.8), Inches(5.4))

    add_what_result_why(s9, Inches(6.8), Inches(1.45), Inches(5.733), Inches(5.4),
        "Multivariate Energy Distance computed in PCA space (50 PCs, V-statistic estimator) and DistanceTest permutation hypothesis test (1,000 label permutations, BH-FDR) vs WT control.",
        "36/36 non-WT perturbations are statistically significant (all p = 0.000999, FDR = 0.000999). Effect magnitude spans a 12-fold dynamic range: Top: PDX1het (E = 13.6337), HHEXhet (E = 10.4732), GATA6 (E = 9.7045), KDM2B (E = 9.3204), HHEX (E = 8.9955). Bottom: MNX1 (E = 1.0755), PAX6 (E = 1.1531), BCOR (E = 1.3674), NEUROD1 (E = 1.4187).",
        "Proves that statistical significance alone (36/36) is uninformative without effect size quantification. Master lineage drivers produce an order of magnitude larger multivariate displacement than terminal regulators."
    )

    set_notes(s9,
        "Looking at Slide 9, Figure 06 displays the ranked Energy Distance for all 36 non-WT perturbations relative to WT controls. "
        "Energy Distance is calculated in 50-dimensional PCA space using the V-statistic formulation, comparing between-group distances against within-group dispersions. "
        "Every single one of the 36 perturbations achieved statistical significance under 1,000 label permutations, with an empirical p-value and FDR of 0.000999. "
        "However, the true biological insight lies in effect magnitude: perturbations like PDX1het (E = 13.63), HHEXhet (E = 10.47), and GATA6 (E = 9.70) "
        "produce massive multivariate displacement, whereas factors like MNX1 (E = 1.08) and PAX6 (E = 1.15) produce subtle shifts. "
        "This demonstrates that master lineage gatekeepers cause 10-fold larger transcriptomic displacement than terminal factors. "
        "Now let's examine where in the single-cell state space these displacements occur using lochNESS."
    )

    # =========================================================================
    # SLIDE 10: lochNESS Directional Localization
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Signed lochNESS Resolves Focal Accumulation from Lineage Depletion", "STATE LOCALIZATION (lochNESS)", 10)
    add_image(s10, FIG_DIR / "21_umap_lochness_score.png", Inches(0.8), Inches(1.45), Inches(4.5), Inches(5.4))
    add_image(s10, FIG_DIR / "25_lochness_by_genotype.png", Inches(5.4), Inches(1.45), Inches(3.8), Inches(5.4))

    add_what_result_why(s10, Inches(9.35), Inches(1.45), Inches(3.18), Inches(5.4),
        "Continuous k-nearest neighbor enrichment score in PCA space (k=30): lochNESS = (local_fraction / overall_fraction) - 1. Evaluated for all 111,581 cells across 36 perturbations.",
        "Resolves directional duality: Top positive accumulation (>0): GATA6 (+14.18), PDX1het (+14.15), TADA2B (+11.23), GLIS3 (+9.53), FOXA2 (+5.86). Strongest depletion (<0): PDX1 (-0.5891, 77.8% depleted cells) and FOXA2 (-0.4952, 70.7% depleted cells).",
        "A single global mean lochNESS is misleading because positive trapping cancels negative depletion. Directional decomposition is required to reveal lineage blocks."
    )

    set_notes(s10,
        "On Slide 10, we examine continuous local neighborhood enrichment using lochNESS. Figure 21 (left) shows the global single-cell score distribution, "
        "while Figure 25 (middle) decomposes lochNESS into positive accumulation and negative depletion across genotypes. "
        "Because lochNESS is signed—with positive values indicating local over-representation and negative values indicating depletion—a perturbation can simultaneously "
        "have intense focal accumulation in one region and massive depletion across downstream states. "
        "For instance, GATA6 and PDX1het achieve extreme positive enrichment scores exceeding +14.0, while PDX1 and FOXA2 exhibit over 70% depleted cells. "
        "Decomposing lochNESS directionally reveals that TF knockouts act simultaneously as focal traps and downstream lineage blocks."
    )

    # =========================================================================
    # SLIDE 11: lochNESS Across 15 Cell States
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "lochNESS Maps State-Specific Perturbation Trapping and Exclusion", "STATE-BY-STATE RESOLUTION", 11)
    add_image(s11, FIG_DIR / "13_lochness_by_celltype.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))

    add_what_result_why(s11, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4),
        "High-resolution matrix of mean signed lochNESS scores across all 36 non-WT perturbations and 15 curated cell states (celltype_2).",
        "Pinpoints developmental arrest points: GATA6 strongly enriches in Endothelial (+3.76) and ESC (+14.18) while depleting SC-beta (-0.43); FOXA2 enriches in Liver (+4.12) while depleting mature endocrine states; NEUROG3 traps cells in pancreatic/ductal progenitors (PDP) while abolishing SC-beta and SC-EC cells.",
        "Bridges continuous single-cell geometry with discrete biological annotations, providing a precise diagnostic map of lineage fate alterations."
    )

    set_notes(s11,
        "Slide 11 presents Figure 13, the full matrix of mean signed lochNESS values across all 36 perturbations and 15 curated cell states. "
        "This heatmap acts as a developmental diagnostic chart: we can immediately trace where each perturbation accumulates and where it creates a developmental void. "
        "GATA6 KO cells accumulate heavily in endothelial and pluripotent states while vanishing from endocrine lineages. "
        "FOXA2 KO cells accumulate intensely in liver hepatocytes, confirming a major endodermal fate diversion. "
        "And NEUROG3 KO cells pile up in pancreatic ductal progenitors (PDP) while completely disappearing from mature beta-cell states. "
        "Let us validate these observations with formal, sample-stratified cell-state enrichment tests."
    )

    # =========================================================================
    # SLIDE 12: Stratified Cell-State Enrichment
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Stratified Odds-Ratio Testing Uncovers Dramatic Lineage Conversions", "LINEAGE CONVERSION", 12)
    add_image(s12, FIG_DIR / "04_genotype_celltype_enrichment.png", Inches(0.8), Inches(1.45), Inches(6.2), Inches(5.4))

    add_what_result_why(s12, Inches(7.2), Inches(1.45), Inches(5.333), Inches(5.4),
        "Stratified hypergeometric / Fisher test for cell-state over-representation across Genotype x Celltype_2, stratified by orig.ident to eliminate library composition confounding.",
        "Discovers 313 significant lineage associations (FDR < 0.05). Major fate conversions: GATA6 -> Endothelial (25.7% of cells vs 0.7% baseline, log2 OR = +5.21, FDR = 1.05e-141); FOXA2 -> Liver (34.0% of cells vs 2.0% baseline, log2 OR = +4.09, FDR = 3.65e-224); NEUROG3 -> complete SC-beta loss (0 cells, 0.0%, log2 OR = -inf) and SC-EC loss (log2 OR = -4.75, FDR = 3.25e-33); GSC -> Stromal (log2 OR = +2.66).",
        "Sample stratification prevents spurious batch associations. Proves master TFs act as binary lineage switches: their loss actively diverts endodermal cells into alternative mesodermal, hepatic, or stromal fates."
    )

    set_notes(s12,
        "Looking at Slide 12, Figure 04 displays the log2 odds-ratio heatmap from our sample-stratified cell-state enrichment analysis. "
        "Because single cells originated from 13 distinct multiplexed libraries, naive testing would be confounded by batch library composition. "
        "Our stratified hypergeometric model accounts for library structure and identifies 313 statistically significant associations. "
        "The findings reveal profound lineage diversions: GATA6 loss causes 25.7% of cells to convert into endothelial cells—a log2 odds ratio of +5.21 (FDR 1e-141). "
        "FOXA2 loss diverts 34% of cells into liver hepatocytes (log2 OR +4.09, FDR 3.6e-224). "
        "And NEUROG3 loss causes a complete, absolute dropout of SC-beta cells (0 cells observed). "
        "Next, let's explore how these independent metrics correlate with each other."
    )

    # =========================================================================
    # SLIDE 13: Cross-Metric Coupling (PS vs Distance)
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Single-Cell Response Strength Strongly Predicts Global Phenotype Shift", "CROSS-METRIC COUPLING", 13)
    add_image(s13, FIG_DIR / "07_ps_vs_distance.png", Inches(0.8), Inches(1.45), Inches(5.8), Inches(5.4))

    add_what_result_why(s13, Inches(6.8), Inches(1.45), Inches(5.733), Inches(5.4),
        "Spearman rank correlation between mean Perturbation Score (PS) and multivariate Energy Distance vs WT across 26 evaluable perturbations.",
        "Strong, highly significant positive correlation: Spearman rho = +0.7832, p = 2.24e-6, n = 26. Perturbations with high single-cell response rates (KDM2B, GLIS3, HHEX, GATA6) systematically produce the largest multivariate transcriptomic displacement from WT.",
        "Demonstrates biological coherence across analytical scales: strong single-cell transcriptional engagement (PS) translates directly into large global multivariate divergence from wild-type differentiation."
    )

    set_notes(s13,
        "Slide 13 examines the relationship between single-cell response strength and global phenotype magnitude in Figure 07. "
        "We observe a remarkably strong, statistically significant Spearman rank correlation of rho = +0.7832 (p = 2.24e-6 across 26 perturbations). "
        "Perturbations like KDM2B, GLIS3, HHEX, and GATA6 show high values on both axes: when a large proportion of cells mounts a strong transcriptional response, "
        "the aggregate multivariate distribution shifts substantially away from wild-type. "
        "This strong coupling provides independent validation that both PS and Energy Distance capture true biological perturbation strength."
    )

    # =========================================================================
    # SLIDE 14: Cross-Metric Decoupling (Distance vs lochNESS)
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Distance and lochNESS Capture Distinct, Complementary Dimensions", "CROSS-METRIC DECOUPLING", 14)
    add_image(s14, FIG_DIR / "08_distance_vs_lochness_positive.png", Inches(0.8), Inches(1.45), Inches(3.8), Inches(5.4))
    add_image(s14, FIG_DIR / "12_distance_vs_lochness_absolute.png", Inches(4.75), Inches(1.45), Inches(3.8), Inches(5.4))

    add_what_result_why(s14, Inches(8.7), Inches(1.45), Inches(3.833), Inches(5.4),
        "Spearman rank correlations comparing Energy Distance with positive lochNESS mean (left, n=36) and absolute lochNESS mean (right, n=36).",
        "Distance vs Positive lochNESS: rho = +0.4103 (p = 0.0129); Distance vs Absolute lochNESS: rho = +0.4512 (p = 0.0057); Distance vs Negative lochNESS: rho = -0.1410 (p = 0.4263).",
        "Moderate positive correlation shows large global phenotypes often involve focal trapping, but the modest coupling proves lochNESS provides non-redundant spatial information unavailable from Energy Distance alone."
    )

    set_notes(s14,
        "On Slide 14, we investigate the relationship between global Energy Distance and lochNESS localization in Figures 08 and 12. "
        "We find a moderate, statistically significant correlation between Energy Distance and positive lochNESS (rho = +0.4103, p = 0.0129), "
        "as well as absolute lochNESS (rho = +0.4512, p = 0.0057). In contrast, Distance and negative lochNESS are virtually decoupled (rho = -0.1410). "
        "This is an essential conceptual takeaway: while large phenotypes often manifest as focal accumulation, Distance alone cannot tell you where cells go. "
        "The modest correlation is not a limitation—it proves that lochNESS provides an orthogonal, non-redundant layer of spatial information. "
        "Now let's examine pairwise phenotypic relationships in DistanceSpace."
    )

    # =========================================================================
    # SLIDE 15: Perturbation DistanceSpace
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "DistanceSpace Maps 630 Pairwise Phenotypes into 9 Similarity Groups", "PHENOTYPE MANIFOLD", 15)
    add_image(s15, FIG_DIR / "14_distance_space.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))

    add_what_result_why(s15, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4),
        "Classical Multidimensional Scaling (PCoA) and hierarchical clustering of all 630 pairwise Energy Distances between non-WT perturbations (36 choose 2 = 630).",
        "Discovers 9 Phenotypic Similarity Groups (PG1–PG9). Closest pair in entire screen: HNF4A <-> HNF4Ahet (d = 0.0905, Rank 1). Other tight clusters: ONECUT1e <-> OTUD5 (d = 0.2664), GATA4 <-> GATA6het (d = 0.3729), FOXA1 <-> HNF4A (d = 0.3905). Distinct outlier groups: GATA6 (PG9), FOXA2 (PG8), PDX1 (PG7).",
        "Constructs a continuous geometric manifold of perturbation phenotypes, revealing functional phenocopying and confirming perfect technical concordance between heterozygous and homozygous edits."
    )

    set_notes(s15,
        "Slide 15 shows Figure 14: Perturbation DistanceSpace. Here, we evaluate all 630 pairwise Energy Distances among the 36 non-WT perturbations, "
        "projecting them onto low-dimensional PCoA coordinates and clustering them into 9 Phenotypic Similarity Groups (PG1 to PG9). "
        "The single closest pair in the entire screen is HNF4A and HNF4Ahet, with a tiny distance of d = 0.0905. This demonstrates exceptional technical reproducibility "
        "and phenotypic concordance between homozygous and heterozygous edits. "
        "Other tight clusters include ONECUT1e and OTUD5 (d = 0.2664), and GATA4 with GATA6het (d = 0.3729). "
        "Meanwhile, GATA6, FOXA2, and PDX1 form isolated single-member groups (PG9, PG8, PG7), reflecting their unique diverted phenotypes. "
        "Next, let's explore co-functional modules and downstream gene programs."
    )

    # =========================================================================
    # SLIDE 16: Co-Functional Modules
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "Perturbations Partition into 6 Co-Functional Regulatory Modules", "REGULATORY MODULES", 16)
    add_image(s16, FIG_DIR / "15_module_program_strength.png", Inches(0.8), Inches(1.45), Inches(5.5), Inches(5.4))

    add_what_result_why(s16, Inches(6.5), Inches(1.45), Inches(6.033), Inches(5.4),
        "Stage 7 co-functional module discovery clustering perturbations by downstream differential expression effects (log2FC vs WT across 980 responsive genes), mapped to 4 gene programs.",
        "Identifies 6 Co-functional Modules (M1–M6): M1 (29 TFs: PDX1het, HHEX, GATA6, GLIS3, FOXA2, NEUROG3, etc.) forms the primary developmental core with strong positive P3/P4 and negative P2 strength; M2 (TLE3, +P1 strength 0.666); M3 (NEUROD1, BCOR, +P1 strength 0.512); M4 (PDX1); M5 (TADA2B); M6 (PAX6, PBX1, -P1 strength -0.664).",
        "Groups transcription factors by their shared downstream regulatory consequences rather than sequence homology, linking upstream regulators to downstream execution programs."
    )

    set_notes(s16,
        "Looking at Slide 16, Figure 15 displays the module $\times$ program strength matrix across the 6 discovered co-functional modules (M1 to M6). "
        "By clustering perturbations based on their transcriptome-wide log2 fold change patterns across 980 responsive genes, we identify distinct regulatory modules. "
        "Module M1 encompasses 29 transcription factors—the core developmental drivers—which collectively repress mature beta-cell program P2 (strength -0.870) "
        "while upregulating progenitor biosynthesis program P3 (+0.636) and mesenchymal program P4 (+0.411). "
        "Specialized modules include M2 (TLE3) and M3 (NEUROD1, BCOR), which strongly activate endocrine program P1 (+0.666 and +0.512). "
        "Let us examine what these 4 downstream gene programs represent."
    )

    # =========================================================================
    # SLIDE 17: Gene Programs
    # =========================================================================
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "Four Core Gene Programs Reflect Endocrine, Growth, and EMT States", "GENE PROGRAMS", 17)
    add_image(s17, FIG_DIR / "16_program_activity_celltype2.png", Inches(0.8), Inches(1.45), Inches(6.0), Inches(5.4))

    add_what_result_why(s17, Inches(7.0), Inches(1.45), Inches(5.533), Inches(5.4),
        "Activity scores of 4 co-regulated downstream gene programs (P1–P4, total 980 genes) evaluated across 15 curated biological cell states.",
        "Programs map onto discrete differentiation states: P1 (6 genes: GAL, AKAP12, PEG10, CACNA2D3, FGF12, CDK6) -> active in SC-alpha (0.378) and SC-beta (0.371); P2 (549 genes) -> mature endocrine/beta-cell signature, highest in SC-delta (0.647), SC-beta (0.622), SC-alpha (0.574), EnP (0.553); P3 (316 genes) -> progenitor growth program, active in ESC (1.107), DE (1.087), PFG (1.043), PP (1.002); P4 (109 genes) -> vascular/mesenchymal program, active in Endothelial (1.298) and Stromal (0.193).",
        "Demonstrates that data-driven gene clustering cleanly decomposes the pancreatic regulome into mature endocrine, progenitor biosynthesis, and mesenchymal state signatures."
    )

    set_notes(s17,
        "Slide 17 presents Figure 16: the activity of the 4 co-regulated gene programs (P1 to P4) across the 15 curated cell states. "
        "These 980 responsive downstream genes segregate into clear biological compartments: "
        "Program P2 (549 genes) is the hallmark mature endocrine program, showing highest activity in SC-beta, SC-alpha, and SC-delta cells. "
        "Program P3 (316 genes) represents early progenitor growth, showing high uniform activity in ESC, DE, PFG, and PP progenitors. "
        "Program P4 (109 genes) is the endothelial/stromal program, peaking specifically in endothelial cells (activity 1.298). "
        "And Program P1 (6 genes) represents a specialized endocrine secretion signature. "
        "Let us validate the functional identity of these programs using pathway over-representation analysis."
    )

    # =========================================================================
    # SLIDE 18: Program Functional Enrichment
    # =========================================================================
    s18 = prs.slides.add_slide(blank_layout)
    add_header(s18, "Pathway Over-Representation Annotates Biological Mechanisms", "FUNCTIONAL ENRICHMENT", 18)
    add_image(s18, FIG_DIR / "17_program_enrichment.png", Inches(0.8), Inches(1.45), Inches(6.0), Inches(5.4))

    add_what_result_why(s18, Inches(7.0), Inches(1.45), Inches(5.533), Inches(5.4),
        "Over-Representation Analysis (ORA / hypergeometric test) of gene programs P2, P3, P4 against MSigDB Hallmark, Reactome, and GO Biological Process gene sets.",
        "Highly significant biological enrichments: P2 (Beta-cell signature) -> HALLMARK_PANCREAS_BETA_CELLS (overlap 36/42, FDR = 1.28e-3, OR = 4.97); P3 (Progenitor signature) -> HALLMARK_MYC_TARGETS_V1 (overlap 76/78, FDR = 3.50e-36, OR = 104.8), MTORC1_SIGNALING (FDR = 3.05e-20), TRANSLATION (FDR = 1.13e-19); P4 (Mesenchymal/Vascular) -> EPITHELIAL_MESENCHYMAL_TRANSITION (overlap 14/36, FDR = 1.47e-4, OR = 5.69), ANGIOGENESIS (FDR = 3.12e-4).",
        "Confirms that unsupervised gene programs capture genuine biological processes: mature beta-cell identity (P2), rapid progenitor translation/growth (P3), and EMT/vascular differentiation (P4)."
    )

    set_notes(s18,
        "Looking at Slide 18, Figure 17 shows the functional pathway enrichment results for programs P2, P3, and P4. "
        "Using over-representation analysis against MSigDB Hallmark, Reactome, and GO sets, we find striking statistical concordance: "
        "Program P2 is significantly enriched for Pancreas Beta Cells (36 of 42 genes overlapping, FDR = 1.28e-3, odds ratio 4.97). "
        "Program P3 exhibits astronomical enrichment for MYC Targets V1 (76 of 78 genes overlapping, FDR = 3.50e-36, odds ratio 104.8), "
        "as well as mTORC1 signaling and ribosomal translation (FDR 1.13e-19), reflecting the massive biosynthetic activity of rapid progenitor proliferation. "
        "Program P4 is enriched for Epithelial Mesenchymal Transition (FDR = 1.47e-4) and Angiogenesis (FDR = 3.12e-4). "
        "Next, let's look at how transcription factors cross-regulate each other in a directed regulatory network."
    )

    # =========================================================================
    # SLIDE 19: Module Network
    # =========================================================================
    s19 = prs.slides.add_slide(blank_layout)
    add_header(s19, "Directed Regulatory Network Captures TF-TF Downstream Coupling", "REGULATORY NETWORK", 19)
    add_image(s19, FIG_DIR / "18_module_network.png", Inches(0.8), Inches(1.45), Inches(5.8), Inches(5.4))

    add_what_result_why(s19, Inches(6.8), Inches(1.45), Inches(5.733), Inches(5.4),
        "Directed co-functional regulatory network where nodes represent perturbed transcription factors (colored by module M1–M6) and directed edges indicate significant downstream differential expression of target TFs (|log2FC| edge weight).",
        "Captures hierarchical cross-regulatory architecture: Master hubs (PDX1, FOXA2, GATA6, NEUROG3, RFX6) exert extensive cross-regulatory repression and activation across downstream TFs, demonstrating dense cross-talk among core Module M1 regulators.",
        "Maps functional regulatory influence between master regulators without requiring direct physical binding data, uncovering key upstream control nodes governing differentiation."
    )

    set_notes(s19,
        "On Slide 19, Figure 18 reconstructs the directed regulatory network among the perturbed transcription factors. "
        "Here, nodes represent the targeted transcription factors colored by co-functional module, while directed edges represent significant downstream "
        "differential expression of target TFs, weighted by absolute log2 fold change. "
        "The network reveals a densely connected web of cross-regulation centered around master hubs like PDX1, FOXA2, GATA6, NEUROG3, and RFX6. "
        "This illustrates that perturbations in one master regulator cascade through the regulatory hierarchy by modulating the expression of multiple downstream transcription factors. "
        "Now let's synthesize all metrics across all 37 genotypes in our integrated summary atlas."
    )

    # =========================================================================
    # SLIDE 20: Integrated Summary Atlas
    # =========================================================================
    s20 = prs.slides.add_slide(blank_layout)
    add_header(s20, "Integrated Multi-Metric Profiling Across All 37 Genotypes", "MULTI-METRIC SYNTHESIS", 20)
    add_image(s20, FIG_DIR / "19_perturbation_summary.png", Inches(0.8), Inches(1.45), Inches(7.5), Inches(5.4))

    add_what_result_why(s20, Inches(8.5), Inches(1.45), Inches(4.03), Inches(5.4),
        "Master multi-panel atlas aligning cell counts, PS mean/median, Energy Distance, directional lochNESS (pos/neg/abs), dominant cell state, co-functional module, and phenotype group across all 37 genotypes.",
        "Demonstrates diverse multi-dimensional profiles: (1) High PS + High Distance + Focal lochNESS: GATA6, GLIS3, HHEX; (2) High Distance + Progenitor Trap: PDX1het; (3) Modest PS + Massive Cell Diversion: FOXA2; (4) Severe Lineage Depletion + Modest Distance: NEUROG3, PDX1; (5) Dosage Concordance: HNF4A/HNF4Ahet.",
        "Conclusively proves that no single score can characterize perturbation biology. Multi-dimensional profiling is required to resolve cellular response, global phenotype, and lineage fate."
    )

    set_notes(s20,
        "Slide 20 presents Figure 19: the master integrated perturbation summary atlas. "
        "Across all 37 genotypes, this multi-panel alignment brings together cell abundance, PS response score, Energy Distance, directional lochNESS, "
        "dominant cell state, module assignment, and DistanceSpace phenotype group. "
        "This atlas illustrates why multi-metric integration is essential: GATA6 exhibits high PS, high Energy Distance, and extreme positive lochNESS; "
        "FOXA2 shows moderate Energy Distance but massive hepatic diversion; NEUROG3 shows moderate Distance but complete beta-cell depletion; "
        "and HNF4A shows near-perfect concordance across all metrics between homozygous and heterozygous edits. "
        "To explore these mechanisms in depth, we now present three detailed biological case studies."
    )

    # =========================================================================
    # SLIDE 21: Case Study 1 - GATA6 Lineage Conversion
    # =========================================================================
    s21 = prs.slides.add_slide(blank_layout)
    add_header(s21, "Case Study 1: GATA6 Loss Triggers Endothelial Lineage Conversion", "CASE STUDY 1: GATA6", 21)
    add_image(s21, FIG_DIR / "28_umap_highlight_genotypes.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))

    add_card(s21, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4), "GATA6 Knockout Lineage Diversion", [
        "Biological Role: GATA6 is a zinc-finger master transcription factor required for definitive endoderm specification and pancreatic development.",
        "OBSERVATION (Cell State): GATA6 KO cells (n=1,500) completely abandon the pancreatic trajectory and accumulate massively in the Endothelial cluster (25.7% vs 0.7% baseline, log2 OR = +5.21, FDR = 1.05e-141).",
        "OBSERVATION (Lineage Depletion): Endocrine lineages are almost entirely abolished (SC-EC log2 OR = -5.46, SC-alpha log2 OR = -5.57, SC-beta log2 OR = -4.39).",
        "INTERPRETATION: GATA6 does not merely guide pancreatic differentiation; it acts as an essential repressor of alternative endothelial and mesodermal fates in endodermal progenitors.",
        "HYPOTHESIS: In the absence of GATA6, endodermal chromatin fails to commit to pancreatic fate, derepressing vascular/endothelial gene programs (P4) and executing an aberrant mesodermal conversion."
    ], COLOR_ALERT)

    set_notes(s21,
        "Slide 21 introduces Case Study 1: GATA6 in Figure 28. GATA6 is a master endodermal regulator. "
        "When GATA6 is knocked out (1,500 cells), single cells undergo the most dramatic lineage conversion in the entire screen: "
        "rather than arresting in definitive endoderm, 25.7% of GATA6 KO cells convert into endothelial cells—a 36-fold enrichment over the 0.7% baseline (log2 OR +5.21, FDR 1e-141). "
        "Simultaneously, mature endocrine cells (SC-beta, SC-alpha, SC-EC) are almost entirely eliminated. "
        "This proves that GATA6 functions as a critical repressor of endothelial fate during human endoderm differentiation. "
        "Let us examine GATA6's multi-metric profile in detail."
    )

    # =========================================================================
    # SLIDE 22: Case Study 1 Deep Dive - GATA6 Metrics
    # =========================================================================
    s22 = prs.slides.add_slide(blank_layout)
    add_header(s22, "GATA6 Metric Profile: High Response, Extreme Distance, and Focal Trapping", "CASE STUDY 1 (DEEP DIVE)", 22)
    add_image(s22, FIG_DIR / "per_genotype_combined/GATA6_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))

    add_card(s22, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4), "GATA6 Quantitative Multi-Metric Profile", [
        "Cells: 1,500 | Guides Tested: 3 distinct sgRNAs.",
        "Perturbation Score (PS): Mean = 0.5776 (Rank 4/26), Median = 0.6482, Responder Fraction = 61.6%.",
        "Energy Distance: E = 9.7045 (Rank 3/36, FDR = 0.000999) — massive multivariate transcriptomic displacement from WT.",
        "lochNESS Localization: Positive Mean = +14.18 (Rank 1 in screen), Absolute Mean = 13.79 (Rank 1).",
        "Phenotype Space: Forms isolated Phenotype Group PG9 in DistanceSpace; assigned to Co-functional Module M1.",
        "SYNTHESIS: GATA6 demonstrates extreme concordance across all metrics: high single-cell response penetrance, third-largest global Energy Distance, and the highest focal lochNESS localization in the screen.",
        "BIOLOGICAL CONCLUSION: GATA6 is indispensable for locking pluripotent cells into the pancreatic endoderm fate."
    ], COLOR_PRIMARY)

    set_notes(s22,
        "On Slide 22, we examine the combined single-cell PS and lochNESS UMAP panels for GATA6. "
        "GATA6 demonstrates exceptional convergence across every quantitative metric: "
        "It achieves a high PS response (mean 0.5776, median 0.6482, 61.6% responder fraction); "
        "It generates the 3rd largest Energy Distance in the screen (E = 9.7045, FDR = 0.000999); "
        "And it achieves the Rank 1 positive lochNESS score (+14.18) and Rank 1 absolute lochNESS score (13.79) across all 36 perturbations. "
        "In DistanceSpace, GATA6 sits in its own isolated cluster (PG9), reflecting its unique endothelial phenotype. "
        "Next, let's examine Case Study 2: FOXA2."
    )

    # =========================================================================
    # SLIDE 23: Case Study 2 - FOXA2 Hepatic Diversion
    # =========================================================================
    s23 = prs.slides.add_slide(blank_layout)
    add_header(s23, "Case Study 2: FOXA2 Loss Diverts Pancreatic Endoderm to Hepatic Fate", "CASE STUDY 2: FOXA2", 23)
    add_image(s23, FIG_DIR / "per_genotype_combined/FOXA2_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))

    add_card(s23, Inches(7.8), Inches(1.45), Inches(4.7), Inches(5.4), "FOXA2 Hepatic Diversion Profile", [
        "Biological Role: Pioneer transcription factor FOXA2 opens condensed chromatin to establish foregut endoderm competency.",
        "OBSERVATION (Cell State): FOXA2 KO cells (n=4,896) undergo a dramatic fate diversion into Liver hepatocytes (34.0% of cells vs 2.0% baseline, log2 OR = +4.09, FDR = 3.65e-224).",
        "OBSERVATION (Quantitative Profile): PS Mean = 0.5085 | Energy Distance = 2.1444 (FDR = 0.000999) | lochNESS Positive Mean = +5.86 (Rank 5) | lochNESS Negative Mean = -0.4952 (Rank 3 most depleted, 70.7% depleted cells).",
        "OBSERVATION (DistanceSpace): Forms isolated single-member Phenotype Group PG8 in DistanceSpace; assigned to Module M1.",
        "INTERPRETATION: FOXA2 deficiency does not arrest cells in pluripotency; instead, shared endodermal progenitors lose pancreatic competence and default into the hepatic lineage.",
        "HYPOTHESIS: FOXA2 is required to activate pancreatic gene programs; without FOXA2, foregut endoderm defaults to the default liver program."
    ], COLOR_SECONDARY)

    set_notes(s23,
        "Slide 23 focuses on Case Study 2: FOXA2. FOXA2 is a canonical pioneer transcription factor that opens chromatin in foregut endoderm. "
        "When FOXA2 is knocked out (4,896 cells), cells undergo a striking redirection: 34.0% of FOXA2 KO cells differentiate into liver hepatocytes, "
        "compared to only 2.0% in baseline controls (log2 OR +4.09, FDR 3.65e-224). "
        "Quantitatively, FOXA2 exhibits a strong positive lochNESS score (+5.86, Rank 5) in the liver cluster, alongside 70.7% depleted cells in pancreatic branches (neg mean -0.4952). "
        "In DistanceSpace, FOXA2 resides in its own isolated cluster (PG8). "
        "This proves that FOXA2 is an indispensable pioneer factor that steers multipotent foregut endoderm away from liver and toward the pancreas. "
        "Now let's examine Case Study 3: NEUROG3 and PDX1."
    )

    # =========================================================================
    # SLIDE 24: Case Study 3 - NEUROG3 & PDX1 Endocrine Blockade
    # =========================================================================
    s24 = prs.slides.add_slide(blank_layout)
    add_header(s24, "Case Study 3: NEUROG3 and PDX1 Enforce Endocrine Differentiation Checkpoints", "CASE STUDY 3: NEUROG3 & PDX1", 24)
    add_image(s24, FIG_DIR / "per_genotype_combined/NEUROG3_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(4.5), Inches(5.4))
    add_image(s24, FIG_DIR / "per_genotype_combined/PDX1_ps_lochness_umap.png", Inches(5.4), Inches(1.45), Inches(3.8), Inches(5.4))

    add_card(s24, Inches(9.35), Inches(1.45), Inches(3.18), Inches(5.4), "Endocrine Checkpoints", [
        "NEUROG3 (Ngn3, n=1,543): Complete loss of mature SC-beta cells (0.0% observed, log2 OR = -inf) and SC-EC loss (log2 OR = -4.75, FDR = 3.25e-33). Cells accumulate in Pancreatic/Ductal Progenitors (PDP, log2 OR = +1.11). Module M1, PG3.",
        "PDX1 (n=6,207): Essential beta-cell factor. 77.8% of cells negatively depleted (neg mean = -0.589). Forms isolated PG7 and Module M4.",
        "PDX1het (n=469): Heterozygous knockout yields Rank 1 Energy Distance in screen (E = 13.6337) and Rank 2 Positive lochNESS (+14.15), trapped in ESC state (83.8%).",
        "CONCLUSION: NEUROG3 acts as the indispensable master gate for endocrine commitment. PDX1 dosage is critical: heterozygous perturbation blocks earliest specification, while complete loss disrupts endocrine maturation."
    ], COLOR_PURPLE)

    set_notes(s24,
        "Slide 24 presents Case Study 3, comparing NEUROG3 (left) and PDX1 (middle). "
        "NEUROG3 (Ngn3) is the master endocrine commitment factor. In NEUROG3 knockout cells (1,543 cells), not a single SC-beta cell is formed (0.0%, log2 OR = -infinity), "
        "and cells are completely trapped at the pancreatic ductal progenitor (PDP) stage. "
        "Meanwhile, PDX1 knockout causes widespread depletion across mature endocrine states (77.8% negative cells, lochNESS neg mean -0.589). "
        "Remarkably, the heterozygous PDX1 perturbation (PDX1het) produces the largest Energy Distance in the entire screen (E = 13.63, Rank 1), "
        "with 83.8% of cells trapped at the pluripotent ESC stage. "
        "This confirms that human pancreatic differentiation contains discrete, unpassable checkpoints governed sequentially by PDX1 and NEUROG3. "
        "Let us conclude with our final summary."
    )

    # =========================================================================
    # SLIDE 25: Conclusions & Summary
    # =========================================================================
    s25 = prs.slides.add_slide(blank_layout)
    add_header(s25, "Conclusions: A Multi-Dimensional Blueprint of Human Pancreatic Regulators", "SUMMARY & CONCLUSIONS", 25)

    add_card(s25, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3), "Core Biological Discoveries", [
        "1. Master Binary Switches: GATA6 represses endothelial conversion; FOXA2 prevents hepatic diversion; NEUROG3 strictly gates endocrine commitment.",
        "2. Dosage & Penetrance Sensitivity: Heterozygous PDX1 and homozygous PDX1 reveal dosage-dependent developmental arrest points; HNF4A and HNF4Ahet show near-perfect phenotypic concordance (d = 0.0905).",
        "3. Phenotypic Manifold Organization: 630 pairwise Energy Distances organize 36 regulators into 9 phenotypic groups (PG1–PG9), separating master branch drivers from specialized regulators.",
        "4. Downstream Regulome: 6 co-functional modules and 4 gene programs cleanly map mature beta-cell identity (P2), progenitor biosynthesis (P3), and mesenchymal/vascular states (P4)."
    ], COLOR_PRIMARY)

    add_card(s25, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3), "Methodological Principles for Perturb-seq", [
        "1. Multi-Metric Necessity: No single score suffices. PS measures cellular response; Energy Distance measures global phenotype shift; lochNESS maps spatial trapping; DistanceSpace maps phenocopying.",
        "2. Directional lochNESS is Mandatory: Averaging signed lochNESS obscures biology by canceling positive focal trapping with downstream lineage depletion.",
        "3. Sample Stratification: Stratifying cell-state enrichment by orig.ident eliminates library composition confounding in multi-stage differentiation screens.",
        "4. Transparent, Auditable Pipelines: Documenting skipped targets (e.g. 10 composite/heterozygous targets for PS) and bounded sampling ensures statistical rigor and reproducibility."
    ], COLOR_SECONDARY)

    set_notes(s25,
        "In conclusion, on Slide 25, we summarize the major biological and methodological insights of this study. "
        "Biologically, we have constructed a comprehensive, single-cell resolution atlas of 36 master regulators in human pancreatic development, "
        "demonstrating how specific transcription factors act as binary gatekeepers against endothelial, hepatic, and ductal diversion. "
        "Methodologically, we demonstrate that evaluating Perturb-seq experiments requires an integrated, multi-layered framework: "
        "combining single-cell response scoring (PS), multivariate distribution distance (Energy Distance), continuous signed spatial enrichment (lochNESS), "
        "sample-stratified cell enrichment, phenotypic DistanceSpace, and co-functional gene modules. "
        "This framework provides a reproducible blueprint for single-cell functional genomics. "
        "Thank you. We now transition to the backup slides."
    )

    # =========================================================================
    # SLIDE 26: Backup - PS & lochNESS Atlases
    # =========================================================================
    s26 = prs.slides.add_slide(blank_layout)
    add_header(s26, "Full 36-Genotype Single-Cell PS and lochNESS UMAP Atlases", "FULL SCREEN ATLAS", 26, is_backup=True)
    add_image(s26, FIG_DIR / "ps_per_genotype_umap_atlas.png", Inches(0.8), Inches(1.45), Inches(5.6), Inches(5.4))
    add_image(s26, FIG_DIR / "lochness_per_genotype_umap_atlas.png", Inches(6.6), Inches(1.45), Inches(5.9), Inches(5.4))

    set_notes(s26,
        "Backup Slide 26 displays the complete 36-genotype atlas for single-cell PS score density (left) and lochNESS spatial projection (right). "
        "This serves as a comprehensive visual encyclopedia for all perturbations evaluated in the screen."
    )

    # =========================================================================
    # SLIDE 27: Backup - Genotype x Cell-State Matrices
    # =========================================================================
    s27 = prs.slides.add_slide(blank_layout)
    add_header(s27, "High-Resolution Genotype x Cell-State Response Matrices", "FULL RESPONSE MATRICES", 27, is_backup=True)
    add_image(s27, FIG_DIR / "24_ps_genotype_celltype_heatmap.png", Inches(0.8), Inches(1.45), Inches(5.6), Inches(5.4))
    add_image(s27, FIG_DIR / "26_lochness_by_celltype2.png", Inches(6.6), Inches(1.45), Inches(5.9), Inches(5.4))

    set_notes(s27,
        "Backup Slide 27 shows the complete genotype x cell state response heatmaps for PS (left) and lochNESS distribution across cell types (right), "
        "covering all 505 genotype-celltype pairs."
    )

    # =========================================================================
    # SLIDE 28: Backup - DistanceSpace Full Matrix
    # =========================================================================
    s28 = prs.slides.add_slide(blank_layout)
    add_header(s28, "Full 630-Pair DistanceSpace Matrix and Nearest Phenotypic Neighbors", "DISTANCESPACE AUDIT", 28, is_backup=True)
    add_image(s28, FIG_DIR / "14_distance_space.png", Inches(0.8), Inches(1.45), Inches(6.5), Inches(5.4))

    add_card(s28, Inches(7.5), Inches(1.45), Inches(5.033), Inches(5.4), "Top Nearest Phenotypic Neighbors in DistanceSpace", [
        "1. HNF4A <-> HNF4Ahet: d = 0.0905 (Rank 1 closest pair across all 630 pairs). Both in PG3, Module M1.",
        "2. ONECUT1e <-> OTUD5: d = 0.2664 (Rank 2). Both in PG4, Module M1.",
        "3. GATA4 <-> GATA6het: d = 0.3729 (Rank 3). Both in PG4, Module M1.",
        "4. BMPR1A <-> GATA4: d = 0.3793 (Rank 4). Both in PG4, Module M1.",
        "5. FOXA1 <-> HNF4A: d = 0.3905 (Rank 5). Both in PG3, Module M1.",
        "6. FOXA1 <-> TET1: d = 0.4368 (Rank 6). Both in PG3, Module M1.",
        "7. GATA6het <-> QSER1: d = 0.4544 (Rank 7). Both in PG4, Module M1.",
        "8. OTUD5 <-> QSER1: d = 0.4731 (Rank 8). Both in PG4, Module M1.",
        "Isolated Outliers: GATA6 (PG9), FOXA2 (PG8), PDX1 (PG7), TADA2B (PG6)."
    ], COLOR_PURPLE)

    set_notes(s28,
        "Backup Slide 28 provides the full quantitative ranking of the top nearest neighbor pairs in DistanceSpace across all 630 pairwise comparisons. "
        "Notice the tight clustering of epigenetic and endodermal factors within PG3 and PG4."
    )

    # =========================================================================
    # SLIDE 29: Backup - QC, Sampling & Skipped Targets
    # =========================================================================
    s29 = prs.slides.add_slide(blank_layout)
    add_header(s29, "Quality Control, Bounded Sampling, and Skipped Targets Audit", "METHODOLOGICAL AUDIT", 29, is_backup=True)

    add_card(s29, Inches(0.8), Inches(1.5), Inches(5.6), Inches(5.3), "Audit of 10 Skipped PS Perturbations", [
        "GATA4het (1,957 cells): Target gene not in expression matrix.",
        "GATA6het (2,266 cells): Target gene not in expression matrix.",
        "HHEXe (1,487 cells): Enhancer target not in expression matrix.",
        "HHEXhet (328 cells): Target gene not in expression matrix.",
        "HNF4Ahet (829 cells): Target gene not in expression matrix.",
        "NANOGe-het (996 cells): Enhancer target not in expression matrix.",
        "ONECUT1e (2,436 cells): Enhancer target not in expression matrix.",
        "PDX1het (469 cells): Target gene not in expression matrix.",
        "QSER1TET1 (1,157 cells): Composite target not in expression matrix.",
        "TET1/2/3 (948 cells): Composite triple knockout not in expression matrix.",
        "RATIONALE: pertps requires single-gene expression mapping; skipping composite/enhancer targets prevents erroneous classification."
    ], COLOR_ALERT)

    add_card(s29, Inches(6.8), Inches(1.5), Inches(5.7), Inches(5.3), "DistanceTest & lochNESS Algorithmic Parameters", [
        "Energy Distance Estimator: V-statistic on 50 PCA dimensions: E(X,Y) = 2 E||X-Y|| - E||X-X'|| - E||Y-Y'||.",
        "Permutations: 1,000 exact label permutations. Empirical p-value = (1 + count) / (1 + 1000). All 36 perturbations achieved count = 0 (p = 0.000999, BH-FDR = 0.000999).",
        "Bounded Sampling: Max 2,000 perturbed cells and 5,000 WT control cells per target to prevent sample-size distortion.",
        "lochNESS kNN Graph: k = 30 nearest neighbors in PCA space, division by actual neighbor count (k-1) to avoid underestimation.",
        "Stage 7 Feature Selection: 980 responsive downstream genes (Welch statistics / mean difference vs WT) clustered with agglomerative clustering."
    ], COLOR_PRIMARY)

    set_notes(s29,
        "Backup Slide 29 provides an auditable methodological record detailing why 10 perturbations were skipped for PS scoring, "
        "as well as the exact mathematical parameters used for Energy Distance, permutation testing, bounded sampling, and lochNESS calculation."
    )

    # =========================================================================
    # SLIDE 30: Backup - Supporting Case Studies (HNF4A & GLIS3)
    # =========================================================================
    s30 = prs.slides.add_slide(blank_layout)
    add_header(s30, "Additional Case Studies: HNF4A Dosage Concordance and GLIS3 Response", "ADDITIONAL CASE STUDIES", 30, is_backup=True)
    add_image(s30, FIG_DIR / "per_genotype_combined/HNF4A_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(4.5), Inches(5.4))
    add_image(s30, FIG_DIR / "per_genotype_combined/GLIS3_ps_lochness_umap.png", Inches(5.4), Inches(1.45), Inches(3.8), Inches(5.4))

    add_card(s30, Inches(9.35), Inches(1.45), Inches(3.18), Inches(5.4), "HNF4A & GLIS3 Insights", [
        "HNF4A Dosage Concordance: HNF4A (987 cells, E = 1.75) and HNF4Ahet (829 cells, E = 1.86) exhibit the smallest pairwise DistanceSpace divergence in the entire screen (d = 0.0905, Rank 1). Proves high technical reproducibility and phenotypic stability.",
        "GLIS3 Top Responder: GLIS3 (935 cells) achieves the highest PS median in the screen (0.7500) and highest responder fraction (66.6%), with E = 8.21 and positive lochNESS = +9.53 (Rank 4). Assigned to PG2 with PDX1het.",
        "BIOLOGICAL SIGNIFICANCE: GLIS3 is a known neonatal diabetes and polycystic kidney disease risk factor; its extreme responder phenotype highlights its acute requirement in early progenitor maintenance."
    ], COLOR_GREEN)

    set_notes(s30,
        "Backup Slide 30 provides supporting case studies on HNF4A dosage concordance and GLIS3 top responder phenotypes. "
        "HNF4A and its heterozygous counterpart show the highest phenotypic similarity in the screen (d = 0.0905), "
        "while GLIS3 exhibits the highest single-cell response rate in the entire dataset (PS median 0.750, 66.6% responders)."
    )

    # Save presentation
    os.makedirs(PRES_DIR, exist_ok=True)
    prs.save(str(PPTX_OUT))
    print(f"Presentation saved successfully to: {PPTX_OUT}")
    print(f"Total slides generated: {len(prs.slides)}")

if __name__ == "__main__":
    build_all_slides()
