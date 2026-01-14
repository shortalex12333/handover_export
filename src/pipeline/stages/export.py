"""
Stage 8: Export report to various formats
"""
from typing import Optional, List

from ..types import FormattedReport


class ExportStage:
    """
    Stage 8: Export report to various formats

    n8n equivalent: "HTML Converter" + "Prepare for Email" + "Convert to Attachment" + "Send a message"
    """

    def __init__(
        self,
        pdf_generator=None,
        email_sender=None
    ):
        self.pdf = pdf_generator
        self.email = email_sender

    async def export_html(self, report: FormattedReport) -> str:
        """Export as HTML string"""
        return report.html

    async def export_pdf(self, report: FormattedReport, output_path: str) -> str:
        """Export as PDF file"""
        if not self.pdf:
            # Use weasyprint if available
            try:
                from weasyprint import HTML
                html_doc = HTML(string=report.html)
                html_doc.write_pdf(output_path)
                return output_path
            except ImportError:
                raise ValueError("PDF generation requires weasyprint")

        return await self.pdf.generate(report.html, output_path)

    async def send_email(
        self,
        report: FormattedReport,
        recipients: List[str],
        subject: Optional[str] = None
    ) -> dict:
        """Send report via email"""
        if not self.email:
            raise ValueError("Email sender not configured")

        # Generate subject if not provided
        if not subject:
            date_str = report.generated_at.strftime('%Y-%m-%d')
            sections = report.meta.get('sectionsProcessed', 0)
            emails = report.meta.get('totalEmails', 0)
            subject = f"Yacht Handover Report - {date_str} | {sections} Active Sections | {emails} Emails"

        date_str = report.generated_at.strftime('%Y-%m-%d')

        # Prepare email body
        email_body = f"""
Please find attached the Yacht Handover Report for {date_str}.

This report contains:
- Technical summaries
- Key action items
- Direct email links
- Vendor details and deadlines

Sections with updates: {', '.join(report.sections.keys())}
"""

        return await self.email.send(
            recipients=recipients,
            subject=subject,
            body=email_body,
            html_attachment=report.html,
            attachment_name=f"Yacht_Handover_Report_{date_str}.html"
        )

    def get_json_output(self, report: FormattedReport) -> dict:
        """Export as JSON-serializable dict"""
        return {
            'meta': report.meta,
            'sections': {
                cat: [
                    {
                        'subject': h.subject,
                        'summary': h.summary,
                        'category': h.category.value,
                        'domain_code': h.domain_code,
                        'presentation_bucket': h.presentation_bucket,
                        'actions': [
                            {
                                'priority': a.priority.value,
                                'task': a.task,
                                'sub_tasks': a.sub_tasks
                            }
                            for a in h.actions
                        ],
                        'source_ids': h.source_ids
                    }
                    for h in handovers
                ]
                for cat, handovers in report.sections.items()
            },
            'generated_at': report.generated_at.isoformat()
        }
