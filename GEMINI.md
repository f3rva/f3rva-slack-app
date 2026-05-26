# Gemini Agent Instructions for F3 RVA Slack App

This document provides comprehensive instructions, architectural guardrails, coding conventions, and best practices for developing and maintaining the `f3rva-slack-app` repository. 

As a monolithic Slack app on the free tier, developers and AI agents must adhere strictly to these patterns to ensure scalability, responsiveness, and clean division of concerns.

---

## 1. Project Overview

**F3 RVA Slack App** is a monolithic Slack application designed for the `f3-rva-workspace.slack.com` workspace. 
It consolidates all custom F3 RVA workspace automations into a single app instance.
- **Initial Core Feature:** Allow members to manage their custom emergency contact profile fields via interactive Block Kit modals.
- **Long-term Goal:** Build a highly modular framework that can host additional slash commands, message shortcuts, and event listeners without architectural degradation.

---

## 2. Technology Stack

- **Core Framework:** Slack Bolt for Python 1.20+ (`slack-bolt`)
- **Language:** Python 3.12+ (Strict typing enforced)
- **Environment Management:** `python-dotenv` for configuration loading
- **Connection Mode:** HTTP Webhook Mode (deprecating Socket Mode) via `app.start(port=3001)` locally (configurable via PORT env var) and AWS Lambda `AwsLambdaHandler` in production
- **Database Backend:** Google Sheets API using `gspread` and `google-auth`
- **Testing:** `pytest` and `pytest-mock` for testing services and listener handlers

---

## 3. Project Structure

AI agents must preserve and respect the following directory structure:

```text
src/
├── config/                 # Configurations, environment variable parser, constant definitions
│   ├── __init__.py
│   └── settings.py         # Loads and validates SLACK_* tokens, custom field IDs, and Google Sheets config
├── listeners/              # Slack event, command, action, and modal routing layer
│   ├── __init__.py         # Registers listeners onto the central Bolt App instance
│   ├── actions.py          # Handles interactive block elements (e.g. button clicks)
│   ├── commands.py         # Handles slash commands (e.g. /profile)
│   ├── events.py           # Handles event subscriptions (e.g. app_mention, member_joined_channel)
│   ├── shortcuts.py        # Handles global and message shortcuts
│   └── views.py            # Handles modal submissions and user form confirmations
├── services/               # Core business logic layer (Free of Slack-specific transport details)
│   ├── __init__.py
│   ├── slack_profile.py    # Manages Fetch-and-Seed cache lookup & Google Sheet updates
│   └── database.py         # GoogleSheetsService backend using gspread and service account auth
└── tests/                  # Test suite mirroring the application structure
    ├── __init__.py
    ├── test_listeners.py
    └── test_services.py
app.py                      # Server entrypoint. Standard HTTP webhook dev server and dynamic AWS Lambda handler
requirements.txt            # Dependency manifest (includes gspread, google-auth, boto3)
```

---

## 4. Coding & Architectural Conventions

To maintain codebase sanity, follow these strict development rules:

### A. The "Thin Listeners" Rule
Listeners (found under `listeners/`) must remain extremely lightweight. They act purely as controllers:
1. **Acknowledge** the Slack request instantly (see Slack-specific guidelines below).
2. **Extract** relevant parameters from the payload (e.g., `user_id`, `trigger_id`, form values).
3. **Delegate** all business logic, database queries, and profile modifications to the `services/` layer.
4. **Respond** to the user (e.g., open a modal, send an ephemeral message, or update a block view) based on the service's output.

*Never put raw Slack API profile update calls, database connections, or validation logic directly inside a listener callback.*

### B. Descriptive and Narrative Naming
Follow clean-code naming conventions. Favor clear, descriptive, narrative-like variable and function names over short or cryptic ones:
- **Good:** `retrieve_user_emergency_contact_profile_data()`
- **Bad:** `get_profile()`, `emergency_info()`
- **Good:** `is_user_emergency_contact_field_empty`
- **Bad:** `is_empty`, `check_field`

### C. Strict Type Hinting
All code must be statically typed. Define types for all function signatures (arguments and return types) using Python's `typing` module:
```python
from typing import Dict, Any, Optional
from slack_sdk.web import WebClient

def get_custom_profile_fields(
    client: WebClient, 
    user_id: str
) -> Dict[str, Optional[str]]:
    # ...
```
Avoid using `Any` where possible. Declare detailed typing models or classes if dealing with highly structured custom data structures.

