import spacy
from spacymoji import Emoji
from config import *
from pos_tree_model import *


if __name__ == '__main__':
    nlp = spacy.load('en')
    emoji = Emoji(nlp)
    nlp.add_pipe(emoji, first=True)
    rebuild_pos_tree_from_db(nlp)
    print("All Done!")