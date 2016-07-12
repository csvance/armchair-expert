from config import *
from search import *
from memegen import *

from pyborg import pyborg

class FTBot(object):

    def __init__(self):
        self.pyborg = pyborg()
        self.replyrate = CONFIG_DEFAULT_REPLYRATE
        self.reply = None
        self.shutup = False

    def output(self,msg,args):
        #resource = GoogleImages(msg, CONFIG_KEY, CONFIG_CX).execute(CONFIG_DOWNLOAD_DIR, rand=True)
        #ComputerMemeScene(resource=resource).generate()
        self.reply = {'channel': args['channel'],'message': msg}

    def process_message(self,message,args,is_owner=False):
        #Always reply when we are mentioned
        if(message.startswith('@FTBot') and self.shutup == False):
            self.pyborg.process_msg(self, message, 100, 1, args, not_quiet=1, owner=is_owner)
        elif(self.shutup == False):
            self.pyborg.process_msg(self, message, self.replyrate, 1, args, not_quiet=1, owner=is_owner)
        else:
            self.pyborg.process_msg(self, message, 0, 1, args, not_quiet=1, owner=is_owner)




