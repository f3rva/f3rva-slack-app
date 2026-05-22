# F3 RVA Slack App

A monolithic Slack application designed for the `f3-rva-workspace.slack.com` workspace.

To support the Slack free tier constraints (where writing to other members' custom profile fields is blocked), this application uses a hybrid architecture:
1. **Google Sheets Database Backend:** Acts as the database of record for member profile fields. On first view, the app runs a one-shot "Fetch-and-Seed" migration that reads the member's existing Slack custom fields (allowed via Bot Token), seeds them into the spreadsheet, and saves all subsequent updates directly to Google Sheets.
2. **HTTP Webhook Server (Parity Mode):** The app operates entirely in standard HTTP Webhook mode. It uses Slack's cryptographically secured signature verification (`SLACK_SIGNING_SECRET`) in both local development (listening on port 3001 exposed via `ngrok` by default) and production (AWS Lambda + Amazon API Gateway).

The application is written in **Python 3.12+** using the official **Slack Bolt for Python** framework.

---

## Features

1. **Emergency Contact Profile Manager**
   - Allows members (PAX) to view, add, or update custom emergency contact details via interactive Block Kit modals using `/profile`.
   - Bypasses API multi-user write restrictions on the free tier by using Google Sheets as the storage layer of record.
   - Automatically migrates existing Slack emergency contact data on first use ("Fetch-and-Seed").
2. **Monolithic Extensibility**
   - Decoupled listener-router architecture makes it easy to plug in new commands, event listeners, or interactive workflows.
3. **100% Signature Verified**
   - Secures all requests cryptographically using the Slack Signing Secret, ensuring identical security profiles locally and in production.

---

## Tech Stack

- **Language:** Python 3.12+ (strictly typed)
- **Framework:** Slack Bolt for Python (`slack-bolt`)
- **Database:** Google Sheets API (`gspread` + `google-auth`)
- **Production Serverless Hosting:** AWS Lambda (Python 3.12) + Amazon API Gateway
- **Local Dev Server:** Built-in Bolt HTTP server (port 3001 by default) behind an `ngrok` tunnel

---

## Directory Structure

```text
f3rva-slack-app/
├── README.md               # Developer setup and Slack config guide
├── GEMINI.md               # AI agent styling, architecture, and coding guardrails
├── requirements.txt        # Python dependency manifest (gspread, boto3, slack-bolt, etc.)
├── app.py                  # Entrypoint. Dynamically detects AWS Lambda context or boots local dev server
├── config/                 # Configuration and environment parser
│   ├── __init__.py
│   └── settings.py         # Type-safe validation of Slack & Google Sheets credentials
├── listeners/              # Routing & controller layer (thin controllers)
│   ├── __init__.py         # Registers listeners onto the central Bolt App instance
│   ├── actions.py          # Handles interactive block events (button clicks, menu selects)
│   ├── commands.py         # Handles Slash commands (e.g., `/profile`)
│   ├── events.py           # Handles Slack events (e.g., app_mention)
│   ├── shortcuts.py        # Handles global and message shortcuts
│   └── views.py            # Handles modal submissions (form validation and saves)
├── services/               # Core business logic layer (independent of transport/framework)
│   ├── __init__.py
│   ├── slack_profile.py    # Service for retrieving/seeding from Slack and saving to Sheets
│   └── database.py         # GoogleSheetsService backend using gspread
└── tests/                  # Test suite
    ├── __init__.py
    ├── test_listeners.py
    └── test_services.py
```

---

## Quickstart: Local Development

### 1. Prerequisites
- Python 3.10+ (recommend Python 3.12+) installed locally.
- Git.
- Admin access (or App Manager privileges) in the `f3-rva-workspace` Slack workspace.
- A free Google Cloud Console project with the **Google Sheets API** and **Google Drive API** enabled.
- A tunneling tool like `ngrok` installed.

### 2. Google Sheets Setup
Choose one of the following keyless authentication strategies:

* **Strategy A: GCP Workload Identity Federation (WIF) - For Production**
  1. Share the Google Spreadsheet directly with **your GCP Service Account's email address** as an **Editor** (no key file is generated).
  2. Configure a GCP Workload Identity Pool and Provider to trust your AWS Account and the Lambda function's IAM Role.
  3. Generate a keyless **Workload Identity credentials configuration file** (e.g. `wif-credential-config.json`).
* **Strategy B: Local Developer Credentials (Keyless Fallback - For Local Development)**
  1. Share the Google Spreadsheet directly with **your own corporate email address** as an **Editor**.
  2. Install the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) on your local computer.
  3. In your terminal, run the login command requesting Google Sheets and Drive access scopes:
     ```bash
     gcloud auth application-default login --scopes="https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive,https://www.googleapis.com/auth/cloud-platform"
     ```
     This opens a browser where you log in with your corporate Google Account, creating a secure local keyless credentials file with the necessary scopes that the app loads automatically!

* **Strategy C: Local Service Account Impersonation (Recommended for Enterprise/Corporate Workspace Blocks)**
  If your corporate Google Workspace blocks the "Google Cloud SDK" from accessing sensitive scopes (showing a *"This app is blocked"* error during Strategy B), use keyless Service Account Impersonation. Your local login uses standard safe scopes, and your app impersonates a Service Account to access Sheets:
  1. **Reset standard local login** (does not request sensitive scopes, so it bypasses corporate Workspace blocks):
     ```bash
     gcloud auth application-default login
     ```
  2. **Create a target Service Account** in your GCP project (no key generated):
     ```bash
     gcloud iam service-accounts create slack-app-local \
         --description="Service account for local Slack App development" \
         --display-name="slack-app-local"
     ```
  3. **Grant yourself permission** to impersonate the service account:
     ```bash
     gcloud iam service-accounts add-iam-policy-binding \
         slack-app-local@YOUR_PROJECT_ID.iam.gserviceaccount.com \
         --member="user:YOUR_CORPORATE_EMAIL@domain.com" \
         --role="roles/iam.serviceAccountTokenCreator"
     ```
  4. **Share your Google Spreadsheet** directly with the Service Account email (`slack-app-local@YOUR_PROJECT_ID.iam.gserviceaccount.com`) as an **Editor**.
  5. Add the target Service Account to your local `.env` file:
     ```ini
     GOOGLE_IMPERSONATE_SERVICE_ACCOUNT=slack-app-local@YOUR_PROJECT_ID.iam.gserviceaccount.com
     ```

