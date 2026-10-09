# F3 RVA Slack Pester Bot

A lightweight, automated, zero-cost workspace directory compliance scanner designed for the `f3-rva-workspace.slack.com` workspace. 

Rather than offloading data to slow, complex external databases or requiring individual user OAuth installs (which created significant onboarding friction), this application operates purely natively:
1. **Compliance Scanning:** The bot scans active workspace members on a weekly schedule.
2. **Profile Audit:** It inspects each member's standard **"What I do" (Title)** profile description for the keyword `"ICE"` (In Case of Emergency) and optional custom emergency fields.
3. **Friendly DM Reminders:** It sends a highly polished, private Block Kit DM nudge to non-compliant users, giving them a 30-second step-by-step guide to edit their own profile card. The bot automatically stops nudging them once their profile is updated.

The entire codebase—both the scanner application and the AWS EventBridge scheduled CDK deployment stacks—is written **natively in Python 3.12+**.

---

## Tech Stack

*   **Language:** Python 3.12+
*   **Slack SDK:** `slack-sdk` (pure standard Python client)
*   **Infrastructure-from-Code:** Python AWS CDK v2 (`aws-cdk-lib`)
*   **Serverless Cron Hosting:** AWS Lambda (Python 3.12) + CloudWatch EventBridge Cron Rule (running weekly)
*   **Testing:** `pytest` + `pytest-mock`

---

## Directory Structure

```text
f3rva-slack-app/
├── README.md               # Setup, local testing, and CDK deploy guide
├── GEMINI.md               # AI coding guardrails and styling principles
├── requirements.txt        # Python dependency manifest (slack-sdk, python-dotenv)
├── app.py                  # Scanner entrypoint (local direct runs or AWS Lambda cron handler)
├── config/                 # Configuration and environment loaders
│   ├── __init__.py
│   └── settings.py         # Loads and validates Slack tokens on startup
├── services/               # Core business services
│   ├── __init__.py
│   └── scanner.py          # Workspace compliance scanner and DM nudging engine
├── tests/                  # Automated test suite
│   ├── __init__.py
│   └── test_scanner.py     # Scanner and reminder unit tests
└── infrastructure/         # Co-located Python AWS CDK project
    ├── requirements.txt    # CDK Python libraries (aws-cdk-lib, constructs)
    ├── cdk.json            # CDK execution runner config (triggers "python app.py")
    ├── app.py              # CDK app entrypoint registering dev/prod environments
    └── infrastructure_stack.py # Stack definition creating scheduled Cron Lambdas
```

---

## Quickstart: Local Development

