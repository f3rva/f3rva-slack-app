import pytest
from unittest.mock import MagicMock, patch
from services.slack_profile import slack_profile_service
from config.settings import settings

@patch("services.slack_profile.google_sheets_service")
def test_retrieve_user_custom_profile_fields_cached_success(mock_sheets) -> None:
    """Verifies that retrieval returns the cached record from Google Sheets if found."""
    mock_client = MagicMock()
    mock_user_id = "U12345"

    # Define mock database response
    mock_sheets.get_user_record.return_value = {
        "user_id": mock_user_id,
        "display_name": "Test User",
        "start_date": "2024-05-15",
        "primary_contact": "Primary Contact Phone",
        "backup_contact": "Backup Contact Phone",
        "updated_at": "2026-05-22 12:00:00"
    }

    # Execute service call
    result = slack_profile_service.retrieve_user_custom_profile_fields(
        client=mock_client,
        user_id=mock_user_id
    )

    # Assertions
    assert result["start_date"] == "2024-05-15"
    assert result["primary_contact"] == "Primary Contact Phone"
    assert result["backup_contact"] == "Backup Contact Phone"

    # Verify Google Sheets was queried and Slack API was NOT called
    mock_sheets.get_user_record.assert_called_once_with(mock_user_id)
    mock_client.users_profile_get.assert_not_called()


@patch("services.slack_profile.google_sheets_service")
def test_retrieve_user_custom_profile_fields_seed_success(mock_sheets) -> None:
    """Verifies that if no cached record exists, fields are fetched from Slack, seeded in Sheets, and returned."""
    mock_client = MagicMock()
    mock_user_id = "U98765"

    # Define mock database response: Not found
    mock_sheets.get_user_record.return_value = None

    # Stub response payload from Slack users.profile.get
    mock_client.users_profile_get.return_value = {
        "profile": {
            "display_name": "Pax Runner",
            "real_name": "Pax Real Name",
            "fields": {
                settings.start_date_profile_field_id: {
                    "value": "2023-11-10",
                    "alt": ""
                },
                settings.primary_emergency_contact_profile_field_id: {
                    "value": "Primary Contact (Wife) - 555-9000",
                    "alt": ""
                },
                settings.backup_emergency_contact_profile_field_id: {
                    "value": "Backup Contact (Brother) - 555-8000",
                    "alt": ""
                }
            }
        }
    }

    # Execute service call
    result = slack_profile_service.retrieve_user_custom_profile_fields(
        client=mock_client,
        user_id=mock_user_id
    )

    # Validate mapping results
    assert result["start_date"] == "2023-11-10"
    assert result["primary_contact"] == "Primary Contact (Wife) - 555-9000"
    assert result["backup_contact"] == "Backup Contact (Brother) - 555-8000"

    # Assert WebClient was invoked correctly (retrievals must use the Bot token)
    mock_client.users_profile_get.assert_called_once_with(
        token=settings.slack_bot_token,
        user=mock_user_id
    )

    # Assert Google Sheets was queried and then seeded with the display name and Slack values
    mock_sheets.get_user_record.assert_called_once_with(mock_user_id)
    mock_sheets.upsert_user_record.assert_called_once_with(
        user_id=mock_user_id,
        display_name="Pax Runner",
        start_date="2023-11-10",
        primary_contact="Primary Contact (Wife) - 555-9000",
        backup_contact="Backup Contact (Brother) - 555-8000"
    )


@patch("services.slack_profile.google_sheets_service")
def test_update_user_custom_profile_fields_success(mock_sheets) -> None:
    """Verifies that update_user_custom_profile_fields writes updates directly to Google Sheets database."""
    mock_client = MagicMock()
    mock_user_id = "U12345"

    # Test values
    start_date = "2025-01-01"
    primary_contact = "Primary Emergency Details"
    backup_contact = "Backup Emergency Details"

    # Stub user profile fetch from Slack to get display/real name
    mock_client.users_profile_get.return_value = {
        "profile": {
            "display_name": "Pax Leader",
            "real_name": "Real Pax Leader"
        }
    }

    # Execute service call
    slack_profile_service.update_user_custom_profile_fields(
        client=mock_client,
        user_id=mock_user_id,
        start_date=start_date,
        primary_contact=primary_contact,
        backup_contact=backup_contact
    )

    # Assert Slack profile get was called to resolve name using bot token
    mock_client.users_profile_get.assert_called_once_with(
        token=settings.slack_bot_token,
        user=mock_user_id
    )

    # Assert Google Sheets database was upserted with correct values
    mock_sheets.upsert_user_record.assert_called_once_with(
        user_id=mock_user_id,
        display_name="Pax Leader",
        start_date=start_date,
        primary_contact=primary_contact,
        backup_contact=backup_contact
    )
