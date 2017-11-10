import asyncio
import re
from concurrent import futures

import discord
import spacy
from config import *
from ftbot import *
from messages import *

client = discord.Client()


async def reply_queue_handler():
    await client.wait_until_ready()
    while not client.is_closed:
        output_message = await ftbot.get_reply()
        await client.send_message(output_message.args['channel'], output_message.message_filtered)


@client.event
@asyncio.coroutine
def on_message(message):

    # Prevent feedback loop / learning from ourself
    if str(message.author) == CONFIG_DISCORD_ME:
        return

    # Ignore messages in NSFW channels
    elif str(message.channel) in CONFIG_DISCORD_IGNORE_CHANNELS:
        return

    input_message = MessageInput(message=message)

    # Handle Comands
    if message.content.startswith("!"):

        processed = False

        if message.content.startswith('!shutup'):
            ftbot.shutup(input_message.args)
            processed = True
        elif message.content.startswith('!wakeup'):
            ftbot.wakeup(input_message.args)
            processed = True
        elif message.content.startswith('!replyrate'):
            try:
                ftbot.replyrate = int(message.content.split(" ")[1])
                yield from client.send_message(message.channel, "New reply rate: %s" % ftbot.replyrate)
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')
            processed = True

        # If the command was not handled
        if not processed:
            yield from client.send_message(message.channel, "Unknown Command: %s" % message.content)
            return

    # Hand the message off to the markov layer
    else:
        ftbot.process_message(input_message)



print("Starting FTBot")
loop = asyncio.get_event_loop()
ftbot = FTBot(loop=loop)
print("Running Discord")
print("My join URL: https://discordapp.com/oauth2/authorize?&client_id=%d&scope=bot&permissions=0" % (
CONFIG_DISCORD_CLIENT_ID))

pool = futures.ThreadPoolExecutor(1)
loop.run_in_executor(pool, client.run, CONFIG_DISCORD_TOKEN)

loop.create_task(reply_queue_handler())

ftbot.message_handler()