from config import *
from search import *
import janus

from markov import MarkovAI

class FTBot(object):
    def __init__(self,loop):
        self.ai = MarkovAI()
        self.replyrate = CONFIG_DEFAULT_REPLYRATE
        self.reply = None
        self.shutup = False
        self.message_queue = janus.Queue(loop=loop)
        self.reply_queue = janus.Queue(loop=loop)
        self.loop = loop

    def output(self, msg, args):
        if msg is None:
            return
        self.reply_queue.sync_q.put({'channel': args['channel'], 'message': msg})

    async def get_reply(self):
        return await self.reply_queue.async_q.get()

    def shutup(self, args):
        self.shutup = True
        self.output(CONFIG_MESSAGE_SHUTUP, args)

    def wakeup(self, args):
        self.shutup = False
        self.output(CONFIG_MESSAGE_WAKEUP, args)

    def process_message(self, message, args):
        self.message_queue.sync_q.put({'message': message,'args': args})

    def message_handler(self):
        while True:

            task = self.message_queue.sync_q.get()

            message = task['message']
            args = task['args']

            # Always reply when we are mentioned
            if args['mentioned'] and self.shutup is False:
                self.ai.process_msg(self, message, 100, args)
            elif self.shutup is False:
                self.ai.process_msg(self, message, self.replyrate, args)
            else:
                self.ai.process_msg(self, message, 0, args)



