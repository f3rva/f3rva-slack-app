import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from a local .env file if it exists
load_dotenv()

class AppSettings:
    """Manages application-wide settings for the F3 RVA Slack Pester Bot."""

    def __init__(self) -> None:
        # Slack Credentials (Required)
        self.slack_bot_token: str = self._get_required_env_variable("SLACK_BOT_TOKEN")
        
        # Optional Custom Profile Field IDs (for paid workspaces supporting custom fields)
        # If undefined, the bot will scan standard "What I do" (Title) profiles instead.
        self.primary_emergency_contact_profile_field_id: Optional[str] = os.getenv("EMERGENCY_CONTACT_PRIMARY_FIELD_ID")
        self.backup_emergency_contact_profile_field_id: Optional[str] = os.getenv("EMERGENCY_CONTACT_BACKUP_FIELD_ID")
        
        # Email Notification Configuration (Required for SES email alerts)
        # Defaults to 'admin@f3rva.org' if not specified
        self.email_sender_source: str = os.getenv("EMAIL_SENDER_SOURCE", "admin@f3rva.org").strip()
        
        self.app_environment: str = os.getenv("APP_ENV", "development")

    def _get_required_env_variable(self, variable_name: str) -> str:
        """Retrieves an environment variable or raises a descriptive error if missing."""
        value: Optional[str] = os.getenv(variable_name)
        if not value:
            raise ValueError(
                f"Missing critical configuration environment variable: '{variable_name}'. "
                f"Please ensure it is defined in your environment or your local '.env' file."
            )
        return value.strip()

# Singleton instance of application configuration
settings: AppSettings = AppSettings()
