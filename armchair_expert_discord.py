import asyncio
from concurrent import futures

from armchair_expert import *
from messages import *
import sys

client = discord.Client()

# Prevent duplicate lookups for the same information
user_id_cache = {}

people = []

async def get_member_list():

    names = []

    for server in client.servers:
        for member in server.members:
            names.append(member.name.lower())

    return names


async def replace_mention_with_nick(content: str):
    message = content

    user_ids = re.findall(r'<@[!]?([0-9]+)>', message)
    for user_id in user_ids:
        if user_id in user_id_cache:
            user = user_id_cache[user_id]
        else:
            user = await client.get_user_info(int(user_id))
            user_id_cache[user_id] = user
        message = re.sub(r'<@[!]?[0-9]+>', user.name, message)

    return message


async def reply_queue_handler():
    await client.wait_until_ready()
    while not client.is_closed:
        output_message = await ftbot.get_reply()
        # TODO: Figure out this warning
        await client.send_message(output_message.args['channel'], output_message.message_filtered)


@client.event
@asyncio.coroutine
def on_message(message: discord.Message) -> None:
    global people

    # Prevent feedback loop / learning from ourself
    if str(message.author) == CONFIG_DISCORD_ME:
        return

    # Ignore messages in NSFW channels
    elif str(message.channel) in CONFIG_DISCORD_IGNORE_CHANNELS:
        return

    # Replace mentions with nicknames
    message.content = yield from replace_mention_with_nick(message.content)

    # Get the latest user list
    people = yield from get_member_list()

    # Handle Comands
    if message.content.startswith("!"):

        command_message = MessageInputCommand(message=message,people=people)

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
        ftbot.process_message(MessageInput(message=message, people=people))


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
