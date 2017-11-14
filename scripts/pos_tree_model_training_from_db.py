import spacy
from config import *
from pos_tree_model import *
from markov_schema import *

if __name__ == '__main__':

    nlp = spacy.load('en')
    pos_tree_model = PosTreeModel(nlp=nlp, people=CONFIG_DISCORD_MEMBERS)

    # Process database lines
    session = Session()
    lines = session.query(Line).filter(Line.author != CONFIG_DISCORD_ME).order_by(Line.timestamp).all()
    for line in lines:
        print(line)
        pos_tree_model.process_sentence(line.text)

    pos_tree_model.update_probabilities()
    pos_tree_model.save()

    print("All Done!")