### D. Google Sheets Caching & Seeding Strategy
To bypass Slack profile write restrictions on the free tier, our backend storage has pivoted entirely to Google Sheets.
1. **Caching/Database of Record:** The Google Sheet is the database of record for member profile information (Start Date, Primary/Backup Contacts).
2. **Fetch-and-Seed Migration:** When a user's record is requested:
   - The application checks Google Sheets first.
   - If found, it returns the cached values immediately without calling Slack API, improving performance and conserving API rate limits.
   - If not found (first view), the app retrieves their display name and existing custom profile fields from Slack using the Bot token (which is allowed), seeds a new row in Google Sheets, and saves it.
3. **Subsequent Updates:** All subsequent profile updates are written directly to Google Sheets, keeping the local profile fields untouched.

---

## 5. Slack-Specific Development Guidelines

Working with the Slack API introduces unique constraints that must be handled correctly:

### A. The 3-Second Acknowledgment Rule (`ack()`)
Slack requires that all slash commands, block actions, shortcuts, and modal submissions be acknowledged **within 3.0 seconds**. If your application takes longer, Slack will show a timeout error to the user.
- **Rule:** The very first line of code in any command, action, shortcut, or view submission listener **MUST** be `ack()`.
- **Heavy Operations:** If a listener needs to perform a heavy operation (like writing to a slow DB or making an external HTTP call), use **Lazy Listeners** or offload the execution to a thread/process pool.

#### Example: Using Lazy Listeners in Bolt
Bolt for Python supports lazy listeners natively, which automatically handles running the acknowledgment and heavy logic in separate threads:
```python
from slack_bolt import Ack

# 1. Acknowledgment function (runs immediately within 3s)
def acknowledge_emergency_command(ack: Ack) -> None:
    ack()

# 2. Lazy execution function (runs asynchronously)
def process_emergency_command(body: dict, client: WebClient) -> None:
    trigger_id = body["trigger_id"]
    # Open the Modal or perform slow profile query here...
    client.views_open(trigger_id=trigger_id, view={...})

# 3. Registration
app.command("/emergency-contact")(
    ack=acknowledge_emergency_command,
    lazy=[process_emergency_command]
)
```

### B. Block Kit Form State Management
When users submit modals or forms built with Slack Block Kit:
- Form inputs must reside within an `input` block.
- Values must be retrieved by indexing the `view["state"]["values"]` object using the `block_id` and the `action_id`.
- Ensure all blocks and input elements have explicit, hardcoded `block_id` and `action_id` values. Do **not** let Slack auto-generate IDs, as they will randomize on every render and break data extraction.

### C. Graceful User Notifications & Ephemeral Messages
- When actions succeed or fail, do not spam channels. 
- Use **ephemeral messages** (`client.chat_postEphemeral`) to notify only the interacting user of errors or progress.
- Catch `SlackApiError` in every listener, log the raw trace in internal system logs, and show a clean, user-friendly Block Kit error modal to the user.

### D. Data Privacy & Log Filtering
Custom profile fields for emergency contacts contain Personally Identifiable Information (PII) and protected details (like medical notes, relationships, and phone numbers).
- **Rule:** Never print or write user emergency contact values, phone numbers, or notes to the standard system output or log files.
- **Rule:** Only log structural event data (e.g. `"Updating emergency contact fields for user U12345"`).

---

## 6. DevOps & Workflow Rules

1. **Branch Naming Conventions:**
   - All new features must be developed on a dedicated feature branch starting with: `feature/<feature-name>` (e.g., `feature/emergency-contact-modal`).
   - Bug fixes must use: `bug/<bug-name>` (e.g., `bug/fix-timeout-on-ack`).
   - Automated agent scripts/commits must use: `bot/<description>` (e.g., `bot/update-gemini-docs`).
2. **Environment Variable Safeguards:**
   - Never commit `.env` or plain token secrets. Ensure `.env` is listed inside `.gitignore`.
   - Access all environment variables exclusively via `config.settings`, which performs type casting, validation, and raises descriptive `ValueError` exceptions on startup if critical tokens are missing.
3. **Test-Driven Mentality:**
   - Every service logic component in `services/` must have a corresponding test suite in `tests/`.
   - Mock all network-level Bolt `WebClient` API calls using `pytest-mock` to guarantee fast, deterministic tests.
