import logging
from slack_bolt import App
from listeners.commands import acknowledge_profile_command, process_profile_command
from listeners.views import (
    acknowledge_profile_modal_submission,
    process_profile_modal_submission,
)

logger = logging.getLogger(__name__)

def register_listeners(app: App) -> None:
    """Attaches all command, view, action, event, and shortcut routing to the Bolt App instance."""
    
    logger.info("Initializing listener routing registry for monolithic application.")
    
    # 1. Slash Command Router
    app.command("/profile")(
        ack=acknowledge_profile_command,
        lazy=[process_profile_command]
    )
    
    # 2. Modal View Submission Router
    app.view("profile_modal_submit")(
        ack=acknowledge_profile_modal_submission,
        lazy=[process_profile_modal_submission]
    )
    
    # 3. Action Callbacks (Placeholder)
    # Register interactive component elements clicks here
    
    # 4. Events subscriptions (Placeholder)
    # Register events listeners here
    
    # 5. Shortcuts Router (Placeholder)
    # Register global or message shortcuts here
    
    logger.info("Successfully registered all monolithic application listener routes.")
