import asyncio
import re

import discord
import logging
from config.discord import *
from connectors.connector_common import *
from storage.discord import DiscordTrainingDataManager
from common.discord import DiscordHelper
from spacy.tokens import Doc


class DiscordReplyGenerator(ConnectorReplyGenerator):
    def generate(self, message: str, doc: Doc = None) -> Optional[str]:

        reply = ConnectorReplyGenerator.generate(self, message, doc, ignore_topics=[DISCORD_USERNAME.split('#')[0]])

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
        self._logger = logging.getLogger(self.__class__.__name__)

    async def on_ready(self):
        self._ready = True
        self._logger.info(
            "Server join URL: https://discordapp.com/oauth2/authorize?&client_id=%d&scope=bot&permissions=0"
            % DISCORD_CLIENT_ID)

    async def on_message(self, message: discord.Message):
        # Prevent feedback loop
        if str(message.author) == DISCORD_USERNAME:
            return

        filtered_content = DiscordHelper.filter_content(message)

        learn = False
        # Learn from private messages
        if message.server is None and DISCORD_LEARN_FROM_DIRECT_MESSAGE:
            DiscordTrainingDataManager().store(message)
            learn = True
        # Learn from all server messages
        elif message.server is not None and DISCORD_LEARN_FROM_ALL:
            if str(message.channel) not in DISCORD_LEARN_CHANNEL_EXCEPTIONS:
                DiscordTrainingDataManager().store(message)
                learn = True
        # Learn from User
        elif str(message.author) == DISCORD_LEARN_FROM_USER:
            DiscordTrainingDataManager().store(message)
            learn = True

        # real-time learning
        if learn:
            self._worker.send(ConnectorRecvMessage(filtered_content, learn=True, reply=False))
            self._worker.recv()

        # Reply to mentions
        for mention in message.mentions:
            if str(mention) == DISCORD_USERNAME:
                self._logger.debug("Message: %s" % filtered_content)
                self._worker.send(ConnectorRecvMessage(filtered_content))
                reply = self._worker.recv()
                self._logger.debug("Reply: %s" % reply)
                if reply is not None:
                    await self.send_message(message.channel, reply)
                return

        # Reply to private messages
        if message.server is None:
            self._logger.debug("Private Message: %s" % filtered_content)
            self._worker.send(ConnectorRecvMessage(filtered_content))
            reply = self._worker.recv()
            self._logger.debug("Reply: %s" % reply)
            if reply is not None:
                await self.send_message(message.channel, reply)
            return


class DiscordWorker(ConnectorWorker):
    def __init__(self, read_queue: Queue, write_queue: Queue, shutdown_event: Event,
                 credentials: DiscordApiCredentials):
        ConnectorWorker.__init__(self, name='DiscordWorker', read_queue=read_queue, write_queue=write_queue,
                                 shutdown_event=shutdown_event)
        self._credentials = credentials
        self._client = None
        self._logger = None

    async def _watchdog(self):
        while True:
            await asyncio.sleep(0.2)

            if self._shutdown_event.is_set():
                self._logger.info("Got shutdown signal.")
                await self._client.close()
                return

    def run(self):
        from storage.discord import DiscordTrainingDataManager
        self._logger = logging.getLogger(self.__class__.__name__)
        self._db = DiscordTrainingDataManager()
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
