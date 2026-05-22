import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from a local .env file if it exists
load_dotenv()

class AppSettings:
    """Manages application-wide settings and validates critical Slack configurations on startup."""

    def __init__(self) -> None:
        self.slack_bot_token: str = self._get_required_env_variable("SLACK_BOT_TOKEN")
        self.slack_app_token: str = self._get_required_env_variable("SLACK_APP_TOKEN")
        
        # Unique Custom Profile Field IDs created in the Slack Workspace Admin Console
        self.start_date_profile_field_id: str = self._get_required_env_variable(
            "START_DATE_FIELD_ID"
        )
        self.primary_emergency_contact_profile_field_id: str = self._get_required_env_variable(
            "EMERGENCY_CONTACT_PRIMARY_FIELD_ID"
        )
        self.backup_emergency_contact_profile_field_id: str = self._get_required_env_variable(
            "EMERGENCY_CONTACT_BACKUP_FIELD_ID"
        )
        
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
