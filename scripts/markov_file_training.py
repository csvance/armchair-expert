import asyncio
import os

from ftbot import *
from messages import *


class TXTFileFeeder(object):
    def __init__(self, data_file_path):
        data = open(data_file_path, 'r').read()
        self.lines = self.filter_lines(data.split("\n"))

    # noinspection PyMethodMayBeStatic
    def filter_lines(self, lines):

        filtered_line_list = []

        for line in lines:
            if line != '':
                filtered_line_list.append(line.strip())

        return filtered_line_list


def feed(ai, training_files):
    def get_extension(file_name):
        return file_name.split(".")[1]

    for file in training_files:

        if get_extension(file) == "txt":
            feeder = TXTFileFeeder(file)
        else:
            print("Unhandled file extension: %s" % get_extension(file))
            continue

        for line in feeder.lines:
            print(line)
            input_message = MessageInput(text=line)
            ai.process_msg(None, input_message, replyrate=0)


if __name__ == '__main__':

    print("Starting FTBot")
    ftbot = FTBot(event_loop=asyncio.get_event_loop())

    print("Training...")

    path = "training/markov_training_files"
    process_files = []
    root, dirs, files = os.walk(path).__next__()
    for filename in files:
        process_files.append("%s/%s" % (root, filename))
    feed(ftbot.ai, process_files)

    print("All Done!")
