from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import AliasChoices, Field


class Settings(BaseSettings):
    app_name: str = "Event Backend"
    debug: bool = False

    # JWT
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24  # 1 day
    ticket_qr_expires_minutes: int = Field(default=60 * 24, alias="TICKET_QR_EXPIRES_MINUTES")

    # Database
    database_url: str = Field(default="postgresql://postgres:1111@localhost:5432/eventdb", alias="DATABASE_URL")

    # Google OAuth
    #TODO: start free trial later to have free credits
    google_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_CLIENT_ID", "CLIENT_ID"),
    )
    google_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("GOOGLE_CLIENT_SECRET", "CLIENT_SECRET"),
    )
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback",
        validation_alias=AliasChoices("GOOGLE_REDIRECT_URI", "REDIRECT_URI"),
    )
    google_scope: str = (
        "openid email profile"
    )

    # Email verification / Resend
    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    resend_from_email: str = Field(default="onboarding@resend.dev", alias="RESEND_FROM_EMAIL")
    smtp_host: str = Field(default="smtp.gmail.com", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: str = Field(default="", alias="SMTP_USERNAME")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="", alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    email_verification_code_ttl_minutes: int = Field(default=10, alias="EMAIL_VERIFICATION_CODE_TTL_MINUTES")
    email_verification_secret: str = Field(default="change-email-verification-secret", alias="EMAIL_VERIFICATION_SECRET")

    # Ethereum / Hardhat
    ethereum_rpc_url: str = Field(default="http://127.0.0.1:8545", alias="ETHEREUM_RPC_URL")
    ethereum_private_key: str = Field(default="", alias="ETHEREUM_PRIVATE_KEY")
    ticket_contract_address: str = Field(default="", alias="TICKET_CONTRACT_ADDRESS")
    ticket_contract_abi_path: str = Field(default="", alias="TICKET_CONTRACT_ABI_PATH")

    # Ticket hashing
    ticket_secret_key: str = Field(default="change-ticket-secret", alias="TICKET_SECRET_KEY")

    # Cloudinary
    cloudinary_cloud_name: str = Field(default="", alias="CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key: str = Field(default="", alias="CLOUDINARY_API_KEY")
    cloudinary_api_secret: str = Field(default="", alias="CLOUDINARY_API_SECRET")

    # External parser-service endpoint used by /events/scrape
    parser_service_url: str = Field(
        default="http://localhost:8010/scrape/events",
        alias="PARSER_SERVICE_URL",
    )
    popular_cities: str = Field(
        default="Kyiv,Lviv,Odesa,Kharkiv,Dnipro",
        alias="POPULAR_CITIES",
    )
    scrape_interval_hours: int = Field(default=12, alias="SCRAPE_INTERVAL_HOURS")
    cleanup_interval_hours: int = Field(default=24, alias="CLEANUP_INTERVAL_HOURS")
    scrape_max_cities_per_run: int = Field(default=10, alias="SCRAPE_MAX_CITIES_PER_RUN")
    city_activity_retention_days: int = Field(default=14, alias="CITY_ACTIVITY_RETENTION_DAYS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

