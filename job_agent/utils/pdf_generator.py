import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

def generate_resume_pdf(resume_text: str, output_path: str) -> str:
    """
    Parses resume text (markdown-like) and generates a clean, professional PDF resume.
    """
    # Create target directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Document Setup - 0.5 inch margins to ensure single-page fitting for average resumes
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    name_style = ParagraphStyle(
        'NameStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1A365D") # Deep Navy
    )
    
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4A5568") # Dark Grey
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#2B6CB0"), # Slate Blue
        spaceBefore=8,
        spaceAfter=3
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=4
    )
    
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#2D3748"),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3
    )
    
    story = []
    
    # Helper to draw a thin horizontal line below section headers
    def get_divider():
        t = Table([['']], colWidths=[540], rowHeights=[2])
        t.setStyle(TableStyle([
            ('LINEBELOW', (0,0), (-1,-1), 0.75, colors.HexColor("#CBD5E0")),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        return t
        
    lines = resume_text.split('\n')
    
    # Flag to identify top headers (Name/Contact info) before first section
    in_header = True
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        # 1. Main Header / Name (e.g. starts with "# " or first line is Name)
        if line.startswith("# ") and not line.startswith("## "):
            name_text = line.replace("#", "").strip()
            story.append(Paragraph(name_text, name_style))
            story.append(Spacer(1, 4))
            continue
            
        # 2. Section Headers (e.g. "## Experience")
        if line.startswith("## "):
            in_header = False
            section_text = line.replace("##", "").strip().upper()
            story.append(Spacer(1, 6))
            story.append(Paragraph(section_text, section_style))
            story.append(get_divider())
            story.append(Spacer(1, 4))
            continue
            
        # 3. Bullet points
        if line.startswith("- ") or line.startswith("* ") or line.startswith("• "):
            # Replace prefix with bullet character
            bullet_text = re.sub(r'^[-*•]\s*', '&bull; ', line)
            story.append(Paragraph(bullet_text, bullet_style))
            continue
            
        # 4. Header metadata/contact info (if we are in the header block)
        if in_header:
            story.append(Paragraph(line, contact_style))
            story.append(Spacer(1, 2))
        else:
            # 5. Regular body text
            story.append(Paragraph(line, body_style))
            
    # Build PDF
    doc.build(story)
    return output_path
