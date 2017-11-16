import asyncio
import os

from armchair_expert import *
from messages import *

from ml_common import *

if __name__ == '__main__':

    ai = MarkovAI()

    path = "training/markov_training_files"
    directory_data_fetcher = DirectoryUnstructuredDataFetcher(path)

    for line in directory_data_fetcher.get_data():
        print(line)
        input_message = MessageInput(text=line)
        ai.process_msg(None, input_message, replyrate=0)

    print("All Done!")
