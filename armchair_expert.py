import janus

from markov import MarkovAI
from messages import *


class IOModule(object):
    def __init__(self):
        pass

    def output(self, output_message: MessageOutput) -> None:
        pass

    def process_message(self, input_message: MessageInput) -> None:
        pass


class ArmchairExpert(IOModule):
    def __init__(self, event_loop, rebuild_pos_tree: bool = False):
        IOModule.__init__(self)
        self.ai = MarkovAI(rebuild_pos_tree=rebuild_pos_tree)
        self.replyrate = CONFIG_DEFAULT_REPLYRATE
        self.reply = None
        self.shutup_flag = False
        self.message_queue = janus.Queue(loop=event_loop)
        self.reply_queue = janus.Queue(loop=event_loop)
        self.event_loop = event_loop

    def output(self, output_message: MessageOutput) -> None:
        if output_message is None:
            return

        self.reply_queue.sync_q.put(output_message)

    async def get_reply(self):
        return await self.reply_queue.async_q.get()

    def shutup(self, args: dict) -> None:
        self.shutup_flag = True
        message_output = MessageOutput(text=CONFIG_MESSAGE_SHUTUP)
        message_output.args['channel'] = args['channel']
        self.output(message_output)

    def wakeup(self, args: dict) -> None:
        self.shutup_flag = False
        message_output = MessageOutput(text=CONFIG_MESSAGE_WAKEUP)
        message_output.args['channel'] = args['channel']
        self.output(MessageOutput(text=CONFIG_MESSAGE_WAKEUP))

    def process_message(self, input_message: MessageInput) -> None:
        self.message_queue.sync_q.put(input_message)

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
