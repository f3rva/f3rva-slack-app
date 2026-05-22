# F3 RVA Slack App

A monolithic Slack application designed for the `f3-rva-workspace.slack.com` workspace. 

Operating under the Slack free tier, this application acts as a single centralized "monolith" that routes all custom F3 RVA workspace functionalities (slash commands, events, interactive actions, and shortcuts) through a single bot instance.

The application is written in **Python 3.12+** using the official **Slack Bolt for Python** framework.

---

## Features

1. **Emergency Contact Manager (Initial Feature)**
   - Allows members (PAX) to view, add, or update custom emergency contact fields in their Slack profile using interactive modals.
   - Leverages Slack's Custom Profile Fields to store emergency contact name, relationship, phone number, and medical notes securely.
2. **Monolithic Extensibility**
   - Built with a decoupled listener-router architecture, making it simple to plug in new commands, event listeners, or interactive workflows as the workspace grows.

---

## Technical Stack

- **Language:** Python 3.12+
- **Framework:** Slack Bolt for Python (`slack-bolt`)
- **Local Dev Connection:** Socket Mode (bypasses firewalls and avoids public URL exposure like `ngrok`)
- **HTTP Hosting (Production):** Compatible with WSGI/ASGI web servers (e.g., Gunicorn + FastAPI/Flask) if HTTP-mode is desired in the future.

---

## Directory Structure

```text
f3rva-slack-app/
├── README.md               # Developer setup and Slack config guide
├── GEMINI.md               # AI agent styling, architecture, and coding guardrails
├── requirements.txt        # Python dependency manifest
├── app.py                  # Entrypoint. Initializes Bolt App & starts listener server
├── config/                 # Configuration and settings loader
│   ├── __init__.py
│   └── settings.py
├── listeners/              # Routing & listener handlers (decoupled from server setup)
│   ├── __init__.py         # Central router registering sub-listeners to the App
│   ├── actions.py          # Handles interactive block events (button clicks, menu selects)
│   ├── commands.py         # Handles Slash commands (e.g., `/emergency-contact`)
│   ├── events.py           # Handles Slack events (e.g., channel joins, profile changes)
│   ├── shortcuts.py        # Handles global and message shortcuts
│   └── views.py            # Handles modal submissions (form validation and saves)
├── services/               # Core business logic layer (independent of the Slack framework)
│   ├── __init__.py
│   ├── slack_profile.py    # Service for reading/writing custom fields in users' profiles
│   └── database.py         # Interface for auxiliary datastores if needed
└── tests/                  # Test suite
    ├── __init__.py
    ├── test_listeners.py
    └── test_services.py
```

---

## Quickstart: Local Development

### 1. Prerequisites
- Python 3.12 or newer installed locally.
- Git.
- Admin access (or App Manager privileges) in the `f3-rva-workspace` Slack workspace to configure the application.

### 2. Clone and Setup Environment
```bash
# Clone the repository (if not already local)
git clone git@github.com:f3rva/f3rva-slack-app.git
cd f3rva-slack-app

# Create a virtual environment
python3 -m venv .venv

# Activate the virtual environment
# On macOS/Linux:
source .venv/bin/activate
# On Windows:
# .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
# Bot User OAuth Token (xoxb-...)
SLACK_BOT_TOKEN=xoxb-your-bot-token

# App-level Token (xapp-...) required for Socket Mode
SLACK_APP_TOKEN=xapp-your-app-level-token

# Field IDs for Custom Profile Fields (obtained from Slack Admin UI)
EMERGENCY_CONTACT_NAME_FIELD_ID=XF0123ABCD
EMERGENCY_CONTACT_PHONE_FIELD_ID=XF4567EFGH
EMERGENCY_CONTACT_RELATION_FIELD_ID=XF8901IJKL
EMERGENCY_CONTACT_MED_NOTES_FIELD_ID=XF2345MNOP

# App Environment (development, production)
APP_ENV=development
```

### 4. Run the App Locally
```bash
python app.py
```
*Note: Since the app utilizes Socket Mode, it establishes a secure WebSocket connection directly with Slack's servers. You do not need to configure public IP forwarding or run `ngrok`.*

