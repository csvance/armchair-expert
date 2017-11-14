import asyncio
import os

from armchair_expert import *
from messages import *

from ml_common import TXTFileFeeder


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

    ftbot = ArmchairExpert(event_loop=asyncio.get_event_loop())

    path = "training/markov_training_files"
    process_files = []
    root, dirs, files = os.walk(path).__next__()
    for filename in files:
        process_files.append("%s/%s" % (root, filename))
    feed(ftbot.ai, process_files)

    print("All Done!")
