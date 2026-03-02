from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "LeadPilot"
    API_V1_STR: str = "/api/v1"
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    ENCRYPTION_KEY_FERNET: str
    
    # OAuth
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = None
    GOOGLE_OAUTH_ALLOWED_DOMAINS: List[str] = []
    
    # AI
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.1-pro-preview"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_OUTPUT_TOKENS: int = 2048
    
    # Integrations
    META_CLIENT_ID: Optional[str] = None
    META_CLIENT_SECRET: Optional[str] = None
    META_APP_SECRET: Optional[str] = None
    META_OAUTH_REDIRECT_URI: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    ZOHO_CLIENT_ID: Optional[str] = None
    ZOHO_CLIENT_SECRET: Optional[str] = None
    
    # Email
    EMAIL_PROVIDER: str = "console" # console, smtp, sendgrid
    
    # SendGrid
    SENDGRID_API_KEY: Optional[str] = None
    SENDGRID_FROM_EMAIL: Optional[str] = None
    SENDGRID_FROM_NAME: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 465
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_SSL: bool = True
    SMTP_USE_TLS: bool = False
    EMAIL_FROM: str = "no-reply@leadpilot.ai"
    EMAIL_FROM_NAME: str = "LeadPilot"
    EMAIL_MAX_RETRIES: int = 3
    EMAIL_RETRY_BASE_DELAY: int = 2
    APP_BASE_URL: Optional[str] = None # For constructing links
    EMAIL_VERIFICATION_GRACE_DAYS: int = 7

    # Runtime Event Trail
    RUNTIME_EVENT_RETENTION_DAYS: int = 30

    # Webhook Hardening
    WEBHOOK_MAX_PAYLOAD_BYTES: int = 1_048_576  # 1 MB

    # HuggingFace Dataset Export
    HF_TOKEN: Optional[str] = None
    HF_DATASET_REPO: str = "ashrafkassem/leadpilot-data"

    @model_validator(mode="after")
    def validate_email_settings(self) -> "Settings":
        import logging
        logger = logging.getLogger(__name__)
        
        if self.EMAIL_PROVIDER == "smtp":
            if not self.SMTP_HOST or not self.SMTP_USERNAME or not self.SMTP_PASSWORD:
                logger.warning("SMTP_HOST, SMTP_USERNAME, and SMTP_PASSWORD are not fully set. Email functionality will be unstable.")
        elif self.EMAIL_PROVIDER == "sendgrid":
            if not self.SENDGRID_API_KEY or not self.SENDGRID_FROM_EMAIL:
                logger.warning("SENDGRID_API_KEY and SENDGRID_FROM_EMAIL are requires for SendGrid provider.")
                
        return self

    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[AnyHttpUrl], str]:
        if isinstance(v, str) and not v.startswith("[") and v:
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        return [] # Default to empty list instead of raising if empty string

    model_config = SettingsConfigDict(
        case_sensitive=True, env_file=".env", extra="ignore"
    )

settings = Settings()
