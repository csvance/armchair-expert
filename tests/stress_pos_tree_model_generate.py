from pos_tree_model import *
import spacy

nlp = spacy.load('en')

pos_tree_model = PosTreeModel(nlp=nlp)

runs = 100000
for i in range(0,runs):
    pos_tree_model.generate_sentence(words=[])