from ftbot import *
import discord
import asyncio
from config import *
import re
client = discord.Client()

def discord_client_run():
    client.run(CONFIG_DISCORD_TOKEN)

@client.event
@asyncio.coroutine
def on_message(message):

    if str(message.author) == CONFIG_DISCORD_ME:
        return

    #Handle Comands
    if message.content.startswith("!"):
        if message.content.startswith('!shutup'):
            ftbot.shutup()
            yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
            ftbot.reply = None
        elif message.content.startswith('!wakeup'):
            ftbot.wakeup()
            yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
            ftbot.reply = None
        elif message.content.startswith('!replyrate'):
            newrate = 0
            try:
                ftbot.replyrate = int(message.content.split(" ")[1])
                yield from client.send_message(message.channel, "New reply rate: %s" % ftbot.replyrate)
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')
        elif message.content.startswith("!meme"):
            try:
                meme = message.content.split("!meme")[1]
                if(len(meme) > 2):
                    ftbot.memegen(meme, {'channel': message.channel})
                    if(ftbot.reply != None):
                        yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                        ftbot.reply = None
                else:
                    yield from client.send_message(message.channel, 'Command Syntax error.')
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')
        else:
            if str(message.author) == CONFIG_DISCORD_OWNER:
                ftbot.process_message(message.content, {'channel': message.channel},is_owner=True)
            else:
                ftbot.process_message(message.content, {'channel': message.channel},is_owner=False)
            if ftbot.reply != None:
                yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                ftbot.reply = None
    else:
        for msg in message.content.split("\n"):

            mentioned = False
            if msg.find(CONFIG_DISCORD_MENTION_ME) != 1:
                mentioned = True

            ftbot.process_message(msg,{'channel': message.channel},mentioned=mentioned)
            if ftbot.reply != None:
                yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                ftbot.reply = None

print("Starting FTBot")
ftbot = FTBot()
print("Running Discord")
discord_client_run()
