from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field


class Settings(BaseSettings):
    app_name: str = "Event Backend"
    debug: bool = False

    # JWT
    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 60 * 24  # 1 day

    # Database
    database_url: str = Field(default="postgresql://postgres:1111@localhost:5432/eventdb", alias="DATABASE_URL")

    # Google OAuth
    #TODO: start free trial later to have free credits
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(default="http://localhost:8000/auth/google/callback", alias="GOOGLE_REDIRECT_URI")
    google_scope: str = (
        "openid email profile"
    )

    # Ethereum / Hardhat
    ethereum_rpc_url: str = Field(default="http://127.0.0.1:8545", alias="ETHEREUM_RPC_URL")
    ethereum_private_key: str = Field(default="", alias="ETHEREUM_PRIVATE_KEY")
    ticket_contract_address: str = Field(default="", alias="TICKET_CONTRACT_ADDRESS")
    ticket_contract_abi_path: str = Field(default="", alias="TICKET_CONTRACT_ABI_PATH")

    # Ticket hashing
    ticket_secret_key: str = Field(default="change-ticket-secret", alias="TICKET_SECRET_KEY")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

