"""Generate onboarding brief PDF for Campfire ERP (template)."""
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.colors import HexColor


def generate_onboarding_pdf():
    """Generate a 5-page onboarding brief for Campfire (ERP context)."""
    os.makedirs("static", exist_ok=True)
    doc = SimpleDocTemplate(
        "static/onboarding_brief.pdf",
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=HexColor("#5B21B6"),
        spaceAfter=30,
    )
    story = []

    # Page 1
    story.append(Paragraph("Welcome to Campfire", title_style))
    story.append(Paragraph("ERP Onboarding Brief", styles["Heading2"]))
    story.append(Spacer(1, 0.5 * inch))
    story.append(
        Paragraph(
            "This brief gives new hires context on Campfire's product, market, and team. "
            "For live Q&A, use the Campfire ERP Onboarding Assistant in the app.",
            styles["BodyText"],
        )
    )
    story.append(PageBreak())

    # Page 2
    story.append(Paragraph("Company Overview", title_style))
    story.append(
        Paragraph(
            "<b>Campfire.ai:</b> AI-native ERP platform for finance &amp; accounting teams.<br/>"
            "<b>Mission:</b> Replace legacy ERP with an intuitive, AI-first system for venture-funded startups.<br/>"
            "<b>Key differentiators:</b> Automation, multi-entity management, Ember AI (Claude-powered).<br/>"
            "<b>Customers:</b> Replit, PostHog, Decagon, Heidi Health, CloudZero, 100+ companies.<br/>"
            "<b>Funding:</b> $100M+ (Series B led by Accel &amp; Ribbit).<br/>",
            styles["BodyText"],
        )
    )
    story.append(PageBreak())

    # Page 3
    story.append(Paragraph("Product & ERP Context", title_style))
    story.append(
        Paragraph(
            "<b>What we do:</b> Finance and accounting ERP — general ledger, revenue automation, "
            "multi-entity, high-velocity operations.<br/><br/>"
            "<b>Traditional ERP landscape:</b> NetSuite, SAP, Oracle, QuickBooks — we compete by being "
            "AI-native, faster to implement, and built for modern startups.<br/><br/>"
            "<b>Ember AI:</b> Conversational interface powered by Anthropic's Claude for natural-language "
            "finance workflows.<br/>",
            styles["BodyText"],
        )
    )
    story.append(PageBreak())

    # Page 4
    story.append(Paragraph("Market & Competition", title_style))
    story.append(
        Paragraph(
            "<b>Competitors:</b> NetSuite, SAP, Oracle, QuickBooks (legacy and SMB).<br/><br/>"
            "<b>Our positioning:</b> Built for venture-funded startups; AI-first design; automation and "
            "multi-entity out of the box; faster onboarding than legacy ERP.<br/><br/>"
            "Use the in-app Competitive Intelligence section (You.com) for up-to-date intel on these players.",
            styles["BodyText"],
        )
    )
    story.append(PageBreak())

    # Page 5
    story.append(Paragraph("Getting Started", title_style))
    story.append(
        Paragraph(
            "<b>Your first steps:</b> Use the Campfire ERP Onboarding Assistant to ask questions at your level — "
            "from \"What is ERP?\" to \"How do we compare to NetSuite?\" Answers are tailored to your knowledge level.<br/><br/>"
            "<i>Campfire ERP Onboarding — Powered by You.com and Render</i>",
            styles["BodyText"],
        )
    )
    doc.build(story)
    print("✅ PDF onboarding brief generated at static/onboarding_brief.pdf")


if __name__ == "__main__":
    generate_onboarding_pdf()
