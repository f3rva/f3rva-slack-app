import os
import aws_cdk as cdk
from infrastructure_stack import F3RVAStackSlackApp

app = cdk.App()

# Get the account information from the sourced environment variables
dev_account = os.environ.get("F3RVA_ACCOUNT_DEV")
prod_account = os.environ.get("F3RVA_ACCOUNT_PROD")

if not dev_account:
    raise ValueError("Please specify required environment variable F3RVA_ACCOUNT_DEV")
if not prod_account:
    raise ValueError("Please specify required environment variable F3RVA_ACCOUNT_PROD")

# Account settings mirroring legacy environments
aws_account_development = cdk.Environment(account=dev_account, region="us-east-1")
aws_account_production = cdk.Environment(account=prod_account, region="us-east-1")

F3RVAStackSlackApp(
    app,
    "F3RVA-slack-app-dev",
    app_name="f3rva",
    env_name="dev",
    env=aws_account_development
)

F3RVAStackSlackApp(
    app,
    "F3RVA-slack-app-prod",
    app_name="f3rva",
    env_name="prod",
    env=aws_account_production
)

app.synth()
