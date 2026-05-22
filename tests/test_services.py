import pytest
from unittest.mock import MagicMock
from services.slack_profile import slack_profile_service
from config.settings import settings

def test_retrieve_user_custom_profile_fields_success() -> None:
    """Verifies that retrieve_user_custom_profile_fields parses custom profile fields correctly."""
    mock_client = MagicMock()
    mock_user_id = "U12345"
    
    # Stub response payload from users.profile.get
    mock_client.users_profile_get.return_value = {
        "profile": {
            "fields": {
                settings.start_date_profile_field_id: {
                    "value": "2024-05-15",
                    "alt": ""
                },
                settings.primary_emergency_contact_profile_field_id: {
                    "value": "John Doe (Spouse) - 555-0100",
                    "alt": ""
                },
                settings.backup_emergency_contact_profile_field_id: {
                    "value": "Jane Doe (Sister) - 555-0200",
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
    assert result["start_date"] == "2024-05-15"
    assert result["primary_contact"] == "John Doe (Spouse) - 555-0100"
    assert result["backup_contact"] == "Jane Doe (Sister) - 555-0200"
    
    # Assert WebClient was invoked correctly
    mock_client.users_profile_get.assert_called_once_with(user=mock_user_id)

def test_update_user_custom_profile_fields_success() -> None:
    """Verifies that update_user_custom_profile_fields structures the API payload correctly."""
    mock_client = MagicMock()
    mock_user_id = "U12345"
    
    # Test values
    start_date = "2025-01-01"
    primary_contact = "Primary Emergency Details"
    backup_contact = "Backup Emergency Details"
    
    # Execute service call
    slack_profile_service.update_user_custom_profile_fields(
        client=mock_client,
        user_id=mock_user_id,
        start_date=start_date,
        primary_contact=primary_contact,
        backup_contact=backup_contact
    )
    
    # Expected custom fields format
    expected_fields_payload = {
        settings.start_date_profile_field_id: {
            "value": start_date,
            "alt": ""
        },
        settings.primary_emergency_contact_profile_field_id: {
            "value": primary_contact,
            "alt": ""
        },
        settings.backup_emergency_contact_profile_field_id: {
            "value": backup_contact,
            "alt": ""
        }
    }
    
    # Assert WebClient was invoked with the exact expected payload structure
    mock_client.users_profile_set.assert_called_once_with(
        user=mock_user_id,
        profile={"fields": expected_fields_payload}
    )
