"""
Stage 2: Extract and normalize email content
"""
import re
from typing import List
from urllib.parse import quote
from datetime import datetime
from dateutil import parser

from ..types import RawEmail, ExtractedEmail


class ExtractContentStage:
    """
    Stage 2: Extract and normalize email content

    n8n equivalent: "Extract Subject & Body" + "Add Short Id"
    """

    def __init__(self):
        self.html_pattern = re.compile(r'<[^>]+>')
        self.whitespace_pattern = re.compile(r'\s+')

    def execute(self, emails: List[RawEmail], start_index: int = 1) -> List[ExtractedEmail]:
        """Extract structured data from raw emails"""

        extracted = []

        for idx, email in enumerate(emails, start=start_index):
            short_id = f"E{idx}"

            # Generate Outlook deeplink
            encoded_id = quote(email.id, safe='')
            outlook_link = (
                f"https://outlook.office365.com/mail/deeplink/read/{encoded_id}"
                f"?ItemID={encoded_id}&exvsurl=1"
            )

            # Extract body text
            body_content = email.body.get('content', email.body_preview)
            if email.body.get('contentType') == 'html':
                body_content = self._strip_html(body_content)

            # Parse sender
            from_addr = email.from_address.get('emailAddress', {})
            sender_name = from_addr.get('name', '')
            sender_email = from_addr.get('address', '')

            # Parse datetime
            try:
                received_at = parser.parse(email.received_datetime)
            except Exception:
                received_at = datetime.now()

            extracted.append(ExtractedEmail(
                short_id=short_id,
                email_id=email.id,
                conversation_id=email.conversation_id,
                subject=email.subject,
                body_text=body_content,
                body_preview=email.body_preview,
                sender_name=sender_name,
                sender_email=sender_email,
                received_at=received_at,
                has_attachments=email.has_attachments,
                outlook_link=outlook_link
            ))

        return extracted

    def _strip_html(self, html: str) -> str:
        """Remove HTML tags and normalize whitespace"""
        text = self.html_pattern.sub('', html)
        text = self.whitespace_pattern.sub(' ', text)
        return text.strip()
