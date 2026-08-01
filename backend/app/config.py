from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # MongoDB connection string, for example: mongodb://localhost:27017
    mongo_uri: str

    # Name of the MongoDB database used by DhakaNest.
    database_name: str

    # Secret key used to sign JWT access tokens. Keep the real value in .env.
    jwt_secret_key: str

    # JWT signing algorithm. HS256 is a common default for this project.
    jwt_algorithm: str = "HS256"

    # How long a login token stays valid, in minutes.
    access_token_expire_minutes: int = 1440

    # Cloudinary account credentials used for property image storage.
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # Validation limits for images attached to one rental listing.
    listing_image_max_count: int = 8
    listing_image_max_size_mb: int = 5

    # This tells pydantic-settings to also read values from a .env file.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Import this single settings object wherever configuration is needed.
settings = Settings()
