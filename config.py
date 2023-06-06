import os

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")  
SG_TOKEN = os.environ.get("SG_TOKEN")  

__all__ = ["DISCORD_TOKEN", "SG_TOKEN"]
