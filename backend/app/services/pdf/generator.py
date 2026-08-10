"""PDF report generation using ReportLab."""

import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.config import Settings
from app.schemas.hcp import HCPProfile
from app.services.normalizer import ProfileNormalizer

logger = logging.getLogger(__name__)


class PDFReportGenerator:
    def __init__(self, settings: Settings):
        self.output_dir = settings.pdf_output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, profile: HCPProfile) -> str:
        filename = f"hcp_report_{profile.npi}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = self.output_dir / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=letter, topMargin=0.75 * inch)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=18, spaceAfter=12)
        heading = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=14, spaceAfter=8)
        body = styles["BodyText"]

        story: list = []
        name = ProfileNormalizer.provider_display_name(profile.identity)

        story.append(Paragraph("HCP Intelligence Report", title_style))
        story.append(Paragraph(f"{name} | NPI: {profile.npi}", heading))
        story.append(
            Paragraph(
                f"Generated: {profile.generated_at.strftime('%Y-%m-%d %H:%M UTC')}",
                body,
            )
        )
        story.append(Spacer(1, 0.2 * inch))

        identity_data = [
            ["Field", "Value"],
            ["Specialty", profile.identity.primary_specialty or "N/A"],
            ["Credential", profile.identity.credential or "N/A"],
            [
                "Location",
                f"{profile.identity.address.city}, {profile.identity.address.state}",
            ],
            ["Phone", profile.identity.phone or "N/A"],
            ["NPI Status", profile.identity.status or "N/A"],
        ]
        story.append(Paragraph("Provider Identity", heading))
        story.append(self._make_table(identity_data))
        story.append(Spacer(1, 0.15 * inch))

        metrics_data = [
            ["Metric", "Value"],
            ["Publications", str(len(profile.publications))],
            ["Clinical Trials", str(len(profile.clinical_trials))],
            ["Unique Collaborators", str(profile.features.unique_collaborator_count)],
            ["Years Active", str(profile.features.years_active)],
        ]
        story.append(Paragraph("Activity Metrics", heading))
        story.append(self._make_table(metrics_data))
        story.append(Spacer(1, 0.15 * inch))

        if profile.collaboration_network:
            network = profile.collaboration_network
            story.append(Paragraph("Research Collaboration Network", heading))
            network_data = [
                ["Metric", "Value"],
                ["Total Collaborators", str(network.metrics.total_collaborators)],
                ["Strongest Collaborator", network.metrics.strongest_collaborator or "N/A"],
                ["Strongest Collaboration", str(network.metrics.max_shared_publications)],
            ]
            story.append(self._make_table(network_data))
            top_rows = [["Top Collaborator", "Shared Publications"]]
            for node in network.nodes[1:6]:
                top_rows.append([node.label, str(node.shared_publications)])
            if len(top_rows) > 1:
                story.append(Spacer(1, 0.1 * inch))
                story.append(Paragraph("Top Collaborators", heading))
                story.append(self._make_table(top_rows))
            story.append(Spacer(1, 0.15 * inch))

        if profile.ml_predictions:
            ml_data = [["Model", "Score", "KOL Tier"]]
            for p in profile.ml_predictions:
                ml_data.append([p.model_name, f"{p.influence_score}/100", p.kol_tier])
            story.append(Paragraph("Influence Prediction", heading))
            story.append(self._make_table(ml_data))
            story.append(Spacer(1, 0.15 * inch))

        if profile.ai_summary:
            story.append(Paragraph("AI Intelligence Summary", heading))
            for para in profile.ai_summary.split("\n"):
                if para.strip():
                    story.append(Paragraph(para.strip(), body))
                    story.append(Spacer(1, 0.05 * inch))

        if profile.judge_evaluation:
            ev = profile.judge_evaluation
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("Quality Evaluation", heading))
            story.append(
                Paragraph(
                    f"Overall: {ev.overall_score}/10 | Groundedness: {ev.groundedness}/10 | "
                    f"Passed: {'Yes' if ev.passed else 'No'}",
                    body,
                )
            )

        doc.build(story)
        logger.info("PDF generated: %s", filepath)
        return str(filepath)

    @staticmethod
    def _make_table(data: list[list[str]]) -> Table:
        table = Table(data, colWidths=[2.5 * inch, 4 * inch])
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565C0")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        return table
