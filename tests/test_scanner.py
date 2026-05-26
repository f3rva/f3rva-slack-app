import pytest
from unittest.mock import MagicMock, patch
from services.scanner import PesterBotScanner
from config.settings import settings

def test_check_user_compliance_with_ice_in_title() -> None:
    """Verifies that user is compliant if 'ICE' is in their standard profile title."""
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    mock_user = {
        "id": "U12345",
        "profile": {
            "title": "ICE: Wife Sarah (555-1234)"
        }
    }
    
    assert scanner.check_user_compliance(mock_user) is True

def test_check_user_compliance_case_insensitive() -> None:
    """Verifies that user is compliant if 'ice' appears in different casing in their profile title."""
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    mock_user = {
        "id": "U12345",
        "profile": {
            "title": "In Case of Emergency (ice) - 555-5678"
        }
    }
    
    assert scanner.check_user_compliance(mock_user) is True

@patch("services.scanner.settings")
def test_check_user_compliance_with_custom_fields(mock_settings) -> None:
    """Verifies that user is compliant if their custom emergency contact profile field has a value."""
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    mock_settings.primary_emergency_contact_profile_field_id = "X12345"
    
    mock_user = {
        "id": "U12345",
        "profile": {
            "title": "Developer",
            "fields": {
                "X12345": {
                    "value": "Jane (Wife) - 555-0999"
                }
            }
        }
    }
    
    assert scanner.check_user_compliance(mock_user) is True

@patch("services.scanner.settings")
def test_check_user_non_compliance(mock_settings) -> None:
    """Verifies that user is non-compliant if both title and custom fields are empty."""
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    mock_settings.primary_emergency_contact_profile_field_id = "X12345"
    
    mock_user = {
        "id": "U12345",
        "profile": {
            "title": "F3 Leader",
            "fields": {
                "X12345": {
                    "value": ""
                }
            }
        }
    }
    
    assert scanner.check_user_compliance(mock_user) is False

def test_send_pester_reminder_dispatches_slack_message() -> None:
    """Verifies that send_pester_reminder posts the correct Block Kit DM reminder to Slack."""
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    scanner.send_pester_reminder("U12345", "Test User")
    
    # Assert chat_postMessage was invoked with Block Kit parameters targeting the correct user
    client.chat_postMessage.assert_called_once()
    called_kwargs = client.chat_postMessage.call_args[1]
    assert called_kwargs["channel"] == "U12345"
    assert "blocks" in called_kwargs
    assert len(called_kwargs["blocks"]) == 3
    assert "Safety Reminder" in called_kwargs["text"]

@patch("services.scanner.boto3")
def test_send_email_reminder_dispatches_ses_email(mock_boto) -> None:
    """Verifies that send_email_reminder triggers boto3 SES send_email with correct params."""
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    mock_ses = MagicMock()
    mock_boto.client.return_value = mock_ses
    
    scanner.send_email_reminder("user@domain.com", "Test User")
    
    mock_boto.client.assert_called_once_with("ses", region_name="us-east-1")
    mock_ses.send_email.assert_called_once()
    called_kwargs = mock_ses.send_email.call_args[1]
    assert called_kwargs["Source"] == "admin@f3rva.org"
    assert called_kwargs["Destination"] == {"ToAddresses": ["user@domain.com"]}
    assert "Emergency Contact Details" in called_kwargs["Message"]["Subject"]["Data"]

@patch("services.scanner.boto3")
@patch("services.scanner.settings")
def test_run_workspace_scan_reminds_only_non_compliant_users(mock_settings, mock_boto) -> None:
    """Verifies that the workspace scan processes active members, skips bots/deactivated users,

    and triggers BOTH Slack DM and SES email notifications for non-compliant members.
    """
    client = MagicMock()
    scanner = PesterBotScanner(client=client)
    
    mock_settings.primary_emergency_contact_profile_field_id = "X12345"
    mock_settings.email_sender_source = "admin@f3rva.org"
    
    mock_ses = MagicMock()
    mock_boto.client.return_value = mock_ses
    
    # Stub users_list pagination to return 4 mock users in one page
    client.users_list.return_value = {
        "members": [
            {
                "id": "U001",
                "name": "compliant.pax",
                "real_name": "Compliant Pax",
                "is_bot": False,
                "deleted": False,
                "profile": {
                    "title": "ICE: Wife (555-0001)",
                    "email": "compliant@domain.com"
                }
            },
            {
                "id": "U002",
                "name": "noncompliant.pax",
                "real_name": "Noncompliant Pax",
                "is_bot": False,
                "deleted": False,
                "profile": {
                    "title": "Regular Title",
                    "email": "noncompliant@domain.com"
                }
            },
            {
                "id": "U003",
                "name": "bot.account",
                "is_bot": True,
                "deleted": False,
                "profile": {}
            },
            {
                "id": "U004",
                "name": "deactivated.pax",
                "is_bot": False,
                "deleted": True,
                "profile": {}
            },
            {
                "id": "U005",
                "name": "noemail.pax",
                "real_name": "No Email Pax",
                "is_bot": False,
                "deleted": False,
                "profile": {
                    "title": "Regular Title"
                    # No email address in profile
                }
            }
        ],
        "response_metadata": {
            "next_cursor": ""
        }
    }
    
    # Execute the scan
    summary = scanner.run_workspace_scan()
    
    # Assertions on returned user classifications
    assert "U001" in summary["compliant"]
    assert "U002" in summary["reminded"]
    assert "U005" in summary["reminded"]
    assert "U003" not in summary["compliant"] and "U003" not in summary["reminded"]
    assert "U004" not in summary["compliant"] and "U004" not in summary["reminded"]
    
    # Verify exactly two Slack DMs were dispatched (to U002 and U005)
    assert client.chat_postMessage.call_count == 2
    called_channels = [call[1]["channel"] for call in client.chat_postMessage.call_args_list]
    assert "U002" in called_channels
    assert "U005" in called_channels
    
    # Verify exactly one SES email was triggered (only to noncompliant@domain.com, skipped for U005)
    mock_boto.client.assert_called_once_with("ses", region_name="us-east-1")
    mock_ses.send_email.assert_called_once()
    called_kwargs = mock_ses.send_email.call_args[1]
    assert called_kwargs["Destination"] == {"ToAddresses": ["noncompliant@domain.com"]}
