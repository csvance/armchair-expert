import asyncio

from config import *
from ftbot import *

print("Starting FTBot")
ftbot = FTBot(loop=asyncio.get_event_loop())

ftbot.ai.rebuild_db(ignore=CONFIG_DISCORD_IGNORE_CHANNELS)
