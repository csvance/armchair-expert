from config import *
from search import *
from memegen import *

from pyborg import pyborg

class FTBot(object):

    def __init__(self):
        self.pyborg = pyborg()
        self.replyrate = 100
        self.reply = None

    def output(self,msg,args):
        #resource = GoogleImages(msg, CONFIG_KEY, CONFIG_CX).execute(CONFIG_DOWNLOAD_DIR, rand=True)
        #ComputerMemeScene(resource=resource).generate()
        self.reply = {'channel': args['channel'],'message': msg}

    def process_message(self,message,args):
        self.pyborg.process_msg(self, message, self.replyrate, 1, args, not_quiet=1)




