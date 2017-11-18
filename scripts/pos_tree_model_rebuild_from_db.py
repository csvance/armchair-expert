import spacy
from spacymoji import Emoji
from config import *
from pos_tree_model import *
from ml_common import create_nlp_instance

if __name__ == '__main__':
    nlp = create_nlp_instance()
    rebuild_pos_tree_from_db(nlp)
    print("All Done!")