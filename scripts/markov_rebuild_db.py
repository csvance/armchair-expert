import asyncio

from config import *
from armchair_expert import ArmchairExpert

if __name__ == '__main__':

    ftbot = ArmchairExpert(event_loop=asyncio.get_event_loop())

    if CONFIG_DISCORD_MINI_ME is None:
        ftbot.ai.rebuild_db(ignore=CONFIG_DISCORD_IGNORE_CHANNELS)
    else:
        ftbot.ai.rebuild_db(ignore=CONFIG_DISCORD_IGNORE_CHANNELS,author=[CONFIG_DISCORD_MINI_ME])
