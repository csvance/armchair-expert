import os

import spacy

from messages import *
from ml_common import *


if __name__ == '__main__':

    path = "training/markov_training_files"
    nlp = spacy.load('en')
    process_files = []
    pos_tree_model = PosTreeModel(nlp=nlp, people=CONFIG_DISCORD_MEMBERS)

    training_data_fetcher = DirectoryFileDataFetcher(path)

    for line in training_data_fetcher.get_data():
        print(line)
        pos_tree_model.process_text(line)

    pos_tree_model.update_probabilities()
    pos_tree_model.save()

    print("All Done!")
