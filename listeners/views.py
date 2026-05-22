import logging
from typing import Dict, Any, Optional
from slack_bolt import Ack
from slack_sdk.web import WebClient
from services.slack_profile import slack_profile_service

logger = logging.getLogger(__name__)

def acknowledge_profile_modal_submission(ack: Ack) -> None:
    """Acknowledge the modal submission instantly within the 3-second window."""
    ack()

def process_profile_modal_submission(
    body: Dict[str, Any], view: Dict[str, Any], client: WebClient
) -> None:
    """Processes the profile form submission asynchronously by extracting and saving data."""
    user_id: str = body["user"]["id"]
    channel_id: str = view.get("private_metadata", "")
    
    logger.info(
        f"Processing profile modal submission asynchronously for user: '{user_id}'."
    )

    try:
        # Extract individual state input values using explicit block and action IDs
        state_values = view.get("state", {}).get("values", {})

        start_date: Optional[str] = (
            state_values.get("start_date_block", {})
            .get("start_date_input", {})
            .get("selected_date")
        )
        primary_contact: Optional[str] = (
            state_values.get("primary_contact_block", {})
            .get("primary_contact_input", {})
            .get("value")
        )
        backup_contact: Optional[str] = (
            state_values.get("backup_contact_block", {})
            .get("backup_contact_input", {})
            .get("value")
        )

        # Execute profile custom fields save
        slack_profile_service.update_user_custom_profile_fields(
            client=client,
            user_id=user_id,
            start_date=start_date,
            primary_contact=primary_contact,
            backup_contact=backup_contact,
        )

        # Notify the user of successful profile updates in the original channel
        if channel_id:
            client.chat_postEphemeral(
                channel=channel_id,
                user=user_id,
                text="✅ *F3 Profile Updated!* Your start date and emergency contact details have been successfully saved to your profile.",
            )
            logger.info(
                f"Posted successful save notification to user '{user_id}' in channel '{channel_id}'."
            )
        else:
            logger.warning(
                f"Skipping save notification for user '{user_id}' as 'channel_id' private metadata is empty."
            )

    except Exception as error:
        logger.error(
            f"Failed to process profile modal submission for user '{user_id}': {error}"
        )
        if channel_id:
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="❌ *Update Failed:* We encountered an error saving your profile changes. Please verify and try again.",
                )
            except Exception as ephemeral_error:
                logger.error(f"Failed to post error ephemeral notification: {ephemeral_error}")