---

## Slack App Configuration Guide (api.slack.com)

To connect this codebase to the F3 RVA Slack workspace, configure your app on the [Slack API Portal](https://api.slack.com/apps) with the following settings:

### 1. Enable Socket Mode
1. Navigate to **Basic Information** > **App-Level Tokens**.
2. Click **Generate Token and Scopes**, choose the `connections:write` scope, and name the token (e.g., `f3rva-socket-mode-token`). Save the generated token as `SLACK_APP_TOKEN` in your `.env`.
3. In the left-hand sidebar, go to **Settings** > **Socket Mode** and toggle **Enable Socket Mode** to `On`.

### 2. Configure Scopes (OAuth & Permissions)
Navigate to **Features** > **OAuth & Permissions** and add the following **Bot Token Scopes**:
- `commands`: Allows the bot to register and handle custom slash commands.
- `users.profile:read`: Allows the bot to view users' profiles (needed to pre-populate current emergency contact details).
- `users.profile:write`: Allows the bot to modify users' profiles (needed to write updated emergency contact details).
- `users:read`: Allows the bot to fetch list data and general info about workspace members.

Install the app to the workspace after configuring these scopes to generate the `SLACK_BOT_TOKEN` (starts with `xoxb-`).

### 3. Create Custom Profile Fields (Slack Admin Console)
Because Slack does not have native emergency contact fields, you must create them as an administrator:
1. Go to your Slack Workspace Admin settings (`f3-rva-workspace.admin.slack.com`).
2. Navigate to **Workspace Settings** > **Customize [Workspace Name]** > **Profile Fields**.
3. Create custom text fields for:
   - **Emergency Contact Name**
   - **Emergency Contact Phone**
   - **Emergency Contact Relationship**
   - **Medical/Important Notes**
4. To retrieve the unique **Field IDs** for your `.env` configuration, either:
   - Inspect the network requests when updating your profile in the browser.
   - Run a test script using the `users.profile.get` API method with your bot token to inspect the profile payload of a user. The custom fields will appear under `fields` in format `XFXXXXXXX`.

### 4. Register Slash Commands
Navigate to **Features** > **Slash Commands** and click **Create New Command**:
- **Command:** `/emergency-contact`
- **Short Description:** Manage or update your F3 RVA emergency contact information.
- **Usage Hint:** `[edit / view]`

### 5. Enable Interactivity
Navigate to **Features** > **Interactivity & Shortcuts** and toggle it to **On**.
*(Since Socket Mode is enabled, you do not need to provide a Request URL. Slack will route interactive actions over the socket connection).*

---

## Monolithic Extensibility: Adding New Features

The repository scales as a monolith by separating listener definitions from application startup. To add a new command, event, or button action:

### 1. Implement Listener Logic
Add your handler inside the appropriate module under `listeners/`. For example, to add a new command handler in `listeners/commands.py`:
```python
import logging
from slack_bolt import Ack

logger = logging.getLogger(__name__)

def handle_q_signups(ack: Ack, body: dict, say: callable):
    """Handles the /q-signup slash command."""
    ack()  # Always acknowledge the command immediately!
    user_id = body.get("user_id")
    say(text=f"Hey <@{user_id}>! Here is the link to the Q-sheet signups: [Link]")
```

### 2. Register the Listener
Hook the handler up to the App in `listeners/__init__.py`:
```python
from slack_bolt import App
from listeners.commands import handle_q_signups

def register_listeners(app: App) -> None:
    # Existing registrations...
    app.command("/emergency-contact")(handle_emergency_command)
    
    # New registrations
    app.command("/q-signup")(handle_q_signups)
```

By decoupling registration, `app.py` remains a clean, small entrypoint focused entirely on environment loading and server startup.

---

## Testing

The project uses `pytest` for unit and integration tests. Tests should mock the Slack Bolt SDK to verify that services process business logic safely and correct responses are formulated.

```bash
# Run tests
pytest
```
