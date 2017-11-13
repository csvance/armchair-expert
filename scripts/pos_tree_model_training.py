from pos_tree_model import PosTreeModel

import os
import spacy
from messages import *
import emoji

from ml_common import TXTFileFeeder


def feed(pos_model, training_files):
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
            pos_model.process_text(emoji.demojize(line))

if __name__ == '__main__':

    path = "training/markov_training_files"
    nlp = spacy.load('en')
    process_files = []
    root, dirs, files = os.walk(path).__next__()
    for filename in files:
        process_files.append("%s/%s" % (root, filename))

    pos_tree_model = PosTreeModel(nlp=nlp)
    feed(pos_tree_model, process_files)
    pos_tree_model.update_probabilities()
    pos_tree_model.save()

    print("All Done!")
