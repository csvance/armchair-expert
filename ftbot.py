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
        self.reply = {'channel': args['channel'],'message': msg}

    def memegen(self,msg,args):
        filename = "%s/meme_%s.jpg" % (CONFIG_SERVE_DIR,random.randint(0,9999999))
        resource = GoogleImages(msg, CONFIG_GOOGLE_KEY, CONFIG_GOOGLE_CX).execute(CONFIG_DOWNLOAD_DIR)
        ComputerMemeScene(resource=resource).generate(filename)
        self.output("http://%s/%s" % (CONFIG_MY_IP,filename.split("/")[1]),args)

    def process_message(self,message,args,is_owner=False):
        #Always reply when we are mentioned
        if(message.find(CONFIG_DISCORD_MENTION_ME) != -1 and self.shutup == False):
            self.pyborg.process_msg(self, message, 100, 1, args, not_quiet=1, owner=is_owner)
        elif(self.shutup == False):
            self.pyborg.process_msg(self, message, self.replyrate, 1, args, not_quiet=1, owner=is_owner)
        else:
            self.pyborg.process_msg(self, message, 0, 1, args, not_quiet=1, owner=is_owner)



