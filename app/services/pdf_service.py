"""
PDF Report Generator Service
Generates professional PDF reports for skill gap analysis
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from io import BytesIO
from datetime import datetime
import boto3
from app.core.config import settings
import requests

# Colors
PRIMARY_COLOR = HexColor("#6366F1")  # Indigo
SECONDARY_COLOR = HexColor("#8B5CF6")  # Purple
SUCCESS_COLOR = HexColor("#10B981")  # Green
WARNING_COLOR = HexColor("#F59E0B")  # Amber
DANGER_COLOR = HexColor("#EF4444")  # Red
DARK_BG = HexColor("#1F2937")
LIGHT_BG = HexColor("#F3F4F6")


def create_styles():
    """Create custom styles for the PDF."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=PRIMARY_COLOR,
        spaceAfter=30,
        alignment=TA_CENTER
    ))
    
    # Section heading
    styles.add(ParagraphStyle(
        name='SectionHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=PRIMARY_COLOR,
        spaceBefore=20,
        spaceAfter=12,
        borderPadding=(0, 0, 5, 0)
    ))
    
    # Body text
    styles.add(ParagraphStyle(
        name='BodyText',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY
    ))
    
    # Bullet points
    styles.add(ParagraphStyle(
        name='BulletPoint',
        parent=styles['Normal'],
        fontSize=10,
        leftIndent=20,
        bulletIndent=10,
        leading=14
    ))
    
    return styles


def create_skill_bar_chart(skills_data: list[dict], title: str = "Skill Demand") -> Drawing:
    """Create a bar chart showing skill demand/scores."""
    drawing = Drawing(400, 200)
    
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 50
    chart.width = 300
    chart.height = 125
    
    # Extract data
    skill_names = [s.get("skill", s.get("name", ""))[:12] for s in skills_data[:8]]
    scores = [s.get("score", s.get("count", 50)) for s in skills_data[:8]]
    
    chart.data = [scores]
    chart.categoryAxis.categoryNames = skill_names
    chart.categoryAxis.labels.angle = 45
    chart.categoryAxis.labels.fontSize = 8
    
    chart.bars[0].fillColor = PRIMARY_COLOR
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(scores) * 1.2 if scores else 100
    
    drawing.add(chart)
    return drawing


