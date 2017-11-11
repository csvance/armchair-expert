import asyncio
from concurrent import futures

from armchair_expert import *
from messages import *

client = discord.Client()


async def reply_queue_handler():
    await client.wait_until_ready()
    while not client.is_closed:
        output_message = await ftbot.get_reply()
        # TODO: Figure out this warning
        await client.send_message(output_message.args['channel'], output_message.message_filtered)


@client.event
@asyncio.coroutine
def on_message(message: discord.message.Message) -> None:
    # Prevent feedback loop / learning from ourself
    if str(message.author) == CONFIG_DISCORD_ME:
        return

    # Ignore messages in NSFW channels
    elif str(message.channel) in CONFIG_DISCORD_IGNORE_CHANNELS:
        return

    # Handle Comands
    if message.content.startswith("!"):

        command_message = MessageInputCommand(message=message)

        if message.content.startswith(CONFIG_COMMAND_TOKEN + 'shutup'):
            ftbot.shutup(command_message.args)
        elif message.content.startswith(CONFIG_COMMAND_TOKEN + 'wakeup'):
            ftbot.wakeup(command_message.args)
        elif message.content.startswith(CONFIG_COMMAND_TOKEN + 'replyrate'):
            try:
                ftbot.replyrate = int(message.content.split(" ")[1])
                yield from client.send_message(message.channel, "New reply rate: %s" % ftbot.replyrate)
            except KeyError:
                yield from client.send_message(message.channel, 'Command Syntax error.')

        else:
            ftbot.process_message(command_message)

    # Hand the message off to the markov layer
    else:
        ftbot.process_message(MessageInput(message=message))


print("Starting ArmchairExpert")
loop = asyncio.get_event_loop()
ftbot = ArmchairExpert(event_loop=loop)
print("Running Discord")
print("My join URL: https://discordapp.com/oauth2/authorize?&client_id=%d&scope=bot&permissions=0" % (
    CONFIG_DISCORD_BOTID))

pool = futures.ThreadPoolExecutor(1)
loop.run_in_executor(pool, client.run, CONFIG_DISCORD_TOKEN)

loop.create_task(reply_queue_handler())

ftbot.message_handler()
