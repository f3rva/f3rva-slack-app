import os

# Populate static dummy environment variables for config module verification during testing
os.environ["SLACK_BOT_TOKEN"] = "xoxb-mock-bot-token-value"
os.environ["EMERGENCY_CONTACT_PRIMARY_FIELD_ID"] = "XF_PRIMARY_MOCK"
os.environ["EMERGENCY_CONTACT_BACKUP_FIELD_ID"] = "XF_BACKUP_MOCK"
os.environ["EMAIL_SENDER_SOURCE"] = "admin@f3rva.org"
os.environ["APP_ENV"] = "testing"


