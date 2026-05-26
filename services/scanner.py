import logging
import boto3
from typing import Dict, Any, Optional, List
from slack_sdk.web import WebClient
from config.settings import settings

logger = logging.getLogger(__name__)

class PesterBotScanner:
    """Scans all active workspace members to ensure they have Emergency Contact (ICE) info

    configured natively in their Slack profiles. Sends friendly DM and email reminders to non-compliant members.
    """

    def __init__(self, client: WebClient) -> None:
        self.client = client

    def check_user_compliance(self, user: Dict[str, Any]) -> bool:
        """Determines if a user has configured Emergency Contact (ICE) details in their profile.

        Checks both:
        1. The standard "Title" field for the keyword "ICE".
        2. Optional custom emergency contact fields if their field IDs are configured.
        """
        profile: Dict[str, Any] = user.get("profile", {})
        
        # 1. Check standard "Title" field for "ICE" (case-insensitive)
        title: str = profile.get("title", "").strip().lower()
        if "ice" in title:
            return True

        # 2. Check custom emergency contact fields if configured
        fields: Any = profile.get("fields")
        if isinstance(fields, dict):
            # Safe helper to check a custom field by ID
            def _has_field_value(field_id: Optional[str]) -> bool:
                if not field_id:
                    return False
                field_data = fields.get(field_id)
                if isinstance(field_data, dict):
                    return bool(field_data.get("value", "").strip())
                return False

            if _has_field_value(settings.primary_emergency_contact_profile_field_id):
                return True

        return False

    def send_pester_reminder(self, user_id: str, user_name: str) -> None:
        """Sends a beautifully formatted Block Kit reminder DM to a non-compliant user."""
        logger.info(f"Sending friendly emergency contact reminder DM to user: {user_name} ({user_id})")
        
        reminder_blocks: List[Dict[str, Any]] = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"👋 *F3 RVA Safety Reminder*\n\n"
                        f"Hey <@{user_id}>! To keep the PAX safe during our workouts, we ask everyone to add their "
                        f"**Emergency Contact (ICE)** info directly to their Slack profile. This makes it instantly "
                        f"visible to leaders in one click on their phone in case of an emergency."
                    )
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*How to add it in 30 seconds:*\n"
                        f"1️⃣ Tap your profile picture in Slack and select *Edit Profile*.\n"
                        f"2️⃣ **Choose one of the following methods:**\n"
                        f"    * 💻 *On Desktop (Recommended):* Populate the dedicated **`Emergency Contact - Primary`** and **`Emergency Contact - Backup`** fields.\n"
                        f"    * 📱 *On Mobile:* Scroll to the **`Title`** field and add: `ICE: [Name] ([Relationship]) - [Phone Number]`.\n"
                        f"3️⃣ Tap *Save Changes*."
                    )
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "ℹ️ _The bot will stop reminding you once your profile is updated. Thank you for helping keep the PAX safe!_"
                    }
                ]
            }
        ]

        try:
            self.client.chat_postMessage(
                channel=user_id,
                blocks=reminder_blocks,
                text="⚠️ F3 RVA Safety Reminder: Please configure your Emergency Contact (ICE) info in your Slack profile."
            )
        except Exception as e:
            logger.error(f"Failed to send reminder DM to user {user_id}: {e}")

    def send_email_reminder(self, email: str, user_name: str) -> None:
        """Sends a friendly emergency contact reminder email via Amazon SES using boto3."""
        sender = settings.email_sender_source
        logger.info(f"Sending friendly emergency contact reminder email to {user_name} ({email}) from {sender}...")
        
        subject = "⚠️ F3 RVA Safety Action Required: Emergency Contact Details"
        body_text = (
            f"Hello {user_name},\n\n"
            f"To keep the PAX safe during our workouts, we ask everyone to add their "
            f"Emergency Contact (ICE) info directly to their Slack profile. This makes it instantly "
            f"visible to leaders in one click on their phone in case of an emergency.\n\n"
            f"How to add it in 30 seconds:\n"
            f"1. Tap your profile picture in Slack and select 'Edit Profile'.\n"
            f"2. Choose one of the following methods:\n"
            f"   * On Desktop (Recommended): Populate the dedicated 'Emergency Contact - Primary' and 'Emergency Contact - Backup' fields.\n"
            f"   * On Mobile: Scroll to the 'Title' field and add: ICE: [Name] ([Relationship]) - [Phone Number].\n"
            f"3. Tap 'Save Changes'.\n\n"
            f"Thank you for helping keep the PAX safe!\n\n"
            f"— F3 RVA Safety Bot"
        )
        body_html = (
            f"<p>Hello {user_name},</p>"
            f"<p>To keep the PAX safe during our workouts, we ask everyone to add their "
            f"<strong>Emergency Contact (ICE)</strong> info directly to their Slack profile. This makes it instantly "
            f"visible to leaders in one click on their phone in case of an emergency.</p>"
            f"<p><strong>How to add it in 30 seconds:</strong></p>"
            f"<ol>"
            f"<li>Tap your profile picture in Slack and select <strong>Edit Profile</strong>.</li>"
            f"<li><strong>Choose one of the following methods:</strong>"
            f"  <ul>"
            f"    <li>💻 <strong>On Desktop (Recommended):</strong> Populate the dedicated <strong>Emergency Contact - Primary</strong> and <strong>Emergency Contact - Backup</strong> fields.</li>"
            f"    <li>📱 <strong>On Mobile:</strong> Scroll to the <strong>Title</strong> field and add: <code>ICE: [Name] ([Relationship]) - [Phone Number]</code>.</li>"
            f"  </ul>"
            f"</li>"
            f"<li>Tap <strong>Save Changes</strong>.</li>"
            f"</ol>"
            f"<p>Thank you for helping keep the PAX safe!</p>"
            f"<p>— F3 RVA Safety Bot</p>"
        )

        try:
            # Deploy in us-east-1 where other f3rva email stacks live
            ses_client = boto3.client("ses", region_name="us-east-1")
            ses_client.send_email(
                Source=sender,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": subject},
                    "Body": {
                        "Text": {"Data": body_text},
                        "Html": {"Data": body_html}
                    }
                }
            )
            logger.info(f"Successfully sent SES email reminder to {email}")
        except Exception as e:
            logger.error(f"Failed to send email reminder via SES to {email}: {e}")

    def run_workspace_scan(self) -> Dict[str, List[str]]:
        """Scans the entire workspace and sends reminders to non-compliant members.

        Returns a summary dictionary of compliant and reminded user IDs.
        """
        logger.info("Starting workspace-wide emergency profile scan...")
        
        compliant_users: List[str] = []
        reminded_users: List[str] = []
        
        cursor: Optional[str] = None
        
        try:
            while True:
                # Page through all users in the directory
                response = self.client.users_list(cursor=cursor, limit=200)
                members: List[Dict[str, Any]] = response.get("members", [])
                
                for member in members:
                    user_id = member.get("id")
                    user_name = member.get("name")
                    real_name = member.get("real_name") or user_name
                    
                    # Skip bots, deleted accounts, and slackbot
                    if member.get("is_bot") or member.get("deleted") or user_id == "USLACKBOT":
                        continue
                        
                    is_compliant = self.check_user_compliance(member)
                    if is_compliant:
                        compliant_users.append(user_id)
                    else:
                        reminded_users.append(user_id)
                        profile = member.get("profile", {})
                        display_name = profile.get("display_name") or real_name
                        logger.info(f"Nagging non-compliant user: Display Name = '{display_name}' (ID = '{user_id}')")
                        
                        # 1. Send the Slack DM nudge
                        self.send_pester_reminder(user_id, real_name)
                        
                        # 2. Extract email address from profile and send SES warning if present
                        email = member.get("profile", {}).get("email")
                        if email:
                            self.send_email_reminder(email, real_name)
                        else:
                            logger.info(f"Skipping email nudge for {real_name} as no email address is present in their Slack profile.")
                
                # Fetch next page cursor
                cursor = response.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                    
            logger.info(
                f"Workspace scan completed successfully. "
                f"Total members analyzed: {len(compliant_users) + len(reminded_users)}. "
                f"Compliant: {len(compliant_users)}, Reminded: {len(reminded_users)}."
            )
            
            return {
                "compliant": compliant_users,
                "reminded": reminded_users
            }
            
        except Exception as e:
            logger.exception(f"Fatal failure during workspace emergency scan: {e}")
            raise e
