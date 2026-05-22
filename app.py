import os
import sys
import logging
from slack_bolt import App
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

# Initialize the central Slack Bolt App using our validated Slack credentials.
# process_before_response=True guarantees synchronous webhook execution parity,
# which is essential for serverless FaaS like AWS Lambda.
app = App(
    token=settings.slack_bot_token,
    signing_secret=settings.slack_signing_secret,
    process_before_response=True
)

# Attach all listener and monolithic routing definitions to our App
register_listeners(app=app)

# Expose the handler for AWS Lambda environment.
# We load the AwsLambdaHandler dynamically to avoid local dependency issues if boto3 is not installed.
handler = None
if "AWS_LAMBDA_FUNCTION_NAME" in os.environ or os.getenv("APP_ENV") == "production":
    try:
        from slack_bolt.adapter.aws_lambda import AwsLambdaHandler
        handler = AwsLambdaHandler(app=app)
        logger.info("AWS Lambda Handler initialized successfully.")
    except ImportError as e:
        logger.error(
            f"Failed to initialize AWS Lambda handler. Please ensure 'boto3' is installed "
            f"in the deployment environment: {e}"
        )

if __name__ == "__main__":
    logger.info(
        f"Bootstrapping F3 RVA Slack Monolith App in '{settings.app_environment}' environment..."
    )
    
    try:
        # Start Bolt's built-in development HTTP server. We default to 3001
        # to avoid port conflicts with the Vite website project running on 3000.
        port = int(os.getenv("PORT", 3001))
        logger.info(f"Starting Slack Bolt HTTP Webhook server on port {port}...")
        app.start(port=port)
        
    except KeyboardInterrupt:
        logger.info("Shutdown signal received (Ctrl+C). Exiting gracefully.")
    except Exception as error:
        logger.critical(f"Fatal application startup failure: {error}")
        sys.exit(1)