*(Optional) Set the first row header fields to: `user_id`, `display_name`, `start_date`, `primary_contact`, `backup_contact`, `updated_at`. If empty, the app will automatically write headers.*

### 3. Clone and Setup Environment
```bash
# Clone the repository
git clone git@github.com:f3rva/f3rva-slack-app.git
cd f3rva-slack-app

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a local `.env` file in the root directory:
```env
# Slack Credentials
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-slack-signing-secret

# Field IDs for Custom Slack Profile Fields (used for fetch-and-seed lookup)
START_DATE_FIELD_ID=XF0123ABCD
EMERGENCY_CONTACT_PRIMARY_FIELD_ID=XF4567EFGH
EMERGENCY_CONTACT_BACKUP_FIELD_ID=XF8901IJKL

# Google Sheets Configuration
GOOGLE_SHEETS_SPREADSHEET_KEY=your-spreadsheet-key

# Google Application Default Credentials (ADC) configuration:
# For local keyless development via Strategy B, you can leave this empty/commented!
# For production keyless WIF, this can point to the path of your bundled, keyless WIF config:
# GOOGLE_APPLICATION_CREDENTIALS=wif-credential-config.json

# App Environment
APP_ENV=development
```

### 5. Expose Development Server via ngrok
Slack must be able to send HTTP POST request webhooks to your local machine.
1. Expose port 3001:
   ```bash
   ngrok http 3001
   ```
2. Copy the resulting public HTTPS URL (e.g. `https://1234-abcd.ngrok-free.app`).

### 6. Run the App Locally
```bash
python app.py
```
The app will start a signature-verified HTTP webhook server listening on port 3001 (or another port if the `PORT` env var is specified)!

---

## Slack App Configuration Guide (api.slack.com)

To connect this codebase to the F3 RVA Slack workspace, configure your app on the [Slack API Portal](https://api.slack.com/apps):

### 1. Configure Scopes (OAuth & Permissions)
Navigate to **Features** > **OAuth & Permissions** and add the following **Bot Token Scopes**:
- `commands`: Allows the bot to register and handle custom slash commands.
- `users.profile:read`: Allows the bot to view users' profiles (needed for initial fetch-and-seed data lookup).
- `users:read`: Allows the bot to fetch list data and general info about workspace members.
- `chat:write`: Allows the bot to send success notification/ephemeral messages to users.

Install the app to the workspace after configuring these scopes to generate the `SLACK_BOT_TOKEN` (starts with `xoxb-`).

### 2. Enable Interactivity & Event Subscriptions
1. Go to **Features** > **Interactivity & Shortcuts** and toggle it **On**.
   - Set the **Request URL** to `https://<your-ngrok-or-apigateway-url>/slack/events`.
2. Go to **Features** > **Event Subscriptions** and toggle it **On**.
   - Set the **Request URL** to `https://<your-ngrok-or-apigateway-url>/slack/events`.
   - Subscribe to desired bot events under **Subscribe to Bot Events** (if applicable).

### 3. Register Slash Commands
Navigate to **Features** > **Slash Commands** and click **Create New Command**:
- **Command:** `/profile`
- **Request URL:** `https://<your-ngrok-or-apigateway-url>/slack/events`
- **Short Description:** Manage or update your F3 RVA emergency contact information and start date.

---

## Production Deployment: AWS Lambda

AWS Lambda provides an ideal, highly cost-effective, zero-maintenance serverless hosting model.

### 1. Build & Package
To package the app for AWS Lambda (Python 3.12 runtime):
1. Package dependencies into a deployment zip file or container:
   ```bash
   pip install -r requirements.txt -t package/
   cp -r app.py config/ listeners/ services/ package/
   cd package && zip -r ../deployment.zip .
   ```
2. Upload `deployment.zip` to your AWS Lambda function.

### 2. Configure AWS Lambda environment
Define the environment variables in your AWS Lambda configuration:
- `SLACK_BOT_TOKEN`
- `SLACK_SIGNING_SECRET`
- `START_DATE_FIELD_ID`
- `EMERGENCY_CONTACT_PRIMARY_FIELD_ID`
- `EMERGENCY_CONTACT_BACKUP_FIELD_ID`
- `GOOGLE_SHEETS_SPREADSHEET_KEY`
- `GOOGLE_APPLICATION_CREDENTIALS=wif-credential-config.json` (Points to the keyless WIF configuration file bundled in your deployment package)
- `APP_ENV=production`

### 3. Expose via Amazon API Gateway
1. Create an **API Gateway (HTTP API)**.
2. Configure a `POST` route at `/slack/events` integration pointing to your AWS Lambda function.
3. Deploy the API and copy the Invoke URL to update Slack's Interactivity and Command Request URLs.
4. Set the AWS Lambda execution handler path to: `app.handler`.

---

## Testing

The project uses `pytest` and `pytest-mock` for unit and integration testing.

```bash
# Run the test suite
pytest tests/
```
