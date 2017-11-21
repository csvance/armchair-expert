from pos_tree_model import *
from config import *
from ml_common import create_spacy_instance

nlp = create_spacy_instance()

pos_tree_model = PosTreeModel(path=CONFIG_POS_TREE_CONFIG_PATH, nlp=nlp)

runs = 100000
for i in range(0,runs):
    pos_tree_model.generate_sentence(words=[])