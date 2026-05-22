import logging
from typing import Dict, Any
from slack_bolt import Ack
from slack_sdk.web import WebClient

logger = logging.getLogger(__name__)

# Placeholder module for handling global or message shortcuts
# (e.g. initiating profile updates via a drop-down menu on a user message)
#
# To register a new shortcut handler:
# 1. Implement acknowledge_shortcut and process_shortcut handlers here.
# 2. Map in listeners/__init__.py: app.shortcut("shortcut_id")(ack=..., lazy=[...])
