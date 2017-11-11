import asyncio

from config import *
from ftbot import *
from messages import *
import os


class TXTFileFeeder(object):
    def __init__(self,path):
        data = open(path,'r').read()
        self.lines = self.filter_lines(data.split("\n"))

    def filter_lines(self,lines):

        filtered_line_list = []

        for line in lines:
            if line != '':
                filtered_line_list.append(line.strip())

        return filtered_line_list


def feed(ai, training_files):

    def get_extension(filename):
        return filename.split(".")[1]

    for file in training_files:

        feeder = None
        if get_extension(file) == "txt":
            feeder = TXTFileFeeder(file)
        else:
            print("Unhandled file extension: %s" % get_extension(file))
            continue

        for line in feeder.lines:
            print(line)
            input_message = MessageInput(text=line)
            ai.process_msg(None,input_message,replyrate=0)


if __name__ == '__main__':

    print("Starting FTBot")
    ftbot = FTBot(event_loop=asyncio.get_event_loop())

    print("Training...")

    path = "training/markov_training_files"
    process_files = []
    root, dirs, files = os.walk(path).__next__()
    for filename in files:
        process_files.append("%s/%s" % (root,filename))
    feed(ftbot.ai,process_files)

    print("All Done!")

