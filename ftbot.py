import janus

from config import *
from markov import MarkovAI
from messages import *

class FTBot(object):
    def __init__(self, loop):
        self.ai = MarkovAI()
        self.replyrate = CONFIG_DEFAULT_REPLYRATE
        self.reply = None
        self.shutup_flag = False
        self.message_queue = janus.Queue(loop=loop)
        self.reply_queue = janus.Queue(loop=loop)
        self.loop = loop

    def output(self, msg):
        if msg is None:
            return

        self.reply_queue.sync_q.put(msg)

    async def get_reply(self):
        return await self.reply_queue.async_q.get()

    def shutup(self, args):
        self.shutup_flag = True
        self.output(MessageOutput(text=CONFIG_MESSAGE_SHUTUP, channel=args['channel']))

    def wakeup(self, args):
        self.shutup_flag = False
        self.output(MessageOutput(text=CONFIG_MESSAGE_WAKEUP, channel=args['channel']))

    def process_message(self, msg):
        self.message_queue.sync_q.put(msg)

    def message_handler(self):
        while True:

            input_message = self.message_queue.sync_q.get()

            # Always reply when we are mentioned
            if input_message.args['mentioned'] and self.shutup_flag is False:
                self.ai.process_msg(self, input_message, 100)
            elif self.shutup_flag is False:
                self.ai.process_msg(self, input_message, self.replyrate)
            elif self.shutup_flag is True:
                self.ai.process_msg(self, input_message, 0)

