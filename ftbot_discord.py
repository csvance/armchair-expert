from ftbot import *
import discord
import asyncio
from config import *
client = discord.Client()

def discord_client_run():
    client.run(CONFIG_DISCORD_TOKEN)

@client.event
@asyncio.coroutine
def on_message(message):
    #Handle Comands
    if message.content.startswith("!"):
        if message.content.startswith('!shutup'):
            ftbot.shutup = True
            yield from client.send_message(message.channel, "I can't wait for you to shut me up")
        elif message.content.startswith('!wakeup'):
            ftbot.shutup = False
            yield from client.send_message(message.channel, "Im awake as @Devices is a cuck")
        elif message.content.startswith('!replyrate'):
            newrate = 0
            try:
                ftbot.replyrate = int(message.content.split(" ")[1])
                yield from client.send_message(message.channel, "New reply rate: %s" % ftbot.replyrate)
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')
        else:
            ftbot.process_message(message.content, {'channel': message.channel})
            if(ftbot.reply != None):
                yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
                ftbot.reply = None
    else:
        ftbot.process_message(message.content,{'channel': message.channel})
        if (ftbot.reply != None):
            yield from client.send_message(ftbot.reply['channel'], ftbot.reply['message'])
            ftbot.reply = None

print("Starting FTBot")
ftbot = FTBot()
print("Running Discord")
discord_client_run()
