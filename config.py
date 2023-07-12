import os

# These environment variables are managed by the cloud infrastructure, and imported from there
DISCORD_TOKEN   = os.environ.get("DISCORD_TOKEN")
SG_TOKEN        = os.environ.get("SG_TOKEN")

__all__         = ["DISCORD_TOKEN", "SG_TOKEN"]
