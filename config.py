import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_NAME = "rootv1"

DATA_DIR = os.getenv("DATA_DIR", "")
if DATA_DIR and not DATA_DIR.endswith(os.sep):
    DATA_DIR += os.sep

# Bot intents
INTENTS = {
    "message_content": True,
    "members": True,
    "moderation": True,
}
