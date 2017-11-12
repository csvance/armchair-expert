import discord
import sys
from markov_schema import *
from armchair_expert_discord import replace_mention_with_nick,client


async def fix_ids():
    session = Session()

    for line in session.query(Line).filter(Line.text.like('%<%')).all():
        line.text = await replace_mention_with_nick(line.text)
        print(line.text)
        session.commit()

    sys.exit(0)