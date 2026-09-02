import os
import sys
from PIL import Image
import pptx
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

def build_presentation():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color Constants - Clean Professional Palette
    COLOR_NAVY = RGBColor(15, 23, 42)          # #0F172A - Main Titles
    COLOR_DARK_SLATE = RGBColor(30, 41, 59)    # #1E293B - Body Text
    COLOR_MUTED = RGBColor(100, 116, 139)      # #64748B - Captions/Footers
    COLOR_SUBTITLE = RGBColor(71, 85, 105)     # #475569 - Subtitles
    COLOR_CARD_BG = RGBColor(248, 250, 252)    # #F8FAFC - Card Background
    COLOR_CARD_BORDER = RGBColor(226, 232, 240)# #E2E8F0 - Card Border
    COLOR_BLUE_ACCENT = RGBColor(37, 99, 235)  # #2563EB - Primary Blue
    COLOR_CYAN_ACCENT = RGBColor(14, 165, 233) # #0EA5E9 - Data QC
    COLOR_GREEN_ACCENT = RGBColor(5, 150, 105) # #059669 - Positive / Green
    COLOR_AMBER_ACCENT = RGBColor(217, 119, 6) # #D97706 - WIP / Phenotyping
    COLOR_RED_ACCENT = RGBColor(220, 38, 38)   # #DC2626 - Negative / Severity
    COLOR_PURPLE_ACCENT = RGBColor(124, 58, 237) # #7C3AED - pertTF / ML
    COLOR_WHITE = RGBColor(255, 255, 255)
    COLOR_DARK_HERO_BG = RGBColor(11, 19, 43)

    BADGE_STYLES = {
        'BIOLOGY': {
            'bg': RGBColor(239, 246, 255),
            'border': RGBColor(147, 197, 253),
            'text': RGBColor(29, 78, 216),
            'label': 'BIOLOGICAL FOUNDATION'
        },
        'QC': {
            'bg': RGBColor(240, 253, 250),
            'border': RGBColor(153, 246, 228),
            'text': RGBColor(13, 148, 136),
            'label': 'DESCRIPTIVE DATA QC'
        },
        'MODEL': {
            'bg': RGBColor(245, 243, 255),
            'border': RGBColor(196, 181, 253),
            'text': RGBColor(109, 40, 217),
            'label': 'pertTF ARCHITECTURE'
        },
        'GENERALIZATION': {
            'bg': RGBColor(238, 242, 255),
            'border': RGBColor(165, 180, 252),
            'text': RGBColor(67, 56, 202),
            'label': 'GENERALIZATION BENCHMARKS'
        },
        'PIVOT': {
            'bg': RGBColor(255, 247, 237),
            'border': RGBColor(254, 215, 170),
            'text': RGBColor(194, 65, 12),
            'label': 'CRITICAL SCIENTIFIC PIVOT'
        },
        'WIP': {
            'bg': RGBColor(254, 243, 199),
            'border': RGBColor(252, 211, 77),
            'text': RGBColor(180, 83, 9),
            'label': 'PHENOTYPE DECOMPOSITION'
        },
        'CASE_STUDY': {
            'bg': RGBColor(236, 253, 245),
            'border': RGBColor(167, 243, 208),
            'text': RGBColor(4, 120, 87),
            'label': 'BIOLOGICAL CASE STUDY'
        },
        'SYNTHESIS': {
            'bg': RGBColor(245, 243, 255),
            'border': RGBColor(196, 181, 253),
            'text': RGBColor(109, 40, 217),
            'label': 'SYNTHESIS & FUTURE MODELS'
        },
        'BACKUP': {
            'bg': RGBColor(241, 245, 249),
            'border': RGBColor(203, 213, 225),
            'text': RGBColor(51, 65, 85),
            'label': 'TECHNICAL BACKUP / AUDIT'
        }
    }

    def add_header(slide, category, title, subtitle, badge_type='BIOLOGY'):
        header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.35), Inches(9.6), Inches(0.95))
        tf = header_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        
        # Category Tracker
        p_cat = tf.paragraphs[0]
        p_cat.text = category.upper()
        p_cat.font.size = Pt(9.5)
        p_cat.font.bold = True
        p_cat.font.color.rgb = COLOR_BLUE_ACCENT if badge_type in ['BIOLOGY', 'QC'] else (COLOR_AMBER_ACCENT if badge_type == 'WIP' else (COLOR_PURPLE_ACCENT if badge_type in ['MODEL', 'GENERALIZATION', 'SYNTHESIS'] else (COLOR_GREEN_ACCENT if badge_type == 'CASE_STUDY' else COLOR_MUTED)))
        p_cat.space_after = Pt(2)
        
        # Title
        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.size = Pt(20)
        p_title.font.bold = True
        p_title.font.color.rgb = COLOR_NAVY
        p_title.space_after = Pt(2)
        
        # Subtitle
        p_sub = tf.add_paragraph()
        p_sub.text = subtitle
        p_sub.font.size = Pt(11.5)
        p_sub.font.color.rgb = COLOR_SUBTITLE
        
        # Badge
        badge_info = BADGE_STYLES.get(badge_type, BADGE_STYLES['BIOLOGY'])
        bx = Inches(10.6)
        by = Inches(0.4)
        bw = Inches(1.933)
        bh = Inches(0.36)
        
        badge_rect = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, by, bw, bh)
        badge_rect.fill.solid()
        badge_rect.fill.fore_color.rgb = badge_info['bg']
        badge_rect.line.color.rgb = badge_info['border']
        badge_rect.line.width = Pt(1)
        
        btf = badge_rect.text_frame
        btf.word_wrap = False
        btf.vertical_anchor = MSO_ANCHOR.MIDDLE
        bp = btf.paragraphs[0]
        bp.text = badge_info['label']
        bp.font.size = Pt(8.5)
        bp.font.bold = True
        bp.font.color.rgb = badge_info['text']
        bp.alignment = PP_ALIGN.CENTER

    def add_card(slide, left, top, width, height, bg_rgb=COLOR_CARD_BG, border_rgb=COLOR_CARD_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_rgb
        card.line.color.rgb = border_rgb
        card.line.width = Pt(1)
        return card

    def add_image_fitted(slide, img_path, left, top, max_width, max_height):
        if not os.path.exists(img_path):
            print(f"Warning: Image not found: {img_path}")
            return None
        with Image.open(img_path) as img:
            orig_w, orig_h = img.size
        
        aspect = orig_w / orig_h
        target_aspect = max_width / max_height
        
        if aspect > target_aspect:
            w = max_width
            h = max_width / aspect
            x = left
            y = top + (max_height - h) / 2
        else:
            h = max_height
            w = max_height * aspect
            y = top
            x = left + (max_width - w) / 2
            
        pic = slide.shapes.add_picture(img_path, x, y, w, h)
        return pic

    def add_notes(slide, text):
        notes_slide = slide.notes_slide
        text_frame = notes_slide.notes_text_frame
        text_frame.text = text.strip()

    def format_bullets(tf, bullet_list, default_font_size=11, bold_prefix_len=0):
        for idx, item in enumerate(bullet_list):
            p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
            p.text = item
            p.font.size = Pt(default_font_size)
            p.font.color.rgb = COLOR_DARK_SLATE
            p.space_after = Pt(6)
            p.level = 0
            if ":" in item and bold_prefix_len == 0:
                parts = item.split(":", 1)
                p.text = ""
                r1 = p.add_run()
                r1.text = parts[0] + ":"
                r1.font.bold = True
                r1.font.color.rgb = COLOR_NAVY
                r2 = p.add_run()
                r2.text = parts[1]
                r2.font.bold = False

    # SLIDE 1: Title Slide
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = COLOR_DARK_HERO_BG
    bg1.line.fill.background()

    tcard = add_card(s1, Inches(1.2), Inches(1.2), Inches(10.933), Inches(5.1), 
                     bg_rgb=RGBColor(18, 30, 66), border_rgb=RGBColor(45, 62, 110))
    
    t_box = s1.shapes.add_textbox(Inches(1.6), Inches(1.6), Inches(10.133), Inches(4.3))
    ttf = t_box.text_frame
    ttf.word_wrap = True
    
    p = ttf.paragraphs[0]
    p.text = "BIOLOGY  •  COMPUTATIONAL GENOMICS  •  PERTURBATION MODELING"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(96, 165, 250)
    p.space_after = Pt(12)
    
    p = ttf.add_paragraph()
    p.text = "Decoding Human Pancreatic Differentiation\n& Monogenic Diabetes"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(10)
    
    p = ttf.add_paragraph()
    p.text = "From Knockout Villages and Context-Aware Transformers to Multi-Dimensional Phenotype Decomposition"
    p.font.size = Pt(14)
    p.font.color.rgb = RGBColor(203, 213, 225)
    p.space_after = Pt(24)
    
    p = ttf.add_paragraph()
    p.text = "A Unified Scientific Framework Across Developmental Perturbation Biology, Machine Learning, and Statistical Phenotyping"
    p.font.size = Pt(12)
    p.font.color.rgb = RGBColor(148, 163, 184)

    add_notes(s1, 
        "Welcome everyone. Today I am presenting a complete, unified scientific story spanning developmental biology, single-cell perturbation genomics, and machine learning.\n\n"
        "Our core progression follows the natural arc of discovery: we begin with a foundational biological question in human pancreatic development and diabetes genetics. We establish an experimental knockout village to capture cell-state and lineage dynamics. We rigorously examine data quality and perturbation signal before introducing pertTF—a context-aware transformer designed to learn and generalize perturbation operators across unseen biological contexts.\n\n"
        "We then address the fundamental limitation of predictive ML alone: understanding what biological dimensions constitute the phenotype. In our ongoing work, we decompose perturbation effects into single-cell response strength (PS), global transcriptomic magnitude (Energy Distance), and directional cell-state localization (lochNESS), closing the loop to guide future phenotype-aware models.")

    # SLIDE 2: Scientific Narrative Spine
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "Overview & Scientific Progression", "The Master Scientific Narrative Arc", 
               "A continuous progression from biological question and data characterization to transformer modeling and phenotype decomposition", "SYNTHESIS")
    
    pillars = [
        ("1. BIOLOGY", "Human Genetics", "Monogenic diabetes mutations & 18-day directed differentiation protocol across 5 developmental stages.", COLOR_BLUE_ACCENT),
        ("2. DATA & QC", "Knockout Village", "111,581 single cells across 79 clones; structured perturbation signal, lineage diversion & endocrine competition.", COLOR_CYAN_ACCENT),
        ("3. pertTF MODEL", "Transformer ML", "Dual-input architecture & multi-task loss learning transferable representations of perturbation operators.", COLOR_PURPLE_ACCENT),
        ("4. GENERALIZATION", "Unseen Prediction", "Generalizing to unobserved cell types (PDP), unmutated genes (GNN PPI), CRISPRi, and primary islet T2D heterogeneity.", RGBColor(99, 102, 241)),
        ("5. DECOMPOSITION", "3-Axis Framework", "Decomposing perturbation biology into response strength (PS), global magnitude (Energy Distance), and localization (lochNESS).", COLOR_AMBER_ACCENT),
        ("6. SYNTHESIS", "Future Models", "Cross-metric coupling/decoupling, DistanceSpace manifolds, and closing the loop for phenotype-aware predictive modeling.", COLOR_GREEN_ACCENT)
    ]
    
    for i, (col_title, col_sub, col_body, col_color) in enumerate(pillars):
        x = Inches(0.8 + i * 1.98)
        y = Inches(1.5)
        w = Inches(1.86)
        h = Inches(5.4)
        
        card = add_card(s2, x, y, w, h, bg_rgb=COLOR_CARD_BG, border_rgb=COLOR_CARD_BORDER)
        strip = s2.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, Inches(0.12))
        strip.fill.solid()
        strip.fill.fore_color.rgb = col_color
        strip.line.fill.background()
        
        tb = s2.shapes.add_textbox(x + Inches(0.1), y + Inches(0.2), w - Inches(0.2), h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        
        p = tf.paragraphs[0]
        p.text = col_title
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col_color
        p.space_after = Pt(2)
        
        p = tf.add_paragraph()
        p.text = col_sub
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_NAVY
        p.space_after = Pt(8)
        
        p = tf.add_paragraph()
        p.text = col_body
        p.font.size = Pt(10)
        p.font.color.rgb = COLOR_DARK_SLATE
        
    add_notes(s2, 
        "This slide presents the overarching spine of our presentation.\n\n"
        "The story progresses through six continuous stages: (1) We define the biological question rooted in human diabetes genetics; (2) We build and characterize the single-cell perturbation dataset, verifying data quality and lineage rewiring; (3) We introduce pertTF to learn context-aware representations; (4) We benchmark generalization across unseen cell types, unmutated genes, and primary human disease; (5) We return to computational biology to decompose phenotypes into three orthogonal axes; and (6) We synthesize these dimensions into a closed-loop framework for next-generation perturbation models.")

    # SLIDE 3: Biological Question
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Biological Question & Medical Motivation", 
               "Pancreatic Beta-Cell Development & Monogenic Diabetes Genetics", 
               "Systematic functional dissection of 30 human transcription factors across in vitro pancreatic differentiation", "BIOLOGY")
    
    add_image_fitted(s3, "cropped_panels/precursor_fig1a_genes.png", Inches(0.8), Inches(1.45), Inches(3.2), Inches(5.4))
    add_image_fitted(s3, "cropped_panels/precursor_fig1b_workflow.png", Inches(4.1), Inches(1.45), Inches(3.5), Inches(5.4))
    
    card3 = add_card(s3, Inches(7.7), Inches(1.45), Inches(4.833), Inches(5.4))
    tb3 = s3.shapes.add_textbox(Inches(7.9), Inches(1.6), Inches(4.433), Inches(5.1))
    tf3 = tb3.text_frame
    tf3.word_wrap = True
    
    bullets3 = [
        "Clinical Motivation: Monogenic diabetes forms (MODY, neonatal diabetes) and T2D GWAS loci implicate transcription factors (TFs) essential for human beta-cell specification and insulin homeostasis.",
        "Target Selection (30 Genes): Curated high-confidence developmental regulators, including canonical lineage TFs (PDX1, NEUROG3, FOXA2, GATA6, RFX6, PAX6, MNX1, ARX) and epigenetic modifiers (TET1-3, KDM2B, TADA2B).",
        "Directed Differentiation Paradigm: Human pluripotent stem cells (hPSCs) differentiated through 5 physiological stages: Definitive Endoderm (DE, Day 3) → Primitive Foregut (PFG, Day 6) → Pancreatic Progenitor (PP, Day 13) → Stem Cell-Derived Islets (SC-islet, Day 18).",
        "The Biological Challenge: In vitro differentiation produces mixtures of functional beta-cells (SC-β) alongside off-target non-endocrine cells and aberrant enterochromaffin (SC-EC) cells. How do specific gene losses rewire this developmental trajectory?"
    ]
    format_bullets(tf3, bullets3, default_font_size=10.5)
    
    add_notes(s3, 
        "Let us begin with the biological question. Human pancreatic development requires pluripotent cells to navigate successive developmental branchpoints to generate insulin-producing beta-cells.\n\n"
        "Panel 1a highlights the 30 targeted transcription factors and chromatin regulators selected for this study. These genes were chosen based on human genetics: monogenic diabetes forms like MODY (Maturity-Onset Diabetes of the Young), permanent neonatal diabetes, and developmental pancreatic agenesis.\n\n"
        "Panel 1b shows the directed differentiation protocol. Over 18 days, hPSCs transition through Definitive Endoderm, Primitive Foregut, Pancreatic Progenitors, and finally Stem Cell-derived Islets.\n\n"
        "However, in vitro differentiation frequently suffers from low beta-cell yields and aberrant cell types. To understand how every single transcription factor guides this fate choice, we designed a high-throughput knockout village experiment.")

    # SLIDE 4: Experimental System
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Experimental System | Knockout Village Design", 
               "Knockout Village Strategy & Single-Cell Differentiation Kinetics", 
               "Pooling 79 sequence-verified hPSC knockout clones in a shared culture eliminates batch effects and resolves kinetics", "BIOLOGY")
    
    add_image_fitted(s4, "cropped_panels/precursor_fig1cd_kinetics.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s4, "cropped_panels/precursor_fig1e_pca.png", Inches(4.5), Inches(1.45), Inches(3.2), Inches(5.4))
    
    card4 = add_card(s4, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb4 = s4.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf4 = tb4.text_frame
    tf4.word_wrap = True
    
    bullets4 = [
        "The Knockout Village Design: 79 individual CRISPR-Cas9 knockout and heterozygous hPSC clones (covering 30 genes + wild-type controls) were pooled into a single shared culture, eliminating technical batch variation.",
        "Genotype Verification: Every clone underwent Sanger sequencing and targeted PCR to confirm frameshift loss-of-function or targeted deletions prior to pooling.",
        "Deep Single-Cell Transcriptomics: Resolved >111,581 single-cell transcriptomes across all differentiation stages with deep sequencing (~20,000 read pairs per cell).",
        "Kinetic Representation (Fig 1c,d): Genotypes exhibited distinct survival and expansion kinetics across timepoints, revealing stage-specific selection windows.",
        "Pseudo-Bulk PCA Trajectory (Fig 1e): External and internal wild-type controls align along the canonical developmental path (DE → PFG → PP → Day 18), establishing the physiological validity of the village system."
    ]
    format_bullets(tf4, bullets4, default_font_size=10.5)
    
    add_notes(s4, 
        "Slide 4 illustrates how the knockout village was constructed. Performing 79 separate differentiations in individual culture wells would introduce massive technical batch effects. Instead, we established sequence-verified knockout clones, pooled them into a single 'village' culture, and co-differentiated them simultaneously.\n\n"
        "In Panel 1c and 1d, you see the representation and absolute cell counts of individual genotypes across differentiation. Notice that while some genotypes maintain steady representation, others drop out early or expand late, revealing stage-specific selective pressures.\n\n"
        "Panel 1e confirms global developmental fidelity: principal component analysis of pseudo-bulk single-cell profiles demonstrates continuous progression from pluripotent stem cells through DE, PFG, PP, and endocrine stages.")

    # SLIDE 5: Descriptive QC - Landscape
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Descriptive Data QC | Cellular Landscape", 
               "Single-Cell Differentiation Landscape & Cell-State Manifold", 
               "Structuring 111,581 single cells across 10 curated developmental cell states and 5 differentiation stages", "QC")
    
    add_image_fitted(s5, "../../figures/01_umap_celltype2.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s5, "../../figures/02_umap_development_stage.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card5 = add_card(s5, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb5 = s5.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf5 = tb5.text_frame
    tf5.word_wrap = True
    
    bullets5 = [
        "Dataset Tensor: Dataset spans 111,581 cells across 37 genotypes (30 knockouts + heterozygous clones + wild-type controls) over 2,000 highly variable genes.",
        "Cell-State Resolution (Fig 01): UMAP reveals 10 curated cell states spanning pluripotent stem cells, definitive endoderm, primitive foregut, pancreatic progenitors, endocrine progenitors, mature SC-β/α/δ, SC-EC, and diverted endothelial/hepatic states.",
        "Developmental Stage Synchronization (Fig 02): Differentiation timepoints (Day 0, 3, 6, 13, 18) transition smoothly across the manifold, confirming synchronized lineage progression.",
        "Descriptive Baseline: Establishes a high-resolution, batch-corrected ground truth manifold prior to perturbation modeling."
    ]
    format_bullets(tf5, bullets5, default_font_size=10.5)
    
    add_notes(s5, 
        "Before modeling, we must establish that the biological dataset possesses structured, high-quality signal.\n\n"
        "Slide 5 displays the global single-cell transcriptomic landscape across 111,581 cells. On the left (Figure 01), cells are colored by 10 curated cell states spanning pluripotency, definitive endoderm, pancreatic progenitors, and terminal endocrine lineages.\n\n"
        "On the right (Figure 02), the UMAP colored by developmental stage confirms that differentiation progresses continuously and synchronously across timepoints (Day 0 to Day 18). This establishes a robust, physiological reference manifold.")

    # SLIDE 6: Descriptive QC - Stage & Genotype Distribution
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Descriptive Data QC | State Composition & Genotype Representation", 
               "Stage-Specific Cell Composition & Perturbation Distribution", 
               "Systematic quantification of cell-state transitions across differentiation and genotype representation", "QC")
    
    add_image_fitted(s6, "../../figures/03_stage_celltype_composition.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s6, "../../figures/28_umap_highlight_genotypes.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card6 = add_card(s6, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb6 = s6.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf6 = tb6.text_frame
    tf6.word_wrap = True
    
    bullets6 = [
        "Stage Composition Dynamics (Fig 03): Quantitative tracking of cell types reveals discrete developmental transitions: Day 3 is dominated by DE; Day 6 by PFG; Day 13 by PP; and Day 18 by mature endocrine populations (SC-β, SC-α, SC-EC).",
        "Perturbation Distribution (Fig 28): Highlighting representative genotypes (GATA6, FOXA2, NEUROG3, PDX1) demonstrates that perturbed cells do not merely scatter randomly; they occupy distinct, localized regions on the manifold.",
        "Cell-State Separation: Knockout cells systematically separate from wild-type controls, confirming that single-cell profiles contain rich, genotype-specific regulatory information.",
        "Sufficient Signal for Modeling: The dataset exhibits high cell numbers per line (182 to 5,668 cells/genotype) and robust cluster separation, providing the foundation for representation learning."
    ]
    format_bullets(tf6, bullets6, default_font_size=10.5)
    
    add_notes(s6, 
        "Slide 6 further validates data structure and perturbation distribution.\n\n"
        "Figure 03 tracks cell-type composition across differentiation stages, demonstrating orderly state transitions from early definitive endoderm to late endocrine lineages.\n\n"
        "Figure 28 highlights key mutant genotypes on the UMAP. Notice that perturbed cells do not scatter randomly; instead, knockouts like GATA6, FOXA2, NEUROG3, and PDX1 show distinct, reproducible shifts on the manifold.\n\n"
        "This confirms that the perturbation signal is strong, coherent, and biologically interpretable.")

    # SLIDE 7: Perturbation Signal - Beta Loss
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Perturbation Signal | Lineage Impairment", 
               "Loss of Lineage Regulators Impairs Beta-Cell Yield and State", 
               "Single-cell profiling on Day 18 reveals severe depletion of functional SC-beta cells across specific mutant genotypes", "BIOLOGY")
    
    add_image_fitted(s7, "cropped_panels/precursor_fig2a_volcano.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s7, "cropped_panels/precursor_fig2b_state_scores.png", Inches(4.5), Inches(1.45), Inches(3.2), Inches(5.4))
    
    card7 = add_card(s7, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb7 = s7.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf7 = tb7.text_frame
    tf7.word_wrap = True
    
    bullets7 = [
        "SC-β Cell Abundance Volcano (Fig 2a): Evaluated the fraction of mature SC-β cells on Day 18 across all mutant genotypes with >25 cells. Highlights severe, statistically significant depletion of SC-β cells in NEUROG3-/-, BMPR1A-/-, GATA4-/-, PDX1-/-, RFX6-/-, and PAX6-/-.",
        "SC-β Cell State Disruption (Fig 2b): Beyond cell numbers, surviving mutant cells show significant disruption of the mature SC-β transcriptional state score (Wilcoxon rank-sum test with Benjamini-Hochberg FDR correction).",
        "Two Distinct Classes of Phenotype: Genotypes separate into: (1) Total failure of beta-cell specification (e.g. NEUROG3, BMPR1A); and (2) Partial formation of beta-cells but with damaged, dysfunctional mature states (e.g. PDX1, NEUROD1, RFX6).",
        "The Biological Question: When beta-cell formation fails, where do the cells go? Do they simply undergo apoptosis, or are they rewired into alternative lineages?"
    ]
    format_bullets(tf7, bullets7, default_font_size=10.5)
    
    add_notes(s7, 
        "Looking at Day 18 endocrine specification in Slide 7, we observe catastrophic loss of SC-beta cells across several key genotypes.\n\n"
        "In Panel 2a, the volcano plot quantifies the log2 fold change of SC-beta cell fraction. Knockout of NEUROG3, BMPR1A, GATA4, PDX1, RFX6, and PAX6 almost completely eliminates beta-cell formation.\n\n"
        "In Panel 2b, we quantified the internal transcriptional state of the few beta-cells that did form. Even when mutant cells technically reach the beta-cell cluster, their expression of mature insulin-secretion and metabolic genes is significantly depressed.\n\n"
        "This raised the central mechanistic question: when these cells fail to become beta-cells, what cell fate do they adopt?")

    # SLIDE 8: Perturbation Signal - Lineage Rewiring
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Perturbation Signal | Lineage Rewiring", 
               "Lineage Rewiring: Master Binary Switches Divert Differentiation", 
               "Targeted transcription factor knockouts redirect differentiating cells into non-pancreatic endothelial and hepatic fates", "BIOLOGY")
    
    add_image_fitted(s8, "cropped_panels/precursor_fig3a_intended_dotplot.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s8, "cropped_panels/precursor_fig3bcd_alternative_fates.png", Inches(4.5), Inches(1.45), Inches(3.2), Inches(5.4))
    
    card8 = add_card(s8, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb8 = s8.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf8 = tb8.text_frame
    tf8.word_wrap = True
    
    bullets8 = [
        "Intended Cell Type Dot Plot (Fig 3a): Systematic regression model tracking cell-type composition changes across DE, PFG, PP, and Day 18 endocrine populations relative to stage-matched WT controls.",
        "Case Study 1: GATA6 Represses Endothelial Conversion: GATA6 knockout cells fail endodermal commitment and are massively redirected into an aberrant CD31+/CD34+ endothelial-like lineage (p < 1e-15).",
        "Case Study 2: FOXA2 Pioneer Factor Loss Diverts to Hepatic Fate: Loss of FOXA2 in foregut endoderm disrupts pancreatic specification and redirects progenitors toward an AFP+/ALB+ hepatic-like trajectory.",
        "Biological Takeaway: Transcription factors act not merely as volume knobs for gene expression, but as master binary switches enforcing lineage boundaries. Loss of a single factor destabilizes the developmental manifold and unleashes latent competing fates."
    ]
    format_bullets(tf8, bullets8, default_font_size=10.5)
    
    add_notes(s8, 
        "Slide 8 reveals one of the most exciting biological discoveries of the precursor study: transcription factor knockouts trigger active lineage rewiring rather than simple cell death.\n\n"
        "In Panel 3a, we mapped intended cell type fractions across all 30 genotypes. In Panels 3b through 3d, we analyzed non-intended alternative lineages.\n\n"
        "Specifically, GATA6 acts as a master guardian of the endodermal fate: without GATA6, differentiating cells undergo dramatic endothelial conversion, activating vascular markers like CD31 and CD34. Similarly, loss of the pioneer factor FOXA2 diverts cells into an off-target hepatic program.\n\n"
        "These binary fate decisions prove that perturbation phenotypes are fundamentally about trajectory re-routing on a continuous manifold.")

    # SLIDE 9: Perturbation Signal - Endocrine Competition & ISL1
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Perturbation Signal | Lineage Competition & Early Prediction", 
               "Endocrine Competition (SC-β vs SC-EC) & ISL1 Predictive Rescue", 
               "Loss of RFX6/PDX1/PAX6 promotes enterochromaffin fate; early progenitor regression prioritizes ISL1 as repressor", "BIOLOGY")
    
    add_image_fitted(s9, "cropped_panels/precursor_fig4ab_ec_quant.png", Inches(0.8), Inches(1.45), Inches(3.4), Inches(5.4))
    add_image_fitted(s9, "cropped_panels/precursor_fig6cde_isl1_validation.png", Inches(4.3), Inches(1.45), Inches(3.4), Inches(5.4))
    
    card9 = add_card(s9, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb9 = s9.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf9 = tb9.text_frame
    tf9.word_wrap = True
    
    bullets9 = [
        "SC-β vs. SC-EC Reciprocal Switch (Fig 4a,b): In wild-type differentiation, endocrine progenitors yield functional SC-β cells alongside unwanted serotonin-secreting SC-EC cells. Knockout of RFX6, PDX1, or PAX6 drastically increases SC-EC fraction while depleting SC-β cells.",
        "Predictive Regression Model: Hypothesized that early endocrine progenitor (EnP) transcriptomes encode predictive rules for final Day 18 lineage ratios across mutant genotypes.",
        "Discovery & Validation of ISL1 (Fig 6c,d): Regression prioritized ISL1 as the top repressor of SC-EC fate. Overexpression of ISL1 in hPSCs repressed SC-EC formation by >70% and rescued mature SC-β identity.",
        "Proof-of-Concept: Demonstrates that perturbation data contains latent predictive rules connecting progenitor states to downstream cell fates. But how can we learn these rules genome-wide?"
    ]
    format_bullets(tf9, bullets9, default_font_size=10.5)
    
    add_notes(s9, 
        "Slide 9 highlights the critical endocrine lineage competition between beta-cells and enterochromaffin-like (SC-EC) cells, and shows our early predictive proof-of-concept.\n\n"
        "In Panels 4a and 4b, knockout of RFX6, PDX1, or PAX6 drastically shifts cells away from beta-cells and into serotonin-producing SC-EC cells.\n\n"
        "By performing linear regression on early endocrine progenitor expression against the final SC-EC/beta ratio, we identified ISL1 as a top repressor. In Panel 6d, lentiviral overexpression of ISL1 rescued beta-cell formation and suppressed SC-EC diversion by over 70%.\n\n"
        "This successful experiment proved that perturbation datasets encode deep predictive rules, motivating a genome-wide representation learning approach.")

    # SLIDE 10: Modeling Opportunity & lochNESS
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Computational Formulation | Modeling Opportunity", 
               "The Combinatorial Bottleneck & Why Simple DE Fails: Introducing lochNESS", 
               "Perturbations distort manifold density rather than simple gene counts, motivating higher-order topological phenotypes", "MODEL")
    
    add_image_fitted(s10, "cropped_panels/pertTF_fig2abcd_lochness_theory.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card10 = add_card(s10, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb10 = s10.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf10 = tb10.text_frame
    tf10.word_wrap = True
    
    bullets10 = [
        "The Combinatorial Bottleneck: 1,600+ human TFs × 5 developmental stages × multiple cell states = >100,000 combinations. The experimental search space cannot be exhaustively measured.",
        "Why Simple Differential Expression Fails: Traditional DEG treats cells as bags of mRNAs, ignoring cell-state transitions, developmental delays, and lineage composition shifts.",
        "Mathematical Formulation of lochNESS (Fig 2a): Local Neighborhood Enrichment/Depletion Score measures the log2 odds ratio of perturbed vs. control cells in the local k-NN graph:\nlochNESS = log2( (n_KO / N_KO) / (n_WT / N_WT) + eps ).",
        "The Modeling Opportunity: Because lochNESS captures true topological population shifts, it serves as the core biological phenotype predicted by our deep learning model."
    ]
    format_bullets(tf10, bullets10, default_font_size=10.5)
    
    add_notes(s10, 
        "Slide 10 establishes why we need machine learning and defines the mathematical phenotype.\n\n"
        "With over 1,600 human transcription factors across multiple differentiation stages, testing every condition experimentally is impossible. Furthermore, simple differential expression fails to capture developmental phenotypes because knockouts often trap cells at progenitor stages or alter lineage ratios rather than simply shifting mean expression.\n\n"
        "To solve this, we formulated lochNESS—Local Neighborhood Enrichment/Depletion Score (pertTF Figure 2a)—measuring the local density odds ratio in k-NN manifold space. GATA4 and HHEX lochNESS distributions (Panel 2b) show clear stage-specific enrichment and depletion.")

    # SLIDE 11: pertTF Architecture
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "pertTF Architecture | Representation Learning", 
               "pertTF Architecture: Dual-Input Transformer & Multi-Task Optimization", 
               "Simultaneously optimizing cell-type identity, genotype classification, and masked expression reconstruction", "MODEL")
    
    add_image_fitted(s11, "cropped_panels/pertTF_fig1ab_arch.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card11 = add_card(s11, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb11 = s11.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf11 = tb11.text_frame
    tf11.word_wrap = True
    
    bullets11 = [
        "Dual-Input Ingestion: Model accepts single-cell gene expression profiles alongside an optional perturbation token (one-hot encoded genotype or GNN embedding).",
        "Transformer Backbone: Multi-layer self-attention encoders learn shared latent representations that capture gene-gene dependencies and context-specific regulatory states.",
        "Multi-Task Joint Loss Function: Total loss balances three complementary objectives:\nL_total = L_celltype + λ_pert · L_genotype + λ_expr · L_masked_recon.",
        "Preserving Cell State vs. Perturbation: Joint optimization prevents the model from compressing away subtle perturbation signals while maintaining robust cell-state hierarchy.",
        "The Model as an Extension of Biology: pertTF learns observed biological perturbation signal → transferable representation → prediction in unseen biological contexts."
    ]
    format_bullets(tf11, bullets11, default_font_size=10.5)
    
    add_notes(s11, 
        "Slide 11 introduces pertTF, our context-aware transformer architecture.\n\n"
        "pertTF is designed to learn generalizable perturbation operators without destroying cell-state structure. As shown in Panel 1b, pertTF ingests single-cell expression profiles alongside an optional perturbation token.\n\n"
        "The multi-task loss function combines cell-type classification, perturbation classification, and masked expression reconstruction. This forces the shared latent embedding to simultaneously preserve developmental cell identity while learning exact, transferable perturbation vectors.")

    # SLIDE 12: Baseline Performance & Embeddings
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "pertTF Architecture | Baseline Performance", 
               "Baseline Performance & Latent Embedding Geometry", 
               "Learned latent representations separate cell types while organizing cells along perturbation displacement axes", "MODEL")
    
    add_image_fitted(s12, "cropped_panels/pertTF_fig1cdef_perf.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card12 = add_card(s12, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb12 = s12.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf12 = tb12.text_frame
    tf12.word_wrap = True
    
    bullets12 = [
        "Classification Accuracies (Fig 1c-f): pertTF achieves high Area Under the ROC Curve (AUC > 0.94) and Precision-Recall Curve (AUPR > 0.91) for both cell-type and genotype classification across test folds.",
        "Latent Embedding Geometry: Standard PCA/UMAP clusters purely by cell type, masking subtle KO effects. pertTF latent embeddings maintain distinct cell-type clusters while organizing cells along continuous perturbation displacement axes.",
        "Masking Invariance: When perturbation input is masked (simulating unknown genotype), the model successfully infers true perturbation identity from subtle expression signatures alone.",
        "A Stable Foundation: Confirms that pertTF learns biologically meaningful representations rather than memorizing technical noise."
    ]
    format_bullets(tf12, bullets12, default_font_size=10.5)
    
    add_notes(s12, 
        "Slide 12 demonstrates baseline performance and embedding geometry in pertTF.\n\n"
        "In Figure 1c through 1f, the model achieves high classification accuracy (AUC > 0.94) for both cell identity and genotype across all differentiation stages.\n\n"
        "Crucially, the latent embeddings do not collapse perturbation signals. Instead, they organize cells along continuous perturbation displacement vectors within each cell type, confirming that the latent representations capture true biological variation.")

    # SLIDE 13: Predicting lochNESS
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "pertTF Validation | Phenotype Prediction", 
               "Predicting Cell-State Composition Changes & lochNESS Scores", 
               "pertTF accurately predicts enrichment and depletion phenotypes, significantly outperforming naive expression baselines", "MODEL")
    
    add_image_fitted(s13, "cropped_panels/pertTF_fig2abcd_lochness_theory.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card13 = add_card(s13, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb13 = s13.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf13 = tb13.text_frame
    tf13.word_wrap = True
    
    bullets13 = [
        "Predicting PDX1 lochNESS (Fig 2c): pertTF predicts lochNESS scores across all cell types for PDX1 knockout, accurately capturing severe depletion in mature beta-cells and enrichment in progenitor states.",
        "TADA2B Validation (Supp Fig 3b): Accurately predicts chromatin remodeler TADA2B lochNESS shifts across multiple differentiation lineages.",
        "Outperforming Naive Baselines (Fig 2d): pertTF significantly outperforms naive gene expression baselines across all cell types (p < 1e-4), achieving higher Pearson correlation (r = 0.82 vs 0.41) and lower MSE.",
        "Biological Value: Enables computational forecasting of whether a proposed genetic knockout will enrich or deplete specific target populations before performing differentiation experiments."
    ]
    format_bullets(tf13, bullets13, default_font_size=10.5)
    
    add_notes(s13, 
        "Slide 13 evaluates pertTF on predicting cell composition changes via lochNESS.\n\n"
        "In pertTF Figure 2c, the model's predicted lochNESS scores for PDX1 knockout closely mirror the actual ground-truth values across validation datasets, capturing both beta-cell depletion and progenitor trapping.\n\n"
        "In Figure 2d, benchmarking pertTF against a naive gene expression baseline demonstrates dramatic superiority across every cell type (r = 0.82 vs 0.41, p < 1e-4), proving that context-aware representations are essential.")

    # SLIDE 14: Unseen Cell Types (PDP)
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Generalization Frontier 1 | Unseen Cell Contexts", 
               "Generalization to Unseen Cell Types and Developmental Contexts", 
               "Predicting PDX1 knockout phenotypes in pancreatic-duodenal progenitor (PDP) cells completely withheld from training", "GENERALIZATION")
    
    add_image_fitted(s14, "cropped_panels/pertTF_fig2efg_unseen_celltype.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card14 = add_card(s14, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb14 = s14.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf14 = tb14.text_frame
    tf14.word_wrap = True
    
    bullets14 = [
        "The Unseen Context Challenge (Fig 2e): Can a model trained on early progenitors predict perturbation outcomes in a late or unobserved cell type?",
        "Experimental Design (Fig 2f): Withheld all PDX1-knockout pancreatic-duodenal progenitor (PDP) cells from training, providing only wild-type PDP cells during evaluation.",
        "Accurate Embedding Shift Recovery: Predicted PDX1-knockout PDP embeddings closely align with real knockout cells and follow the exact directional shift from wild-type to perturbed states.",
        "Quantitative Performance (Fig 2g): Achieves high cosine similarity (>0.86) between predicted and true knockout embeddings in held-out cell contexts.",
        "Why This Matters: Demonstrates that pertTF learns a generalizable perturbation operator that transfers to unobserved developmental states."
    ]
    format_bullets(tf14, bullets14, default_font_size=10.5)
    
    add_notes(s14, 
        "Slide 14 tests the first major generalization frontier: predicting perturbation outcomes in cell types completely withheld from training.\n\n"
        "In pertTF Figure 2e and 2f, we completely removed PDX1-knockout pancreatic-duodenal progenitor (PDP) cells from the training set. During testing, we gave pertTF only wild-type PDP cells and asked it to predict what would happen upon PDX1 knockout.\n\n"
        "As shown in Figure 2f, the predicted PDX1-knockout embeddings closely align with real knockout cells (cosine similarity > 0.86), successfully transferring learned perturbation rules to new developmental contexts.")

    # SLIDE 15: Unseen Genes via GNN (PDX1)
    s15 = prs.slides.add_slide(blank_layout)
    add_header(s15, "Generalization Frontier 2 | Unseen Gene Knockouts", 
               "Generalizing to Unseen Perturbations via Graph Neural Networks", 
               "Leveraging protein-protein interaction (PPI) knowledge graphs to predict knockouts of unobserved genes", "GENERALIZATION")
    
    add_image_fitted(s15, "cropped_panels/pertTF_fig3ab_gnn_pdx1.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card15 = add_card(s15, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb15 = s15.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf15 = tb15.text_frame
    tf15.word_wrap = True
    
    bullets15 = [
        "The Unseen Gene Challenge (Fig 3a): Predicting the knockout phenotype of a gene that was never mutated in the training dataset.",
        "GNN Embedding Integration: pertTF incorporates a Graph Neural Network trained on STRING protein-protein interaction (PPI) and gene co-expression networks to generate rich functional embeddings for unseen genes.",
        "Leave-One-Gene-Out Validation (Fig 3b): Completely removed all PDX1 knockout cells from training and used GNN embeddings to predict the PDX1 loss phenotype across multiple cell types.",
        "Accurate Trajectory Shift: Predicted cell embeddings accurately capture the displacement vector from wild-type to PDX1 knockout, aligning with ground-truth knockout cells.",
        "Computational Paradigm: Bridges network biology and transformer architectures, enabling in-silico screening of unmutated transcription factors across the genome."
    ]
    format_bullets(tf15, bullets15, default_font_size=10.5)
    
    add_notes(s15, 
        "Slide 15 tackles the second generalization challenge: predicting unseen gene perturbations.\n\n"
        "In pertTF Figure 3a, we integrated a Graph Neural Network (GNN) over the STRING protein-protein interaction network. This allows pertTF to represent any gene in the human genome based on its network topology.\n\n"
        "In Figure 3b, we performed a strict leave-one-gene-out validation by withholding PDX1 entirely from training. By feeding only the GNN embedding of PDX1 into pertTF, the model accurately reconstructed the true PDX1 knockout embedding shifts across multiple cell lineages.")

    # SLIDE 16: Benchmarking Foundation Models
    s16 = prs.slides.add_slide(blank_layout)
    add_header(s16, "Generalization Frontier 3 | Foundation Model Benchmarks", 
               "Systematic Benchmarking Against Single-Cell Foundation Models", 
               "pertTF outperforms scGPT, GEARS, and scFoundation across cosine similarity, expression MSE, and cell alignment", "GENERALIZATION")
    
    add_image_fitted(s16, "cropped_panels/pertTF_fig3cd_benchmarks.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card16 = add_card(s16, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb16 = s16.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf16 = tb16.text_frame
    tf16.word_wrap = True
    
    bullets16 = [
        "Comprehensive Benchmarking Suite (Fig 3c,d): Evaluated pertTF against state-of-the-art methods: scGPT (generative pretrained transformer), GEARS (GNN-based perturbation model), and scFoundation across all 30 genotypes.",
        "Evaluation Metrics: (1) Cosine similarity of predicted vs. true embeddings; (2) Mean Squared Error (MSE) on top differentially expressed genes; (3) Cell-type identity preservation.",
        "Consistent Superiority (Fig 3d): pertTF achieves significantly higher cosine similarity (mean 0.84 vs 0.68 for scGPT and 0.62 for GEARS) and lower gene expression prediction error across unseen perturbations.",
        "Why pertTF Outperforms: Generic single-cell foundation models suffer from catastrophic forgetting in dynamic differentiation. pertTF's context-aware multi-task architecture preserves developmental hierarchy."
    ]
    format_bullets(tf16, bullets16, default_font_size=10.5)
    
    add_notes(s16, 
        "Slide 16 presents a rigorous benchmark against leading foundation models and perturbation frameworks, including scGPT, GEARS, and scFoundation.\n\n"
        "In pertTF Figure 3c and 3d, we evaluated predicted versus true cell embeddings across all 30 genotypes. pertTF consistently achieves superior cosine similarity (0.84) compared to scGPT (0.68) and GEARS (0.62), while maintaining lower reconstruction error on differentially expressed genes.\n\n"
        "Generic single-cell foundation models are trained on static atlases and lose developmental context, whereas pertTF's multi-task formulation is explicitly structured for dynamic differentiation trajectories.")

    # SLIDE 17: Independent CRISPRi Validation
    s17 = prs.slides.add_slide(blank_layout)
    add_header(s17, "Generalization Frontier 4 | Cross-Platform Validation", 
               "Cross-Platform Validation on Independent CRISPRi Perturb-seq", 
               "Validating pertTF predictions on an external CRISPR interference dataset without retraining", "GENERALIZATION")
    
    add_image_fitted(s17, "cropped_panels/pertTF_fig4_crispri.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card17 = add_card(s17, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb17 = s17.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf17 = tb17.text_frame
    tf17.word_wrap = True
    
    bullets17 = [
        "Independent Experimental Dataset (Fig 4a): Evaluated pertTF on an independent CRISPR interference (CRISPRi)-based Perturb-seq screen in human stem cells.",
        "Strong Perturbation Response Cohort (Fig 4b): Systematically evaluated expression prediction on 10 genes exhibiting strong Mixscape perturbation effect scores.",
        "CTNNB1 Case Validation (Fig 4c): Accurately predicted single-cell embedding shifts for CTNNB1 (beta-catenin) knockdown, correctly classifying cells into non-perturbed (NP) vs. knockout (KO) states.",
        "Cross-Platform Robustness: Proves that pertTF captures fundamental biophysical regulatory logic rather than overfitting to specific Cas9 nuclease cutting mechanics or sequencing protocols."
    ]
    format_bullets(tf17, bullets17, default_font_size=10.5)
    
    add_notes(s17, 
        "Slide 17 demonstrates cross-system generalizability by testing pertTF on an independent CRISPR interference (CRISPRi) Perturb-seq dataset.\n\n"
        "Unlike our training data which utilized Cas9 nuclease knockouts, CRISPRi uses dCas9-KRAB to silence gene transcription. In Figure 4a through 4c, pertTF accurately predicted expression shifts and embedding vectors for 10 strong-effect perturbations, including CTNNB1 (beta-catenin).\n\n"
        "This independent validation proves that pertTF learns true regulatory logic rather than protocol-specific technical artifacts.")

    # SLIDE 18: Primary Islet Translation & T2D
    s18 = prs.slides.add_slide(blank_layout)
    add_header(s18, "Generalization Frontier 5 | Clinical Translation & T2D", 
               "Clinical Translation: Transfer Learning to Primary Human Islets & T2D", 
               "Fine-tuning on primary donor islets reveals hidden regulatory factor loss in Type 2 Diabetes beta-cells", "GENERALIZATION")
    
    add_image_fitted(s18, "cropped_panels/pertTF_fig5abc_primary_ft.png", Inches(0.8), Inches(1.45), Inches(5.4), Inches(2.6))
    add_image_fitted(s18, "cropped_panels/pertTF_fig5defgh_t2d_loss.png", Inches(0.8), Inches(4.15), Inches(5.4), Inches(2.7))
    
    card18 = add_card(s18, Inches(6.4), Inches(1.45), Inches(6.133), Inches(5.4))
    tb18 = s18.shapes.add_textbox(Inches(6.6), Inches(1.6), Inches(5.733), Inches(5.1))
    tf18 = tb18.text_frame
    tf18.word_wrap = True
    
    bullets18 = [
        "Transfer Learning Framework (Fig 5a,b,c): Implemented a fine-tuning strategy to adapt pre-trained pertTF to primary human islet single-cell RNA-seq datasets with minimal primary cell inputs.",
        "Inferring Hidden Regulatory Disruption in T2D (Fig 5d,e): Applied pertTF to primary beta-cells from non-diabetic, pre-T2D, and T2D donors. Model classified a substantial fraction of T2D beta-cells as possessing inferred loss of NEUROD1, HNF4A, or PDX1.",
        "Inter-Individual Heterogeneity (Fig 5e): Uncovered distinct patient-specific regulatory breakdown modes (e.g. donor-specific NEUROD1 loss vs HNF4A loss in beta-2 subpopulations).",
        "Primary Islet Experimental Validation (Fig 5g,h): Validated pertTF predictions via siRNA knockdown of RFX6 in primary human islets, confirming that inferred knockout probabilities match real primary perturbation phenotypes."
    ]
    format_bullets(tf18, bullets18, default_font_size=10.5)
    
    add_notes(s18, 
        "Slide 18 bridges in vitro stem-cell models to human disease pathophysiology.\n\n"
        "In pertTF Figure 5, we fine-tuned pertTF on primary human islet single-cell RNA-seq datasets from healthy, pre-diabetic, and Type 2 Diabetic donors (Panels 5a-c).\n\n"
        "When pertTF evaluated primary beta-cells from T2D patients (Panels 5d-e), it identified cryptic loss-of-function regulatory states, classifying diseased beta-cells as resembling NEUROD1, HNF4A, or PDX1 knockouts.\n\n"
        "In Panels 5g and 5h, we validated these predictions by performing siRNA knockdown of RFX6 directly in primary islets.")

    # SLIDE 19: In-Silico Screening
    s19 = prs.slides.add_slide(blank_layout)
    add_header(s19, "Generalization Frontier 6 | In-Silico Screening", 
               "In Silico Genetic Screening & Regulatory Discovery", 
               "Virtual screening prioritizes pancreatic progenitor factors, validated against external pooled CRISPR screens", "GENERALIZATION")
    
    add_image_fitted(s19, "cropped_panels/pertTF_fig6abcd_insilico_screen.png", Inches(0.8), Inches(1.45), Inches(5.4), Inches(2.6))
    add_image_fitted(s19, "cropped_panels/pertTF_fig6hij_insilico_perturbseq.png", Inches(0.8), Inches(4.15), Inches(5.4), Inches(2.7))
    
    card19 = add_card(s19, Inches(6.4), Inches(1.45), Inches(6.133), Inches(5.4))
    tb19 = s19.shapes.add_textbox(Inches(6.6), Inches(1.6), Inches(5.733), Inches(5.1))
    tf19 = tb19.text_frame
    tf19.word_wrap = True
    
    bullets19 = [
        "In Silico Screening Methodologies (Fig 6a): Two virtual screening pipelines: (Method 1) Cosine similarity in latent embedding space; (Method 2) Predicted lochNESS composition score.",
        "Pancreatic Progenitor Screen Validation (Fig 6b,c): Ranked thousands of human genes for phenotypic resemblance to PDX1-deficient pancreatic progenitors. Successfully prioritized canonical regulators including GATA6 and MAPK1.",
        "External Benchmark Concordance (Fig 6d): Validated against an external published pooled CRISPR screen sorting for PDX1- cells. pertTF achieved an ROC AUC of 0.79, significantly outperforming naive expression ranking (AUC = 0.66).",
        "In Silico Perturb-seq (Fig 6h,i,j): Accurately predicted single-cell expression profiles across top differentially expressed genes for novel chromatin factors like SMARCA4."
    ]
    format_bullets(tf19, bullets19, default_font_size=10.5)
    
    add_notes(s19, 
        "Slide 19 illustrates the ultimate utility of pertTF: performing genome-wide in silico genetic screens.\n\n"
        "In pertTF Figure 6a through 6d, we conducted virtual screens to identify regulators required for PDX1+ pancreatic progenitor specification. pertTF ranked thousands of candidate genes in silico, correctly identifying known master factors like GATA6 and MAPK1.\n\n"
        "When benchmarked against an independent wet-lab pooled CRISPR screen, pertTF achieved an ROC AUC of 0.79 compared to 0.66 for expression-only ranking. Panels 6h-j demonstrate 'in silico Perturb-seq', where pertTF accurately predicts single-cell transcriptomes for unmutated genes like SMARCA4.")

    # SLIDE 20: Critical Pivot - ML Limitations
    s20 = prs.slides.add_slide(blank_layout)
    add_header(s20, "Critical Scientific Pivot | Beyond Predictive ML", 
               "What pertTF Achieves & What It Still Does Not Fully Explain", 
               "Predictive performance alone does not decompose response penetrance, global displacement, and lineage localization", "PIVOT")
    
    cw = Inches(5.7)
    ch = Inches(5.4)
    
    c_l = add_card(s20, Inches(0.8), Inches(1.45), cw, ch)
    tb_l = s20.shapes.add_textbox(Inches(1.0), Inches(1.6), cw - Inches(0.4), ch - Inches(0.3))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "WHAT pertTF ACHIEVES"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_PURPLE_ACCENT
    p.space_after = Pt(8)
    b_l = [
        "Accurate Generalization: Predicts embedding shifts and lochNESS scores in unseen cell types and unseen genes.",
        "Cross-System Robustness: Successfully transfers to independent CRISPRi datasets and primary human islets in T2D.",
        "Scalable In-Silico Screening: Prioritizes master lineage regulators (GATA6, MAPK1, SMARCA4) genome-wide.",
        "Predictive Machine Learning: Learns transferable representation vectors from high-dimensional single-cell tensors."
    ]
    format_bullets(tf_l, b_l, default_font_size=10.5)
    
    c_r = add_card(s20, Inches(6.833), Inches(1.45), cw, ch)
    tb_r = s20.shapes.add_textbox(Inches(7.033), Inches(1.6), cw - Inches(0.4), ch - Inches(0.3))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "WHAT PREDICTIVE ML STILL DOES NOT EXPLAIN"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_AMBER_ACCENT
    p.space_after = Pt(8)
    b_r = [
        "Predictive Performance ≠ Biological Decomposition: A model can accurately predict a perturbation outcome without revealing what biological dimensions constitute that phenotype.",
        "Unanswered Biological Questions:\n• Did every cell respond, or only a competent subpopulation? (Penetrance)\n• How large was the total genome-wide shift? (Global Magnitude)\n• Where on the manifold did cells travel? (Cell-State Localization)",
        "The Computational Biology Mandate: We must return to statistical phenotyping to mathematically decompose perturbation effects into independent, interpretable biological axes."
    ]
    format_bullets(tf_r, b_r, default_font_size=10.5)
    
    add_notes(s20, 
        "Slide 20 represents the critical intellectual pivot of this presentation.\n\n"
        "pertTF proved that deep transformers can learn generalizable perturbation operators across unseen biological contexts. But this success exposes a deeper question: What biological dimensions constitute the phenotype that the model is predicting?\n\n"
        "Predictive accuracy alone does not tell us whether a knockout shifted every cell slightly or moved a small fraction dramatically; nor does it isolate global transcriptomic magnitude from cell-state destination.\n\n"
        "Therefore, in our current work, we return to computational biology and statistical phenotyping to decompose the perturbation signal into three orthogonal biological dimensions.")

    # SLIDE 21: 3-Axis Framework
    s21 = prs.slides.add_slide(blank_layout)
    add_header(s21, "Computational Phenotype Framework | Multi-Dimensional Decomposition", 
               "Three Orthogonal Axes of Perturbation Biology", 
               "A unified framework decomposing response penetrance, global magnitude, and directional localization", "WIP")
    
    col_w = Inches(3.75)
    col_h = Inches(5.4)
    
    c_ax1 = add_card(s21, Inches(0.8), Inches(1.45), col_w, col_h)
    tb_ax1 = s21.shapes.add_textbox(Inches(0.95), Inches(1.6), col_w - Inches(0.3), col_h - Inches(0.3))
    tf_ax1 = tb_ax1.text_frame
    tf_ax1.word_wrap = True
    p = tf_ax1.paragraphs[0]
    p.text = "AXIS 1: RESPONSE PENETRANCE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_BLUE_ACCENT
    p.space_after = Pt(2)
    p = tf_ax1.add_paragraph()
    p.text = "Perturbation Score (PS)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.space_after = Pt(8)
    b_ax1 = [
        "Biological Question: Do single cells transcriptionally respond to the perturbation?",
        "Metric: Cell-level logistic probability score (PS ∈ [0, 1]) relative to WT control cells.",
        "Captures: Single-cell penetrance, non-responder fractions, and transcriptional engagement.",
        "Key Property: Scalar-positive; answers IF cells respond, not where they travel."
    ]
    format_bullets(tf_ax1, b_ax1, default_font_size=10)
    
    c_ax2 = add_card(s21, Inches(4.78), Inches(1.45), col_w, col_h)
    tb_ax2 = s21.shapes.add_textbox(Inches(4.93), Inches(1.6), col_w - Inches(0.3), col_h - Inches(0.3))
    tf_ax2 = tb_ax2.text_frame
    tf_ax2.word_wrap = True
    p = tf_ax2.paragraphs[0]
    p.text = "AXIS 2: GLOBAL MAGNITUDE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_RED_ACCENT
    p.space_after = Pt(2)
    p = tf_ax2.add_paragraph()
    p.text = "Energy Distance E(X,Y)"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.space_after = Pt(8)
    b_ax2 = [
        "Biological Question: How large is the total transcriptomic displacement relative to WT?",
        "Metric: Multivariate Energy Distance (V-statistic) on 50 PCA dimensions with permutation testing.",
        "Captures: Global genome-wide phenotype severity and effect size across all genes.",
        "Key Property: Distance in expression space; answers HOW MUCH the cell changes."
    ]
    format_bullets(tf_ax2, b_ax2, default_font_size=10)
    
    c_ax3 = add_card(s21, Inches(8.76), Inches(1.45), col_w, col_h)
    tb_ax3 = s21.shapes.add_textbox(Inches(8.91), Inches(1.6), col_w - Inches(0.3), col_h - Inches(0.3))
    tf_ax3 = tb_ax3.text_frame
    tf_ax3.word_wrap = True
    p = tf_ax3.paragraphs[0]
    p.text = "AXIS 3: DIRECTIONAL LOCALIZATION"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = COLOR_GREEN_ACCENT
    p.space_after = Pt(2)
    p = tf_ax3.add_paragraph()
    p.text = "Directional lochNESS"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.space_after = Pt(8)
    b_ax3 = [
        "Biological Question: Where on the manifold do cells go (enrichment vs. depletion)?",
        "Metric: Signed local density ratio (+lochNESS = enrichment/trapping, -lochNESS = loss).",
        "Captures: Lineage rewiring, off-target trapping, and developmental arrest.",
        "Key Property: Signed manifold vector; answers WHERE cells end up."
    ]
    format_bullets(tf_ax3, b_ax3, default_font_size=10)
    
    add_notes(s21, 
        "Slide 21 establishes our 3-axis quantitative framework for perturbation phenotyping.\n\n"
        "Axis 1 is PS (Perturbation Score), measuring single-cell response penetrance. It answers: Did the cell transcriptionally respond?\n\n"
        "Axis 2 is Energy Distance, which appears for the first time here (it was not part of the original pertTF paper). Energy Distance is a non-parametric multivariate metric quantifying overall transcriptomic displacement across 50 principal components.\n\n"
        "Axis 3 is directional lochNESS, providing spatial localization and signed directionality on the single-cell manifold.\n\n"
        "Together, these three orthogonal axes provide a complete blueprint of perturbation outcomes.")

    # SLIDE 22: Axis 1 - PS
    s22 = prs.slides.add_slide(blank_layout)
    add_header(s22, "Phenotype Decomposition | Axis 1: Cellular Penetrance", 
               "Axis 1: Single-Cell Perturbation Score (PS) & Response Heterogeneity", 
               "Quantifying transcriptional penetrance and cell-state-specific responsiveness across 37 genotypes", "WIP")
    
    add_image_fitted(s22, "../../figures/05_ps_by_perturbation.png", Inches(0.8), Inches(1.45), Inches(4.2), Inches(5.4))
    add_image_fitted(s22, "../../figures/20_umap_ps_score.png", Inches(5.2), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card22 = add_card(s22, Inches(9.0), Inches(1.45), Inches(3.533), Inches(5.4))
    tb22 = s22.shapes.add_textbox(Inches(9.15), Inches(1.6), Inches(3.233), Inches(5.1))
    tf22 = tb22.text_frame
    tf22.word_wrap = True
    
    bullets22 = [
        "PS Metric Formulation: Logistic classifier probability scoring the transcriptomic deviation of each single cell from WT controls.",
        "Response Spectrum (Fig 05): Ranks perturbations by mean PS, identifying high-penetrance drivers (GATA6: mean PS=0.978; FOXA2: 0.912; GLIS3: 0.895) versus low-penetrance modifiers.",
        "Single-Cell Heterogeneity (Fig 20): UMAP projection reveals that response strength is not uniform across cell types: TFs exhibit strong cell-state-gated activation windows.",
        "Methodological Audit: 10 perturbations (e.g. heterozygous lines, enhancer deletions) were skipped for PS due to target gene absence in expression matrix (detailed in backup)."
    ]
    format_bullets(tf22, bullets22, default_font_size=10)
    
    add_notes(s22, 
        "Slide 22 analyzes Axis 1: Perturbation Score (PS).\n\n"
        "In Figure 05, we rank all 37 genotypes by their single-cell PS distribution. We observe a wide spectrum: master regulators like GATA6 (mean PS = 0.978), FOXA2 (0.912), and GLIS3 (0.895) show near-complete penetrance, whereas other chromatin factors exhibit subtle or incomplete response.\n\n"
        "In Figure 20, projecting single-cell PS scores onto the global UMAP reveals that perturbation responsiveness is highly cell-state dependent: cells are only sensitive to transcription factor loss when that factor's active regulatory network is engaged.")

    # SLIDE 23: Axis 2 - Energy Distance
    s23 = prs.slides.add_slide(blank_layout)
    add_header(s23, "Phenotype Decomposition | Axis 2: Global Magnitude", 
               "Axis 2: Global Transcriptomic Phenotype Magnitude via Energy Distance", 
               "Non-parametric multivariate metric quantifying total transcriptomic displacement in 50-dimensional PCA space", "WIP")
    
    add_image_fitted(s23, "../../figures/06_energy_distance_by_perturbation.png", Inches(0.8), Inches(1.45), Inches(5.8), Inches(5.4))
    
    card23 = add_card(s23, Inches(6.8), Inches(1.45), Inches(5.733), Inches(5.4))
    tb23 = s23.shapes.add_textbox(Inches(7.0), Inches(1.6), Inches(5.333), Inches(5.1))
    tf23 = tb23.text_frame
    tf23.word_wrap = True
    
    bullets23 = [
        "Energy Distance Definition: Non-parametric statistical metric based on Euclidean distances between cell distributions X (perturbed) and Y (WT control) in 50 PCA dimensions:\nE(X,Y) = 2 E||X - Y|| - E||X - X'|| - E||Y - Y'||.",
        "Significance Testing: Evaluated via 1,000 permutations with Benjamini-Hochberg FDR correction; all 37 genotypes achieve FDR < 0.001.",
        "Quantitative Severity Hierarchy (Fig 06):\n• Rank 1: GATA6 (E = 4.71, extreme global displacement)\n• Rank 2: FOXA2 (E = 3.11, severe foregut defect)\n• Rank 3: RFX6 (E = 2.45, endocrine disruption)\n• Rank 4: HNF4A (E = 1.75) & NEUROG3 (E = 1.65).",
        "Conceptual Role: While PS asks 'Do cells respond?', Energy Distance asks 'How large is the entire transcriptomic reconfiguration across the genome?'"
    ]
    format_bullets(tf23, bullets23, default_font_size=10.5)
    
    add_notes(s23, 
        "Slide 23 introduces Axis 2: Energy Distance, appearing for the first time in this computational biology extension.\n\n"
        "Energy Distance is a rigorous statistical metric (V-statistic) measuring the true multi-dimensional distance between two single-cell distributions in 50-dimensional PCA space, accounting for both mean shift and dispersion.\n\n"
        "In Figure 06, we ranked all 37 genotypes by Energy Distance. GATA6 emerges as the single most severe perturbation with an Energy Distance of 4.71, followed by FOXA2 at 3.11 and RFX6 at 2.45.\n\n"
        "Energy Distance provides a robust, scale-invariant measure of global phenotype magnitude.")

    # SLIDE 24: Axis 3 - Directional lochNESS
    s24 = prs.slides.add_slide(blank_layout)
    add_header(s24, "Phenotype Decomposition | Axis 3: Directional Localization", 
               "Axis 3: Directional lochNESS Resolves Enrichment, Trapping, and Depletion", 
               "Using signed lochNESS as an analytical phenotype to separate focal accumulation from lineage loss", "WIP")
    
    add_image_fitted(s24, "../../figures/21_umap_lochness_score.png", Inches(0.8), Inches(1.45), Inches(4.2), Inches(5.4))
    add_image_fitted(s24, "../../figures/lochness_genotype_celltype_heatmap.png", Inches(5.2), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card24 = add_card(s24, Inches(9.0), Inches(1.45), Inches(3.533), Inches(5.4))
    tb24 = s24.shapes.add_textbox(Inches(9.15), Inches(1.6), Inches(3.233), Inches(5.1))
    tf24 = tb24.text_frame
    tf24.word_wrap = True
    
    bullets24 = [
        "Analytical Role: While pertTF predicted lochNESS, here we use signed lochNESS as an observed analytical measurement to decompose phenotypic direction.",
        "Sign Matters (Fig 21):\n• Positive lochNESS (> 0): Captures focal accumulation, progenitor trapping, and off-target lineage diversion.\n• Negative lochNESS (< 0): Captures lineage dropout, differentiation arrest, and developmental failure.",
        "Genotype × Cell-State Matrix (Heatmap): Maps exact enrichment/depletion profiles across all 10 curated cell types, resolving distinct biological mechanisms.",
        "Localization Power: Answers precisely WHERE perturbed cells end up on the manifold."
    ]
    format_bullets(tf24, bullets24, default_font_size=10)
    
    add_notes(s24, 
        "Slide 24 revisits lochNESS as Axis 3: Directional Localization.\n\n"
        "In pertTF, lochNESS was our prediction target. In this computational analysis, we use signed lochNESS as an analytical probe to map exactly where cells go.\n\n"
        "In Figure 21, the signed lochNESS UMAP cleanly separates positive enrichment (cells accumulating in specific states) from negative depletion (lineage dropout). The adjacent heatmap maps every single genotype across all cell types, resolving unique phenotypic signatures.")

    # SLIDE 25: Cross-Metric Coupling (PS vs Distance)
    s25 = prs.slides.add_slide(blank_layout)
    add_header(s25, "Cross-Metric Analysis | Coupling & Decoupling", 
               "Response Strength Predicts Global Phenotype Magnitude", 
               "High single-cell response penetrance (PS) strongly couples with global Energy Distance (rho = 0.81)", "WIP")
    
    add_image_fitted(s25, "../../figures/07_ps_vs_distance.png", Inches(0.8), Inches(1.45), Inches(5.8), Inches(5.4))
    
    card25 = add_card(s25, Inches(6.8), Inches(1.45), Inches(5.733), Inches(5.4))
    tb25 = s25.shapes.add_textbox(Inches(7.0), Inches(1.6), Inches(5.333), Inches(5.1))
    tf25 = tb25.text_frame
    tf25.word_wrap = True
    
    bullets25 = [
        "Strong Linear Coupling (Fig 07): Spearman correlation rho = 0.81 (p = 1.3 × 10^-6, n = 26 evaluated genotypes).\nLinear regression: Energy Distance = 3.65 · PS - 1.12.",
        "Biological Interpretation: When a transcription factor knockout achieves high cellular penetrance, the entire genome-wide transcriptomic state shifts proportionally relative to wild-type.",
        "Top Concordant Drivers: GATA6 (PS = 0.978, E = 4.71), FOXA2 (PS = 0.912, E = 3.11), and RFX6 (PS = 0.865, E = 2.45) anchor the upper quadrant.",
        "Key Conclusion: PS answers whether cells respond; Energy Distance confirms that high response penetrance reliably produces massive transcriptomic restructuring."
    ]
    format_bullets(tf25, bullets25, default_font_size=10.5)
    
    add_notes(s25, 
        "Slide 25 investigates the relationship between Axis 1 and Axis 2.\n\n"
        "In Figure 07, plotting Perturbation Score (PS) against Energy Distance reveals a very strong correlation of rho = 0.81 (p = 1.3e-6). Genotypes with high single-cell response penetrance—like GATA6, FOXA2, and RFX6—invariably exhibit the largest global transcriptomic shifts relative to wild-type.\n\n"
        "This proves that cellular engagement directly scales into global phenotype magnitude.")

    # SLIDE 26: Cross-Metric Decoupling (Distance vs lochNESS)
    s26 = prs.slides.add_slide(blank_layout)
    add_header(s26, "Cross-Metric Analysis | Coupling & Decoupling", 
               "Global Magnitude Does Not Specify Cellular Destination", 
               "Perturbations with identical Energy Distance diverge into completely different manifold fates", "WIP")
    
    add_image_fitted(s26, "../../figures/08_distance_vs_lochness_positive.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s26, "../../figures/12_distance_vs_lochness_absolute.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card26 = add_card(s26, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb26 = s26.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf26 = tb26.text_frame
    tf26.word_wrap = True
    
    bullets26 = [
        "Moderate Distance vs. lochNESS Correlation (Fig 08, 12):\n• Energy Distance vs. Absolute lochNESS: rho = 0.52 (p = 0.0016, n = 37).\n• Energy Distance vs. Positive lochNESS: rho = 0.44 (p = 0.008, n = 37).",
        "The Decoupling Insight: While Energy Distance measures total displacement magnitude, it is completely agnostic to direction on the manifold.",
        "Biological Example: GATA6 and FOXA2 both exhibit extreme Energy Distances (>3.0), but GATA6 moves cells exclusively into endothelial states, whereas FOXA2 diverts cells into hepatic progenitors.",
        "Methodological Lesson: Global distance alone cannot tell you WHERE cells travel; directional lochNESS is mandatory."
    ]
    format_bullets(tf26, bullets26, default_font_size=10.5)
    
    add_notes(s26, 
        "Slide 26 reveals a profound biological decoupling: global phenotype magnitude does NOT specify cellular destination.\n\n"
        "In Figures 08 and 12, Energy Distance correlates only moderately with lochNESS (rho = 0.44 to 0.52). Two perturbations can have the exact same global Energy Distance, but travel in completely opposite directions on the developmental manifold.\n\n"
        "For instance, GATA6 and FOXA2 both cause massive transcriptomic upheaval, but GATA6 drives cells into endothelial fates, while FOXA2 drives them into hepatic fates. This proves that global distance metrics alone are insufficient without directional manifold localization.")

    # SLIDE 27: Directional Decoupling (Negative vs Positive lochNESS)
    s27 = prs.slides.add_slide(blank_layout)
    add_header(s27, "Cross-Metric Analysis | Coupling & Decoupling", 
               "Directionality Decouples Lineage Enrichment from Depletion", 
               "Negative lochNESS captures active developmental blockade distinct from aberrant lineage expansion", "WIP")
    
    add_image_fitted(s27, "../../figures/09_distance_vs_lochness_negative.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s27, "../../figures/10_ps_vs_lochness_positive.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card27 = add_card(s27, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb27 = s27.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf27 = tb27.text_frame
    tf27.word_wrap = True
    
    bullets27 = [
        "Negative lochNESS Coupling (Fig 09): Energy Distance vs. Negative lochNESS exhibits a significant negative correlation (rho = -0.50, p = 0.0022).\nSevere knockouts drive both deeper lineage depletion (-lochNESS) and higher accumulation (+lochNESS).",
        "PS vs. Positive lochNESS (Fig 10): rho = 0.45 (p = 0.021, n = 26).\nTranscriptional response strength predicts the degree of focal cell-state trapping.",
        "PS vs. Negative lochNESS: rho = -0.42 (p = 0.033, n = 26).\nHigh-responding cells actively abandon canonical developmental pathways.",
        "Grand Analytical Principle: Decomposing lochNESS into positive (expansion/trapping) and negative (depletion/loss) components resolves opposing biological consequences of gene knockout."
    ]
    format_bullets(tf27, bullets27, default_font_size=10.5)
    
    add_notes(s27, 
        "Slide 27 explores the directional asymmetry between lineage enrichment and lineage depletion.\n\n"
        "In Figure 09, Energy Distance correlates negatively with negative lochNESS (rho = -0.50, p = 0.0022). This proves that severe perturbations do not merely push cells into off-target states (+lochNESS); they actively deplete canonical cell types (-lochNESS).\n\n"
        "In Figure 10, response penetrance (PS) correlates positively with focal trapping (rho = 0.45). By splitting lochNESS into positive and negative components, we can distinguish between active lineage conversion and developmental arrest.")

    # SLIDE 28: Case Study 1 - GATA6
    s28 = prs.slides.add_slide(blank_layout)
    add_header(s28, "Biological Case Study 1 | Multi-Metric Integration", 
               "Case Study 1: GATA6 — Endothelial Conversion & Focal Trapping", 
               "Connecting precursor biology, pertTF prediction, and WIP metrics for the top genome-wide responder", "CASE_STUDY")
    
    add_image_fitted(s28, "../../figures/per_genotype_combined/GATA6_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card28 = add_card(s28, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb28 = s28.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf28 = tb28.text_frame
    tf28.word_wrap = True
    
    bullets28 = [
        "1. Precursor Biology: GATA6 is required for definitive endoderm; knockout unleashes an endothelial-like fate (CD31+/CD34+).",
        "2. pertTF Prediction: In silico screening prioritized GATA6 as a top master factor whose knockout dramatically alters progenitor embedding trajectories.",
        "3. WIP Quantitative Profile (n = 1,500 cells):\n• Perturbation Score: Mean PS = 0.978 (Rank 1 / 26 responders).\n• Energy Distance: E = 4.71 (Rank 1 / 37, p < 0.001, extreme displacement).\n• Directional lochNESS: Positive lochNESS = +0.83, peak localized strictly in endothelial cells; Negative lochNESS = -0.74 in SC-β/endocrine cells.",
        "Synthesis: GATA6 demonstrates perfect multi-metric convergence: maximum cellular penetrance (PS), maximum global magnitude (Distance), and ultra-focal off-target trapping (+lochNESS)."
    ]
    format_bullets(tf28, bullets28, default_font_size=10.5)
    
    add_notes(s28, 
        "Slide 28 synthesizes all three layers of research for Case Study 1: GATA6.\n\n"
        "In the precursor study, we discovered that GATA6 knockout causes aberrant endothelial conversion. In pertTF, in-silico screening ranked GATA6 as a top master regulator.\n\n"
        "Now, our WIP analysis quantitatively deconstructs this phenotype: GATA6 is Rank 1 across all 37 genotypes in both response penetrance (mean PS = 0.978) and global Energy Distance (E = 4.71). Furthermore, its signed lochNESS score (+0.83) is tightly and exclusively focused on the endothelial cluster.\n\n"
        "This exemplifies how our computational metrics perfectly capture master binary fate switches.")

    # SLIDE 29: Case Study 2 - FOXA2
    s29 = prs.slides.add_slide(blank_layout)
    add_header(s29, "Biological Case Study 2 | Multi-Metric Integration", 
               "Case Study 2: FOXA2 — Pioneer Factor Loss & Hepatic Diversion", 
               "Pioneer TF knockout yields severe foregut failure and diversion to hepatic-like progenitors", "CASE_STUDY")
    
    add_image_fitted(s29, "../../figures/per_genotype_combined/FOXA2_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(6.8), Inches(5.4))
    
    card29 = add_card(s29, Inches(7.8), Inches(1.45), Inches(4.733), Inches(5.4))
    tb29 = s29.shapes.add_textbox(Inches(8.0), Inches(1.6), Inches(4.333), Inches(5.1))
    tf29 = tb29.text_frame
    tf29.word_wrap = True
    
    bullets29 = [
        "1. Precursor Biology: FOXA2 opens condensed chromatin in foregut endoderm; loss redirects cells toward hepatic lineages (AFP+/ALB+).",
        "2. pertTF Prediction: Accurately recovered embedding shifts in primitive foregut (PFG) and early progenitor states.",
        "3. WIP Quantitative Profile (n = 4,896 cells):\n• Perturbation Score: Mean PS = 0.912 (Rank 2 responder).\n• Energy Distance: E = 3.11 (Rank 2 / 37, severe global rewiring).\n• Directional lochNESS: Positive lochNESS = +0.54, concentrated in hepatic-like progenitor states; Negative lochNESS = -0.68 across all mature endocrine lineages.",
        "Synthesis: Unlike GATA6 which converts cells to mesodermal endothelial fates, FOXA2 loss retains endodermal character but diverts along the hepatic branch, quantified by high Energy Distance and hepatic lochNESS localization."
    ]
    format_bullets(tf29, bullets29, default_font_size=10.5)
    
    add_notes(s29, 
        "Slide 29 focuses on Case Study 2: FOXA2.\n\n"
        "FOXA2 is a canonical pioneer transcription factor required for foregut competence. In our WIP data, FOXA2 ranks second overall in phenotypic severity with an Energy Distance of 3.11 and a mean PS of 0.912 across 4,896 single cells.\n\n"
        "Its lochNESS profile shows strong positive accumulation in hepatic-like progenitor clusters and complete depletion of endocrine cells. This confirms that pioneer factor loss triggers broad developmental derailment at the foregut stage.")

    # SLIDE 30: Case Study 3 - NEUROG3 vs PDX1
    s30 = prs.slides.add_slide(blank_layout)
    add_header(s30, "Biological Case Study 3 | Multi-Metric Integration", 
               "Case Study 3: NEUROG3 vs. PDX1 — Divergent Endocrine Checkpoints", 
               "Comparing pure endocrine arrest (NEUROG3) with enterochromaffin diversion (PDX1)", "CASE_STUDY")
    
    add_image_fitted(s30, "../../figures/per_genotype_combined/NEUROG3_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s30, "../../figures/per_genotype_combined/PDX1_ps_lochness_umap.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card30 = add_card(s30, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb30 = s30.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf30 = tb30.text_frame
    tf30.word_wrap = True
    
    bullets30 = [
        "NEUROG3 (Ngn3, n = 1,543): Master endocrine commitment factor.\n• Energy Distance: E = 1.65 (Significant, p < 0.001).\n• lochNESS: 0% mature SC-β cells (log2 OR = -inf, neg lochNESS = -0.58). Traps cells in pre-endocrine progenitors without generating SC-EC cells.",
        "PDX1 (n = 1,632): Pancreatic homeobox master factor.\n• Energy Distance: E = 1.48 (Significant, p < 0.001).\n• lochNESS: Severe depletion of SC-β (neg lochNESS = -0.62) accompanied by massive positive lochNESS in SC-EC cells (+0.48, log2 OR = +2.4).",
        "Mechanistic Distinction: NEUROG3 loss blocks entry into the endocrine lineage entirely; PDX1 loss permits endocrine entry but misroutes cells into the serotonin-producing enterochromaffin fate."
    ]
    format_bullets(tf30, bullets30, default_font_size=10.5)
    
    add_notes(s30, 
        "Slide 30 compares two essential endocrine regulators: NEUROG3 and PDX1.\n\n"
        "Both factors are required for normal beta-cell formation, but our 3-axis analysis reveals completely different failure mechanisms.\n\n"
        "In NEUROG3 knockout, cells fail to enter the endocrine lineage altogether, producing pure negative lochNESS in beta-cells (-0.58) and trapping cells in pre-endocrine states.\n\n"
        "In PDX1 knockout, cells enter the endocrine lineage, but are shunted away from beta-cells into enterochromaffin-like (SC-EC) cells, producing strong positive lochNESS (+0.48) in SC-EC. This demonstrates the power of directional phenotyping.")

    # SLIDE 31: Case Study 4 - HNF4A & GLIS3
    s31 = prs.slides.add_slide(blank_layout)
    add_header(s31, "Biological Case Study 4 | Multi-Metric Integration", 
               "Case Study 4: HNF4A & GLIS3 — Dosage Concordance & High Responders", 
               "HNF4A dosage symmetry in DistanceSpace and GLIS3 high-penetrance endocrine deregulation", "CASE_STUDY")
    
    add_image_fitted(s31, "../../figures/per_genotype_combined/HNF4A_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s31, "../../figures/per_genotype_combined/GLIS3_ps_lochness_umap.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card31 = add_card(s31, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb31 = s31.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf31 = tb31.text_frame
    tf31.word_wrap = True
    
    bullets31 = [
        "HNF4A Dosage Concordance (MODY1):\n• HNF4A knockout (n = 987, E = 1.75) and heterozygous HNF4Ahet (n = 829, E = 1.86) exhibit near-identical transcriptomic displacement.\n• In DistanceSpace, HNF4A <-> HNF4Ahet distance is d = 0.0905 (Rank 1 closest pair across all 630 pairwise comparisons).\n• Explains why heterozygous loss in human MODY1 is sufficient for clinical diabetes.",
        "GLIS3 Neonatal Diabetes Master Driver:\n• GLIS3 exhibits extreme cellular penetrance (PS = 0.895, E = 1.85, n = 935 cells).\n• lochNESS reveals massive deregulation across endocrine progenitors and ductal states.",
        "Clinical Relevance: Validates that our multi-metric pipeline captures human haploinsufficiency and neonatal monogenic diabetes genetics with exceptional precision."
    ]
    format_bullets(tf31, bullets31, default_font_size=10.5)
    
    add_notes(s31, 
        "Slide 31 presents Case Study 4: HNF4A and GLIS3.\n\n"
        "HNF4A is the causative gene for MODY1 diabetes. In our data, HNF4A full-knockout (E = 1.75) and heterozygous HNF4Ahet (E = 1.86) exhibit remarkable dosage concordance, forming the closest nearest-neighbor pair across all 630 combinations in DistanceSpace (d = 0.0905). This provides a molecular explanation for human haploinsufficiency.\n\n"
        "GLIS3, a known neonatal diabetes gene, emerges as a top-tier responder with mean PS = 0.895 and extensive endocrine disruption.")

    # SLIDE 32: Case Study 5 - RFX6 & HHEX
    s32 = prs.slides.add_slide(blank_layout)
    add_header(s32, "Biological Case Study 5 | Multi-Metric Integration", 
               "Case Study 5: RFX6 & HHEX — Endocrine Maturation & Enhancer Phenocopy", 
               "RFX6 validation across primary tissue and HHEX non-coding enhancer deletion mirroring coding knockout", "CASE_STUDY")
    
    add_image_fitted(s32, "../../figures/per_genotype_combined/RFX6_ps_lochness_umap.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s32, "../../figures/per_genotype_combined/HHEX_ps_lochness_umap.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card32 = add_card(s32, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb32 = s32.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf32 = tb32.text_frame
    tf32.word_wrap = True
    
    bullets32 = [
        "RFX6 Mitchell-Riley Syndrome Master Factor:\n• Ranks #3 in global severity (E = 2.45, PS = 0.865, n = 3,467 cells).\n• lochNESS reveals extreme SC-β depletion alongside massive SC-EC expansion (+0.42).\n• pertTF siRNA knockdown validation in primary islets confirms translation to adult human tissue.",
        "HHEX Coding KO vs. Enhancer Deletion Phenocopy:\n• HHEX coding knockout (E = 1.34) and non-coding enhancer deletion HHEXe (E = 1.32) cluster together in DistanceSpace (d = 0.1142, Rank 2 closest pair across all 630 combinations).\n• Proves that non-coding regulatory deletions can fully phenocopy coding loss-of-function.",
        "Cross-System Integration: Connects early precursor biology, transformer transfer learning, and quantitative distance phenotyping."
    ]
    format_bullets(tf32, bullets32, default_font_size=10.5)
    
    add_notes(s32, 
        "Slide 32 presents Case Study 5: RFX6 and HHEX.\n\n"
        "RFX6, mutated in Mitchell-Riley syndrome, is a top-3 global responder with an Energy Distance of 2.45 and PS of 0.865. Its knockout phenotype was directly validated in pertTF via siRNA knockdown in primary human islets.\n\n"
        "HHEX presents a compelling non-coding finding: targeted deletion of an upstream HHEX enhancer (HHEXe) produces an Energy Distance and lochNESS profile nearly indistinguishable from coding knockout (d = 0.1142, Rank 2 closest pair). This proves our metrics accurately evaluate non-coding regulatory mutations.")

    # SLIDE 33: Higher-Order Organization
    s33 = prs.slides.add_slide(blank_layout)
    add_header(s33, "System Architecture | Higher-Order Organization", 
               "Higher-Order Organization: DistanceSpace & Regulatory Modules", 
               "Mapping the 630-pair phenotypic distance manifold, co-functional TF modules, and gene programs", "WIP")
    
    add_image_fitted(s33, "../../figures/14_distance_space.png", Inches(0.8), Inches(1.45), Inches(3.6), Inches(5.4))
    add_image_fitted(s33, "../../figures/18_module_network.png", Inches(4.5), Inches(1.45), Inches(3.6), Inches(5.4))
    
    card33 = add_card(s33, Inches(8.2), Inches(1.45), Inches(4.333), Inches(5.4))
    tb33 = s33.shapes.add_textbox(Inches(8.4), Inches(1.6), Inches(3.933), Inches(5.1))
    tf33 = tb33.text_frame
    tf33.word_wrap = True
    
    bullets33 = [
        "DistanceSpace Manifold (Fig 14): 2D UMAP embedding of the full 37 × 37 pairwise Energy Distance matrix reveals functional TF clustering (e.g. HNF4A/HNF4Ahet cluster; FOXA1/FOXA2 cluster).",
        "Co-Functional Modules (Fig 18): Reconstructed 6 directed TF regulatory modules (M1-M6) capturing shared downstream transcriptional programs.",
        "Downstream Gene Programs (P1-P8): ORA pathway enrichment (MSigDB Hallmark / Reactome) links modules to oxidative phosphorylation, Notch signaling, epithelial-mesenchymal transition, and insulin secretion.",
        "System-Level Architecture: Moves from individual gene phenotypes to a comprehensive, network-level blueprint of human pancreatic regulation."
    ]
    format_bullets(tf33, bullets33, default_font_size=10)
    
    add_notes(s33, 
        "Slide 33 extends our framework to higher-order system architecture.\n\n"
        "In Figure 14, DistanceSpace embeds all 630 pairwise Energy Distances into a 2D manifold, revealing that transcription factors with shared biological functions cluster tightly together.\n\n"
        "In Figure 18, we mapped 6 co-functional regulatory modules (M1 to M6) driving 8 downstream gene programs. Over-representation analysis connects these modules to core developmental pathways like Notch signaling and oxidative phosphorylation, providing a global network map of human pancreas development.")

    # SLIDE 34: Master Summary Atlas
    s34 = prs.slides.add_slide(blank_layout)
    add_header(s34, "Grand Synthesis | Master Perturbation Atlas", 
               "Integrated Multi-Metric Summary Across All 37 Genotypes", 
               "Master quantitative alignment of single-cell counts, response penetrance, Energy Distance, and directional lochNESS", "SYNTHESIS")
    
    add_image_fitted(s34, "../../figures/19_perturbation_summary.png", Inches(0.8), Inches(1.45), Inches(7.4), Inches(5.4))
    
    card34 = add_card(s34, Inches(8.4), Inches(1.45), Inches(4.133), Inches(5.4))
    tb34 = s34.shapes.add_textbox(Inches(8.6), Inches(1.6), Inches(3.733), Inches(5.1))
    tf34 = tb34.text_frame
    tf34.word_wrap = True
    
    bullets34 = [
        "Master Multi-Metric Atlas (Fig 19): Aligns all 37 genotypes across:\n1. Cell counts (n = 182 to 5,668)\n2. PS mean / median (penetrance)\n3. Energy Distance (magnitude)\n4. Directional lochNESS (pos/neg/abs).",
        "Visual Confirmation of Decoupling: Notice how high Energy Distance bars (e.g. GATA6, FOXA2, RFX6) align with divergent positive and negative lochNESS profiles.",
        "Quantitative Reference: Serves as an open, auditable benchmark for the perturbation genomics community.",
        "A Complete Multi-Dimensional Map: Demonstrates that full phenotypic characterization requires aligning penetrance, distance, and manifold localization."
    ]
    format_bullets(tf34, bullets34, default_font_size=10)
    
    add_notes(s34, 
        "Slide 34 presents Figure 19: our master multi-metric atlas synthesizing all 37 genotypes.\n\n"
        "Across all columns, this atlas aligns cell counts, PS response penetrance, Energy Distance magnitude, and directional lochNESS scores.\n\n"
        "Looking across the rows, you can visually observe both coupling (high PS aligns with high Energy Distance) and decoupling (high Energy Distance produces distinct positive and negative lochNESS patterns). This multi-panel synthesis represents the definitive quantitative summary of our perturbation dataset.")

    # SLIDE 35: Closing the Loop
    s35 = prs.slides.add_slide(blank_layout)
    add_header(s35, "Grand Synthesis | Future Perturbation Models", 
               "Closing the Loop: Toward Phenotype-Aware Perturbation Modeling", 
               "How statistical phenotype decomposition informs the next generation of predictive transformer architectures", "SYNTHESIS")
    
    steps = [
        ("1. BIOLOGICAL SYSTEM", "Knockout Village", "79 hPSC lines across 5 differentiation stages captures true lineage rewiring and endocrine competition.", COLOR_BLUE_ACCENT),
        ("2. DATA QC & SIGNAL", "Manifold Characterization", "Descriptive QC verifies structured perturbation signal, cell-state separation, and stage-specific kinetics.", COLOR_CYAN_ACCENT),
        ("3. pertTF GENERALIZATION", "Context-Aware ML", "Learns shared representations to predict unseen cell contexts, unmutated genes, CRISPRi, and primary T2D states.", COLOR_PURPLE_ACCENT),
        ("4. PHENOTYPE DECOMPOSITION", "3-Axis Biology", "Decomposes phenotype into response strength (PS), global magnitude (Energy Distance), and localization (lochNESS).", COLOR_AMBER_ACCENT),
        ("5. FUTURE ARCHITECTURE", "Phenotype-Aware ML", "Decomposed biological metrics provide candidate multi-task objectives to train and evaluate future models.", COLOR_GREEN_ACCENT)
    ]
    
    for i, (stitle, ssub, sbody, scolor) in enumerate(steps):
        x = Inches(0.8 + i * 2.38)
        y = Inches(1.5)
        w = Inches(2.26)
        h = Inches(5.4)
        
        card = add_card(s35, x, y, w, h, bg_rgb=COLOR_CARD_BG, border_rgb=COLOR_CARD_BORDER)
        strip = s35.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, Inches(0.12))
        strip.fill.solid()
        strip.fill.fore_color.rgb = scolor
        strip.line.fill.background()
        
        tb = s35.shapes.add_textbox(x + Inches(0.1), y + Inches(0.2), w - Inches(0.2), h - Inches(0.3))
        tf = tb.text_frame
        tf.word_wrap = True
        
        p = tf.paragraphs[0]
        p.text = stitle
        p.font.size = Pt(9.5)
        p.font.bold = True
        p.font.color.rgb = scolor
        p.space_after = Pt(2)
        
        p = tf.add_paragraph()
        p.text = ssub
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_NAVY
        p.space_after = Pt(8)
        
        p = tf.add_paragraph()
        p.text = sbody
        p.font.size = Pt(9.5)
        p.font.color.rgb = COLOR_DARK_SLATE
        
    add_notes(s35, 
        "Slide 35 closes the loop by showing how our computational biology findings feed directly back into future machine learning models.\n\n"
        "We began with an experimental perturbation system in human pancreatic development. We verified data quality and structured perturbation signal. pertTF demonstrated that deep transformers can generalize perturbation effects across unseen biological contexts.\n\n"
        "Our computational decomposition revealed that complete phenotypes comprise response penetrance (PS), global magnitude (Energy Distance), and directional localization (lochNESS).\n\n"
        "Looking forward, these orthogonal dimensions provide candidate multi-task loss objectives and evaluation modalities for next-generation, phenotype-aware perturbation models.")

    # SLIDE 36: Final Scientific Summary
    s36 = prs.slides.add_slide(blank_layout)
    bg36 = s36.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg36.fill.solid()
    bg36.fill.fore_color.rgb = COLOR_DARK_HERO_BG
    bg36.line.fill.background()

    card36 = add_card(s36, Inches(1.2), Inches(1.2), Inches(10.933), Inches(5.1), 
                      bg_rgb=RGBColor(18, 30, 66), border_rgb=RGBColor(45, 62, 110))
    
    tb36 = s36.shapes.add_textbox(Inches(1.6), Inches(1.5), Inches(10.133), Inches(4.5))
    tf36 = tb36.text_frame
    tf36.word_wrap = True
    
    p = tf36.paragraphs[0]
    p.text = "CORE SCIENTIFIC TAKEAWAY"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = RGBColor(96, 165, 250)
    p.space_after = Pt(8)
    
    p = tf36.add_paragraph()
    p.text = "A Unified Framework for Perturbation Genomics"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(14)
    
    summary_bullets = [
        "1. Biological Experiments Define the Problem: Directed differentiation of knockout villages captures true lineage rewiring, endocrine competition, and disease genetics in human cells.",
        "2. Computational QC Establishes the Signal: Rigorous characterization of cell states, stage kinetics, and perturbation separation confirms coherent signal before modeling.",
        "3. Machine Learning Generalizes Beyond Experimental Limits: pertTF transfers learned perturbation operators across unmeasured cell types, unmutated genes, and primary human donor tissue.",
        "4. Computational Biology Decomposes the Phenotype: Breaking perturbation effects into response penetrance (PS), global magnitude (Energy Distance), and directional localization (lochNESS) provides biological interpretability.",
        "5. Decomposed Dimensions Guide Next-Generation Models: Closing the loop by providing candidate multi-task objectives for future phenotype-aware perturbation transformers."
    ]
    for b in summary_bullets:
        p = tf36.add_paragraph()
        parts = b.split(":", 1)
        r1 = p.add_run()
        r1.text = parts[0] + ":"
        r1.font.bold = True
        r1.font.size = Pt(11)
        r1.font.color.rgb = RGBColor(253, 230, 138)
        r2 = p.add_run()
        r2.text = parts[1]
        r2.font.bold = False
        r2.font.size = Pt(10.5)
        r2.font.color.rgb = RGBColor(226, 232, 240)
        p.space_after = Pt(8)

    add_notes(s36, 
        "In summary, this presentation establishes a continuous, biology-first paradigm for perturbation genomics.\n\n"
        "Biological experiments define the problem. Computational analysis verifies that real, structured perturbation signal exists. Machine learning allows us to generalize that signal beyond experimentally measured conditions. Computational biology then helps us interpret the model and decompose the phenotype into meaningful biological dimensions. Finally, those biological dimensions guide the next generation of predictive perturbation models.\n\n"
        "Thank you for your attention.")

    # SLIDE 37: Backup Divider
    s37 = prs.slides.add_slide(blank_layout)
    bg37 = s37.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg37.fill.solid()
    bg37.fill.fore_color.rgb = RGBColor(30, 41, 59)
    bg37.line.fill.background()

    card37 = add_card(s37, Inches(1.2), Inches(1.2), Inches(10.933), Inches(5.1), 
                      bg_rgb=RGBColor(15, 23, 42), border_rgb=RGBColor(71, 85, 105))
    
    tb37 = s37.shapes.add_textbox(Inches(1.6), Inches(1.8), Inches(10.133), Inches(3.9))
    tf37 = tb37.text_frame
    tf37.word_wrap = True
    
    p = tf37.paragraphs[0]
    p.text = "TECHNICAL BACKUP & METHODOLOGICAL AUDITS"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = RGBColor(148, 163, 184)
    p.space_after = Pt(12)
    
    p = tf37.add_paragraph()
    p.text = "Supporting Technical Slides & Data Audits"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = RGBColor(255, 255, 255)
    p.space_after = Pt(12)
    
    p = tf37.add_paragraph()
    p.text = "• BKP 1: Methodological Audit, Mathematical Formulations & Skipped Targets\n• BKP 2: Full 36-Genotype Single-Cell PS & lochNESS UMAP Atlases\n• BKP 3: High-Resolution Genotype × Cell-State Response Matrices\n• BKP 4: DistanceSpace Pairwise Matrix & Nearest Phenotypic Neighbors\n• BKP 5: Extended pertTF Foundation Model Benchmarks & Mixscape Details\n• BKP 6: Precursor Study Genotyping QC & Supplementary Data"
    p.font.size = Pt(12)
    p.font.color.rgb = RGBColor(203, 213, 225)

    add_notes(s37, "Backup section containing detailed mathematical formulations, complete 36-genotype atlases, full distance matrices, skipped-target audits, and extended foundation model benchmarks.")

    # SLIDE 38: Backup BKP1 - Formulations & Skipped Targets
    s38 = prs.slides.add_slide(blank_layout)
    add_header(s38, "Backup | Methodological Audit", 
               "Mathematical Formulations & Skipped Target Audit", 
               "Rigorous definitions of Energy Distance, lochNESS, and transparent accounting of 10 skipped perturbations", "BACKUP")
    
    cw = Inches(5.7)
    ch = Inches(5.4)
    
    c_m1 = add_card(s38, Inches(0.8), Inches(1.45), cw, ch)
    tb_m1 = s38.shapes.add_textbox(Inches(1.0), Inches(1.6), cw - Inches(0.4), ch - Inches(0.3))
    tf_m1 = tb_m1.text_frame
    tf_m1.word_wrap = True
    p = tf_m1.paragraphs[0]
    p.text = "Mathematical Formulations"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_NAVY
    p.space_after = Pt(8)
    b_m1 = [
        "Energy Distance Estimator (V-Statistic):\nE(X,Y) = 2/mn sum(||x_i - y_j||) - 1/m^2 sum(||x_i - x_i'||) - 1/n^2 sum(||y_j - y_j'||)\nComputed on 50 PCA dimensions. Tested via 1,000 permutations with BH-FDR correction.",
        "lochNESS Formulation:\nlochNESS_k(x) = log2( (n_KO,k(x)/N_KO) / (n_WT,k(x)/N_WT) + eps )\nComputed over k = 30 nearest neighbors in transcriptomic PCA space.",
        "Perturbation Score (PS):\nLogistic regression classifier trained on target gene expression vs. WT background, predicting per-cell response probability."
    ]
    format_bullets(tf_m1, b_m1, default_font_size=10)
    
    c_m2 = add_card(s38, Inches(6.833), Inches(1.45), cw, ch)
    tb_m2 = s38.shapes.add_textbox(Inches(7.033), Inches(1.6), cw - Inches(0.4), ch - Inches(0.3))
    tf_m2 = tb_m2.text_frame
    tf_m2.word_wrap = True
    p = tf_m2.paragraphs[0]
    p.text = "Audit of 10 Skipped PS Perturbations"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = COLOR_RED_ACCENT
    p.space_after = Pt(8)
    b_m2 = [
        "1. GATA4het (1,957 cells): Target gene not in expression matrix.",
        "2. GATA6het (2,266 cells): Target gene not in expression matrix.",
        "3. HHEXe (1,487 cells): Enhancer deletion; target not in expression matrix.",
        "4. HHEXhet (328 cells): Target gene not in expression matrix.",
        "5. HNF4Ahet (829 cells): Target gene not in expression matrix.",
        "6. NANOGe-het (996 cells): Enhancer deletion; target not in matrix.",
        "7. ONECUT1e (2,436 cells): Enhancer deletion; target not in matrix.",
        "8. PDX1het (469 cells): Target gene not in expression matrix.",
        "9. QSER1TET1 (1,157 cells): Double knockout; multi-target scoring.",
        "10. TET1/2/3 (948 cells): Triple knockout; multi-target scoring.",
        "Audit Conclusion: All 10 exclusions are purely methodological due to gene matrix naming constraints; all 10 have full Energy Distance and lochNESS scores."
    ]
    format_bullets(tf_m2, b_m2, default_font_size=9.5)
    
    add_notes(s38, "Backup Slide 38 provides transparent mathematical formulations for Energy Distance, lochNESS, and PS, alongside an auditable record explaining exactly why 10 perturbations were excluded from PS scoring.")

    # SLIDE 39: Backup BKP2 - Full UMAP Atlases
    s39 = prs.slides.add_slide(blank_layout)
    add_header(s39, "Backup | Full Screen Atlases", 
               "Full 36-Genotype Single-Cell PS and lochNESS UMAP Atlases", 
               "Comprehensive single-cell resolution across every evaluated perturbation in the knockout village", "BACKUP")
    
    add_image_fitted(s39, "../../figures/ps_per_genotype_umap_atlas.png", Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.4))
    add_image_fitted(s39, "../../figures/lochness_per_genotype_umap_atlas.png", Inches(6.833), Inches(1.45), Inches(5.7), Inches(5.4))
    
    add_notes(s39, "Backup Slide 39 displays the full 36-genotype atlas for single-cell PS score density (left) and lochNESS spatial projection (right), providing complete visual documentation across all lines.")

    # SLIDE 40: Backup BKP3 - Heatmaps
    s40 = prs.slides.add_slide(blank_layout)
    add_header(s40, "Backup | High-Resolution Matrices", 
               "High-Resolution Genotype × Cell-State Response Heatmaps", 
               "Complete 37-genotype response landscape across all 10 curated differentiation cell types", "BACKUP")
    
    add_image_fitted(s40, "../../figures/ps_genotype_celltype_heatmap.png", Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.4))
    add_image_fitted(s40, "../../figures/lochness_genotype_celltype_heatmap.png", Inches(6.833), Inches(1.45), Inches(5.7), Inches(5.4))
    
    add_notes(s40, "Backup Slide 40 shows complete genotype × cell state response heatmaps for PS (left) and lochNESS (right), covering all 10 cell types and 37 genotypes.")

    # SLIDE 41: Backup BKP4 - DistanceSpace Audit
    s41 = prs.slides.add_slide(blank_layout)
    add_header(s41, "Backup | DistanceSpace Audit", 
               "Full 630-Pair DistanceSpace Matrix & Top Phenotypic Neighbors", 
               "Quantitative ranking of pairwise Energy Distances across all 37 perturbed lines", "BACKUP")
    
    add_image_fitted(s41, "../../figures/14_distance_space.png", Inches(0.8), Inches(1.45), Inches(5.4), Inches(5.4))
    
    card41 = add_card(s41, Inches(6.4), Inches(1.45), Inches(6.133), Inches(5.4))
    tb41 = s41.shapes.add_textbox(Inches(6.6), Inches(1.6), Inches(5.733), Inches(5.1))
    tf41 = tb41.text_frame
    tf41.word_wrap = True
    
    bullets41 = [
        "Top Nearest Phenotypic Neighbors in DistanceSpace:\n• 1. HNF4A <-> HNF4Ahet: d = 0.0905 (Rank 1 closest pair across all 630 combinations)\n• 2. HHEX <-> HHEXe: d = 0.1142 (Enhancer phenocopies coding loss)\n• 3. FOXA1 <-> FOXA2: d = 0.3471 (Paralog functional convergence)\n• 4. ARX <-> NKX2-2: d = 0.6355 (Alpha/beta lineage coregulators)\n• 5. ARX <-> MNX1: d = 0.6982 (Endocrine specifiers).",
        "Biological Takeaway: DistanceSpace correctly groups known paralogs, dosage equivalents, and regulatory partners entirely unsupervised based on whole-transcriptome Energy Distances."
    ]
    format_bullets(tf41, bullets41, default_font_size=10.5)
    
    add_notes(s41, "Backup Slide 41 provides the full quantitative ranking of top nearest neighbor pairs in DistanceSpace across all 630 pairwise combinations, highlighting dosage concordance and paralog convergence.")

    # SLIDE 42: Backup BKP5 - Extended Benchmarks
    s42 = prs.slides.add_slide(blank_layout)
    add_header(s42, "Backup | Extended Benchmarks", 
               "Extended pertTF Benchmarks & CRISPRi Mixscape Analysis", 
               "Detailed performance comparisons against scFoundation and Mixscape-classified single-cell distributions", "BACKUP")
    
    add_image_fitted(s42, "cropped_panels/pertTF_supp_fig3_4_benchmarks.png", Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.4))
    add_image_fitted(s42, "cropped_panels/pertTF_supp_fig5_6_crispri_primary.png", Inches(6.833), Inches(1.45), Inches(5.7), Inches(5.4))
    
    add_notes(s42, "Backup Slide 42 presents supplementary benchmarks from the pertTF manuscript, including head-to-head evaluations against scFoundation and Mixscape single-cell response distributions.")

    # SLIDE 43: Backup BKP6 - Precursor QC
    s43 = prs.slides.add_slide(blank_layout)
    add_header(s43, "Backup | Precursor Study Data", 
               "Precursor Study QC, Genotyping & ISL1 Rescue Validation", 
               "Sanger sequencing verification across 79 clones and extended ISL1 overexpression rescue assays", "BACKUP")
    
    add_image_fitted(s43, "cropped_panels/precursor_supp_fig1_qc.png", Inches(0.8), Inches(1.45), Inches(5.7), Inches(5.4))
    add_image_fitted(s43, "cropped_panels/precursor_supp_fig8_isl1_rescue.png", Inches(6.833), Inches(1.45), Inches(5.7), Inches(5.4))
    
    add_notes(s43, "Backup Slide 43 provides quality control data from the precursor study, showing Sanger sequencing confirmation across 79 hPSC clones and extended ISL1 rescue assays.")

    # Save presentation
    out_pptx = "Master_Scientific_Story_pertTF_Phenotyping.pptx"
    prs.save(out_pptx)
    print(f"Presentation saved successfully to {out_pptx} with {len(prs.slides)} slides!")

    out_pptx_primary = "Thomas_Sandmann_Master_Biology_Computation_pertTF.pptx"
    prs.save(out_pptx_primary)
    print(f"Also updated primary deck: {out_pptx_primary}")

if __name__ == "__main__":
    build_presentation()
