from config import *
import json
import numpy as np
import re


class PosTreeModel(object):
    def __init__(self, nlp=None, path="models/pos-tree-model/tree.json"):
        self.tree = {}
        self.nlp = nlp
        self.path = path

        if path is not None:
            self.load(path)

    @staticmethod
    def pos_from_word(word: str, nlp) -> str:
        # spacy detects emoji in the format of :happy: as PUNCT, give it its own POS
        if re.match(r"<:[a-z]+:[0-9]+>", word) or re.match(r":[a-z]+:", word):
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

        # If the length of the tree is only 4 this is the end of the sentence
        if len(tree_start) == 3:
            print(tree_start.keys())
            return words

        for pos in tree_start:
            if pos[0] == '_':
                continue
            a_choices.append(pos)
            p_values.append(tree_start[pos]['_p'])

        a_choices.append('_e')
        p_values.append(tree_start['_e_p'])

        choice = np.random.choice(a_choices,p=p_values)
        if choice != '_e':
            words.append(choice)

        # Cut off the chain since we rolled ending
        if choice == '_e':
            return words

        return self.generate_sentence(tree_start[choice],words)

    def update_probabilities(self, tree_branch=None) -> None:

        start = False
        if tree_branch is None:
            tree_branch = self.tree
            start = True

        tree_sum = 0.
        for pos in tree_branch:
            if pos[0] == '_':
                continue
            tree_sum += tree_branch[pos]['_c']

        if not start and '_e_c' in tree_branch:
            tree_sum += tree_branch['_e_c']

        for pos in tree_branch:
            if pos[0] == '_':
                continue
            tree_branch[pos]['_p'] = tree_branch[pos]['_c'] / tree_sum

        if not start and '_e_c' in tree_branch:
            tree_branch['_e_p'] = tree_branch['_e_c'] / tree_sum
        else:
            tree_branch['_e_p'] = 0.

        # Recurse through each child
        for pos in tree_branch:
            if pos[0] != "_":
                self.update_probabilities(tree_branch[pos])

    def process_sentence(self, sentence: str) -> None:
        tree_branch = self.tree

        for word in sentence.split(" "):

            if len(word) == 0:
                continue

            nlp_pos = PosTreeModel.pos_from_word(word,self.nlp)
            if str(nlp_pos) == 'PUNCT':
                print(word)

            if nlp_pos in tree_branch:
                tree_branch[nlp_pos]['_c'] += 1
            else:
                tree_branch[nlp_pos] = {}
                tree_branch[nlp_pos]['_c'] = 1

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
            self.process_line(re.sub(r'"|\(|\)|\[|\]|{|}|%|@|$|\^|&|\*|_|\\|/', "", line))