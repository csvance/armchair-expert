import asyncio

from config import *
from armchair_expert import ArmchairExpert

if __name__ == '__main__':

    ftbot = ArmchairExpert(event_loop=asyncio.get_event_loop())

    ftbot.ai.rebuild_db(ignore=CONFIG_DISCORD_IGNORE_CHANNELS)