def generate_pdf_report(
    user_name: str,
    user_email: str,
    preferred_roles: list[str],
    analysis: dict,
    user_skills: list[dict]
) -> BytesIO:
    """
    Generate a professional PDF report from the skill gap analysis.
    Returns BytesIO buffer containing the PDF.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1*cm,
        leftMargin=1*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    styles = create_styles()
    story = []
    
    # Title Page
    story.append(Spacer(1, 2*inch))
    story.append(Paragraph("Skill Gap Analysis Report", styles['CustomTitle']))
    story.append(Spacer(1, 0.5*inch))
    
    # User info
    story.append(Paragraph(f"<b>Prepared for:</b> {user_name}", styles['BodyText']))
    story.append(Paragraph(f"<b>Email:</b> {user_email}", styles['BodyText']))
    story.append(Paragraph(f"<b>Target Roles:</b> {', '.join(preferred_roles)}", styles['BodyText']))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}", styles['BodyText']))
    
    story.append(PageBreak())
    
    # Executive Summary
    story.append(Paragraph("1. Executive Summary", styles['SectionHeading']))
    summary = analysis.get("executive_summary", "No summary available.")
    story.append(Paragraph(summary, styles['BodyText']))
    story.append(Spacer(1, 0.3*inch))
    
    # Overall Scores Box
    overall_gap = analysis.get("overall_gap_percentage", 0)
    overall_fit = analysis.get("overall_fit_score", 0)
    
    score_data = [
        ["Metric", "Score"],
        ["Overall Fit Score", f"{overall_fit}/100"],
        ["Skill Gap", f"{overall_gap}%"],
        ["Market Readiness", f"{analysis.get('skill_assessment', {}).get('market_readiness_score', 'N/A')}/10"]
    ]
    
    score_table = Table(score_data, colWidths=[200, 150])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), LIGHT_BG),
        ('GRID', (0, 0), (-1, -1), 1, PRIMARY_COLOR)
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Market Trends Section
    story.append(Paragraph("2. Current Market Trends", styles['SectionHeading']))
    market = analysis.get("market_trends", {})
    
    story.append(Paragraph("<b>Top In-Demand Skills:</b>", styles['BodyText']))
    for skill in market.get("top_skills", [])[:5]:
        story.append(Paragraph(f"• {skill}", styles['BulletPoint']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<b>Growing Technologies:</b>", styles['BodyText']))
    for tech in market.get("growing_technologies", [])[:5]:
        story.append(Paragraph(f"• {tech}", styles['BulletPoint']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(f"<b>Market Direction:</b> {market.get('market_direction', 'N/A')}", styles['BodyText']))
    
    story.append(PageBreak())
    
    # User's Skill Assessment
    story.append(Paragraph("3. Your Skill Assessment", styles['SectionHeading']))
    assessment = analysis.get("skill_assessment", {})
    
    story.append(Paragraph(f"<b>Market Readiness Score:</b> {assessment.get('market_readiness_score', 'N/A')}/10", styles['BodyText']))
    story.append(Spacer(1, 0.1*inch))
    
    story.append(Paragraph("<b>Your Strong Skills (aligned with market):</b>", styles['BodyText']))
    for skill in assessment.get("strong_skills", [])[:8]:
        story.append(Paragraph(f"✅ {skill}", styles['BulletPoint']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<b>Skills Needing Improvement:</b>", styles['BodyText']))
    for skill in assessment.get("needs_improvement", [])[:8]:
        story.append(Paragraph(f"⚠️ {skill}", styles['BulletPoint']))
    
    story.append(PageBreak())
    
    # Gap Analysis for Each Role
    story.append(Paragraph("4. Skill Gap Analysis by Target Role", styles['SectionHeading']))
    
    for role_analysis in analysis.get("gap_analysis", []):
        role_name = role_analysis.get("role", "Unknown Role")
        gap_pct = role_analysis.get("gap_percentage", 0)
        
        story.append(Paragraph(f"<b>{role_name}</b>", styles['BodyText']))
        story.append(Paragraph(f"Gap: {gap_pct}%", styles['BodyText']))
        
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("Skills You Have:", styles['BodyText']))
        for skill in role_analysis.get("user_has", [])[:5]:
            story.append(Paragraph(f"  ✅ {skill}", styles['BulletPoint']))
        
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("Skills Missing:", styles['BodyText']))
        for skill in role_analysis.get("user_missing", [])[:5]:
            story.append(Paragraph(f"  ❌ {skill}", styles['BulletPoint']))
        
        story.append(Spacer(1, 0.3*inch))
    
    story.append(PageBreak())
    
    # Critical Missing Skills
    story.append(Paragraph("5. Critical Skills to Acquire", styles['SectionHeading']))
    
    missing_data = [["Skill", "Importance", "Learning Difficulty"]]
    for skill in analysis.get("critical_missing_skills", [])[:10]:
        missing_data.append([
            skill.get("skill", ""),
            skill.get("importance", ""),
            skill.get("learning_difficulty", "")
        ])
    
    if len(missing_data) > 1:
        missing_table = Table(missing_data, colWidths=[180, 100, 120])
        missing_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), SECONDARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), white),
            ('GRID', (0, 0), (-1, -1), 0.5, SECONDARY_COLOR),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG])
        ]))
        story.append(missing_table)
    
    story.append(PageBreak())
    
    # Recommendations
    story.append(Paragraph("6. Personalized Recommendations", styles['SectionHeading']))
    recs = analysis.get("recommendations", {})
    
    story.append(Paragraph("<b>🚀 Immediate Actions (Next 30 Days):</b>", styles['BodyText']))
    for action in recs.get("immediate_actions", []):
        story.append(Paragraph(f"• {action}", styles['BulletPoint']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<b>📅 Short-Term Goals (1-3 Months):</b>", styles['BodyText']))
    for goal in recs.get("short_term_goals", []):
        story.append(Paragraph(f"• {goal}", styles['BulletPoint']))
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("<b>🎯 Long-Term Strategy:</b>", styles['BodyText']))
    story.append(Paragraph(recs.get("long_term_strategy", ""), styles['BodyText']))
    
    story.append(PageBreak())
    
    # Learning Resources
    story.append(Paragraph("7. Recommended Learning Resources", styles['SectionHeading']))
    
    for resource in analysis.get("learning_resources", [])[:3]:
        skill_name = resource.get("skill", "")
        story.append(Paragraph(f"<b>{skill_name}</b>", styles['BodyText']))
        
        story.append(Paragraph("Free Resources:", styles['BodyText']))
        for r in resource.get("free_resources", [])[:3]:
            story.append(Paragraph(f"  • {r}", styles['BulletPoint']))
        
        story.append(Paragraph("Paid Courses:", styles['BodyText']))
        for c in resource.get("paid_courses", [])[:2]:
            story.append(Paragraph(f"  • {c}", styles['BulletPoint']))
        
        story.append(Paragraph("Certifications:", styles['BodyText']))
        for cert in resource.get("certifications", [])[:2]:
            story.append(Paragraph(f"  • {cert}", styles['BulletPoint']))
        
        story.append(Spacer(1, 0.2*inch))
    
    # Competitiveness Scores
    story.append(PageBreak())
    story.append(Paragraph("8. Market Competitiveness Scores", styles['SectionHeading']))
    
    scores_data = [["Target Role", "Score", "Assessment"]]
    for score in analysis.get("competitiveness_scores", []):
        scores_data.append([
            score.get("role", ""),
            f"{score.get('score', 0)}/100",
            score.get("explanation", "")[:50] + "..."
        ])
    
    if len(scores_data) > 1:
        scores_table = Table(scores_data, colWidths=[120, 60, 250])
        scores_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, PRIMARY_COLOR)
        ]))
        story.append(scores_table)
    
    # Key Insights
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("9. Key Insights", styles['SectionHeading']))
    for insight in analysis.get("key_insights", []):
        story.append(Paragraph(f"💡 {insight}", styles['BulletPoint']))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "<i>This report was generated by AI-powered analysis and should be used as guidance, not absolute career advice. "
        "Market conditions change rapidly - consider refreshing this report regularly.</i>",
        ParagraphStyle(name='Footer', fontSize=8, textColor=HexColor("#666666"), alignment=TA_CENTER)
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def upload_to_s3(pdf_buffer: BytesIO, filename: str) -> str:
    """
    Upload PDF to S3 bucket and return the URL.
    """
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        bucket = settings.AWS_S3_BUCKET
        key = f"reports/{filename}"
        
        s3_client.upload_fileobj(
            pdf_buffer,
            bucket,
            key,
            ExtraArgs={'ContentType': 'application/pdf'}
        )
        
        # Generate presigned URL (valid for 7 days)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=604800  # 7 days
        )
        
        return url
        
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        # Fallback: store in Supabase Storage
        return upload_to_supabase_storage(pdf_buffer, filename)


def upload_to_supabase_storage(pdf_buffer: BytesIO, filename: str) -> str:
    """
    Fallback: Upload PDF to Supabase Storage bucket.
    """
    try:
        # Using Supabase Storage API
        url = f"{settings.SUPABASE_URL}/storage/v1/object/reports/{filename}"
        headers = {
            "apikey": settings.SUPABASE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
            "Content-Type": "application/pdf"
        }
        
        response = requests.post(url, headers=headers, data=pdf_buffer.read())
        
        if response.status_code in [200, 201]:
            return f"{settings.SUPABASE_URL}/storage/v1/object/public/reports/{filename}"
        else:
            print(f"Supabase storage error: {response.text}")
            return ""
            
    except Exception as e:
        print(f"Error uploading to Supabase Storage: {e}")
        return ""
