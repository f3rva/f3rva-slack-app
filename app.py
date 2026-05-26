import sys
import logging
from slack_sdk.web import WebClient
from config.settings import settings
from services.scanner import PesterBotScanner

# Configure robust logging for both local runs and CloudWatch
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("app")

def run_pester_scan() -> None:
    """Instantiates a Slack client and runs the workspace compliance check."""
    logger.info("Initializing Slack WebClient...")
    client = WebClient(token=settings.slack_bot_token)
    
    scanner = PesterBotScanner(client=client)
    scanner.run_workspace_scan()

def handler(event, context) -> dict:
    """The entry point for AWS Lambda, triggered on an EventBridge scheduled cron rule."""
    logger.info("AWS Lambda EventBridge scheduled trigger received.")
    try:
        run_pester_scan()
        return {
            "statusCode": 200,
            "body": "Workspace scan completed successfully."
        }
    except Exception as error:
        logger.critical(f"Lambda execution failed: {error}")
        return {
            "statusCode": 500,
            "body": f"Workspace scan failed: {error}"
        }

if __name__ == "__main__":
    logger.info("Starting local F3 RVA Slack Pester Bot scan...")
    try:
        run_pester_scan()
        logger.info("Local scan finished successfully.")
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C). Exiting.")
    except Exception as error:
        logger.critical(f"Local scan run failed: {error}")
        sys.exit(1)
