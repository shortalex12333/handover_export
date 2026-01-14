"""
Microsoft Graph API client for email operations
"""
import logging
from typing import Optional, Dict, Any, List
import httpx
from msal import ConfidentialClientApplication

from ..config import AzureConfig

logger = logging.getLogger(__name__)


class GraphClient:
    """
    Microsoft Graph API client using MSAL for authentication.
    Handles token acquisition and API requests.
    """

    BASE_URL = "https://graph.microsoft.com/v1.0"

    def __init__(self, config: AzureConfig):
        self.config = config
        self._token: Optional[str] = None
        self._msal_app = ConfidentialClientApplication(
            client_id=config.client_id,
            client_credential=config.client_secret,
            authority=config.authority,
        )

    async def _get_token(self) -> str:
        """Acquire access token using client credentials flow"""
        if self._token:
            return self._token

        result = self._msal_app.acquire_token_for_client(scopes=self.config.scopes)

        if "access_token" not in result:
            error = result.get("error_description", "Unknown error")
            logger.error(f"Failed to acquire token: {error}")
            raise Exception(f"Token acquisition failed: {error}")

        self._token = result["access_token"]
        return self._token

    async def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make GET request to Graph API"""
        token = await self._get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        url = f"{self.BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params, timeout=30.0)

            if response.status_code == 401:
                # Token expired, clear and retry
                self._token = None
                token = await self._get_token()
                headers["Authorization"] = f"Bearer {token}"
                response = await client.get(url, headers=headers, params=params, timeout=30.0)

            response.raise_for_status()
            return response.json()

    async def get_messages(
        self,
        query: Optional[str] = None,
        top: int = 100,
        folder_id: Optional[str] = None,
        filter_expr: Optional[str] = None,
        select: Optional[List[str]] = None,
        orderby: str = "receivedDateTime desc"
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from user's mailbox.

        Args:
            query: Search query string
            top: Maximum number of messages to return
            folder_id: Specific folder ID to search in
            filter_expr: OData filter expression
            select: Fields to select
            orderby: Sort order
        """
        endpoint = f"/me/mailFolders/{folder_id}/messages" if folder_id else "/me/messages"

        params = {
            "$top": min(top, 999),
            "$orderby": orderby,
        }

        if select:
            params["$select"] = ",".join(select)
        else:
            params["$select"] = ",".join([
                "id", "subject", "from", "receivedDateTime",
                "bodyPreview", "body", "isRead", "hasAttachments",
                "importance", "conversationId"
            ])

        if filter_expr:
            params["$filter"] = filter_expr

        if query:
            sanitized = query.replace('"', '').strip()
            params["$search"] = f'"{sanitized}"'

        result = await self.get(endpoint, params=params)
        return result.get("value", [])

    async def get_mail_folders(self) -> List[Dict[str, Any]]:
        """Get list of mail folders"""
        result = await self.get("/me/mailFolders")
        return result.get("value", [])
