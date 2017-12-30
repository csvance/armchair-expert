import asyncio
import re

import discord

from config.discord import *
from connectors.connector_common import *


class DiscordReplyGenerator(ConnectorReplyGenerator):
    def generate(self, message: str):
        reply = ConnectorReplyGenerator.generate(self, message)

        if reply is None:
            return None

        if DISCORD_REMOVE_URL:
            # Remove URLs
            reply = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', reply)
            reply = reply.strip()

        if len(reply) > 0:
            return reply
        else:
            return None


class DiscordClient(discord.Client):
    def __init__(self, worker: 'DiscordWorker'):
        discord.Client.__init__(self)
        self._worker = worker
        self._ready = False

    async def on_ready(self):
        self._ready = True
        print(
            "Discord Server Join URL: https://discordapp.com/oauth2/authorize?&client_id=%d&scope=bot&permissions=0"
            % DISCORD_CLIENT_ID)

    async def on_message(self, message: discord.Message):
        # Prevent feedback loop
        if str(message.author) == DISCORD_USERNAME:
            return

        # Replace mentions with names
        filtered_content = message.content
        for mention in message.mentions:
            if mention.nick is not None:
                replace_name = mention.nick
            else:
                replace_name = mention.name
            replace_id = mention.id
            replace_tag = "<@%s>" % replace_id
            filtered_content = filtered_content.replace(replace_tag, replace_name)

        # Reply to mentions
        for mention in message.mentions:
            if str(mention) == DISCORD_USERNAME:
                self._worker.send(filtered_content)
                reply = self._worker.recv()
                if reply is None:
                    return
                await self.send_message(message.channel, reply)
                return

        # Reply to private messages
        if message.server is None:
            self._worker.send(filtered_content)
            reply = self._worker.recv()
            if reply is None:
                return
            await self.send_message(message.channel, reply)
            return


class DiscordWorker(ConnectorWorker):
    def __init__(self, read_queue: Queue, write_queue: Queue, shutdown_event: Event,
                 credentials: DiscordApiCredentials):
        ConnectorWorker.__init__(self, name='DiscordWorker', read_queue=read_queue, write_queue=write_queue,
                                 shutdown_event=shutdown_event)
        self._credentials = credentials
        self._client = None

    async def _watchdog(self):
        while True:
            await asyncio.sleep(0.2)

            if self._shutdown_event.is_set():
                await self._client.close()
                return

    def run(self):
        self._client = DiscordClient(self)
        self._client.loop.create_task(self._watchdog())
        self._client.run(self._credentials.token)


class DiscordScheduler(ConnectorScheduler):
    def __init__(self, shutdown_event: Event, credentials: DiscordApiCredentials):
        ConnectorScheduler.__init__(self, shutdown_event)
        self._worker = DiscordWorker(read_queue=self._write_queue, write_queue=self._read_queue,
                                     shutdown_event=shutdown_event, credentials=credentials)


class DiscordFrontend(Connector):
    def __init__(self, reply_generator: DiscordReplyGenerator, connectors_event: Event,
                 credentials: DiscordApiCredentials):
        Connector.__init__(self, reply_generator=reply_generator, connectors_event=connectors_event)
        self._scheduler = DiscordScheduler(self._shutdown_event, credentials)