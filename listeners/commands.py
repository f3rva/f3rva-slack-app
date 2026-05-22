import logging
from typing import Dict, Any, Optional
from slack_bolt import Ack
from slack_sdk.web import WebClient
from services.slack_profile import slack_profile_service

logger = logging.getLogger(__name__)

def acknowledge_profile_command(ack: Ack) -> None:
    """Acknowledge the /profile slash command within the 3-second threshold."""
    ack()

def process_profile_command(body: Dict[str, Any], client: WebClient) -> None:
    """Lazily process the slash command by querying profile data and opening the modal."""
    user_id: str = body["user_id"]
    trigger_id: str = body["trigger_id"]

    logger.info(
        f"Processing /profile command asynchronously for user: '{user_id}'."
    )

    try:
        # Retrieve the user's current custom profile data
        profile_data = slack_profile_service.retrieve_user_custom_profile_fields(
            client=client, user_id=user_id
        )

        start_date: Optional[str] = profile_data.get("start_date")
        primary_contact: Optional[str] = profile_data.get("primary_contact")
        backup_contact: Optional[str] = profile_data.get("backup_contact")

        # Construct the Block Kit modal view
        modal_view: Dict[str, Any] = {
            "type": "modal",
            "callback_id": "profile_modal_submit",
            "private_metadata": body.get("channel_id", ""),
            "title": {
                "type": "plain_text",
                "text": "Update Profile",
                "emoji": True,
            },
            "submit": {
                "type": "plain_text",
                "text": "Save",
                "emoji": True,
            },
            "close": {
                "type": "plain_text",
                "text": "Cancel",
                "emoji": True,
            },
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Hey <@{user_id}>! Use this form to update your F3 RVA custom profile and emergency contact details.",
                    },
                },
                {
                    "type": "divider"
                },
                {
                    "type": "input",
                    "block_id": "start_date_block",
                    "optional": True,
                    "element": {
                        "type": "datepicker",
                        "action_id": "start_date_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select your F3 start date",
                            "emoji": True,
                        },
                        # Pre-populate if existing date exists
                        **({"initial_date": start_date} if start_date else {})
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Start Date",
                        "emoji": True,
                    },
                },
                {
                    "type": "input",
                    "block_id": "primary_contact_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "primary_contact_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Name (Relationship) - Phone Number",
                            "emoji": True,
                        },
                        "max_length": 150,
                        # Pre-populate if existing contact exists
                        **({"initial_value": primary_contact} if primary_contact else {})
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Emergency Contact - Primary",
                        "emoji": True,
                    },
                },
                {
                    "type": "input",
                    "block_id": "backup_contact_block",
                    "optional": True,
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "backup_contact_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Name (Relationship) - Phone Number",
                            "emoji": True,
                        },
                        "max_length": 150,
                        # Pre-populate if existing contact exists
                        **({"initial_value": backup_contact} if backup_contact else {})
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Emergency Contact - Backup",
                        "emoji": True,
                    },
                },
            ],
        }

        # Launch the interactive Block Kit Modal popup
        client.views_open(trigger_id=trigger_id, view=modal_view)
        logger.info(f"Opened profile modal view successfully for user '{user_id}'.")

    except Exception as error:
        logger.error(
            f"Failed to open profile modal view for user '{user_id}': {error}"
        )
        # Notify the user via an ephemeral message in the channel where the command was run
        channel_id = body.get("channel_id")
        if channel_id:
            try:
                client.chat_postEphemeral(
                    channel=channel_id,
                    user=user_id,
                    text="❌ Sorry, we encountered an error while trying to fetch your profile information. Please try again later.",
                )
            except Exception as ephemeral_error:
                logger.error(f"Failed to post error ephemeral notification: {ephemeral_error}")
