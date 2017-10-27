from ftbot import *
import discord
import asyncio
from config import *
import extras
import re
from concurrent import futures

client = discord.Client()


async def reply_queue_handler():
    await client.wait_until_ready()
    while not client.is_closed:
        reply = await ftbot.get_reply()
        await client.send_message(reply['channel'], reply['message'])

@client.event
@asyncio.coroutine
def on_message(message):
    if str(message.author) == CONFIG_DISCORD_ME:
        return

    if str(message.channel) in CONFIG_DISCORD_IGNORE_CHANNELS:
        print("--NSFW FILTER--")
        return

    channel = message.channel
    author = message.author
    try:
        server = message.channel.server.id
    except AttributeError:
        # Private Message
        server = 0

    args = {'channel': channel,
            'author': str(author),
            'author_mention': "<@%s>" % author.id,
            'server': server,
            'mentioned': False}

    # Handle Comands
    if message.content.startswith("!"):

        processed = False

        if message.content.startswith('!shutup'):
            ftbot.shutup()
            processed = True
        elif message.content.startswith('!wakeup'):
            ftbot.wakeup(args)
            processed = True
        elif message.content.startswith('!replyrate'):
            try:
                ftbot.replyrate = int(message.content.split(" ")[1])
                yield from client.send_message(message.channel, "New reply rate: %s" % ftbot.replyrate)
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')
            processed = True
        elif message.content.startswith("!meme"):
            try:
                meme = message.content.split("!meme")[1]
                if len(meme) > 2:
                    ftbot.memegen(meme, {'channel': message.channel})
                else:
                    yield from client.send_message(message.channel, 'Command Syntax error.')
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')
            processed = True
        elif message.content.startswith("!"):
            ret_msg = extras.command_router(message.content)
            if ret_msg != "No such command!":
                processed = True
                yield from client.send_message(message.channel, ret_msg)

        if not processed:
            if str(message.author) == CONFIG_DISCORD_OWNER:
                args['is_owner'] = True
                ftbot.process_message(message.content, args)
            else:
                args['is_owner'] = False
                ftbot.process_message(message.content, args)
    else:
        for msg in message.content.split("\n"):

            if msg.find(CONFIG_DISCORD_MENTION_ME) != -1:
                args['mentioned'] = True
            else:
                args['mentioned'] = False

            # Treat mentioning another user as a single word
            msg = re.sub(r'<@[!]?[0-9]+>', '#nick', msg)

            # Don't learn from private messages
            if message.server is not None:
                args['learning'] = True
                ftbot.process_message(msg, args)
            else:
                args['learning'] = False
                ftbot.process_message(msg, args)

loop = asyncio.get_event_loop()

print("Starting FTBot")
ftbot = FTBot(loop=loop)
print("Running Discord")
print("My join URL: https://discordapp.com/oauth2/authorize?&client_id=%d&scope=bot&permissions=0" % (CONFIG_DISCORD_CLIENT_ID))

pool = futures.ThreadPoolExecutor(4)

loop.run_in_executor(pool,ftbot.message_handler)
loop.create_task(reply_queue_handler())
client.run(CONFIG_DISCORD_TOKEN)

