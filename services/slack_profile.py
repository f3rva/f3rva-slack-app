import logging
from typing import Dict, Optional
from slack_sdk.web import WebClient
from config.settings import settings

logger = logging.getLogger(__name__)

class SlackProfileService:
    """Handles business logic for retrieving and updating custom Slack profile fields.
    
    Adheres strictly to PII constraints by never logging sensitive custom field content
    such as phone numbers or medical notes.
    """

    def retrieve_user_custom_profile_fields(
        self, client: WebClient, user_id: str
    ) -> Dict[str, Optional[str]]:
        """Queries a user's Slack profile and extracts the values of specific custom fields.
        
        Args:
            client: An initialized Slack WebClient.
            user_id: The Slack user identifier (e.g., 'U12345678').
            
        Returns:
            A dictionary containing the values of the custom profile fields.
        """
        logger.info(
            f"Retrieving custom profile fields for user ID: '{user_id}'."
        )
        
        try:
            response = client.users_profile_get(user=user_id)
            profile = response.get("profile", {})
            fields = profile.get("fields", {})
            
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
            
            return {
                "start_date": start_date_value,
                "primary_contact": primary_contact_value,
                "backup_contact": backup_contact_value,
            }
            
        except Exception as error:
            logger.error(
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
        """Updates specific custom profile fields in a user's Slack profile.
        
        Args:
            client: An initialized Slack WebClient.
            user_id: The Slack user identifier (e.g., 'U12345678').
            start_date: The date string to set (e.g., 'YYYY-MM-DD').
            primary_contact: The primary emergency contact text.
            backup_contact: The backup emergency contact text.
        """
        # Strictly audit logging to never output raw PII variables to system output
        logger.info(
            f"Initiating custom profile fields update for user ID: '{user_id}'."
        )

        try:
            # Build the custom fields object using specific field IDs
            custom_fields_payload = {
                settings.start_date_profile_field_id: {
                    "value": start_date if start_date else "",
                    "alt": "",
                },
                settings.primary_emergency_contact_profile_field_id: {
                    "value": primary_contact if primary_contact else "",
                    "alt": "",
                },
                settings.backup_emergency_contact_profile_field_id: {
                    "value": backup_contact if backup_contact else "",
                    "alt": "",
                },
            }

            # Update the user profile
            client.users_profile_set(
                user=user_id,
                profile={"fields": custom_fields_payload}
            )
            logger.info(
                f"Successfully updated custom profile fields for user ID: '{user_id}'."
            )
            
        except Exception as error:
            logger.error(
                f"Failed to update custom profile fields for user '{user_id}': {error}"
            )
            raise error

# Singleton instance of the profile service
slack_profile_service: SlackProfileService = SlackProfileService()
