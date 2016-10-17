from ftbot import *
import discord
import asyncio
from config import *
import extras
import re

client = discord.Client()


def discord_client_run():
    client.run(CONFIG_DISCORD_TOKEN)


@client.event
@asyncio.coroutine
def on_message(message):

    if str(message.author) == CONFIG_DISCORD_ME:
        return

    if str(message.channel) in CONFIG_DISCORD_IGNORE_CHANNELS:
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
            'server': server}

    # Handle Comands
    if message.content.startswith("!"):

        processed = False

        if message.content.startswith('!shutup'):
            ftbot.shutup()
            yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
            ftbot.reply = None
            processed = True
        elif message.content.startswith('!wakeup'):
            ftbot.wakeup(args)
            yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
            ftbot.reply = None
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
                    if ftbot.reply is not None:
                        yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                        ftbot.reply = None
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
                ftbot.process_message(message.content, args, is_owner=True)
            else:
                ftbot.process_message(message.content, args, is_owner=False)
            if ftbot.reply is not None:
                yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                ftbot.reply = None
    else:
        for msg in message.content.split("\n"):

            mentioned = False
            if msg.find(CONFIG_DISCORD_MENTION_ME) != -1:
                mentioned = True

            # Treat mentioning another user as a single word
            msg = re.sub(r'<@[0-9]+>', '#nick', msg)

            ftbot.process_message(msg, args, mentioned=mentioned)
            if ftbot.reply is not None:
                yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                ftbot.reply = None


print("Starting FTBot")
ftbot = FTBot()
print("Running Discord")
discord_client_run()
