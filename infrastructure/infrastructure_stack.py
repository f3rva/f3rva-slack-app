import os
import subprocess
import jsii
import aws_cdk as cdk
from aws_cdk import (
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_events as events,
    aws_events_targets as targets,
)
from constructs import Construct

@jsii.implements(cdk.ILocalBundling)
class LocalBundler:
    """Provides Docker-free local asset bundling during CDK synthesis if pip3 and rsync are present."""

    def try_bundle(self, output_dir: str, options: cdk.BundlingOptions) -> bool:
        try:
            # Verify system has required bundling tools
            subprocess.run(["pip3", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            subprocess.run(["rsync", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            return False

        try:
            # 1. Install pip dependencies from requirements.txt into target asset output directory
            # We run cwd=".." because the parent folder is the root containing requirements.txt
            subprocess.run(
                ["pip3", "install", "--no-cache-dir", "-r", "requirements.txt", "-t", output_dir],
                cwd="..",
                check=True
            )
            # 2. Sync codebase files excluding git, virtualenvs, tests, caches, and infrastructure code
            subprocess.run([
                "rsync", "-av",
                "--exclude=.git",
                "--exclude=.venv",
                "--exclude=__pycache__",
                "--exclude=tests",
                "--exclude=infrastructure",
                "--exclude=.pytest_cache",
                ".", f"{output_dir}/"
            ], cwd="..", check=True)
            return True
        except Exception as e:
            print(f"Local bundling failed, falling back to CDK Docker bundling: {e}")
            return False

class F3RVAStackSlackApp(cdk.Stack):
    """Deploys a Python 3.12 Lambda function that runs workspace compliance scans on a weekly schedule."""

    def __init__(self, scope: Construct, construct_id: str, app_name: str, env_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Create a dedicated IAM Execution Role for the Lambda Function
        lambda_role_name = f"{app_name}-{env_name}-slackAppLambdaRole"
        lambda_role = iam.Role(
            self,
            "SlackAppLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=lambda_role_name,
            description=f"Execution role for the {app_name} Slack App Lambda function in {env_name}",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )
        cdk.Tags.of(lambda_role).add("Name", f"{app_name}-{env_name}-{lambda_role_name}")

        # Grant the role permission to send emails via Amazon Simple Email Service (SES)
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ses:SendEmail", "ses:SendRawEmail"],
                resources=["*"]
            )
        )

        # 2. Define the Python Lambda Function
        # We point cdk.Code.from_asset to ".." which contains app.py and requirements.txt
        slack_app_lambda = _lambda.Function(
            self,
            "SlackAppFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="app.handler",
            code=_lambda.Code.from_asset(
                path="..",
                bundling=cdk.BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install --no-cache-dir -r requirements.txt -t /asset-output && cp -ru . /asset-output"
                    ],
                    local=LocalBundler()
                )
            ),
            role=lambda_role,
            timeout=cdk.Duration.seconds(30), # Allows up to 30 seconds for full workspace directory scans
            memory_size=256,                  # Low memory footprint, fast cold starts
            environment={
                "APP_ENV": "production" if env_name == "prod" else "development",
                
                # Dynamic SSM Resolvers - Securely loads values from SSM Parameter Store at deploy time
                "SLACK_BOT_TOKEN": f"{{{{resolve:ssm:/{app_name}/{env_name}/slack_bot_token}}}}",
                "EMERGENCY_CONTACT_PRIMARY_FIELD_ID": f"{{{{resolve:ssm:/{app_name}/{env_name}/primary_emergency_contact_field_id}}}}",
                "EMERGENCY_CONTACT_BACKUP_FIELD_ID": f"{{{{resolve:ssm:/{app_name}/{env_name}/backup_emergency_contact_field_id}}}}",
                
                # Configures the verified email sender address based on the environment
                "EMAIL_SENDER_SOURCE": "admin@dev.f3rva.org" if env_name == "dev" else "admin@f3rva.org"
            }
        )
        cdk.Tags.of(slack_app_lambda).add("Name", f"{app_name}-{env_name}-slack-app")

        # 3. Create EventBridge Scheduled Rule (runs every Monday morning at 9:00 AM UTC / 5:00 AM EDT)
        rule = events.Rule(
            self,
            "SlackAppScheduleRule",
            schedule=events.Schedule.cron(minute="0", hour="9", week_day="MON"),
            description=f"Scheduled trigger for the {app_name} Slack Pester Bot in {env_name}"
        )
        rule.add_target(targets.LambdaFunction(slack_app_lambda))

        # Tag all stack resources
        cdk.Tags.of(self).add("APPLICATION", app_name)
        cdk.Tags.of(self).add("ENVIRONMENT", env_name)
