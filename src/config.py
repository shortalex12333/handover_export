"""
Configuration management for Handover Export Service
Loads from environment variables matching Render deployment
"""
import os
from dataclasses import dataclass
from typing import Optional
from functools import lru_cache
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class AzureConfig:
    """Azure AD / Microsoft Graph configuration"""
    client_id: str
    client_secret: str
    tenant_id: str

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    @property
    def scopes(self) -> list[str]:
        return ["https://graph.microsoft.com/.default"]


@dataclass
class SupabaseConfig:
    """Supabase database configuration"""
    url: str
    service_key: str
    jwt_secret: str


@dataclass
class Settings:
    """Application settings loaded from environment"""

    # Environment
    environment: str
    log_level: str

    # Master Supabase (CelesteOS Central)
    master_supabase: SupabaseConfig

    # Test Tenant Supabase
    test_tenant_supabase: Optional[SupabaseConfig]

    # Azure / Microsoft Graph
    azure: Optional[AzureConfig]

    # OpenAI
    openai_api_key: str

    # Render
    render_service_id: Optional[str]

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""

        # Master Supabase
        master_supabase = SupabaseConfig(
            url=os.environ.get("MASTER_SUPABASE_URL", ""),
            service_key=os.environ.get("MASTER_SUPABASE_SERVICE_KEY", ""),
            jwt_secret=os.environ.get("MASTER_SUPABASE_JWT_SECRET", ""),
        )

        # Test Tenant (yTEST_YACHT_001)
        test_tenant_url = os.environ.get("yTEST_YACHT_001_SUPABASE_URL")
        test_tenant_supabase = None
        if test_tenant_url:
            test_tenant_supabase = SupabaseConfig(
                url=test_tenant_url,
                service_key=os.environ.get("yTEST_YACHT_001_SUPABASE_SERVICE_KEY", ""),
                jwt_secret=os.environ.get("yTEST_YACHT_001_SUPABASE_JWT_SECRET", ""),
            )

        # Azure configuration
        azure_client_id = os.environ.get("AZURE_CLIENT_ID")
        azure = None
        if azure_client_id:
            azure = AzureConfig(
                client_id=azure_client_id,
                client_secret=os.environ.get("AZURE_CLIENT_SECRET", ""),
                tenant_id=os.environ.get("AZURE_TENANT_ID", ""),
            )

        return cls(
            environment=os.environ.get("ENVIRONMENT", "development"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            master_supabase=master_supabase,
            test_tenant_supabase=test_tenant_supabase,
            azure=azure,
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            render_service_id=os.environ.get("RENDER_SERVICE_ID"),
        )

    def get_tenant_config(self, tenant_alias: str) -> Optional[SupabaseConfig]:
        """
        Get tenant Supabase config by alias.
        Looks for env vars: {tenant_alias}_SUPABASE_URL, etc.
        """
        url = os.environ.get(f"{tenant_alias}_SUPABASE_URL")
        if not url:
            return None

        return SupabaseConfig(
            url=url,
            service_key=os.environ.get(f"{tenant_alias}_SUPABASE_SERVICE_KEY", ""),
            jwt_secret=os.environ.get(f"{tenant_alias}_SUPABASE_JWT_SECRET", ""),
        )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings.from_env()
