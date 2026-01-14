"""
Stage 1: Fetch emails from Microsoft Graph API
"""
from typing import List, Optional
from datetime import datetime, timedelta

from ...graph.client import GraphClient
from ..types import RawEmail


class FetchEmailsStage:
    """
    Stage 1: Fetch emails from Microsoft Graph API

    n8n equivalent: Webhook trigger + Graph API call
    """

    def __init__(self, graph_client: GraphClient):
        self.graph = graph_client

    async def execute(
        self,
        query: Optional[str] = None,
        days_back: int = 90,
        max_emails: int = 500,
        folder_id: Optional[str] = None
    ) -> List[RawEmail]:
        """Fetch emails matching criteria"""

        # Build filter for date range
        filter_expr = None
        if days_back > 0:
            cutoff = (datetime.now() - timedelta(days=days_back)).isoformat() + 'Z'
            filter_expr = f"receivedDateTime ge {cutoff}"

        # Fetch from Graph API
        messages = await self.graph.get_messages(
            query=query,
            top=max_emails,
            folder_id=folder_id,
            filter_expr=filter_expr,
        )

        # Convert to RawEmail objects
        return [
            RawEmail(
                id=msg['id'],
                subject=msg.get('subject', '(no subject)'),
                body=msg.get('body', {}),
                body_preview=msg.get('bodyPreview', ''),
                from_address=msg.get('from', {}),
                received_datetime=msg.get('receivedDateTime', ''),
                conversation_id=msg.get('conversationId', ''),
                has_attachments=msg.get('hasAttachments', False),
                importance=msg.get('importance', 'normal')
            )
            for msg in messages
        ]
