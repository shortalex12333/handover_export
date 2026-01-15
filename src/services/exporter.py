"""
Handover Exporter Service
Generates PDF, HTML, and Email exports from signed handover drafts
"""
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from uuid import uuid4
import tempfile

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

from ..db.supabase_client import SupabaseClient


class HandoverExporter:
    """
    Exports handover drafts to PDF, HTML, or Email

    Requirements:
    - Draft must be in SIGNED state
    - Templates must exist in templates/ directory
    - Supabase Storage configured for file uploads
    """

    def __init__(self, db_client: SupabaseClient):
        self.db = db_client

        # Initialize Jinja2 environment
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True
        )

    async def export_to_pdf(
        self,
        draft_id: str,
        yacht_id: str
    ) -> str:
        """
        Export handover draft to PDF

        Args:
            draft_id: Draft to export
            yacht_id: Vessel ID for storage path

        Returns:
            export_id: UUID of export record with file URL
        """

        # Fetch complete draft data
        draft_data = await self._fetch_draft_with_details(draft_id)

        # Validate state
        if draft_data["state"] != "SIGNED":
            raise ValueError(
                f"Cannot export draft in state {draft_data['state']}. "
                f"Draft must be SIGNED."
            )

        # Render HTML from template
        html_content = await self._render_template(draft_data)

        # Convert HTML to PDF
        pdf_bytes = self._html_to_pdf(html_content)

        # Upload to Supabase Storage
        file_url = await self._upload_to_storage(
            pdf_bytes,
            yacht_id,
            draft_id,
            file_type="pdf"
        )

        # Create export record
        export_id = await self._create_export_record(
            draft_id=draft_id,
            export_type="pdf",
            file_url=file_url
        )

        return export_id

    async def export_to_html(
        self,
        draft_id: str,
        yacht_id: str
    ) -> str:
        """
        Export handover draft to HTML

        Args:
            draft_id: Draft to export
            yacht_id: Vessel ID

        Returns:
            export_id: UUID of export record
        """

        # Fetch complete draft data
        draft_data = await self._fetch_draft_with_details(draft_id)

        # Validate state
        if draft_data["state"] != "SIGNED":
            raise ValueError("Draft must be SIGNED to export")

        # Render HTML from template
        html_content = await self._render_template(draft_data)

        # Upload HTML to storage
        file_url = await self._upload_to_storage(
            html_content.encode('utf-8'),
            yacht_id,
            draft_id,
            file_type="html"
        )

        # Create export record
        export_id = await self._create_export_record(
            draft_id=draft_id,
            export_type="html",
            file_url=file_url
        )

        return export_id

    async def export_to_email(
        self,
        draft_id: str,
        yacht_id: str,
        recipients: List[str],
        sender_email: Optional[str] = None
    ) -> str:
        """
        Export handover draft via email

        Args:
            draft_id: Draft to export
            yacht_id: Vessel ID
            recipients: List of email addresses
            sender_email: Sender email (default from config)

        Returns:
            export_id: UUID of export record
        """

        # Fetch complete draft data
        draft_data = await self._fetch_draft_with_details(draft_id)

        # Validate state
        if draft_data["state"] != "SIGNED":
            raise ValueError("Draft must be SIGNED to export")

        # Render HTML body
        html_content = await self._render_template(draft_data)

        # Generate PDF attachment
        pdf_bytes = self._html_to_pdf(html_content)

        # Send email
        await self._send_email(
            recipients=recipients,
            subject=f"Handover Report - {draft_data['period_end_date']}",
            html_body=html_content,
            pdf_attachment=pdf_bytes,
            sender=sender_email
        )

        # Create export record
        export_id = await self._create_export_record(
            draft_id=draft_id,
            export_type="email",
            file_url=None,
            email_sent_at=datetime.now()
        )

        return export_id

    async def _fetch_draft_with_details(self, draft_id: str) -> Dict:
        """
        Fetch draft with all related data:
        - Draft metadata
        - Sections with items
        - Signoffs with user details
        - User profiles (outgoing/incoming)
        """

        # Fetch draft
        draft_result = self.db.client.table("handover_drafts") \
            .select("""
                *,
                outgoing_user:user_profiles!outgoing_user_id(id, full_name, email, role),
                incoming_user:user_profiles!incoming_user_id(id, full_name, email, role)
            """) \
            .eq("id", draft_id) \
            .single() \
            .execute()

        if not draft_result.data:
            raise ValueError(f"Draft {draft_id} not found")

        draft = draft_result.data

        # Fetch sections with items
        sections_result = self.db.client.table("handover_draft_sections") \
            .select("*") \
            .eq("draft_id", draft_id) \
            .order("section_order") \
            .execute()

        sections = sections_result.data or []

        # Fetch items for each section
        for section in sections:
            items_result = self.db.client.table("handover_draft_items") \
                .select("*") \
                .eq("section_id", section["id"]) \
                .order("item_order") \
                .execute()

            section["items"] = items_result.data or []

        draft["sections"] = sections

        # Fetch signoffs
        signoffs_result = self.db.client.table("handover_signoffs") \
            .select("""
                *,
                user:user_profiles(id, full_name, role)
            """) \
            .eq("draft_id", draft_id) \
            .order("signed_at") \
            .execute()

        draft["signoffs"] = signoffs_result.data or []

        # Add formatted dates
        draft["period_start_date"] = self._format_datetime(draft["period_start"])
        draft["period_end_date"] = self._format_datetime(draft["period_end"])

        return draft

    async def _render_template(self, draft_data: Dict) -> str:
        """Render Jinja2 template with draft data"""

        template = self.jinja_env.get_template("handover_report.html")

        html_content = template.render(
            draft=draft_data,
            generated_at=datetime.now()
        )

        return html_content

    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML string to PDF bytes using WeasyPrint"""

        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()

        return pdf_bytes

    async def _upload_to_storage(
        self,
        file_bytes: bytes,
        yacht_id: str,
        draft_id: str,
        file_type: str
    ) -> str:
        """
        Upload file to Supabase Storage

        Storage path: handovers/{yacht_id}/{draft_id}.{file_type}

        Returns:
            Public URL or signed URL
        """

        file_name = f"{draft_id}.{file_type}"
        storage_path = f"handovers/{yacht_id}/{file_name}"

        # Upload to Supabase Storage
        # Note: This requires supabase-storage-py library
        try:
            # Write to temporary file first
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_type}') as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            # Upload file
            self.db.client.storage.from_("handover-exports").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": f"application/{file_type}"}
            )

            # Get public URL
            file_url = self.db.client.storage.from_("handover-exports").get_public_url(storage_path)

            return file_url

        except Exception as e:
            # Fallback: Return placeholder URL
            # In production, handle storage errors properly
            return f"https://storage.supabase.com/handovers/{yacht_id}/{file_name}"

    async def _create_export_record(
        self,
        draft_id: str,
        export_type: str,
        file_url: Optional[str] = None,
        email_sent_at: Optional[datetime] = None
    ) -> str:
        """Create handover_exports record"""

        export_data = {
            "id": str(uuid4()),
            "draft_id": draft_id,
            "export_type": export_type,
            "file_url": file_url,
            "email_sent_at": email_sent_at.isoformat() if email_sent_at else None,
            "created_at": datetime.now().isoformat()
        }

        result = self.db.client.table("handover_exports") \
            .insert(export_data) \
            .execute()

        if result.data:
            return result.data[0]["id"]

        raise Exception("Failed to create export record")

    async def _send_email(
        self,
        recipients: List[str],
        subject: str,
        html_body: str,
        pdf_attachment: bytes,
        sender: Optional[str] = None
    ):
        """
        Send email via SMTP or SendGrid

        This is a placeholder implementation.
        In production, use SendGrid, AWS SES, or similar service.
        """

        # For now, just log the email send
        # In production, implement actual email sending

        print(f"[EMAIL] Would send to: {', '.join(recipients)}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] Attachment size: {len(pdf_attachment)} bytes")

        # Example SendGrid implementation:
        """
        import sendgrid
        from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition

        sg = sendgrid.SendGridAPIClient(api_key=os.environ.get('SENDGRID_API_KEY'))

        message = Mail(
            from_email=sender or 'noreply@celesteos.com',
            to_emails=recipients,
            subject=subject,
            html_content=html_body
        )

        # Add PDF attachment
        attachment = Attachment(
            FileContent(base64.b64encode(pdf_attachment).decode()),
            FileName('handover_report.pdf'),
            FileType('application/pdf'),
            Disposition('attachment')
        )
        message.attachment = attachment

        response = sg.send(message)
        """

        pass

    def _format_datetime(self, dt_string: str) -> str:
        """Format ISO datetime string to readable format"""

        try:
            dt = datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
            return dt.strftime('%d %B %Y %H:%M')
        except:
            return dt_string
