from pos_tree_model import *
from ml_common import create_nlp_instance

nlp = create_nlp_instance()

pos_tree_model = PosTreeModel(nlp=nlp)

runs = 100000
for i in range(0,runs):
    pos_tree_model.generate_sentence(words=[])