### 1. Prerequisites
*   Python 3.10+ (recommend Python 3.12+).
*   Git.
*   Admin/App Manager permissions in your test Slack workspace.
*   Standard AWS CLI and global [AWS CDK CLI](https://docs.aws.amazon.com/cdk/v2/guide/cli.html) installed (`npm install -g aws-cdk`).

### 2. Installation & Setup
```bash
# Clone the repository
git clone git@github.com:f3rva/f3rva-slack-app.git
cd f3rva-slack-app

# Create and activate a Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install application dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Local Environment
Create a local `.env` file in the root directory:
```env
# Slack Bot User OAuth Token (Starts with 'xoxb-', found in api.slack.com)
SLACK_BOT_TOKEN=xoxb-your-bot-token

# (Optional) Administrative Slack User Token (Starts with 'xoxp-', required for billing active filters)
SLACK_USER_TOKEN=xoxp-your-user-token

# (Optional) Custom emergency contact profile field IDs if your workspace supports them:
EMERGENCY_CONTACT_PRIMARY_FIELD_ID=XF12345ABC
EMERGENCY_CONTACT_BACKUP_FIELD_ID=XF67890DEF

# (Optional) Verified SES Email Sender address. Defaults to 'admin@f3rva.org' if omitted.
# Note: This email (or its domain) must be a verified identity in your Amazon SES Console!
EMAIL_SENDER_SOURCE=admin@dev.f3rva.org

# App Environment
APP_ENV=development
```

### 4. Run the Scan Locally
To trigger a live workspace scan and send DM reminders to non-compliant users immediately:
```bash
python app.py
```

---

## Slack App Configuration Guide (api.slack.com)

This Slack App serves two key regional roles:
1. **Compliance Scanner (Pester Bot):** Scans active members, audits profile ICE descriptions, and sends reminder DMs.
2. **Website Authentication & Backblast Publishing (`f3rva-api` & `f3rva-website`):** Enables 1-click **Sign in with Slack** (OpenID Connect) for members to log into `f3rva.org`, and automatically posts formatted backblast summary cards to the regional `#backblasts` channel.

To configure the app on the [Slack API Portal](https://api.slack.com/apps):

### 1. OAuth & Permissions: Redirect URLs
Navigate to **Features** > **OAuth & Permissions** > **Redirect URLs** and add the website OAuth callback endpoints:
* `https://f3rva.org/auth/slack/callback` (Production)
* `https://dev.f3rva.org/auth/slack/callback` (Development)
* `http://localhost:5173/auth/slack/callback` (Local frontend dev)

Click **Save URLs**.

### 2. Scopes
* **Bot Token Scopes**:
  * `users:read`: Allows fetching the active workspace member directory.
  * `users.profile:read`: Allows inspecting standard "What I do" (Title) and custom profile fields.
  * `chat:write`: Allows sending reminder DMs to members and dispatching backblast cards to `#backblasts`.
  * `users:read.email`: Allows retrieving each member's email address for SES email alerts.
* **User Token Scopes**:
  * `admin` *(Optional but recommended)*: Grants permissions to query `team.billableInfo` for active billing filtering.
  * *Note: Do NOT add `openid`, `profile`, or `email` here as static workspace scopes. OpenID Connect scopes are requested dynamically during user sign-in via the authorize URL.*

### 3. Channel Membership
* In the Slack workspace, invite the bot to the backblasts channel: `/invite @<bot_name>` in `#backblasts`.

### 4. Install / Reinstall to Workspace
* Click **Install (or Reinstall) to Workspace** to generate your `SLACK_BOT_TOKEN` (`xoxb-`) and `SLACK_USER_TOKEN` (`xoxp-`).
* Obtain your **Client ID** and **Client Secret** under **Settings** > **Basic Information** > **App Credentials**.

---

## AWS CDK Infrastructure & Deployment

The infrastructure is co-located inside the `infrastructure/` subfolder. The Lambda function is private and contains no public URL endpoints, securing it fully at $0 running cost.

### 1. Setup Infrastructure Environment
Install the Python CDK dependencies inside your virtual environment:
```bash
cd infrastructure
pip install -r requirements.txt
```

### 2. Configure AWS Environment Variables
The CDK stacks require the target AWS 12-digit Account IDs to synthesize the SSM Parameter Store and EventBridge integrations. 
Ensure these are exported in your terminal session:
```bash
export F3RVA_ACCOUNT_DEV="123456789012"
export F3RVA_ACCOUNT_PROD="987654321098"
```

### 3. Provision AWS SSM Parameter Store Parameters
Before deploying the stacks via CDK or integrating with `f3rva-api`, provision the following parameters in your target AWS account's Systems Manager (SSM) Parameter Store (in `us-east-1`):

#### Pester Bot Parameters
| Parameter Name | Type | Recommended Value (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `/f3rva/{env}/slack_bot_token` | `SecureString` | `xoxb-your-slack-bot-token` | The Slack Bot User OAuth Token with required scopes. |
| `/f3rva/{env}/slack_user_token` | `SecureString` | `xoxp-your-slack-user-token` | Administrative Slack User Token (required for billing status check). |
| `/f3rva/{env}/primary_emergency_contact_field_id` | `String` | `XF12345ABC` | Custom primary emergency contact field ID. |
| `/f3rva/{env}/backup_emergency_contact_field_id` | `String` | `XF67890DEF` | Custom backup emergency contact field ID. |
| `/f3rva/{env}/email_sender_source` | `String` | `admin@dev.f3rva.org` | The verified SES email sender identity. |
| `/f3rva/{env}/app_env` | `String` | `development` | Configures the runtime environment (`development` or `production`). |

#### Website Authentication & Backblast Integration Parameters (`f3rva-api`)
| Parameter Name | Type | Recommended Value (Dev) | Description |
| :--- | :--- | :--- | :--- |
| `/f3rva/{env}/slack_client_id` | `String` | `11191764578630.11224289195056` | Slack App Client ID from Basic Information. |
| `/f3rva/{env}/slack_client_secret` | `SecureString` | `your-slack-client-secret` | Slack App Client Secret from Basic Information. |
| `/f3rva/{env}/slack_allowed_team_id` | `String` | `T0B5MNGH0JJ` | Allowed Slack Team/Workspace ID to restrict authentication. |
| `/f3rva/{env}/slack_backblast_channel_id` | `String` | `C0B5NK4E44V` | Target Slack Channel ID for automated backblast summary cards. |
| `/f3rva/{env}/backblast_url_prefix` | `String` | `https://dev.f3rva.org` | Base URL prefix for backblast permalinks (`https://f3rva.org` in prod). |

*(Replace `{env}` in the path with `dev` or `prod` depending on the environment stack. Underscores are the native naming convention).*

### 4. CDK CLI Commands
Execute these commands from inside the `infrastructure/` folder:

```bash
# Synthesize the CloudFormation template and verify local asset bundling
cdk synth F3RVA-slack-app-dev

# Deploy the Dev Stack to AWS
cdk deploy F3RVA-slack-app-dev --require-approval never

# Deploy the Prod Stack to AWS
cdk deploy F3RVA-slack-app-prod --require-approval never
```

*Note: Bundling uses a high-performance **Local Python Bundler**. During synthesis, it checks for system `pip3` and `rsync`. If present, it packages requirements locally in seconds without requiring Docker! If missing, it falls back to a standard CDK Docker bundling container.*

---

## Testing
The application uses `pytest` and `pytest-mock` for testing the directory auditing and DM dispatch logic with mocked Slack APIs.

Run tests from the root directory:
```bash
pytest tests/
```
