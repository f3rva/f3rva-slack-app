import os

# Populate static dummy environment variables for config module verification during testing
os.environ["SLACK_BOT_TOKEN"] = "xoxb-mock-bot-token-value"
os.environ["SLACK_SIGNING_SECRET"] = "mock-slack-signing-secret-value"
os.environ["START_DATE_FIELD_ID"] = "XF_START_DATE_MOCK"
os.environ["EMERGENCY_CONTACT_PRIMARY_FIELD_ID"] = "XF_PRIMARY_MOCK"
os.environ["EMERGENCY_CONTACT_BACKUP_FIELD_ID"] = "XF_BACKUP_MOCK"
os.environ["GOOGLE_SHEETS_SPREADSHEET_KEY"] = "mock-spreadsheet-key"
os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"] = '{"type": "service_account", "project_id": "mock-project"}'
os.environ["APP_ENV"] = "testing"

