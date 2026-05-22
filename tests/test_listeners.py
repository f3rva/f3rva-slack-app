import pytest
from unittest.mock import MagicMock, patch
from listeners.commands import acknowledge_profile_command, process_profile_command
from listeners.views import (
    acknowledge_profile_modal_submission,
    process_profile_modal_submission,
)

def test_acknowledge_profile_command() -> None:
    """Verifies the /profile slash command is acknowledged immediately."""
    mock_ack = MagicMock()
    acknowledge_profile_command(ack=mock_ack)
    mock_ack.assert_called_once()

@patch("listeners.commands.slack_profile_service")
def test_process_profile_command_opens_modal(mock_profile_service) -> None:
    """Verifies that process_profile_command fetches fields and opens a Block Kit modal."""
    mock_client = MagicMock()
    mock_body = {
        "user_id": "U98765",
        "trigger_id": "T12345",
        "channel_id": "C55555"
    }
    
    # Mock current profile fields returned by service
    mock_profile_service.retrieve_user_custom_profile_fields.return_value = {
        "start_date": "2023-11-20",
        "primary_contact": "John Doe",
        "backup_contact": "Jane Doe"
    }
    
    # Execute lazy listener call
    process_profile_command(body=mock_body, client=mock_client)
    
    # Assert service query was invoked
    mock_profile_service.retrieve_user_custom_profile_fields.assert_called_once_with(
        client=mock_client,
        user_id="U98765"
    )
    
    # Assert client.views_open was invoked with structured modal parameters
    mock_client.views_open.assert_called_once()
    called_args, called_kwargs = mock_client.views_open.call_args
    assert called_kwargs["trigger_id"] == "T12345"
    view_payload = called_kwargs["view"]
    assert view_payload["type"] == "modal"
    assert view_payload["callback_id"] == "profile_modal_submit"
    assert view_payload["private_metadata"] == "C55555"
    # Verify blocks contain input items
    block_types = [block["type"] for block in view_payload["blocks"]]
    assert "input" in block_types

def test_acknowledge_profile_modal_submission() -> None:
    """Verifies modal submission is acknowledged immediately."""
    mock_ack = MagicMock()
    acknowledge_profile_modal_submission(ack=mock_ack)
    mock_ack.assert_called_once()

@patch("listeners.views.slack_profile_service")
def test_process_profile_modal_submission_saves_fields(mock_profile_service) -> None:
    """Verifies modal form inputs are parsed and saved successfully."""
    mock_client = MagicMock()
    mock_body = {
        "user": {
            "id": "U98765"
        }
    }
    mock_view = {
        "private_metadata": "C55555",
        "state": {
            "values": {
                "start_date_block": {
                    "start_date_input": {
                        "selected_date": "2020-05-10"
                    }
                },
                "primary_contact_block": {
                    "primary_contact_input": {
                        "value": "Primary Name - Phone"
                    }
                },
                "backup_contact_block": {
                    "backup_contact_input": {
                        "value": "Backup Name - Phone"
                    }
                }
            }
        }
    }
    
    # Execute lazy listener call
    process_profile_modal_submission(
        body=mock_body,
        view=mock_view,
        client=mock_client
    )
    
    # Verify that the service update function was called with parsed parameters
    mock_profile_service.update_user_custom_profile_fields.assert_called_once_with(
        client=mock_client,
        user_id="U98765",
        start_date="2020-05-10",
        primary_contact="Primary Name - Phone",
        backup_contact="Backup Name - Phone"
    )
    
    # Verify that success ephemeral alert is dispatched
    mock_client.chat_postEphemeral.assert_called_once_with(
        channel="C55555",
        user="U98765",
        text="✅ *F3 Profile Updated!* Your start date and emergency contact details have been successfully saved to your profile."
    )

@patch("listeners.views.slack_profile_service")
def test_process_profile_modal_submission_saves_fields_dm(mock_profile_service) -> None:
    """Verifies modal form inputs submitted in a DM channel notify using standard chat_postMessage."""
    mock_client = MagicMock()
    mock_body = {
        "user": {
            "id": "U98765"
        }
    }
    mock_view = {
        "private_metadata": "D12345",  # DM channel ID starts with 'D'
        "state": {
            "values": {
                "start_date_block": {
                    "start_date_input": {
                        "selected_date": "2020-05-10"
                    }
                },
                "primary_contact_block": {
                    "primary_contact_input": {
                        "value": "Primary Name - Phone"
                    }
                },
                "backup_contact_block": {
                    "backup_contact_input": {
                        "value": "Backup Name - Phone"
                    }
                }
            }
        }
    }
    
    # Execute lazy listener call
    process_profile_modal_submission(
        body=mock_body,
        view=mock_view,
        client=mock_client
    )
    
    # Verify that success standard DM message is dispatched (no chat_postEphemeral)
    mock_client.chat_postMessage.assert_called_once_with(
        channel="U98765",
        text="✅ *F3 Profile Updated!* Your start date and emergency contact details have been successfully saved to your profile."
    )
    mock_client.chat_postEphemeral.assert_not_called()
