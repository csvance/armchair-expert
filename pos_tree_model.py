from config import *
import json
import numpy as np
import re

from markov_schema import *


def rebuild_pos_tree_from_db(nlp):
    pos_tree_model = PosTreeModel(nlp=nlp, people=CONFIG_DISCORD_MEMBERS, rebuild=True)

    # Process database lines
    session = Session()
    lines = session.query(Line).filter(Line.author != CONFIG_DISCORD_ME).order_by(Line.timestamp).all()
    for line in lines:
        print(line)
        pos_tree_model.process_sentence(line.text)

    pos_tree_model.update_probabilities()
    pos_tree_model.save()


class PosTreeModel(object):
    def __init__(self, nlp=None, path: str=CONFIG_POS_TREE_CONFIG_PATH, people: dict=None, rebuild: bool=False):
        self.tree = {}
        self.nlp = nlp
        self.path = path
        self.people = people

        if path is not None and not rebuild:
            self.load(path)

    @staticmethod
    def pos_from_word(word: str, nlp, people: list=None) -> str:

        # Makeup for shortcomings of NLP detecting online nicknames
        if people is not None:
            if word in people:
                return 'NOUN'

        # spacy detects emoji in the format of :happy: as PUNCT, give it its own POS
        if re.match(r"<:[a-z0-9_]+:[0-9_]+>", word) or re.match(r":[a-z_]+:", word):
            pos = 'EMOJI'
        else:
            nlp_doc = nlp(word)
            pos = nlp_doc[0].pos_
        return pos

    def generate_sentence(self,tree_start: dict=None, words: list=None) -> list:

        if tree_start is None:
            tree_start = self.tree

        a_choices = []
        p_values = []

        pos_keys = [x for x in tree_start if x.find("_") == -1]

        if len(pos_keys) == 0:
            return words

        for pos in pos_keys:
            a_choices.append(pos)
            p_values.append(tree_start[pos]['_p'])

        a_choices.append('_e')
        p_values.append(tree_start['_e_p'])

        choice = np.random.choice(a_choices,p=p_values)
        if choice != '_e':
            words.append(choice)
        else:
            return words

        return self.generate_sentence(tree_start[choice],words)

    def update_probabilities(self, tree_branch=None, deep: bool=True) -> None:

        start = False
        if tree_branch is None:
            tree_branch = self.tree
            start = True

        pos_keys = [x for x in tree_branch if x.find("_") == -1]

        tree_sum = 0.
        for pos_key in pos_keys:
            tree_sum += tree_branch[pos_key]['_c']

        if not start and '_e_c' in tree_branch:
            tree_sum += tree_branch['_e_c']

        for pos_key in pos_keys:
            tree_branch[pos_key]['_p'] = tree_branch[pos_key]['_c'] / tree_sum

        if not start and '_e_c' in tree_branch:
            tree_branch['_e_p'] = tree_branch['_e_c'] / tree_sum
        else:
            tree_branch['_e_p'] = 0.

        if not deep:
            return

        # Recurse through each child
        for pos_key in pos_keys:
            self.update_probabilities(tree_branch[pos_key])

    def process_sentence(self, sentence: str, update_prob: bool=False) -> None:
        tree_branch = self.tree

        for word in sentence.split(" "):

            if len(word) == 0:
                continue

            nlp_pos = None
            if self.people is not None:
                if word in self.people:
                    nlp_pos = "NOUN"

            if nlp_pos is None:
                nlp_pos = PosTreeModel.pos_from_word(word, self.nlp, people=self.people)

            if nlp_pos in tree_branch:
                tree_branch[nlp_pos]['_c'] += 1
            else:
                tree_branch[nlp_pos] = {}
                tree_branch[nlp_pos]['_c'] = 1

            # TODO: Fix this, it breaks something
            # if update_prob:
            #     self.update_probabilities(tree_branch, deep=False)

            tree_branch = tree_branch[nlp_pos]

        if '_e_c' in tree_branch:
            tree_branch['_e_c'] += 1
        else:
            tree_branch['_e_c'] = 1

    def save(self,path: str=None) -> None:
        if path is None:
            open(self.path,'w').write(json.dumps(self.tree,separators=(',', ':')))
        else:
            open(path, 'w').write(json.dumps(self.tree,separators=(',', ':')))

    def load(self,path: str) -> None:
        try:
            data = open(path,'r').read()
        except FileNotFoundError:
            return
        self.tree = json.loads(data)

    def process_line(self, line: str) -> None:
        for sentence in re.split(CONFIG_MARKOV_SENTENCE_GROUP_SPLIT, line):
            self.process_sentence(sentence)

    def process_text(self, text: str) -> None:
        for line in text.split("\n"):
            self.process_line(re.sub(CONFIG_MARKOV_SYMBOL_STRIP, "", line))

    def update_people(self, people: str) -> None:
        self.people = people
