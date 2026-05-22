import logging
from typing import Dict, Optional
from slack_sdk.web import WebClient
from config.settings import settings
from services.database import google_sheets_service

logger = logging.getLogger(__name__)

class SlackProfileService:
    """Handles business logic for retrieving and updating custom Slack profile fields,
    utilizing a Google Sheets database backend for storage parity and free-tier compatibility.
    
    Adheres strictly to PII constraints by never logging sensitive custom field content
    such as phone numbers or medical notes.
    """

    def retrieve_user_custom_profile_fields(
        self, client: WebClient, user_id: str
    ) -> Dict[str, Optional[str]]:
        """Queries the Google Sheets database first. If not found, fetches from Slack using
        the Bot Token, seeds the Google Sheets database, and returns the retrieved values.
        
        Args:
            client: An initialized Slack WebClient.
            user_id: The Slack user identifier (e.g., 'U12345678').
            
        Returns:
            A dictionary containing the values of the custom profile fields.
        """
        logger.info(
            f"Retrieving profile fields for user ID: '{user_id}'."
        )
        
        try:
            # 1. Query Google Sheets database
            record = google_sheets_service.get_user_record(user_id)
            if record is not None:
                logger.info(f"Database record found for user ID: '{user_id}'. Returning cached values.")
                return {
                    "start_date": record["start_date"] if record["start_date"] else None,
                    "primary_contact": record["primary_contact"] if record["primary_contact"] else None,
                    "backup_contact": record["backup_contact"] if record["backup_contact"] else None,
                }
            
            # 2. First-time fetch-and-seed migration from Slack profile API
            logger.info(f"No database record found for user ID: '{user_id}'. Performing initial fetch-and-seed from Slack.")
            response = client.users_profile_get(token=settings.slack_bot_token, user=user_id)
            profile = response.get("profile", {})
            fields = profile.get("fields", {})
            
            # Extract display name or real name
            display_name = profile.get("display_name") or profile.get("real_name") or user_id
            
            # Helper to extract a custom field value by its ID safely
            def _extract_field_value(field_id: str) -> Optional[str]:
                field_data = fields.get(field_id)
                if isinstance(field_data, dict):
                    return field_data.get("value")
                return None

            start_date_value = _extract_field_value(settings.start_date_profile_field_id)
            primary_contact_value = _extract_field_value(
                settings.primary_emergency_contact_profile_field_id
            )
            backup_contact_value = _extract_field_value(
                settings.backup_emergency_contact_profile_field_id
            )
            
            # 3. Seed into Google Sheets database
            google_sheets_service.upsert_user_record(
                user_id=user_id,
                display_name=display_name,
                start_date=start_date_value if start_date_value else "",
                primary_contact=primary_contact_value if primary_contact_value else "",
                backup_contact=backup_contact_value if backup_contact_value else ""
            )
            
            return {
                "start_date": start_date_value,
                "primary_contact": primary_contact_value,
                "backup_contact": backup_contact_value,
            }
            
        except Exception as error:
            logger.exception(
                f"Failed to retrieve custom profile fields for user '{user_id}': {error}"
            )
            raise error

    def update_user_custom_profile_fields(
        self,
        client: WebClient,
        user_id: str,
        start_date: Optional[str],
        primary_contact: Optional[str],
        backup_contact: Optional[str],
    ) -> None:
        """Updates the user's custom profile fields in the Google Sheets backend.
        
        Args:
            client: An initialized Slack WebClient.
            user_id: The Slack user identifier (e.g., 'U12345678').
            start_date: The date string to set (e.g., 'YYYY-MM-DD').
            primary_contact: The primary emergency contact text.
            backup_contact: The backup emergency contact text.
        """
        # Strictly audit logging to never output raw PII variables to system output
        logger.info(
            f"Initiating profile fields update in database for user ID: '{user_id}'."
        )

        try:
            # Retrieve current display name/real name from Slack using Bot Token
            response = client.users_profile_get(token=settings.slack_bot_token, user=user_id)
            profile = response.get("profile", {})
            display_name = profile.get("display_name") or profile.get("real_name") or user_id

            # Save the new values directly to Google Sheets database
            google_sheets_service.upsert_user_record(
                user_id=user_id,
                display_name=display_name,
                start_date=start_date if start_date else "",
                primary_contact=primary_contact if primary_contact else "",
                backup_contact=backup_contact if backup_contact else ""
            )
            
            logger.info(
                f"Successfully updated profile fields in database for user ID: '{user_id}'."
            )
            
        except Exception as error:
            logger.exception(
                f"Failed to update profile fields in database for user '{user_id}': {error}"
            )
            raise error

# Singleton instance of the profile service
slack_profile_service: SlackProfileService = SlackProfileService()
