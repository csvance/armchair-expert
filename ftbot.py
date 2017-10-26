from config import *
from search import *
from memegen import *
import time

from markov import MarkovAI


def run_async(func):
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


class FTBot(object):
    def __init__(self):
        self.ai = MarkovAI()
        self.replyrate = CONFIG_DEFAULT_REPLYRATE
        self.reply = None
        self.shutup = False

    def output(self, msg, args):
        if msg is None:
            self.reply = None
            return

        self.reply = {'channel': args['channel'], 'message': msg}

    def memegen(self, msg, args):
        filename = "%s/meme_%s.jpg" % (CONFIG_SERVE_DIR, random.randint(0, 9999999))
        resource = GoogleImages(msg, CONFIG_GOOGLE_KEY, CONFIG_GOOGLE_CX).execute(CONFIG_DOWNLOAD_DIR)
        if resource is None:
            self.output("Out of memes try again tommorow.", args)
        ComputerMemeScene(resource=resource).generate(filename)
        self.output("http://%s/%s" % (CONFIG_MY_IP, filename.split("/")[1]), args)

    def shutup(self, args):
        self.shutup = True
        self.output(CONFIG_MESSAGE_SHUTUP, args)

    def wakeup(self, args):
        self.shutup = False
        self.output(CONFIG_MESSAGE_WAKEUP, args)

    def process_message(self, message, args, is_owner=False, learning=True):
        # Always reply when we are mentioned
        if args['mentioned'] and self.shutup is False:
            self.ai.process_msg(self, message, 100, args, learning=learning)
        elif self.shutup is False:
            self.ai.process_msg(self, message, self.replyrate, args, owner=is_owner, learning=learning)
        else:
            self.ai.process_msg(self, message, 0, args, learning=learning)
