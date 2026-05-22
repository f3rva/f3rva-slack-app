import sys
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from config.settings import settings
from listeners import register_listeners

# Configure robust system-wide logging with level controls
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Initialize the central Slack Bolt App using our validated Slack Bot Token
app = App(
    token=settings.slack_bot_token,
    # Bolt automatically verifies signatures if using standard HTTP mode,
    # but Socket Mode handles communication over secure WebSockets.
)

# Attach all listener and monolithic routing definitions to our App
register_listeners(app=app)

if __name__ == "__main__":
    logger.info(
        f"Bootstrapping F3 RVA Slack Monolith App in '{settings.app_environment}' environment..."
    )
    
    try:
        # Initialize and boot the Slack Socket Mode connector
        handler = SocketModeHandler(
            app=app,
            app_token=settings.slack_app_token
        )
        logger.info("Socket Mode Handler initialized. Opening WebSocket connection to Slack...")
        handler.start()
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C). Exiting gracefully.")
    except Exception as error:
        logger.critical(f"Fatal application startup failure: {error}")
        sys.exit(1)
