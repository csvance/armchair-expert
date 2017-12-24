import json
import numpy as np
import zlib
from typing import List, Optional
from spacy.tokens import Doc
from nlp_common import Pos


class PosTreeModel(object):
    def __init__(self):
        self.tree = {}

    def _generate_sentence(self, tree_start: dict = None, words: list = None) -> List[Pos]:

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

        choice = np.random.choice(a_choices, p=p_values)
        if choice != '_e':
            words.append(Pos[choice])
        else:
            if words[:-1] != 'EOS':
                words.append(Pos.EOS)
            return words

        return self._generate_sentence(tree_start[choice], words)

    def generate_sentence(self):
        words = []
        return self._generate_sentence(words=words)

    def update_probabilities(self, tree_branch=None, deep: bool = True, start=False) -> None:

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
            self.update_probabilities(tree_branch[pos_key], start=False)

    def save(self, path: str) -> None:
        open(path, 'wb').write(zlib.compress(json.dumps(self.tree, separators=(',', ':')).encode()))

    def load(self, path: str) -> None:
        data = zlib.decompress(open(path, 'rb').read()).decode()
        self.tree = json.loads(data)

    def learn(self, doc: Doc, update_prob=False, people: Optional[List[str]] = None) -> None:
        tree_branch = self.tree

        for sent_idx, sent in enumerate(doc.sents):
            for token_index, token in enumerate(sent):

                custom_pos = Pos.from_token(token, people=people)
                pos_key = str(custom_pos).split(".")[1]

                if pos_key in tree_branch:
                    tree_branch[pos_key]['_c'] += 1
                else:
                    tree_branch[pos_key] = {}
                    tree_branch[pos_key]['_c'] = 1

                if update_prob:
                    start = False if token_index == 0 else True
                    self.update_probabilities(tree_branch, deep=False, start=start)

                tree_branch = tree_branch[pos_key]

            # Inject a fake PoS 'EOS' at the end of every sentence
            pos_key = 'EOS'
            if pos_key in tree_branch:
                tree_branch[pos_key]['_c'] += 1
            else:
                tree_branch[pos_key] = {}
                tree_branch[pos_key]['_c'] = 1

            if update_prob:
                self.update_probabilities(tree_branch, deep=False, start=False)

            tree_branch = tree_branch[pos_key]

        if '_e_c' in tree_branch:
            tree_branch['_e_c'] += 1
        else:
            tree_branch['_e_c'] = 1
