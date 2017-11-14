import spacy
from config import *
from pos_tree_model import *


if __name__ == '__main__':
    nlp = spacy.load('en')
    rebuild_pos_tree_from_db(nlp)
    print("All Done!")