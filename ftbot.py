from config import *
from search import *
from memegen import *
from pyborg import pyborg
import sys

class FTBot(object):

    def __init__(self):
        self.pyborg = pyborg()

    def output(self,msg,args):
        print("Message: %s" % msg)
        print("Args: %s" % args)


    def run(self):
        while(True):
            msg = input('FTBot> ')
            if(msg == 'quit'):
                return
            self.pyborg.process_msg(self,msg,100,1,None,owner=1,not_quiet=1)
        sys.exit(0)


if False:
    resource = GoogleImages('viper rapper', CONFIG_KEY, CONFIG_CX).execute(CONFIG_DOWNLOAD_DIR,rand=True)
    ComputerMemeScene(resource=resource).generate()


bot = FTBot()
bot.run()