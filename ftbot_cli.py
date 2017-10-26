from ftbot import *
from config import *

print("Starting FTBot")
ftbot = FTBot()

ftbot.ai.rebuild_db(ignore=CONFIG_DISCORD_IGNORE_CHANNELS)
