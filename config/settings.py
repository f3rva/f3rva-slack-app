import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from a local .env file if it exists
load_dotenv()

class AppSettings:
    """Manages application-wide settings and validates critical Slack & Google Sheets configurations on startup."""

    def __init__(self) -> None:
        # Slack Credentials
        self.slack_bot_token: str = self._get_required_env_variable("SLACK_BOT_TOKEN")
        self.slack_signing_secret: str = self._get_required_env_variable("SLACK_SIGNING_SECRET")
        
        # User Access Token is now optional/deprecated but we retain it for legacy reference
        user_token: Optional[str] = os.getenv("SLACK_USER_TOKEN")
        self.slack_user_token: Optional[str] = user_token.strip() if user_token else None

        # Unique Custom Profile Field IDs created in the Slack Workspace Admin Console
        # Retained for Fetch-and-Seed lookup from Slack
        self.start_date_profile_field_id: str = self._get_required_env_variable(
            "START_DATE_FIELD_ID"
        )
        self.primary_emergency_contact_profile_field_id: str = self._get_required_env_variable(
            "EMERGENCY_CONTACT_PRIMARY_FIELD_ID"
        )
        self.backup_emergency_contact_profile_field_id: str = self._get_required_env_variable(
            "EMERGENCY_CONTACT_BACKUP_FIELD_ID"
        )
        
        # Google Sheets Backend Configuration
        self.google_sheets_spreadsheet_key: str = self._get_required_env_variable(
            "GOOGLE_SHEETS_SPREADSHEET_KEY"
        )
        
        # Google service account JSON string or credentials file path are now optional.
        # If omitted, the application will fallback to standard Google Application Default Credentials (ADC),
        # which is perfect for Workload Identity Federation (WIF) in production and local 'gcloud' logins.
        self.google_service_account_json: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        self.google_service_account_file: Optional[str] = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        self.google_impersonate_service_account: Optional[str] = os.getenv("GOOGLE_IMPERSONATE_SERVICE_ACCOUNT")


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
